"""Preferences and Ranking Schemas
Defines request and response models for multi-criteria route evaluation,
Pareto-dominance analysis, metric details, and transparent recommendations.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.routes import RouteModel


class PreferenceSelection(BaseModel):
    """User-selected criteria for route ranking.
    No numerical weights or fixed health profile categories.
    """
    air_quality: bool = Field(default=False, description="Prioritize cleaner air (lower EAQI / PM2.5)")
    temperature: bool = Field(default=False, description="Prioritize thermal comfort / lower heat exposure")
    traffic_exposure: bool = Field(default=False, description="Prioritize lower motorized traffic exposure")
    greenery: bool = Field(default=False, description="Prioritize tree canopy, parks, and vegetation presence")
    walking_distance: bool = Field(default=False, description="Prioritize shorter walking distance")
    no_preference: bool = Field(
        default=False,
        description="Explicitly opt out of preference filtering; applies transparent default baseline"
    )

    def active_factors(self) -> List[str]:
        """Return list of selected factor keys. If no_preference is True, returns empty list."""
        if self.no_preference:
            return []
        factors = []
        if self.air_quality:
            factors.append("air_quality")
        if self.temperature:
            factors.append("temperature")
        if self.traffic_exposure:
            factors.append("traffic_exposure")
        if self.greenery:
            factors.append("greenery")
        if self.walking_distance:
            factors.append("walking_distance")
        return factors


class FactorMetricDetail(BaseModel):
    """Detailed breakdown for a single evaluation factor on a specific route."""
    factor: str = Field(..., description="Factor key identifier")
    label: str = Field(..., description="Human-readable factor label")
    raw_value: Optional[float] = Field(default=None, description="Actual physical measurement or index")
    unit: str = Field(..., description="Measurement unit (e.g. m, °C, EAQI, %)")
    better_direction: str = Field(..., description="'lower' or 'higher' indicates preferable direction")
    normalized_score: Optional[float] = Field(
        default=None,
        description="Dimensionless score in [0.0, 1.0], where 1.0 is most favorable and 0.0 is least favorable"
    )
    is_available: bool = Field(default=True, description="False if provider lacked data for this metric")
    status_note: Optional[str] = Field(default=None, description="Note on measurement source or status")


class RankedRoute(RouteModel):
    """Extended RouteModel containing algorithmic ranking results, Pareto dominance,
    concise trade-offs, and factor-by-factor breakdown.
    """
    rank: int = Field(..., description="1-based rank order (1 is most recommended)")
    multi_criteria_score: float = Field(
        ...,
        description="Equal-priority normalized composite score in [0.0, 1.0]"
    )
    is_recommended: bool = Field(
        default=False,
        description="True for the primary recommended route (Rank 1)"
    )
    is_pareto_dominated: bool = Field(
        default=False,
        description="True if another candidate route is strictly better or equal on all active factors"
    )
    dominated_by: List[str] = Field(
        default_factory=list,
        description="IDs of candidate routes that Pareto-dominate this route"
    )
    recommendation_status: str = Field(
        ...,
        description="Descriptive status (e.g., 'Recommended (Rank 1)', 'Pareto-Optimal Alternative', 'Dominated Alternative')"
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Bullet points explaining why this route achieved this rank"
    )
    trade_offs: str = Field(
        ...,
        description="Concise description of trade-offs relative to other candidate routes"
    )
    factor_details: Dict[str, FactorMetricDetail] = Field(
        default_factory=dict,
        description="Factor-by-factor measurements, units, and normalized scores"
    )


class RouteRankingRequest(BaseModel):
    """Request payload for ranking candidate routes according to user-selected preferences."""
    routes: List[RouteModel] = Field(..., min_length=1, description="List of candidate walking routes to evaluate")
    preferences: PreferenceSelection = Field(
        default_factory=PreferenceSelection,
        description="Selected environmental and distance preferences"
    )


class RouteComparisonRow(BaseModel):
    """Structured row for frontend comparison table across candidate routes."""
    route_id: str
    route_name: str
    rank: int
    is_recommended: bool
    is_pareto_dominated: bool
    distance_km: float
    duration_min: float
    air_quality_raw: Optional[float] = None
    air_quality_score: Optional[float] = None
    temperature_c: Optional[float] = None
    temperature_score: Optional[float] = None
    traffic_score_raw: Optional[float] = None
    traffic_score: Optional[float] = None
    greenery_raw: Optional[float] = None
    greenery_score: Optional[float] = None
    walking_distance_m: float
    distance_score: Optional[float] = None
    overall_score: float


class MetricChange(BaseModel):
    """Explains a metric change for a route following data refresh or departure time update."""
    route_id: str
    route_name: str
    factor: str
    previous_value: Optional[float] = None
    new_value: Optional[float] = None
    unit: str
    change_summary: str


class ReevaluationSummary(BaseModel):
    """Transparent summary explaining environmental changes and recommendation impact."""
    previous_recommended_route_id: Optional[str] = None
    new_recommended_route_id: Optional[str] = None
    recommendation_changed: bool = False
    recommendation_change_note: str
    metric_changes: List[MetricChange] = Field(default_factory=list)
    has_changes: bool = False
    disclaimer: str = Field(
        default="Pre-trip route comparison re-evaluation only. This application does not perform automatic in-walk navigation or real-time GPS rerouting.",
        description="Explicit limitation notice"
    )


class RouteRefreshRequest(BaseModel):
    """Request payload to refresh only the environmental data for candidate routes."""
    routes: List[RouteModel] = Field(..., min_length=1, description="Existing candidate routes")
    preferences: PreferenceSelection = Field(default_factory=PreferenceSelection)
    departure_time: Optional[str] = Field(default=None, description="Updated departure time (ISO 8601)")
    force_refresh: bool = Field(default=True, description="Bypass cache for environmental providers")


class RouteRankingResponse(BaseModel):
    """Complete response returned by POST /api/rank."""
    ranked_routes: List[RankedRoute] = Field(..., description="Routes ordered from best (Rank 1) to worst")
    selected_factors: List[str] = Field(..., description="Factors explicitly selected by user")
    active_evaluation_factors: List[str] = Field(
        ...,
        description="Factors actually evaluated after handling missing data and default rules"
    )
    missing_selected_factors: List[str] = Field(
        default_factory=list,
        description="Selected factors that were excluded due to missing provider data"
    )
    is_default_evaluation: bool = Field(
        default=False,
        description="True if system evaluated all supported factors because no preferences were selected"
    )
    confidence: str = Field(
        default="high",
        description="'high', 'moderate', or 'low' (withheld recommendation if all selected factors missing)"
    )
    withheld_recommendation: bool = Field(
        default=False,
        description="True if a confident recommendation was withheld due to insufficient data"
    )
    algorithmic_explanation: str = Field(
        ...,
        description="Transparent documentation of normalization, equal-priority weights, Pareto dominance, and tie-breaking"
    )
    comparison_matrix: List[RouteComparisonRow] = Field(
        default_factory=list,
        description="Comparison matrix rows formatted for direct table rendering"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Operational notices regarding missing factors or withheld confidence"
    )


class RouteRefreshResponse(BaseModel):
    """Response returning refreshed routes, updated ranking, and change explanation."""
    routes: List[RouteModel]
    ranking: RouteRankingResponse
    reevaluation: ReevaluationSummary
