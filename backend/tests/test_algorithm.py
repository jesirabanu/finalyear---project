"""Tests for Multi-Criteria Preference Ranking Engine.
Covers:
- Lower-is-better factors (air quality, temperature, distance, traffic)
- Higher-is-better factor (greenery)
- Conflicting criteria and trade-off generation
- Pareto-dominated routes identification
- Ties and deterministic, stable tie-breaking
- Missing data handling (no zero-filling, transparent exclusion, withheld recommendation)
- Single route and multiple routes evaluation
- No-preference selection and default baseline
- Proof of zero fixed/arbitrary weights (equal priority 1/k)
- POST /api/rank endpoint validation and responses
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.algorithm.ranking_engine import (
    FACTOR_SPECS,
    extract_raw_metric,
    normalize_factor_values,
    compute_pareto_dominance,
    rank_routes,
)
from app.schemas.environment import (
    AirQualityData,
    EnvironmentalMetadata,
    GreeneryData,
    PollutantReading,
    RouteEnvironmentalSummary,
    TrafficExposureData,
    WeatherData,
)
from app.schemas.preferences import PreferenceSelection, RouteRankingRequest
from app.schemas.routes import RouteModel

client = TestClient(app)


def make_test_route(
    route_id: str,
    name: str = "Test Route",
    distance_m: float = 1000.0,
    eaqi: float = 30.0,
    temp_c: float = 20.0,
    greenery_pct: float = 50.0,
    traffic_idx: float = 40.0,
    omit_eaqi: bool = False,
    omit_greenery: bool = False,
    omit_traffic: bool = False,
) -> RouteModel:
    """Helper to create a populated RouteModel for ranking tests."""
    aq = AirQualityData(
        european_aqi=PollutantReading(
            value=eaqi if not omit_eaqi else None,
            unit="EAQI",
            status="available" if not omit_eaqi else "missing_from_provider",
        )
    )
    wx = WeatherData(
        temperature_c=temp_c,
        apparent_temperature_c=temp_c,
    )
    gr = GreeneryData(
        score=greenery_pct if not omit_greenery else None,
        unit="%",
        status="available" if not omit_greenery else "missing_from_provider",
    )
    tr = TrafficExposureData(
        score=traffic_idx if not omit_traffic else None,
        unit="index (0-100)",
        status="available" if not omit_traffic else "missing_from_provider",
    )
    meta = EnvironmentalMetadata(
        retrieval_timestamp="2026-10-22T12:00:00Z",
    )

    env = RouteEnvironmentalSummary(
        air_quality=aq,
        weather=wx,
        greenery=gr,
        traffic_exposure=tr,
        metadata=meta,
        samples_count=3,
        has_air_quality=not omit_eaqi,
        has_weather=True,
        has_greenery=not omit_greenery,
        has_traffic=not omit_traffic,
    )

    avail_metrics = {
        "walking_distance": distance_m,
        "air_quality": eaqi if not omit_eaqi else None,
        "temperature": temp_c,
        "greenery": greenery_pct if not omit_greenery else None,
        "traffic_exposure": traffic_idx if not omit_traffic else None,
    }

    units = {
        "walking_distance": "m",
        "air_quality": "EAQI",
        "temperature": "°C",
        "greenery": "%",
        "traffic_exposure": "index (0-100)",
    }

    missing = []
    if omit_eaqi:
        missing.append("air_quality")
    if omit_greenery:
        missing.append("greenery")
    if omit_traffic:
        missing.append("traffic_exposure")

    return RouteModel(
        id=route_id,
        name=name,
        distance_m=distance_m,
        distance_km=round(distance_m / 1000.0, 2),
        duration_s=round(distance_m / 1.4, 1),
        duration_min=round(distance_m / 84.0, 1),
        coordinates=[[51.5, -0.1], [51.51, -0.09]],
        environment=env,
        available_environmental_metrics=avail_metrics,
        metric_units=units,
        missing_factors=missing,
        data_quality_status="complete" if not missing else "partial_data",
        timestamps={"retrieval_timestamp": "2026-10-22T12:00:00Z"},
        source_metadata={"routing_provider": "OpenRouteService"},
    )


class TestLowerAndHigherFactors:
    """Verifies that each factor optimizes in its documented direction."""

    def test_lower_is_better_air_quality(self):
        """Lower EAQI (cleaner air) must achieve a higher normalized score and rank #1."""
        clean_route = make_test_route("r_clean", "Clean Route", eaqi=15.0)
        dirty_route = make_test_route("r_dirty", "Dirty Route", eaqi=65.0)

        res = rank_routes([clean_route, dirty_route], PreferenceSelection(air_quality=True))

        assert res.ranked_routes[0].id == "r_clean"
        assert res.ranked_routes[0].rank == 1
        assert res.ranked_routes[0].factor_details["air_quality"].normalized_score == 1.0
        assert res.ranked_routes[1].id == "r_dirty"
        assert res.ranked_routes[1].factor_details["air_quality"].normalized_score == 0.0

    def test_lower_is_better_temperature(self):
        """Lower temperature (less heat stress) must achieve a higher score and rank #1."""
        cool_route = make_test_route("r_cool", "Cool Route", temp_c=18.0)
        hot_route = make_test_route("r_hot", "Hot Route", temp_c=34.0)

        res = rank_routes([cool_route, hot_route], PreferenceSelection(temperature=True))

        assert res.ranked_routes[0].id == "r_cool"
        assert res.ranked_routes[0].factor_details["temperature"].normalized_score == 1.0
        assert res.ranked_routes[1].id == "r_hot"
        assert res.ranked_routes[1].factor_details["temperature"].normalized_score == 0.0

    def test_lower_is_better_walking_distance(self):
        """Shorter walking distance must achieve a higher score and rank #1."""
        short_route = make_test_route("r_short", "Short Route", distance_m=1200.0)
        long_route = make_test_route("r_long", "Long Route", distance_m=2400.0)

        res = rank_routes([short_route, long_route], PreferenceSelection(walking_distance=True))

        assert res.ranked_routes[0].id == "r_short"
        assert res.ranked_routes[0].factor_details["walking_distance"].normalized_score == 1.0
        assert res.ranked_routes[1].id == "r_long"
        assert res.ranked_routes[1].factor_details["walking_distance"].normalized_score == 0.0

    def test_lower_is_better_traffic_exposure(self):
        """Lower traffic exposure index must achieve a higher score and rank #1."""
        quiet_route = make_test_route("r_quiet", "Quiet Route", traffic_idx=15.0)
        busy_route = make_test_route("r_busy", "Busy Route", traffic_idx=85.0)

        res = rank_routes([quiet_route, busy_route], PreferenceSelection(traffic_exposure=True))

        assert res.ranked_routes[0].id == "r_quiet"
        assert res.ranked_routes[0].factor_details["traffic_exposure"].normalized_score == 1.0
        assert res.ranked_routes[1].id == "r_busy"
        assert res.ranked_routes[1].factor_details["traffic_exposure"].normalized_score == 0.0

    def test_higher_is_better_greenery(self):
        """Higher greenery presence (%) must achieve a higher score and rank #1."""
        green_route = make_test_route("r_green", "Park Route", greenery_pct=85.0)
        concrete_route = make_test_route("r_concrete", "Urban Alley", greenery_pct=15.0)

        res = rank_routes([green_route, concrete_route], PreferenceSelection(greenery=True))

        assert res.ranked_routes[0].id == "r_green"
        assert res.ranked_routes[0].factor_details["greenery"].normalized_score == 1.0
        assert res.ranked_routes[1].id == "r_concrete"
        assert res.ranked_routes[1].factor_details["greenery"].normalized_score == 0.0


