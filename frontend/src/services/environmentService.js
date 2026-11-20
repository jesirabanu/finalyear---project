/**
 * Environmental Data Service
 * Client module for querying Open-Meteo atmospheric and weather data
 * from the FastAPI backend (/api/environment).
 */

/**
 * Fetches point-level environmental metrics from the backend.
 *
 * @param {Object} params
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lon - Longitude in decimal degrees
 * @param {string} [params.time] - Optional ISO 8601 timestamp
 * @returns {Promise<Object>} Environmental data object
 */
export async function fetchPointEnvironment({ lat, lon, time }) {
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    throw new Error('Valid numeric coordinates are required.');
  }

  let url = `/api/environment?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
  if (time) {
    url += `&time=${encodeURIComponent(time)}`;
  }

  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Environmental API returned status ${response.status}`);
  }

  return response.json();
}

/**
 * Returns a human-friendly label and color for European AQI.
 *
 * @param {number|null} aqi - European AQI value
 * @returns {{ category: string, color: string }}
 */
export function getEaqiMeta(aqi) {
  if (aqi === null || aqi === undefined) {
    return { category: 'Unavailable', color: '#94a3b8' };
  }
  if (aqi <= 20) return { category: 'Good', color: '#10b981' };
  if (aqi <= 40) return { category: 'Fair', color: '#3b82f6' };
  if (aqi <= 60) return { category: 'Moderate', color: '#f59e0b' };
  if (aqi <= 80) return { category: 'Poor', color: '#ef4444' };
  if (aqi <= 100) return { category: 'Very Poor', color: '#9333ea' };
  return { category: 'Extremely Poor', color: '#7e22ce' };
}
