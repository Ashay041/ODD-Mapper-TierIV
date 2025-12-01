from flask import Blueprint, jsonify
from app import mongo, local_cache
from app.models import WebRequest, BaseExporter, Feature, FeatureDict
from .junction_analysis import *
from shapely.geometry import mapping
from pymongo import UpdateOne, ReplaceOne

from collections import Counter
import itertools
import networkx as nx
from tqdm import tqdm


junction_bp = Blueprint('junction_bp', __name__)

@junction_bp.route('/junction', methods=['POST'])
def junction_main():
    return jsonify(analyze_all_nodes()), 200


def analyze_all_nodes():
    '''
    Run analysis for all nodes
    - Retrieve request, full graph, and list of core nodes from local cache
    - Append geometry and extracted feature metadata to list of results
    - Cross check & Bulk write to NoSQL database
        - mongo.db.junction: Saved past analyzed results (optional to overwrite by passing initial request 'overwrite=True'), unique key by coordinates
        - mongo.db.network_feature: For the current query request, outputed metadata for odd compliant network validation, unique by node id, appendable across features
    - Construct `feature_dict` listing all feature attributes and their elements related to ODD compliance check

    Return: list of results, feature dictionary
    '''
    # get parameters
    req_obj = local_cache.get('request')
    if not isinstance(req_obj, WebRequest):
        raise TypeError('Request parsing error')

    ## DEBUG
    # print(req_obj) ##

    # fetch cache
    G = local_cache.get('graph')
    core_nodes = local_cache.get('graph_core_nodes')

    ## DEBUG
    # print(
    #     'number of all nodes: ', len(G.nodes),
    #     '\nnumber of core nodes: ', len(core_nodes)
    # ) ##

    # run task
    all_results = []
    nodes = core_nodes
    ops_junc = []
    ops_net = []

    for node_id in tqdm(nodes, desc='Processing nodes for junction analysis', total=len(nodes)):
        ## DEBUG
        # print(node_id) ##

        doc = analyze_node(
            G=G, node_id=node_id, overwrite=req_obj.overwrite,
            junc_right_hand_traffic=req_obj.junc_right_hand_traffic,
            junc_ty_angle_threshold=req_obj.junc_ty_angle_threshold,
            junc_nbr_pos_threshold=req_obj.junc_nbr_pos_threshold,
            junc_trim_dist=req_obj.junc_trim_dist,
            junc_conflict_classifier=req_obj.junc_conflict_classifier,
            lane_width=req_obj.lane_width,
            odd=req_obj.odd,
            ops_junc = ops_junc, ops_net=ops_net
        )
        if doc is not None:
            all_results.append(doc)
    
        
    # bulk write
    coll = mongo.db.junction #type:ignore
    net_coll = mongo.db.network_feature #type:ignore
    if ops_junc:
        print('Bulk save to database: junction collection')
        coll.bulk_write(ops_junc)
    if ops_net:
        print('Builk save to database: feature collection')
        net_coll.bulk_write(ops_net)


    # feature map
    junction_type_dict = Feature('junction_type', Feature.enum_values(JunctionType))
    junction_conflict_dict = Feature('junction_conflict', Feature.enum_values(JuncConflict))
    feature_dict = FeatureDict()
    feature_dict.add_feature_type('junction', [junction_type_dict, junction_conflict_dict])
    
    
    # return
    return {
        'results': all_results,
        'feature_dict': feature_dict.out(),
    }


def analyze_node(G: nx.MultiDiGraph, node_id: int, overwrite: bool, 
                 junc_right_hand_traffic: bool,
                 junc_ty_angle_threshold: float,
                 junc_nbr_pos_threshold: float,
                 junc_trim_dist: float,
                 junc_conflict_classifier: list[dict],
                 lane_width: float,
                 odd: dict,
                 ops_junc: list,
                 ops_net:list):
    '''
    Single node analysis
    - Classify node by junction type
    - Construct counter for possible conflicts at node
    - Generate geometric corridor for node by uniting segments of neighboring edges
    
    Return: single document for node geometry and properties
    '''

    ## DEBUG
    # print(coll)
    # print(net_coll) ##

    # retrieve coordinates
    coords = (G.nodes[node_id]['x'], G.nodes[node_id]['y'])
    id = {'x': coords[0], 'y': coords[1]}

    # check if node already exist in database
    coll = mongo.db.junction #type:ignore

    # find past identical analysis from junction collection
    saved = coll.find_one({'_id': id})

    if not overwrite and saved is not None:
        doc             = saved

    else:
        # junction classification
        jt = (
            classify_edge_tag(G, node_id)
            or classify_node_tag(G, node_id)
            or classify_node_other(G, node_id, junc_ty_angle_threshold)
        )
        if jt is None:
            return None
        junction_type = jt.name

        ## DEBUG
        # print(junction_type) ##

        # build corridors
        lines, polygon = get_node_corridors(G, node_id, junc_trim_dist, lane_width)

        ## DEBUG
        # print(polygon) ##
        
        ## conflict counting   
        ctr = Counter()
        legs = get_legs(G, node_id)
        for leg1, leg2 in itertools.combinations(legs, 2):
            count_pair_interaction(G, node_id, 
                                leg1, leg2, 
                                ctr, 
                                junc_conflict_classifier, 
                                junc_nbr_pos_threshold, 
                                junc_right_hand_traffic)
    
        # flatten enum keys to names
        conflict_counter = {c.name: n for c, n in ctr.items()}

        # prepare document
        properties = {
            'feature_type': 'junction',
            'node_coords':  coords,
            'junc_type':    junction_type,
            'conflict_counter': conflict_counter,
        }

        feature_dict = {
            'type': 'Feature',
            'geometry': mapping(polygon),
            'properties': properties,
        }

        
        validated_dict = BaseExporter.model_validate(feature_dict)
        doc = validated_dict.model_dump(mode="json")

        # update into MongoDB
        ops_junc.append(ReplaceOne({'_id': id}, doc, upsert=True))

    # output to network analysis for the current central request
    ops_net.append(
        UpdateOne(
            {'_id': node_id},
            {'$addToSet': {'features': doc.get('properties')}},
            upsert=True
        )
    )

    return doc


# For checking status of async operations
# @junction_bp.route('/status', methods=['GET'])
# def check_status():
#     '''
#     Front-end can poll this endpoint with ?group_id=<UUID> to check number of subtasks done vs. pending
#     '''

#     group_id = request.args.get('group_id')
#     if not group_id:
#         return jsonify({
#             'error': 'must supply group_id'
#         }), 400
    
#     res = GroupResult.restore(group_id)
#     if res is None:
#         return jsonify({
#             'error': 'no matching group_id'
#         }), 404

#     return jsonify({
#         'group_id': group_id,
#         'completed': len(res.completed_results),
#         'failed': len(res.failed_results),
#         'total': len(res.results),
#         'state': res.state
#     })
