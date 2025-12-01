# ODD (Operational Design Domain) Visualization Tool - Complete Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Key Terminologies](#key-terminologies)
4. [Tech Stack](#tech-stack)
5. [System Architecture (HLD)](#system-architecture-hld)
6. [Project Structure](#project-structure)
7. [Data Flow](#data-flow)
8. [Backend Deep Dive](#backend-deep-dive)
9. [Frontend Deep Dive](#frontend-deep-dive)
10. [Filter System Explained](#filter-system-explained)
11. [Setup & Usage Guide](#setup--usage-guide)
12. [Code Examples](#code-examples)

---

## 1. Project Overview

**Name:** TierIV ODD Safety Visualization Tool
**Institution:** Carnegie Mellon University Capstone Project
**Partner:** TierIV (Autonomous Vehicle Company)
**Purpose:** Analyze road networks to identify which roads are safe for autonomous vehicles (AVs) to operate on

### What This Tool Does
- Fetches real road data from OpenStreetMap (OSM)
- Analyzes junctions, road features, school zones, parking lots
- Filters roads based on safety criteria (ODD compliance)
- Visualizes safe vs. unsafe roads on an interactive map
- Helps AV companies plan deployment routes

---

## 2. Problem Statement

### The Challenge
**Autonomous vehicles cannot drive everywhere.** They need specific conditions to operate safely:
- Simple intersections (not complex roundabouts)
- Clear lane markings
- Appropriate speed limits
- Avoiding school zones and parking lots
- Roads with sufficient width

### The Solution
This tool automatically:
1. Downloads road network data for any location
2. Analyzes every junction and road segment
3. Applies user-defined safety criteria
4. Shows which roads meet the requirements (green lines)
5. Shows which roads don't (hidden or blue lines)

### Real-World Impact
- **AV Companies:** Plan deployment zones
- **City Planners:** Identify infrastructure improvements needed
- **Researchers:** Study ODD compliance patterns
- **Regulators:** Assess safety coverage

---

## 3. Key Terminologies

### ODD (Operational Design Domain)
The specific conditions where an AV can safely operate. Includes:
- Geographic area (geofencing)
- Road types (highways, residential streets)
- Environmental conditions (weather, lighting)
- Speed limits
- Junction complexity

**Example ODD:**
> "This AV can operate on primary and secondary roads with speed limits ≤ 50 km/h, only at T-junctions and crossroads, avoiding school zones."

### OSM (OpenStreetMap)
Free, crowd-sourced map database. Contains:
- Road geometry (coordinates)
- Road metadata (speed limits, lanes, surface)
- Points of interest (schools, parking, signals)

### Junction Types

**T-Junction**
```
    |
    |
----+----
```
3-way intersection where one road ends at another.

**Y-Junction**
```
   / \
  /   \
 /     \
```
3-way intersection where roads meet at similar angles.

**Crossroad**
```
    |
----+----
    |
```
4-way intersection where two roads cross.

**Roundabout**
```
  ---
 /   \
|  ○  |
 \   /
  ---
```
Circular junction where traffic flows in one direction.

### Conflict Types

**INTERSECT**
- Two vehicles' paths cross
- Example: Car going straight vs. car turning left
- **Risk:** Collision if timing is wrong
- **Impact on ODD:** High complexity

**MERGE**
- Two vehicles' paths combine into one lane
- Example: Car merging from right turn into through traffic
- **Risk:** Side-swipe collision
- **Impact on ODD:** Medium complexity

**NO_CONFLICT**
- Paths don't interfere
- Example: Two cars turning right from opposite directions
- **Risk:** Minimal
- **Impact on ODD:** Low complexity, safe

### Road Features

**highway_type:** Road classification in OSM
- `motorway` - Major highway
- `primary` - Major road
- `secondary` - Important local road
- `residential` - Neighborhood street
- `service` - Parking lot access

**lane_markings:** Turn permissions per lane
- `through` - Go straight only
- `left` - Turn left only
- `right` - Turn right only
- `left;through` - Left or straight

**speed_limit:** Maximum legal speed (km/h or mph)

**lane_width:** Physical width of lanes (meters)

**oneway:** Boolean - can traffic flow both directions?

**is_major_road:** Boolean - is this a primary/secondary road?

---

## 4. Tech Stack

### Backend (Python/Flask)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Programming language |
| Flask | 3.1.1 | Web framework for API |
| OSMnx | 2.0.5 | Fetch OSM data as graphs |
| NetworkX | 3.4.2 | Graph algorithms |
| GeoPandas | 1.1.0 | Spatial data manipulation |
| Shapely | 2.1.1 | Geometric operations |
| MongoDB | Latest | NoSQL database |
| PyMongo | 4.13.2 | MongoDB driver |
| Pydantic | 2.11.7 | Data validation |

**Why These Choices?**
- **OSMnx:** Industry standard for OSM data, built on NetworkX
- **NetworkX:** Graph algorithms for road networks (connected components, path finding)
- **GeoPandas:** Spatial operations (buffering, dissolving zones)
- **MongoDB:** Flexible schema for varying feature types, fast geospatial queries
- **Flask:** Lightweight, easy to organize with blueprints

### Frontend (React)

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.1.0 | UI framework |
| Leaflet | 1.9.4 | Interactive maps |
| React-Leaflet | 5.0.0 | React wrapper for Leaflet |
| Create React App | 5.0.1 | Build tooling |

**Why These Choices?**
- **React:** Component-based, efficient state management
- **Leaflet:** Standard for web mapping, large plugin ecosystem
- **React-Leaflet:** Declarative map components

---

## 5. System Architecture (HLD)

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│                     (Web Browser)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ HTTP Requests
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  IntroPage   │  │   MapView    │  │   Sidebar    │      │
│  │ (Location    │  │  (Leaflet    │  │  (Filters &  │      │
│  │  Input)      │  │   Display)   │  │  Controls)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                           │                                  │
│                    API Calls (JSON)                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (Flask API)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 API Endpoints                         │   │
│  │  /query  /junction  /road_features  /network         │   │
│  │  /school_zones  /parking_lot  /traffic_signals       │   │
│  └────────────┬──────────────────────────┬───────────────┘   │
│               │                          │                   │
│               ▼                          ▼                   │
│  ┌────────────────────┐    ┌────────────────────┐          │
│  │  Service Modules   │    │   Cache (60 min)   │          │
│  │  - Query           │    │   - Graph          │          │
│  │  - Junction        │    │   - Core Nodes     │          │
│  │  - Road Features   │    │   - GeoDataFrame   │          │
│  │  - School Zones    │    └────────────────────┘          │
│  │  - Network Filter  │                                     │
│  └────────┬───────────┘                                     │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────┐                                    │
│  │   OSMnx Library     │                                    │
│  │  (Fetch OSM Data)   │                                    │
│  └──────────┬──────────┘                                    │
│             │                                                │
└─────────────┼────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│              OpenStreetMap (Overpass API)                    │
│              - Road Networks                                 │
│              - Amenities (Schools, Parking, Signals)         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    MongoDB Database                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │    junction      │  │ network_primary  │                │
│  │  (Long-term      │  │  (Edge geometries│                │
│  │   junction       │  │   + metadata)    │                │
│  │   cache)         │  │                  │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐                                       │
│  │ network_feature  │                                       │
│  │ (Node metadata)  │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Frontend:**
- User interface
- Map visualization
- Filter selection
- API communication
- State management

**Backend:**
- Data fetching (OSM)
- Graph analysis
- Junction classification
- Feature extraction
- ODD filtering
- Caching

**Database:**
- Persistent storage
- Junction cache
- Network metadata
- Geospatial queries

---

## 6. Project Structure

```
tieriv-ood-nov30/
│
├── TierIV-Capstone-Backend/
│   ├── run.py                      # Flask server entry point
│   ├── config.py                   # Configuration loader
│   ├── requirements.txt            # Python dependencies
│   │
│   ├── app/
│   │   ├── __init__.py             # Flask app factory
│   │   ├── routes.py               # API route listing
│   │   ├── models.py               # Pydantic models
│   │   ├── extensions.py           # Singletons (Cache, DB)
│   │   │
│   │   └── service/
│   │       ├── query/
│   │       │   └── query.py        # POST /query
│   │       ├── junction/
│   │       │   ├── junction_analysis.py  # Classification
│   │       │   └── junction_tasks.py     # POST /junction
│   │       ├── network/
│   │       │   └── network_task.py       # POST /network
│   │       ├── road_features/
│   │       │   └── road_features_service.py  # POST /road_features
│   │       ├── SchoolZone/
│   │       │   └── school_zone_service.py    # POST /school_zones
│   │       ├── parkingLot/
│   │       │   └── parking_lot_service.py    # POST /parking_lot
│   │       └── traffic_signals/
│   │           └── traffic_signals_service.py # POST /traffic_signals
│   │
│   ├── predefined/
│   │   └── user_predefined_inputs.xlsx  # Config file
│   │
│   └── cache/                      # OSM data cache (JSON)
│
└── TierIV-Capstone-Frontend/
    ├── package.json                # NPM dependencies
    ├── public/
    │   └── index.html              # HTML template
    │
    └── src/
        ├── index.js                # React entry point
        ├── App.js                  # Main component
        │
        └── Components/
            ├── IntroPage.js        # Location input form
            ├── MapView.js          # Leaflet map container
            ├── Sidebar.js          # Filter controls
            ├── JunctionLayer.js    # Junction visualization
            ├── SchoolZoneLayer.js  # School zone overlay
            ├── RoadNetworkLayer.js # All roads display
            └── TrafficSignalLayer.js # Signal markers
```

---

## 7. Data Flow

### Complete User Journey

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Initial Query                                        │
└─────────────────────────────────────────────────────────────┘

User enters location → Frontend: POST /query
                     ↓
Backend: Fetch OSM data via OSMnx
        - Road network (MultiDiGraph)
        - Amenities (GeoDataFrame)
        - Cache graph + core_nodes
                     ↓
Frontend: Display map, show sidebar

┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Feature Analysis                                     │
└─────────────────────────────────────────────────────────────┘

User clicks "Junction" → Frontend: POST /junction
                       ↓
Backend: For each node:
        1. Classify junction type
        2. Build corridor polygon
        3. Count conflict types
        4. Store in MongoDB
                       ↓
Frontend: Display junction polygons, show filter options

User clicks "Road network" → Frontend: POST /road_features
                            ↓
Backend: Extract metadata for each edge:
        - highway_type, speed_limit, lanes
        - lane_markings, oneway, width
        - Store in MongoDB
                            ↓
Frontend: Display roads, show filter options

┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Filter Selection                                     │
└─────────────────────────────────────────────────────────────┘

User selects filters:
  - junction_type: [T_JUNCTION, CROSSROAD]
  - junction_conflict: [NO_CONFLICT]
  - school_zone: [false]
  - speed_limit: [50]
  - highway_type: [primary, secondary]
                       ↓
Frontend: Builds odd_param object

┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Network Generation                                   │
└─────────────────────────────────────────────────────────────┘

User clicks "Generate Network" → Frontend: POST /network
                                ↓
Backend:
1. Get ODD criteria (live/predefined/all)
2. Query network_feature for all nodes
3. Build incompliant_nodes set:
   - Nodes in school zones (if school_zone=false)
   - Nodes with forbidden junction types
   - Nodes with forbidden conflicts
4. Query network_primary for all edges
5. Filter edges:
   - Reject if either endpoint is incompliant
   - Reject if metadata doesn't match ODD
6. Build graph from compliant edges
7. Find longest connected component
8. Convert to GeoJSON MultiLineString
                                ↓
Frontend: Render green network on map
```

### Data Transformation

```
OSM XML/JSON
    ↓ (OSMnx)
NetworkX MultiDiGraph (nodes, edges, attributes)
    ↓ (Junction Analysis)
Junction Metadata (type, conflicts, polygon)
    ↓ (MongoDB)
Persistent Storage
    ↓ (ODD Filtering)
Compliant Subgraph
    ↓ (Shapely)
GeoJSON MultiLineString
    ↓ (React-Leaflet)
Visual Polylines on Map
```

---

## 8. Backend Deep Dive

### API Endpoints

#### POST /query - Initialize Session
**Purpose:** Fetch OSM data for a location

**Request:**
```json
{
  "input_type": "PLACE",
  "input": "Pittsburgh, PA",
  "dist": 10000,
  "overwrite": false,
  "default_query": false
}
```

**Process:**
1. Parse request with Pydantic validation
2. Check cache (query_key hash)
3. If new: Fetch OSM data via `ox.graph_from_place()`
4. Configure graph (add geometries, normalize widths)
5. Cache graph and core_nodes
6. Drop old MongoDB collections

**Response:**
```json
{
  "message": "Request and query successful.",
  "n_nodes": 1247,
  "n_edges": 3521
}
```

---

#### POST /junction - Analyze Junctions
**Purpose:** Classify junctions and count conflicts

**Process:**
1. For each core node:
   - **Classify type:**
     - Check OSM tags (roundabout, etc.)
     - Analyze geometry (degree, angles)
     - Assign: T_JUNCTION, CROSSROAD, Y_JUNCTION, etc.
   - **Build corridor:**
     - Trim edges to junction distance
     - Buffer edges by lane width
     - Union into polygon
   - **Count conflicts:**
     - For each edge pair:
       - Determine movement directions (THRU, TURN, CROSS)
       - Determine neighbor position (OPP, NEAR, FAR)
       - Look up conflict in classifier matrix
       - Increment counter (INTERSECT, MERGE, NO_CONFLICT)
2. Store in MongoDB

**Response:**
```json
{
  "results": [
    {
      "type": "Feature",
      "geometry": {"type": "Polygon", "coordinates": [...]},
      "properties": {
        "junc_type": "T_JUNCTION",
        "conflict_counter": {
          "INTERSECT": 2,
          "MERGE": 1,
          "NO_CONFLICT": 0
        }
      }
    }
  ],
  "feature_dict": [...]
}
```

---

#### POST /network - Generate ODD-Compliant Network
**Purpose:** Filter roads based on ODD criteria

**Request:**
```json
{
  "odd_type": "live",
  "odd_param": {
    "junction_type": ["T_JUNCTION"],
    "junction_conflict": ["NO_CONFLICT"],
    "school_zone": [false],
    "speed_limit": [50],
    "highway_type": ["primary", "secondary"]
  }
}
```

**Process:**
```python
# 1. Build incompliant node set
incompliant_nodes = set()

for node in network_feature.find():
    for feature in node['features']:
        # Check school zones
        if feature['feature_type'] == 'school_zone' and False in odd['school_zone']:
            incompliant_nodes.add(node['_id'])

        # Check junctions
        if feature['feature_type'] == 'junction':
            junc_type = feature['metadata']['junc_type']
            if junc_type not in odd['junction_type']:
                incompliant_nodes.add(node['_id'])

            conflicts = feature['metadata']['conflict_counter']
            for conflict in conflicts:
                if conflict not in odd['junction_conflict']:
                    incompliant_nodes.add(node['_id'])

# 2. Filter edges
compliant_edges = []

for edge in network_primary.find():
    u, v = edge['_id'].split('_')[:2]

    # Check node compliance
    if u in incompliant_nodes or v in incompliant_nodes:
        continue

    # Check edge metadata
    metadata = edge['properties']['metadata']

    if metadata['highway_type'] not in odd['highway_type']:
        continue

    if metadata['speed_limit'] > odd['speed_limit']:
        continue

    compliant_edges.append(edge['geometry'])

# 3. Find longest connected component
G = nx.Graph()
for edge in compliant_edges:
    G.add_edge(edge.start, edge.end)

components = list(nx.connected_components(G))
longest = max(components, key=lambda c: sum(edge_lengths))

# 4. Convert to GeoJSON
return mapping(MultiLineString(edges_in_longest))
```

**Response:** GeoJSON MultiLineString

---

### MongoDB Collections

**junction**
```json
{
  "_id": ObjectId,
  "x": 137.952,
  "y": 36.113,
  "type": "Feature",
  "geometry": {"type": "Polygon", "coordinates": [...]},
  "properties": {
    "junc_type": "T_JUNCTION",
    "conflict_counter": {"INTERSECT": 2, "MERGE": 1}
  }
}
```

**network_primary**
```json
{
  "_id": "12345_67890_0",
  "type": "Feature",
  "geometry": {"type": "LineString", "coordinates": [...]},
  "properties": {
    "metadata": {
      "highway_type": "primary",
      "speed_limit": 50,
      "lane_width": 3.5,
      "oneway": false
    }
  }
}
```

**network_feature**
```json
{
  "_id": 12345,
  "features": [
    {
      "feature_type": "junction",
      "metadata": {"junc_type": "T_JUNCTION", "conflict_counter": {...}}
    },
    {
      "feature_type": "school_zone",
      "metadata": {"school_names": ["Lincoln Elementary"]}
    }
  ]
}
```

---

## 9. Frontend Deep Dive

### Component Hierarchy

```
App
├── IntroPage (location input)
└── MapView (main view)
    ├── TileLayer (OpenStreetMap base)
    ├── Sidebar (filters + controls)
    ├── ZoneLayers
    │   ├── SchoolZoneLayer
    │   └── ParkingLotLayer
    ├── TrafficSignalLayer
    ├── JunctionLayer
    ├── RoadNetworkLayer (all roads - blue)
    └── GeoJSON (ODD network - green)
```

### State Management

**App.js:**
```javascript
const [locationParams, setLocationParams] = useState(null);
const [networkGeo, setNetworkGeo] = useState(null);
const [networkVersion, setNetworkVersion] = useState(0);

// After query
setLocationParams({input_type, input, dist});

// After network generation
setNetworkGeo(geojson);
setNetworkVersion(prev => prev + 1);  // Force re-render
```

**Sidebar.js:**
```javascript
const [selected, setSelected] = useState([]);  // Toggled layers
const [roadFeatures, setRoadFeatures] = useState(null);  // Feature dict
const [selectedFeatureValues, setSelectedFeatureValues] = useState({});  // ODD criteria
const [oddType, setOddType] = useState("all");  // all/predefined/live

const handleGenerateNetwork = () => {
  const body = {
    odd_type: oddType,
    odd_param: selectedFeatureValues
  };

  fetch(`${BACKEND_URL}/network`, {
    method: "POST",
    body: JSON.stringify(body)
  })
    .then(res => res.json())
    .then(geojson => onGenerateNetwork(geojson));
};
```

### Conditional Rendering

**MapView.js:**
```javascript
{networkGeo ? (
  // Show filtered network (green)
  <GeoJSON
    key={networkVersion}
    data={networkGeo}
    style={{color: "green", weight: 4}}
  />
) : (
  // Show all roads (blue)
  <RoadNetworkLayer visible={layers.includes("road_features")} />
)}
```

---

## 10. Filter System Explained

### Filter Types

**1. List Filters (Multiple Selection)**
```javascript
// Example: junction_type
{
  "feature_attr": "junction_type",
  "values": ["T_JUNCTION", "CROSSROAD", "Y_JUNCTION", "ROUNDABOUT"]
}

// User can select multiple (checkboxes)
selectedFeatureValues.junction_type = ["T_JUNCTION", "CROSSROAD"]
```

**2. Boolean Filters (Toggle)**
```javascript
// Example: school_zone
{
  "feature_attr": "school_zone",
  "values": [true, false]
}

// User toggles on/off
selectedFeatureValues.school_zone = [false]  // Avoid school zones
```

**3. Numeric Filters (Input Box)**
```javascript
// Example: speed_limit
{
  "feature_attr": "speed_limit",
  "values": []  // User enters value
}

// User types number
selectedFeatureValues.speed_limit = [50]  // Max 50 km/h
```

### What Each Filter Does

**junction_type**
- **Values:** T_JUNCTION, CROSSROAD, Y_JUNCTION, ROUNDABOUT
- **Effect:** Only roads with selected junction types are included
- **Example:** Select [T_JUNCTION, CROSSROAD] → Avoids roundabouts and Y-junctions

**junction_conflict**
- **Values:** NO_CONFLICT, MERGE, INTERSECT
- **Effect:** Only roads with selected conflict levels are included
- **Example:** Select [NO_CONFLICT] → Avoids junctions where vehicles' paths cross

**school_zone**
- **Values:** true, false
- **Effect:** Include/exclude roads near schools
- **Example:** Select [false] → Avoids all roads within 100m of schools

**parking_lot**
- **Values:** true, false
- **Effect:** Include/exclude roads near parking
- **Example:** Select [false] → Avoids parking lot entrances/exits

**traffic_signals**
- **Values:** true, false
- **Effect:** Include/exclude roads with traffic lights
- **Example:** Select [true] → Only roads with signals (structured right-of-way)

**highway_type**
- **Values:** motorway, primary, secondary, tertiary, residential, service
- **Effect:** Only selected road types are included
- **Example:** Select [primary, secondary] → Avoids highways and residential streets

**speed_limit**
- **Values:** Numeric (km/h)
- **Effect:** Roads must have speed ≤ limit
- **Example:** Set 50 → Excludes highways (typically 80-120 km/h)

**lane_width**
- **Values:** Numeric (meters)
- **Effect:** Roads must have width ≥ minimum
- **Example:** Set 3.5 → Excludes narrow alleys

**oneway**
- **Values:** true, false
- **Effect:** Include/exclude one-way streets
- **Example:** Select [true] → Only one-way streets (simpler traffic patterns)

**is_major_road**
- **Values:** true, false
- **Effect:** Include/exclude major roads (primary/secondary)
- **Example:** Select [false] → Avoids busy arterials

### Practical Filter Scenarios

**Scenario 1: Conservative AV (Maximum Safety)**
```json
{
  "junction_type": ["T_JUNCTION"],
  "junction_conflict": ["NO_CONFLICT"],
  "school_zone": [false],
  "parking_lot": [false],
  "traffic_signals": [true],
  "highway_type": ["primary", "secondary"],
  "speed_limit": [40],
  "lane_width": [3.5]
}
```
**Result:** Small network, major roads only, simple junctions, no schools/parking

**Scenario 2: Aggressive AV (Broader Coverage)**
```json
{
  "junction_type": ["T_JUNCTION", "CROSSROAD", "Y_JUNCTION"],
  "junction_conflict": ["NO_CONFLICT", "MERGE", "INTERSECT"],
  "school_zone": [true],
  "parking_lot": [true],
  "highway_type": ["primary", "secondary", "tertiary"],
  "speed_limit": [60],
  "lane_width": [3.0]
}
```
**Result:** Large network, handles complex scenarios

**Scenario 3: Residential Shuttle**
```json
{
  "junction_type": ["T_JUNCTION", "CROSSROAD"],
  "junction_conflict": ["NO_CONFLICT"],
  "highway_type": ["residential"],
  "speed_limit": [25],
  "traffic_signals": [false],
  "is_major_road": [false]
}
```
**Result:** Neighborhood streets only, low speed, simple junctions

---

## 11. Setup & Usage Guide

### Prerequisites
- Python 3.12+
- Node.js 16+
- MongoDB instance (local or cloud)

### Backend Setup

```bash
# Navigate to backend
cd TierIV-Capstone-Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
CONNECTION_STR=mongodb+srv://your-cluster.mongodb.net/?
USERNAME=your_username
PASSWORD=your_password
EOF

# Run server
python run.py
```

Server runs at `http://127.0.0.1:5000`

### Frontend Setup

```bash
# Navigate to frontend
cd TierIV-Capstone-Frontend

# Install dependencies
npm install

# (Optional) Configure backend URL
cat > .env << EOF
REACT_APP_BACKEND_URL=http://127.0.0.1
REACT_APP_BACKEND_PORT=5000
EOF

# Run development server
npm start
```

App opens at `http://localhost:3000`

### Step-by-Step Usage

**1. Enter Location**
- Open `http://localhost:3000`
- Select input type: "PLACE" (easiest)
- Enter: "Pittsburgh, PA"
- Click "Submit"
- Wait 10-30 seconds for data fetch

**2. View Features**
- Sidebar appears
- Click "Junction" → Wait for analysis
- Map shows junction polygons (color-coded)
- Click "Road network" → Roads appear
- Click "School zones", "Parking lots", "Traffic signals"

**3. Configure Filters**
- In sidebar, select "Live" ODD Type
- Expand "Junction" section
- Check: T_JUNCTION, CROSSROAD
- Expand "Road Features" section
- Select highway_type: residential
- Set speed_limit: 25
- Toggle is_major_road: OFF
- Toggle traffic_signals: OFF

**4. Generate Network**
- Click "Generate Network" button
- Wait 5-10 seconds
- Green lines appear (ODD-compliant)
- Blue lines disappear
- Zoom/pan to explore

**5. Iterate**
- Change filters
- Click "Generate Network" again
- Compare different configurations

---

## 12. Code Examples

### Example 1: Custom API Query

```python
import requests

# Initialize session
response = requests.post(
    "http://127.0.0.1:5000/query",
    json={
        "input_type": "BBOX",
        "input": "-80.05,40.43,-79.95,40.47",  # Pittsburgh bbox
        "dist": 5000,
        "overwrite": False,
        "default_query": False
    }
)
print(f"Fetched {response.json()['n_nodes']} nodes")

# Analyze junctions
response = requests.post("http://127.0.0.1:5000/junction")
junctions = response.json()['results']
print(f"Found {len(junctions)} junctions")

# Generate custom ODD network
response = requests.post(
    "http://127.0.0.1:5000/network",
    json={
        "odd_type": "live",
        "odd_param": {
            "junction_type": ["T_JUNCTION"],
            "speed_limit": [40],
            "highway_type": ["primary", "secondary"]
        }
    }
)
network = response.json()
print(f"Network has {len(network['coordinates'])} segments")
```

### Example 2: MongoDB Query

```python
from pymongo import MongoClient

client = MongoClient("your_mongodb_uri")
db = client.your_database

# Find all T-junctions with high conflict counts
t_junctions = db.junction.find({
    "properties.metadata.junc_type": "T_JUNCTION",
    "properties.metadata.conflict_counter.INTERSECT": {"$gte": 3}
})

for junc in t_junctions:
    coords = junc['properties']['node_coords']
    conflicts = junc['properties']['metadata']['conflict_counter']
    print(f"Complex T-junction at {coords}: {conflicts}")

# Find all edges on primary roads with low speed limits
slow_primary = db.network_primary.find({
    "properties.metadata.highway_type": "primary",
    "properties.metadata.speed_limit": {"$lte": 40}
})

print(f"Found {slow_primary.count()} slow primary roads")
```

### Example 3: React Component Usage

```javascript
// Custom component to highlight filtered roads
function FilteredRoadLayer({ oddCriteria }) {
  const [network, setNetwork] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/network", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        odd_type: "live",
        odd_param: oddCriteria
      })
    })
      .then(res => res.json())
      .then(data => setNetwork(data));
  }, [oddCriteria]);

  if (!network) return null;

  return (
    <GeoJSON
      data={network}
      style={{ color: "green", weight: 4, opacity: 0.8 }}
      onEachFeature={(feature, layer) => {
        layer.bindPopup("ODD-compliant road");
      }}
    />
  );
}

// Usage
<FilteredRoadLayer
  oddCriteria={{
    junction_type: ["T_JUNCTION"],
    speed_limit: [50]
  }}
/>
```

---

## Summary

This ODD Visualization Tool enables autonomous vehicle companies to:
1. **Identify** safe operating zones in any geographic area
2. **Visualize** ODD compliance on interactive maps
3. **Experiment** with different safety criteria
4. **Plan** deployment strategies

**Key Takeaway:** Not all roads are ready for autonomous vehicles. This tool helps find the ones that are.

---

## Quick Reference

### API Endpoints
- `POST /query` - Initialize session
- `POST /junction` - Analyze junctions
- `POST /road_features/` - Analyze roads
- `POST /school_zones` - Detect school zones
- `POST /parking_lot` - Detect parking lots
- `POST /traffic_signals` - Detect traffic signals
- `POST /network` - Generate ODD-compliant network

### MongoDB Collections
- `junction` - Junction cache
- `network_primary` - Edge geometries + metadata
- `network_feature` - Node metadata

### Key Files
- Backend: `run.py`, `app/service/network/network_task.py`
- Frontend: `App.js`, `Sidebar.js`, `MapView.js`
- Config: `predefined/user_predefined_inputs.xlsx`
