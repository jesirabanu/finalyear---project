"""Geocoding Service
Interfaces with OpenStreetMap Nominatim with strict adherence to usage policies:
- Identifies application via configured User-Agent
- Enforces minimum 1.0s interval between outbound requests (rate limit)
- Implements an in-memory TTL query cache to eliminate duplicate requests
- Handles timeouts, errors, and empty results gracefully
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.schemas.geocoding import GeocodeResult, ReverseGeocodeResult

logger = logging.getLogger(__name__)

# In-memory cache: normalized query -> (timestamp, List[GeocodeResult])
_geocode_cache: Dict[str, Tuple[float, List[GeocodeResult]]] = {}
# In-memory cache: normalized coordinates -> (timestamp, ReverseGeocodeResult)
_reverse_geocode_cache: Dict[str, Tuple[float, ReverseGeocodeResult]] = {}
CACHE_TTL_SECONDS = 600.0  # 10 minutes

# Concurrency lock and timestamp for Nominatim 1 req/sec policy
_rate_limit_lock = asyncio.Lock()
_last_request_timestamp: float = 0.0


async def search_locations(query: str, limit: int = 5) -> List[GeocodeResult]:
    """Search for matching geographical locations via OpenStreetMap Nominatim.

    Args:
        query: Location query string (minimum 3 characters).
        limit: Maximum number of suggestions to return (1-10).

    Returns:
        List of parsed GeocodeResult items.

    Raises:
        HTTPException: If query is invalid, external service fails, or rate limits are reached.
    """
    clean_query = query.strip() if query else ""
    if len(clean_query) < 3:
        raise HTTPException(
            status_code=400,
            detail="Location search query must be at least 3 characters long."
        )

    norm_key = f"{clean_query.lower()}:{limit}"
    now = time.time()

    # Check cache
    if norm_key in _geocode_cache:
        cached_time, cached_results = _geocode_cache[norm_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            logger.debug(f"Serving geocoding cache for query: {clean_query}")
            return cached_results

    # Enforce Nominatim rate limit: maximum 1 request per second
    global _last_request_timestamp
    async with _rate_limit_lock:
        elapsed = time.time() - _last_request_timestamp
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_request_timestamp = time.time()

        params = {
            "q": clean_query,
            "format": "json",
            "limit": min(max(limit, 1), 10),
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": settings.NOMINATIM_USER_AGENT,
            "Accept-Language": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    settings.NOMINATIM_API_URL,
                    params=params,
                    headers=headers
                )

            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Geocoding rate limit reached with OpenStreetMap Nominatim. Please wait a moment."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Geocoding service returned status code {response.status_code}."
                )

            raw_data = response.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Geocoding service timed out. Please check your internet connection and try again."
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Unable to connect to geocoding service: {str(exc)}"
            )

    # Parse results
    results: List[GeocodeResult] = []
    if isinstance(raw_data, list):
        for item in raw_data:
            try:
                results.append(
                    GeocodeResult(
                        place_id=int(item["place_id"]),
                        display_name=item["display_name"],
                        lat=float(item["lat"]),
                        lon=float(item["lon"]),
                        type=item.get("type"),
                        importance=float(item["importance"]) if "importance" in item and item["importance"] is not None else None,
                    )
                )
            except (KeyError, ValueError, TypeError) as parse_err:
                logger.warning(f"Skipping malformed geocoding item: {parse_err}")
                continue

    # Update cache
    _geocode_cache[norm_key] = (time.time(), results)
    return results


async def reverse_geocode(lat: float, lon: float) -> ReverseGeocodeResult:
    """Reverse geocode coordinates into a human-readable location address via Nominatim.

    Args:
        lat: Latitude in decimal degrees (-90.0 to 90.0).
        lon: Longitude in decimal degrees (-180.0 to 180.0).

    Returns:
        Structured ReverseGeocodeResult with place_id, display_name, lat, lon, and address details.

    Raises:
        HTTPException: If coordinates are out of bounds, external service fails, or rate limits are reached.
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=400,
            detail="Latitude must be between -90 and 90, and longitude between -180 and 180."
        )

    # Normalize cache key by rounding to 5 decimal places (~1.1m precision)
    norm_key = f"{round(lat, 5):.5f},{round(lon, 5):.5f}"
    now = time.time()

    # Check cache
    if norm_key in _reverse_geocode_cache:
        cached_time, cached_result = _reverse_geocode_cache[norm_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            logger.debug(f"Serving reverse geocoding cache for coordinates: {norm_key}")
            return cached_result

    # Enforce Nominatim rate limit: maximum 1 request per second
    global _last_request_timestamp
    async with _rate_limit_lock:
        elapsed = time.time() - _last_request_timestamp
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_request_timestamp = time.time()

        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": settings.NOMINATIM_USER_AGENT,
            "Accept-Language": "en",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    settings.NOMINATIM_REVERSE_API_URL,
                    params=params,
                    headers=headers
                )

            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Geocoding rate limit reached with OpenStreetMap Nominatim. Please wait a moment."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Reverse geocoding service returned status code {response.status_code}."
                )

            raw_data = response.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Reverse geocoding service timed out. Please check your internet connection and try again."
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Unable to connect to reverse geocoding service: {str(exc)}"
            )

    if not isinstance(raw_data, dict):
        raise HTTPException(
            status_code=502,
            detail="Invalid response structure from reverse geocoding service."
        )

    if "error" in raw_data:
        raise HTTPException(
            status_code=404,
            detail=f"Reverse geocoding error: {raw_data['error']}"
        )

    place_id = None
    if "place_id" in raw_data and raw_data["place_id"] is not None:
        try:
            place_id = int(raw_data["place_id"])
        except (ValueError, TypeError):
            place_id = None

    display_name = raw_data.get("display_name")
    if not display_name or not isinstance(display_name, str):
        # Graceful fallback if display_name is missing or empty
        display_name = f"Location ({lat:.5f}, {lon:.5f})"

    address = raw_data.get("address") if isinstance(raw_data.get("address"), dict) else None

    # Parse response lat/lon or fallback to query coordinates
    try:
        resp_lat = float(raw_data["lat"]) if "lat" in raw_data else float(lat)
        resp_lon = float(raw_data["lon"]) if "lon" in raw_data else float(lon)
    except (ValueError, TypeError):
        resp_lat = float(lat)
        resp_lon = float(lon)

    result = ReverseGeocodeResult(
        place_id=place_id,
        display_name=display_name,
        lat=resp_lat,
        lon=resp_lon,
        address=address,
    )

    _reverse_geocode_cache[norm_key] = (time.time(), result)
    return result

