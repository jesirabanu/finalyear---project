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


class RouteEnvironmentalPoint(BaseModel):
    """Environmental reading at a specific sampled waypoint along a route."""
    point_index: int = Field(..., description="Index of sample point along route (0=start, etc.)")
    lat: float = Field(..., description="Sample point latitude")
    lon: float = Field(..., description="Sample point longitude")
    air_quality: Optional[AirQualityData] = None
    weather: Optional[WeatherData] = None


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
    notes: List[str] = Field(default_factory=list, description="Operational notes, warnings, or missing variable details")


class SinglePointEnvironmentResponse(BaseModel):
    """Response returned by GET /api/environment."""
    latitude: float
    longitude: float
    requested_time: Optional[str] = None
    air_quality: AirQualityData
    weather: WeatherData
    metadata: EnvironmentalMetadata
