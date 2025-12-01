# TierIV ODD Analyzer

## What
An Operational Design Domain (ODD) analysis system that evaluates road infrastructure and features to determine autonomous vehicle operational safety. The system queries OpenStreetMap data, analyzes road networks, junctions, traffic signals, school zones, parking lots, and other features to generate ODD compliance reports.

## Why
Autonomous vehicles require detailed understanding of their operational environment. This tool helps identify areas where autonomous vehicles can safely operate by analyzing road infrastructure, detecting potential hazards, and mapping operational constraints based on real-world geographic data.

## How
1. **Frontend** - Interactive map interface for defining analysis regions and visualizing ODD compliance results
2. **Backend** - Flask-based API that queries OSM data, analyzes road features using graph theory and geospatial algorithms, and stores results in MongoDB
3. **Analysis Pipeline** - Multi-stage feature extraction including junction analysis, network validation, traffic signal detection, and zone identification

## Tech Stack

### Backend
- **Framework**: Flask 3.1.1 with Flask-CORS
- **Database**: MongoDB (PyMongo 4.13.2)
- **Caching**: Flask-Caching (local cache)
- **Geospatial**: OSMnx 2.0.5, GeoPandas 1.1.0, Shapely 2.1.1
- **Analysis**: NetworkX 3.4.2, NumPy 2.3.2, Pandas 2.3.1, SciPy 1.16.1
- **Task Queue**: Celery 5.5.3
- **Data Validation**: Pydantic 2.11.7

### Frontend
- **Framework**: React 19.1.0
- **Mapping**: Leaflet 1.9.4, React-Leaflet 5.0.0
- **Geometry**: Terraformer WKT Parser
- **Testing**: Jest, React Testing Library

## API Endpoints

### Core Endpoints

#### `POST /query`
Initial query endpoint - processes location request, fetches OSM data, generates road network graph, and caches core objects for subsequent analysis.

**Request**: Location coordinates, radius, configuration options
**Response**: Query status, cached graph info

#### `POST /junction`
Analyzes road junctions/intersections - extracts geometry, calculates complexity metrics, identifies turn restrictions, and validates ODD compliance.

**Response**: Junction features with coordinates, turn lanes, traffic controls, complexity scores

#### `POST /network`
Performs network-level analysis - validates connectivity, identifies isolated segments, analyzes lane configurations, and checks access restrictions.

**Response**: Network topology, segment metadata, accessibility flags

#### `POST /school_zone`
Detects school zones and educational facilities within query area using OSM tags and spatial proximity.

**Response**: School zone boundaries, associated speed limits, operational hours

#### `POST /parking_lot`
Identifies parking areas and lots - extracts boundaries, capacity, access points, and surface types.

**Response**: Parking geometries, capacity info, surface conditions

#### `POST /traffic_signals`
Locates traffic signals and their configurations - identifies signal positions, phases, and junction associations.

**Response**: Traffic signal coordinates, control types, associated junctions

#### `POST /road_features`
Extracts detailed road characteristics - surface quality, lighting, width, lane markings, and special attributes.

**Response**: Road segments with material, lighting status, dimensions, lane details

#### `GET /`
Health check and endpoint discovery.

**Response**: API status, available endpoints list

## Project Structure

```
.
├── TierIV-Capstone-Backend/     # Flask API backend
│   ├── app/
│   │   ├── service/              # Feature analysis modules
│   │   │   ├── query/            # OSM data query & caching
│   │   │   ├── junction/         # Junction analysis
│   │   │   ├── network/          # Network validation
│   │   │   ├── SchoolZone/       # School zone detection
│   │   │   ├── parkingLot/       # Parking lot extraction
│   │   │   ├── traffic_signals/  # Traffic signal identification
│   │   │   └── road_features/    # Road feature analysis
│   │   ├── models.py             # Data models
│   │   ├── routes.py             # Main routes
│   │   └── extensions.py         # App extensions
│   ├── config.py                 # Configuration
│   ├── run.py                    # Application entry point
│   └── requirements.txt          # Python dependencies
│
├── TierIV-Capstone-Frontend/    # React web interface
│   ├── src/
│   │   ├── Components/          # React components
│   │   │   ├── MapComponent.js  # Main map container
│   │   │   ├── Sidebar.js       # Control panel
│   │   │   ├── IntroPage.js     # Landing page
│   │   │   └── *Layer.js        # Feature layer components
│   │   └── App.js               # Main app component
│   └── package.json             # npm dependencies
│
└── docs-local/                   # Local documentation (not tracked)
```

## Getting Started

### Backend Setup
```bash
cd TierIV-Capstone-Backend
pip install -r requirements.txt
python run.py
```
Backend runs on `http://localhost:5000`

### Frontend Setup
```bash
cd TierIV-Capstone-Frontend
npm install
npm start
```
Frontend runs on `http://localhost:3000`

### Configuration
Create `.env` file in backend directory with MongoDB connection string:
```
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/database
```

## Usage
1. Open frontend interface
2. Define analysis region on map (center point + radius)
3. Configure analysis parameters
4. Submit query to process OSM data
5. View results on map with feature layers
6. Export ODD compliance report

## License
Academic project for TierIV capstone
