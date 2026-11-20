import { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './components/MapView';
import { fetchWalkingRoutes, rankCandidateRoutes, refreshRouteEnvironments } from './services/routingService';
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

  // Environmental Factor Preferences (5 factors + no_preference)
  const [preferences, setPreferences] = useState({
    air_quality: true,
    temperature: false,
    traffic_exposure: false,
    greenery: true,
    walking_distance: true,
    no_preference: false,
  });

  // Departure Time selection (null = Now/Current conditions; or ISO 8601 string)
  const [departureTime, setDepartureTime] = useState(null);

  // Refresh & Re-evaluation tracking states
  const [isRefreshingEnvironment, setIsRefreshingEnvironment] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState(null);
  const [reevaluationData, setReevaluationData] = useState(null);

  // Mode for clicking on the map: 'origin' | 'destination' | 'none'
  const [clickMode, setClickMode] = useState('none');

  // Notification / Alert message toast
  const [notification, setNotification] = useState(null);

  // Routes state: raw routes from provider vs algorithmically ranked routes
  const [rawRoutes, setRawRoutes] = useState([]);
  const [rankingData, setRankingData] = useState(null);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [isLoadingRoutes, setIsLoadingRoutes] = useState(false);
  const [isRanking, setIsRanking] = useState(false);
  const [routeError, setRouteError] = useState(null);

  // Active routes list presented to user (ranked routes when available, else raw)
  const displayedRoutes = rankingData?.ranked_routes && rankingData.ranked_routes.length > 0
    ? rankingData.ranked_routes
    : rawRoutes;

  // Recalculate rankings whenever selections change on existing routes
  const executeRanking = useCallback(async (routesToRank, currentPrefs) => {
    if (!routesToRank || routesToRank.length === 0) {
      setRankingData(null);
      return;
    }

    setIsRanking(true);
    try {
      const result = await rankCandidateRoutes({
        routes: routesToRank,
        preferences: currentPrefs,
      });

      if (result) {
        setRankingData(result);
        if (result.ranked_routes && result.ranked_routes.length > 0) {
          // If previous selection isn't valid, select Rank 1
          setSelectedRouteId((prevId) => {
            const exists = result.ranked_routes.some((r) => r.id === prevId);
            return exists ? prevId : result.ranked_routes[0].id;
          });
        }
      }
    } catch (err) {
      console.warn('Ranking recalculation error:', err);
    } finally {
      setIsRanking(false);
    }
  }, []);

  // Trigger ranking recalculation when preferences change
  const prevPrefsRef = useRef(preferences);
  useEffect(() => {
    if (rawRoutes.length > 0 && JSON.stringify(prevPrefsRef.current) !== JSON.stringify(preferences)) {
      prevPrefsRef.current = preferences;
      executeRanking(rawRoutes, preferences);
    }
  }, [preferences, rawRoutes, executeRanking]);

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
    setRawRoutes([]);
    setRankingData(null);
    setSelectedRouteId(null);
    setRouteError(null);
    setDepartureTime(null);
    setReevaluationData(null);
    setLastRefreshTime(null);
    setPreferences({
      air_quality: false,
      temperature: false,
      traffic_exposure: false,
      greenery: false,
      walking_distance: false,
      no_preference: true,
    });
    setClickMode('none');
    setNotification({
      type: 'info',
      message: 'Map reset. Search or click on the map to choose new start and destination points.',
    });
  };

  const handleClearRoutes = () => {
    setRawRoutes([]);
    setRankingData(null);
    setSelectedRouteId(null);
    setRouteError(null);
    setReevaluationData(null);
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
    setReevaluationData(null);

    try {
      const data = await fetchWalkingRoutes({
        origin,
        destination,
        alternatives: 2,
        departureTime,
      });

      const parsed = data.routes || [];
      setRawRoutes(parsed);

      if (parsed.length > 0) {
        setSelectedRouteId(parsed[0].id);
        const altCount = parsed.length - 1;
        setNotification({
          type: 'info',
          message:
            altCount > 0
              ? `Found ${parsed.length} walking paths (1 primary, ${altCount} alternative${altCount > 1 ? 's' : ''}). Ranking applied.`
              : 'Found 1 walking route (no alternative pedestrian paths identified).',
        });

        // Run multi-criteria ranking on newly calculated routes
        await executeRanking(parsed, preferences);
        setLastRefreshTime(new Date().toLocaleTimeString());
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

  const handleRefreshEnvironment = async () => {
    if (rawRoutes.length === 0) return;

    setIsRefreshingEnvironment(true);
    try {
      const refreshed = await refreshRouteEnvironments({
        routes: rawRoutes,
        preferences,
        departureTime,
        forceRefresh: true,
      });

      if (refreshed?.routes) {
        setRawRoutes(refreshed.routes);
        if (refreshed.ranking) {
          setRankingData(refreshed.ranking);
        }
        if (refreshed.reevaluation) {
          setReevaluationData(refreshed.reevaluation);
        }
        setLastRefreshTime(new Date().toLocaleTimeString());
        setNotification({
          type: 'info',
          message: refreshed.reevaluation?.recommendation_change_note || 'Environmental metrics refreshed.',
        });
      }
    } catch (err) {
      console.error('Refresh error:', err);
      setNotification({
        type: 'warning',
        message: err.message || 'Failed to refresh environmental conditions.',
      });
    } finally {
      setIsRefreshingEnvironment(false);
    }
  };

  const handleSelectRoute = (routeId) => {
    setSelectedRouteId(routeId);
    const chosen = displayedRoutes.find((r) => r.id === routeId);
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
        departureTime={departureTime}
        setDepartureTime={setDepartureTime}
        clickMode={clickMode}
        setClickMode={setClickMode}
        onCalculateRoutes={handleCalculateRoutes}
        onRefreshEnvironment={handleRefreshEnvironment}
        isRefreshing={isRefreshingEnvironment}
        lastRefreshTime={lastRefreshTime}
        reevaluationData={reevaluationData}
        onClearRoutes={handleClearRoutes}
        onReset={handleReset}
        routes={displayedRoutes}
        rankingData={rankingData}
        selectedRouteId={selectedRouteId}
        onSelectRoute={handleSelectRoute}
        isLoadingRoutes={isLoadingRoutes}
        isRanking={isRanking}
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
          routes={displayedRoutes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={handleSelectRoute}
        />
      </main>
    </div>
  );
}
