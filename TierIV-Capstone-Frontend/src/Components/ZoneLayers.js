// src/Components/ZoneLayers.js
import React, { useState, useEffect } from "react";
import { Polygon, Marker, Tooltip, Popup } from "react-leaflet";

// Turn a GeoJSON ring [[lng,lat],…] → Leaflet [[lat,lng],…]
function coordsToLatLng(ring) {
  return ring.map(([lng, lat]) => [lat, lng]);
}

export default function ZoneLayers({ filters = [] }) {
  const [schoolZones, setSchoolZones] = useState([]);
  const [parkingLots, setParkingLots] = useState([]);

  useEffect(() => {
    if (filters.includes("school_zones")) {
      fetch("http://127.0.0.1:5000/school_zone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((data) => {
          // assume backend returns { results: [Feature,…] }
          setSchoolZones(Array.isArray(data) ? data : data.results || []);
        })
        .catch((err) => {
          console.error("Failed loading school zones:", err);
          setSchoolZones([]);
        });
    } else {
      setSchoolZones([]);
    }
  }, [filters]);

  useEffect(() => {
    if (filters.includes("parking_lot")) {
      fetch("http://127.0.0.1:5000/parking_lot/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((data) => {
          setParkingLots(Array.isArray(data) ? data : data.results || []);
        })
        .catch((err) => {
          console.error("Failed loading parking lots:", err);
          setParkingLots([]);
        });
    } else {
      setParkingLots([]);
    }
  }, [filters]);

  return (
    <>
      {schoolZones.map((feature, idx) => {
        const outerRing = feature.geometry.coordinates[0];
        const coords = coordsToLatLng(outerRing);
        const facilities = feature.properties?.facilities || [];

        return (
          <React.Fragment key={`school-${idx}`}>
            <Polygon
              positions={coords}
              pathOptions={{ color: "#ff7800", weight: 2, fillOpacity: 0.2 }}
            >
              <Tooltip direction="center" permanent>
                School Zone
              </Tooltip>
            </Polygon>
            {facilities.map((f, i) => (
              <Marker key={`school-fac-${idx}-${i}`} position={[f.center[1], f.center[0]]}>
                <Popup>{f.name || "School"}</Popup>
              </Marker>
            ))}
          </React.Fragment>
        );
      })}

      {parkingLots.map((feature, idx) => {
        const outerRing = feature.geometry.coordinates[0];
        const coords = coordsToLatLng(outerRing);
        const facilities = feature.properties?.facilities || [];

        return (
          <React.Fragment key={`parking-${idx}`}>
            <Polygon
              positions={coords}
              pathOptions={{ color: "#0000cd", weight: 2, fillOpacity: 0.2 }}
            >
              <Tooltip direction="center" permanent>
                Parking Lot
              </Tooltip>
            </Polygon>
            {facilities.map((f, i) => (
              <Marker key={`parking-fac-${idx}-${i}`} position={[f.center[1], f.center[0]]}>
                <Popup>{f.name || "Parking"}</Popup>
              </Marker>
            ))}
          </React.Fragment>
        );
      })}
    </>
  );
}
