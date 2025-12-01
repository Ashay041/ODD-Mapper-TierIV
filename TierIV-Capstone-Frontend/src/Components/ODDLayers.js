// src/ODDLayers.js
import React, { useState, useEffect } from "react";
import { GeoJSON, Marker, Popup, Polygon } from "react-leaflet";
import "./ODDLayers.css";  // styles for this component

// Helper to parse your WKT‐POLYGON strings into Leaflet [lat, lng] arrays
function parseWKTPolygon(wkt) {
  return wkt
    .replace(/^POLYGON\s*\(\(/i, "")
    .replace(/\)\)$/, "")
    .split(",")
    .map(pair => {
      const [lng, lat] = pair.trim().split(/\s+/).map(Number);
      return [lat, lng];
    });
}

export default function ODDLayers() {
  const [junctions, setJunctions] = useState([]);
  const [edges, setEdges]         = useState(null);
  const [lanes, setLanes]         = useState(null);
  const [roadNet, setRoadNet]     = useState(null);

  useEffect(() => {
    // fire off all your fetches in parallel
    fetch("/api/junctions").then(r => r.json()).then(setJunctions).catch(console.error);
    fetch("/api/edges").then(r => r.json()).then(setEdges).catch(console.error);
    fetch("/api/lanes").then(r => r.json()).then(setLanes).catch(console.error);
    fetch("/api/longest-road-network")
      .then(r => r.json())
      .then(setRoadNet)
      .catch(console.error);
  }, []);

  return (
    <>
      {/* 1) Junction points + WKT polygons */}
      {junctions.map(j => (
        <React.Fragment key={j.node_id}>
          <Marker position={[j.node_coord[1], j.node_coord[0]]}>
            <Popup>
              <strong>{j.junc_type}</strong><br/>
              Conflicts: {JSON.stringify(j.conflict_counter)}
            </Popup>
          </Marker>
          {j.polygon && (
            <Polygon
              positions={parseWKTPolygon(j.polygon)}
              pathOptions={{ color: "blue", weight: 2, fillOpacity: 0.1 }}
            />
          )}
        </React.Fragment>
      ))}

      {/* 2) Edges (LineStrings) */}
      {edges && (
        <GeoJSON
          data={edges}
          style={() => ({ color: "#555", weight: 2 })}
          onEachFeature={(feature, layer) => {
            layer.bindPopup(`Edge ID: ${feature.properties.id}`);
          }}
        />
      )}

      {/* 3) Lanes (could be polygons or lines) */}
      {lanes && (
        <GeoJSON
          data={lanes}
          style={() => ({ color: "green", weight: 1, dashArray: "4 4" })}
          onEachFeature={(feature, layer) => {
            layer.bindPopup(`Lane ${feature.properties.lane_id}`);
          }}
        />
      )}

      {/* 4) Longest road network (GeoJSON) */}
      {roadNet && (
        <GeoJSON
          data={roadNet}
          style={{ color: "orange", weight: 5 }}
          onEachFeature={(feature, layer) => {
            const name = feature.properties?.name || "Road";
            layer.bindPopup(`🛣️ ${name}`);
          }}
        />
      )}
    </>
  );
}