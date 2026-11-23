"""Traffic Exposure & Road Proximity Service
Evaluates pedestrian exposure to vehicular traffic using defensible data sources:

1. Live Traffic Provider Investigation & Integration:
   - Evaluated Provider: TomTom Traffic Flow API (or compatible real-time traffic provider).
   - Metrics: Real-time speed, free-flow speed, and delay percentage (currentSpeed / freeFlowSpeed).
   - Authentication: Requires TOMTOM_TRAFFIC_API_KEY in backend/.env.
   - Rate Limits: 5 QPS, 2,500 daily requests on free evaluation tier.
   - Licensing & Usage: Non-commercial evaluation permitted; allows displaying traffic flow along pedestrian corridors.
   - Pedestrian Significance: Walking adjacent to heavily congested motorways/arterials exposes pedestrians to
     peak exhaust emissions (NO2, PM2.5) and traffic noise.

2. Defensible Static Infrastructure Proxy (Default / Fallback Mode):
   - Used when reliable live traffic data is unconfigured or unavailable.
   - Evaluates proximity to OpenStreetMap major vehicular infrastructure (motorway, trunk, primary, secondary).
   - NEVER claims or labels road classification as live traffic volume or actual transient congestion.
   - Strictly separates live traffic metrics from static proxy metrics in the data model.
   - Documents units, timestamps, coverage, source, and limitations explicitly.
"""
import asyncio
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.schemas.environment import (
    LiveTrafficMetrics,
    StaticRoadProxyMetrics,
    TrafficExposureData,
)
from app.schemas.routes import RouteModel
from app.services.greenery_service import compute_corridor_bbox, haversine_distance_m

logger = logging.getLogger(__name__)

# In-memory cache for major road queries: bbox_key -> (timestamp, elements)
_road_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
# In-memory cache for TomTom point queries: normalized "lat,lon" -> (timestamp, Optional[Dict[str, float]])
_tomtom_traffic_cache: Dict[str, Tuple[float, Optional[Dict[str, float]]]] = {}
_traffic_lock = asyncio.Lock()
_last_traffic_request_time = 0.0


def build_overpass_major_roads_query(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> str:
    """Overpass QL query to fetch only major motorized vehicular roadways in bbox."""
    bbox_str = f"{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f}"
    return f"""
    [out:json][timeout:{int(settings.OVERPASS_TIMEOUT_SECONDS)}][maxsize:2097152];
    (
      way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link)$"]({bbox_str});
    );
    out body center qt;
    """


async def fetch_overpass_major_roads(
    bbox: Tuple[float, float, float, float]
) -> Optional[List[Dict[str, Any]]]:
    """Fetch mapped major roads within corridor bbox from OpenStreetMap via Overpass API."""
    global _last_traffic_request_time
    min_lat, min_lon, max_lat, max_lon = bbox

    # Safety check on bbox size
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon
    if lat_span > 0.08 or lon_span > 0.08:
        return None

    cache_key = f"roads_{min_lat:.3f}_{min_lon:.3f}_{max_lat:.3f}_{max_lon:.3f}"
    now = time.time()
    if cache_key in _road_cache:
        cached_time, cached_elements = _road_cache[cache_key]
        if now - cached_time < settings.OVERPASS_CACHE_TTL_SECONDS:
            return cached_elements

    query = build_overpass_major_roads_query(min_lat, min_lon, max_lat, max_lon)
    headers = {
        "User-Agent": settings.NOMINATIM_USER_AGENT,
        "Accept": "application/json",
    }

    async with _traffic_lock:
        elapsed = time.time() - _last_traffic_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)

        try:
            async with httpx.AsyncClient(timeout=settings.OVERPASS_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    settings.OVERPASS_API_URL,
                    data={"data": query},
                    headers=headers,
                )
            _last_traffic_request_time = time.time()

            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                _road_cache[cache_key] = (now, elements)
                return elements
            else:
                logger.warning(f"Overpass road query returned status {response.status_code}")
                return None
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(f"Failed to query Overpass for road infrastructure: {exc}")
            _last_traffic_request_time = time.time()
            return None


