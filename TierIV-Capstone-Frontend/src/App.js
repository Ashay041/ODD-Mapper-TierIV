import React, { useState } from "react";
import Sidebar from "./Components/Sidebar";
import MapView from "./Components/MapView";
import IntroPage from "./Components/IntroPage";

import "./App.css";

function App() {
  // null until the user has submitted their location
  const [locationParams, setLocationParams] = useState(null);
  // sidebar's filters button
  const [activeFilters, setActiveFilters] = useState([]);
  // store the GeoJSON LineString returned by /network
  const [networkGeo, setNetworkGeo] = useState(null);
  // counter to force re-render when network updates
  const [networkVersion, setNetworkVersion] = useState(0);

  // called by IntroPage when the user clicks Submit
  const handleLocationSubmit = (params) => {
    setLocationParams(params);
  };

  // if no location yet, show the intro form
  if (!locationParams) {
    return <IntroPage onSubmit={handleLocationSubmit} />;
  }

  // handler for network generation that increments version
  const handleGenerateNetwork = (geo) => {
    setNetworkGeo(geo);
    setNetworkVersion((v) => v + 1);
  };

  // once we have input, render the map UI
  return (
    <div className="app-container">
      <div className="main-content">
        <Sidebar
          onSubmitFilters={setActiveFilters}
          onGenerateNetwork={handleGenerateNetwork}
        />
        <MapView
          locationParams={locationParams}
          filters={activeFilters}
          networkGeo={networkGeo}
          networkVersion={networkVersion}
        />
      </div>
    </div>
  );
}

export default App;
