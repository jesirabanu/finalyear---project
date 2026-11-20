"""Environmental Data Service
Interacts with Open-Meteo Air Quality and Forecast APIs:
- Global gridded coverage (~11 km atmospheric model; ~2-11 km weather model)
- Multi-location batch queries via comma-separated coordinates
- Strict handling of missing fields (no silent zero substitution)
- In-memory caching with configurable TTL
- Route geometry sampling and documented aggregation
- Explicit metadata documenting modeled nature, spatial resolution limits, and timestamps
"""
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.schemas.environment import (
    AirQualityData,
    EnvironmentalMetadata,
    PollutantReading,
    RouteEnvironmentalPoint,
    RouteEnvironmentalSummary,
    SinglePointEnvironmentResponse,
    WeatherData,
)

logger = logging.getLogger(__name__)

# In-memory TTL Cache: cache_key -> (timestamp, data_dict)
_env_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

# WMO Weather interpretation codes
WMO_WEATHER_CODES: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _get_wmo_description(code: Optional[int]) -> Optional[str]:
    """Map numeric WMO code to human-readable weather description."""
    if code is None:
        return None
    return WMO_WEATHER_CODES.get(code, f"Weather Code {code}")


def _evaluate_european_aqi(aqi: Optional[float]) -> Tuple[Optional[str], Optional[str]]:
    """Determine European Air Quality Index category and hex color indicator.

    EAQI Thresholds:
    0-20: Good (#10b981)
    20-40: Fair (#3b82f6)
    40-60: Moderate (#f59e0b)
    60-80: Poor (#ef4444)
    80-100: Very Poor (#9333ea)
    >100: Extremely Poor (#7e22ce)
    """
    if aqi is None:
        return None, None
    if aqi <= 20:
        return "Good", "#10b981"
    elif aqi <= 40:
        return "Fair", "#3b82f6"
    elif aqi <= 60:
        return "Moderate", "#f59e0b"
    elif aqi <= 80:
        return "Poor", "#ef4444"
    elif aqi <= 100:
        return "Very Poor", "#9333ea"
    else:
        return "Extremely Poor", "#7e22ce"


def sample_route_geometry(
    coordinates: List[List[float]], max_samples: int = 4
) -> List[Tuple[int, float, float]]:
    """Sample a manageable number of representative points along route geometry.

    Selects start (0%), intermediate waypoints, and destination (100%) to capture
    spatial variations without triggering excessive requests.

    Args:
        coordinates: List of [lat, lon] pairs from route geometry.
        max_samples: Target number of sampled points (typically 3 to 5).

    Returns:
        List of (point_index, lat, lon) tuples.
    """
    if not coordinates:
        return []

    n = len(coordinates)
    if n <= max_samples:
        return [(i, coordinates[i][0], coordinates[i][1]) for i in range(n)]

    # Evenly space sample indices along the coordinate array
    step = (n - 1) / float(max_samples - 1)
    sample_indices = sorted(list({int(round(i * step)) for i in range(max_samples)}))

    # Ensure last index is included
    if sample_indices[-1] != n - 1:
        sample_indices[-1] = n - 1

    return [(idx, coordinates[idx][0], coordinates[idx][1]) for idx in sample_indices]


def _build_cache_key(prefix: str, lat: float, lon: float, time_str: Optional[str]) -> str:
    """Create rounded coordinate cache key (~100m grid resolution matching model updates)."""
    rounded_lat = round(lat, 3)
    rounded_lon = round(lon, 3)
    t_key = time_str or "current"
    return f"{prefix}:{rounded_lat}:{rounded_lon}:{t_key}"


