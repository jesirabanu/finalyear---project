"""Coordinate Schemas
Defines geographical coordinate representations with bounds validation.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CoordinatePoint(BaseModel):
    """Geographical coordinate point representation.

    Attributes:
        lat: Latitude in decimal degrees, bounded by [-90.0, 90.0].
        lon: Longitude in decimal degrees, bounded by [-180.0, 180.0].
        label: Optional human-readable location name or address.
    """
    lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees between -90.0 and 90.0",
        examples=[51.5138]
    )
    lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees between -180.0 and 180.0",
        examples=[-0.0984]
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable address or description",
        examples=["St. Paul's Cathedral, London"]
    )