class TestParetoDominance:
    """Verifies identification and penalization of Pareto-dominated routes."""

    def test_pareto_dominated_route_identified(self):
        """Route A is superior to Route B on all selected criteria. Route B must be flagged as dominated."""
        # Route A: 1000m, EAQI 20
        # Route B: 1500m, EAQI 40 (worse on both distance and air quality)
        route_a = make_test_route("r_a", "Superior Route A", distance_m=1000.0, eaqi=20.0)
        route_b = make_test_route("r_b", "Inferior Route B", distance_m=1500.0, eaqi=40.0)

        res = rank_routes([route_a, route_b], PreferenceSelection(walking_distance=True, air_quality=True))

        r_a_ranked = next(r for r in res.ranked_routes if r.id == "r_a")
        r_b_ranked = next(r for r in res.ranked_routes if r.id == "r_b")

        assert r_a_ranked.rank == 1
        assert r_a_ranked.is_pareto_dominated is False
        assert r_a_ranked.is_recommended is True

        assert r_b_ranked.rank == 2
        assert r_b_ranked.is_pareto_dominated is True
        assert "r_a" in r_b_ranked.dominated_by
        assert "Pareto-dominated alternative" in r_b_ranked.reasons[0]

    def test_conflicting_criteria_are_non_dominated(self):
        """When Route A is shorter but dirtier, and Route B is longer but cleaner, both are non-dominated."""
        # Route A: 1000m (best dist), EAQI 50 (worst AQ)
        # Route B: 1500m (worst dist), EAQI 20 (best AQ)
        route_a = make_test_route("r_a", "Fast Dirty Route", distance_m=1000.0, eaqi=50.0)
        route_b = make_test_route("r_b", "Slow Clean Route", distance_m=1500.0, eaqi=20.0)

        res = rank_routes([route_a, route_b], PreferenceSelection(walking_distance=True, air_quality=True))

        for r in res.ranked_routes:
            assert r.is_pareto_dominated is False, f"Route {r.id} should be non-dominated"
            assert "Pareto-optimal alternative" in r.reasons[0]


