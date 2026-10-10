import { useEffect } from 'react';
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

export default function MapView({
  origin,
  destination,
  onMapClick,
  clickMode,
  routes = [],
  selectedRouteId = null,
  onSelectRoute = () => {},
}) {
  // Default map center (Central London demo area)
  const defaultCenter = [51.505, -0.09];
  const defaultZoom = 13;

  const selectedRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];

  // Sort routes so the selected route renders last (on top)
  const sortedRoutes = [...routes].sort((a, b) => {
    if (a.id === selectedRouteId) return 1;
    if (b.id === selectedRouteId) return -1;
    return 0;
  });

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

        {/* Polylines for calculated walking routes */}
        {sortedRoutes.map((route) => {
          const isSelected = route.id === selectedRouteId;
          return (
            <div key={route.id}>
              {/* White background glow for active route */}
              {isSelected && (
                <Polyline
                  positions={route.coordinates}
                  pathOptions={{
                    color: '#ffffff',
                    weight: 10,
                    opacity: 0.8,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                />
              )}

              {/* Main colored polyline */}
              <Polyline
                positions={route.coordinates}
                pathOptions={{
                  color: route.color || (isSelected ? '#2563eb' : '#94a3b8'),
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
            </div>
          );
        })}

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
