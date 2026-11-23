import { useEffect, useState, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Tooltip,
  useMap,
  useMapEvents,
  ZoomControl,
} from 'react-leaflet';
import L from 'leaflet';
import { Layers, Wind, Thermometer, TreePine, ShieldCheck, Palette } from 'lucide-react';
import { METRIC_CONFIGS, buildRouteSegments } from '../utils/environmentalSegmentation';

// Create custom SVG markers for Start (Green) and Destination (Red)
const createCustomIcon = (color, label) => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background-color: ${color};
        width: 32px;
        height: 32px;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
      ">
        <span style="
          transform: rotate(45deg);
          color: white;
          font-weight: 700;
          font-size: 13px;
          font-family: sans-serif;
        ">${label}</span>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

const startIcon = createCustomIcon('#10b981', 'A'); // Emerald Green
const endIcon = createCustomIcon('#ef4444', 'B');   // Bright Red

// Sub-component to handle map click events
function MapEventsHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    },
  });
  return null;
}

// Sub-component to adjust map bounds when routes or waypoints change
function MapBoundsUpdater({ origin, destination, selectedRoute }) {
  const map = useMap();

  useEffect(() => {
    // If a selected route exists with coordinates, fit bounds to that route
    if (selectedRoute?.coordinates && selectedRoute.coordinates.length > 0) {
      const bounds = L.latLngBounds(selectedRoute.coordinates);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
      return;
    }

    // Otherwise, fit bounds between origin and destination markers
    if (origin && destination) {
      const bounds = L.latLngBounds([
        [origin.lat, origin.lon],
        [destination.lat, destination.lon],
      ]);
      map.fitBounds(bounds, { padding: [60, 60], maxZoom: 16 });
    } else if (origin) {
      map.flyTo([origin.lat, origin.lon], 14);
    } else if (destination) {
      map.flyTo([destination.lat, destination.lon], 14);
    }
  }, [origin, destination, selectedRoute, map]);

  return null;
}

// Sub-component to render route polylines as solid or environmental macro-segments
function RoutePolylineRenderer({
  route,
  isSelected,
  currentMetric,
  onSelectRoute,
}) {
  const segments = useMemo(
    () => buildRouteSegments(route, currentMetric),
    [route, currentMetric]
  );

  const isMultiSegment = currentMetric !== 'default' && segments.length > 1;

  return (
    <>
      {/* White background glow for active route */}
      {isSelected && (
        <Polyline
          positions={route.coordinates}
          pathOptions={{
            color: '#ffffff',
            weight: 12,
            opacity: 0.88,
            lineCap: 'round',
            lineJoin: 'round',
          }}
        />
      )}

      {/* Render single polyline if default or only 1 segment */}
      {!isMultiSegment ? (
        <Polyline
          positions={route.coordinates}
          pathOptions={{
            color: segments[0]?.color || route.color || (isSelected ? '#2563eb' : '#94a3b8'),
            weight: isSelected ? 6 : 4,
            opacity: isSelected ? 0.95 : 0.55,
            dashArray: isSelected ? null : '6, 6',
            lineCap: 'round',
            lineJoin: 'round',
          }}
          eventHandlers={{
            click: () => onSelectRoute(route.id),
          }}
        >
          <Tooltip sticky>
            <div className="route-tooltip-content">
              <strong>{route.name}</strong>
              <div>{route.distance_km} km &bull; {Math.round(route.duration_min)} min walk</div>
              {segments[0]?.metricValue !== null && (
                <div>{segments[0].metricLabel}: <strong>{segments[0].metricDisplay}</strong></div>
              )}
              <small>{isSelected ? '✓ Currently Selected' : 'Click to select'}</small>
            </div>
          </Tooltip>
          <Popup>
            <div className="route-popup-card">
              <div className="route-popup-header" style={{ color: route.color }}>
                <strong>{route.name}</strong>
              </div>
              <p className="route-popup-details">
                Distance: <strong>{route.distance_km} km</strong> ({Math.round(route.distance_m)} m)<br />
                Estimated Duration: <strong>{Math.round(route.duration_min)} minutes</strong>
              </p>
              {route.summary && <p className="route-popup-summary">{route.summary}</p>}
              {!isSelected && (
                <button
                  type="button"
                  className="btn-popup-select"
                  onClick={() => onSelectRoute(route.id)}
                >
                  Select this Route
                </button>
              )}
            </div>
          </Popup>
        </Polyline>
      ) : (
        /* Render environmental macro-segments */
        segments.map((seg, sIdx) => (
          <Polyline
            key={`${route.id}-seg-${sIdx}`}
            positions={seg.coordinates}
            pathOptions={{
              color: seg.color,
              weight: isSelected ? 7 : 4,
              opacity: isSelected ? 0.95 : 0.55,
              dashArray: seg.isMissing ? '6, 6' : (isSelected ? null : '6, 6'),
              lineCap: 'round',
              lineJoin: 'round',
            }}
            eventHandlers={{
              click: () => onSelectRoute(route.id),
            }}
          >
            <Tooltip sticky>
              <div className="route-tooltip-content">
                <strong>{route.name}</strong>
                <div>
                  Segment #{sIdx + 1} of {segments.length} &bull; {seg.metricLabel}: <strong>{seg.metricDisplay}</strong>
                </div>
                <div>{route.distance_km} km &bull; {Math.round(route.duration_min)} min walk</div>
                <small>{isSelected ? '✓ Currently Selected' : 'Click to select'}</small>
              </div>
            </Tooltip>
            <Popup>
              <div className="route-popup-card">
                <div className="route-popup-header" style={{ color: seg.color }}>
                  <strong>{route.name}</strong>
                </div>
                <p className="route-popup-details">
                  Distance: <strong>{route.distance_km} km</strong> ({Math.round(route.distance_m)} m)<br />
                  Estimated Duration: <strong>{Math.round(route.duration_min)} minutes</strong><br />
                  Segment #{sIdx + 1} {seg.metricLabel}: <strong>{seg.metricDisplay}</strong>
                </p>
                {route.summary && <p className="route-popup-summary">{route.summary}</p>}
                {!isSelected && (
                  <button
                    type="button"
                    className="btn-popup-select"
                    onClick={() => onSelectRoute(route.id)}
                  >
                    Select this Route
                  </button>
                )}
              </div>
            </Popup>
          </Polyline>
        ))
      )}
    </>
  );
}

