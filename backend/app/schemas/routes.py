"""Route Request and Response Schemas
Defines request parameters, validation, and route structure including Leaflet-formatted coordinates.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.schemas.coordinates import CoordinatePoint
from app.schemas.environment import RouteEnvironmentalSummary


class RouteRequest(BaseModel):
    """Request payload for finding walking routes between two waypoints."""
    source: CoordinatePoint = Field(
        ...,
        description="Starting location coordinates"
    )
    destination: CoordinatePoint = Field(
        ...,
        description="Target destination coordinates"
    )
    alternatives: int = Field(
        default=2,
        ge=0,
        le=3,
        description="Target number of alternative walking routes to request (0 to 3)"
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional ISO 8601 departure timestamp (e.g. 2026-10-22T15:00:00Z). None defaults to immediate departure."
    )
    force_refresh: bool = Field(
        default=False,
        description="If True, bypasses local TTL cache to retrieve fresh provider data"
    )

    @model_validator(mode="after")
    def validate_distinct_points(self) -> "RouteRequest":
        """Verify that source and destination are not identical locations."""
        lat_diff = abs(self.source.lat - self.destination.lat)
        lon_diff = abs(self.source.lon - self.destination.lon)
        if lat_diff < 1e-5 and lon_diff < 1e-5:
            raise ValueError(
                "Source and destination must be distinct locations. "
                "Provided coordinates are practically identical."
            )
        return self


class RouteStepModel(BaseModel):
    """Model representing an individual turn-by-turn walking instruction/maneuver."""
    instruction: str = Field(..., description="Human-readable turn-by-turn instruction text")
    distance_m: float = Field(default=0.0, description="Step distance in metres")
    duration_s: float = Field(default=0.0, description="Step duration in seconds")
    type: Optional[int] = Field(default=None, description="Maneuver action code (e.g. ORS step type)")
    modifier: Optional[str] = Field(default=None, description="Maneuver modifier (e.g. 'left', 'right', 'straight')")
    name: Optional[str] = Field(default=None, description="Street or pathway name")
    location: Optional[List[float]] = Field(default=None, description="Starting coordinate [latitude, longitude]")
    way_points: Optional[List[int]] = Field(default=None, description="Start and end coordinate index interval [start_idx, end_idx]")


class RouteModel(BaseModel):
    """Model representing an individual calculated walking route.

    Coordinate format documentation:
    - `coordinates`: Formatted as `[[latitude, longitude], ...]` for direct consumption
      by Leaflet `Polyline` components without requiring frontend coordinate inversion.
    - `geojson_geometry`: Standard GeoJSON LineString geometry formatted as
      `{"type": "LineString", "coordinates": [[longitude, latitude], ...]}`.
    """
    id: str = Field(..., description="Stable unique identifier for the route (e.g. route_0)")
    name: str = Field(..., description="Descriptive label (e.g. Primary Walking Path)")
    distance_m: float = Field(..., description="Total walking distance in metres")
    distance_km: float = Field(..., description="Total walking distance in kilometres (rounded)")
    duration_s: float = Field(..., description="Estimated walking duration in seconds")
    duration_min: float = Field(..., description="Estimated walking duration in minutes (rounded)")
    coordinates: List[List[float]] = Field(
        ...,
        description="List of [latitude, longitude] pairs ready for Leaflet Polyline rendering"
    )
    geojson_geometry: Optional[Dict[str, Any]] = Field(
        default=None,
        description="GeoJSON geometry object with [longitude, latitude] coordinates"
    )
    color: str = Field(default="#2563eb", description="Suggested distinct hex color code for map display")
    is_primary: bool = Field(default=False, description="Whether this is the primary recommended route")
    summary: Optional[str] = Field(default=None, description="Brief summary description of the route")
    steps: List[RouteStepModel] = Field(
        default_factory=list,
        description="Ordered turn-by-turn walking maneuver instructions"
    )
    environment: Optional["RouteEnvironmentalSummary"] = Field(
        default=None,
        description="Environmental profile (air quality and temperature) associated with this route"
    )
    available_environmental_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of available environmental and distance measurements"
    )
    metric_units: Dict[str, str] = Field(
        default_factory=dict,
        description="Measurement units corresponding to each available metric"
    )
    timestamps: Dict[str, Any] = Field(
        default_factory=dict,
        description="Retrieval and validity timestamps for environmental data"
    )
    source_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Attribution and provenance metadata for route and environmental services"
    )
    data_quality_status: str = Field(
        default="complete",
        description="Overall data completeness: 'complete', 'partial_data', or 'insufficient_data'"
    )
    missing_factors: List[str] = Field(
        default_factory=list,
        description="List of factors with missing, unrecorded, or unavailable data"
    )


class RouteResponse(BaseModel):
    """Complete response returned by POST /api/routes."""
    routes: List[RouteModel] = Field(..., description="List of parsed walking routes")
    total_routes: int = Field(..., description="Number of routes returned")
    has_alternatives: bool = Field(
        ...,
        description="True if genuine provider alternatives are returned, False if only 1 route was available"
    )
    source: CoordinatePoint = Field(..., description="Echo of origin point")
    destination: CoordinatePoint = Field(..., description="Echo of destination point")
    message: Optional[str] = Field(
        default=None,
        description="Informative message regarding route generation or alternative availability"
    )
