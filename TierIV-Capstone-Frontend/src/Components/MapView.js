import React, { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  useMap,
  Marker,
  Popup,
  GeoJSON
} from "react-leaflet";
import L from "leaflet";
import "./MapView.css";
import "leaflet/dist/leaflet.css";

import JunctionLayer from "./JunctionLayer";
import ZoneLayers from "./ZoneLayers";
import TrafficSignalLayer from "./TrafficSignalLayer";
import RoadNetworkLayer from "./RoadNetworkLayer";

// --- Fix default icon URLs ---
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

// --- CitySearch component (live search box) ---
function CitySearch() {
  const map = useMap();
  const [city, setCity] = React.useState("");
  const [pos, setPos] = React.useState(null);
  const [label, setLabel] = React.useState("");

  const handleSearch = async () => {
    if (!city.trim()) return;
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          city
        )}`
      );
      const results = await res.json();
      if (!results.length) {
        alert("City not found");
        return;
      }
      const { lat, lon, display_name } = results[0];
      const coords = [parseFloat(lat), parseFloat(lon)];
      map.flyTo(coords, 12);
      setPos(coords);
      setLabel(display_name);
    } catch (e) {
      console.error(e);
      alert("Search failed");
    }
  };

  return (
    <>
      <div className="search-container">
        <input
          className="search-input"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Search city…"
        />
        <button className="search-btn" onClick={handleSearch}>
          Go
        </button>
      </div>
      {pos && (
        <Marker position={pos}>
          <Popup>{label}</Popup>
        </Marker>
      )}
    </>
  );
}

// --- LocationHandler for initial IntroPage locationParams ---
function LocationHandler({ params }) {
  const map = useMap();
  const [markerPos, setMarkerPos] = React.useState(null);
  const [markerLabel, setMarkerLabel] = React.useState("");

  useEffect(() => {
    if (!params) return;
    (async () => {
      switch (params.type) {
        case "BBOX": {
          const { min_lat, min_lon, max_lat, max_lon } = params.bbox;
          map.fitBounds([
            [parseFloat(min_lat), parseFloat(min_lon)],
            [parseFloat(max_lat), parseFloat(max_lon)],
          ]);
          break;
        }
        case "POINT": {
          const lat = parseFloat(params.lat),
            lon = parseFloat(params.lon),
            dist = parseFloat(params.distance);
          map.setView([lat, lon], 14);
          setMarkerPos([lat, lon]);
          setMarkerLabel(`Center @ ${lat}, ${lon}`);
          new L.Circle([lat, lon], { radius: dist }).addTo(map);
          break;
        }
        case "ADDRESS":
        case "PLACE": {
          const query =
            params.type === "ADDRESS" ? params.address : params.place;
          const res = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
              query
            )}`
          );
          const data = await res.json();
          if (!data.length) return alert("Location not found");
          const { lat, lon, display_name } = data[0];
          const L_lat = parseFloat(lat),
            L_lon = parseFloat(lon);
          map.setView([L_lat, L_lon], 14);
          setMarkerPos([L_lat, L_lon]);
          setMarkerLabel(display_name);
          if (params.distance) {
            new L.Circle([L_lat, L_lon], {
              radius: parseFloat(params.distance),
              className: "circle-overlay", // Apply CSS class for styling
            }).addTo(map);
          }
          break;
        }
      }
    })();
  }, [params, map]);

  return markerPos ? (
    <Marker position={markerPos}>
      <Popup>{markerLabel}</Popup>
    </Marker>
  ) : null;
}

// --- Main MapView exports both search + initial-handling + layers ---
export default function MapView({ locationParams, filters, networkGeo, networkVersion }) {
  // Sidebar now passes { layers: string[], featureFilters: {...} }
  const layers = Array.isArray(filters?.layers) ? filters.layers : [];

  return (
    <MapContainer center={[0, 0]} zoom={2} className="map-container">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* initial placement */}
      <LocationHandler params={locationParams} />

      {/* live search */}
      <CitySearch />

      {/* ODD layers */}
      <ZoneLayers filters={layers} />
      <TrafficSignalLayer enabled={layers.includes("traffic_signals")} />
      <JunctionLayer filters={layers} />

      {/* generated network - show filtered network when available, otherwise show all roads */}
      {networkGeo && networkGeo.type === "Feature" ? (
        <GeoJSON
          key={networkVersion}
          data={networkGeo}
          style={{ color: "green", weight: 4 }}
        />
      ) : (
        <RoadNetworkLayer visible={layers.includes("road_features")} />
      )}
    </MapContainer>
  );
}
