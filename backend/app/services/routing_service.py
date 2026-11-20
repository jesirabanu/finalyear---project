"""OpenRouteService Pedestrian Routing Service
Requests walking directions and genuine alternative routes from OpenRouteService.
Parses GeoJSON features into Leaflet-ready coordinates and metadata.
Strictly handles error states, rate limits, timeouts, and API key validation.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.algorithm.ranking_engine import rank_routes, compute_reevaluation_summary
from app.schemas.preferences import RouteRefreshRequest, RouteRefreshResponse
from app.schemas.routes import RouteModel, RouteRequest, RouteResponse
from app.services.environmental_service import enrich_routes_with_environmental_data
from app.services.greenery_service import enrich_routes_with_greenery_data
from app.services.traffic_service import enrich_routes_with_traffic_data

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


def populate_route_metadata(
    route: RouteModel,
    provider_name: str = "OpenRouteService Walking Directions (foot-walking)",
) -> None:
    """Populate consistent route data model fields: available metrics, units, timestamps,
    source metadata, data-quality status, and missing factors.
    """
    env = route.environment
    now_iso = datetime.now(timezone.utc).isoformat()

    metrics: Dict[str, Any] = {
        "walking_distance": route.distance_m,
    }
    units: Dict[str, str] = {
        "walking_distance": "m",
    }
    missing: List[str] = []

    # Air quality (prefer European AQI, fallback to PM2.5)
    if env and env.air_quality and env.air_quality.european_aqi and env.air_quality.european_aqi.value is not None:
        metrics["air_quality"] = env.air_quality.european_aqi.value
        units["air_quality"] = env.air_quality.european_aqi.unit or "EAQI"
    elif env and env.air_quality and env.air_quality.pm2_5 and env.air_quality.pm2_5.value is not None:
        metrics["air_quality"] = env.air_quality.pm2_5.value
        units["air_quality"] = env.air_quality.pm2_5.unit or "μg/m³"
    else:
        metrics["air_quality"] = None
        units["air_quality"] = "EAQI"
        missing.append("air_quality")

    # Temperature / heat (prefer apparent / feels-like temperature)
    if env and env.weather and env.weather.apparent_temperature_c is not None:
        metrics["temperature"] = env.weather.apparent_temperature_c
        units["temperature"] = "°C"
    elif env and env.weather and env.weather.temperature_c is not None:
        metrics["temperature"] = env.weather.temperature_c
        units["temperature"] = "°C"
    else:
        metrics["temperature"] = None
        units["temperature"] = "°C"
        missing.append("temperature")

    # Greenery
    if env and env.greenery and env.greenery.score is not None:
        metrics["greenery"] = env.greenery.score
        units["greenery"] = env.greenery.unit or "%"
    else:
        metrics["greenery"] = None
        units["greenery"] = "%"
        missing.append("greenery")

    # Traffic exposure
    if env and env.traffic_exposure and env.traffic_exposure.score is not None:
        metrics["traffic_exposure"] = env.traffic_exposure.score
        units["traffic_exposure"] = env.traffic_exposure.unit or "index (0-100)"
    else:
        metrics["traffic_exposure"] = None
        units["traffic_exposure"] = "index (0-100)"
        missing.append("traffic_exposure")

    # Status determination
    if len(missing) == 0:
        dq_status = "complete"
    elif len(missing) >= 3:
        dq_status = "insufficient_data"
    else:
        dq_status = "partial_data"

    route.available_environmental_metrics = metrics
    route.metric_units = units
    route.missing_factors = missing
    route.data_quality_status = dq_status
    route.timestamps = {
        "retrieval_timestamp": env.metadata.retrieval_timestamp if env else now_iso,
        "forecast_timestamp": env.metadata.forecast_timestamp if env else None,
        "observation_or_forecast_timestamp": getattr(env.metadata, "observation_or_forecast_timestamp", None) if env else None,
        "is_forecast": getattr(env.metadata, "is_forecast", False) if env else False,
        "departure_time": getattr(env.metadata, "departure_time", None) if env else None,
        "is_stale": getattr(env.metadata, "is_stale", False) if env else False,
        "stale_warning": getattr(env.metadata, "stale_warning", None) if env else None,
        "cache_age_seconds": getattr(env.metadata, "cache_age_seconds", None) if env else None,
    }
    route.source_metadata = {
        "routing_provider": provider_name,
        "weather_provider": env.metadata.weather_source if env else "Open-Meteo Weather",
        "air_quality_provider": env.metadata.air_quality_source if env else "Open-Meteo Air Quality (Copernicus CAMS)",
        "spatial_resolution": env.metadata.spatial_resolution_note if env else "Regional grid",
        "is_modeled": env.metadata.is_modeled if env else True,
    }
    if env and env.greenery:
        route.source_metadata["greenery_source"] = env.greenery.source
        route.source_metadata["greenery_limitation"] = env.greenery.limitation_note
    if env and env.traffic_exposure:
        route.source_metadata["traffic_source"] = env.traffic_exposure.source
        route.source_metadata["traffic_type"] = env.traffic_exposure.metric_type
        route.source_metadata["traffic_is_live"] = env.traffic_exposure.is_live_measurement
        route.source_metadata["traffic_limitation"] = env.traffic_exposure.limitation_note


def _parse_osrm_route(
    idx: int,
    route_data: Dict[str, Any],
    primary_distance: float = 0.0,
) -> RouteModel:
    """Parse raw GeoJSON route dictionary returned by OSRM into a validated RouteModel."""
    geom = route_data.get("geometry", {})
    raw_coords = geom.get("coordinates", [])

    # Invert [lon, lat] -> [lat, lon] for Leaflet
    leaflet_coords: List[List[float]] = [
        [float(pt[1]), float(pt[0])] for pt in raw_coords if len(pt) >= 2
    ]

    dist_m = float(route_data.get("distance", 0.0))
    dur_s = float(route_data.get("duration", 0.0))

    color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
    is_primary = (idx == 0)
    route_name = (
        "Route 1: Primary Walking Route"
        if is_primary
        else f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
    )

    summary = (
        "Shortest direct pedestrian path"
        if is_primary
        else f"Alternative pedestrian detour (+{round((dist_m - primary_distance) / 1000.0, 2)} km)"
        if primary_distance > 0
        else "Alternative path"
    )

    return RouteModel(
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
        summary=summary,
    )


async def _fetch_osrm_walking_routes(request: RouteRequest) -> List[RouteModel]:
    """Fetch pedestrian walking paths from OSRM as an automatic high-availability fallback."""
    osrm_base = getattr(settings, "OSRM_ROUTING_URL", "https://router.project-osrm.org/route/v1/foot")
    routes: List[RouteModel] = []

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Primary direct walking route
        primary_url = f"{osrm_base}/{request.source.lon},{request.source.lat};{request.destination.lon},{request.destination.lat}?overview=full&geometries=geojson&alternatives=true"
        try:
            resp = await client.get(primary_url)
            if resp.status_code == 200:
                osrm_routes = resp.json().get("routes", [])
                for idx, r in enumerate(osrm_routes):
                    p_dist = routes[0].distance_m if routes else 0.0
                    routes.append(_parse_osrm_route(idx, r, primary_distance=p_dist))
        except Exception as exc:
            logger.warning(f"OSRM primary route query error: {exc}")

        if not routes:
            raise HTTPException(
                status_code=404,
                detail="No pedestrian route found between the specified coordinates.",
            )

        # 2. If user requested alternatives and OSRM returned fewer than requested, compute lateral detour waypoints
        if request.alternatives > 0 and len(routes) < request.alternatives + 1:
            mid_lon = (request.source.lon + request.destination.lon) / 2.0
            mid_lat = (request.source.lat + request.destination.lat) / 2.0
            dx = request.destination.lon - request.source.lon
            dy = request.destination.lat - request.source.lat

            offsets = [(-0.35, 0.35), (0.35, -0.35)]
            target_count = min(request.alternatives + 1, 3)

            for factor_x, factor_y in offsets:
                if len(routes) >= target_count:
                    break
                w_lon = mid_lon + dy * factor_x
                w_lat = mid_lat + dx * factor_y
                alt_url = f"{osrm_base}/{request.source.lon},{request.source.lat};{w_lon:.6f},{w_lat:.6f};{request.destination.lon},{request.destination.lat}?overview=full&geometries=geojson"
                try:
                    alt_resp = await client.get(alt_url)
                    if alt_resp.status_code == 200:
                        alt_data = alt_resp.json().get("routes", [])
                        if alt_data:
                            routes.append(
                                _parse_osrm_route(
                                    len(routes),
                                    alt_data[0],
                                    primary_distance=routes[0].distance_m,
                                )
                            )
                except Exception as exc:
                    logger.debug(f"OSRM alternative waypoint error: {exc}")

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

    parsed_routes: List[RouteModel] = []
    used_provider = "OpenRouteService Walking Directions (foot-walking)"

    async with httpx.AsyncClient(timeout=8.0) as client:
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

            if response.status_code == 200:
                data = response.json()
                features = data.get("features", [])
                if features:
                    parsed_routes = _parse_ors_features(features)
            elif response.status_code == 401 or response.status_code == 403:
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

        except HTTPException:
            raise
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(
                f"OpenRouteService connection issue ({exc}). Activating OSRM pedestrian routing fallback."
            )
            try:
                parsed_routes = await _fetch_osrm_walking_routes(request)
                used_provider = "OSRM (Open Source Routing Machine - Foot)"
            except HTTPException:
                raise
            except Exception:
                if isinstance(exc, httpx.TimeoutException):
                    raise HTTPException(
                        status_code=504,
                        detail="OpenRouteService directions request timed out. Please try again.",
                    )
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to communicate with OpenRouteService: {str(exc)}",
                )

    if not parsed_routes:
        # Fallback to OSRM if ORS features were empty
        try:
            parsed_routes = await _fetch_osrm_walking_routes(request)
            used_provider = "OSRM (Open Source Routing Machine - Foot)"
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=404,
                detail="OpenRouteService returned no route geometry for the given coordinates.",
            )

    # Enrich parsed walking routes with real environmental data in batch
    try:
        await enrich_routes_with_environmental_data(
            parsed_routes, time_str=request.departure_time, force_refresh=request.force_refresh
        )
    except Exception as env_err:
        logger.warning(f"Environmental enrichment error (non-fatal): {env_err}")

    # Enrich candidate routes with Overpass greenery metrics
    try:
        await enrich_routes_with_greenery_data(parsed_routes)
    except Exception as green_err:
        logger.warning(f"Greenery enrichment error (non-fatal): {green_err}")

    # Enrich candidate routes with traffic exposure metrics
    try:
        await enrich_routes_with_traffic_data(parsed_routes, departure_time=request.departure_time)
    except Exception as traffic_err:
        logger.warning(f"Traffic enrichment error (non-fatal): {traffic_err}")

    # Populate consistent route data model for every candidate route
    for route in parsed_routes:
        populate_route_metadata(route, provider_name=used_provider)

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


async def refresh_route_environments(request: RouteRefreshRequest) -> RouteRefreshResponse:
    """Refresh only the environmental data for candidate routes without re-requesting ORS directions.

    Recalculates route-level metrics and rankings, explains data changes and recommendation impact,
    and returns a transparent re-evaluation summary.
    """
    routes = [RouteModel(**r.model_dump()) for r in request.routes]
    old_rank_1_id = routes[0].id if routes else None

    # Refresh environmental data (with force_refresh to query providers fresh)
    try:
        await enrich_routes_with_environmental_data(
            routes, time_str=request.departure_time, force_refresh=request.force_refresh
        )
    except Exception as exc:
        logger.warning(f"Environmental refresh error: {exc}")

    # Refresh traffic metrics
    try:
        await enrich_routes_with_traffic_data(routes, departure_time=request.departure_time)
    except Exception as exc:
        logger.warning(f"Traffic refresh error: {exc}")

    for r in routes:
        populate_route_metadata(r)

    # Re-rank routes with active preferences
    ranking_result = rank_routes(routes, request.preferences)

    # Compute explicit reevaluation diff
    reevaluation = compute_reevaluation_summary(
        old_routes=request.routes,
        new_ranking=ranking_result,
        old_rank_1_id=old_rank_1_id,
    )

    return RouteRefreshResponse(
        routes=routes,
        ranking=ranking_result,
        reevaluation=reevaluation,
    )
