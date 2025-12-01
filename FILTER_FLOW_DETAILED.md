# Complete Filter Selection Flow - Step by Step

## Overview
This document explains exactly what happens when a user selects filters and generates an ODD-compliant network.

---

## The Complete Journey: From Click to Green Lines

### STAGE 1: Initial Setup (Before Filter Selection)

#### Step 1.1: User Submits Location
**Where:** `IntroPage.js`

```javascript
// User enters "Pittsburgh, PA" and clicks Submit
const handleSubmit = () => {
  fetch("http://127.0.0.1:5000/query", {
    method: "POST",
    body: JSON.stringify({
      input_type: "PLACE",
      input: "Pittsburgh, PA",
      dist: 10000
    })
  })
}
```

#### Step 1.2: Backend Fetches OSM Data
**Where:** `app/service/query/query.py`

```python
# Backend receives request
def query_osm():
    # 1. Fetch road network from OSM
    G = ox.graph_from_place("Pittsburgh, PA", network_type='drive')
    # Result: Graph with 1,247 nodes, 3,521 edges

    # 2. Cache the graph
    local_cache.set('graph', G)
    local_cache.set('core_nodes', core_node_list)

    # 3. Return to frontend
    return {"n_nodes": 1247, "n_edges": 3521}
```

#### Step 1.3: Frontend Shows Map
**Where:** `App.js`

```javascript
// App receives response
setLocationParams(locationData);
// Now shows: MapView + Sidebar
```

---

### STAGE 2: Feature Analysis (Preparing for Filters)

#### Step 2.1: User Clicks "Junction" Layer
**Where:** `Sidebar.js`

```javascript
const handleLayerToggle = (layer) => {
  if (layer === 'junction') {
    // Add to selected layers
    setSelected([...selected, 'junction']);

    // Fetch junction analysis
    fetchJunctionData();
  }
}

const fetchJunctionData = () => {
  fetch("http://127.0.0.1:5000/junction", {
    method: "POST"
  })
  .then(res => res.json())
  .then(data => {
    // Store results for map display
    setJunctionResults(data.results);

    // Store feature dictionary for filter UI
    setJunctionFeatures(data.feature_dict);
    // feature_dict = [
    //   {
    //     feature_type: "junction",
    //     features: [
    //       {
    //         feature_attr: "junction_type",
    //         values: ["T_JUNCTION", "CROSSROAD", "Y_JUNCTION", "ROUNDABOUT"]
    //       },
    //       {
    //         feature_attr: "junction_conflict",
    //         values: ["INTERSECT", "MERGE", "NO_CONFLICT"]
    //       }
    //     ]
    //   }
    // ]
  });
}
```

#### Step 2.2: Backend Analyzes All Junctions
**Where:** `app/service/junction/junction_tasks.py`

```python
def junction_analysis():
    # Get cached graph
    G = local_cache.get('graph')
    core_nodes = local_cache.get('core_nodes')

    results = []

    # For each node in the network
    for node_id in core_nodes:
        # Step A: Classify junction type
        junc_type = classify_node(G, node_id)
        # Result: "T_JUNCTION"

        # Step B: Count conflicts
        conflict_counter = count_conflicts(G, node_id)
        # Result: {"INTERSECT": 2, "MERGE": 1, "NO_CONFLICT": 0}

        # Step C: Build polygon
        polygon = create_junction_polygon(G, node_id)

        # Step D: Store in MongoDB
        db.junction.insert_one({
            "x": node_coords[0],
            "y": node_coords[1],
            "properties": {
                "junc_type": junc_type,
                "conflict_counter": conflict_counter
            },
            "geometry": polygon
        })

        # Also store in network_feature collection
        db.network_feature.update_one(
            {"_id": node_id},
            {"$push": {
                "features": {
                    "feature_type": "junction",
                    "metadata": {
                        "junc_type": junc_type,
                        "conflict_counter": conflict_counter
                    }
                }
            }},
            upsert=True
        )

        results.append({
            "type": "Feature",
            "geometry": polygon,
            "properties": {
                "junc_type": junc_type,
                "conflict_counter": conflict_counter
            }
        })

    # Build feature dictionary
    all_junction_types = set()
    all_conflict_types = set()

    for result in results:
        all_junction_types.add(result['properties']['junc_type'])
        all_conflict_types.update(result['properties']['conflict_counter'].keys())

    feature_dict = [{
        "feature_type": "junction",
        "features": [
            {
                "feature_attr": "junction_type",
                "values": list(all_junction_types)
            },
            {
                "feature_attr": "junction_conflict",
                "values": list(all_conflict_types)
            }
        ]
    }]

    return {
        "results": results,  # For map display
        "feature_dict": feature_dict  # For filter UI
    }
```

