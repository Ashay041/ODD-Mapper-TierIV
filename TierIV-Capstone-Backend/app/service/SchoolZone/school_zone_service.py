import json
import os
from datetime import datetime

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from pymongo import UpdateOne
from pydantic import ValidationError
from shapely.geometry import mapping
from flask import Blueprint, jsonify

from app import local_cache, mongo
from app.models import BaseExporter, WebRequest, Feature, FeatureDict
from app.service.query.query_models import MapLocation

class SchoolZoneMapper:
    """
    Acts as a service to generate school zone data.
    It now operates on a pre-existing graph and GeoDataFrame for efficiency.
    It dissolves overlapping zones into single, continuous areas.
    """
    def __init__(self, graph: nx.MultiDiGraph, features_gdf: gpd.GeoDataFrame, school_zone_radius=100):
        self.graph = graph
        self.features_gdf = features_gdf
        self.school_zone_radius = school_zone_radius
        self.schools = None
        self.school_zones = None # This will hold the final, dissolved zones
        self.road_nodes_in_zones = []

    def _fetch_schools(self):
        """Internal: Fetches school and kindergarten data from the provided GeoDataFrame."""
        print("Filtering schools from the cached GeoDataFrame...")
        try:
            school_tags = ["school", "kindergarten"]
            if 'amenity' not in self.features_gdf.columns:
                print("Warning: 'amenity' column not found in cached GDF.")
                self.schools = gpd.GeoDataFrame()
                return False

            gdf = self.features_gdf[self.features_gdf['amenity'].isin(school_tags)].copy()

            if gdf.empty:
                print("No schools or kindergartens found in the cached GDF.")
                self.schools = gpd.GeoDataFrame()
                return False
            
            gdf = gdf[~gdf.index.duplicated(keep='first')].copy()
            gdf['facility_type'] = gdf.apply(
                lambda row: 'kindergarten' if 'kindergarten' in str(row.get('amenity')) else 'school', axis=1)
            self.schools = gdf
            print(f"Found {len(self.schools)} unique facilities.")
            return True
        except Exception as e:
            print(f"An error occurred while fetching schools from GDF: {e}")
            return False

    def _create_school_zones(self):
        """Internal: Creates the initial circular buffer zones for each facility."""
        if self.schools is None or self.schools.empty: return False
        print("Creating initial circular school zones...")
        
        G_proj = ox.project_graph(self.graph)
        schools_projected = self.schools.to_crs(G_proj.graph['crs'])
        buffers = schools_projected.geometry.buffer(self.school_zone_radius)
        
        # This creates the initial, potentially overlapping zones
        initial_zones = gpd.GeoDataFrame(geometry=buffers, crs=G_proj.graph['crs']).to_crs(self.graph.graph['crs'])
        
        # We need to associate the original school data with these zones for the next step
        self.school_zones = self.schools.copy().set_geometry(initial_zones.geometry)
        return True

    def _dissolve_and_aggregate_zones(self):
        """
        Internal: Dissolves overlapping zones and aggregates the data of the
        schools contained within each new, larger zone.
        """
        if self.school_zones is None or self.school_zones.empty:
            return False

        print("Dissolving overlapping zones and aggregating school data...")

        # 1. Dissolve all overlapping polygons. 'explode' separates any non-contiguous zones.
        zones_to_dissolve = self.school_zones.copy()
        zones_to_dissolve['dissolve_key'] = 1
        # --- FIX: Only keep the geometry column after dissolving to prevent column name conflicts ---
        dissolved_gdf = zones_to_dissolve.dissolve(by='dissolve_key')[['geometry']]
        dissolved_gdf = dissolved_gdf.explode(index_parts=False).reset_index(drop=True)

        # 2. Spatially join the original school points to the new dissolved zones
        schools_in_dissolved_zones = gpd.sjoin(self.schools, dissolved_gdf, how="inner", predicate="within")

        # 3. Aggregate the school data for each dissolved zone
        def create_facility_dict(row):
            centroid = row.geometry.centroid
            return {
                'name': row.get('name'),
                'type': row['facility_type'], # This will now work correctly
                'center': [centroid.x, centroid.y]
            }
        schools_in_dissolved_zones['facility_info'] = schools_in_dissolved_zones.apply(create_facility_dict, axis=1)

        # Group by the dissolved zone's index and aggregate the facility info into a list
        aggregated_data = schools_in_dissolved_zones.groupby('index_right').agg({
            'facility_info': list
        }).rename(columns={'facility_info': 'facilities'})

        # 4. Merge the aggregated data back with the dissolved geometries
        final_zones = dissolved_gdf.merge(aggregated_data, left_index=True, right_index=True)

        # 5. Update the class attribute with the final dissolved zones
        self.school_zones = final_zones
        print(f"Created {len(self.school_zones)} final dissolved school zones.")
        return True

    def _calculate_nodes_in_zones(self):
        """Internal: Gets road network data from the provided graph and saves it to MongoDB."""
        if self.school_zones is None or self.school_zones.empty: return False
        print("Getting nodes and edges from the cached graph...")
        try:
            nodes, edges = ox.graph_to_gdfs(self.graph)
        except Exception as e:
            print(f"Could not convert graph to GeoDataFrames: {e}")
            return False
        
        print("Identifying nodes within zones for internal use...")
        # unary_union is correct here as it creates a single geometry for intersection tests
        unified_zones = self.school_zones.geometry.unary_union
        nodes_inside = nodes[nodes.within(unified_zones)]
        edge_node_ids = set()
        
        inside_node_ids = set(nodes_inside.index)
        intersecting_edges = edges[edges.intersects(unified_zones)]
        if not intersecting_edges.empty:
            edge_data = intersecting_edges.reset_index()
            edge_node_ids.update(edge_data['u'])
            edge_node_ids.update(edge_data['v'])
        
        final_node_ids = inside_node_ids.union(edge_node_ids)
        self.road_nodes_in_zones = sorted(list(final_node_ids))
        print(f"Found and stored {len(self.road_nodes_in_zones)} nodes for later use.")

        # # --- Database Insertion Logic ---
        # try:
        #     net_coll = mongo.db.network_noncompliant
        #     if self.road_nodes_in_zones:
        #         for node_id in self.road_nodes_in_zones:
        #             net_coll.insert_one({'id': node_id, 'odd': 'school_zone'})
        #         print(f"Inserted {len(self.road_nodes_in_zones)} individual 'school_zone' documents into 'network_noncompliant'.")
        # except Exception as e:
        #     print(f"An error occurred while saving nodes to MongoDB: {e}")
            
        # return True
            # --- Database Insertion Logic (Updated for Efficiency and to Prevent Duplicates) ---
        try:
            from flask import current_app
            net_coll = mongo.db.network_feature #type:ignore
            if self.road_nodes_in_zones:
                # Create a list of bulk "upsert" operations.
                # An upsert will insert a document if it doesn't exist, or do nothing if it does.
                # This is the most efficient way to handle this "insert if not exists" logic.
                operations = [
                    UpdateOne(
                        {'_id': node_id},
                        {'$addToSet': {
                            'features': {
                                'feature_type': 'school_zone'
                            }
                        }
                        },
                        upsert=True
                    )
                    for node_id in self.road_nodes_in_zones
                ]

                # Execute the bulk write operation if the list is not empty
                if operations:
                    result = net_coll.bulk_write(operations, ordered=False)
                    print(f"Bulk write to 'network_noncompliant' complete.")
                    print(f"  - Nodes already present: {result.matched_count}")
                    print(f"  - New nodes inserted: {result.upserted_count}")
            else:
                print("No road nodes found within school zones to process for database insertion.")
                
        except Exception as e:
            print(f"An error occurred while saving nodes to MongoDB: {e}")
            
        return True

    def generate_zone_data(self):
        """
        Executes the full workflow and returns a dictionary suitable for an API response.
        """
        if not self._fetch_schools() or not self._create_school_zones():
            return {"result": [], "status_code": 404}

        # --- NEW STEP: Dissolve the zones after creating them ---
        self._dissolve_and_aggregate_zones()
        
        self._calculate_nodes_in_zones()

        zone_features = []
        # --- MODIFIED LOOP: Iterate over the final dissolved zones ---
        for index, zone in self.school_zones.iterrows():
            feature_dict = {
                "type": "Feature",
                "geometry": mapping(zone.geometry), # Use the dissolved geometry
                "properties": {
                    "feature_type": "school_zone",
                    # Use the new aggregated list of facilities
                    "facilities": zone['facilities'] 
                }
            }
            try:
                # Note: Your BaseExporter model may need to be updated to accept this new 'properties' structure
                validated_feature = BaseExporter.model_validate(feature_dict)
                zone_features.append(validated_feature.model_dump(mode="json"))
            except ValidationError as e:
                print(f"Validation failed for dissolved zone {index}: {e}")
                continue
        
        return zone_features

school_zone_bp = Blueprint('school_zone_bp', __name__, url_prefix='/school_zone')

@school_zone_bp.route('/', methods=['POST'], strict_slashes=False)
def generate_school_zones_endpoint():
    """
    API endpoint to generate school zone data. It uses the SchoolZoneMapper
    class as a service to perform the analysis on the cached graph.
    """
    req_obj = local_cache.get('request')
    if not isinstance(req_obj, WebRequest):
        return jsonify(error="Request context not found in cache. Please run a query first."), 400

    G = local_cache.get('graph')
    if G is None:
        return jsonify(error="Graph not found in cache. Please run a query first."), 400
        
    gdf = local_cache.get('gdf')
    if gdf is None:
        return jsonify(error="GDF not found in cache. Please run a query first."), 400

    mapper = SchoolZoneMapper(
        graph=G,
        features_gdf=gdf,
        school_zone_radius=getattr(req_obj, 'school_zone_radius', 100),
    )

    api_response = mapper.generate_zone_data()

    # feature map
    zone_type_map = Feature('school_zone', [True, False])
    feature_map = FeatureDict()
    feature_map.add_feature_type('school_zone', [zone_type_map])

    return jsonify({'results': api_response, 'feature_dict': feature_map.out()}), 200
