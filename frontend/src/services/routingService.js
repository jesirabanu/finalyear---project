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
export async function fetchWalkingRoutes({ origin, destination, alternatives = 2, departureTime = null, forceRefresh = false }) {
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
    departure_time: departureTime || null,
    force_refresh: !!forceRefresh,
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

/**
 * Evaluates and ranks candidate routes using the backend multi-criteria ranking engine.
 *
 * @param {Object} params
 * @param {Array<Object>} params.routes - List of candidate walking routes
 * @param {Object} params.preferences - Factor selections
 * @returns {Promise<{
 *   ranked_routes: Array<Object>,
 *   selected_factors: Array<string>,
 *   active_evaluation_factors: Array<string>,
 *   missing_selected_factors: Array<string>,
 *   is_default_evaluation: boolean,
 *   confidence: string,
 *   withheld_recommendation: boolean,
 *   algorithmic_explanation: string,
 *   comparison_matrix: Array<Object>,
 *   warnings: Array<string>
 * }>}
 */
export async function rankCandidateRoutes({ routes, preferences }) {
  if (!routes || routes.length === 0) {
    return null;
  }

  const payload = {
    routes,
    preferences: {
      air_quality: !preferences.no_preference && !!preferences.air_quality,
      temperature: !preferences.no_preference && !!preferences.temperature,
      traffic_exposure: !preferences.no_preference && !!preferences.traffic_exposure,
      greenery: !preferences.no_preference && !!preferences.greenery,
      walking_distance: !preferences.no_preference && !!preferences.walking_distance,
      no_preference: !!preferences.no_preference,
    },
  };

  try {
    const response = await fetch('/api/rank', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Ranking request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Route ranking service error:', error);
    throw error;
  }
}

/**
 * Refreshes only the environmental metrics (air quality, temperature, traffic, shade)
 * for existing candidate routes, bypassing cache and recalculating rankings.
 *
 * @param {Object} params
 * @param {Array<Object>} params.routes - Candidate routes to refresh
 * @param {Object} params.preferences - Preference factor toggles
 * @param {string|null} [params.departureTime] - ISO 8601 departure timestamp
 * @param {boolean} [params.forceRefresh=true] - Force fresh upstream query
 * @returns {Promise<{
 *   routes: Array<Object>,
 *   ranking: Object,
 *   reevaluation: {
 *     previous_recommended_route_id: string|null,
 *     new_recommended_route_id: string|null,
 *     recommendation_changed: boolean,
 *     recommendation_change_note: string,
 *     metric_changes: Array<Object>,
 *     has_changes: boolean,
 *     disclaimer: string
 *   }
 * }>}
 */
export async function refreshRouteEnvironments({ routes, preferences, departureTime = null, forceRefresh = true }) {
  if (!routes || routes.length === 0) {
    throw new Error('No candidate routes available to refresh.');
  }

  const payload = {
    routes,
    preferences: {
      air_quality: !preferences.no_preference && !!preferences.air_quality,
      temperature: !preferences.no_preference && !!preferences.temperature,
      traffic_exposure: !preferences.no_preference && !!preferences.traffic_exposure,
      greenery: !preferences.no_preference && !!preferences.greenery,
      walking_distance: !preferences.no_preference && !!preferences.walking_distance,
      no_preference: !!preferences.no_preference,
    },
    departure_time: departureTime || null,
    force_refresh: !!forceRefresh,
  };

  try {
    const response = await fetch('/api/routes/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Environmental refresh failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Route environment refresh error:', error);
    throw error;
  }
}

