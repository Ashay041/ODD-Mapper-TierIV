// src/Components/SchoolZoneLayer.js
import React, { useState, useEffect } from "react";
import { Polygon, Popup } from "react-leaflet";

/** Turn a GeoJSON ring [ [lng, lat], … ] → [ [lat, lng], … ] */
function ringToLatLngs(ring) {
  return ring.map(([lng, lat]) => [lat, lng]);
}

export default function SchoolZoneLayer({ enabled }) {
  const [schoolZones, setSchoolZones] = useState([]);

  useEffect(() => {
    if (!enabled) {
      setSchoolZones([]);
      return;
    }

    fetch("http://127.0.0.1:5000/school_zones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        let features = [];

        if (Array.isArray(data)) {
          features = data;
        } else if (Array.isArray(data.results)) {
          features = data.results;
        } else if (Array.isArray(data.features)) {
          features = data.features;
        } else {
          console.warn("Unexpected school_zones response shape:", data);
        }

        setSchoolZones(features);
      })
      .catch((err) => {
        console.error("Failed to fetch school zones:", err);
        setSchoolZones([]);
      });
  }, [enabled]);

  return (
    <>
      {schoolZones.map((feature, idx) => {
        const { geometry, properties = {} } = feature;
        const meta = properties.metadata || {};
        
        // Handle polygon geometry
        if (!geometry?.coordinates) {
          return null;
        }

        const positions = geometry.coordinates.map(ringToLatLngs);
        
        return (
          <Polygon
            key={`school-zone-${idx}`}
            positions={positions}
            pathOptions={{ 
              color: "#ffeb3b", // Yellow color for school zones
              weight: 2, 
              fillOpacity: 0.3 
            }}
          >
            <Popup>
              <div style={{ maxWidth: '300px', fontSize: '12px' }}>
                <strong>School Zone #{idx}</strong><br/>
                
                {/* Use exact same logic as junctions */}
                {Object.keys(meta).length > 0 && (
                  <>
                    <br/><strong>Metadata:</strong><br/>
                    {Object.entries(meta).map(([key, value]) => {
                      // Same logic as junctions for handling different data types
                      let displayValue;
                      if (key === 'conflict_counter' && typeof value === 'object') {
                        if (Array.isArray(value)) {
                          displayValue = value.map(item => String(item)).join(', ');
                        } else {
                          displayValue = JSON.stringify(value);
                        }
                      } else if (typeof value === 'object' && value !== null) {
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
                
                {/* Show other properties if they exist - same as junctions */}
                {Object.keys(properties).length > 0 && (
                  <>
                    <br/><strong>Additional Properties:</strong><br/>
                    {Object.entries(properties).map(([key, value]) => (
                      !['metadata'].includes(key) && (
                        <div key={key}>
                          <strong>{key.replace(/_/g, " ")}:</strong> {String(value)}<br/>
                        </div>
                      )
                    ))}
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