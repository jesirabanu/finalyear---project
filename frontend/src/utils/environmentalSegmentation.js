/**
 * Environmental Route Segmentation Utilities
 *
 * Divides route coordinates into macro-segments corresponding to representative
 * sample points and associates each with metric-specific color scales.
 */

export const METRIC_CONFIGS = {
  default: {
    id: 'default',
    label: 'Route Colors',
    sublabel: 'Standard',
    unit: '',
  },
  air_quality: {
    id: 'air_quality',
    label: 'Air Quality',
    sublabel: 'EAQI',
    unit: 'EAQI',
    legend: [
      { label: 'Good (0-20)', color: '#10b981' },
      { label: 'Fair (21-40)', color: '#3b82f6' },
      { label: 'Moderate (41-60)', color: '#f59e0b' },
      { label: 'Poor (61-80)', color: '#ef4444' },
      { label: 'Very Poor (81+)', color: '#9333ea' },
      { label: 'No Data', color: '#94a3b8' },
    ],
  },
  temperature: {
    id: 'temperature',
    label: 'Temperature',
    sublabel: '°C',
    unit: '°C',
    legend: [
      { label: '< 5°C (Cold)', color: '#3b82f6' },
      { label: '5-14°C (Cool)', color: '#06b6d4' },
      { label: '15-22°C (Mild)', color: '#10b981' },
      { label: '23-28°C (Warm)', color: '#f59e0b' },
      { label: '> 28°C (Hot)', color: '#ef4444' },
      { label: 'No Data', color: '#94a3b8' },
    ],
  },
  greenery: {
    id: 'greenery',
    label: 'Greenery',
    sublabel: '% Score',
    unit: '%',
    legend: [
      { label: 'Dense (75-100%)', color: '#15803d' },
      { label: 'Good (50-75%)', color: '#22c55e' },
      { label: 'Moderate (25-50%)', color: '#86efac' },
      { label: 'Sparse (0-25%)', color: '#cbd5e1' },
      { label: 'No Data', color: '#94a3b8' },
    ],
  },
  traffic_exposure: {
    id: 'traffic_exposure',
    label: 'Traffic Exposure',
    sublabel: 'Exposure Index',
    unit: '/100',
    legend: [
      { label: 'Quiet (0-30)', color: '#10b981' },
      { label: 'Moderate (31-60)', color: '#f59e0b' },
      { label: 'Heavy (61-100)', color: '#ef4444' },
      { label: 'No Data', color: '#94a3b8' },
    ],
  },
};

export function getAirQualityColor(aqi) {
  if (aqi === null || aqi === undefined || isNaN(aqi)) return '#94a3b8';
  if (aqi <= 20) return '#10b981';
  if (aqi <= 40) return '#3b82f6';
  if (aqi <= 60) return '#f59e0b';
  if (aqi <= 80) return '#ef4444';
  if (aqi <= 100) return '#9333ea';
  return '#7e22ce';
}

export function getAirQualityCategory(aqi) {
  if (aqi === null || aqi === undefined || isNaN(aqi)) return 'Unknown';
  if (aqi <= 20) return 'Good';
  if (aqi <= 40) return 'Fair';
  if (aqi <= 60) return 'Moderate';
  if (aqi <= 80) return 'Poor';
  if (aqi <= 100) return 'Very Poor';
  return 'Extremely Poor';
}

export function getTemperatureColor(temp) {
  if (temp === null || temp === undefined || isNaN(temp)) return '#94a3b8';
  if (temp < 5) return '#3b82f6';
  if (temp < 15) return '#06b6d4';
  if (temp <= 22) return '#10b981';
  if (temp <= 28) return '#f59e0b';
  return '#ef4444';
}

export function getGreeneryColor(score) {
  if (score === null || score === undefined || isNaN(score)) return '#94a3b8';
  if (score < 25) return '#cbd5e1';
  if (score < 50) return '#86efac';
  if (score < 75) return '#22c55e';
  return '#15803d';
}

export function getTrafficColor(score) {
  if (score === null || score === undefined || isNaN(score)) return '#94a3b8';
  if (score <= 30) return '#10b981';
  if (score <= 60) return '#f59e0b';
  return '#ef4444';
}

/**
 * Builds continuous macro-segments for a route corresponding to its sampled environmental readings.
 *
 * @param {Object} route - The route object containing `coordinates` and `environment.sample_points`.
 * @param {string} metricId - The selected metric ('default', 'air_quality', 'temperature', 'greenery', 'traffic_exposure').
 * @returns {Array<Object>} List of segment objects with `coordinates`, `color`, `metricValue`, `metricDisplay`, and `isMissing`.
 */
