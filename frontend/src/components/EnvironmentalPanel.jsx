import { useState } from 'react';
import {
  Wind,
  Thermometer,
  TreePine,
  ShieldCheck,
  CloudSun,
  Droplets,
  Gauge,
  Info,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Clock,
  Footprints,
} from 'lucide-react';

export default function EnvironmentalPanel({ environment, preferences = null }) {
  const [showSamples, setShowSamples] = useState(false);

  if (!environment) {
    return (
      <div className="env-unavailable-box">
        <Info size={14} />
        <span>Environmental exposure data currently unavailable for this corridor.</span>
      </div>
    );
  }

  // Preference-based dynamic display filtering
  const isDefault = !preferences || !!preferences.no_preference || (
    !preferences.air_quality &&
    !preferences.temperature &&
    !preferences.traffic_exposure &&
    !preferences.greenery &&
    !preferences.walking_distance
  );

  const showAirQuality = isDefault || !!preferences?.air_quality;
  const showWeather = isDefault || !!preferences?.temperature;
  const showGreenery = isDefault || !!preferences?.greenery;
  const showTraffic = isDefault || !!preferences?.traffic_exposure;
  const hasAnyEnvFactor = showAirQuality || showWeather || showGreenery || showTraffic;

  const {
    air_quality: aq,
    weather: wx,
    greenery: gr,
    traffic_exposure: tr,
    metadata: meta,
    sample_points: samplePoints,
    notes = [],
    is_stale: isStale,
    stale_warning: staleWarning,
  } = environment;

  const aqiVal = aq?.european_aqi?.value;
  const aqiCat = aq?.aqi_category || (aqiVal !== null && aqiVal !== undefined ? 'Estimated' : 'Unavailable');
  const aqiColor = aq?.aqi_color || '#94a3b8';

  const grScore = gr?.score;
  const grStatus = gr?.status || 'unavailable';
  const grCovPct = gr?.greenery_fraction !== null && gr?.greenery_fraction !== undefined
    ? Math.round(gr.greenery_fraction * 100)
    : null;

  const trScore = tr?.score;
  const isLiveTraffic = !!tr?.is_live_measurement;

  return (
    <div className="environmental-panel">
      {/* Air Quality Summary Row */}
      {showAirQuality && (
        <div className="env-metric-group">
          <div className="env-group-header">
            <div className="env-header-title">
              <Wind size={14} className="text-primary" />
              <span>Air Quality Profile</span>
            </div>
            {aqiVal !== null && aqiVal !== undefined ? (
              <span
                className="aqi-badge-pill"
                style={{ backgroundColor: `${aqiColor}20`, color: aqiColor, borderColor: aqiColor }}
              >
                <span className="aqi-dot" style={{ backgroundColor: aqiColor }}></span>
                EAQI {aqiVal} ({aqiCat})
              </span>
            ) : (
              <span className="aqi-badge-pill unavailable">AQI Unavailable</span>
            )}
          </div>

          <div className="pollutant-grid">
            <div className="pollutant-cell">
              <span className="pollutant-name">PM2.5</span>
              <span className="pollutant-val">
                {aq?.pm2_5?.value !== null && aq?.pm2_5?.value !== undefined ? (
                  <>
                    {aq.pm2_5.value} <small>{aq.pm2_5.unit}</small>
                  </>
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>

            <div className="pollutant-cell">
              <span className="pollutant-name">PM10</span>
              <span className="pollutant-val">
                {aq?.pm10?.value !== null && aq?.pm10?.value !== undefined ? (
                  <>
                    {aq.pm10.value} <small>{aq.pm10.unit}</small>
                  </>
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>

            <div className="pollutant-cell">
              <span className="pollutant-name">NO₂</span>
              <span className="pollutant-val">
                {aq?.nitrogen_dioxide?.value !== null && aq?.nitrogen_dioxide?.value !== undefined ? (
                  <>
                    {aq.nitrogen_dioxide.value} <small>{aq.nitrogen_dioxide.unit}</small>
                  </>
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Meteorological & Thermal Row */}
      {showWeather && (
        <div className="env-metric-group">
          <div className="env-group-header">
            <div className="env-header-title">
              <Thermometer size={14} className="text-warning" />
              <span>Thermal & Weather</span>
            </div>
            {wx?.weather_description && (
              <span className="wx-desc-pill">
                <CloudSun size={12} />
                {wx.weather_description}
              </span>
            )}
          </div>

          <div className="weather-grid">
            <div className="weather-cell">
              <span className="wx-label">Ambient Temp</span>
              <span className="wx-val">
                {wx?.temperature_c !== null && wx?.temperature_c !== undefined ? (
                  `${wx.temperature_c} °C`
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>

            <div className="weather-cell">
              <span className="wx-label">Feels Like</span>
              <span className="wx-val">
                {wx?.apparent_temperature_c !== null && wx?.apparent_temperature_c !== undefined ? (
                  `${wx.apparent_temperature_c} °C`
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>

            <div className="weather-cell">
              <span className="wx-label">Humidity</span>
              <span className="wx-val">
                {wx?.relative_humidity_pct !== null && wx?.relative_humidity_pct !== undefined ? (
                  <>
                    <Droplets size={11} className="inline-icon" />
                    {wx.relative_humidity_pct}%
                  </>
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>

            <div className="weather-cell">
              <span className="wx-label">Wind</span>
              <span className="wx-val">
                {wx?.wind_speed_kmh !== null && wx?.wind_speed_kmh !== undefined ? (
                  <>
                    <Gauge size={11} className="inline-icon" />
                    {wx.wind_speed_kmh} km/h
                  </>
                ) : (
                  <span className="val-missing">Unavailable</span>
                )}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Greenery & Parks Corridor Row */}
      {showGreenery && (
        <div className="env-metric-group">
          <div className="env-group-header">
            <div className="env-header-title">
              <TreePine size={14} className="text-success" />
              <span>Greenery & Parks Corridor</span>
            </div>
            {grScore !== null && grScore !== undefined ? (
              <span className="gr-badge-pill available">
                Greenery Score: {Math.round(grScore)}%
              </span>
            ) : grStatus === 'empty_osm_coverage' ? (
              <span className="gr-badge-pill zero">0% Mapped Greenery</span>
            ) : (
              <span className="gr-badge-pill unavailable">Greenery Unavailable</span>
            )}
          </div>

          <div className="greenery-grid">
            <div className="greenery-cell">
              <span className="gr-label">50m Buffer Coverage</span>
              <span className="gr-val">
                {grCovPct !== null ? `${grCovPct}%` : <span className="val-missing">Unavailable</span>}
              </span>
            </div>
            <div className="greenery-cell">
              <span className="gr-label">Adjacent Parks</span>
              <span className="gr-val">
                {gr?.parks_count !== null && gr?.parks_count !== undefined
                  ? `${gr.parks_count} park${gr.parks_count === 1 ? '' : 's'}`
                  : <span className="val-missing">None</span>}
              </span>
            </div>
            <div className="greenery-cell">
              <span className="gr-label">Mapped Features</span>
              <span className="gr-val">
                {gr?.mapped_features_count ?? 0}
              </span>
            </div>
            <div className="greenery-cell">
              <span className="gr-label">Data Origin</span>
              <span className="gr-val gr-sub">OSM Overpass</span>
            </div>
          </div>

          <p className="env-sub-note">
            ℹ️ <strong>Greenery Notice:</strong> Proximity to mapped OSM green polygons (parks, tree cover) is a spatial buffer indicator; it is not equivalent to measured Green View Index (GVI), canopy density, or shade.
          </p>
        </div>
      )}

      {/* Traffic Exposure & Road Hierarchy Row */}
      {showTraffic && (
        <div className="env-metric-group">
          <div className="env-group-header">
            <div className="env-header-title">
              <ShieldCheck size={14} className="text-secondary" />
              <span>Traffic Exposure Indicator</span>
            </div>
            {trScore !== null && trScore !== undefined ? (
              <span className={`tr-badge-pill ${isLiveTraffic ? 'live' : 'proxy'}`}>
                {isLiveTraffic ? 'Live Traffic' : 'Road Proxy'}: {Math.round(trScore)}/100
              </span>
            ) : (
              <span className="tr-badge-pill unavailable">Traffic Unavailable</span>
            )}
          </div>

          <div className="traffic-grid">
            <div className="traffic-cell">
              <span className="tr-label">Indicator Type</span>
              <span className="tr-val">
                {isLiveTraffic ? 'Live Speed / Congestion' : 'Static Road Hierarchy Proxy'}
              </span>
            </div>
            <div className="traffic-cell">
              <span className="tr-label">Major Road Proximity</span>
              <span className="tr-val">
                {tr?.static_proxy?.major_road_nearby_pct !== null && tr?.static_proxy?.major_road_nearby_pct !== undefined
                  ? `${Math.round(tr.static_proxy.major_road_nearby_pct)}% of path`
                  : isLiveTraffic ? 'Live Congestion' : 'Low (<50m)'}
              </span>
            </div>
            <div className="traffic-cell">
              <span className="tr-label">Dominant Road Class</span>
              <span className="tr-val">
                {tr?.road_class || tr?.static_proxy?.dominant_road_class || 'Pedestrian / Local'}
              </span>
            </div>
            <div className="traffic-cell">
              <span className="tr-label">Live Measurement?</span>
              <span className="tr-val">
                {isLiveTraffic ? 'Yes (Live API)' : 'No (Static OSM Proxy)'}
              </span>
            </div>
          </div>

          <p className="env-sub-note">
            ⚠️ <strong>Traffic Limitation Notice:</strong> {isLiveTraffic
              ? 'Live speed congestion reflects current motor vehicle delay on adjacent roadways.'
              : 'Static road infrastructure proxy based on proximity to mapped arterial roadways. Does NOT represent live vehicular counts, real-time speed, or transient congestion.'}
          </p>
        </div>
      )}


      {/* Notice when only Distance is selected */}
      {!hasAnyEnvFactor && (
        <div className="env-selected-only-notice">
          <Footprints size={15} className="text-primary inline-icon" />
          <span>Walking distance preference active: Route ranked exclusively for shortest pedestrian path. Environmental factors are excluded based on your selection.</span>
        </div>
      )}

      {/* Model Transparency & Provenance Disclaimer */}
      {hasAnyEnvFactor && (
        <div className="env-provenance-footer">
          {/* Stale Warning Banner if retained on provider failure */}
          {(isStale || meta?.is_stale) && (
            <div className="stale-warning-banner">
              <AlertTriangle size={14} className="text-warning inline-icon" />
              <span>
                <strong>Stale Data Notice:</strong> {staleWarning || meta?.stale_warning || 'Provider was unreachable during refresh; displaying retained previous measurements.'}
              </span>
            </div>
          )}

          <div className="provenance-tags">
            {showWeather && <span className="provenance-tag">Open-Meteo (~11km NWP)</span>}
            {showAirQuality && <span className="provenance-tag">CAMS Air Quality</span>}
            {showGreenery && <span className="provenance-tag subtle">OSM Overpass Geometries</span>}
            {showTraffic && <span className="provenance-tag subtle">OSM Road Hierarchy</span>}
            {meta?.observation_or_forecast_timestamp && (
              <span className="provenance-time">
                {meta.is_forecast ? 'Forecast Step: ' : 'Observation: '}
                {meta.observation_or_forecast_timestamp}
              </span>
            )}
            {meta?.retrieval_timestamp && (
              <span className="provenance-time subtle">
                <Clock size={11} className="inline-icon" /> Fetched: {new Date(meta.retrieval_timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>

          {notes && notes.length > 0 && (
            <div className="env-notes-callout">
              <AlertTriangle size={12} />
              <span>{notes.join(' ')}</span>
            </div>
          )}

          {/* Toggle Sample Points Inspection */}
          {samplePoints && samplePoints.length > 0 && (
            <div className="sample-points-inspector">
              <button
                type="button"
                className="btn-toggle-samples"
                onClick={() => setShowSamples(!showSamples)}
              >
                <span>{showSamples ? 'Hide' : 'Inspect'} {samplePoints.length} Route Sample Points</span>
                {showSamples ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              </button>

              {showSamples && (
                <div className="samples-table-wrapper">
                  <table className="samples-table">
                    <thead>
                      <tr>
                        <th>Pt</th>
                        <th>Coords</th>
                        {showAirQuality && <th>PM2.5</th>}
                        {showAirQuality && <th>EAQI</th>}
                        {showWeather && <th>Temp</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {samplePoints.map((pt, i) => (
                        <tr key={i}>
                          <td>#{pt.point_index + 1}</td>
                          <td className="coords-cell">{pt.lat.toFixed(3)}, {pt.lon.toFixed(3)}</td>
                          {showAirQuality && <td>{pt.air_quality?.pm2_5?.value ?? '—'}</td>}
                          {showAirQuality && <td>{pt.air_quality?.european_aqi?.value ?? '—'}</td>}
                          {showWeather && <td>{pt.weather?.temperature_c !== null ? `${pt.weather?.temperature_c}°C` : '—'}</td>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
