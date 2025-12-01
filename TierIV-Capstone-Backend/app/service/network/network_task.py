from flask import Blueprint, jsonify, request
from app import mongo, local_cache
from app.models import WebRequest, BaseExporter
from app.service.junction.junction_models import JuncConflict


from shapely.geometry import mapping, shape, LineString, MultiLineString
from shapely.ops import linemerge

from collections import Counter
import itertools
import networkx as nx
from tqdm import tqdm


network_bp = Blueprint('network_bp', __name__)

@network_bp.route('/network', methods=['POST'])
def network_main():
    '''
    Main route for odd compliant network analysis output
    '''
    resp = network_odd_compliance()
    if resp is None:
        return jsonify({'message': 'No odd compliant network'}), 200

    return jsonify(resp), 200

    

def network_odd_compliance():
    '''
    Aggregate odd compliance network check
    - Request passed when `/network` route is called contains
        - Options for odd definitions:
            - all: no odd compliance check
            - predefined: use list of predefined elements in excel as odd
            - live: use in-session toggled elements at the frontend as odd
        - ODD data structure:
            - attribute (e.g., 'junction_type') -> list of elements(e.g., ['ROUNDABOUT', 'CROSSROAD'])
    - Construct list of incompliant nodes based on documents in `network_feature` collection, analysis conducted by feature type
    - Construct list of compliant edge geometries, cross-validate with incompliant nodes
        - Edge compliance criteria:
            - Neither side of the edge has match in list of incompliant nodes
            - Edge metadata is compliant of current ODD definitions
    - Find the longest connected ODD-compliant network

    Return: single LineString representing the longest connected ODD-compliant road network
    '''
    req = request.get_json()
    
    req_obj = local_cache.get('request')
    if not isinstance(req_obj, WebRequest):
        raise

    # define collections
    coll_primary = mongo.db.network_primary #type:ignore
    coll_feature = mongo.db.network_feature #type:ignore

    incompliant_nodes = set()
    compliant_geom = []

    # get requested odd type
    odd_type = req.get('odd_type', 'all').lower()
    odd = (
        req_obj.odd if odd_type == 'predefined' else
        req.get('odd_param') if odd_type == 'live' else
        None
    )

    print(odd)

    if odd is None:
        compliant_geom = [shape(doc['geometry']) for doc in coll_primary.find()]

    else:
        incompliant_nodes = set()
        compliant_geom = []

        features = list(coll_feature.find())
        primary_docs = list(coll_primary.find())

        def normalize_bool_list(lst):
            return [x if isinstance(x, str) else bool(x) for x in lst]

        # Only get boolean filters if they're explicitly in the request
        # If not present, set to None to skip filtering
        odd_school_zone = normalize_bool_list(odd.get('school_zone')) if 'school_zone' in odd else None
        odd_parking_lot = normalize_bool_list(odd.get('parking_lot')) if 'parking_lot' in odd else None
        odd_traffic_signals = normalize_bool_list(odd.get('traffic_signals')) if 'traffic_signals' in odd else None

        for doc in features:
            for f in doc['features']:
                # school zone filtering
                if f['feature_type'] == 'school_zone' and odd_school_zone is not None:
                    # If user selected True (wants school zones), don't filter out school zones
                    # If user selected False (doesn't want school zones), filter them out
                    if True not in odd_school_zone:
                        incompliant_nodes.add(doc['_id'])
                        continue

                # parking lot filtering
                if f['feature_type'] == 'parking_lot' and odd_parking_lot is not None:
                    # If user selected True (wants parking lots), don't filter out parking lots
                    # If user selected False (doesn't want parking lots), filter them out
                    if True not in odd_parking_lot:
                        incompliant_nodes.add(doc['_id'])
                        continue

                # traffic signals filtering
                if f['feature_type'] == 'traffic_signals' and odd_traffic_signals is not None:
                    # If user selected True (wants traffic signals), don't filter out traffic signals
                    # If user selected False (doesn't want traffic signals), filter them out
                    if True not in odd_traffic_signals:
                        incompliant_nodes.add(doc['_id'])
                        continue

                # junction
                elif f['feature_type'] == 'junction':
                    metadata = f.get('metadata')
                    if not metadata or check_single_junction_odd_incompliance(odd, metadata):
                        incompliant_nodes.add(doc['_id'])


        for doc in primary_docs:
            metadata = doc['properties']['metadata']
            nodes = list(map(int, doc['_id'].split('_')[:2]))

            # Check if any node is compliant
            if all(node_id not in incompliant_nodes for node_id in nodes):
                if check_single_edge_odd_compliance(odd, metadata):
                    compliant_geom.append(shape(doc['geometry']))

    return get_longest_network(compliant_geom)