def extract_representative_traffic_points(
    coordinates: List[List[float]], max_points: int = 2
) -> List[Tuple[float, float]]:
    """Extract 1 to 2 representative coordinates from an individual route geometry.
    - Routes with few waypoints (< 4) use the midpoint.
    - Longer routes use spaced points (e.g. 1/3 and 2/3).
    - If spaced points are closer than 100m, single midpoint is preferred to avoid redundant API calls.
    """
    if not coordinates:
        return []
    n = len(coordinates)
    if n < 4 or max_points <= 1:
        pt = coordinates[n // 2]
        return [(float(pt[0]), float(pt[1]))]

    p1 = coordinates[n // 3]
    p2 = coordinates[(2 * n) // 3]
    lat1, lon1 = float(p1[0]), float(p1[1])
    lat2, lon2 = float(p2[0]), float(p2[1])

    # If the two points are too close (< 100m apart), sample only the midpoint
    if haversine_distance_m(lat1, lon1, lat2, lon2) < 100.0:
        mid = coordinates[n // 2]
        return [(float(mid[0]), float(mid[1]))]

    return [(lat1, lon1), (lat2, lon2)]


async def query_tomtom_traffic_point(
    lat: float, lon: float, client: Optional[httpx.AsyncClient] = None
) -> Optional[Dict[str, float]]:
    """Query TomTom Traffic Flow for a single coordinate point with caching."""
    key = settings.TOMTOM_TRAFFIC_API_KEY.strip() if settings.TOMTOM_TRAFFIC_API_KEY else ""
    if not key or key == "your_tomtom_api_key_here":
        return None

    cache_key = f"{round(lat, 4):.4f},{round(lon, 4):.4f}"
    now = time.time()
    if cache_key in _tomtom_traffic_cache:
        cached_time, cached_val = _tomtom_traffic_cache[cache_key]
        if now - cached_time < settings.TRAFFIC_CACHE_TTL_SECONDS:
            return cached_val

    url = f"{settings.TOMTOM_TRAFFIC_API_URL}?point={lat},{lon}&unit=KMPH&key={key}"

    async def _request(c: httpx.AsyncClient) -> Optional[Dict[str, float]]:
        resp = await c.get(url)
        if resp.status_code == 200:
            data = resp.json()
            flow = data.get("flowSegmentData", {})
            current_speed = flow.get("currentSpeed")
            free_flow = flow.get("freeFlowSpeed")

            if current_speed is not None and free_flow is not None and free_flow > 0:
                ratio = float(current_speed) / float(free_flow)
                congestion_pct = round(max(0.0, min(100.0, (1.0 - ratio) * 100.0)), 1)
                parsed = {
                    "current_speed": float(current_speed),
                    "free_flow": float(free_flow),
                    "congestion_pct": congestion_pct,
                }
                _tomtom_traffic_cache[cache_key] = (now, parsed)
                return parsed
            else:
                _tomtom_traffic_cache[cache_key] = (now, None)
                return None
        elif resp.status_code in (401, 403):
            logger.warning("TomTom Traffic authorization failed.")
            return None
        elif resp.status_code == 429:
            logger.warning("TomTom Traffic rate limit reached.")
            return None
        else:
            logger.warning(f"TomTom Traffic returned status {resp.status_code}")
            return None

    try:
        if client is not None:
            return await _request(client)
        else:
            async with httpx.AsyncClient(timeout=settings.TRAFFIC_TIMEOUT_SECONDS) as c:
                return await _request(c)
    except Exception as exc:
        logger.warning(f"Live traffic query error for point ({lat}, {lon}) (non-fatal): {exc}")
        return None


async def fetch_live_traffic_flow(
    sampled_coords: List[List[float]],
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[LiveTrafficMetrics]:
    """Query live traffic speed and congestion from TomTom Traffic Flow API for an individual candidate route.
    Returns None if no API key is provided, service is unreachable, or no usable flow data returned.
    """
    key = settings.TOMTOM_TRAFFIC_API_KEY.strip() if settings.TOMTOM_TRAFFIC_API_KEY else ""
    if not key or key == "your_tomtom_api_key_here":
        # Live traffic API not configured; fallback to static proxy
        return None

    if not sampled_coords:
        return None

    points = extract_representative_traffic_points(sampled_coords, max_points=2)
    if not points:
        return None

    tasks = [query_tomtom_traffic_point(lat, lon, client=client) for lat, lon in points]
    point_results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = [
        r for r in point_results
        if isinstance(r, dict) and r.get("current_speed") is not None
    ]

    if not valid_results:
        return None

    avg_congestion = round(sum(r["congestion_pct"] for r in valid_results) / len(valid_results), 1)
    avg_current_speed = round(sum(r["current_speed"] for r in valid_results) / len(valid_results), 1)
    avg_free_flow = round(sum(r["free_flow"] for r in valid_results) / len(valid_results), 1)
    now_iso = datetime.now(timezone.utc).isoformat()

    return LiveTrafficMetrics(
        congestion_pct=avg_congestion,
        current_speed_kmh=avg_current_speed,
        free_flow_speed_kmh=avg_free_flow,
        provider="TomTom Traffic Flow API",
        timestamp=now_iso,
        status="available",
    )


def is_time_non_current(departure_time: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Determine if a requested departure time differs significantly (>30 mins) from current time."""
    if not departure_time:
        return False, None
    try:
        dt = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff_mins = (dt - now).total_seconds() / 60.0
        if abs(diff_mins) > 30.0:
            direction = "future" if diff_mins > 0 else "historical"
            return True, f"Live vehicular traffic is unavailable for {direction} departure time ({departure_time})."
    except Exception:
        pass
    return False, None


def compute_route_traffic_profile(
    route_coordinates: List[List[float]],
    osm_road_elements: Optional[List[Dict[str, Any]]],
    live_traffic: Optional[LiveTrafficMetrics] = None,
    buffer_distance_m: float = 50.0,
    departure_time: Optional[str] = None,
) -> TrafficExposureData:
    """Compute traffic exposure profile for a single walking route:
    - If live traffic data exists and departure time is current: assigns live congestion metrics.
    - If departure time is in the future: live traffic is marked unavailable.
    - Else: computes static major road proximity proxy from OSM.
    - Strictly keeps live traffic metrics and static proxy metrics separate in data model.
    - Never labels static road classification as live traffic volume.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    is_non_current, time_msg = is_time_non_current(departure_time)

    # 1. If departure time is future/historical, live traffic cannot be applied
    if is_non_current and live_traffic and live_traffic.congestion_pct is not None:
        return TrafficExposureData(
            score=None,
            unit="index (0-100)",
            status="unavailable",
            metric_type="live_traffic_congestion",
            is_live_measurement=True,
            road_class=None,
            source="TomTom Real-Time Traffic Flow API",
            timestamp=now_iso,
            time_applicability_note=time_msg,
            limitation_note="Live traffic measurements are valid only for immediate departures. Future traffic flow is unavailable.",
            live_traffic=None,
            static_proxy=None,
        )

    # 2. Check if verified live traffic data is available for immediate departure
    if live_traffic and live_traffic.congestion_pct is not None:
        return TrafficExposureData(
            score=live_traffic.congestion_pct,
            unit="index (0-100)",
            status="live_measured",
            metric_type="live_traffic_congestion",
            is_live_measurement=True,
            road_class=None,
            source="TomTom Real-Time Traffic Flow API",
            timestamp=live_traffic.timestamp or now_iso,
            time_applicability_note="Valid for current immediate departure.",
            limitation_note="Real-time vehicular speed and congestion index on adjacent roadways.",
            live_traffic=live_traffic,
            static_proxy=None,
        )

    # 2. Compute Static Road Hierarchy Infrastructure Proxy
    if osm_road_elements is None:
        # Provider unavailable / timeout
        return TrafficExposureData(
            score=None,
            unit="index (0-100)",
            status="unavailable",
            metric_type="static_road_hierarchy_proxy",
            is_live_measurement=False,
            road_class=None,
            source="OpenStreetMap Highway Infrastructure Hierarchy",
            timestamp=now_iso,
            limitation_note="Traffic exposure data currently unavailable from external providers.",
            live_traffic=None,
            static_proxy=None,
        )

    if not osm_road_elements or not route_coordinates:
        # Bounded area contains no major arterial roadways -> quiet pedestrian corridor
        static_proxy = StaticRoadProxyMetrics(
            major_road_nearby_pct=0.0,
            dominant_road_class="pedestrian_or_minor",
            major_roads_count=0,
            source="OpenStreetMap Highway Tags",
            status="available",
        )
        return TrafficExposureData(
            score=15.0,  # Baseline low exposure for quiet pathways
            unit="index (0-100)",
            status="static_proxy_estimated",
            metric_type="static_road_hierarchy_proxy",
            is_live_measurement=False,
            road_class="pedestrian_or_minor",
            source="OpenStreetMap Highway Infrastructure Hierarchy (Major Road Proximity Proxy)",
            timestamp=now_iso,
            limitation_note=(
                "Static infrastructure proxy based on absence of mapped major arterials in corridor. "
                "Does NOT represent live vehicular traffic volume or transient congestion."
            ),
            live_traffic=None,
            static_proxy=static_proxy,
        )

    # Extract coordinates of major road elements
    road_points: List[Tuple[float, float, str]] = []
    road_class_counts: Dict[str, int] = {}

    for el in osm_road_elements:
        hw_type = el.get("tags", {}).get("highway", "major_road")
        road_class_counts[hw_type] = road_class_counts.get(hw_type, 0) + 1

        if "center" in el and "lat" in el["center"]:
            road_points.append((float(el["center"]["lat"]), float(el["center"]["lon"]), hw_type))
        elif "lat" in el and "lon" in el:
            road_points.append((float(el["lat"]), float(el["lon"]), hw_type))

    dominant_class = (
        max(road_class_counts, key=road_class_counts.get)
        if road_class_counts
        else "secondary"
    )

    # Sub-sample route coordinates to test proximity
    n_pts = len(route_coordinates)
    sample_step = max(1, n_pts // 25)
    sample_coords = [route_coordinates[i] for i in range(0, n_pts, sample_step)]
    if route_coordinates[-1] not in sample_coords:
        sample_coords.append(route_coordinates[-1])

    # Count how many route sample points are within buffer_distance_m of a major road
    points_near_major_road = 0
    for lat, lon in sample_coords:
        for r_lat, r_lon, _ in road_points:
            dist = haversine_distance_m(lat, lon, r_lat, r_lon)
            if dist <= buffer_distance_m:
                points_near_major_road += 1
                break

    total_samples = max(1, len(sample_coords))
    major_road_nearby_pct = round((points_near_major_road / total_samples) * 100.0, 1)

    # Exposure score: Baseline 20.0 (minor roads), scaled up by major road proximity
    # Max 90.0 for routes running alongside major motorways/arterials
    exposure_score = round(min(90.0, 20.0 + (major_road_nearby_pct * 0.70)), 1)

    static_proxy = StaticRoadProxyMetrics(
        major_road_nearby_pct=major_road_nearby_pct,
        dominant_road_class=dominant_class,
        major_roads_count=len(osm_road_elements),
        source="OpenStreetMap Highway Tags",
        status="available",
    )

    return TrafficExposureData(
        score=exposure_score,
        unit="index (0-100)",
        status="static_proxy_estimated",
        metric_type="static_road_hierarchy_proxy",
        is_live_measurement=False,
        road_class=dominant_class,
        source="OpenStreetMap Highway Infrastructure Hierarchy (Major Road Proximity Proxy)",
        timestamp=now_iso,
        limitation_note=(
            "Static infrastructure proxy based on proximity to mapped major roadways. "
            "Does NOT represent live vehicular traffic volume, real-time speed, or transient congestion."
        ),
        live_traffic=None,
        static_proxy=static_proxy,
    )


async def enrich_routes_with_traffic_data(
    routes: List[RouteModel], departure_time: Optional[str] = None
) -> None:
    """Enrich candidate walking routes with traffic exposure indicators:
    - Queries TomTom live traffic independently for each candidate route if key configured and departure is near-current.
    - Falls back to route-specific static road hierarchy proxy from OSM if live traffic is unavailable or unconfigured.
    - Ensures candidate routes never inherit Route 0's traffic metrics.
    """
    if not routes:
        return

    # 1. Query major roads in route corridor bounding box once for all routes (static fallback)
    bbox = compute_corridor_bbox(routes)
    osm_roads = await fetch_overpass_major_roads(bbox)

    # 2. Check if live traffic API is configured
    key = settings.TOMTOM_TRAFFIC_API_KEY.strip() if settings.TOMTOM_TRAFFIC_API_KEY else ""
    is_live_enabled = bool(key and key != "your_tomtom_api_key_here")

    live_metrics_by_route: List[Optional[LiveTrafficMetrics]] = [None] * len(routes)

    if is_live_enabled:
        # Query TomTom live traffic independently for each candidate route concurrently
        try:
            async with httpx.AsyncClient(timeout=settings.TRAFFIC_TIMEOUT_SECONDS) as client:
                tasks = [
                    fetch_live_traffic_flow(route.coordinates, client=client)
                    for route in routes
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, res in enumerate(results):
                    if isinstance(res, LiveTrafficMetrics):
                        live_metrics_by_route[i] = res
                    elif isinstance(res, Exception):
                        logger.warning(f"Live traffic query failed for route {routes[i].id}: {res}")
                        live_metrics_by_route[i] = None
                    else:
                        live_metrics_by_route[i] = None
        except Exception as exc:
            logger.warning(f"Failed to query live traffic for routes: {exc}")
            live_metrics_by_route = [None] * len(routes)

    # 3. Compute route-specific traffic profile independently for each route
    for i, route in enumerate(routes):
        route_live_traffic = live_metrics_by_route[i]
        traffic_profile = compute_route_traffic_profile(
            route.coordinates,
            osm_roads,
            live_traffic=route_live_traffic,
            departure_time=departure_time,
        )
        if route.environment:
            route.environment.traffic_exposure = traffic_profile
            route.environment.has_traffic = (traffic_profile.score is not None)
            if traffic_profile.status == "unavailable":
                route.environment.notes.append("Traffic exposure data unavailable from providers.")
            elif traffic_profile.metric_type == "static_road_hierarchy_proxy":
                route.environment.notes.append(
                    "Traffic indicator based on static road hierarchy proxy (not live volume)."
                )