#### Step 2.3: Frontend Displays Junction Polygons
**Where:** `JunctionLayer.js`

```javascript
{junctionResults.map((junction, idx) => (
  <Polygon
    key={idx}
    positions={junction.geometry.coordinates}
    pathOptions={{
      color: getColorByType(junction.properties.junc_type),
      fillOpacity: 0.3
    }}
  />
))}
```

#### Step 2.4: Sidebar Shows Filter Options
**Where:** `Sidebar.js`

```javascript
// Feature dictionary is used to render filter UI
{junctionFeatures?.features.map((feature) => (
  <div key={feature.feature_attr}>
    <h4>{feature.feature_attr}</h4>
    {feature.values.map(value => (
      <label>
        <input
          type="checkbox"
          value={value}
          onChange={(e) => handleFilterChange(feature.feature_attr, value, e.target.checked)}
        />
        {value}
      </label>
    ))}
  </div>
))}
```

**Result:** User now sees:
- Junction polygons on map
- Filter checkboxes for junction_type and junction_conflict

---

### STAGE 3: User Selects Filters

#### Step 3.1: User Checks "T_JUNCTION"
**Where:** `Sidebar.js`

```javascript
const handleFilterChange = (attribute, value, isChecked) => {
  setSelectedFeatureValues(prev => {
    const current = prev[attribute] || [];

    if (isChecked) {
      // Add to selection
      return {
        ...prev,
        [attribute]: [...current, value]
      };
    } else {
      // Remove from selection
      return {
        ...prev,
        [attribute]: current.filter(v => v !== value)
      };
    }
  });
}

// After user checks T_JUNCTION and CROSSROAD:
// selectedFeatureValues = {
//   junction_type: ["T_JUNCTION", "CROSSROAD"]
// }
```

#### Step 3.2: User Checks "NO_CONFLICT"
```javascript
// User checks NO_CONFLICT
// selectedFeatureValues = {
//   junction_type: ["T_JUNCTION", "CROSSROAD"],
//   junction_conflict: ["NO_CONFLICT"]
// }
```

#### Step 3.3: User Clicks "Road network" Layer
```javascript
// Triggers road_features fetch
fetch("http://127.0.0.1:5000/road_features/", {method: "POST"})
  .then(res => res.json())
  .then(data => {
    setRoadFeatures(data.feature_dict);
    // feature_dict = [
    //   {
    //     feature_type: "road",
    //     features: [
    //       {feature_attr: "highway_type", values: ["primary", "secondary", "residential"]},
    //       {feature_attr: "speed_limit", values: []},
    //       {feature_attr: "lane_width", values: []}
    //     ]
    //   }
    // ]
  });
```

#### Step 3.4: User Selects Road Filters
```javascript
// User selects:
// - highway_type: "residential" (checkbox)
// - speed_limit: 25 (text input)
// - is_major_road: false (toggle)
// - traffic_signals: false (toggle)

// selectedFeatureValues now = {
//   junction_type: ["T_JUNCTION", "CROSSROAD"],
//   junction_conflict: ["NO_CONFLICT"],
//   highway_type: ["residential"],
//   speed_limit: [25],
//   is_major_road: [false],
//   traffic_signals: [false]
// }
```

#### Step 3.5: User Selects "Live" ODD Type
```javascript
const handleOddTypeChange = (e) => {
  setOddType(e.target.value);  // "live"
}

// oddType = "live"
```

---

### STAGE 4: Network Generation (The Main Event)

#### Step 4.1: User Clicks "Generate Network" Button
**Where:** `Sidebar.js`

