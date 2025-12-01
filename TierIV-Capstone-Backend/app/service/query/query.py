import osmnx as ox
from osmnx import settings as ox_settings
import geopandas as gpd
import networkx as nx
from typing import Optional, List, Union
from pydantic import ValidationError
from flask import Blueprint, request, jsonify
from shapely import LineString
import re
import numpy as np
from scipy.spatial import KDTree

from app import local_cache, mongo
from app.models import WebRequest
from .query_models import MapLocation
from app.service.junction.junction_analysis import _convert_to_meters


query_bp = Blueprint('query_bp', __name__)

def configure_osmnx():
    '''
    Appends our extra way-tags if they're not already present for enriched metadata

    Note: See `osmnx.settings` module documentation for details on default settings
    '''
    
    G_add_useful_tags_way = ['lanes:forward', 'lanes:backward', 'turn:lanes:forward', 'turn:lanes:backward', 'surface', 'access', 'layer', 'lit']

    for t in G_add_useful_tags_way:
        if t not in ox_settings.useful_tags_way:
            ox_settings.useful_tags_way.append(t)
    

@query_bp.route('/query', methods=['POST'])
def query_config_endpoint():
    '''
    Main route for query and configuration
    - Parse initial request, default model settings, predefined configuration to Central Request Object
    - Query from OSM
        - Full graph: MultiDirectedGraph retaining all neighboring nodes within the queried boundary (with truncate_by_edge=True)
        - List of core nodes: List of node_ids mapped to matching nodes by coordiantes using KD-tree (with truncate_by_edge=False)
        - GeoDataFrame: Feature data frame
    
    - Locally cached objects:
        - `request`: Central Request Object
        - `graph`: Full graph
        - `graph_core_nodes`: List of core nodes
        - `gdf`: Feature GeoDataFrame

        Supplementary cache for utility
        - `query_key`: compression string for detecting identical query (last vs. current) 
    '''
    # parse request and validate
    raw = request.get_json()

    try:
        req_obj = WebRequest(**raw)
    except ValidationError as e:
        return jsonify(error=e.errors()), 400
    
    # store request object in local cache
    local_cache.set('request', req_obj)

    # check cache keys
    query_key = local_cache.get('query_key')
    query_key2 = req_obj.query_key()

    new_query = False
    core_nodes = None
    G = None
    if query_key2 != query_key:
        new_query = True
        local_cache.set('query_key', query_key2)

    if new_query:
        # get queried graph
        if local_cache.get('graph') is None:
            configure_osmnx()

        G = get_graph(
            MapLocation[req_obj.input_type],
            req_obj.input,
            dist=req_obj.dist,
            truncate_by_edge=True
        )
        configure_graph(G, req_obj.lane_width)
        local_cache.set('graph', G)

        # get core list of nodes
        G_core = get_graph(
            MapLocation[req_obj.input_type],
            req_obj.input,
            dist=req_obj.dist,
            truncate_by_edge=False
        )

        # match core nodes by coordinates in full graph
        full_nodes = list(G.nodes)
        full_coords = np.array([(G.nodes[n]['x'], G.nodes[n]['y']) for n in full_nodes])

        # KD tree to find nearest neighbor (preventing potential slight mistach of coordinates)
        tree = KDTree(full_coords)

        # find the nearest neighbor with degree of tolerance
        mapped_core_nodes = []
        tol = 1e-5      # degree of tolerance
        for n_core, data_core in G_core.nodes(data=True):
            pt = np.array([data_core['x'], data_core['y']])
            dist, idx = tree.query(pt)
            if dist > tol:
                continue
            mapped_core_nodes.append(full_nodes[idx])

        # cache core nodes ids
        core_nodes = mapped_core_nodes
        local_cache.set('graph_core_nodes', core_nodes)

        # get feature data frame
        GDF = get_features(
            MapLocation[req_obj.input_type],
            req_obj.input,
            tags={'amenity': True, 'access': True, 'foot': True, 'pedestrian': True, 'highway': 'traffic_signals'},
            dist=req_obj.dist,
        )
        local_cache.set('gdf', GDF)
    else:
        # Retrieve core_nodes from cache if not a new query
        G = local_cache.get('graph')
        # PENDING
        core_nodes = local_cache.get('graph_core_nodes')

        # drop existing network collections
    mongo.db.network_primary.drop() #type:ignore
    mongo.db.network_feature.drop() #type:ignore

    response = {'message': 'Request and query successful.',
                'input_type': req_obj.input_type,
                'input': req_obj.input,
                'dist': req_obj.dist,
                'n_nodes': len(core_nodes) if core_nodes is not None else 0,
                'n_edges': len(G.edges) if G is not None else 0,
                }
    return jsonify(response), 200
    
    
