import json
import os
from datetime import datetime

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from pydantic import ValidationError
from shapely.geometry import mapping
from flask import Blueprint, jsonify
from pymongo import UpdateOne

from app import local_cache, mongo
from app.models import BaseExporter, WebRequest, Feature, FeatureDict
from app.service.query.query_models import MapLocation

class ParkingLotMapper:
    """
    Acts as a service to identify parking lots and their connecting road nodes.
    It unifies Point and Polygon geometries, then dissolves overlapping lots.
    """
    def __init__(self, graph: nx.MultiDiGraph, features_gdf: gpd.GeoDataFrame, point_buffer_radius=15):
        self.graph = graph
        self.features_gdf = features_gdf
        self.point_buffer_radius = point_buffer_radius # Radius in meters to buffer points into polygons
        self.parking_lots = None # This will hold the final, dissolved parking zones
        self.connecting_nodes = []

    def _fetch_parking_lots(self):
        """Internal: Fetches parking lot features from the provided GeoDataFrame."""
        print("Filtering parking lots from the cached GeoDataFrame...")
        try:
            parking_tag = "parking"
            if 'amenity' not in self.features_gdf.columns:
                print("Warning: 'amenity' column not found in cached GDF.")
                self.parking_lots = gpd.GeoDataFrame()
                return False

            gdf = self.features_gdf[self.features_gdf['amenity'] == parking_tag].copy()

            if gdf.empty:
                print("No parking lots found in the cached GDF.")
                self.parking_lots = gpd.GeoDataFrame()
                return False
            
            self.parking_lots = gdf[~gdf.index.duplicated(keep='first')].copy()
            print(f"Found {len(self.parking_lots)} initial parking lot features.")
            return True
        except Exception as e:
            print(f"An error occurred while fetching parking lots from GDF: {e}")
            return False

    def _unify_geometries(self):
        """
        Internal: Converts any Point geometries into Polygons by applying a buffer.
        This ensures all parking features have an area for dissolving.
        """
        if self.parking_lots is None or self.parking_lots.empty:
            return False
        
        print("Unifying geometries: Buffering points to polygons...")
        
        # Project to local UTM for accurate meter-based buffering
        G_proj = ox.project_graph(self.graph)
        lots_proj = self.parking_lots.to_crs(G_proj.graph['crs'])

        # Identify which geometries are points
        is_point = lots_proj.geometry.geom_type == 'Point'
        
        # Buffer only the points
        lots_proj.loc[is_point, 'geometry'] = lots_proj.loc[is_point].buffer(self.point_buffer_radius)
        
        # Project back to the original CRS and update the main DataFrame
        self.parking_lots = lots_proj.to_crs(self.graph.graph['crs'])
        print("All parking features are now represented as polygons.")
        return True

    def _dissolve_and_aggregate_lots(self):
        """
        Internal: Dissolves overlapping parking polygons and aggregates their data.
        """
        if self.parking_lots is None or self.parking_lots.empty:
            return False

        print("Dissolving overlapping parking lots and aggregating data...")

        # Create a copy to preserve original data for the spatial join
        original_lots_for_join = self.parking_lots.copy()
        
        # Dissolve all overlapping polygons
        lots_to_dissolve = self.parking_lots.copy()
        lots_to_dissolve['dissolve_key'] = 1
        dissolved_gdf = lots_to_dissolve.dissolve(by='dissolve_key')[['geometry']]
        dissolved_gdf = dissolved_gdf.explode(index_parts=False).reset_index(drop=True)

        # Spatially join the original lots to the new dissolved zones
        lots_in_dissolved_zones = gpd.sjoin(original_lots_for_join, dissolved_gdf, how="inner", predicate="intersects")

        # Aggregate the lot data for each dissolved zone
        def create_facility_dict(row):
            centroid = row.geometry.centroid
            return {
                'name': row.get('name'),
                'center': [centroid.x, centroid.y]
            }
        lots_in_dissolved_zones['facility_info'] = lots_in_dissolved_zones.apply(create_facility_dict, axis=1)

        aggregated_data = lots_in_dissolved_zones.groupby('index_right').agg({
            'facility_info': list
        }).rename(columns={'facility_info': 'facilities'})

        # Merge the aggregated data back with the dissolved geometries
        self.parking_lots = dissolved_gdf.merge(aggregated_data, left_index=True, right_index=True)
        print(f"Created {len(self.parking_lots)} final dissolved parking lot zones.")
        return True

    def _find_connecting_nodes(self):
        """Internal: Finds road nodes connected to the final dissolved parking lots."""
        if self.parking_lots is None or self.parking_lots.empty:
            return False

        print("Finding road nodes connected to parking lots...")
        try:
            nodes, edges = ox.graph_to_gdfs(self.graph)
            unified_zones = self.parking_lots.geometry.unary_union
            
            intersecting_edges = edges[edges.intersects(unified_zones)]
            
            all_connecting_nodes = set()
            if not intersecting_edges.empty:
                edge_data = intersecting_edges.reset_index()
                all_connecting_nodes.update(edge_data['u'])
                all_connecting_nodes.update(edge_data['v'])
            
            self.connecting_nodes = sorted(list(all_connecting_nodes))
            print(f"Found {len(self.connecting_nodes)} road nodes connected to parking lots.")
            return True
        except Exception as e:
            print(f"An error occurred while finding connecting nodes: {e}")
            return False

    def _save_nodes_to_db(self):
        """Internal: Saves the connecting node IDs to the non-compliant collection."""
        if not self.connecting_nodes:
            return True
            
        print("Saving connecting nodes to MongoDB...")
        try:
            net_coll = mongo.db.road_feature #type:ignore
            operations = []
            for node_id in self.connecting_nodes:
                operations = [
                    UpdateOne(
                        {'_id': node_id},
                        {'$addToSet': {
                            'features': {
                                'feature_type': 'parking_lot'
                            }
                        }
                        },
                        upsert=True
                    )
                ]
            if operations:
                result = net_coll.bulk_write(operations, ordered=False)
        except Exception as e:
            print(f"An error occurred while saving nodes to MongoDB: {e}")
        
        return True

    def generate_data(self):
        """
        Executes the full workflow and returns a dictionary for the API response.
        """
        if not self._fetch_parking_lots():
            return {"result": [], "status_code": 404, "message": "No parking lots found."}

        self._unify_geometries()
        self._dissolve_and_aggregate_lots()
        self._find_connecting_nodes()
        self._save_nodes_to_db()

        parking_features = []
        for index, lot in self.parking_lots.iterrows():
            feature_dict = {
                "type": "Feature",
                "geometry": mapping(lot.geometry),
                "properties": {
                    "feature_type": "odd_parking_lot",
                    "facilities": lot['facilities']
                }
            }
            try:
                # Note: Your BaseExporter model may need to be updated for this new structure
                validated_feature = BaseExporter.model_validate(feature_dict)
                parking_features.append(validated_feature.model_dump(mode="json"))
            except ValidationError as e:
                print(f"Validation failed for parking lot {index}: {e}")
                continue
        
        return parking_features


parking_lot_bp = Blueprint('parking_lot_bp', __name__, url_prefix='/parking_lot')

@parking_lot_bp.route('/', methods=['POST'], strict_slashes=False)
def generate_parking_lots_endpoint():
    """
    API endpoint to generate ODD parking lot data and find connecting nodes.
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

    mapper = ParkingLotMapper(
        graph=G,
        features_gdf=gdf,
    )

    api_response = mapper.generate_data()

    # feature map
    parking_type_map = Feature('parking_lot', [True, False])
    feature_map = FeatureDict()
    feature_map.add_feature_type('parking_lot', [parking_type_map])

    return jsonify({'results': api_response, 'feature_dict': feature_map.out()}), 200