```javascript
const handleGenerateNetwork = () => {
  // Build request body
  const body = {
    odd_type: oddType,  // "live"
    odd_param: selectedFeatureValues  // All selected filters
  };

  // Send to backend
  fetch("http://127.0.0.1:5000/network", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  })
  .then(res => res.json())
  .then(networkGeoJSON => {
    // Pass to parent component (App.js)
    onGenerateNetwork(networkGeoJSON);
  });
}
```

**Request sent to backend:**
```json
{
  "odd_type": "live",
  "odd_param": {
    "junction_type": ["T_JUNCTION", "CROSSROAD"],
    "junction_conflict": ["NO_CONFLICT"],
    "highway_type": ["residential"],
    "speed_limit": [25],
    "is_major_road": [false],
    "traffic_signals": [false]
  }
}
```

---

#### Step 4.2: Backend Receives Request
**Where:** `app/service/network/network_task.py`

```python
@network_bp.route('', methods=['POST'])
def network_odd_compliance():
    # Parse request
    req = request.get_json()
    odd_type = req.get('odd_type', 'all').lower()  # "live"

    # Get ODD criteria
    if odd_type == 'live':
        odd = req.get('odd_param')
        # odd = {
        #   "junction_type": ["T_JUNCTION", "CROSSROAD"],
        #   "junction_conflict": ["NO_CONFLICT"],
        #   "highway_type": ["residential"],
        #   "speed_limit": [25],
        #   "is_major_road": [false],
        #   "traffic_signals": [false]
        # }
```

---

#### Step 4.3: Build Incompliant Nodes Set
**Where:** Same file, continuing...

```python
    # Initialize empty set
    incompliant_nodes = set()

    # Query all nodes with features from MongoDB
    features = db.network_feature.find()

    # Extract ODD criteria
    odd_junction_type = odd.get('junction_type', ['ALL'])
    odd_junction_conflict = odd.get('junction_conflict', ['ALL'])
    odd_school_zone = odd.get('school_zone', [True])
    odd_parking_lot = odd.get('parking_lot', [True])
    odd_traffic_signals = odd.get('traffic_signals', [True])

    # Iterate through all nodes
    for doc in features:
        node_id = doc['_id']  # e.g., 12345
        node_features = doc['features']  # List of features at this node

        # Check each feature at this node
        for feature in node_features:
            feature_type = feature['feature_type']

            # CHECK 1: School zones
            if feature_type == 'school_zone':
                if False in odd_school_zone:  # User said: avoid school zones
                    # This node is in a school zone, mark as incompliant
                    incompliant_nodes.add(node_id)
                    print(f"Node {node_id} rejected: in school zone")

            # CHECK 2: Parking lots
            if feature_type == 'parking_lot':
                if False in odd_parking_lot:
                    incompliant_nodes.add(node_id)
                    print(f"Node {node_id} rejected: near parking lot")

            # CHECK 3: Traffic signals
            if feature_type == 'traffic_signals':
                if False in odd_traffic_signals:  # User said: no traffic signals
                    incompliant_nodes.add(node_id)
                    print(f"Node {node_id} rejected: has traffic signal")

            # CHECK 4: Junction type and conflicts
            if feature_type == 'junction':
                metadata = feature['metadata']
                junc_type = metadata['junc_type']  # e.g., "ROUNDABOUT"
                conflict_counter = metadata['conflict_counter']

                # Check junction type
                if 'ALL' not in odd_junction_type:
                    if junc_type not in odd_junction_type:
                        # User only wants T_JUNCTION and CROSSROAD
                        # This is a ROUNDABOUT
                        incompliant_nodes.add(node_id)
                        print(f"Node {node_id} rejected: junction type {junc_type}")

                # Check conflicts
                if 'ALL' not in odd_junction_conflict:
                    for conflict_type in conflict_counter:
                        if conflict_type not in odd_junction_conflict:
                            # User only wants NO_CONFLICT
                            # This junction has INTERSECT conflicts
                            incompliant_nodes.add(node_id)
                            print(f"Node {node_id} rejected: has {conflict_type} conflicts")

    print(f"Total incompliant nodes: {len(incompliant_nodes)}")
    # Example output: "Total incompliant nodes: 423"
```