def get_graph (input_type: MapLocation, input,
               dist: float=10000.0, network_type: str='drive', 
               truncate_by_edge: bool=True, retain_all=True, 
               custom_filter: Optional[Union[str, List[str]]] = None) -> nx.MultiDiGraph:
    '''
    `input type`: Location enums (bbox, point, address, place)

    `input`: data format for each input type:
        `bbox`:     coordinates(min_lon, min_lat, max_lon, max_lat)
        `point`:    center_point(lat, lon)
        `address`:  str(e.g., 市役所前, 高原通り, Daimon-nanabancho, Shiojiri, Nagano Prefecture, 399-0737, Japan)
        `place`:    str(e.g., Shiojiri, Nagano Prefecture, Japan) - return top search result

    Default params:
        `distance`:     10000 (10KM)    - distance from the center to the bounding box
        `network_type`: drive           - type of street network

    Connectivity:  
        `truncate_by_edge`:    `True`  - include immediate neighboring nodes outside of bbox
        `retain_all`:           `False` - retain only the largest weakly connected components
    
    `custom filter`: search elements instead of using the specification in `network_type`
        e.g., 
        `["highway"~"motorway|motorway_link|trunk|trunk_link"]`
        `['[maxspeed=50]', '[lanes=2]']`
    '''

    if input_type == MapLocation.BBOX:
        return ox.graph_from_bbox(input, network_type=network_type, truncate_by_edge=truncate_by_edge, retain_all=retain_all, custom_filter=custom_filter)
    elif input_type == MapLocation.POINT:
        return ox.graph_from_point(input, dist, network_type=network_type, truncate_by_edge=truncate_by_edge, retain_all=retain_all, custom_filter=custom_filter)
    elif input_type == MapLocation.ADDRESS:
        return ox.graph_from_address(input, dist, network_type=network_type, truncate_by_edge=truncate_by_edge, retain_all=retain_all, custom_filter=custom_filter)
    elif input_type == MapLocation.PLACE:
        return ox.graph_from_place(input, network_type=network_type, truncate_by_edge=truncate_by_edge, retain_all=retain_all, custom_filter=custom_filter)
    else:
        raise ValueError(f"Unsupported input_type: {input_type}")
    

def configure_graph (G: nx.MultiDiGraph, default_lane_width: float):
    '''
    Fill in missing geom for edges: Assume & add straight-line `LineString` for edges without 'geometry' attribute
    '''
    # Fill in proprietary data (PENDING)

    # Fill in missing attributes with default settings
    for u, v, key, data in G.edges(keys=True, data=True):
        if 'geometry' not in data:
            x0, y0 = G.nodes[u]['x'], G.nodes[u]['y']
            x1, y1 = G.nodes[v]['x'], G.nodes[v]['y']
            data['geometry'] = LineString([(x0, y0), (x1, y1)])
        
        # normalize widths
        for width_attr in ['width', 'est_width']:
            if width_attr in data:
                data[width_attr] = _convert_to_meters(data[width_attr])






def get_features (input_type: MapLocation, input,
                  tags: dict[str, bool | str | list[str]], dist: float=10000) -> gpd.GeoDataFrame:
    '''
    `input_type`:  (bbox, point, address, place)

    `input`: data format for each input type:
        `bbox`:     coordinates(left, bottom, right, top)
        `point`:    center_point(lat, lon)
        `address`:  str(e.g., 市役所前, 高原通り, Daimon-nanabancho, Shiojiri, Nagano Prefecture, 399-0737, Japan)
        `place`:    str(e.g., Shiojiri, Nagano Prefecture, Japan) - return top search result

    Default params:
        `distance`: 10000 (10KM)    - distance from the center to the bounding box
    
    `tags':         search elements
        e.g.,
        `{'building': True}`
        `{'amenity':True, 'landuse':['retail','commercial'], 'highway':'bus_stop'}`
    '''

    if input_type == MapLocation.BBOX:
        return ox.features_from_bbox(input, tags)
    elif input_type == MapLocation.POINT:
        return ox.features_from_point(input, tags, dist)
    elif input_type == MapLocation.ADDRESS:
        return ox.features_from_address(input, tags, dist)
    elif input_type == MapLocation.PLACE:
        return ox.features_from_place(input, tags)
    else:
        raise ValueError(f"Unsupported input_type: {input_type}")


# def sample_usage():
#     shiojiri_bbox = (137.94225, 36.10779, 137.96753, 36.12129)
#     print(f'Showing sample area: Shiojiri {str(shiojiri_bbox)}')
#     G = get_graph(MapLocation.BBOX, shiojiri_bbox)
#     fig, ax = plt.subplots(figsize=(8, 8))
#     ox.plot_graph(G, node_size=15, edge_color='blue', node_color='red', ax=ax, show=True)


# if __name__ == "__main__":
#     print("Sample usage:")
#     sample_usage()