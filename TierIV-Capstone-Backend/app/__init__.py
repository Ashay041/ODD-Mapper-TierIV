from flask import Flask
from flask_cors import CORS
import ssl
import certifi

from config import Config
from flask_caching import Cache
from flask_pymongo import PyMongo
from .extensions import local_cache, mongo, celery_init_app


def create_app(CONFIG=Config) -> Flask:
    '''
    Flask app factory
    '''
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    cfg = CONFIG()
    app.config.from_object(cfg)

    # cache and db
    local_cache.init_app(app, config=cfg.LOCAL_CACHE)
    # with app.app_context():
    #     local_cache.clear()

    mongo_auth = cfg.load_authentication()
    app.config['MONGO_URI'] = mongo_auth['URI']
    app.config["MONGO_OPTIONS"] = {
        # less secure version:
        # 'ssl_cert_reqs': ssl.CERT_NONE,
        # more secure version:
        'tlsCAFile': certifi.where()
    }
    mongo.init_app(app, uri=mongo_auth['URI'])
    print('mongo.uri: ', mongo.cx)
    print('mongo.db: ', mongo.db)

    # celery_init_app(app)

    # register blueprints
    from app.service.query.query import query_bp
    app.register_blueprint(query_bp)

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.service.junction.junction_tasks import junction_bp
    app.register_blueprint(junction_bp)
    
    from app.service.SchoolZone.school_zone_service import school_zone_bp
    app.register_blueprint(school_zone_bp)
    
    from app.service.parkingLot.parking_lot_service import parking_lot_bp
    app.register_blueprint(parking_lot_bp)

    from app.service.traffic_signals.traffic_signals_service import traffic_light_bp
    app.register_blueprint(traffic_light_bp)

    from app.service.network.network_task import network_bp
    app.register_blueprint(network_bp)

    from app.service.road_features.road_features_service import road_feature_bp
    app.register_blueprint(road_feature_bp)

    return app
