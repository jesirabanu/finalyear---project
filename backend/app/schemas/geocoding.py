"""Geocoding Schemas
Defines structured results returned by the backend geocoding endpoint.
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GeocodeResult(BaseModel):
    """Structured location search result from Nominatim."""
    place_id: int = Field(..., description="Unique provider place identifier")
    display_name: str = Field(..., description="Full descriptive location name or address")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    type: Optional[str] = Field(default=None, description="Feature category or type")
    importance: Optional[float] = Field(default=None, description="Relevance ranking score")


class ReverseGeocodeResult(BaseModel):
    """Structured reverse geocoding result from Nominatim."""
    place_id: Optional[int] = Field(default=None, description="Unique provider place identifier")
    display_name: str = Field(..., description="Human-readable descriptive location name or address")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    address: Optional[Dict[str, Any]] = Field(default=None, description="Detailed address components")

