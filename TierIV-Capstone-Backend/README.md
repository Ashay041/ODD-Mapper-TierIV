
# TierIV-CMU M25 Capstone: Operational Design Domain Safety Visualization Tool (Backend)

This project is part of the Summer 2025 Capstone for the Master of Information Systems Management program at Carnegie Mellon University, conducted in collaboration with TierIV as our industry partner. It features a backend pipeline designed to perform modular feature analysis and connectivity assessments on road network data, aimed at evaluating autonomous driving viability. The system leverages OpenStreetMap data to enable dynamic Operational Design Domain (ODD) filtering and visualization.




## Stakeholders

#### Primary Backend Contributors
- [@youyouh511](https://github.com/youyouh511)
- [@RohanRGH](https://github.com/RohanRGH)
- [@yhulsurk](https://github.com/yhulsurk)
- [@Ashay041](https://github.com/Ashay041)

#### Primary Frontend Contributors
- [@Aakash-919](https://github.com/Aakash-919)
- [@vimmuyengwa](https://github.com/vimmuyengwa)

## Architecture Overview
- **Request Management**: A centralized request object orchestrates query parameters and defines the scope of each session.
- **Data Querying & Caching**: Utilizes OSMnx to retrieve road network and amenity data based on bounding polygons and location types. Each session generates a configured data object that is cached locally for efficiency and consistency.
- **Feature Analysis**: Modular processors extract structured metadata and geometric representations for key infrastructure types, including road segments, junctions, signals, regulatory zones, and parking areas.
- **NoSQL Storage**: MongoDB serves as the caching layer for computed collections, minimizing redundant computations and streamlining downstream access.
- **Dynamic Output Generation**: Produces both raw feature documents and structured attribute dictionaries to support frontend filtering logic and map-based visualization workflows


## Key Features & API Summary
**Query & Initialization** `/query`  
Initializes the central request object and generates a directional `MultiDiGraph` and `GeoDataFrame`, configured according to product specifications. Ensures edge geometry integrity and completeness for downstream analysis.

**Road Segments** `/road_features/`  
Analyzes lane markings, directionality, and speed limits for compliance assessment.  

**Junctions** `/junction`  
Classifies junction types, calculates conflict potential, and generates polygonal complexity metrics.  

**School Zones** `/school_zone/`  
Derives operational zones around educational facilities using spatial buffers and metadata fusion.  

**Parking Lots** `/parking_lot/`  
Expands point-based data into standardized approach/departure polygons.

**Traffic Signals** `/traffic_signals/`  
Detects, classifies, and localizes signal nodes within the network graph.

**ODD Filtering Logic** `/network`  
Supports 3 analysis modes:
  - *All*: Full connectivity regardless of metadata
  - *Predefined*: Compliance based on uploaded config
  - *Live*: Interactive filter selections based on current analysis

Note: Stakeholder should be mindful of tolerance level of missing data and their impact on ODD compliance. Strongly recommended to review code in ODD compliance check to ensure correct translation of concepts.

## Artifacts
#### User Predefined Inputs (Excel File)  
`predefined\user_predefined_inputs.xlsx`  
The user-defined Excel file acts as a backend anchor, supplying default query parameters, validation constraints, and ODD (Operational Design Domain) criteria for automated configuration of road network analysis. 

`.env`: User must maintain a local `.env` file specifying the authentication for the MongoDB NoSQL database:
- CONNECTION_STR
- USERNAME
- PASSWORD

**Key Roles**
- *Default Configuration*: Initializes key fields such as input type, boundary definitions, and analysis scope.
- *Validation Layer*: Applies basic range and format checks as users populate the file, helping avoid malformed queries.
- *ODD Specification*: Encodes feature-level thresholds and permitted attributes aligned with autonomous operation criteria.

**Usage**  
Detailed field descriptions, valid value ranges, and expected formats are documented directly within the file to guide users in populating inputs correctly.

**Limitations & Future Considerations**  
While the current design requires backend access to modify or replace the file, future iterations could support frontend integration. This would allow users to dynamically supply, customize, and save real-time configurations, creating an archive of state-of-art operational presets for reproducibility and collaborative sharing.

## Installation

```bash
  pip install -r requirements.txt
```
    
## Run Server (before initializing Frontend)
```bash
  python run.py
```

python -m pip install "pymongo[srv]==3.12"

