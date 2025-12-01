import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from pymongo import UpdateOne
from pydantic import ValidationError
from flask import Blueprint, jsonify, current_app
from shapely.geometry import mapping

from app.extensions import mongo, local_cache
from app.models import WebRequest, BaseExporter, Feature, FeatureDict
from .road_features_models import *


class RoadFeatureExtractor:
    """
    Service to extract detailed road features from OSM graph data.
    Processes cached graph to extract comprehensive road segment information.
    """
    
    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph
        self.road_features: List[RoadFeature] = []
        self.extraction_timestamp = datetime.utcnow().isoformat()
    
    def _parse_speed_limit(self, maxspeed_tag: Any) -> Optional[float]:
        """Parse speed limit from OSM maxspeed tag"""
        if not maxspeed_tag:
            return None
        
        speed_str = str(maxspeed_tag).strip().lower()
        
        # Handle common speed formats
        if speed_str in ['none', 'unlimited', 'signals']:
            return None
        
        # Extract numeric speed
        speed_match = re.search(r'(\d+)', speed_str)
        if not speed_match:
            return None
        
        speed_value = float(speed_match.group(1))
        
        # Convert mph to km/h if needed
        if 'mph' in speed_str:
            speed_value = speed_value * 1.60934
        
        return speed_value
    
    def _parse_lane_count(self, edge_data: Dict) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Parse lane information from edge data"""
        total_lanes = None
        lanes_forward = None
        lanes_backward = None
        
        # Try to get total lanes
        if 'lanes' in edge_data:
            try:
                total_lanes = int(edge_data['lanes'])
            except (ValueError, TypeError):
                pass
        
        # Try to get directional lanes
        if 'lanes:forward' in edge_data:
            try:
                lanes_forward = int(edge_data['lanes:forward'])
            except (ValueError, TypeError):
                pass
                
        if 'lanes:backward' in edge_data:
            try:
                lanes_backward = int(edge_data['lanes:backward'])
            except (ValueError, TypeError):
                pass
        
        # Estimate total if directional lanes are available
        if total_lanes is None and lanes_forward is not None and lanes_backward is not None:
            total_lanes = lanes_forward + lanes_backward
        
        # Estimate directional lanes if total is available and road is not oneway
        if total_lanes and not edge_data.get('oneway', False):
            if lanes_forward is None and lanes_backward is None:
                # Assume equal split for bidirectional roads
                lanes_forward = total_lanes // 2
                lanes_backward = total_lanes - lanes_forward
        
        return total_lanes, lanes_forward, lanes_backward
    
    def _parse_lane_markings(self, turn_lanes_tag: Optional[str]) -> List[LaneMarking]:
        """Parse turn:lanes tag into lane markings"""
        if not turn_lanes_tag:
            return []
        
        markings = []
        lanes = str(turn_lanes_tag).split('|')
        
        for lane in lanes:
            lane_moves = lane.strip().split(';')
            for move in lane_moves:
                move = move.strip().lower()
                
                # Map OSM turn lane values to our enum
                if move in ['through', 'straight']:
                    markings.append(LaneMarking.THROUGH)
                elif move == 'left':
                    markings.append(LaneMarking.LEFT)
                elif move == 'right':
                    markings.append(LaneMarking.RIGHT)
                elif move == 'slight_left':
                    markings.append(LaneMarking.SLIGHT_LEFT)
                elif move == 'slight_right':
                    markings.append(LaneMarking.SLIGHT_RIGHT)
                elif move == 'sharp_left':
                    markings.append(LaneMarking.SHARP_LEFT)
                elif move == 'sharp_right':
                    markings.append(LaneMarking.SHARP_RIGHT)
                elif move == 'reverse':
                    markings.append(LaneMarking.REVERSE)
                elif move == 'merge_to_left':
                    markings.append(LaneMarking.MERGE_TO_LEFT)
                elif move == 'merge_to_right':
                    markings.append(LaneMarking.MERGE_TO_RIGHT)
                elif move == 'none':
                    markings.append(LaneMarking.NONE)
                else:
                    markings.append(LaneMarking.UNKNOWN)
        
        return markings
    
    def _get_highway_type(self, highway_tag: str) -> Optional[HighwayType]:
        """Convert OSM highway tag to HighwayType enum, return None if not car-accessible"""
        highway_str = str(highway_tag).lower().strip()
        
        try:
            return HighwayType(highway_str)
        except ValueError:
            # Return None for non-car-accessible or unknown highway types
            return None
    
    def _extract_coordinates_and_geometry_type(self, edge_data: Dict, u_node: Dict, v_node: Dict) -> Tuple[List[Tuple[float, float]], GeometryType]:
        """Extract coordinates and determine geometry type from edge geometry"""
        if 'geometry' in edge_data and edge_data['geometry']:
            geom = edge_data['geometry']
            
            # Determine geometry type from actual geometry object
            if hasattr(geom, 'geom_type'):
                geom_type_str = geom.geom_type
                if geom_type_str == 'LineString':
                    geometry_type = GeometryType.LINESTRING
                elif geom_type_str == 'MultiLineString':
                    geometry_type = GeometryType.MULTILINESTRING
                elif geom_type_str == 'Point':
                    geometry_type = GeometryType.POINT
                else:
                    geometry_type = GeometryType.LINESTRING  # Default fallback
            else:
                geometry_type = GeometryType.LINESTRING  # Default fallback
            
            # Extract coordinates
            if hasattr(geom, 'coords'):
                coordinates = [(float(coord[0]), float(coord[1])) for coord in geom.coords]
            elif hasattr(geom, 'geoms'):  # MultiLineString case
                coordinates = []
                for line in geom.geoms:
                    if hasattr(line, 'coords'):
                        coordinates.extend([(float(coord[0]), float(coord[1])) for coord in line.coords])
            else:
                # Fallback to straight line between nodes
                u_coords = (float(u_node['x']), float(u_node['y']))
                v_coords = (float(v_node['x']), float(v_node['y']))
                coordinates = [u_coords, v_coords]
                geometry_type = GeometryType.LINESTRING
        else:
            # Fallback to straight line between nodes
            u_coords = (float(u_node['x']), float(u_node['y']))
            v_coords = (float(v_node['x']), float(v_node['y']))
            coordinates = [u_coords, v_coords]
            geometry_type = GeometryType.LINESTRING
        
        return coordinates, geometry_type
    
    def _get_lane_width(self, edge_data: Dict) -> Optional[float]:
        """Get lane width from OSM data only"""
        if 'width' in edge_data:
            try:
                total_width = float(edge_data['width'])
                # If we have lane count, calculate per-lane width
                if 'lanes' in edge_data:
                    lanes = int(edge_data['lanes'])
                    if lanes > 0:
                        return total_width / lanes
                return total_width
            except (ValueError, TypeError):
                pass
        return None
    
    def extract_road_features(self) -> bool:
        """Extract road features from the cached graph"""
        if not self.graph or len(self.graph.edges) == 0:
            print("No graph data available for road feature extraction")
            return False
        
        print(f"Extracting road features from {len(self.graph.edges)} edges...")
        
        extracted_count = 0

        for u, v, key, edge_data in self.graph.edges(keys=True, data=True):
            try:
                # Get node data
                u_node = self.graph.nodes[u]
                v_node = self.graph.nodes[v]
                
                # Basic edge information
                edge_id = f"{u}_{v}_{key}"
                highway_type = self._get_highway_type(edge_data.get('highway', 'unknown'))
                
                # Skip non-car-accessible highway types
                if highway_type is None:
                    continue
                
                # Speed limit - only from OSM data
                speed_limit = self._parse_speed_limit(edge_data.get('maxspeed'))
                
                # Lane information
                total_lanes, lanes_forward, lanes_backward = self._parse_lane_count(edge_data)
                
                # Lane markings
                lane_markings_forward = self._parse_lane_markings(edge_data.get('turn:lanes:forward'))
                lane_markings_backward = self._parse_lane_markings(edge_data.get('turn:lanes:backward'))
                
                # Lane width
                lane_width = self._get_lane_width(edge_data)
                
                # Geometry and coordinates
                coordinates, geometry_type = self._extract_coordinates_and_geometry_type(edge_data, u_node, v_node)
                
                # Additional attributes
                oneway = edge_data.get('oneway', False)
                if isinstance(oneway, str):
                    oneway = oneway.lower() in ['yes', 'true', '1']
                
                # Create RoadFeature object
                road_feature = RoadFeature(
                    node_from=u,
                    node_to=v,
                    key=key,
                    edge_id=edge_id,
                    highway_type=highway_type,
                    speed_limit=speed_limit,
                    total_lanes=total_lanes,
                    lanes_forward=lanes_forward,
                    lanes_backward=lanes_backward,
                    lane_width=lane_width,
                    lane_markings_forward=lane_markings_forward,
                    lane_markings_backward=lane_markings_backward,
                    turn_lanes_forward=edge_data.get('turn:lanes:forward'),
                    turn_lanes_backward=edge_data.get('turn:lanes:backward'),
                    coordinates=coordinates,
                    geometry_type=geometry_type,
                    name=edge_data.get('name'),
                    oneway=oneway,
                    extraction_timestamp=self.extraction_timestamp
                )
                
                self.road_features.append(road_feature)
                extracted_count += 1
                
            except Exception as e:
                print(f"Error processing edge {u}-{v}-{key}: {e}")
                continue
        
        print(f"Successfully extracted {extracted_count} road features")
        return extracted_count > 0
    
    def _save_to_database(self) -> Dict[str, int]:
        network_coll = mongo.db.network_primary #type:ignore

        """Save extracted road features to MongoDB using BaseExporter format"""
        if not self.road_features:
            return {"inserted": 0, "errors": 0}
        
        print("Saving road features to database...")
        
        try:
            # Create collection for road features
            road_coll = mongo.db.road_features #type:ignore
            net_coll = mongo.db.network_primary #type:ignore

            print(f"Database collection created successfully {road_coll}")

            # Create index for efficient queries
            road_coll.create_index([("edge_id", 1)], unique=True, background=True)
            road_coll.create_index([("highway_type", 1), ("extraction_timestamp", -1)], background=True)
            
            # Prepare bulk operations
            operations = []
            operations_net = []

            for rf in self.road_features:
                try:
                    # Create feature_dict following the same structure as BaseExporter
                    feature_dict = {
                        "edge_id": rf.edge_id,
                        "type": "Feature",
                        "geometry": {
                            "type": rf.geometry_type.value,
                            "coordinates": rf.coordinates
                        },
                        "properties": {
                            "feature_type": "road_segment",
                            "node_from": rf.node_from,
                            "node_to": rf.node_to,
                            "highway_type": rf.highway_type.value,
                            "speed_limit": rf.speed_limit,
                            "total_lanes": rf.total_lanes,
                            "lanes_forward": rf.lanes_forward,
                            "lanes_backward": rf.lanes_backward,
                            "lane_width": rf.lane_width,
                            "name": rf.name,
                            "oneway": rf.oneway,
                            "lane_markings_forward": [m.value for m in rf.lane_markings_forward],
                            "lane_markings_backward": [m.value for m in rf.lane_markings_backward],
                            "turn_lanes_forward": rf.turn_lanes_forward,
                            "turn_lanes_backward": rf.turn_lanes_backward,
                            "is_major_road": rf.is_major_road(),
                            "extraction_timestamp": rf.extraction_timestamp
                        }
                    }
                    
                    exporter = BaseExporter(
                        type = 'Feature',
                        geometry=feature_dict['geometry'],
                        properties=feature_dict['properties']
                    )
                    doc = exporter.model_dump(serialize_as_any=True)
                    doc ['geometry'] = mapping(doc['geometry'])
                    
                    ordered_doc = {
                        'edge_id': rf.edge_id,
                        'type': doc['type'],
                        'geometry': doc['geometry'],
                        'properties': doc['properties']
                    }
                    
                    operations.append(
                        UpdateOne(
                            {'edge_id': rf.edge_id},
                            {'$set': ordered_doc},
                            upsert=True
                        )
                    )

                    operations_net.append(
                        UpdateOne(
                            {'_id': rf.edge_id},
                            {'$set': ordered_doc},
                            upsert=True
                        )
                    )


                    
                except ValidationError as e:
                    print(f"Validation failed for road feature {rf.edge_id}: {e}")
                    continue
            
            
            # Execute bulk write
            result = road_coll.bulk_write(operations, ordered=False)
            net_coll.bulk_write(operations_net, ordered=False)
            
            print(f"Database save complete: {result.upserted_count} new, {result.matched_count} updated")
            
            return {
                "inserted": result.upserted_count,
                "updated": result.matched_count,
                "errors": 0
            }
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            return {"inserted": 0, "updated": 0, "errors": len(self.road_features)}
    
    def generate_road_feature_data(self) -> Dict[str, Any]:
        """Execute the full road feature extraction workflow"""
        try:
            # Extract features from graph
            if not self.extract_road_features():
                return {"result": [], "status_code": 404, "message": "No road features extracted"}
            
            # Save to database
            db_result = self._save_to_database()
            
            # Create exportable features following the same pattern as BaseExporter
            export_features = []

            for rf in self.road_features:
                try:
                    # Create feature_dict following the same structure as BaseExporter
                    feature_dict = {
                        "edge_id": rf.edge_id,
                        "type": "Feature",
                        "geometry": {
                            "type": rf.geometry_type.value,
                            "coordinates": rf.coordinates
                        },
                        "properties": {
                            "feature_type": "road_segment",
                            "node_from": rf.node_from,
                            "node_to": rf.node_to,
                            "highway_type": rf.highway_type.value,
                            "speed_limit": rf.speed_limit,
                            "total_lanes": rf.total_lanes,
                            "lanes_forward": rf.lanes_forward,
                            "lanes_backward": rf.lanes_backward,
                            "lane_width": rf.lane_width,
                            "name": rf.name,
                            "oneway": rf.oneway,
                            "lane_markings_forward": [m.value for m in rf.lane_markings_forward],
                            "lane_markings_backward": [m.value for m in rf.lane_markings_backward],
                            "turn_lanes_forward": rf.turn_lanes_forward,
                            "turn_lanes_backward": rf.turn_lanes_backward,
                            "is_major_road": rf.is_major_road(),
                            "extraction_timestamp": rf.extraction_timestamp
                        }
                    }
                    
                    # Validate using BaseExporter model
                    validated_feature = BaseExporter.model_validate(feature_dict)
                    export_features.append(validated_feature.model_dump(mode="json"))
                except ValidationError as e:
                    print(f"Validation failed for road feature {rf.edge_id}: {e}")
                    continue
            
            return {
                "result": export_features,
                "status_code": 200,
                "database": db_result,
                "extraction_metadata": {
                    "timestamp": self.extraction_timestamp,
                    "total_features": len(self.road_features),
                    "graph_nodes": len(self.graph.nodes),
                    "graph_edges": len(self.graph.edges)
                }
            }
            
        except Exception as e:
            print(f"Error in road feature extraction: {e}")
            return {
                "result": [],
                "status_code": 500,
                "error": str(e),
                "timestamp": self.extraction_timestamp
            }


# Flask Blueprint
road_feature_bp = Blueprint('road_feature_bp', __name__, url_prefix='/road_features')

@road_feature_bp.route('/', methods=['POST'], strict_slashes=False)
def extract_road_features_endpoint():
    """
    API endpoint to extract road features from cached graph data.
    Uses the RoadFeatureExtractor service to analyze the network.
    """
    # Check for cached request object
    req_obj = local_cache.get('request')
    if not isinstance(req_obj, WebRequest):
        return jsonify(error="Request context not found in cache. Please run a query first."), 400
    
    # Check for cached graph
    G = local_cache.get('graph')
    if G is None:
        return jsonify(error="Graph not found in cache. Please run a query first."), 400
    
    # Create extractor
    extractor = RoadFeatureExtractor(graph=G)
    
    # Execute extraction
    api_response = extractor.generate_road_feature_data()
    
    # feature map
    highway_type_dict = Feature('highway_type', Feature.enum_values(HighwayType))
    lane_markings_dict = Feature('lane_markings', Feature.enum_values(LaneMarking))
    oneway_dict = Feature('oneway', [True, False])
    is_major_road_dict = Feature('is_major_road', [True, False])
    speed_limit_dict = Feature('speed_limit', [])
    lane_width = Feature('lane_width', [])

    feature_map = FeatureDict()
    feature_map.add_feature_type('road_segment', [highway_type_dict, lane_markings_dict, speed_limit_dict, oneway_dict, is_major_road_dict, lane_width])
    
    return jsonify({'results': api_response['result'], 'feature_dict': feature_map.out()}), api_response['status_code']


@road_feature_bp.route('/filter', methods=['POST'])
def filter_road_features_endpoint():
    """Filter road features by various criteria"""
    try:
        from flask import request
        
        filters = request.get_json() or {}
        road_coll = mongo.db.road_features #type:ignore
        
        # Build query from filters
        query = {}
        
        if 'highway_types' in filters:
            query['highway_type'] = {'$in': filters['highway_types']}
        
        if 'min_speed_limit' in filters:
            query['speed_limit'] = {'$gte': filters['min_speed_limit']}
        
        if 'max_speed_limit' in filters:
            query.setdefault('speed_limit', {})['$lte'] = filters['max_speed_limit']
        
        if 'min_lanes' in filters:
            query['total_lanes'] = {'$gte': filters['min_lanes']}
        
        if 'oneway_only' in filters and filters['oneway_only']:
            query['oneway'] = True
        
        if 'major_roads_only' in filters and filters['major_roads_only']:
            major_types = ['motorway', 'motorway_link', 'primary', 'primary_link', 'secondary', 'secondary_link']
            query['highway_type'] = {'$in': major_types}
        
        # Execute query
        results = list(road_coll.find(query).limit(1000))  # Limit results
        
        # Remove MongoDB _id fields
        for result in results:
            result.pop('_id', None)
        
        return jsonify({
            "results": results,
            "count": len(results),
            "query": query
        }), 200
        
    except Exception as e:
        return jsonify(error=f"Error filtering features: {str(e)}"), 500