export default function MapView({
  origin,
  destination,
  onMapClick,
  clickMode,
  routes = [],
  selectedRouteId = null,
  onSelectRoute = () => {},
  envMetric = null,
  onEnvMetricChange = null,
}) {
  // Default map center (Central London demo area)
  const defaultCenter = [51.505, -0.09];
  const defaultZoom = 13;

  const [internalMetric, setInternalMetric] = useState('air_quality');
  const currentMetric = envMetric !== null && envMetric !== undefined ? envMetric : internalMetric;

  const handleMetricChange = (metricId) => {
    if (onEnvMetricChange) {
      onEnvMetricChange(metricId);
    } else {
      setInternalMetric(metricId);
    }
  };

  const selectedRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];

  // Sort routes so the selected route renders last (on top)
  const sortedRoutes = [...routes].sort((a, b) => {
    if (a.id === selectedRouteId) return 1;
    if (b.id === selectedRouteId) return -1;
    return 0;
  });

  const renderMetricIcon = (metricId) => {
    switch (metricId) {
      case 'air_quality':
        return <Wind size={12} />;
      case 'temperature':
        return <Thermometer size={12} />;
      case 'greenery':
        return <TreePine size={12} />;
      case 'traffic_exposure':
        return <ShieldCheck size={12} />;
      default:
        return <Palette size={12} />;
    }
  };

  return (
    <div className="map-view-wrapper">
      <div className="map-interaction-hint">
        <span>
          💡 Mode:{' '}
          <strong>
            {clickMode === 'origin'
              ? 'Setting Start (A)'
              : clickMode === 'destination'
              ? 'Setting Destination (B)'
              : routes.length > 0
              ? 'Click any route on map to inspect'
              : 'Map Navigation'}
          </strong>
          {clickMode !== 'none' ? ' — Click on the map to place point.' : ''}
        </span>
      </div>

      {/* Environmental Metric Selector and Legend Overlay */}
      {routes.length > 0 && (
        <div className="map-env-controls-overlay">
          <div className="env-metric-toggle-group">
            <span className="env-toggle-title">
              <Layers size={13} />
              <span>Map Layer:</span>
            </span>
            {Object.values(METRIC_CONFIGS).map((metric) => {
              const isActive = currentMetric === metric.id;
              return (
                <button
                  key={metric.id}
                  type="button"
                  className={`btn-env-metric-pill ${isActive ? 'active' : ''}`}
                  onClick={() => handleMetricChange(metric.id)}
                >
                  {renderMetricIcon(metric.id)}
                  <span>{metric.label}</span>
                </button>
              );
            })}
          </div>

          {/* Active Metric Legend */}
          {currentMetric !== 'default' && METRIC_CONFIGS[currentMetric]?.legend && (
            <div className="env-map-legend">
              <span className="legend-title">
                {METRIC_CONFIGS[currentMetric].label} Scale ({METRIC_CONFIGS[currentMetric].unit}):
              </span>
              <div className="legend-items-list">
                {METRIC_CONFIGS[currentMetric].legend.map((item, idx) => (
                  <div key={idx} className="legend-item">
                    <span
                      className="legend-color-swatch"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="legend-label">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <MapContainer
        center={origin ? [origin.lat, origin.lon] : defaultCenter}
        zoom={defaultZoom}
        zoomControl={false}
        className="leaflet-map-canvas"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <ZoomControl position="bottomright" />

        <MapEventsHandler onMapClick={onMapClick} />
        <MapBoundsUpdater
          origin={origin}
          destination={destination}
          selectedRoute={selectedRoute}
        />

        {/* Polylines for calculated walking routes (solid or environmental macro-segments) */}
        {sortedRoutes.map((route) => (
          <RoutePolylineRenderer
            key={route.id}
            route={route}
            isSelected={route.id === selectedRouteId}
            currentMetric={currentMetric}
            onSelectRoute={onSelectRoute}
          />
        ))}

        {/* Origin Marker */}
        {origin && (
          <Marker position={[origin.lat, origin.lon]} icon={startIcon}>
            <Popup>
              <div className="marker-popup">
                <strong>🟢 Start Point (A)</strong>
                <p>{origin.label || `${origin.lat.toFixed(5)}, ${origin.lon.toFixed(5)}`}</p>
                <small className="text-muted">
                  Lat: {origin.lat.toFixed(4)}, Lon: {origin.lon.toFixed(4)}
                </small>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {destination && (
          <Marker position={[destination.lat, destination.lon]} icon={endIcon}>
            <Popup>
              <div className="marker-popup">
                <strong>🔴 Destination Point (B)</strong>
                <p>{destination.label || `${destination.lat.toFixed(5)}, ${destination.lon.toFixed(5)}`}</p>
                <small className="text-muted">
                  Lat: {destination.lat.toFixed(4)}, Lon: {destination.lon.toFixed(4)}
                </small>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
