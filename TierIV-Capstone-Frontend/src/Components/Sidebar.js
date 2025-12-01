// src/Components/Sidebar.js
import React, { useState } from "react";
import "./Sidebar.css";

export default function Sidebar({ onSubmitFilters, onGenerateNetwork }) {
  const OPTIONS = [
    { key: "road_features", label: "Road network" },
    { key: "junction", label: "Junction" },
    { key: "school_zones", label: "School zones" },
    { key: "parking_lot", label: "Parking lots" },
    { key: "traffic_signals", label: "Traffic signals" },
  ];

  const [selected, setSelected] = useState(
    OPTIONS.reduce((acc, o) => ({ ...acc, [o.key]: false }), {})
  );
  const [roadFeatures, setRoadFeatures] = useState([]);
  const [junctionFeatures, setJunctionFeatures] = useState([]);
  const [schoolZoneFeatures, setSchoolZoneFeatures] = useState([]);
  const [parkingLotFeatures, setParkingLotFeatures] = useState([]);
  const [trafficSignalFeatures, setTrafficSignalFeatures] = useState([]);
  const [selectedFeatureValues, setSelectedFeatureValues] = useState({});
  const [roadAnalysisDone, setRoadAnalysisDone] = useState(false);
  const [collapsedFeatures, setCollapsedFeatures] = useState({});
  const [oddType, setOddType] = useState("all"); // Default to "all"

  const toggle = (key) =>
    setSelected((s) => ({ ...s, [key]: !s[key] }));

  const toggleFeatureCollapse = (attr) => {
    setCollapsedFeatures((prev) => ({ ...prev, [attr]: !prev[attr] }));
  };

  // For list-of-strings features
  const handleValueToggle = (attr, val, allValues) => {
    setSelectedFeatureValues((prev) => {
      const arr = prev[attr] || [];
      const stringifiedVal = String(val);

      // Remove "ALL" first to get clean array
      const cleanArr = arr.filter(x => x !== 'ALL');

      let newArr;
      if (cleanArr.includes(stringifiedVal)) {
        // Deselecting: remove the value
        newArr = cleanArr.filter(x => x !== stringifiedVal);
      } else {
        // Selecting: add the value
        newArr = [...cleanArr, stringifiedVal];
      }

      // Only add "ALL" if every individual value is now selected
      const allSelected = allValues.every(v => newArr.includes(String(v)));
      if (allSelected && newArr.length === allValues.length) {
        newArr = ['ALL', ...newArr];
      }

      return { ...prev, [attr]: newArr };
    });
  };

  // Handler for "All" checkbox (for strings)
  const handleSelectAll = (attr, values) => {
    setSelectedFeatureValues((prev) => {
      const curr = prev[attr] || [];
      // Check if ALL is currently selected (and all individual values)
      const allSelected = curr.includes('ALL') && values.every(v => curr.includes(String(v)));

      if (allSelected) {
        // Clear everything
        return { ...prev, [attr]: [] };
      } else {
        // Select all including "ALL"
        return { ...prev, [attr]: ['ALL', ...values.map(v => String(v))] };
      }
    });
  };

  // For boolean features
  const handleBooleanToggle = (attr) => {
    setSelectedFeatureValues((prev) => {
      const current = prev[attr]?.[0] === true; // Check if current value is true
      return { ...prev, [attr]: [!current] }; // Toggle the boolean value
    });
  };

  // For numeric inputs
  const handleNumericInput = (attr, value) => {
    setSelectedFeatureValues((prev) => ({ ...prev, [attr]: [value] })); // Store numeric input as a list
  };

  const fetchRoadFeatures = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/road_features/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      const features = json.feature_dict?.[0]?.features || [];
      setRoadFeatures(features);
    } catch (e) {
      console.error("Road features load failed", e);
      setRoadFeatures([]);
    }
  };

  const fetchJunctionFeatures = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/junction", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      setJunctionFeatures(json.feature_dict?.[0]?.features || []);
    } catch (e) {
      console.error("Junction features load failed", e);
      setJunctionFeatures([]);
    }
  };

  const fetchSchoolZoneFeatures = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/school_zone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      setSchoolZoneFeatures(json.feature_dict?.[0]?.features || []);
    } catch (e) {
      console.error("School zone features load failed", e);
      setSchoolZoneFeatures([]);
    }
  };

  const fetchParkingLotFeatures = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/parking_lot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      setParkingLotFeatures(json.feature_dict?.[0]?.features || []);
    } catch (e) {
      console.error("Parking lot features load failed", e);
      setParkingLotFeatures([]);
    }
  };

  const fetchTrafficSignalFeatures = async () => {
    try {
      const res = await fetch("http://127.0.0.1:5000/traffic_signals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(res.statusText);
      const json = await res.json();
      setTrafficSignalFeatures(json.feature_dict?.[0]?.features || []);
    } catch (e) {
      console.error("Traffic signal features load failed", e);
      setTrafficSignalFeatures([]);
    }
  };

  const handleGenerateNetwork = async () => {
    // Clear previous output (if applicable)
    onGenerateNetwork(null); // Reset the network data before fetching new data

    // Build the body from the selected feature values
    const body = {
      odd_type: oddType, // Use the selected odd_type value
      odd_param: { ...selectedFeatureValues },
    };

    console.log("Generating network with filters:", body);

    try {
      const res = await fetch("http://127.0.0.1:5000/network", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.status === 204) {
        alert("No content returned from the server.");
        return; // Exit gracefully without breaking the code
      }

      if (!res.ok) throw new Error(`Server ${res.status}`);
      const networkGeo = await res.json();
      console.log("Network received:", networkGeo);

      // Check if the response contains a valid GeoJSON Feature or if it's just a message
      if (networkGeo && networkGeo.message) {
        // Backend returned a message (e.g., "No odd compliant network")
        console.log(networkGeo.message);
        alert(networkGeo.message);
        onGenerateNetwork(null); // Clear the network display
      } else if (networkGeo && networkGeo.type === "Feature") {
        // Valid GeoJSON Feature
        onGenerateNetwork(networkGeo);
      } else {
        // Unexpected response format
        console.warn("Unexpected network response format:", networkGeo);
        onGenerateNetwork(null);
      }
    } catch (err) {
      console.error("Network generation failed:", err);
      alert("Failed to generate network");
    }
  };

  const handleSubmit = async () => {
    const layers = OPTIONS.filter((o) => selected[o.key]).map((o) => o.key);

    if (layers.includes("road_features")) {
      await fetchRoadFeatures();
      setRoadAnalysisDone(true);
      // Auto-generate network when road features are selected
      await handleGenerateNetwork();
    } else {
      setRoadFeatures([]);
      setRoadAnalysisDone(false);
      onGenerateNetwork(null); // Clear network if road features are unchecked
    }
    if (layers.includes("junction")) {
      await fetchJunctionFeatures();
    } else {
      setJunctionFeatures([]);
    }
    if (layers.includes("school_zones")) { // Fixed typo: school_zone -> school_zones
      await fetchSchoolZoneFeatures();
    } else {
      setSchoolZoneFeatures([]);
    }
    if (layers.includes("parking_lot")) {
      await fetchParkingLotFeatures();
    } else {
      setParkingLotFeatures([]);
    }
    if (layers.includes("traffic_signals")) {
      await fetchTrafficSignalFeatures();
    } else {
      setTrafficSignalFeatures([]);
    }

    onSubmitFilters({
      layers,
      featureFilters: selectedFeatureValues,
    });
  };

  const style = (str) => {
    const updated = str.toLowerCase().replace("_", " ");
    return updated.charAt(0).toUpperCase() + updated.slice(1);
  };

  const renderFeatureFilters = (features) =>
    features.map(({ feature_attr, values }) => {
      const normalized = Array.isArray(values) ? values : [values];

      return (
        <div key={feature_attr} className="feature-filter">
          <div
            className="feature-filter-header"
            onClick={() => toggleFeatureCollapse(feature_attr)}
          >
            <strong>{style(feature_attr)}</strong>
            <span>{collapsedFeatures[feature_attr] ? "+" : "-"}</span>
          </div>
          {!collapsedFeatures[feature_attr] && (
            <div className="feature-filter-body">

              {/* Empty list: Allow dynamic numeric input */}
              {normalized.length === 0 && (
                <div className="feature-numeric">
                  <label>{style(feature_attr)}</label>
                  <input
                    type="number"
                    placeholder="Enter numeric value"
                    value={selectedFeatureValues[feature_attr]?.[0] || ''}
                    onChange={(e) =>
                      handleNumericInput(feature_attr, Number(e.target.value))
                    }
                  />
                </div>
              )}

              {/* String list: Show "All" + individual checkboxes */}
              {normalized.length > 0 && normalized.every(v => typeof v === 'string') && (
                <>
                  <label className="feature-checkbox">
                    <input
                      type="checkbox"
                      checked={(selectedFeatureValues[feature_attr] || []).includes('ALL')}
                      onChange={() => handleSelectAll(feature_attr, normalized)}
                    />
                    All
                  </label>
                  {normalized.map(v => (
                    <label key={`${feature_attr}-${v}`} className="feature-checkbox">
                      <input
                        type="checkbox"
                        checked={(selectedFeatureValues[feature_attr] || []).includes(String(v))}
                        onChange={() => handleValueToggle(feature_attr, v, normalized)}
                      />
                      {style(v)}
                    </label>
                  ))}
                </>
              )}

              {/* Boolean list: Show single checkbox */}
              {normalized.length > 0 && normalized.every(v => typeof v === 'boolean') && (
                <label className="feature-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedFeatureValues[feature_attr]?.[0] === true} // Check for boolean true, not string 'True'
                    onChange={() => handleBooleanToggle(feature_attr)}
                  />
                  {style(feature_attr)}
                </label>
              )}

            </div>
          )}
        </div>
      );
    });

  return (
    <div className="sidebar">
      <h3>ODD Attributes</h3>

      {OPTIONS.map((opt) => (
        <label key={opt.key} className="sidebar-checkbox">
          <input
            type="checkbox"
            checked={selected[opt.key]}
            onChange={() => toggle(opt.key)}
          />
          {opt.label}
        </label>
      ))}

      <button className="sidebar-submit" onClick={handleSubmit}>
        Submit Filters
      </button>

      {roadAnalysisDone && (
        <label className="odd-type-dropdown">
          <span>Select ODD Type:</span>
          <select
            value={oddType}
            onChange={(e) => setOddType(e.target.value)}
          >
            <option value="all">All</option>
            <option value="predefined">Predefined</option>
            <option value="live">Live</option>
          </select>
        </label>
      )}

      {roadFeatures.length > 0 && (
        <div className="feature-filters">
          <h4>Road Feature Filters</h4>
          {renderFeatureFilters(roadFeatures)}
        </div>
      )}

      {junctionFeatures.length > 0 && (
        <div className="feature-filters">
          <h4>Junction Feature Filters</h4>
          {renderFeatureFilters(junctionFeatures)}
        </div>
      )}

      {schoolZoneFeatures.length > 0 && (
        <div className="feature-filters">
          <h4>School Zone Feature Filters</h4>
          {renderFeatureFilters(schoolZoneFeatures)}
        </div>
      )}

      {parkingLotFeatures.length > 0 && (
        <div className="feature-filters">
          <h4>Parking Lot Feature Filters</h4>
          {renderFeatureFilters(parkingLotFeatures)}
        </div>
      )}

      {trafficSignalFeatures.length > 0 && (
        <div className="feature-filters">
          <h4>Traffic Signal Feature Filters</h4>
          {renderFeatureFilters(trafficSignalFeatures)}
        </div>
      )}

      {roadAnalysisDone && (
        <button className="sidebar-network" onClick={handleGenerateNetwork}>
          Generate Network
        </button>
      )}
    </div>
  );
}
