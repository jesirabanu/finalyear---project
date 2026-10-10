/**
 * Routing Service
 * Handles communication with the FastAPI backend endpoint (/api/routes),
 * requesting pedestrian walking directions and genuine alternative routes.
 */

/**
 * Requests walking directions and alternative routes between origin and destination.
 *
 * @param {Object} params
 * @param {{lat: number, lon: number, label?: string}} params.origin - Origin coordinate
 * @param {{lat: number, lon: number, label?: string}} params.destination - Destination coordinate
 * @param {number} [params.alternatives=2] - Number of candidate alternative routes to request
 * @returns {Promise<{
 *   routes: Array<{
 *     id: string,
 *     name: string,
 *     distance_m: number,
 *     distance_km: number,
 *     duration_s: number,
 *     duration_min: number,
 *     coordinates: Array<[number, number]>,
 *     color: string,
 *     is_primary: boolean,
 *     summary?: string
 *   }>,
 *   total_routes: number,
 *   has_alternatives: boolean,
 *   message?: string
 * }>}
 */
export async function fetchWalkingRoutes({ origin, destination, alternatives = 2 }) {
  if (!origin || typeof origin.lat !== 'number' || typeof origin.lon !== 'number') {
    throw new Error('Please select a valid origin location with coordinates.');
  }
  if (!destination || typeof destination.lat !== 'number' || typeof destination.lon !== 'number') {
    throw new Error('Please select a valid destination location with coordinates.');
  }

  // Coordinate equality check
  const latDiff = Math.abs(origin.lat - destination.lat);
  const lonDiff = Math.abs(origin.lon - destination.lon);
  if (latDiff < 1e-5 && lonDiff < 1e-5) {
    throw new Error('Origin and destination are the same location. Please choose distinct points.');
  }

  const payload = {
    source: {
      lat: origin.lat,
      lon: origin.lon,
      label: origin.label || 'Origin',
    },
    destination: {
      lat: destination.lat,
      lon: destination.lon,
      label: destination.label || 'Destination',
    },
    alternatives: Math.min(Math.max(alternatives, 0), 3),
  };

  try {
    const response = await fetch('/api/routes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const detail = errorBody.detail || `Server responded with status ${response.status}`;

      if (response.status === 503) {
        throw new Error(`Configuration Required: ${detail}`);
      } else if (response.status === 404) {
        throw new Error(`Routing Error: ${detail}`);
      } else if (response.status === 401 || response.status === 403) {
        throw new Error(`Authentication Error: ${detail}`);
      } else if (response.status === 429) {
        throw new Error(`Rate Limit: ${detail}`);
      } else if (response.status === 504) {
        throw new Error('Request Timed Out: OpenRouteService took too long to respond. Please try again.');
      } else {
        throw new Error(detail);
      }
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Routing service request error:', error);
    throw error;
  }
}