class TestTiesAndStability:
    """Verifies that ties are resolved deterministically and produce reproducible results."""

    def test_identical_metrics_stable_tie_break(self):
        """Two routes with identical metrics must break ties stably via route ID."""
        r1 = make_test_route("route_0", "Route One", distance_m=1000.0, eaqi=25.0)
        r2 = make_test_route("route_1", "Route Two", distance_m=1000.0, eaqi=25.0)

        # Forward order
        res1 = rank_routes([r1, r2], PreferenceSelection(air_quality=True))
        # Reverse order
        res2 = rank_routes([r2, r1], PreferenceSelection(air_quality=True))

        # Output ordering must be identical regardless of input list permutation
        assert [r.id for r in res1.ranked_routes] == ["route_0", "route_1"]
        assert [r.id for r in res2.ranked_routes] == ["route_0", "route_1"]

    def test_distance_as_tie_breaker(self):
        """Equal composite scores must use walking distance as the primary tie-breaker."""
        # When evaluating only air quality, if both routes have identical air quality,
        # the shorter route must win the tie-break.
        long_route = make_test_route("r_long", "Long Route", distance_m=2000.0, eaqi=20.0)
        short_route = make_test_route("r_short", "Short Route", distance_m=1200.0, eaqi=20.0)

        res = rank_routes([long_route, short_route], PreferenceSelection(air_quality=True))

        assert res.ranked_routes[0].id == "r_short"
        assert res.ranked_routes[1].id == "r_long"


class TestMissingDataHandling:
    """Verifies that missing variables are never treated as zeros and handled transparently."""

    def test_missing_data_not_treated_as_zero(self):
        """A missing greenery reading must NOT be treated as 0% greenery."""
        # Route A: has 20% greenery
        # Route B: greenery is missing (None)
        r_a = make_test_route("r_a", "Route A", greenery_pct=20.0)
        r_b = make_test_route("r_b", "Route B", omit_greenery=True)

        res = rank_routes([r_a, r_b], PreferenceSelection(greenery=True, walking_distance=True))

        # Greenery should be excluded from active evaluation because Route B lacks it
        assert "greenery" in res.missing_selected_factors
        assert "greenery" not in res.active_evaluation_factors
        assert len(res.warnings) > 0
        assert "Greenery & Parks" in res.warnings[0]

    def test_all_selected_factors_missing_withholds_recommendation(self):
        """If every selected factor lacks data, system withholds confident recommendation."""
        r1 = make_test_route("r1", "Route 1", omit_traffic=True)
        r2 = make_test_route("r2", "Route 2", omit_traffic=True)

        res = rank_routes([r1, r2], PreferenceSelection(traffic_exposure=True))

        assert res.confidence == "low"
        assert res.withheld_recommendation is True
        assert "Recommendation withheld" in res.warnings[-1]
        # Falls back to walking distance baseline
        assert "walking_distance" in res.active_evaluation_factors


class TestSingleAndMultipleRoutes:
    """Verifies edge cases of route count."""

    def test_single_route_handled(self):
        """A single route should return rank 1 and not crash."""
        r = make_test_route("r_solo", "Solo Route")
        res = rank_routes([r], PreferenceSelection(air_quality=True))

        assert len(res.ranked_routes) == 1
        assert res.ranked_routes[0].rank == 1
        assert res.ranked_routes[0].is_recommended is True
        assert res.ranked_routes[0].is_pareto_dominated is False

    def test_multiple_routes_comprehensive_matrix(self):
        """Evaluating 3 routes creates full comparison matrix."""
        r1 = make_test_route("r1", "Route 1", distance_m=1000.0, eaqi=20.0, temp_c=22.0)
        r2 = make_test_route("r2", "Route 2", distance_m=1200.0, eaqi=15.0, temp_c=24.0)
        r3 = make_test_route("r3", "Route 3", distance_m=1500.0, eaqi=35.0, temp_c=20.0)

        res = rank_routes([r1, r2, r3], PreferenceSelection(air_quality=True, walking_distance=True))

        assert len(res.ranked_routes) == 3
        assert len(res.comparison_matrix) == 3
        for row in res.comparison_matrix:
            assert row.route_id in ["r1", "r2", "r3"]
            assert row.walking_distance_m > 0


