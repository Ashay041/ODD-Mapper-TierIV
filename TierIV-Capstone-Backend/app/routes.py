from flask import Blueprint, jsonify

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def index():
    return jsonify({
        "message": "Welcome to TierIV Capstone Backend",
        "status": "running",
        "endpoints": [
            "/query",
            "/network",
            "/junction",
            "/school_zone",
            "/parking_lot",
            "/traffic_signals",
            "/road_features"
        ]
    })