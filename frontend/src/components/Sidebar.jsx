import { useState, useEffect } from 'react';
import {
  MapPin,
  Navigation,
  Wind,
  Thermometer,
  TreePine,
  Footprints,
  ShieldCheck,
  Search,
  RotateCcw,
  Info,
  Layers,
  X,
  AlertCircle,
  Clock,
  Compass,
  Award,
  CheckCircle2,
  AlertTriangle,
  Scale,
  SlidersHorizontal,
  RefreshCw,
  Calendar,
  ChevronDown,
  ChevronUp,
  CornerUpLeft,
  CornerUpRight,
  ArrowUp,
  Milestone,
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import EnvironmentalPanel from './EnvironmentalPanel';
import RouteComparisonTable from './RouteComparisonTable';
import { searchLocations } from '../services/geocodingService';

export default function Sidebar({
  origin,
  setOrigin,
  destination,
  setDestination,
  preferences,
  setPreferences,
  departureTime = null,
  setDepartureTime = () => {},
  clickMode,
  setClickMode,
  onCalculateRoutes,
  onRefreshEnvironment = null,
  isRefreshing = false,
  lastRefreshTime = null,
  reevaluationData = null,
  onClearRoutes,
  onReset,
  routes = [],
  rankingData = null,
  selectedRouteId = null,
  onSelectRoute = () => {},
  isLoadingRoutes = false,
  isRanking = false,
  routeError = null,
}) {
  const [originSearchText, setOriginSearchText] = useState(origin?.label || '');
  const [destSearchText, setDestSearchText] = useState(destination?.label || '');
  const [prevOrigin, setPrevOrigin] = useState(origin);
  const [prevDest, setPrevDest] = useState(destination);

  const [originSuggestions, setOriginSuggestions] = useState([]);
  const [destSuggestions, setDestSuggestions] = useState([]);
  const [isSearchingOrigin, setIsSearchingOrigin] = useState(false);
  const [isSearchingDest, setIsSearchingDest] = useState(false);
  const [originNoResults, setOriginNoResults] = useState(false);
  const [destNoResults, setDestNoResults] = useState(false);
  const [expandedStepsRouteId, setExpandedStepsRouteId] = useState(null);

  // Synchronize state during rendering when prop changes (official React recommended pattern)
  if (origin !== prevOrigin) {
    setPrevOrigin(origin);
    setOriginSearchText(origin?.label || '');
  }

  if (destination !== prevDest) {
    setPrevDest(destination);
    setDestSearchText(destination?.label || '');
  }

  // Debounced geocoding search for Origin
  useEffect(() => {
    if (!originSearchText || originSearchText === origin?.label || originSearchText.trim().length < 3) {
      return;
    }

    const abortController = new AbortController();
    const timer = setTimeout(async () => {
      setIsSearchingOrigin(true);
      setOriginNoResults(false);
      try {
        const results = await searchLocations(originSearchText, abortController.signal);
        setOriginSuggestions(results);
        setOriginNoResults(results.length === 0);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setOriginSuggestions([]);
        }
      } finally {
        setIsSearchingOrigin(false);
      }
    }, 450);

    return () => {
      clearTimeout(timer);
      abortController.abort();
    };
  }, [originSearchText, origin?.label]);

  // Debounced geocoding search for Destination
  useEffect(() => {
    if (!destSearchText || destSearchText === destination?.label || destSearchText.trim().length < 3) {
      return;
    }

    const abortController = new AbortController();
    const timer = setTimeout(async () => {
      setIsSearchingDest(true);
      setDestNoResults(false);
      try {
        const results = await searchLocations(destSearchText, abortController.signal);
        setDestSuggestions(results);
        setDestNoResults(results.length === 0);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setDestSuggestions([]);
        }
      } finally {
        setIsSearchingDest(false);
      }
    }, 450);

    return () => {
      clearTimeout(timer);
      abortController.abort();
    };
  }, [destSearchText, destination?.label]);

  // Derived suggestions based on current query validity
  const validOriginSuggestions =
    originSearchText && originSearchText.trim().length >= 3 && originSearchText !== origin?.label
      ? originSuggestions
      : [];

  const validDestSuggestions =
    destSearchText && destSearchText.trim().length >= 3 && destSearchText !== destination?.label
      ? destSuggestions
      : [];

  const selectOriginSuggestion = (item) => {
    setOrigin({
      lat: item.lat,
      lon: item.lon,
      label: item.displayName,
    });
    setOriginSearchText(item.displayName);
    setOriginSuggestions([]);
    setOriginNoResults(false);
  };

  const selectDestSuggestion = (item) => {
    setDestination({
      lat: item.lat,
      lon: item.lon,
      label: item.displayName,
    });
    setDestSearchText(item.displayName);
    setDestSuggestions([]);
    setDestNoResults(false);
  };

  const handleClearOrigin = () => {
    setOrigin(null);
    setOriginSearchText('');
    setOriginSuggestions([]);
    setOriginNoResults(false);
  };

  const handleClearDest = () => {
    setDestination(null);
    setDestSearchText('');
    setDestSuggestions([]);
    setDestNoResults(false);
  };

  // Quick preset test locations
  const presets = [
    {
      name: 'London: St Pauls to Tower',
      origin: { lat: 51.5138, lon: -0.0984, label: "St. Paul's Cathedral, London" },
      dest: { lat: 51.5081, lon: -0.0759, label: 'Tower of London' },
    },
    {
      name: 'NYC: Central Park to Times Sq',
      origin: { lat: 40.7648, lon: -73.973, label: 'Central Park South, New York' },
      dest: { lat: 40.758, lon: -73.9855, label: 'Times Square, New York' },
    },
  ];

  const handleApplyPreset = (preset) => {
    setOrigin(preset.origin);
    setDestination(preset.dest);
    setOriginSuggestions([]);
    setDestSuggestions([]);
    setOriginNoResults(false);
    setDestNoResults(false);
  };

  const handleToggleNoPreference = () => {
    setPreferences((prev) => {
      const willBeNoPref = !prev.no_preference;
      if (willBeNoPref) {
        return {
          air_quality: false,
          temperature: false,
          traffic_exposure: false,
          greenery: false,
          walking_distance: false,
          no_preference: true,
        };
      } else {
        return {
          air_quality: true,
          temperature: false,
          traffic_exposure: false,
          greenery: true,
          walking_distance: true,
          no_preference: false,
        };
      }
    });
  };

  const togglePreference = (key) => {
    setPreferences((prev) => {
      const wasNoPref = !!prev.no_preference;
      const currentVal = wasNoPref ? false : !!prev[key];
      const newVal = !currentVal;

      const updated = {
        ...prev,
        no_preference: false,
        [key]: newVal,
      };

      // Check if all individual factors became false
      const anyActive = ['air_quality', 'temperature', 'traffic_exposure', 'greenery', 'walking_distance'].some(
        (f) => updated[f]
      );
      if (!anyActive) {
        updated.no_preference = true;
      }

      return updated;
    });
  };

  const preferenceItems = [
    {
      id: 'air_quality',
      label: 'Air Quality',
      subtitle: 'Lower EAQI & PM2.5 particulates',
      icon: Wind,
      color: '#3b82f6',
      source: 'Copernicus CAMS (~11 km grid)',
      direction: 'Lower is better',
    },
    {
      id: 'temperature',
      label: 'Temperature / Heat',
      subtitle: 'Lower apparent heat stress',
      icon: Thermometer,
      color: '#f59e0b',
      source: 'ECMWF / ICON NWP',
      direction: 'Lower is better',
    },
    {
      id: 'traffic_exposure',
      label: 'Traffic Exposure',
      subtitle: 'Lower motor vehicle corridor proximity',
      icon: ShieldCheck,
      color: '#ec4899',
      source: 'OSM Infrastructure Hierarchy',
      direction: 'Lower is better',
    },
    {
      id: 'greenery',
      label: 'Greenery & Parks',
      subtitle: 'Higher park presence & tree canopies',
      icon: TreePine,
      color: '#10b981',
      source: 'OSM Overpass green buffers',
      direction: 'Higher is better',
    },
    {
      id: 'walking_distance',
      label: 'Walking Distance',
      subtitle: 'Shortest direct pedestrian path',
      icon: Footprints,
      color: '#8b5cf6',
      source: 'OpenRouteService foot-walking',
      direction: 'Lower is better',
    },
  ];

  const activeFactorsList = ['air_quality', 'temperature', 'traffic_exposure', 'greenery', 'walking_distance'].filter(
    (k) => !preferences.no_preference && preferences[k]
  );
  const activePreferencesCount = activeFactorsList.length;

  return (
    <aside className="sidebar-container">
      {/* Brand Header */}
      <div className="brand-header">
        <div className="brand-logo-title">
          <div className="brand-icon-wrapper">
            <Footprints size={24} className="brand-icon" />
          </div>
          <div>
            <h1 className="brand-title">EcoWalk</h1>
            <p className="brand-tagline">AI-Driven Multi-Environmental Pedestrian Routing</p>
          </div>
        </div>
      </div>

      {/* Backend Status Check */}
      <StatusBadge />

      <div className="sidebar-scrollable-content">
        {/* Step 1: Waypoints Section */}
        <section className="control-section">
          <div className="section-header">
            <div className="section-title-wrap">
              <span className="step-num">1</span>
              <h2 className="section-title">Waypoints & Geocoding</h2>
            </div>
            <div className="click-mode-selector">
              <button
                type="button"
                className={`btn-mode-toggle ${clickMode === 'origin' ? 'active green' : ''}`}
                onClick={() => setClickMode(clickMode === 'origin' ? 'none' : 'origin')}
                title="Click on map to place Start point"
              >
                Set A on Map
              </button>
              <button
                type="button"
                className={`btn-mode-toggle ${clickMode === 'destination' ? 'active red' : ''}`}
                onClick={() => setClickMode(clickMode === 'destination' ? 'none' : 'destination')}
                title="Click on map to place Destination"
              >
                Set B on Map
              </button>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="presets-bar">
            <span className="presets-label">Demo Presets:</span>
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="btn-preset-chip"
                onClick={() => handleApplyPreset(p)}
              >
                {p.name}
              </button>
            ))}
          </div>

          {/* Origin Input */}
          <div className="input-group">
            <label className="input-label">
              <span className="origin-marker-dot">A</span>
              Start Location (Origin)
            </label>
            <div className="search-input-wrapper">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search address or click on map..."
                className="text-input"
                value={originSearchText}
                onChange={(e) => setOriginSearchText(e.target.value)}
              />
              {originSearchText && (
                <button
                  type="button"
                  className="input-clear-btn"
                  onClick={handleClearOrigin}
                  aria-label="Clear origin"
                >
                  <X size={14} />
                </button>
              )}
              {isSearchingOrigin && <div className="mini-loader"></div>}
            </div>

            {/* Origin Suggestions Dropdown */}
            {validOriginSuggestions.length > 0 && (
              <ul className="suggestions-list">
                {validOriginSuggestions.map((item, i) => (
                  <li
                    key={item.placeId || i}
                    className="suggestion-item"
                    onClick={() => selectOriginSuggestion(item)}
                  >
                    <MapPin size={14} className="suggestion-icon" />
                    <div className="suggestion-text">
                      <span className="suggestion-name">{item.displayName}</span>
                      <small className="suggestion-coords">
                        {item.lat.toFixed(4)}, {item.lon.toFixed(4)}
                      </small>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {originNoResults && (
              <div className="no-suggestions-hint">
                <AlertCircle size={14} />
                <span>No matching locations found. Try a different city or street name.</span>
              </div>
            )}
          </div>

          {/* Destination Input */}
          <div className="input-group">
            <label className="input-label">
              <span className="dest-marker-dot">B</span>
              Destination
            </label>
            <div className="search-input-wrapper">
              <Search size={16} className="search-icon" />
              <input
                type="text"
                placeholder="Search destination or click on map..."
                className="text-input"
                value={destSearchText}
                onChange={(e) => setDestSearchText(e.target.value)}
              />
              {destSearchText && (
                <button
                  type="button"
                  className="input-clear-btn"
                  onClick={handleClearDest}
                  aria-label="Clear destination"
                >
                  <X size={14} />
                </button>
              )}
              {isSearchingDest && <div className="mini-loader"></div>}
            </div>

            {/* Destination Suggestions Dropdown */}
            {validDestSuggestions.length > 0 && (
              <ul className="suggestions-list">
                {validDestSuggestions.map((item, i) => (
                  <li
                    key={item.placeId || i}
                    className="suggestion-item"
                    onClick={() => selectDestSuggestion(item)}
                  >
                    <MapPin size={14} className="suggestion-icon" />
                    <div className="suggestion-text">
                      <span className="suggestion-name">{item.displayName}</span>
                      <small className="suggestion-coords">
                        {item.lat.toFixed(4)}, {item.lon.toFixed(4)}
                      </small>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {destNoResults && (
              <div className="no-suggestions-hint">
                <AlertCircle size={14} />
                <span>No matching locations found. Try a different landmark or address.</span>
              </div>
            )}
          </div>
        </section>

        {/* Departure Time & Temporal Forecast Section */}
        <section className="control-section departure-time-section">
          <div className="section-header">
            <div className="section-title-wrap">
              <Clock size={16} className="text-primary" />
              <h3 className="section-title">Departure Time & Forecast</h3>
            </div>
            <span className={`time-badge-pill ${departureTime ? 'forecast' : 'now'}`}>
              {departureTime ? 'Forecast Model' : 'Current Conditions (Now)'}
            </span>
          </div>

          <div className="time-quick-presets">
            <button
              type="button"
              className={`time-preset-btn ${!departureTime ? 'active' : ''}`}
              onClick={() => setDepartureTime(null)}
            >
              Now
            </button>
            <button
              type="button"
              className="time-preset-btn"
              onClick={() => {
                const d = new Date(Date.now() + 3600 * 1000);
                d.setMinutes(0, 0, 0);
                setDepartureTime(d.toISOString());
              }}
            >
              +1 Hr
            </button>
            <button
              type="button"
              className="time-preset-btn"
              onClick={() => {
                const d = new Date(Date.now() + 3 * 3600 * 1000);
                d.setMinutes(0, 0, 0);
                setDepartureTime(d.toISOString());
              }}
            >
              +3 Hrs
            </button>
            <button
              type="button"
              className="time-preset-btn"
              onClick={() => {
                const d = new Date(Date.now() + 6 * 3600 * 1000);
                d.setMinutes(0, 0, 0);
                setDepartureTime(d.toISOString());
              }}
            >
              +6 Hrs
            </button>
          </div>

          <div className="custom-time-picker-wrap">
            <label className="input-label-sm">
              <Calendar size={13} className="inline-icon" /> Specific Departure:
            </label>
            <input
              type="datetime-local"
              className="datetime-input"
              value={departureTime ? departureTime.slice(0, 16) : ''}
              onChange={(e) => {
                if (e.target.value) {
                  const iso = new Date(e.target.value).toISOString();
                  setDepartureTime(iso);
                } else {
                  setDepartureTime(null);
                }
              }}
            />
          </div>

          {departureTime && (
            <div className="time-info-note">
              <Info size={13} />
              <span>
                Queries Open-Meteo gridded forecast model for the selected hour.
                Live traffic speed flow is unavailable for future hours.
              </span>
            </div>
          )}
        </section>

        {/* Action Controls for Route Calculation & Environmental Refresh */}
        <section className="actions-section">
          <button
            type="button"
            className="btn-primary"
            onClick={onCalculateRoutes}
            disabled={isLoadingRoutes || !origin || !destination}
          >
            {isLoadingRoutes ? (
              <>
                <div className="button-loader"></div>
                <span>Finding Walking Routes...</span>
              </>
            ) : (
              <>
                <Navigation size={18} />
                <span>Find Walking Routes</span>
              </>
            )}
          </button>

          {routes.length > 0 && onRefreshEnvironment && (
            <button
              type="button"
              className="btn-refresh-env"
              onClick={onRefreshEnvironment}
              disabled={isRefreshing || isLoadingRoutes}
              title="Refresh environmental metrics and recalculate rankings without re-querying route geometry"
            >
              {isRefreshing ? (
                <>
                  <div className="button-loader"></div>
                  <span>Refreshing Environmental Data...</span>
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  <span>Refresh Environmental Data</span>
                </>
              )}
            </button>
          )}

          {(routes.length > 0 || routeError) && (
            <button
              type="button"
              className="btn-secondary"
              onClick={onClearRoutes}
            >
              <RotateCcw size={16} />
              <span>Clear Routes</span>
            </button>
          )}
        </section>

        {/* Error Notification Banner */}
        {routeError && (
          <div className="route-error-card">
            <div className="error-card-header">
              <AlertCircle size={18} className="text-danger" />
              <h4>Route Request Error</h4>
            </div>
            <p className="error-card-msg">{routeError}</p>
            {routeError.includes('ORS_API_KEY') && (
              <div className="error-card-tip">
                <strong>💡 Setup Tip:</strong> Add your free OpenRouteService API key to{' '}
                <code>backend/.env</code> as <code>ORS_API_KEY=your_key</code> and restart the backend.
              </div>
            )}
          </div>
        )}

        {/* Route Cards Display */}
        {routes.length > 0 && (
          <section className="control-section route-cards-section">
            <div className="section-header">
              <div className="section-title-wrap">
                <Compass size={18} className="text-primary" />
                <h2 className="section-title">Walking Routes ({routes.length})</h2>
              </div>
              <span className="badge-count">
                {isRanking ? 'Recalculating...' : `${routes.length} Evaluated`}
              </span>
            </div>

            {/* Freshness Timestamp Callout */}
            {lastRefreshTime && (
              <div className="freshness-callout-bar">
                <Clock size={13} className="text-muted inline-icon" />
                <span>Last Refreshed: {lastRefreshTime}</span>
              </div>
            )}

            {/* Stale Cache Notice Banner */}
            {routes.some((r) => r.environment?.is_stale || r.timestamps?.is_stale) && (
              <div className="sidebar-stale-alert">
                <AlertTriangle size={15} className="text-warning inline-icon" />
                <span>
                  <strong>Stale Data Notice:</strong> Upstream provider request failed during refresh; displaying retained previous measurements.
                </span>
              </div>
            )}

            {/* Environmental Re-evaluation Diff Card */}
            {reevaluationData && (
              <div className="reevaluation-card">
                <div className="reevaluation-header">
                  <RefreshCw size={15} className="text-primary" />
                  <h4>Environmental Re-evaluation Result</h4>
                </div>
                <div className={`reevaluation-badge ${reevaluationData.recommendation_changed ? 'changed' : 'steady'}`}>
                  {reevaluationData.recommendation_change_note}
                </div>
                {reevaluationData.metric_changes && reevaluationData.metric_changes.length > 0 ? (
                  <div className="reevaluation-changes-box">
                    <span className="changes-title">Detected Metric Fluctuations:</span>
                    <ul className="changes-list">
                      {reevaluationData.metric_changes.map((ch, chIdx) => (
                        <li key={chIdx}>
                          <span className="change-route-name">{ch.route_name}:</span> {ch.change_summary}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="reevaluation-steady-text">
                    No significant metric fluctuations detected across route corridor.
                  </p>
                )}
                <div className="reevaluation-disclaimer">
                  ℹ️ {reevaluationData.disclaimer}
                </div>
              </div>
            )}

            {routes.length === 1 && (
              <div className="honest-notice-banner">
                <Info size={15} />
                <span>
                  Single walking route returned. OpenRouteService identified no alternative pedestrian paths for this specific distance/corridor.
                </span>
              </div>
            )}

            {/* Warnings regarding unavailable factors or withheld recommendations */}
            {rankingData?.warnings && rankingData.warnings.length > 0 && (
              <div className="ranking-warnings-card">
                <div className="warning-card-header">
                  <AlertTriangle size={16} className="text-warning" />
                  <span>Data Completeness Notice</span>
                </div>
                <ul className="warning-list">
                  {rankingData.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="routes-list">
              {routes.map((route, idx) => {
                const isSelected = route.id === selectedRouteId;
                const isRec = !!route.is_recommended;
                const isDom = !!route.is_pareto_dominated;
                const rankNum = route.rank || idx + 1;

                return (
                  <div
                    key={route.id}
                    className={`route-card ${isSelected ? 'selected' : ''} ${isRec ? 'card-recommended' : ''} ${isDom ? 'card-dominated' : ''}`}
                    onClick={() => onSelectRoute(route.id)}
                    style={{ borderLeftColor: route.color }}
                  >
                    <div className="route-card-header">
                      <div className="route-card-title-group">
                        <span
                          className="route-color-indicator"
                          style={{ backgroundColor: route.color }}
                        />
                        <h3 className="route-name">{route.name}</h3>
                      </div>
                      <div className="route-badges-wrap">
                        <span className="route-rank-pill">Rank #{rankNum}</span>
                        {isRec ? (
                          <span className="route-type-badge recommended">
                            <Award size={12} /> Recommended
                          </span>
                        ) : isDom ? (
                          <span className="route-type-badge dominated">
                            <AlertTriangle size={12} /> Dominated
                          </span>
                        ) : (
                          <span className="route-type-badge pareto">
                            <CheckCircle2 size={12} /> Pareto-Optimal
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Overall Score */}
                    {typeof route.multi_criteria_score === 'number' && (
                      <div className="route-score-bar">
                        <span className="score-label">Multi-Criteria Score:</span>
                        <strong className="score-val">{route.multi_criteria_score.toFixed(2)}</strong>
                        <small className="score-max">/ 1.00</small>
                      </div>
                    )}

                    <div className="route-card-metrics">
                      <div className="metric-chip">
                        <Footprints size={14} className="metric-icon" />
                        <span className="metric-val">{route.distance_km} km</span>
                        <small className="metric-sub">({Math.round(route.distance_m)} m)</small>
                      </div>
                      <div className="metric-chip">
                        <Clock size={14} className="metric-icon" />
                        <span className="metric-val">{Math.round(route.duration_min)} min</span>
                        <small className="metric-sub">walk</small>
                      </div>

                      {/* Preference-specific quick metric chips */}
                      {(!preferences?.no_preference && preferences?.air_quality) && route.environment?.air_quality?.european_aqi?.value !== null && route.environment?.air_quality?.european_aqi?.value !== undefined && (
                        <div className="metric-chip" title="European Air Quality Index">
                          <Wind size={14} className="metric-icon text-primary" />
                          <span className="metric-val">{route.environment.air_quality.european_aqi.value} EAQI</span>
                          <small className="metric-sub">air</small>
                        </div>
                      )}

                      {(!preferences?.no_preference && preferences?.temperature) && route.environment?.weather?.temperature_c !== null && route.environment?.weather?.temperature_c !== undefined && (
                        <div className="metric-chip" title="Ambient Temperature">
                          <Thermometer size={14} className="metric-icon text-warning" />
                          <span className="metric-val">{route.environment.weather.temperature_c}°C</span>
                          <small className="metric-sub">temp</small>
                        </div>
                      )}

                      {(!preferences?.no_preference && preferences?.greenery) && route.environment?.greenery?.score !== null && route.environment?.greenery?.score !== undefined && (
                        <div className="metric-chip" title="Greenery Buffer Score">
                          <TreePine size={14} className="metric-icon text-success" />
                          <span className="metric-val">{Math.round(route.environment.greenery.score)}%</span>
                          <small className="metric-sub">green</small>
                        </div>
                      )}

                      {(!preferences?.no_preference && preferences?.traffic_exposure) && route.environment?.traffic_exposure?.score !== null && route.environment?.traffic_exposure?.score !== undefined && (
                        <div className="metric-chip" title="Traffic Exposure Index">
                          <ShieldCheck size={14} className="metric-icon text-secondary" />
                          <span className="metric-val">{Math.round(route.environment.traffic_exposure.score)}/100</span>
                          <small className="metric-sub">traffic</small>
                        </div>
                      )}
                    </div>

                    {/* Trade-off summary banner */}
                    {route.trade_offs && (
                      <div className="route-tradeoff-box">
                        <strong>Trade-Off:</strong> <span>{route.trade_offs}</span>
                      </div>
                    )}

                    {/* Reasons list */}
                    {route.reasons && route.reasons.length > 0 && (
                      <div className="route-reasons-box">
                        <span className="reasons-title">Ranking Breakdown:</span>
                        <ul className="reasons-list">
                          {route.reasons.map((rText, rIdx) => (
                            <li key={rIdx}>{rText}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Real Environmental Data Panel filtered by user preferences */}
                    <EnvironmentalPanel environment={route.environment} preferences={preferences} />

                    {/* Turn-by-Turn Walking Directions Accordion */}
                    <div className="route-steps-section">
                      <button
                        type="button"
                        className={`route-steps-toggle ${expandedStepsRouteId === route.id ? 'open' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedStepsRouteId(expandedStepsRouteId === route.id ? null : route.id);
                        }}
                        aria-expanded={expandedStepsRouteId === route.id}
                      >
                        <div className="route-steps-toggle-label">
                          <Milestone size={13} className="route-steps-icon" />
                          <span>Walking Directions</span>
                          {route.steps && route.steps.length > 0 && (
                            <span className="steps-count-badge">
                              {route.steps.length} {route.steps.length === 1 ? 'step' : 'steps'}
                            </span>
                          )}
                        </div>
                        {expandedStepsRouteId === route.id ? (
                          <ChevronUp size={13} className="steps-chevron" />
                        ) : (
                          <ChevronDown size={13} className="steps-chevron" />
                        )}
                      </button>

                      {expandedStepsRouteId === route.id && (
                        <div className="route-steps-content" onClick={(e) => e.stopPropagation()}>
                          {route.steps && route.steps.length > 0 ? (
                            <ol className="route-steps-list">
                              {route.steps.map((step, sIdx) => {
                                const mod = (step.modifier || '').toLowerCase();
                                const instr = (step.instruction || '').toLowerCase();
                                const typeCode = step.type;

                                let StepIcon = Compass;
                                let iconModifierClass = 'icon-default';

                                if (typeCode === 10 || mod === 'arrive' || instr.includes('arrive')) {
                                  StepIcon = MapPin;
                                  iconModifierClass = 'icon-arrive';
                                } else if (typeCode === 11 || mod === 'depart' || instr.includes('depart') || instr.includes('head')) {
                                  StepIcon = Navigation;
                                  iconModifierClass = 'icon-depart';
                                } else if (mod.includes('left') || instr.includes('left')) {
                                  StepIcon = CornerUpLeft;
                                  iconModifierClass = 'icon-left';
                                } else if (mod.includes('right') || instr.includes('right')) {
                                  StepIcon = CornerUpRight;
                                  iconModifierClass = 'icon-right';
                                } else if (mod.includes('straight') || mod.includes('continue') || instr.includes('straight') || instr.includes('continue')) {
                                  StepIcon = ArrowUp;
                                  iconModifierClass = 'icon-straight';
                                } else if (mod.includes('roundabout') || typeCode === 7 || typeCode === 8) {
                                  StepIcon = RotateCcw;
                                  iconModifierClass = 'icon-roundabout';
                                }

                                return (
                                  <li key={sIdx} className="route-step-item">
                                    <div className="step-marker-col">
                                      <span className="step-number-badge">{sIdx + 1}</span>
                                      <span className={`step-icon-wrap ${iconModifierClass}`}>
                                        <StepIcon size={12} />
                                      </span>
                                    </div>
                                    <div className="step-details-col">
                                      <div className="step-instruction-text">{step.instruction}</div>
                                      <div className="step-meta-row">
                                        {step.distance_m > 0 && (
                                          <span className="step-meta-pill step-distance">
                                            {step.distance_m >= 1000
                                              ? `${(step.distance_m / 1000).toFixed(2)} km`
                                              : `${Math.round(step.distance_m)} m`}
                                          </span>
                                        )}
                                        {step.duration_s > 0 && (
                                          <span className="step-meta-pill step-duration">
                                            {Math.round(step.duration_s / 60) > 0
                                              ? `~${Math.round(step.duration_s / 60)} min`
                                              : '< 1 min'}
                                          </span>
                                        )}
                                        {step.name && step.name !== '-' && (
                                          <span className="step-meta-pill step-street">{step.name}</span>
                                        )}
                                      </div>
                                    </div>
                                  </li>
                                );
                              })}
                            </ol>
                          ) : (
                            <div className="steps-empty-notice">
                              <Info size={13} />
                              <span>Detailed turn-by-turn maneuvers unavailable for this path.</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="route-card-footer">
                      <label className="route-select-radio">
                        <input
                          type="radio"
                          name="selectedRoute"
                          checked={isSelected}
                          onChange={() => onSelectRoute(route.id)}
                        />
                        <span>{isSelected ? 'Active on Map' : 'Select this Route'}</span>
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Comparison Table Across All Routes filtered by user preferences */}
            <RouteComparisonTable
              routes={routes}
              rankingData={rankingData}
              selectedRouteId={selectedRouteId}
              onSelectRoute={onSelectRoute}
              preferences={preferences}
            />
          </section>
        )}

        {/* Step 2: Environmental Factors Selection */}
        <section className="control-section">
          <div className="section-header">
            <div className="section-title-wrap">
              <SlidersHorizontal size={18} className="text-primary" />
              <h2 className="section-title">Environmental Preferences</h2>
            </div>
            <span className="badge-count">
              {preferences.no_preference
                ? 'Default Baseline'
                : activePreferencesCount > 0
                ? `${activePreferencesCount} Active`
                : 'Default Baseline'}
            </span>
          </div>

          <p className="section-description">
            Select the environmental factors you care about. No manual numeric weights required—our multi-criteria algorithm evaluates alternative routes transparently using equal priority.
          </p>

          {/* Explicit No-Preference Option */}
          <label
            className={`preference-card no-pref-card ${preferences.no_preference ? 'active' : ''}`}
            htmlFor="pref-no-preference"
          >
            <div className="preference-icon-badge no-pref-badge">
              <Scale size={18} />
            </div>
            <div className="preference-details">
              <span className="preference-name">No Preference (Transparent Baseline)</span>
              <span className="preference-source">
                Evaluates all available environmental factors & distance equally without bias
              </span>
            </div>
            <input
              type="checkbox"
              id="pref-no-preference"
              name="no_preference"
              checked={!!preferences.no_preference}
              onChange={handleToggleNoPreference}
              className="accessible-checkbox"
              aria-label="No preference: apply transparent default baseline"
            />
          </label>

          {/* 5 Specific Environmental Factors */}
          <div className="preferences-grid">
            {preferenceItems.map((pref) => {
              const Icon = pref.icon;
              const isChecked = !preferences.no_preference && !!preferences[pref.id];
              const isDisabled = !!preferences.no_preference;

              return (
                <label
                  key={pref.id}
                  className={`preference-card ${isChecked ? 'active' : ''} ${isDisabled ? 'disabled' : ''}`}
                  htmlFor={`pref-${pref.id}`}
                >
                  <div
                    className="preference-icon-badge"
                    style={{ backgroundColor: `${pref.color}18`, color: pref.color }}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="preference-details">
                    <span className="preference-name">{pref.label}</span>
                    <span className="preference-source">{pref.subtitle}</span>
                    <span className="preference-direction-tag">{pref.direction}</span>
                  </div>
                  <input
                    type="checkbox"
                    id={`pref-${pref.id}`}
                    name={pref.id}
                    checked={isChecked}
                    onChange={() => togglePreference(pref.id)}
                    className="accessible-checkbox"
                    aria-label={`Toggle preference for ${pref.label}`}
                  />
                </label>
              );
            })}
          </div>

          {/* Default Rule Callout & Algorithmic Notice */}
          <div className="default-rule-callout">
            <Info size={16} className="callout-icon" />
            <div className="callout-body">
              <strong>Transparent Algorithmic Policy:</strong>
              {preferences.no_preference ? (
                <p>
                  <strong>Default Baseline Active:</strong> Candidate routes are evaluated across all available environmental indicators and walking distance with equal priority. Does not claim to find an absolute healthiest path.
                </p>
              ) : (
                <p>
                  The engine scores non-dominated candidate routes with equal priority (1/{activePreferencesCount || 1}) across your {activePreferencesCount} selected criteria. Equal weighting is an algorithmic design choice, not a discovered personal psychological preference.
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Reset All Controls */}
        <button
          type="button"
          className="btn-secondary"
          onClick={onReset}
        >
          <RotateCcw size={16} />
          <span>Reset All Map & Preferences</span>
        </button>

        {/* Architecture Status Card */}
        <section className="project-roadmap-card">
          <div className="roadmap-header">
            <Layers size={16} className="text-primary" />
            <h3>Project Architecture Status</h3>
          </div>
          <ul className="roadmap-list">
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>Frontend React + Leaflet OSM Map</span>
            </li>
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>FastAPI Backend & Health-Check Service</span>
            </li>
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>Nominatim Geocoding (Rate-limited & Cached)</span>
            </li>
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>OpenRouteService Walking Directions & Alternatives</span>
            </li>
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>Open-Meteo Multi-Pollutant & Weather Encoders</span>
            </li>
            <li className="roadmap-item done">
              <span className="bullet">✓</span>
              <span>Multi-Criteria Preference Engine & Pareto Dominance</span>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  );
}
