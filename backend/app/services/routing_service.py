"""OpenRouteService Pedestrian Routing Service
Requests walking directions and genuine alternative routes from OpenRouteService.
Parses GeoJSON features into Leaflet-ready coordinates and metadata.
Strictly handles error states, rate limits, timeouts, and API key validation.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.algorithm.ranking_engine import rank_routes, compute_reevaluation_summary
from app.schemas.coordinates import CoordinatePoint
from app.schemas.preferences import RouteRefreshRequest, RouteRefreshResponse
from app.schemas.routes import RouteModel, RouteRequest, RouteResponse, RouteStepModel
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

# OpenRouteService step type code mapping to directional modifiers
ORS_TYPE_TO_MODIFIER: Dict[int, str] = {
    0: "left",
    1: "right",
    2: "sharp left",
    3: "sharp right",
    4: "slight left",
    5: "slight right",
    6: "straight",
    7: "enter roundabout",
    8: "exit roundabout",
    9: "u-turn",
    10: "arrive",
    11: "depart",
    12: "keep left",
    13: "keep right",
}


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, returning default on ValueError/TypeError."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def generate_perpendicular_waypoints(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
    factors: Optional[List[float]] = None,
) -> List[Dict[str, float]]:
    """Generate intermediate detour waypoints perpendicular to the direct route vector.

    Uses latitude-aware longitude scaling:
        Δlon = Δlat / cos(latitude)
    Accounting for the physical convergence of meridians away from the equator.

    Args:
        source_lat: Origin latitude in degrees.
        source_lon: Origin longitude in degrees.
        dest_lat: Destination latitude in degrees.
        dest_lon: Destination longitude in degrees.
        factors: List of signed lateral displacement factors relative to route length.
            Positive values displace to the left, negative values displace to the right.
            Defaults to [0.20, -0.20, 0.35, -0.35].

    Returns:
        List of dicts containing {"lat": float, "lon": float}.
    """
    if factors is None:
        factors = [0.20, -0.20, 0.35, -0.35]

    mid_lat = (source_lat + dest_lat) / 2.0
    mid_lon = (source_lon + dest_lon) / 2.0

    d_lat = dest_lat - source_lat
    d_lon = dest_lon - source_lon

    # Zero-length route safety check
    if abs(d_lat) < 1e-6 and abs(d_lon) < 1e-6:
        return []

    # Latitude-dependent longitude scaling
    # Bound latitude safely to avoid division by near-zero near poles
    clamped_mid_lat = max(min(mid_lat, 89.0), -89.0)
    cos_lat = math.cos(math.radians(clamped_mid_lat))
    cos_lat = max(abs(cos_lat), 0.02)  # Clamp near-polar cos(lat) for numerical stability

    # Direction vector in locally isotropic / metric-scaled coordinates
    v_y = d_lat
    v_x = d_lon * cos_lat

    length = math.hypot(v_x, v_y)
    if length < 1e-7:
        return []

    # Unit vector perpendicular to forward direction (rotated +90 deg counter-clockwise / left)
    perp_x = -v_y / length
    perp_y = v_x / length

    waypoints: List[Dict[str, float]] = []
    for factor in factors:
        if factor == 0.0:
            continue

        offset_dist = factor * length
        offset_x = perp_x * offset_dist
        offset_y = perp_y * offset_dist

        # Convert back from isotropic metric-scaled offset to geographic degree offsets
        delta_lat = offset_y
        delta_lon = offset_x / cos_lat

        w_lat = mid_lat + delta_lat
        w_lon = mid_lon + delta_lon

        # Enforce valid geographic coordinate boundaries
        w_lat = max(min(w_lat, 89.9), -89.9)
        # Normalize longitude to [-180, 180]
        w_lon = ((w_lon + 180.0) % 360.0) - 180.0

        waypoints.append({
            "lat": round(w_lat, 6),
            "lon": round(w_lon, 6),
        })

    return waypoints


def is_valid_pedestrian_route(
    candidate: RouteModel,
    source: CoordinatePoint,
    destination: CoordinatePoint,
    primary_distance_m: Optional[float] = None,
    max_detour_ratio: float = 2.5,
) -> bool:
    """Validate that a candidate route has valid geometry and connects endpoints."""
    if not candidate.coordinates or len(candidate.coordinates) < 2:
        return False

    if candidate.distance_m <= 0:
        return False

    # Check origin proximity (~2.5km / 0.025 degrees)
    start_lat, start_lon = candidate.coordinates[0][0], candidate.coordinates[0][1]
    if abs(start_lat - source.lat) > 0.025 or abs(start_lon - source.lon) > 0.025:
        return False

    # Check destination proximity
    end_lat, end_lon = candidate.coordinates[-1][0], candidate.coordinates[-1][1]
    if abs(end_lat - destination.lat) > 0.025 or abs(end_lon - destination.lon) > 0.025:
        return False

    # Avoid excessive detours
    if primary_distance_m and primary_distance_m > 0:
        if candidate.distance_m > primary_distance_m * max_detour_ratio:
            return False

    return True


def is_duplicate_route(
    candidate: RouteModel,
    existing_routes: List[RouteModel],
    distance_tolerance_ratio: float = 0.03,
) -> bool:
    """Determine whether a candidate route is effectively identical to an already accepted route."""
    for existing in existing_routes:
        dist_diff = abs(candidate.distance_m - existing.distance_m)
        dur_diff = abs(candidate.duration_s - existing.duration_s)
        max_dist = max(existing.distance_m, 1.0)
        max_dur = max(existing.duration_s, 1.0)

        if (dist_diff / max_dist) < distance_tolerance_ratio and (dur_diff / max_dur) < distance_tolerance_ratio:
            # Check midpoint coordinate similarity
            if candidate.coordinates and existing.coordinates:
                cand_mid = candidate.coordinates[len(candidate.coordinates) // 2]
                exist_mid = existing.coordinates[len(existing.coordinates) // 2]
                if abs(cand_mid[0] - exist_mid[0]) < 0.0005 and abs(cand_mid[1] - exist_mid[1]) < 0.0005:
                    return True

    return False


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

        # Extract turn-by-turn walking maneuver steps from segments
        steps: List[RouteStepModel] = []
        segments = props.get("segments", [])
        if isinstance(segments, list):
            for seg in segments:
                if not isinstance(seg, dict):
                    continue
                seg_steps = seg.get("steps", [])
                if not isinstance(seg_steps, list):
                    continue
                for s in seg_steps:
                    if not isinstance(s, dict):
                        continue
                    type_code = s.get("type")
                    if isinstance(type_code, int):
                        mod = s.get("modifier") or ORS_TYPE_TO_MODIFIER.get(type_code)
                    else:
                        mod = s.get("modifier")

                    name = s.get("name")
                    instr = s.get("instruction")
                    if not instr:
                        if mod:
                            instr = f"Walk {mod}" + (f" on {name}" if name else "")
                        elif name:
                            instr = f"Proceed on {name}"
                        else:
                            instr = "Continue along the walking path"

                    way_pts = s.get("way_points")
                    loc = None
                    if isinstance(way_pts, list) and len(way_pts) >= 1 and isinstance(way_pts[0], int):
                        start_idx = way_pts[0]
                        if 0 <= start_idx < len(leaflet_coords):
                            loc = leaflet_coords[start_idx]

                    valid_way_pts = (
                        [int(x) for x in way_pts]
                        if isinstance(way_pts, list) and all(isinstance(x, (int, float)) for x in way_pts)
                        else None
                    )

                    steps.append(
                        RouteStepModel(
                            instruction=str(instr),
                            distance_m=round(_safe_float(s.get("distance")), 1),
                            duration_s=round(_safe_float(s.get("duration")), 1),
                            type=type_code if isinstance(type_code, int) else None,
                            modifier=str(mod) if mod else None,
                            name=str(name) if name else None,
                            location=loc,
                            way_points=valid_way_pts,
                        )
                    )

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
                steps=steps,
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

    # Extract turn-by-turn walking maneuver steps from OSRM legs
    steps: List[RouteStepModel] = []
    legs = route_data.get("legs", [])
    if isinstance(legs, list):
        for leg in legs:
            if not isinstance(leg, dict):
                continue
            leg_steps = leg.get("steps", [])
            if not isinstance(leg_steps, list):
                continue
            for s in leg_steps:
                if not isinstance(s, dict):
                    continue
                maneuver = s.get("maneuver") if isinstance(s.get("maneuver"), dict) else {}
                m_type = str(maneuver.get("type", "") or "")
                m_mod = maneuver.get("modifier")
                name = s.get("name")

                instr = s.get("instruction")
                if not instr:
                    if m_type == "depart":
                        instr = f"Head out on {name}" if name else "Depart walking along the path"
                    elif m_type == "arrive":
                        instr = f"Arrive at destination" + (f" on {name}" if name else "")
                    elif m_mod:
                        instr = f"Turn {m_mod}" + (f" onto {name}" if name else "")
                    elif m_type == "turn":
                        instr = f"Turn onto {name}" if name else "Turn"
                    elif name:
                        instr = f"Continue onto {name}"
                    else:
                        instr = "Continue along the walking path"

                loc = None
                m_loc = maneuver.get("location")
                if isinstance(m_loc, (list, tuple)) and len(m_loc) >= 2:
                    loc = [float(m_loc[1]), float(m_loc[0])]

                steps.append(
                    RouteStepModel(
                        instruction=str(instr),
                        distance_m=round(_safe_float(s.get("distance")), 1),
                        duration_s=round(_safe_float(s.get("duration")), 1),
                        modifier=str(m_mod) if m_mod else None,
                        name=str(name) if name else None,
                        location=loc,
                    )
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
        steps=steps,
    )


async def _fetch_osrm_walking_routes(request: RouteRequest) -> List[RouteModel]:
    """Fetch pedestrian walking paths from OSRM as an automatic high-availability fallback."""
    osrm_base = getattr(settings, "OSRM_ROUTING_URL", "https://router.project-osrm.org/route/v1/foot")
    routes: List[RouteModel] = []
    target_count = min(request.alternatives + 1, 3) if request.alternatives > 0 else 1

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Primary direct walking route
        primary_url = f"{osrm_base}/{request.source.lon},{request.source.lat};{request.destination.lon},{request.destination.lat}?overview=full&geometries=geojson&alternatives=true&steps=true"
        try:
            resp = await client.get(primary_url)
            if resp.status_code == 200:
                osrm_routes = resp.json().get("routes", [])
                for r in osrm_routes:
                    p_dist = routes[0].distance_m if routes else 0.0
                    cand = _parse_osrm_route(len(routes), r, primary_distance=p_dist)
                    if is_valid_pedestrian_route(cand, request.source, request.destination):
                        if not is_duplicate_route(cand, routes):
                            idx = len(routes)
                            cand.id = f"route_{idx}"
                            cand.is_primary = (idx == 0)
                            cand.color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
                            cand.name = (
                                "Route 1: Primary Walking Route"
                                if idx == 0
                                else f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
                            )
                            routes.append(cand)
        except Exception as exc:
            logger.warning(f"OSRM primary route query error: {exc}")

        if not routes:
            raise HTTPException(
                status_code=404,
                detail="No pedestrian route found between the specified coordinates.",
            )

        # 2. If user requested alternatives and OSRM returned fewer than requested, compute lateral detour waypoints
        if request.alternatives > 0 and len(routes) < target_count:
            primary_dist = routes[0].distance_m
            waypoints = generate_perpendicular_waypoints(
                request.source.lat,
                request.source.lon,
                request.destination.lat,
                request.destination.lon,
                factors=[0.20, -0.20, 0.35, -0.35],
            )

            for wp in waypoints:
                if len(routes) >= target_count:
                    break
                alt_url = f"{osrm_base}/{request.source.lon},{request.source.lat};{wp['lon']:.6f},{wp['lat']:.6f};{request.destination.lon},{request.destination.lat}?overview=full&geometries=geojson&steps=true"
                try:
                    alt_resp = await client.get(alt_url)
                    if alt_resp.status_code == 200:
                        alt_data = alt_resp.json().get("routes", [])
                        if alt_data:
                            cand = _parse_osrm_route(
                                len(routes),
                                alt_data[0],
                                primary_distance=primary_dist,
                            )
                            if is_valid_pedestrian_route(
                                cand,
                                request.source,
                                request.destination,
                                primary_distance_m=primary_dist,
                            ):
                                if not is_duplicate_route(cand, routes):
                                    idx = len(routes)
                                    cand.id = f"route_{idx}"
                                    cand.is_primary = False
                                    cand.color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
                                    cand.name = f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
                                    routes.append(cand)
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
    target_count = min(request.alternatives + 1, 3) if wants_alternatives else 1
    if wants_alternatives:
        # target_count specifies total number of candidate paths (primary + alternatives)
        payload["alternative_routes"] = {
            "target_count": target_count,
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
                logger.warning(
                    "Alternative routes request rejected by ORS (HTTP 400). Retrying primary route only."
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
                    raw_routes = _parse_ors_features(features)
                    for r in raw_routes:
                        if is_valid_pedestrian_route(r, request.source, request.destination):
                            if not is_duplicate_route(r, parsed_routes):
                                idx = len(parsed_routes)
                                r.id = f"route_{idx}"
                                r.is_primary = (idx == 0)
                                r.color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
                                r.name = (
                                    "Route 1: Primary Walking Route"
                                    if idx == 0
                                    else f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
                                )
                                parsed_routes.append(r)
            elif response.status_code in (401, 403):
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

            # If user requested alternatives and ORS returned fewer than target_count,
            # generate controlled waypoint-guided corridors via ORS
            if wants_alternatives and len(parsed_routes) >= 1 and len(parsed_routes) < target_count:
                primary_dist = parsed_routes[0].distance_m
                waypoints = generate_perpendicular_waypoints(
                    request.source.lat,
                    request.source.lon,
                    request.destination.lat,
                    request.destination.lon,
                    factors=[0.20, -0.20, 0.35, -0.35],
                )
                for wp in waypoints:
                    if len(parsed_routes) >= target_count:
                        break
                    wp_payload = {
                        "coordinates": [
                            [request.source.lon, request.source.lat],
                            [wp["lon"], wp["lat"]],
                            [request.destination.lon, request.destination.lat],
                        ]
                    }
                    try:
                        wp_resp = await client.post(
                            settings.ORS_API_URL,
                            json=wp_payload,
                            headers=headers,
                        )
                        if wp_resp.status_code == 200:
                            wp_features = wp_resp.json().get("features", [])
                            if wp_features:
                                cand_routes = _parse_ors_features(wp_features)
                                for cand in cand_routes:
                                    if is_valid_pedestrian_route(
                                        cand,
                                        request.source,
                                        request.destination,
                                        primary_distance_m=primary_dist,
                                    ):
                                        if not is_duplicate_route(cand, parsed_routes):
                                            idx = len(parsed_routes)
                                            cand.id = f"route_{idx}"
                                            cand.is_primary = False
                                            cand.color = ROUTE_PALETTE[idx % len(ROUTE_PALETTE)]
                                            cand.name = f"Route {idx + 1}: Alternative Route {chr(64 + idx)}"
                                            detour_km = round((cand.distance_m - primary_dist) / 1000.0, 2)
                                            cand.summary = (
                                                f"Alternative pedestrian detour (+{detour_km} km)"
                                                if detour_km > 0
                                                else "Alternative pedestrian corridor"
                                            )
                                            parsed_routes.append(cand)
                                            break
                    except Exception as wp_exc:
                        logger.debug(f"ORS waypoint alternative attempt error: {wp_exc}")

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
