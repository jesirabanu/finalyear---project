"""API Routes
Defines API endpoints including system health, pedestrian routing, and geocoding.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Query
from app.core.config import settings
from app.schemas.environment import SinglePointEnvironmentResponse
from app.schemas.geocoding import GeocodeResult
from app.schemas.preferences import (
    RouteRankingRequest,
    RouteRankingResponse,
    RouteRefreshRequest,
    RouteRefreshResponse,
)
from app.schemas.routes import RouteRequest, RouteResponse
from app.algorithm.ranking_engine import rank_routes
from app.services.environmental_service import get_point_environmental_data
from app.services.geocoding_service import search_locations
from app.services.routing_service import get_walking_routes, refresh_route_environments

router = APIRouter()


@router.get("/health", summary="System Health Check")
async def health_check():
    """Returns the health status of the backend API,
    along with configuration status for external services.
    """
    ors_configured = bool(
        settings.ORS_API_KEY
        and settings.ORS_API_KEY.strip()
        and settings.ORS_API_KEY != "your_openrouteservice_api_key_here"
    )

    return {
        "status": "ok",
        "service": "AI-Driven Pedestrian Routing API",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integrations": {
            "openrouteservice": {
                "name": "OpenRouteService Walking API",
                "configured": ors_configured,
                "note": (
                    "Required for routing. Add ORS_API_KEY in backend/.env"
                    if not ors_configured
                    else "API key detected"
                ),
            },
            "nominatim_geocoding": {
                "name": "OpenStreetMap Nominatim Geocoding",
                "configured": True,
                "note": "Public API with 1 req/sec rate limit & custom User-Agent",
            },
            "open_meteo_weather": {
                "name": "Open-Meteo Weather API",
                "configured": True,
                "note": "Public API (no key required)",
            },
            "open_meteo_air_quality": {
                "name": "Open-Meteo Air Quality API",
                "configured": True,
                "note": "Public API (no key required)",
            },
            "overpass_osm": {
                "name": "Overpass Greenery & Parks API",
                "configured": True,
                "endpoint": settings.OVERPASS_API_URL,
            },
            "traffic_exposure": {
                "name": "Traffic Exposure Service",
                "configured": True,
                "mode": (
                    "Live Traffic API (TomTom)"
                    if bool(settings.TOMTOM_TRAFFIC_API_KEY and settings.TOMTOM_TRAFFIC_API_KEY.strip())
                    else "Static Road Hierarchy Proxy (OpenStreetMap)"
                ),
                "is_live": bool(settings.TOMTOM_TRAFFIC_API_KEY and settings.TOMTOM_TRAFFIC_API_KEY.strip()),
                "note": (
                    "Optional live traffic key detected"
                    if bool(settings.TOMTOM_TRAFFIC_API_KEY and settings.TOMTOM_TRAFFIC_API_KEY.strip())
                    else "Operating in defensible static major-road proximity proxy mode"
                ),
            },
        },
    }


@router.post(
    "/routes",
    response_model=RouteResponse,
    summary="Find Walking Routes and Alternatives",
    description=(
        "Accepts source and destination coordinates, requests walking routes from "
        "OpenRouteService, parses candidate routes and genuine alternatives, and returns "
        "coordinates formatted directly for Leaflet polylines ([latitude, longitude])."
    ),
)
async def get_routes_endpoint(payload: RouteRequest):
    """Calculate pedestrian walking routes with alternatives."""
    return await get_walking_routes(payload)


@router.post(
    "/routes/refresh",
    response_model=RouteRefreshResponse,
    summary="Refresh Route Environmental Data and Re-evaluate",
    description=(
        "Refreshes environmental data (air quality, temperature, traffic, greenery) for existing "
        "candidate routes without re-requesting ORS directions. Re-evaluates rankings against "
        "preferences, generates change explanation, and produces data freshness provenance."
    ),
)
async def refresh_routes_endpoint(payload: RouteRefreshRequest):
    """Refresh only environmental data and re-evaluate candidate routes."""
    return await refresh_route_environments(payload)


@router.get(
    "/geocode",
    response_model=List[GeocodeResult],
    summary="Search Locations via Geocoding",
    description=(
        "Searches for address and location suggestions using OpenStreetMap Nominatim, "
        "enforcing rate limiting (max 1 req/sec) and application identification."
    ),
)
async def geocode_endpoint(
    q: str = Query(..., min_length=3, description="Search query string (min 3 chars)"),
    limit: int = Query(default=5, ge=1, le=10, description="Maximum number of results to return"),
):
    """Geocode search query into matching location candidates."""
    return await search_locations(query=q, limit=limit)


@router.get(
    "/environment",
    response_model=SinglePointEnvironmentResponse,
    summary="Get Environmental Metrics for Coordinate",
    description=(
        "Retrieves real air quality (PM2.5, PM10, NO2, European AQI) and meteorological conditions "
        "(temperature, feels-like, humidity, wind, weather code) from Open-Meteo for given coordinates "
        "and optional timestamp."
    ),
)
async def get_environment_endpoint(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    time: Optional[str] = Query(default=None, description="Optional ISO 8601 timestamp (e.g. 2026-10-10T12:00:00Z)"),
):
    """Retrieve environmental conditions from Open-Meteo for coordinates."""
    return await get_point_environmental_data(lat=lat, lon=lon, time_str=time)


@router.post(
    "/rank",
    response_model=RouteRankingResponse,
    summary="Rank Walking Routes by Multi-Criteria Preferences",
    description=(
        "Evaluates candidate walking routes against user-selected preferences (air quality, "
        "temperature/heat, traffic exposure, greenery, walking distance) using a deterministic "
        "equal-priority normalized model and formal Pareto-dominance analysis. "
        "Eliminates manual numerical weight guessing and handles missing data transparently."
    ),
)
async def rank_routes_endpoint(payload: RouteRankingRequest):
    """Rank candidate walking routes using multi-criteria preference engine."""
    return rank_routes(payload.routes, payload.preferences)

