"""Environmental Data Schemas
Defines structured representations for air quality, weather data, route sampling,
and metadata including provider attribution, timestamps, and model resolution disclaimers.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PollutantReading(BaseModel):
    """Individual pollutant reading with explicit units and validity status."""
    value: Optional[float] = Field(
        default=None,
        description="Pollutant concentration or index value (None if unrecorded/missing)"
    )
    unit: str = Field(..., description="Measurement unit (e.g. μg/m³, EAQI)")
    status: str = Field(
        default="available",
        description="Status: 'available', 'missing_from_provider', or 'out_of_range'"
    )


class AirQualityData(BaseModel):
    """Air quality metrics retrieved from Open-Meteo Air Quality API (Copernicus CAMS)."""
    pm2_5: Optional[PollutantReading] = Field(default=None, description="Particulate Matter < 2.5 μm")
    pm10: Optional[PollutantReading] = Field(default=None, description="Particulate Matter < 10 μm")
    nitrogen_dioxide: Optional[PollutantReading] = Field(default=None, description="Nitrogen Dioxide (NO2)")
    european_aqi: Optional[PollutantReading] = Field(default=None, description="European Air Quality Index")
    us_aqi: Optional[PollutantReading] = Field(default=None, description="United States Air Quality Index")
    aqi_category: Optional[str] = Field(
        default=None,
        description="Descriptive rating: 'Good', 'Fair', 'Moderate', 'Poor', 'Very Poor', 'Extremely Poor'"
    )
    aqi_color: Optional[str] = Field(
        default=None,
        description="Hex color code for visual AQI indicator"
    )


class WeatherData(BaseModel):
    """Meteorological conditions from Open-Meteo Forecast API (ECMWF/ICON)."""
    temperature_c: Optional[float] = Field(default=None, description="Ambient air temperature at 2m in °C")
    apparent_temperature_c: Optional[float] = Field(default=None, description="Perceived / 'feels-like' temperature in °C")
    relative_humidity_pct: Optional[float] = Field(default=None, description="Relative humidity percentage")
    precipitation_mm: Optional[float] = Field(default=None, description="Precipitation rate in mm")
    wind_speed_kmh: Optional[float] = Field(default=None, description="Wind speed at 10m in km/h")
    weather_code: Optional[int] = Field(default=None, description="WMO weather interpretation code")
    weather_description: Optional[str] = Field(default=None, description="Human-readable weather description")
    temperature_unit: str = Field(default="°C", description="Temperature unit")
    humidity_unit: str = Field(default="%", description="Humidity unit")
    wind_speed_unit: str = Field(default="km/h", description="Wind speed unit")


class EnvironmentalMetadata(BaseModel):
    """Transparent metadata regarding provider, models, temporal timestamps, and resolution limits."""
    provider: str = Field(default="Open-Meteo", description="API Service Provider")
    air_quality_source: str = Field(
        default="Copernicus Atmosphere Monitoring Service (CAMS) & European Environment Agency",
        description="Atmospheric chemical transport model source"
    )
    weather_source: str = Field(
        default="ECMWF & DWD ICON Numerical Weather Prediction Models",
        description="Meteorological model source"
    )
    retrieval_timestamp: str = Field(..., description="ISO 8601 timestamp when data was fetched by the backend")
    forecast_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 validity timestamp of the model forecast step"
    )
    observation_or_forecast_timestamp: Optional[str] = Field(
        default=None,
        description="Observation or forecast validity timestamp corresponding to departure time"
    )
    is_forecast: bool = Field(
        default=False,
        description="True if evaluating against future forecast step rather than current observation"
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="User-selected departure time (ISO 8601) or None for immediate departure"
    )
    is_stale: bool = Field(
        default=False,
        description="True if external API refresh failed and previously cached data was retained"
    )
    stale_warning: Optional[str] = Field(
        default=None,
        description="Explicit user warning when presenting retained stale data"
    )
    cache_age_seconds: Optional[float] = Field(
        default=None,
        description="Age in seconds of cached environmental readings"
    )
    is_modeled: bool = Field(
        default=True,
        description="Explicit flag indicating data is derived from numerical models rather than in-situ street sensors"
    )
    data_nature: str = Field(
        default="gridded_forecast_model",
        description="Categorization: 'gridded_forecast_model', 'measured_in_situ', or 'interpolated'"
    )
    spatial_resolution_note: str = Field(
        default=(
            "Regional atmospheric and meteorological model grid (~11 km air quality, ~2-11 km weather). "
            "Reflects regional area estimates rather than micro-scale, hyper-local street canyon measurements."
        ),
        description="Honest spatial limitation notice"
    )
    license_attribution: str = Field(
        default="Weather & Air Quality data by Open-Meteo.com under Open Database License (ODbL).",
        description="Required provider licensing and attribution"
    )
    is_cached: bool = Field(default=False, description="True if served from backend in-memory cache")


class GreeneryData(BaseModel):
    """Greenery presence and canopy buffer metrics along a walking corridor."""
    score: Optional[float] = Field(
        default=None,
        description="Overall greenery proximity indicator (0 to 100%, higher is better)"
    )
    unit: str = Field(default="%", description="Measurement unit")
    status: str = Field(
        default="available",
        description="Status: 'available', 'empty_osm_coverage', 'missing_from_provider', or 'timeout'"
    )
    greenery_fraction: Optional[float] = Field(
        default=None,
        description="Fraction of route waypoints within defined buffer distance of mapped green area [0.0 - 1.0]"
    )
    buffer_distance_m: float = Field(
        default=50.0,
        description="Buffer distance in metres used to identify adjacent green areas"
    )
    parks_count: Optional[int] = Field(
        default=None,
        description="Number of distinct green spaces/parks adjacent to route corridor"
    )
    mapped_features_count: Optional[int] = Field(
        default=None,
        description="Total OSM green features returned in the bounded corridor"
    )
    source: str = Field(
        default="OpenStreetMap Overpass API (leisure=park/garden, landuse=grass/forest, natural=wood/tree)",
        description="Data source and query tags"
    )
    is_estimated: bool = Field(
        default=True,
        description="Indicates that greenery is computed from mapped polygon proximities rather than in-situ sensor data"
    )
    limitation_note: str = Field(
        default=(
            "Proximity to mapped OSM greenery indicates spatial buffer presence only; it is not equivalent "
            "to a measured Green View Index (GVI), actual canopy density, tree shade, or air pollution reduction."
        ),
        description="Documented scientific and spatial limitation"
    )


class LiveTrafficMetrics(BaseModel):
    """Real-time vehicular speed and congestion metrics from live traffic API."""
    congestion_pct: Optional[float] = Field(
        default=None,
        description="Estimated road traffic congestion percentage (0% = free flow, 100% = standstill)"
    )
    current_speed_kmh: Optional[float] = Field(default=None, description="Current motor vehicle speed in km/h")
    free_flow_speed_kmh: Optional[float] = Field(default=None, description="Historical free-flow speed in km/h")
    provider: Optional[str] = Field(default="TomTom Traffic Flow API", description="Live traffic service provider")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of live traffic observation")
    status: str = Field(default="unavailable", description="'available', 'unavailable', or 'no_key'")


class StaticRoadProxyMetrics(BaseModel):
    """Static road infrastructure exposure proxy based on roadway hierarchy and proximity."""
    major_road_nearby_pct: Optional[float] = Field(
        default=None,
        description="Percentage of route within 50m of mapped major roadways (motorway, trunk, primary)"
    )
    dominant_road_class: Optional[str] = Field(
        default=None,
        description="Dominant roadway classification along path (e.g. 'footway', 'residential', 'primary')"
    )
    major_roads_count: Optional[int] = Field(
        default=None,
        description="Count of major motorized roadways intersecting the route corridor buffer"
    )
    source: str = Field(
        default="OpenStreetMap Highway Infrastructure Hierarchy",
        description="Infrastructure data source"
    )
    status: str = Field(default="available", description="'available', 'empty_osm_coverage', or 'unavailable'")


class TrafficExposureData(BaseModel):
    """Traffic exposure metrics separating live congestion from static road classification proxies."""
    score: Optional[float] = Field(
        default=None,
        description="Traffic exposure index (0 to 100; lower is better / less traffic exposure)"
    )
    unit: str = Field(default="index (0-100)", description="Index unit")
    status: str = Field(
        default="available",
        description="Status: 'available', 'live_measured', 'static_proxy_estimated', or 'unavailable'"
    )
    metric_type: str = Field(
        default="static_road_hierarchy_proxy",
        description="Explicit identifier: 'live_traffic_congestion' or 'static_road_hierarchy_proxy'"
    )
    is_live_measurement: bool = Field(
        default=False,
        description="Strictly False if based on static road classification proxy; True only if from live speed API"
    )
    road_class: Optional[str] = Field(
        default=None,
        description="Dominant roadway classification along the walking path"
    )
    source: str = Field(
        default="OpenStreetMap Highway Infrastructure Hierarchy (Major Road Proximity Proxy)",
        description="Data source"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="Observation or retrieval timestamp"
    )
    limitation_note: str = Field(
        default=(
            "Static infrastructure proxy based on proximity to mapped major roadways. "
            "Does NOT represent live vehicular traffic volume, real-time speed, or transient congestion."
        ),
        description="Explicit disclosure of proxy methodology and limitations"
    )
    live_traffic: Optional[LiveTrafficMetrics] = Field(
        default=None,
        description="Live traffic speed and congestion metrics when API provider is configured"
    )
    static_proxy: Optional[StaticRoadProxyMetrics] = Field(
        default=None,
        description="Static road hierarchy and major road proximity proxy metrics"
    )
    time_applicability_note: Optional[str] = Field(
        default=None,
        description="Temporal applicability notice (e.g. explains that live traffic applies only to immediate departures)"
    )


class RouteEnvironmentalPoint(BaseModel):
    """Environmental reading at a specific sampled waypoint along a route."""
    point_index: int = Field(..., description="Index of sample point along route (0=start, etc.)")
    lat: float = Field(..., description="Sample point latitude")
    lon: float = Field(..., description="Sample point longitude")
    air_quality: Optional[AirQualityData] = None
    weather: Optional[WeatherData] = None
    greenery: Optional[GreeneryData] = None
    traffic_exposure: Optional[TrafficExposureData] = None


class RouteEnvironmentalSummary(BaseModel):
    """Aggregated environmental profile associated with an entire walking route."""
    air_quality: AirQualityData
    weather: WeatherData
    metadata: EnvironmentalMetadata
    samples_count: int = Field(..., description="Number of waypoints sampled along the route geometry")
    sampling_method: str = Field(
        default="evenly_spaced_route_geometry",
        description="Documented methodology used to select route sample points"
    )
    sample_points: List[RouteEnvironmentalPoint] = Field(
        default_factory=list,
        description="Individual waypoint readings along the route"
    )
    summary_method_note: str = Field(
        default=(
            "Route-level summary represents mean concentrations and peak exposures computed across "
            "sampled coordinates along the walking path, avoiding artificial zero-filling of missing variables."
        ),
        description="Documentation of aggregation arithmetic"
    )
    has_air_quality: bool = Field(default=True, description="True if air quality data was successfully obtained")
    has_weather: bool = Field(default=True, description="True if weather data was successfully obtained")
    greenery: Optional[GreeneryData] = Field(default=None, description="Greenery / park presence data")
    traffic_exposure: Optional[TrafficExposureData] = Field(default=None, description="Traffic exposure data")
    has_greenery: bool = Field(default=False, description="True if greenery data was obtained")
    has_traffic: bool = Field(default=False, description="True if traffic exposure data was obtained")
    is_stale: bool = Field(default=False, description="True if served as stale fallback following a refresh failure")
    stale_warning: Optional[str] = Field(default=None, description="User-facing warning if data is stale")
    notes: List[str] = Field(default_factory=list, description="Operational notes, warnings, or missing variable details")


class SinglePointEnvironmentResponse(BaseModel):
    """Response returned by GET /api/environment."""
    latitude: float
    longitude: float
    requested_time: Optional[str] = None
    air_quality: AirQualityData
    weather: WeatherData
    metadata: EnvironmentalMetadata
