from collections import defaultdict
import numpy as np
from shapely.strtree import STRtree
from shapely.geometry import Point, LineString
import osmnx as ox
import networkx as nx


def build_edge_tree(G):
    '''
    Build STRtree for graph for fast spatial queries
    '''
    edge_map = {}
    geometries = []

    for u, v, k, data in G.edges(keys=True, data=True):
        geom = data.get('geometry')
        if geom:
            edge_id = (u, v, k)
            edge_map[id(geom)] = edge_id
            geometries.append(geom)

    tree = STRtree(geometries)
    return tree, edge_map


def match_snapshots_to_edges(snapshots, tree, edge_map):
    '''
    Use the ego location from each snapshots in proprietary data to find the nearest geometry using STRtree
    '''
    match_index = {}
    
    for i, snap in enumerate(snapshots):
        ego = snap.get('ego location', {})
        pt = Point(ego['x'], ego['y'])
        
        nearest_geom = tree.nearest(pt)
        edge_id = edge_map.get(id(nearest_geom))
        if edge_id:
            match_index[i] = edge_id

    return match_index


def preprocess_proprietary_edge_data(proprietary_snapshots, match_index, method='average'):
    '''
    Aggregate proprietary snapshots and add to the matching edge
    '''

    # each edge's list of feature dicts
    edge_data = defaultdict(lambda: defaultdict(list))

    for i, snapshot in enumerate(proprietary_snapshots):
        edge_id = match_index.get(i)
        if edge_id is None:
            continue

        for k, v in snapshot.items():
            if isinstance(v, (int, float)):
                edge_data[edge_id][k].append(v)

    # aggregate snapshots by OSM edge
    aggregated = {}
    for edge_id, features in edge_data.items():
        aggregated[edge_id] = {}
        for k, vals in features.items():
            if not vals:
                continue
            if method == 'min':
                aggregated[edge_id][k] = min(vals)
            elif method == 'max':
                aggregated[edge_id][k] = max(vals)
            elif method == 'average':
                aggregated[edge_id][k] = float(np.mean(vals))

    return aggregated



def configure_graph_mock(G: nx.MultiDiGraph, default_lane_width: float, proprietary_aggregates=None):
    '''
    [SAMPLE FUNCTION - PENDING FURTHER EXPLORATION]
    Configure each edge with default attributes and proprietary data
    '''
    from app.service.junction.junction_analysis import _convert_to_meters

    for u, v, key, data in G.edges(keys=True, data=True):
        if 'geometry' not in data:
            x0, y0 = G.nodes[u]['x'], G.nodes[u]['y']
            x1, y1 = G.nodes[v]['x'], G.nodes[v]['y']
            data['geometry'] = LineString([(x0, y0), (x1, y1)])

        # normalize widths
        for width_attr in ['width', 'est_width']:
            if width_attr in data:
                data[width_attr] = _convert_to_meters(data[width_attr])

        # inject proprietary features
        edge_key = (u, v, key)
        if proprietary_aggregates and edge_key in proprietary_aggregates:
            for feat_key, feat_val in proprietary_aggregates[edge_key].items():
                data[feat_key] = feat_val


# Sample usage
# # After G is queried
# tree, edge_map = build_edge_tree(G)
# match_index = match_snapshots_to_edges(proprietary_snapshots, tree, edge_map)
# aggregated_edge_data = preprocess_proprietary_edge_data(proprietary_snapshots, match_index, method="average")
# configure_graph(G, req_obj.lane_width, proprietary_aggregates=aggregated_edge_data)