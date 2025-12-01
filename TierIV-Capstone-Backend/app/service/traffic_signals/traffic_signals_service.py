import geopandas as gpd
import networkx as nx
from flask import Blueprint, jsonify
from app import mongo
from pydantic import ValidationError
from shapely.geometry import mapping, Point
from pymongo import UpdateOne

from app import local_cache
from app.models import BaseExporter, Feature, FeatureDict

class TrafficSignalMapper:
    """
    Service to identify traffic signals from pre-existing graph and GeoDataFrame data.
    """
    def __init__(self, graph: nx.MultiDiGraph, features_gdf: gpd.GeoDataFrame):
        self.graph = graph
        self.features_gdf = features_gdf
        self.traffic_signals = None
        self.traffic_signals_docs = []

    def _fetch_traffic_signals_gdf(self):
        """
        Internal: Fetches traffic signal data from the provided GeoDataFrame.
        In OSM, traffic signals are typically nodes.
        """
        print("Filtering traffic signals from the cached GeoDataFrame...")
        try:
            # Check if 'highway' column exists
            if 'highway' not in self.features_gdf.columns:
                print("Warning: 'highway' column not found in cached GDF.")
                self.traffic_signals = gpd.GeoDataFrame()
                return False

            # Filter for nodes that are traffic signals
            gdf = self.features_gdf[self.features_gdf['highway'] == 'traffic_signals'].copy()

            if gdf.empty:
                print("No traffic signals found in the cached GDF.")
                self.traffic_signals = gpd.GeoDataFrame()
                return False
            
            # Ensure unique signals based on index (osmid)
            self.traffic_signals = gdf[~gdf.index.duplicated(keep='first')].copy()
            print(f"Found {len(self.traffic_signals)} unique traffic signals.")
            return True
        except Exception as e:
            print(f"An error occurred while fetching traffic signals from GDF: {e}")
            return False


    def generate_graph_results(self):
        '''
        Fetch nodes with traffic signals with graph and node ids
        '''
        operations = []
        net_coll = mongo.db.network_feature #type:ignore

        # loop through nodes
        for node_id in self.graph.nodes:
            node_attrs = self.graph.nodes[node_id]
            if node_attrs.get('highway') == 'traffic_signals':

                # prepare results
                feature_dict = {
                    "type": "Feature",
                    "geometry": Point(node_attrs['x'], node_attrs['y']),
                    "properties": {
                        "feature_type": "traffic_signal",
                    }
                }
                validated_feature = BaseExporter.model_validate(feature_dict)
                self.traffic_signals_docs.append(validated_feature.model_dump(mode="json"))

                # append operations for network collection output
                operations.append(
                    UpdateOne(
                        {'_id': node_id},
                        {'$addToSet': {
                            'features': {
                                'feature_type': 'traffic_signals'
                            }
                        }
                        },
                        upsert=True
                    )
                )

        # bulk write to collection
        if operations:
                output = net_coll.bulk_write(operations, ordered=False)

        return self.traffic_signals_docs 


    def generate_signal_data(self):
        """
        Executes the workflow and returns a dictionary suitable for an API response.
        """
        if not self._fetch_traffic_signals_gdf():
            return {"result": [], "status_code": 404}

        signal_features = []
        for index, signal in self.traffic_signals.iterrows():
            # The geometry for a node in a GeoDataFrame from osmnx is already a Point
            feature_dict = {
                "type": "Feature",
                "geometry": mapping(signal.geometry),
                "properties": {
                    "feature_type": "traffic_signal",
                    "osmid": index, # The GeoDataFrame index is the OSM ID
                    "odd_compliant": True # Placeholder for your logic
                }
            }
            try:
                # Validate using the app's shared BaseExporter model
                validated_feature = BaseExporter.model_validate(feature_dict)
                signal_features.append(validated_feature.model_dump(mode="json"))
            except ValidationError as e:
                print(f"Validation failed for traffic signal {index}: {e}")
                continue
        
        return {"result": signal_features, "status_code": 200}

# --- Flask Blueprint and Endpoint ---
# NOTE: Your app/__init__.py expects 'traffic_light_bp'. 
# We name it that here for consistency, even though the feature is traffic signals.
traffic_light_bp = Blueprint('traffic_light_bp', __name__, url_prefix='/traffic_signals')

@traffic_light_bp.route('/', methods=['POST'], strict_slashes=False)
def generate_traffic_signals_endpoint():
    """
    API endpoint to generate traffic signal data from cached graph and GDF.
    """
    # 1. Get cached data (same pattern as school zones)
    req_obj = local_cache.get('request')
    if not req_obj:
        return jsonify(error="Request context not found in cache. Please run a query first."), 400

    G = local_cache.get('graph')
    if G is None:
        return jsonify(error="Graph not found in cache. Please run a query first."), 400
        
    gdf = local_cache.get('gdf')
    if gdf is None:
        return jsonify(error="GDF not found in cache. Please run a query first."), 400

    # 2. Instantiate the service mapper
    mapper = TrafficSignalMapper(graph=G, features_gdf=gdf)

    # 3. Get the data and return it
    # api_response = mapper.generate_signal_data()
    api_response = mapper.generate_graph_results()

    # feature map
    ts_type_map = Feature('traffic_signals', [True, False])
    feature_map = FeatureDict()
    feature_map.add_feature_type('traffic_signals', [ts_type_map])

    return jsonify({'results': api_response, 'feature_dict': feature_map.out()}), 200