---

#### Step 4.4: Filter Edges
**Where:** Same file, continuing...

```python
    # Query all edges from MongoDB
    primary_docs = db.network_primary.find()

    compliant_geometries = []

    # Iterate through all edges
    for doc in primary_docs:
        edge_id = doc['_id']  # e.g., "12345_67890_0"

        # Extract node IDs from edge ID
        parts = edge_id.split('_')
        u = int(parts[0])  # Start node: 12345
        v = int(parts[1])  # End node: 67890

        # CHECK 5: Both endpoints must be compliant
        if u in incompliant_nodes:
            print(f"Edge {edge_id} rejected: start node {u} incompliant")
            continue

        if v in incompliant_nodes:
            print(f"Edge {edge_id} rejected: end node {v} incompliant")
            continue

        # Both endpoints are compliant, now check edge metadata
        metadata = doc['properties']['metadata']

        # CHECK 6: Highway type
        highway_type = metadata.get('highway_type')
        odd_highway = odd.get('highway_type', ['ALL'])

        if 'ALL' not in odd_highway:
            if highway_type not in odd_highway:
                # User wants "residential" only
                # This is "primary"
                print(f"Edge {edge_id} rejected: highway type {highway_type}")
                continue

        # CHECK 7: Speed limit
        speed_limit = metadata.get('speed_limit', 999)
        odd_speed = odd.get('speed_limit', [999])[0]

        if speed_limit > odd_speed:
            # User wants max 25 km/h
            # This road is 50 km/h
            print(f"Edge {edge_id} rejected: speed {speed_limit} > {odd_speed}")
            continue

        # CHECK 8: Lane width
        lane_width = metadata.get('lane_width', 0)
        odd_width = odd.get('lane_width', [0])[0]

        if lane_width < odd_width:
            print(f"Edge {edge_id} rejected: width {lane_width} < {odd_width}")
            continue

        # CHECK 9: Is major road
        is_major = metadata.get('is_major_road', False)
        odd_major = odd.get('is_major_road', [True])

        if False in odd_major and is_major:
            # User said: no major roads
            # This is a major road
            print(f"Edge {edge_id} rejected: is major road")
            continue

        # CHECK 10: One-way
        oneway = metadata.get('oneway', False)
        odd_oneway = odd.get('oneway', [True])

        if False in odd_oneway and not oneway:
            print(f"Edge {edge_id} rejected: not one-way")
            continue

        # All checks passed! This edge is compliant
        geometry = shape(doc['geometry'])  # Convert to Shapely LineString
        compliant_geometries.append(geometry)
        print(f"Edge {edge_id} accepted ✓")

    print(f"Total compliant edges: {len(compliant_geometries)}")
    # Example: "Total compliant edges: 1,621"
```

---

#### Step 4.5: Find Longest Connected Component
**Where:** Same file, continuing...

```python
    # Build a graph from compliant edges
    G_compliant = nx.Graph()

    for line in compliant_geometries:
        coords = list(line.coords)

        # Add edges between consecutive coordinate pairs
        for i in range(len(coords) - 1):
            G_compliant.add_edge(
                coords[i],      # Start point (x, y)
                coords[i + 1],  # End point (x, y)
                line=line
            )

    print(f"Graph nodes: {G_compliant.number_of_nodes()}")
    print(f"Graph edges: {G_compliant.number_of_edges()}")

    # Find all connected components
    components = list(nx.connected_components(G_compliant))
    print(f"Found {len(components)} connected components")

    # Find the component with maximum total length
    def component_length(component):
        subgraph = G_compliant.subgraph(component)
        total = 0
        for u, v in subgraph.edges:
            line = LineString([u, v])
            total += line.length
        return total

    longest_component = max(components, key=component_length)
    longest_subgraph = G_compliant.subgraph(longest_component).copy()

    print(f"Longest component has {longest_subgraph.number_of_edges()} edges")

    # Extract LineStrings from longest component
    lines_out = []
    for u, v, data in longest_subgraph.edges(data=True):
        lines_out.append(data['line'])

    # Convert to MultiLineString
    multi_line = MultiLineString(lines_out)

    # Convert to GeoJSON
    geojson = mapping(multi_line)
    # geojson = {
    #   "type": "MultiLineString",
    #   "coordinates": [
    #     [[lon1, lat1], [lon2, lat2]],
    #     [[lon2, lat2], [lon3, lat3]],
    #     ...
    #   ]
    # }

    return jsonify(geojson)
```

