// src/Components/JunctionLayer.js
import React, { useEffect, useState } from "react";
import { Polygon, Popup } from "react-leaflet";

/** style by junction type */
function getStyle(type) {
  switch (type) {
    case "CROSSROAD":
      return { color: "#6a0dad", markerColor: "#6a0dad" };
    case "T_JUNCTION":
      return { color: "#d32f2f", markerColor: "#d32f2f" };
    case "Y_JUNCTION":
      return { color: "#388e3c", markerColor: "#388e3c" };
    default:
      return { color: "#777", markerColor: "#777" };
  }
}

/** Turn a GeoJSON ring [ [lng, lat], … ] → [ [lat, lng], … ] */
function ringToLatLngs(ring) {
  return ring.map(([lng, lat]) => [lat, lng]);
}

export default function JunctionLayer({ filters }) {
  const [junctions, setJunctions] = useState([]);

  useEffect(() => {
    if (filters.includes("junction")) {
      fetch("http://127.0.0.1:5000/junction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((json) => {
          setJunctions(json.results || []);
        })
        .catch((err) => {
          console.error("Failed loading junctions:", err);
          setJunctions([]);
        });
    } else {
      setJunctions([]);
    }
  }, [filters]);

  // nothing to draw if user hasn't selected "junction"
  if (!filters.includes("junction")) return null;

  return (
    <>
      {junctions.map((feat, idx) => {
        const { geometry, properties = {} } = feat;
        const meta = properties.metadata || {};
        const nodeCoords =
          meta.node_coords ??
          meta.node_coord ??
          properties.node_coords ??
          properties.node_coord;
        const juncType = meta.junc_type ?? properties.junc_type;

        if (
          !nodeCoords ||
          !Array.isArray(nodeCoords) ||
          nodeCoords.length < 2 ||
          !geometry?.coordinates
        ) {
          return null;
        }

        const style = getStyle(juncType);
        const [lng, lat] = nodeCoords;
        const positions = geometry.coordinates.map(ringToLatLngs);

        return (
          <Polygon
            key={idx}
            positions={positions}
            pathOptions={{ 
              color: style.color, 
              weight: 2, 
              fillOpacity: 0.1 
            }}
          >
            <Popup>
              <div style={{ maxWidth: '300px', fontSize: '12px' }}>
                <strong>Junction</strong><br/>
                
                {Object.keys(meta).length > 0 && (
                  <>
                    {Object.entries(meta).map(([key, value]) => {
                      let displayValue;
                      if (typeof value === 'object' && value !== null) {
                        if (Array.isArray(value)) {
                          displayValue = value.map(item => String(item)).join(', ');
                        } else {
                          displayValue = JSON.stringify(value);
                        }
                      } else {
                        displayValue = String(value);
                      }
                      
                      return (
                        <div key={key}>
                          <strong>{key.replace(/_/g, " ")}:</strong> {displayValue}<br/>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            </Popup>
          </Polygon>
        );
      })}
    </>
  );
}
