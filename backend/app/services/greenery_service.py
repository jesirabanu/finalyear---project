"""OpenStreetMap Overpass Greenery Service
Computes pedestrian route corridor greenery presence and park proximity metrics:
- Queries OSM features (parks, gardens, nature reserves, woods, tree rows, grass) via Overpass API.
- Bounded to the route corridor and reasonable buffer (~150m) to avoid full-city queries.
- Adheres to Overpass server policies: 1 req/sec rate limit, custom User-Agent, 10s timeout, response size limits.
- Caches responses in-memory with TTL to eliminate redundant queries.
- Computes fraction of route within 50m of mapped green areas and distinct adjacent parks.
- Documents that proximity to mapped greenery is NOT equivalent to Green View Index (GVI),
  actual canopy density, shade, or air-pollution absorption.
"""
import asyncio
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.schemas.environment import GreeneryData
from app.schemas.routes import RouteModel

logger = logging.getLogger(__name__)

# Overpass server policy: rate limiting and in-memory cache
_overpass_lock = asyncio.Lock()
_last_overpass_request_time = 0.0
_greenery_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two coordinates in metres."""
    r = 6371000.0  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def compute_corridor_bbox(
    routes: List[RouteModel],
    buffer_deg: float = 0.002,  # ~150-200 metres buffer
) -> Tuple[float, float, float, float]:
    """Compute min/max latitude and longitude bounding box for all routes with buffer.
    Returns: (min_lat, min_lon, max_lat, max_lon)
    """
    all_lats: List[float] = []
    all_lons: List[float] = []

    for r in routes:
        for pt in r.coordinates:
            all_lats.append(pt[0])
            all_lons.append(pt[1])

    if not all_lats or not all_lons:
        return 51.5, -0.1, 51.52, -0.08

    min_lat = max(-90.0, min(all_lats) - buffer_deg)
    max_lat = min(90.0, max(all_lats) + buffer_deg)
    min_lon = max(-180.0, min(all_lons) - buffer_deg)
    max_lon = min(180.0, max(all_lons) + buffer_deg)

    return min_lat, min_lon, max_lat, max_lon


def build_overpass_greenery_query(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> str:
    """Construct an optimized Overpass QL query querying only green features in bbox.
    Uses 'out body center qt' for high performance and low server memory.
    """
    # Overpass bounding box format: (south, west, north, east) -> (min_lat, min_lon, max_lat, max_lon)
    bbox_str = f"{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f}"

    return f"""
    [out:json][timeout:{int(settings.OVERPASS_TIMEOUT_SECONDS)}][maxsize:2097152];
    (
      way["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({bbox_str});
      way["landuse"~"^(grass|forest|meadow|village_green|orchard|cemetery)$"]({bbox_str});
      way["natural"~"^(wood|tree_row|scrub|grassland)$"]({bbox_str});
      node["natural"="tree"]({bbox_str});
      relation["leisure"~"^(park|garden|nature_reserve)$"]({bbox_str});
    );
    out body center qt;
    """


async def fetch_overpass_greenery_features(
    bbox: Tuple[float, float, float, float]
) -> Optional[List[Dict[str, Any]]]:
    """Fetch mapped green features within bounding box via Overpass API with rate limiting and caching.
    Returns None if request failed/timed out, or empty list if no green features found in OSM.
    """
    global _last_overpass_request_time
    min_lat, min_lon, max_lat, max_lon = bbox

    # Check bbox size safety cap to avoid requesting entire regions
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon
    if lat_span > 0.08 or lon_span > 0.08:
        logger.warning(f"Corridor bbox too large ({lat_span:.3f}x{lon_span:.3f}); skipping Overpass.")
        return None

    cache_key = f"{min_lat:.3f}_{min_lon:.3f}_{max_lat:.3f}_{max_lon:.3f}"
    now = time.time()
    if cache_key in _greenery_cache:
        cached_time, cached_data = _greenery_cache[cache_key]
        if now - cached_time < settings.OVERPASS_CACHE_TTL_SECONDS:
            return cached_data

    query = build_overpass_greenery_query(min_lat, min_lon, max_lat, max_lon)
    headers = {
        "User-Agent": settings.NOMINATIM_USER_AGENT,
        "Accept": "application/json",
    }

    async with _overpass_lock:
        # Enforce minimum 1.0 second between consecutive Overpass outbound calls
        elapsed = time.time() - _last_overpass_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)

        try:
            async with httpx.AsyncClient(timeout=settings.OVERPASS_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    settings.OVERPASS_API_URL,
                    data={"data": query},
                    headers=headers,
                )
            _last_overpass_request_time = time.time()

            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                _greenery_cache[cache_key] = (now, elements)
                return elements
            elif response.status_code == 429:
                logger.warning("Overpass API rate limit reached (HTTP 429).")
                return None
            elif response.status_code == 504:
                logger.warning("Overpass API gateway timeout (HTTP 504).")
                return None
            else:
                logger.warning(f"Overpass API returned status {response.status_code}: {response.text[:200]}")
                return None

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(f"Failed to communicate with Overpass API: {exc}")
            _last_overpass_request_time = time.time()
            return None


def extract_feature_coordinates(element: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Extract representative (lat, lon) from Overpass element."""
    if "center" in element and "lat" in element["center"] and "lon" in element["center"]:
        return float(element["center"]["lat"]), float(element["center"]["lon"])
    elif "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    return None


def compute_route_greenery_profile(
    route_coordinates: List[List[float]],
    osm_elements: Optional[List[Dict[str, Any]]],
    buffer_distance_m: float = 50.0,
) -> GreeneryData:
    """Compute documented greenery proximity indicator for a single walking route:
    - Calculates the fraction of route waypoints within defined buffer distance of green features.
    - Counts distinct adjacent parks or green spaces.
    - Accurately reports missing or incomplete data without fabricating values.
    """
    if osm_elements is None:
        # Provider request failed or timed out
        return GreeneryData(
            score=None,
            unit="%",
            status="missing_from_provider",
            greenery_fraction=None,
            buffer_distance_m=buffer_distance_m,
            parks_count=None,
            mapped_features_count=None,
        )

    if not osm_elements or not route_coordinates:
        # Successfully queried OSM, but no green features exist in this corridor
        return GreeneryData(
            score=0.0,
            unit="%",
            status="empty_osm_coverage",
            greenery_fraction=0.0,
            buffer_distance_m=buffer_distance_m,
            parks_count=0,
            mapped_features_count=0,
        )

    # Extract all valid coordinates of returned green features
    green_points: List[Tuple[float, float, str]] = []
    for el in osm_elements:
        coords = extract_feature_coordinates(el)
        if coords:
            tags = el.get("tags", {})
            name = tags.get("name", tags.get("leisure", tags.get("landuse", "greenery")))
            green_points.append((coords[0], coords[1], name))

    if not green_points:
        return GreeneryData(
            score=0.0,
            unit="%",
            status="empty_osm_coverage",
            greenery_fraction=0.0,
            buffer_distance_m=buffer_distance_m,
            parks_count=0,
            mapped_features_count=0,
        )

    # Sub-sample route coordinates to test proximity evenly (up to 25 sample points)
    n_pts = len(route_coordinates)
    sample_step = max(1, n_pts // 25)
    sample_coords = [route_coordinates[i] for i in range(0, n_pts, sample_step)]
    if route_coordinates[-1] not in sample_coords:
        sample_coords.append(route_coordinates[-1])

    # For each route sample point, determine distance to nearest green feature
    points_near_green = 0
    distinct_nearby_parks: set = set()

    for lat, lon in sample_coords:
        min_dist = float("inf")
        closest_park_name = None

        for g_lat, g_lon, g_name in green_points:
            dist = haversine_distance_m(lat, lon, g_lat, g_lon)
            if dist < min_dist:
                min_dist = dist
                closest_park_name = g_name

        if min_dist <= buffer_distance_m:
            points_near_green += 1
            if closest_park_name:
                distinct_nearby_parks.add(closest_park_name)
        elif min_dist <= buffer_distance_m * 2.0 and closest_park_name:
            distinct_nearby_parks.add(closest_park_name)

    total_samples = max(1, len(sample_coords))
    green_fraction = round(points_near_green / total_samples, 3)
    coverage_pct = round(green_fraction * 100.0, 1)
    parks_count = len(distinct_nearby_parks)

    # Score calculation: 85% coverage fraction + up to 15% park presence bonus
    computed_score = round(min(100.0, coverage_pct * 0.85 + min(parks_count, 3) * 5.0), 1)

    return GreeneryData(
        score=computed_score,
        unit="%",
        status="available",
        greenery_fraction=green_fraction,
        buffer_distance_m=buffer_distance_m,
        parks_count=parks_count,
        mapped_features_count=len(osm_elements),
    )


async def enrich_routes_with_greenery_data(routes: List[RouteModel]) -> None:
    """Enrich candidate walking routes with Overpass greenery indicators.
    Executes a single bounded Overpass query for the collective route corridor.
    """
    if not routes:
        return

    bbox = compute_corridor_bbox(routes)
    osm_elements = await fetch_overpass_greenery_features(bbox)

    for route in routes:
        greenery_profile = compute_route_greenery_profile(route.coordinates, osm_elements)
        if route.environment:
            route.environment.greenery = greenery_profile
            route.environment.has_greenery = (greenery_profile.score is not None)
            if greenery_profile.status == "missing_from_provider":
                route.environment.notes.append("Greenery data unavailable from Overpass API.")
            elif greenery_profile.status == "empty_osm_coverage":
                route.environment.notes.append("No mapped OSM parks or green features detected along this corridor.")