def get_longest_network(compliant_geom: list) -> dict | None:
    lines = [geom for geom in compliant_geom if isinstance(geom, LineString)]
    if not lines:
        return None

    # build new graph
    G = nx.Graph()
    for line in lines:
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            G.add_edge(coords[i], coords[i + 1], line=line)

    # find connected components and their total path length
    longest_subgraph = max(
        (G.subgraph(c).copy() for c in nx.connected_components(G)),
        key=lambda sg: sum(LineString([u, v]).length for u, v in sg.edges)
    )

    # reconstruct the geometry from the longest component
    lines_out = [LineString([u, v]) for u, v in longest_subgraph.edges]
    if lines_out:
        # Return a proper GeoJSON Feature, not just the geometry
        return {
            "type": "Feature",
            "geometry": mapping(MultiLineString(lines_out)),
            "properties": {}
        }

    return None



def check_single_junction_odd_incompliance(odd: dict, metadata: dict) -> bool:
    '''
    Check a single node's ODD compliance
    '''
    # determine odd compliance
    odd_junction_types = odd.get('junction_type', ['ALL'])
    odd_junction_conflicts = odd.get('junction_conflict', ['ALL'])

    junction_type = metadata.get('junc_type')
    conflict_counter_str = metadata.get('conflict_counter', {})
    conflict_counter = Counter({JuncConflict[name]: count for name, count in conflict_counter_str.items()})

    if 'ALL' not in odd_junction_types:
        if junction_type is None or junction_type not in odd_junction_types:
            return True
    if 'ALL' not in odd_junction_conflicts:
        for conflict_name in conflict_counter:
            if conflict_counter[conflict_name] and (conflict_name not in odd_junction_conflicts):
                return True

    return False


def check_single_edge_odd_compliance(odd: dict, metadata: dict) -> bool:
    '''
    Check a single edge's ODD compliance
    '''
    # compliance checks
    compliance_rules = [
        ('highway_type', 'highway_type', odd.get('highway_type', 'ALL')),
        ('lane_markings_forward', 'lane_markings', odd.get('lane_markings', 'ALL'))
    ]

    for meta_key, _, odd_value in compliance_rules:
        value = metadata.get(meta_key)
        if isinstance(odd_value, (list, set)) and odd_value:
            if 'ALL' not in odd_value and (value is None or value not in odd_value):
                return False
        elif odd_value != 'ALL' and value != odd_value:
            return False

    # boolean flags
    oneway_odd = odd.get('oneway', True)
    if isinstance(oneway_odd, list) and len(oneway_odd) > 0:
        oneway_odd = oneway_odd[0]
    
    if not oneway_odd and not metadata.get('oneway'):
        return False

    major_road_odd = odd.get('is_major_road', True)
    if isinstance(major_road_odd, list) and len(major_road_odd) > 0:
        major_road_odd = major_road_odd[0]

    if not major_road_odd and not metadata.get('is_major_road'):
        return False


    # helper to get minimum numeric value from mixed types
    def get_min_numeric(source, key, fallback=None):
        val = source.get(key, fallback)
        
        def to_float(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return None

        if isinstance(val, (list, tuple)):
            numeric_vals = [to_float(v) for v in val]
            numeric_vals = [v for v in numeric_vals if v is not None]
            if numeric_vals:
                return min(numeric_vals)
            return None

        numeric_val = to_float(val)
        return numeric_val if numeric_val is not None else None


    # resolve minimum values for comparison
    # Notes: defaults for ODD criteria may be adjusted based on user tolerance of missing data
    min_speed_limit = get_min_numeric(metadata, 'speed_limit', 999)
    odd_speed_limit = get_min_numeric(odd, 'speed_limit')

    min_lane_width = get_min_numeric(metadata, 'lane_width', 0)
    odd_lane_width = get_min_numeric(odd, 'lane_width')


    # compliance checks
    if min_speed_limit is not None and odd_speed_limit is not None:
        if min_speed_limit > odd_speed_limit:
            return False

    if min_lane_width is not None and odd_lane_width is not None:
        if min_lane_width < odd_lane_width:
            return False

    return True

