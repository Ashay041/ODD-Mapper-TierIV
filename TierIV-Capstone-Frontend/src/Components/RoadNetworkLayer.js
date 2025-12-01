// src/Components/RoadNetworkLayer.js
import React, { useState, useEffect } from "react";
import { Polyline, Popup } from "react-leaflet";

export default function RoadNetworkLayer({ visible }) {
  const [roads, setRoads] = useState([]);

  useEffect(() => {
    if (!visible) {
      setRoads([]);
      return;
    }

    fetch("http://127.0.0.1:5000/road_features/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        setRoads(json.results || []);
      })
      .catch((err) => {
        console.error("Failed loading road network:", err);
        setRoads([]);
      });
  }, [visible]);

  if (!visible || roads.length === 0) return null;

  // Convert GeoJSON coordinates to Leaflet format
  const convertCoordinates = (geometry) => {
    if (geometry.type === 'LineString') {
      return geometry.coordinates.map(([lng, lat]) => [lat, lng]);
    }
    return [];
  };

  return (
    <>
      {roads.map((road, idx) => {
        const { geometry, properties = {} } = road;
        const meta = properties.metadata || {};
        const positions = convertCoordinates(geometry);

        return (
          <Polyline
            key={idx}
            positions={positions}
            pathOptions={{
              color: "#3388ff",
              weight: 3,
              opacity: 0.8,
            }}
          >
            <Popup>
              <div style={{ maxWidth: '300px', fontSize: '12px' }}>
                <strong>Road</strong><br/>
                
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
          </Polyline>
        );
      })}
    </>
  );
}
