import { useState } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './components/MapView';
import { fetchWalkingRoutes } from './services/routingService';
import './App.css';

export default function App() {
  // Coordinates default to London central demo area
  const [origin, setOrigin] = useState({
    lat: 51.5138,
    lon: -0.0984,
    label: "St. Paul's Cathedral, London",
  });

  const [destination, setDestination] = useState({
    lat: 51.5081,
    lon: -0.0759,
    label: 'Tower of London',
  });

  // Environmental Factor Preferences (preserved for next phase)
  const [preferences, setPreferences] = useState({
    air_quality: true,
    greenery: true,
    temperature: false,
    walking_distance: true,
    traffic_safety: false,
  });

  // Mode for clicking on the map: 'origin' | 'destination' | 'none'
  const [clickMode, setClickMode] = useState('none');

  // Notification / Alert message toast
  const [notification, setNotification] = useState(null);

  // Routes state
  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [isLoadingRoutes, setIsLoadingRoutes] = useState(false);
  const [routeError, setRouteError] = useState(null);

  // Handle click on Leaflet map canvas
  const handleMapClick = (lat, lon) => {
    const formattedCoord = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
    if (clickMode === 'origin') {
      setOrigin({ lat, lon, label: `Selected Start: ${formattedCoord}` });
      setClickMode('none');
    } else if (clickMode === 'destination') {
      setDestination({ lat, lon, label: `Selected Destination: ${formattedCoord}` });
      setClickMode('none');
    } else {
      // If no mode active: set origin if null, otherwise set destination
      if (!origin) {
        setOrigin({ lat, lon, label: `Point A: ${formattedCoord}` });
      } else {
        setDestination({ lat, lon, label: `Point B: ${formattedCoord}` });
      }
    }
  };

  const handleReset = () => {
    setOrigin(null);
    setDestination(null);
    setRoutes([]);
    setSelectedRouteId(null);
    setRouteError(null);
    setPreferences({
      air_quality: false,
      greenery: false,
      temperature: false,
      walking_distance: false,
      traffic_safety: false,
    });
    setClickMode('none');
    setNotification({
      type: 'info',
      message: 'Map reset. Search or click on the map to choose new start and destination points.',
    });
  };

  const handleClearRoutes = () => {
    setRoutes([]);
    setSelectedRouteId(null);
    setRouteError(null);
  };

  const handleCalculateRoutes = async () => {
    if (!origin || !destination) {
      setNotification({
        type: 'warning',
        message: 'Please define both Start (A) and Destination (B) points before generating routes.',
      });
      return;
    }

    setIsLoadingRoutes(true);
    setRouteError(null);

    try {
      const data = await fetchWalkingRoutes({
        origin,
        destination,
        alternatives: 2,
      });

      setRoutes(data.routes);
      if (data.routes.length > 0) {
        setSelectedRouteId(data.routes[0].id);
        const altCount = data.routes.length - 1;
        setNotification({
          type: 'info',
          message:
            altCount > 0
              ? `Found ${data.routes.length} walking paths (1 primary, ${altCount} alternative${altCount > 1 ? 's' : ''}).`
              : 'Found 1 walking route (no alternative pedestrian paths identified).',
        });
      } else {
        setRouteError('No walking routes returned by routing provider.');
      }
    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch walking routes.';
      setRouteError(errorMsg);
      setNotification({
        type: 'warning',
        message: errorMsg,
      });
    } finally {
      setIsLoadingRoutes(false);
    }
  };

  const handleSelectRoute = (routeId) => {
    setSelectedRouteId(routeId);
    const chosen = routes.find((r) => r.id === routeId);
    if (chosen) {
      setNotification({
        type: 'info',
        message: `Selected ${chosen.name} (${chosen.distance_km} km, ~${Math.round(chosen.duration_min)} mins).`,
      });
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar Controls & Parameters */}
      <Sidebar
        origin={origin}
        setOrigin={setOrigin}
        destination={destination}
        setDestination={setDestination}
        preferences={preferences}
        setPreferences={setPreferences}
        clickMode={clickMode}
        setClickMode={setClickMode}
        onCalculateRoutes={handleCalculateRoutes}
        onClearRoutes={handleClearRoutes}
        onReset={handleReset}
        routes={routes}
        selectedRouteId={selectedRouteId}
        onSelectRoute={handleSelectRoute}
        isLoadingRoutes={isLoadingRoutes}
        routeError={routeError}
      />

      {/* Main Interactive Map Canvas */}
      <main className="map-area">
        {notification && (
          <div className={`toast-notification ${notification.type}`}>
            <div className="toast-text">{notification.message}</div>
            <button
              className="toast-close"
              onClick={() => setNotification(null)}
              aria-label="Close notification"
            >
              &times;
            </button>
          </div>
        )}

        <MapView
          origin={origin}
          destination={destination}
          onMapClick={handleMapClick}
          clickMode={clickMode}
          routes={routes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={handleSelectRoute}
        />
      </main>
    </div>
  );
}