export function buildRouteSegments(route, metricId = 'default') {
  if (!route || !Array.isArray(route.coordinates) || route.coordinates.length < 2) {
    return [];
  }

  const coords = route.coordinates;
  const n = coords.length;
  const samplePoints = route.environment?.sample_points || [];

  // Default metric or no sample points: render single unbroken route polyline
  if (metricId === 'default' || samplePoints.length === 0) {
    return [
      {
        coordinates: coords,
        color: route.color || '#2563eb',
        metricValue: null,
        metricDisplay: 'Standard Route',
        metricLabel: 'Route',
        isMissing: false,
        sampleIndex: 0,
      },
    ];
  }

  // Linear referencing: map each sample point to its coordinate index along route
  const sampleIndices = samplePoints.map((pt) => {
    if (typeof pt.point_index === 'number' && pt.point_index >= 0 && pt.point_index < n) {
      return pt.point_index;
    }
    // Fallback spatial distance match if point_index is absent or invalid
    let bestIdx = 0;
    let minDist = Infinity;
    for (let i = 0; i < n; i++) {
      const dLat = coords[i][0] - pt.lat;
      const dLon = coords[i][1] - pt.lon;
      const distSq = dLat * dLat + dLon * dLon;
      if (distSq < minDist) {
        minDist = distSq;
        bestIdx = i;
      }
    }
    return bestIdx;
  });

  const k = samplePoints.length;

  // Single sample point covers the full route
  if (k === 1) {
    const pt = samplePoints[0];
    const metricInfo = extractSampleMetric(pt, route, metricId);
    return [
      {
        coordinates: coords,
        color: metricInfo.color,
        metricValue: metricInfo.value,
        metricDisplay: metricInfo.display,
        metricLabel: METRIC_CONFIGS[metricId]?.label || 'Metric',
        isMissing: metricInfo.isMissing,
        sampleIndex: 0,
      },
    ];
  }

  // Calculate continuous boundary indices: [0, mid_01, mid_12, ..., n-1]
  const boundaries = [0];
  for (let i = 0; i < k - 1; i++) {
    const rawMid = Math.floor((sampleIndices[i] + sampleIndices[i + 1]) / 2);
    // Guarantee strictly increasing boundaries within valid coordinate range
    const bound = Math.max(boundaries[boundaries.length - 1] + 1, Math.min(rawMid, n - 2));
    boundaries.push(bound);
  }
  boundaries.push(n - 1);

  const segments = [];
  for (let i = 0; i < k; i++) {
    const startIdx = boundaries[i];
    const endIdx = boundaries[i + 1];

    if (startIdx >= endIdx) continue;

    // Slicing to endIdx + 1 ensures consecutive segments connect with zero gaps
    const segCoords = coords.slice(startIdx, endIdx + 1);
    if (segCoords.length < 2) continue;

    const pt = samplePoints[i];
    const metricInfo = extractSampleMetric(pt, route, metricId);

    segments.push({
      coordinates: segCoords,
      color: metricInfo.color,
      metricValue: metricInfo.value,
      metricDisplay: metricInfo.display,
      metricLabel: METRIC_CONFIGS[metricId]?.label || 'Metric',
      isMissing: metricInfo.isMissing,
      sampleIndex: i,
    });
  }

  return segments.length > 0
    ? segments
    : [
        {
          coordinates: coords,
          color: route.color || '#2563eb',
          metricValue: null,
          metricDisplay: 'Standard Route',
          metricLabel: 'Route',
          isMissing: false,
          sampleIndex: 0,
        },
      ];
}

/**
 * Helper to safely extract metric value and color without fabricating missing data.
 */
function extractSampleMetric(samplePoint, route, metricId) {
  let color = '#94a3b8';
  let value = null;
  let display = 'No Data';
  let isMissing = true;

  if (!samplePoint) {
    return { color, value, display, isMissing };
  }

  if (metricId === 'air_quality') {
    const aqi = samplePoint.air_quality?.european_aqi?.value;
    const pm25 = samplePoint.air_quality?.pm2_5?.value;

    if (typeof aqi === 'number' && !isNaN(aqi)) {
      value = aqi;
      color = getAirQualityColor(aqi);
      const cat = samplePoint.air_quality?.european_aqi?.category || getAirQualityCategory(aqi);
      display = `${aqi} EAQI (${cat})`;
      isMissing = false;
    } else if (typeof pm25 === 'number' && !isNaN(pm25)) {
      value = pm25;
      color = getAirQualityColor(pm25 * 2);
      display = `${pm25} µg/m³ PM2.5`;
      isMissing = false;
    }
  } else if (metricId === 'temperature') {
    const temp = samplePoint.weather?.temperature_c;
    if (typeof temp === 'number' && !isNaN(temp)) {
      value = temp;
      color = getTemperatureColor(temp);
      display = `${temp}°C`;
      isMissing = false;
    }
  } else if (metricId === 'greenery') {
    // If point has greenery score, use it; otherwise fallback to route-level greenery if available
    const green = samplePoint.greenery?.score ?? route?.environment?.greenery?.score;
    if (typeof green === 'number' && !isNaN(green)) {
      value = green;
      color = getGreeneryColor(green);
      display = `${Math.round(green)}%`;
      isMissing = false;
    }
  } else if (metricId === 'traffic_exposure') {
    // If point has traffic score, use it; otherwise fallback to route-level traffic if available
    const traffic = samplePoint.traffic_exposure?.score ?? route?.environment?.traffic_exposure?.score;
    if (typeof traffic === 'number' && !isNaN(traffic)) {
      value = traffic;
      color = getTrafficColor(traffic);
      display = `${Math.round(traffic)}/100`;
      isMissing = false;
    }
  }

  return { color, value, display, isMissing };
}
