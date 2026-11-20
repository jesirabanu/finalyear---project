import { useState } from 'react';
import {
  Table,
  CheckCircle2,
  AlertTriangle,
  Award,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';

/**
 * RouteComparisonTable
 * Displays a structured side-by-side comparison across all candidate walking routes.
 * Distinguishes raw physical measurements from dimensionless normalized scores [0.0 - 1.0].
 */
export default function RouteComparisonTable({
  routes = [],
  rankingData = null,
  selectedRouteId = null,
  onSelectRoute = () => {},
  preferences = null,
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!routes || routes.length === 0) {
    return null;
  }

  // Preference-based dynamic column filtering
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
  const showDistance = isDefault || !!preferences?.walking_distance;

  const comparisonRows = rankingData?.comparison_matrix || [];

  return (
    <div className="route-comparison-section">
      <div
        className="comparison-header"
        onClick={() => setIsExpanded(!isExpanded)}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <div className="comparison-title-wrap">
          <Table size={16} className="text-primary" />
          <h3 className="comparison-title">Multi-Criteria Route Comparison Matrix</h3>
          <span className="badge-count">{routes.length} Candidate{routes.length > 1 ? 's' : ''}</span>
        </div>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-label={isExpanded ? 'Collapse comparison table' : 'Expand comparison table'}
        >
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {isExpanded && (
        <div className="comparison-body">
          <div className="comparison-legend">
            <div className="legend-item">
              <span className="legend-swatch raw-swatch">12.4 EAQI</span>
              <span>Raw Measurement (with physical units)</span>
            </div>
            <div className="legend-item">
              <span className="legend-swatch score-swatch">0.85</span>
              <span>Normalized Score [0.0 = worst, 1.0 = best]</span>
            </div>
          </div>

          <div className="table-responsive-wrapper">
            <table className="comparison-table" aria-label="Route multi-criteria comparison">
              <thead>
                <tr>
                  <th scope="col" className="th-sticky">Route & Rank</th>
                  <th scope="col">Status</th>
                  <th scope="col">Overall Score</th>
                  {showDistance && <th scope="col">Distance</th>}
                  {showDistance && <th scope="col">Duration</th>}
                  {showAirQuality && <th scope="col">Air Quality</th>}
                  {showWeather && <th scope="col">Temperature</th>}
                  {showGreenery && <th scope="col">Greenery</th>}
                  {showTraffic && <th scope="col">Traffic</th>}

                </tr>
              </thead>
              <tbody>
                {routes.map((route) => {
                  const isSelected = route.id === selectedRouteId;
                  const rankInfo = route; // RankedRoute properties attached
                  const isRec = !!rankInfo.is_recommended;
                  const isDom = !!rankInfo.is_pareto_dominated;
                  const rank = rankInfo.rank || 1;
                  const score = typeof rankInfo.multi_criteria_score === 'number'
                    ? rankInfo.multi_criteria_score.toFixed(2)
                    : '—';

                  const rowData = comparisonRows.find((r) => r.route_id === route.id);

                  return (
                    <tr
                      key={route.id}
                      className={`table-row ${isSelected ? 'row-selected' : ''} ${isRec ? 'row-recommended' : ''}`}
                      onClick={() => onSelectRoute(route.id)}
                      tabIndex={0}
                      role="button"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectRoute(route.id);
                        }
                      }}
                    >
                      <td className="td-sticky">
                        <div className="route-cell-id">
                          <span
                            className="route-color-pill"
                            style={{ backgroundColor: route.color || '#2563eb' }}
                          ></span>
                          <span className="route-name-bold">{route.name}</span>
                          <span className="rank-tag">Rank #{rank}</span>
                        </div>
                      </td>

                      <td>
                        {isRec ? (
                          <span className="badge-status-pill rec">
                            <Award size={12} />
                            Recommended
                          </span>
                        ) : isDom ? (
                          <span className="badge-status-pill dom">
                            <AlertTriangle size={12} />
                            Dominated
                          </span>
                        ) : (
                          <span className="badge-status-pill pareto">
                            <CheckCircle2 size={12} />
                            Pareto-Optimal
                          </span>
                        )}
                      </td>

                      <td>
                        <div className="score-val-wrap">
                          <span className="score-pill-overall">{score}</span>
                        </div>
                      </td>

                      {showDistance && (
                        <td>
                          <div className="metric-dual-cell">
                            <span className="raw-val">{route.distance_km} km</span>
                            {rowData?.distance_score !== null && rowData?.distance_score !== undefined && (
                              <span className="score-val">{rowData.distance_score.toFixed(2)}</span>
                            )}
                          </div>
                        </td>
                      )}

                      {showDistance && (
                        <td>
                          <span className="raw-val">~{Math.round(route.duration_min)} min</span>
                        </td>
                      )}

                      {showAirQuality && (
                        <td>
                          <div className="metric-dual-cell">
                            {rowData?.air_quality_raw !== null && rowData?.air_quality_raw !== undefined ? (
                              <>
                                <span className="raw-val">{rowData.air_quality_raw} EAQI</span>
                                {rowData.air_quality_score !== null && rowData.air_quality_score !== undefined && (
                                  <span className="score-val">{rowData.air_quality_score.toFixed(2)}</span>
                                )}
                              </>
                            ) : (
                              <span className="missing-val">Unavailable</span>
                            )}
                          </div>
                        </td>
                      )}

                      {showWeather && (
                        <td>
                          <div className="metric-dual-cell">
                            {rowData?.temperature_c !== null && rowData?.temperature_c !== undefined ? (
                              <>
                                <span className="raw-val">{rowData.temperature_c} °C</span>
                                {rowData.temperature_score !== null && rowData.temperature_score !== undefined && (
                                  <span className="score-val">{rowData.temperature_score.toFixed(2)}</span>
                                )}
                              </>
                            ) : (
                              <span className="missing-val">Unavailable</span>
                            )}
                          </div>
                        </td>
                      )}

                      {showGreenery && (
                        <td>
                          <div className="metric-dual-cell">
                            {rowData?.greenery_raw !== null && rowData?.greenery_raw !== undefined ? (
                              <>
                                <span className="raw-val">{Math.round(rowData.greenery_raw)}%</span>
                                {rowData.greenery_score !== null && rowData.greenery_score !== undefined && (
                                  <span className="score-val">{rowData.greenery_score.toFixed(2)}</span>
                                )}
                              </>
                            ) : (
                              <span className="missing-val">Unavailable</span>
                            )}
                          </div>
                        </td>
                      )}

                      {showTraffic && (
                        <td>
                          <div className="metric-dual-cell">
                            {rowData?.traffic_score_raw !== null && rowData?.traffic_score_raw !== undefined ? (
                              <>
                                <span className="raw-val">{Math.round(rowData.traffic_score_raw)}</span>
                                {rowData.traffic_score !== null && rowData.traffic_score !== undefined && (
                                  <span className="score-val">{rowData.traffic_score.toFixed(2)}</span>
                                )}
                              </>
                            ) : (
                              <span className="missing-val">Unavailable</span>
                            )}
                          </div>
                        </td>
                      )}

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="table-footnote">
            <Info size={13} />
            <span>
              Click any row to focus and highlight that walking route on the map. Higher normalized score indicates superior desirability.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
