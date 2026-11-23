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
    ORS_API_URL: str = "https://api.heigit.org/openrouteservice/v2/directions/foot-walking/geojson"
    OSRM_ROUTING_URL: str = "https://router.project-osrm.org/route/v1/foot"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_TIMEOUT_SECONDS: float = 10.0
    OVERPASS_CACHE_TTL_SECONDS: int = 900
    NOMINATIM_API_URL: str = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_REVERSE_API_URL: str = "https://nominatim.openstreetmap.org/reverse"
    NOMINATIM_USER_AGENT: str = "EcoWalk-PedestrianRouting/1.0 (academic-pedestrian-routing)"
    
    # Optional Live Traffic API (TomTom Traffic Flow API)
    TOMTOM_TRAFFIC_API_KEY: str = ""
    TOMTOM_TRAFFIC_API_URL: str = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
    TRAFFIC_CACHE_TTL_SECONDS: int = 600
    TRAFFIC_TIMEOUT_SECONDS: float = 6.0
    
    # Open-Meteo Environmental Endpoints
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_WEATHER_URL: str = "https://api.open-meteo.com/v1/forecast"
    ENVIRONMENT_CACHE_TTL_SECONDS: int = 900
    ENVIRONMENT_TIMEOUT_SECONDS: float = 8.0
    
    # Refresh & Rate Limiting Settings
    MIN_REFRESH_INTERVAL_SECONDS: float = 5.0  # Minimum delay between user manual refreshes
    STALE_DATA_MAX_AGE_SECONDS: int = 86400    # 24 hours max age for retaining stale cache on provider failure
    
    # CORS Origins for frontend communication
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