async def fetch_air_quality_batch(
    coords: List[Tuple[float, float]],
    time_str: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch air quality readings for multiple locations in a single batch query.

    Args:
        coords: List of (lat, lon) tuples.
        time_str: Optional ISO 8601 timestamp for historic/forecast evaluation.
        force_refresh: If True, bypasses cache and forces upstream API call.
                       Retains previous cache as stale fallback if API call fails.

    Returns:
        List of parsed JSON response objects corresponding to input coordinates.
    """
    if not coords:
        return []

    now = time.time()
    results: List[Optional[Dict[str, Any]]] = [None] * len(coords)
    missing_indices: List[int] = []

    # 1. Check cache for each coordinate if not forcing refresh
    for idx, (lat, lon) in enumerate(coords):
        ck = _build_cache_key("aq", lat, lon, time_str)
        if not force_refresh and ck in _env_cache:
            cache_time, cached_data = _env_cache[ck]
            age = now - cache_time
            if age < settings.ENVIRONMENT_CACHE_TTL_SECONDS:
                results[idx] = {**cached_data, "_cache_age": age}
                continue
        missing_indices.append(idx)

    # All returned from fresh cache
    if not missing_indices:
        return [r for r in results if r is not None]

    # 2. Query uncached/refreshed coordinates in a single multi-location request
    uncached_coords = [coords[i] for i in missing_indices]
    lat_str = ",".join(str(round(c[0], 5)) for c in uncached_coords)
    lon_str = ",".join(str(round(c[1], 5)) for c in uncached_coords)

    params: Dict[str, Any] = {
        "latitude": lat_str,
        "longitude": lon_str,
    }

    if time_str:
        params["hourly"] = "pm10,pm2_5,nitrogen_dioxide,european_aqi,us_aqi"
    else:
        params["current"] = "pm10,pm2_5,nitrogen_dioxide,european_aqi,us_aqi"

    fetch_success = False

    async with httpx.AsyncClient(timeout=settings.ENVIRONMENT_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.get(
                settings.OPEN_METEO_AIR_QUALITY_URL,
                params=params,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                raw_data = resp.json()
                items = raw_data if isinstance(raw_data, list) else [raw_data]
                for pos, item in enumerate(items):
                    orig_idx = missing_indices[pos]
                    results[orig_idx] = item
                    ck = _build_cache_key("aq", coords[orig_idx][0], coords[orig_idx][1], time_str)
                    _env_cache[ck] = (now, item)
                fetch_success = True
            else:
                logger.warning(f"Open-Meteo AQI API responded with status {resp.status_code}")
        except Exception as exc:
            logger.warning(f"Failed to fetch air quality from Open-Meteo: {exc}")

    # 3. If upstream fetch failed, fall back to retained cache with explicit stale warning
    if not fetch_success:
        for pos_idx in missing_indices:
            ck = _build_cache_key("aq", coords[pos_idx][0], coords[pos_idx][1], time_str)
            if ck in _env_cache:
                cache_time, cached_data = _env_cache[ck]
                age = now - cache_time
                if age <= settings.STALE_DATA_MAX_AGE_SECONDS:
                    results[pos_idx] = {
                        **cached_data,
                        "_is_stale": True,
                        "_stale_warning": f"Air quality API unreachable; displaying retained cached readings ({int(age // 60)}m old).",
                        "_cache_age": age,
                    }

    return [r if r is not None else {} for r in results]


async def fetch_weather_batch(
    coords: List[Tuple[float, float]],
    time_str: Optional[str] = None,
    force_refresh: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch weather data for multiple locations in a single batch query.

    Args:
        coords: List of (lat, lon) tuples.
        time_str: Optional ISO 8601 timestamp for forecast step matching.
        force_refresh: If True, bypasses cache and forces upstream API call.

    Returns:
        List of parsed JSON response objects corresponding to input coordinates.
    """
    if not coords:
        return []

    now = time.time()
    results: List[Optional[Dict[str, Any]]] = [None] * len(coords)
    missing_indices: List[int] = []

    # 1. Check cache for each coordinate
    for idx, (lat, lon) in enumerate(coords):
        ck = _build_cache_key("weather", lat, lon, time_str)
        if not force_refresh and ck in _env_cache:
            cache_time, cached_data = _env_cache[ck]
            age = now - cache_time
            if age < settings.ENVIRONMENT_CACHE_TTL_SECONDS:
                results[idx] = {**cached_data, "_cache_age": age}
                continue
        missing_indices.append(idx)

    if not missing_indices:
        return [r for r in results if r is not None]

    uncached_coords = [coords[i] for i in missing_indices]
    lat_str = ",".join(str(round(c[0], 5)) for c in uncached_coords)
    lon_str = ",".join(str(round(c[1], 5)) for c in uncached_coords)

    params: Dict[str, Any] = {
        "latitude": lat_str,
        "longitude": lon_str,
    }

    if time_str:
        params["hourly"] = (
            "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
        )
    else:
        params["current"] = (
            "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
        )

    fetch_success = False

    async with httpx.AsyncClient(timeout=settings.ENVIRONMENT_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.get(
                settings.OPEN_METEO_WEATHER_URL,
                params=params,
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                raw_data = resp.json()
                items = raw_data if isinstance(raw_data, list) else [raw_data]
                for pos, item in enumerate(items):
                    orig_idx = missing_indices[pos]
                    results[orig_idx] = item
                    ck = _build_cache_key("weather", coords[orig_idx][0], coords[orig_idx][1], time_str)
                    _env_cache[ck] = (now, item)
                fetch_success = True
            else:
                logger.warning(f"Open-Meteo Weather API responded with status {resp.status_code}")
        except Exception as exc:
            logger.warning(f"Failed to fetch weather from Open-Meteo: {exc}")

    # Fallback to retained cache on failure
    if not fetch_success:
        for pos_idx in missing_indices:
            ck = _build_cache_key("weather", coords[pos_idx][0], coords[pos_idx][1], time_str)
            if ck in _env_cache:
                cache_time, cached_data = _env_cache[ck]
                age = now - cache_time
                if age <= settings.STALE_DATA_MAX_AGE_SECONDS:
                    results[pos_idx] = {
                        **cached_data,
                        "_is_stale": True,
                        "_stale_warning": f"Weather forecast unreachable; displaying retained cached readings ({int(age // 60)}m old).",
                        "_cache_age": age,
                    }

    return [r if r is not None else {} for r in results]


def parse_air_quality_item(
    item: Dict[str, Any], time_str: Optional[str] = None
) -> Tuple[AirQualityData, Optional[str]]:
    """Parse a single raw Open-Meteo air quality response object.

    Strictly preserves None for missing variables without substituting zeros.
    """
    if not item:
        return (
            AirQualityData(
                pm2_5=PollutantReading(value=None, unit="μg/m³", status="missing_from_provider"),
                pm10=PollutantReading(value=None, unit="μg/m³", status="missing_from_provider"),
                nitrogen_dioxide=PollutantReading(value=None, unit="μg/m³", status="missing_from_provider"),
                european_aqi=PollutantReading(value=None, unit="EAQI", status="missing_from_provider"),
                us_aqi=PollutantReading(value=None, unit="USAQI", status="missing_from_provider"),
                aqi_category=None,
                aqi_color=None,
            ),
            None,
        )

    units = item.get("current_units") or item.get("hourly_units") or {}
    forecast_ts: Optional[str] = None

    if "current" in item and item["current"]:
        data_block = item["current"]
        forecast_ts = data_block.get("time")

        def _get_val(k: str) -> Optional[float]:
            v = data_block.get(k)
            return float(v) if v is not None else None

        pm25_val = _get_val("pm2_5")
        pm10_val = _get_val("pm10")
        no2_val = _get_val("nitrogen_dioxide")
        eaqi_val = _get_val("european_aqi")
        usaqi_val = _get_val("us_aqi")

    elif "hourly" in item and item["hourly"]:
        hourly = item["hourly"]
        times = hourly.get("time", [])
        chosen_idx = 0
        if time_str and times:
            # Find closest hourly timestamp
            try:
                target_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                min_diff = float("inf")
                for i, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                    diff = abs((dt - target_dt).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        chosen_idx = i
            except Exception:
                chosen_idx = 0

        if times and chosen_idx < len(times):
            forecast_ts = times[chosen_idx]

        def _get_hourly_val(k: str) -> Optional[float]:
            vals = hourly.get(k, [])
            if chosen_idx < len(vals) and vals[chosen_idx] is not None:
                return float(vals[chosen_idx])
            return None

        pm25_val = _get_hourly_val("pm2_5")
        pm10_val = _get_hourly_val("pm10")
        no2_val = _get_hourly_val("nitrogen_dioxide")
        eaqi_val = _get_hourly_val("european_aqi")
        usaqi_val = _get_hourly_val("us_aqi")
    else:
        pm25_val = pm10_val = no2_val = eaqi_val = usaqi_val = None

    category, color = _evaluate_european_aqi(eaqi_val)

    return (
        AirQualityData(
            pm2_5=PollutantReading(
                value=round(pm25_val, 1) if pm25_val is not None else None,
                unit=units.get("pm2_5", "μg/m³"),
                status="available" if pm25_val is not None else "missing_from_provider",
            ),
            pm10=PollutantReading(
                value=round(pm10_val, 1) if pm10_val is not None else None,
                unit=units.get("pm10", "μg/m³"),
                status="available" if pm10_val is not None else "missing_from_provider",
            ),
            nitrogen_dioxide=PollutantReading(
                value=round(no2_val, 1) if no2_val is not None else None,
                unit=units.get("nitrogen_dioxide", "μg/m³"),
                status="available" if no2_val is not None else "missing_from_provider",
            ),
            european_aqi=PollutantReading(
                value=round(eaqi_val, 1) if eaqi_val is not None else None,
                unit=units.get("european_aqi", "EAQI"),
                status="available" if eaqi_val is not None else "missing_from_provider",
            ),
            us_aqi=PollutantReading(
                value=round(usaqi_val, 1) if usaqi_val is not None else None,
                unit=units.get("us_aqi", "USAQI"),
                status="available" if usaqi_val is not None else "missing_from_provider",
            ),
            aqi_category=category,
            aqi_color=color,
        ),
        forecast_ts,
    )


def parse_weather_item(
    item: Dict[str, Any], time_str: Optional[str] = None
) -> Tuple[WeatherData, Optional[str]]:
    """Parse a single raw Open-Meteo weather response object."""
    if not item:
        return WeatherData(), None

    units = item.get("current_units") or item.get("hourly_units") or {}
    forecast_ts: Optional[str] = None

    if "current" in item and item["current"]:
        cur = item["current"]
        forecast_ts = cur.get("time")

        def _val(k: str) -> Optional[float]:
            v = cur.get(k)
            return float(v) if v is not None else None

        temp = _val("temperature_2m")
        app_temp = _val("apparent_temperature")
        hum = _val("relative_humidity_2m")
        precip = _val("precipitation")
        wind = _val("wind_speed_10m")
        code = cur.get("weather_code")
        code_int = int(code) if code is not None else None

    elif "hourly" in item and item["hourly"]:
        hourly = item["hourly"]
        times = hourly.get("time", [])
        chosen_idx = 0
        if time_str and times:
            try:
                target_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                min_diff = float("inf")
                for i, t_str in enumerate(times):
                    dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                    diff = abs((dt - target_dt).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        chosen_idx = i
            except Exception:
                chosen_idx = 0

        if times and chosen_idx < len(times):
            forecast_ts = times[chosen_idx]

        def _hourly_val(k: str) -> Optional[float]:
            vals = hourly.get(k, [])
            if chosen_idx < len(vals) and vals[chosen_idx] is not None:
                return float(vals[chosen_idx])
            return None

        temp = _hourly_val("temperature_2m")
        app_temp = _hourly_val("apparent_temperature")
        hum = _hourly_val("relative_humidity_2m")
        precip = _hourly_val("precipitation")
        wind = _hourly_val("wind_speed_10m")
        codes = hourly.get("weather_code", [])
        code_int = int(codes[chosen_idx]) if chosen_idx < len(codes) and codes[chosen_idx] is not None else None
    else:
        temp = app_temp = hum = precip = wind = code_int = None

    return (
        WeatherData(
            temperature_c=round(temp, 1) if temp is not None else None,
            apparent_temperature_c=round(app_temp, 1) if app_temp is not None else None,
            relative_humidity_pct=round(hum, 1) if hum is not None else None,
            precipitation_mm=round(precip, 2) if precip is not None else None,
            wind_speed_kmh=round(wind, 1) if wind is not None else None,
            weather_code=code_int,
            weather_description=_get_wmo_description(code_int),
            temperature_unit=units.get("temperature_2m", "°C"),
            humidity_unit=units.get("relative_humidity_2m", "%"),
            wind_speed_unit=units.get("wind_speed_10m", "km/h"),
        ),
        forecast_ts,
    )


def compute_route_environmental_summary(
    sample_points: List[RouteEnvironmentalPoint],
    forecast_ts: Optional[str] = None,
    departure_time: Optional[str] = None,
    is_stale: bool = False,
    stale_warning: Optional[str] = None,
    cache_age_seconds: Optional[float] = None,
) -> RouteEnvironmentalSummary:
    """Aggregate sampled waypoint readings into a documented route summary.

    Averages only available non-null readings without substituting zeros for missing data.
    Separates retrieval timestamp from forecast/observation timestamp and tracks data freshness.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Determine if evaluating future forecast vs immediate observation
    is_forecast = False
    if departure_time:
        try:
            dep_dt = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if (dep_dt - now_dt).total_seconds() > 300.0:  # > 5 minutes in future
                is_forecast = True
        except Exception:
            pass

    metadata = EnvironmentalMetadata(
        retrieval_timestamp=now_iso,
        forecast_timestamp=forecast_ts,
        observation_or_forecast_timestamp=forecast_ts or now_iso,
        is_forecast=is_forecast,
        departure_time=departure_time,
        is_stale=is_stale,
        stale_warning=stale_warning,
        cache_age_seconds=round(cache_age_seconds, 1) if cache_age_seconds else None,
        is_cached=bool(cache_age_seconds and cache_age_seconds > 0),
    )

    if not sample_points:
        return RouteEnvironmentalSummary(
            air_quality=AirQualityData(),
            weather=WeatherData(),
            metadata=metadata,
            samples_count=0,
            has_air_quality=False,
            has_weather=False,
            notes=["No sample points provided to compute environmental profile."],
        )

    # Gather available non-null readings
    valid_pm25 = [
        p.air_quality.pm2_5.value
        for p in sample_points
        if p.air_quality and p.air_quality.pm2_5 and p.air_quality.pm2_5.value is not None
    ]
    valid_pm10 = [
        p.air_quality.pm10.value
        for p in sample_points
        if p.air_quality and p.air_quality.pm10 and p.air_quality.pm10.value is not None
    ]
    valid_no2 = [
        p.air_quality.nitrogen_dioxide.value
        for p in sample_points
        if p.air_quality and p.air_quality.nitrogen_dioxide and p.air_quality.nitrogen_dioxide.value is not None
    ]
    valid_eaqi = [
        p.air_quality.european_aqi.value
        for p in sample_points
        if p.air_quality and p.air_quality.european_aqi and p.air_quality.european_aqi.value is not None
    ]
    valid_usaqi = [
        p.air_quality.us_aqi.value
        for p in sample_points
        if p.air_quality and p.air_quality.us_aqi and p.air_quality.us_aqi.value is not None
    ]

    valid_temp = [
        p.weather.temperature_c
        for p in sample_points
        if p.weather and p.weather.temperature_c is not None
    ]
    valid_app_temp = [
        p.weather.apparent_temperature_c
        for p in sample_points
        if p.weather and p.weather.apparent_temperature_c is not None
    ]
    valid_hum = [
        p.weather.relative_humidity_pct
        for p in sample_points
        if p.weather and p.weather.relative_humidity_pct is not None
    ]
    valid_precip = [
        p.weather.precipitation_mm
        for p in sample_points
        if p.weather and p.weather.precipitation_mm is not None
    ]
    valid_wind = [
        p.weather.wind_speed_kmh
        for p in sample_points
        if p.weather and p.weather.wind_speed_kmh is not None
    ]

    def _avg(lst: List[float]) -> Optional[float]:
        return round(sum(lst) / len(lst), 1) if lst else None

    avg_pm25 = _avg(valid_pm25)
    avg_pm10 = _avg(valid_pm10)
    avg_no2 = _avg(valid_no2)
    avg_eaqi = _avg(valid_eaqi)
    avg_usaqi = _avg(valid_usaqi)
    category, color = _evaluate_european_aqi(avg_eaqi)

    # Predominant weather code across sample points
    weather_codes = [
        p.weather.weather_code
        for p in sample_points
        if p.weather and p.weather.weather_code is not None
    ]
    predominant_code = weather_codes[0] if weather_codes else None

    notes: List[str] = []
    if not valid_pm25 and not valid_eaqi:
        notes.append("Air quality metrics unavailable for this region/time.")
    if not valid_temp:
        notes.append("Weather metrics unavailable for this region/time.")
    if is_stale and stale_warning:
        notes.append(stale_warning)

    air_quality_summary = AirQualityData(
        pm2_5=PollutantReading(
            value=avg_pm25,
            unit="μg/m³",
            status="available" if avg_pm25 is not None else "missing_from_provider",
        ),
        pm10=PollutantReading(
            value=avg_pm10,
            unit="μg/m³",
            status="available" if avg_pm10 is not None else "missing_from_provider",
        ),
        nitrogen_dioxide=PollutantReading(
            value=avg_no2,
            unit="μg/m³",
            status="available" if avg_no2 is not None else "missing_from_provider",
        ),
        european_aqi=PollutantReading(
            value=avg_eaqi,
            unit="EAQI",
            status="available" if avg_eaqi is not None else "missing_from_provider",
        ),
        us_aqi=PollutantReading(
            value=avg_usaqi,
            unit="USAQI",
            status="available" if avg_usaqi is not None else "missing_from_provider",
        ),
        aqi_category=category,
        aqi_color=color,
    )

    weather_summary = WeatherData(
        temperature_c=_avg(valid_temp),
        apparent_temperature_c=_avg(valid_app_temp),
        relative_humidity_pct=_avg(valid_hum),
        precipitation_mm=round(max(valid_precip), 2) if valid_precip else None,
        wind_speed_kmh=_avg(valid_wind),
        weather_code=predominant_code,
        weather_description=_get_wmo_description(predominant_code),
    )

    return RouteEnvironmentalSummary(
        air_quality=air_quality_summary,
        weather=weather_summary,
        metadata=metadata,
        samples_count=len(sample_points),
        sample_points=sample_points,
        has_air_quality=bool(valid_pm25 or valid_eaqi),
        has_weather=bool(valid_temp),
        is_stale=is_stale,
        stale_warning=stale_warning,
        notes=notes,
    )


async def enrich_routes_with_environmental_data(
    routes: List[Any],
    time_str: Optional[str] = None,
    force_refresh: bool = False,
) -> None:
    """Enrich candidate walking routes with sampled environmental metrics in batch.

    Samples points across all routes and issues unified multi-coordinate requests
    to Open-Meteo, keeping external API roundtrips minimal.
    Supports force_refresh with automatic fallback to stale cache on network failures.
    """
    if not routes:
        return

    # 1. Collect all sample points across all candidate routes
    route_samples_map: List[List[Tuple[int, float, float]]] = []
    all_coords_to_query: List[Tuple[float, float]] = []

    for r in routes:
        samples = sample_route_geometry(r.coordinates, max_samples=4)
        route_samples_map.append(samples)
        for _, lat, lon in samples:
            all_coords_to_query.append((lat, lon))

    if not all_coords_to_query:
        return

    # 2. Fetch air quality and weather concurrently in batch
    aq_task = fetch_air_quality_batch(all_coords_to_query, time_str, force_refresh=force_refresh)
    weather_task = fetch_weather_batch(all_coords_to_query, time_str, force_refresh=force_refresh)
    aq_results, weather_results = await asyncio.gather(aq_task, weather_task)

    all_raw = aq_results + weather_results
    is_stale = any(isinstance(r, dict) and r.get("_is_stale") for r in all_raw)
    stale_warning = next((r.get("_stale_warning") for r in all_raw if isinstance(r, dict) and r.get("_stale_warning")), None)
    valid_ages = [r.get("_cache_age") for r in all_raw if isinstance(r, dict) and r.get("_cache_age") is not None]
    max_cache_age = max(valid_ages) if valid_ages else None

    # 3. Associate results back to each route
    cursor = 0
    for r_idx, r in enumerate(routes):
        samples = route_samples_map[r_idx]
        sample_points: List[RouteEnvironmentalPoint] = []
        forecast_ts: Optional[str] = None

        for s_idx, lat, lon in samples:
            raw_aq = aq_results[cursor] if cursor < len(aq_results) else {}
            raw_wx = weather_results[cursor] if cursor < len(weather_results) else {}

            aq_data, aq_ts = parse_air_quality_item(raw_aq, time_str)
            wx_data, wx_ts = parse_weather_item(raw_wx, time_str)
            if not forecast_ts:
                forecast_ts = aq_ts or wx_ts

            sample_points.append(
                RouteEnvironmentalPoint(
                    point_index=s_idx,
                    lat=lat,
                    lon=lon,
                    air_quality=aq_data,
                    weather=wx_data,
                )
            )
            cursor += 1

        summary = compute_route_environmental_summary(
            sample_points,
            forecast_ts=forecast_ts,
            departure_time=time_str,
            is_stale=is_stale,
            stale_warning=stale_warning,
            cache_age_seconds=max_cache_age,
        )
        r.environment = summary


async def get_point_environmental_data(
    lat: float, lon: float, time_str: Optional[str] = None
) -> SinglePointEnvironmentResponse:
    """Retrieve environmental conditions for a specific point and optional time.

    Used by GET /api/environment?lat=...&lon=...&time=...
    """
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(status_code=400, detail="Latitude must be between -90.0 and 90.0")
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Longitude must be between -180.0 and 180.0")

    if time_str:
        try:
            # Validate ISO timestamp
            datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid time format. Please provide an ISO 8601 timestamp (e.g. 2026-10-10T12:00:00Z)",
            )

    aq_task = fetch_air_quality_batch([(lat, lon)], time_str)
    weather_task = fetch_weather_batch([(lat, lon)], time_str)
    aq_list, wx_list = await asyncio.gather(aq_task, weather_task)

    raw_aq = aq_list[0] if aq_list else {}
    raw_wx = wx_list[0] if wx_list else {}

    is_stale = bool(raw_aq.get("_is_stale") or raw_wx.get("_is_stale"))
    stale_warning = raw_aq.get("_stale_warning") or raw_wx.get("_stale_warning")

    aq_data, aq_ts = parse_air_quality_item(raw_aq, time_str)
    wx_data, wx_ts = parse_weather_item(raw_wx, time_str)
    now_iso = datetime.now(timezone.utc).isoformat()

    is_forecast = False
    if time_str:
        try:
            target_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if (target_dt - now_dt).total_seconds() > 300.0:
                is_forecast = True
        except Exception:
            pass

    metadata = EnvironmentalMetadata(
        retrieval_timestamp=now_iso,
        forecast_timestamp=aq_ts or wx_ts,
        observation_or_forecast_timestamp=aq_ts or wx_ts or now_iso,
        is_forecast=is_forecast,
        departure_time=time_str,
        is_stale=is_stale,
        stale_warning=stale_warning,
    )

    return SinglePointEnvironmentResponse(
        latitude=lat,
        longitude=lon,
        requested_time=time_str,
        air_quality=aq_data,
        weather=wx_data,
        metadata=metadata,
    )
