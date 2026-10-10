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
  Check,
  Layers,
  X,
  AlertCircle,
  Clock,
  Compass,
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import { searchLocations } from '../services/geocodingService';

export default function Sidebar({
  origin,
  setOrigin,
  destination,
  setDestination,
  preferences,
  setPreferences,
  clickMode,
  setClickMode,
  onCalculateRoutes,
  onClearRoutes,
  onReset,
  routes = [],
  selectedRouteId = null,
  onSelectRoute = () => {},
  isLoadingRoutes = false,
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

  const togglePreference = (key) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const preferenceItems = [
    {
      id: 'air_quality',
      label: 'Air Quality (Low PM2.5 / AQI)',
      icon: Wind,
      color: '#3b82f6',
      source: 'Open-Meteo AQI',
    },
    {
      id: 'greenery',
      label: 'Greenery & Parks',
      icon: TreePine,
      color: '#10b981',
      source: 'OSM Overpass',
    },
    {
      id: 'temperature',
      label: 'Mild Temperature / Shade',
      icon: Thermometer,
      color: '#f59e0b',
      source: 'Open-Meteo Weather',
    },
    {
      id: 'walking_distance',
      label: 'Shortest Walking Distance',
      icon: Footprints,
      color: '#8b5cf6',
      source: 'OpenRouteService',
    },
    {
      id: 'traffic_safety',
      label: 'Pedestrian-Friendly / Low Traffic',
      icon: ShieldCheck,
      color: '#ec4899',
      source: 'OSM Walkways',
    },
  ];

  const activePreferencesCount = Object.values(preferences).filter(Boolean).length;

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

        {/* Action Controls for Route Calculation */}
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
                {routes.length > 1 ? `${routes.length} Available` : '1 Route'}
              </span>
            </div>

            {routes.length === 1 && (
              <div className="honest-notice-banner">
                <Info size={15} />
                <span>
                  Single walking route returned. OpenRouteService identified no alternative pedestrian paths for this specific distance/corridor.
                </span>
              </div>
            )}

            <div className="routes-list">
              {routes.map((route) => {
                const isSelected = route.id === selectedRouteId;
                return (
                  <div
                    key={route.id}
                    className={`route-card ${isSelected ? 'selected' : ''}`}
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
                      <span className={`route-type-badge ${route.is_primary ? 'primary' : 'alt'}`}>
                        {route.is_primary ? 'Recommended' : 'Alternative'}
                      </span>
                    </div>

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
                    </div>

                    {route.summary && (
                      <p className="route-summary-text">{route.summary}</p>
                    )}

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
          </section>
        )}

        {/* Step 2: Environmental Factors Selection */}
        <section className="control-section">
          <div className="section-header">
            <div className="section-title-wrap">
              <span className="step-num">2</span>
              <h2 className="section-title">Environmental Preferences</h2>
            </div>
            <span className="badge-count">
              {activePreferencesCount > 0
                ? `${activePreferencesCount} Active`
                : 'Default Rule'}
            </span>
          </div>

          <p className="section-description">
            Select the environmental factors you care about. No manual numeric weights required—our multi-criteria algorithm evaluates alternative routes transparently.
          </p>

          <div className="preferences-grid">
            {preferenceItems.map((pref) => {
              const Icon = pref.icon;
              const isChecked = !!preferences[pref.id];
              return (
                <div
                  key={pref.id}
                  className={`preference-card ${isChecked ? 'active' : ''}`}
                  onClick={() => togglePreference(pref.id)}
                >
                  <div
                    className="preference-icon-badge"
                    style={{ backgroundColor: `${pref.color}18`, color: pref.color }}
                  >
                    <Icon size={18} />
                  </div>
                  <div className="preference-details">
                    <span className="preference-name">{pref.label}</span>
                    <span className="preference-source">Data: {pref.source}</span>
                  </div>
                  <div className={`checkbox-custom ${isChecked ? 'checked' : ''}`}>
                    {isChecked && <Check size={14} />}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Default Rule Callout */}
          <div className="default-rule-callout">
            <Info size={16} className="callout-icon" />
            <div className="callout-body">
              <strong>Transparent Default Rule:</strong>
              {activePreferencesCount === 0 ? (
                <p>
                  No preference active. The system applies the <em>Standard Baseline</em>: minimizing walking distance while maintaining pedestrian pathway safety.
                </p>
              ) : (
                <p>
                  The algorithm balances {activePreferencesCount} selected criteria across candidate routes.
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
            <li className="roadmap-item upcoming">
              <span className="bullet">○</span>
              <span>Open-Meteo & Overpass Environmental Encoders</span>
            </li>
            <li className="roadmap-item upcoming">
              <span className="bullet">○</span>
              <span>Multi-Criteria Preference Ranking Algorithm</span>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  );
}
