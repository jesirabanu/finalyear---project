/**
 * Geocoding Service
 * Interacts with the backend geocoding endpoint (/api/geocode),
 * which interfaces with OpenStreetMap Nominatim respecting rate limits,
 * caching, and custom User-Agent policies.
 */

/**
 * Searches for location suggestions matching the user's query.
 *
 * @param {string} query - The location query string (min 3 characters).
 * @param {AbortSignal} [signal] - Optional AbortSignal to cancel previous in-flight requests.
 * @returns {Promise<Array<{placeId: number, displayName: string, lat: number, lon: number}>>}
 */
export async function searchLocations(query, signal) {
  if (!query || query.trim().length < 3) {
    return [];
  }

  const endpoint = `/api/geocode?q=${encodeURIComponent(query.trim())}&limit=5`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error('Geocoding rate limit reached. Please wait a moment.');
      }
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Geocoding failed with status ${response.status}`);
    }

    const data = await response.json();
    return data.map((item) => ({
      placeId: item.place_id,
      displayName: item.display_name,
      lat: item.lat,
      lon: item.lon,
      type: item.type,
      importance: item.importance,
    }));
  } catch (error) {
    if (error.name === 'AbortError') {
      // In-flight request was aborted due to typing newer character; return empty
      return [];
    }
    console.error('Geocoding service error:', error);
    throw error;
  }
}

/**
 * Reverse geocodes coordinates into a human-readable location name.
 *
 * @param {number} lat - Latitude in decimal degrees.
 * @param {number} lon - Longitude in decimal degrees.
 * @param {AbortSignal} [signal] - Optional AbortSignal to cancel obsolete requests.
 * @returns {Promise<{placeId?: number, displayName: string, lat: number, lon: number, address?: Object}|null>}
 */
export async function reverseGeocode(lat, lon, signal) {
  if (typeof lat !== 'number' || typeof lon !== 'number') {
    throw new Error('Valid numerical latitude and longitude are required.');
  }

  const endpoint = `/api/geocode/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error('Geocoding rate limit reached. Please wait a moment.');
      }
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Reverse geocoding failed with status ${response.status}`);
    }

    const data = await response.json();
    return {
      placeId: data.place_id,
      displayName: data.display_name,
      lat: data.lat,
      lon: data.lon,
      address: data.address,
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      return null;
    }
    console.error('Reverse geocoding service error:', error);
    throw error;
  }
}