---

#### Step 4.6: Frontend Receives Network
**Where:** `Sidebar.js`

```javascript
fetch("http://127.0.0.1:5000/network", {...})
  .then(res => res.json())
  .then(networkGeoJSON => {
    // networkGeoJSON = {
    //   type: "MultiLineString",
    //   coordinates: [[[lon, lat], [lon, lat]], ...]
    // }

    // Pass to parent (App.js)
    onGenerateNetwork(networkGeoJSON);
  });
```

#### Step 4.7: App.js Updates State
**Where:** `App.js`

```javascript
const handleGenerateNetwork = (geojson) => {
  setNetworkGeo(geojson);
  setNetworkVersion(prev => prev + 1);  // Force re-render
}
```

---

#### Step 4.8: MapView Renders Green Network
**Where:** `MapView.js`

```javascript
{networkGeo ? (
  // ODD-compliant network (GREEN)
  <GeoJSON
    key={networkVersion}  // Key change forces new component
    data={networkGeo}
    style={{
      color: "green",
      weight: 4,
      opacity: 0.8
    }}
  />
) : (
  // All roads (BLUE)
  <RoadNetworkLayer visible={true} />
)}
```

**What React-Leaflet does:**
1. Parses GeoJSON MultiLineString
2. Extracts coordinate arrays
3. Creates Polyline components for each LineString
4. Renders as SVG paths on the map
5. Applies green color and weight 4

---

### STAGE 5: Visual Result

#### What User Sees:
- **Before Generate Network:** Blue lines (all roads)
- **After Generate Network:** Green lines (filtered roads)
- Green network is subset of blue network
- Only residential streets with simple junctions and no traffic signals

#### Example Numbers (Pittsburgh):
- **Total roads:** 3,521 edges
- **After node filtering:** 2,100 edges remain (59%)
- **After edge filtering:** 890 edges remain (25%)
- **Longest component:** 621 edges (18%)

---

## Summary Diagram

```
USER CLICKS FILTER
       ↓
Sidebar.js: handleFilterChange()
       ↓
selectedFeatureValues updated
       ↓
USER CLICKS "GENERATE NETWORK"
       ↓
Sidebar.js: handleGenerateNetwork()
       ↓
POST /network {odd_type: "live", odd_param: {...}}
       ↓
Backend: network_task.py
       ↓
Query MongoDB network_feature collection
       ↓
Build incompliant_nodes set
  - Check school zones
  - Check parking lots
  - Check traffic signals
  - Check junction types
  - Check junction conflicts
       ↓
Query MongoDB network_primary collection
       ↓
Filter edges (10 checks per edge)
  - Check node compliance
  - Check highway type
  - Check speed limit
  - Check lane width
  - Check major road status
  - Check one-way status
       ↓
Build graph from compliant edges
       ↓
Find connected components
       ↓
Select longest component
       ↓
Convert to GeoJSON MultiLineString
       ↓
Return to frontend
       ↓
App.js: setNetworkGeo(geojson)
       ↓
MapView.js: <GeoJSON data={networkGeo} />
       ↓
React-Leaflet: Render green polylines
       ↓
USER SEES GREEN NETWORK ON MAP
```

---

## Key Takeaways

1. **Frontend stores filter state** in `selectedFeatureValues` object
2. **Network generation is triggered manually** by "Generate Network" button
3. **Backend does ALL the heavy lifting** - frontend just displays results
4. **Node filtering happens first** (school zones, junctions)
5. **Edge filtering happens second** (road metadata)
6. **Longest component extraction ensures connectivity** (no isolated fragments)
7. **React key prop forces re-render** when network changes
8. **MongoDB caching speeds up repeated queries**

The entire flow from click to visualization takes 5-10 seconds depending on network size.
