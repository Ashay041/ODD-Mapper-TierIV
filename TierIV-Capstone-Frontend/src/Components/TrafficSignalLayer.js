// src/Components/TrafficSignalLayer.js
import React, { useState, useEffect } from "react";
import { Marker, Popup } from "react-leaflet";
import L from "leaflet";

/**
 * TrafficSignalLayer fetches and renders traffic signal points
 * from the backend endpoint `/traffic_signals`.  It expects
 * a POST that returns either:
 *   - an array of GeoJSON Features
 *   - or an object with a `results` or `features` array.
 */

// Create a smaller custom icon for traffic signals
const smallSignalIcon = L.divIcon({
  className: 'small-traffic-signal',
  html: '<div style="background-color: #ff6b35; border: 2px solid white; border-radius: 50%; width: 8px; height: 8px;"></div>',
  iconSize: [8, 8],
  iconAnchor: [4, 4],
  popupAnchor: [0, -4]
});

export default function TrafficSignalLayer({ enabled }) {
  const [signals, setSignals] = useState([]);

  useEffect(() => {
    if (!enabled) {
      setSignals([]);
      return;
    }

    fetch("http://127.0.0.1:5000/traffic_signals", {
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
          console.warn("Unexpected traffic_signals response shape:", data);
        }

        setSignals(features);
      })
      .catch((err) => {
        console.error("Failed to fetch traffic signals:", err);
        setSignals([]);
      });
  }, [enabled]);

  return (
    <>
      {signals.map((feature, idx) => {
        const [lng, lat] = feature.geometry.coordinates || [];
        const props = feature.properties || {};
        return (
          <Marker 
            key={`signal-${idx}`} 
            position={[lat, lng]}
            icon={smallSignalIcon}
          >
            <Popup>
              <strong>{props.feature_type || "Signal"}</strong>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}
