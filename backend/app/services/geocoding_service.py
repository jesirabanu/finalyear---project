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
from app.schemas.geocoding import GeocodeResult

logger = logging.getLogger(__name__)

# In-memory cache: normalized query -> (timestamp, List[GeocodeResult])
_geocode_cache: Dict[str, Tuple[float, List[GeocodeResult]]] = {}
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
