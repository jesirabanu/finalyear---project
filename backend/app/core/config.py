"""Application Configuration
Loads environment variables cleanly using pydantic-settings.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Third-party API credentials & endpoints
    ORS_API_KEY: str = ""
    ORS_API_URL: str = "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_API_URL: str = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_USER_AGENT: str = "EcoWalk-PedestrianRouting/1.0 (academic-pedestrian-routing)"
    
    # Open-Meteo Environmental Endpoints
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_WEATHER_URL: str = "https://api.open-meteo.com/v1/forecast"
    ENVIRONMENT_CACHE_TTL_SECONDS: int = 900
    ENVIRONMENT_TIMEOUT_SECONDS: float = 8.0
    
    # CORS Origins for frontend communication
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
