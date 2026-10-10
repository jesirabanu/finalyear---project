"""OpenRouteService Pedestrian Routing Service
Requests walking directions and genuine alternative routes from OpenRouteService.
Parses GeoJSON features into Leaflet-ready coordinates and metadata.
Strictly handles error states, rate limits, timeouts, and API key validation.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.schemas.routes import RouteModel, RouteRequest, RouteResponse
from app.services.environmental_service import enrich_routes_with_environmental_data

logger = logging.getLogger(__name__)

# Distinct color palette for rendering alternative routes on Leaflet
ROUTE_PALETTE = [
    "#2563eb",  # Primary Route: Royal Blue
    "#8b5cf6",  # Alternative A: Vibrant Purple
    "#0d9488",  # Alternative B: Dark Teal
    "#d97706",  # Alternative C: Amber Gold
]


def _is_api_key_configured() -> bool:
    """Check if a non-placeholder ORS_API_KEY is present."""
    key = settings.ORS_API_KEY.strip() if settings.ORS_API_KEY else ""
    return bool(key and key != "your_openrouteservice_api_key_here")


def _parse_ors_features(features: List[Dict[str, Any]]) -> List[RouteModel]:
    """Parse raw GeoJSON features returned by ORS into validated RouteModel instances.

    Converts [longitude, latitude] GeoJSON coordinate pairs into
    [latitude, longitude] pairs required by Leaflet Polylines.
    """
    routes: List[RouteModel] = []

    for idx, feat in enumerate(features):
        geom = feat.get("geometry", {})
        raw_coords = geom.get("coordinates", [])

        if not raw_coords:
            continue

        # Invert [lon, lat] -> [lat, lon] for Leaflet compatibility
        leaflet_coords: List[List[float]] = [
            [float(pt[1]), float(pt[0])] for pt in raw_coords if len(pt) >= 2
        ]

        props = feat.get("properties", {})
        summary = props.get("summary", {})
        dist_m = float(summary.get("distance", 0.0))
        dur_s = float(summary.get("duration", 0.0))

        color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
        is_primary = (idx == 0)
        route_name = (
            "Route 1: Primary Walking Route"
            if is_primary
            else f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
        )

        routes.append(
            RouteModel(
                id=f"route_{idx}",
                name=route_name,
                distance_m=round(dist_m, 1),
                distance_km=round(dist_m / 1000.0, 2),
                duration_s=round(dur_s, 1),
                duration_min=round(dur_s / 60.0, 1),
                coordinates=leaflet_coords,
                geojson_geometry=geom,
                color=color,
                is_primary=is_primary,
                summary=(
                    "Shortest direct pedestrian path"
                    if is_primary
                    else f"Alternative pedestrian detour (+{round((dist_m - routes[0].distance_m) / 1000.0, 2)} km)"
                    if idx > 0 and len(routes) > 0
                    else "Alternative path"
                ),
            )
        )

    return routes


async def get_walking_routes(request: RouteRequest) -> RouteResponse:
    """Fetch real walking routes and alternatives from OpenRouteService.

    Args:
        request: RouteRequest with validated source, destination, and alternatives count.

    Returns:
        RouteResponse containing parsed routes and metadata.

    Raises:
        HTTPException:
            - 503 if ORS_API_KEY is not configured
            - 400/404 if no walking route is found between points
            - 401 if API key authentication fails
            - 429 if rate limits are exceeded
            - 504 on gateway timeout
            - 502 on network/connection failure
    """
    if not _is_api_key_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenRouteService API key is missing or not configured. "
                "Please configure ORS_API_KEY in backend/.env to calculate walking directions."
            ),
        )

    headers = {
        "Authorization": settings.ORS_API_KEY.strip(),
        "Content-Type": "application/json",
        "Accept": "application/json, application/geo+json",
    }

    # ORS requires [[longitude, latitude], [longitude, latitude]]
    base_coords = [
        [request.source.lon, request.source.lat],
        [request.destination.lon, request.destination.lat],
    ]

    # Build request payload with alternative_routes if requested
    payload: Dict[str, Any] = {
        "coordinates": base_coords,
    }

    wants_alternatives = request.alternatives > 0
    if wants_alternatives:
        # target_count specifies total number of candidate paths (primary + alternatives)
        payload["alternative_routes"] = {
            "target_count": min(request.alternatives + 1, 3),
            "weight_factor": 1.4,
            "share_factor": 0.6,
        }

    async with httpx.AsyncClient(timeout=14.0) as client:
        try:
            response = await client.post(
                settings.ORS_API_URL,
                json=payload,
                headers=headers,
            )

            # If ORS failed because alternative_routes was requested for an unsupported route
            # (e.g. distance > 100km or dense restrictions), fallback to standard primary route
            if wants_alternatives and response.status_code == 400:
                err_text = response.text.lower()
                if "alternative" in err_text or "100" in err_text:
                    logger.warning(
                        "Alternative routes request rejected by ORS. Retrying primary route only."
                    )
                    payload.pop("alternative_routes", None)
                    response = await client.post(
                        settings.ORS_API_URL,
                        json=payload,
                        headers=headers,
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="OpenRouteService directions request timed out. Please try again.",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to communicate with OpenRouteService: {str(exc)}",
            )

    # Handle provider HTTP status codes
    if response.status_code == 401 or response.status_code == 403:
        raise HTTPException(
            status_code=401,
            detail="OpenRouteService authorization failed. Please check that your ORS_API_KEY in backend/.env is valid.",
        )
    elif response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="OpenRouteService rate limit reached. Please wait a moment before calculating more routes.",
        )
    elif response.status_code != 200:
        error_msg = "No pedestrian route found between the specified coordinates."
        try:
            err_data = response.json()
            if "error" in err_data:
                err_detail = err_data["error"]
                if isinstance(err_detail, dict) and "message" in err_detail:
                    error_msg = f"Routing provider error: {err_detail['message']}"
                elif isinstance(err_detail, str):
                    error_msg = f"Routing provider error: {err_detail}"
        except Exception:
            pass

        raise HTTPException(
            status_code=404 if response.status_code in (404, 400) else response.status_code,
            detail=error_msg,
        )

    # Parse JSON GeoJSON response
    data = response.json()
    features = data.get("features", [])

    if not features:
        raise HTTPException(
            status_code=404,
            detail="OpenRouteService returned no route geometry for the given coordinates.",
        )

    parsed_routes = _parse_ors_features(features)

    if not parsed_routes:
        raise HTTPException(
            status_code=404,
            detail="Failed to parse valid coordinate geometry from provider response.",
        )

    # Enrich parsed walking routes with real environmental data in batch
    try:
        await enrich_routes_with_environmental_data(parsed_routes)
    except Exception as env_err:
        logger.warning(f"Environmental enrichment error (non-fatal): {env_err}")

    has_alternatives = len(parsed_routes) > 1
    if has_alternatives:
        message = f"Found {len(parsed_routes)} walking routes (1 primary route and {len(parsed_routes) - 1} alternative(s))."
    else:
        message = "1 walking route found. OpenRouteService did not return any alternative pedestrian paths for this route."

    return RouteResponse(
        routes=parsed_routes,
        total_routes=len(parsed_routes),
        has_alternatives=has_alternatives,
        source=request.source,
        destination=request.destination,
        message=message,
    )