class TestNoPreferenceDefaultBaseline:
    """Verifies the documented default rule when no preferences are activated."""

    def test_no_preference_option_evaluates_all_available_metrics(self):
        """Explicit no_preference=True triggers the transparent default evaluation."""
        r1 = make_test_route("r1", "Route 1", distance_m=1000.0, eaqi=20.0, temp_c=21.0)
        r2 = make_test_route("r2", "Route 2", distance_m=1300.0, eaqi=15.0, temp_c=23.0)

        res = rank_routes([r1, r2], PreferenceSelection(no_preference=True))

        assert res.is_default_evaluation is True
        assert "walking_distance" in res.active_evaluation_factors
        assert "air_quality" in res.active_evaluation_factors
        assert "temperature" in res.active_evaluation_factors


class TestNoFixedWeightsProof:
    """Mathematically proves that the algorithm does not use secret or fixed user weights."""

    def test_proof_of_equal_priority_weights(self):
        """For two active factors, each factor must mathematically contribute exactly 0.50 (1/2) weight."""
        # Route 1: perfect on air quality (score=1.0), worst on temperature (score=0.0)
        # Route 2: worst on air quality (score=0.0), perfect on temperature (score=1.0)
        r1 = make_test_route("r1", "Route 1", distance_m=1000.0, eaqi=10.0, temp_c=35.0)
        r2 = make_test_route("r2", "Route 2", distance_m=1000.0, eaqi=50.0, temp_c=18.0)

        res = rank_routes([r1, r2], PreferenceSelection(air_quality=True, temperature=True))

        # Expected score: (1.0 + 0.0) / 2 = 0.5000 exactly for both routes
        assert res.ranked_routes[0].multi_criteria_score == 0.5000
        assert res.ranked_routes[1].multi_criteria_score == 0.5000

        # Now test 3 active factors: (1/3) = 0.3333 weight each
        r_a = make_test_route("ra", "Route A", distance_m=1000.0, eaqi=10.0, temp_c=30.0, greenery_pct=80.0)
        r_b = make_test_route("rb", "Route B", distance_m=1200.0, eaqi=30.0, temp_c=20.0, greenery_pct=20.0)

        res3 = rank_routes([r_a, r_b], PreferenceSelection(air_quality=True, temperature=True, greenery=True))
        # ra has: AQ=1.0, Temp=0.0, Greenery=1.0 -> Sum=2.0 -> Score = 2/3 = 0.6667
        # rb has: AQ=0.0, Temp=1.0, Greenery=0.0 -> Sum=1.0 -> Score = 1/3 = 0.3333
        assert res3.ranked_routes[0].id == "ra"
        assert res3.ranked_routes[0].multi_criteria_score == 0.6667
        assert res3.ranked_routes[1].id == "rb"
        assert res3.ranked_routes[1].multi_criteria_score == 0.3333


class TestRankingEndpoint:
    """Verifies the HTTP POST /api/rank API endpoint."""

    def test_successful_rank_endpoint(self):
        """Posting valid routes and preferences returns 200 with complete ranking response."""
        r1 = make_test_route("route_0", "Route 1", distance_m=1000.0, eaqi=20.0).model_dump()
        r2 = make_test_route("route_1", "Route 2", distance_m=1200.0, eaqi=15.0).model_dump()

        payload = {
            "routes": [r1, r2],
            "preferences": {
                "air_quality": True,
                "walking_distance": True,
                "temperature": False,
                "greenery": False,
                "traffic_exposure": False,
                "no_preference": False,
            },
        }

        res = client.post("/api/rank", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "ranked_routes" in data
        assert len(data["ranked_routes"]) == 2
        assert data["ranked_routes"][0]["rank"] == 1
        assert "comparison_matrix" in data
        assert "algorithmic_explanation" in data

    def test_empty_routes_rejected(self):
        """Posting an empty list of routes must return 422 Unprocessable Entity."""
        res = client.post("/api/rank", json={"routes": [], "preferences": {}})
        assert res.status_code == 422
