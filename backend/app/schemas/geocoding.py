"""Geocoding Schemas
Defines structured results returned by the backend geocoding endpoint.
"""
from typing import Optional
from pydantic import BaseModel, Field


class GeocodeResult(BaseModel):
    """Structured location search result from Nominatim."""
    place_id: int = Field(..., description="Unique provider place identifier")
    display_name: str = Field(..., description="Full descriptive location name or address")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    type: Optional[str] = Field(default=None, description="Feature category or type")
    importance: Optional[float] = Field(default=None, description="Relevance ranking score")
