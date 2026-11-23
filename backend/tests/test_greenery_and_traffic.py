"""Tests for Greenery and Traffic Services and Ranking Integration.
Covers:
- OpenStreetMap Overpass greenery querying (parks, gardens, tree cover)
- Greenery corridor buffer calculation and fraction of route length
- Empty OSM results, malformed geometry, and Overpass timeouts (HTTP 504 / 429)
- Disclosure that greenery buffer proximity is not equivalent to GVI or measured shade
- Live traffic metrics vs. static road infrastructure proxy separation
- Static road classification exposure calculation based on major road proximity
- Verification that road classification is never labeled as live traffic
- Integration into multi-criteria ranking engine (greenery higher-is-better, traffic lower-is-better)
"""
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from app.core.config import settings
from app.algorithm.ranking_engine import rank_routes
from app.schemas.environment import (
    AirQualityData,
    EnvironmentalMetadata,
    GreeneryData,
    LiveTrafficMetrics,
    PollutantReading,
    RouteEnvironmentalSummary,
    StaticRoadProxyMetrics,
    TrafficExposureData,
    WeatherData,
)
from app.schemas.preferences import PreferenceSelection
from app.schemas.routes import RouteModel
from app.services.greenery_service import (
    compute_corridor_bbox,
    compute_route_greenery_profile,
    fetch_overpass_greenery_features,
    haversine_distance_m,
)
from app.services.traffic_service import (
    compute_route_traffic_profile,
    enrich_routes_with_traffic_data,
    extract_representative_traffic_points,
    fetch_live_traffic_flow,
    fetch_overpass_major_roads,
    query_tomtom_traffic_point,
    _tomtom_traffic_cache,
)


def make_route_with_custom_env(
    route_id: str,
    distance_m: float = 1200.0,
    greenery: GreeneryData = None,
    traffic: TrafficExposureData = None,
) -> RouteModel:
    """Helper to construct RouteModel with explicit Greenery and Traffic objects."""
    aq = AirQualityData(
        european_aqi=PollutantReading(value=25.0, unit="EAQI", status="available")
    )
    wx = WeatherData(temperature_c=20.0, apparent_temperature_c=19.5)
    meta = EnvironmentalMetadata(retrieval_timestamp="2026-10-22T12:00:00Z")

    env = RouteEnvironmentalSummary(
        air_quality=aq,
        weather=wx,
        greenery=greenery,
        traffic_exposure=traffic,
        metadata=meta,
        samples_count=3,
        has_air_quality=True,
        has_weather=True,
        has_greenery=greenery is not None and greenery.score is not None,
        has_traffic=traffic is not None and traffic.score is not None,
    )

    avail_metrics = {
        "walking_distance": distance_m,
        "air_quality": 25.0,
        "temperature": 19.5,
        "greenery": greenery.score if greenery else None,
        "traffic_exposure": traffic.score if traffic else None,
    }

    return RouteModel(
        id=route_id,
        name=f"Route {route_id}",
        distance_m=distance_m,
        distance_km=round(distance_m / 1000.0, 2),
        duration_s=round(distance_m / 1.4, 1),
        duration_min=round(distance_m / 84.0, 1),
        coordinates=[
            [51.5138, -0.0984],
            [51.5110, -0.0870],
            [51.5081, -0.0759],
        ],
        environment=env,
        available_environmental_metrics=avail_metrics,
        metric_units={"greenery": "%", "traffic_exposure": "index (0-100)"},
        data_quality_status="complete",
    )


class TestGreeneryService:
    """Tests for Overpass greenery proximity and corridor coverage calculation."""

    def test_haversine_distance_accurate(self):
        """Calculates distance accurately between known points."""
        # Distance between St. Paul's (51.5138, -0.0984) and Tower of London (51.5081, -0.0759) ~ 1680m
        dist = haversine_distance_m(51.5138, -0.0984, 51.5081, -0.0759)
        assert 1500 < dist < 1900

    def test_compute_corridor_bbox_adds_reasonable_buffer(self):
        """Bounding box covers all coordinates plus safety buffer."""
        r = make_route_with_custom_env("r1")
        min_lat, min_lon, max_lat, max_lon = compute_corridor_bbox([r], buffer_deg=0.002)

        assert min_lat < 51.5081
        assert max_lat > 51.5138
        assert min_lon < -0.0984
        assert max_lon > -0.0759

    def test_greenery_proximity_calculation_with_adjacent_parks(self):
        """Route with mapped park in buffer calculates positive fraction, score, and park count."""
        # Route points near 51.5110, -0.0870
        coords = [
            [51.5138, -0.0984],
            [51.5110, -0.0870],
            [51.5081, -0.0759],
        ]
        # Mock OSM park element centered right next to middle waypoint
        mock_osm_elements = [
            {
                "type": "way",
                "id": 1001,
                "center": {"lat": 51.5111, "lon": -0.0871},  # ~12m away
                "tags": {"leisure": "park", "name": "Postman's Park"},
            }
        ]

        profile = compute_route_greenery_profile(coords, mock_osm_elements, buffer_distance_m=50.0)

        assert profile.status == "available"
        assert profile.greenery_fraction > 0.0
        assert profile.score > 0.0
        assert profile.parks_count == 1
        assert profile.buffer_distance_m == 50.0
        assert "Green View Index" in profile.limitation_note

    def test_empty_osm_coverage_handled_honestly(self):
        """Empty OSM response returns score 0.0 with empty_osm_coverage status, without crashing."""
        coords = [[51.51, -0.09], [51.52, -0.08]]
        profile = compute_route_greenery_profile(coords, [])

        assert profile.status == "empty_osm_coverage"
        assert profile.score == 0.0
        assert profile.greenery_fraction == 0.0
        assert profile.parks_count == 0

    def test_overpass_timeout_or_error_preserves_null(self):
        """When Overpass fails or returns None, score must remain None (never zero-filled)."""
        coords = [[51.51, -0.09], [51.52, -0.08]]
        profile = compute_route_greenery_profile(coords, None)

        assert profile.status == "missing_from_provider"
        assert profile.score is None
        assert profile.greenery_fraction is None


class TestTrafficService:
    """Tests for live traffic integration, static infrastructure proxy, and separation."""

    def test_separation_of_live_and_static_in_data_model(self):
        """Data model must maintain live traffic and static proxy in distinct fields."""
        live = LiveTrafficMetrics(
            congestion_pct=65.0,
            current_speed_kmh=18.0,
            free_flow_speed_kmh=50.0,
            status="available",
        )
        static = StaticRoadProxyMetrics(
            major_road_nearby_pct=40.0,
            dominant_road_class="primary",
            major_roads_count=2,
            status="available",
        )

        data = TrafficExposureData(
            score=65.0,
            metric_type="live_traffic_congestion",
            is_live_measurement=True,
            live_traffic=live,
            static_proxy=static,
        )

        assert data.is_live_measurement is True
        assert data.live_traffic.congestion_pct == 65.0
        assert data.static_proxy.dominant_road_class == "primary"

    def test_static_proxy_mode_when_no_live_traffic_key(self):
        """Without a live traffic API key, engine computes static road proximity proxy and sets is_live_measurement=False."""
        coords = [
            [51.5138, -0.0984],
            [51.5110, -0.0870],
            [51.5081, -0.0759],
        ]
        mock_osm_roads = [
            {
                "type": "way",
                "id": 2001,
                "center": {"lat": 51.5111, "lon": -0.0871},  # ~12m from route
                "tags": {"highway": "primary", "name": "Bishopsgate Arterial"},
            }
        ]

        profile = compute_route_traffic_profile(coords, mock_osm_roads, live_traffic=None)

        assert profile.metric_type == "static_road_hierarchy_proxy"
        assert profile.is_live_measurement is False
        assert profile.status == "static_proxy_estimated"
        assert profile.score > 20.0  # Penalized due to proximity to major primary road
        assert profile.road_class == "primary"
        assert "Does NOT represent live vehicular traffic" in profile.limitation_note

    def test_quiet_pedestrian_pathway_achieves_low_exposure_score(self):
        """Route with no adjacent major roads receives low baseline exposure score."""
        coords = [[51.51, -0.09], [51.52, -0.08]]
        profile = compute_route_traffic_profile(coords, [], live_traffic=None)

        assert profile.metric_type == "static_road_hierarchy_proxy"
        assert profile.score == 15.0  # Low exposure baseline for quiet walkways
        assert profile.road_class == "pedestrian_or_minor"

    def test_traffic_provider_failure_preserves_none(self):
        """When traffic provider and OSM both fail, score is None without inventing numbers."""
        coords = [[51.51, -0.09], [51.52, -0.08]]
        profile = compute_route_traffic_profile(coords, None, live_traffic=None)

        assert profile.score is None
        assert profile.status == "unavailable"


class TestRankingIntegrationWithGreeneryAndTraffic:
    """Verifies that selecting greenery or traffic alters rankings in the expected directions."""

    def test_greenery_selection_prefers_greener_corridor(self):
        """Higher greenery percentage must achieve higher score and Rank 1 when greenery is selected."""
        green_profile_high = GreeneryData(
            score=75.0,
            unit="%",
            status="available",
            greenery_fraction=0.75,
            parks_count=2,
        )
        green_profile_low = GreeneryData(
            score=15.0,
            unit="%",
            status="available",
            greenery_fraction=0.15,
            parks_count=0,
        )

        r_green = make_route_with_custom_env("r_green", distance_m=1200.0, greenery=green_profile_high)
        r_urban = make_route_with_custom_env("r_urban", distance_m=1000.0, greenery=green_profile_low)

        # Select only greenery
        res = rank_routes([r_green, r_urban], PreferenceSelection(greenery=True))

        assert res.ranked_routes[0].id == "r_green"
        assert res.ranked_routes[0].factor_details["greenery"].normalized_score == 1.0
        assert res.ranked_routes[1].factor_details["greenery"].normalized_score == 0.0

    def test_traffic_selection_prefers_quieter_corridor(self):
        """Lower traffic exposure score must achieve higher score and Rank 1 when traffic is selected."""
        quiet_traffic = TrafficExposureData(
            score=20.0,
            unit="index (0-100)",
            status="static_proxy_estimated",
            metric_type="static_road_hierarchy_proxy",
            is_live_measurement=False,
        )
        busy_traffic = TrafficExposureData(
            score=85.0,
            unit="index (0-100)",
            status="static_proxy_estimated",
            metric_type="static_road_hierarchy_proxy",
            is_live_measurement=False,
        )

        r_quiet = make_route_with_custom_env("r_quiet", distance_m=1200.0, traffic=quiet_traffic)
        r_busy = make_route_with_custom_env("r_busy", distance_m=1000.0, traffic=busy_traffic)

        # Select only traffic exposure
        res = rank_routes([r_quiet, r_busy], PreferenceSelection(traffic_exposure=True))

        assert res.ranked_routes[0].id == "r_quiet"
        assert res.ranked_routes[0].factor_details["traffic_exposure"].normalized_score == 1.0
        assert res.ranked_routes[1].factor_details["traffic_exposure"].normalized_score == 0.0

    def test_missing_greenery_data_transparently_excluded(self):
        """If greenery has no data, ranking transparently excludes it and ranks by other preferences."""
        missing_greenery = GreeneryData(
            score=None,
            unit="%",
            status="missing_from_provider",
        )
        r1 = make_route_with_custom_env("r1", distance_m=1000.0, greenery=missing_greenery)
        r2 = make_route_with_custom_env("r2", distance_m=1500.0, greenery=missing_greenery)

        res = rank_routes([r1, r2], PreferenceSelection(greenery=True, walking_distance=True))

        assert "greenery" in res.missing_selected_factors
        assert "walking_distance" in res.active_evaluation_factors
        assert res.ranked_routes[0].id == "r1"


def make_candidate_route(
    route_id: str,
    coordinates: List[List[float]],
    distance_m: float = 1000.0,
) -> RouteModel:
    """Helper to construct basic candidate RouteModel for enrichment tests."""
    aq = AirQualityData(
        european_aqi=PollutantReading(value=25.0, unit="EAQI", status="available")
    )
    wx = WeatherData(temperature_c=20.0, apparent_temperature_c=19.5)
    meta = EnvironmentalMetadata(retrieval_timestamp="2026-10-22T12:00:00Z")
    env = RouteEnvironmentalSummary(
        air_quality=aq,
        weather=wx,
        metadata=meta,
        samples_count=len(coordinates),
        has_air_quality=True,
        has_weather=True,
        has_greenery=False,
        has_traffic=False,
    )
    return RouteModel(
        id=route_id,
        name=f"Route {route_id}",
        distance_m=distance_m,
        distance_km=round(distance_m / 1000.0, 2),
        duration_s=round(distance_m / 1.4, 1),
        duration_min=round(distance_m / 84.0, 1),
        coordinates=coordinates,
        environment=env,
        available_environmental_metrics={"walking_distance": distance_m},
        metric_units={"walking_distance": "m"},
        data_quality_status="partial_data",
    )


class TestPerRouteTrafficIsolation:
    """Verifies that each candidate route receives traffic metrics derived from its own geometry."""

    @pytest.mark.asyncio
    async def test_candidate_routes_receive_independent_traffic_metrics(self):
        """Candidate routes with different coordinates receive independent traffic scores."""
        coords_0 = [[51.5138, -0.0984], [51.5110, -0.0870], [51.5081, -0.0759]]
        coords_1 = [[51.5138, -0.0984], [51.5250, -0.0850], [51.5081, -0.0759]]

        r0 = make_candidate_route("r0", coords_0, distance_m=1200.0)
        r1 = make_candidate_route("r1", coords_1, distance_m=1400.0)

        async def mock_get(url, *args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "51.511" in str(url):
                mock_resp.json.return_value = {
                    "flowSegmentData": {"currentSpeed": 15, "freeFlowSpeed": 50}
                }
            elif "51.525" in str(url):
                mock_resp.json.return_value = {
                    "flowSegmentData": {"currentSpeed": 45, "freeFlowSpeed": 50}
                }
            else:
                mock_resp.json.return_value = {
                    "flowSegmentData": {"currentSpeed": 30, "freeFlowSpeed": 50}
                }
            return mock_resp

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_valid_key"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            _tomtom_traffic_cache.clear()
            await enrich_routes_with_traffic_data([r0, r1])

            assert r0.environment.traffic_exposure.score == 70.0
            assert r0.environment.traffic_exposure.is_live_measurement is True
            assert r1.environment.traffic_exposure.score == 10.0
            assert r1.environment.traffic_exposure.is_live_measurement is True
            assert r0.environment.traffic_exposure.score != r1.environment.traffic_exposure.score

    @pytest.mark.asyncio
    async def test_route_0_metrics_never_reused_for_other_routes(self):
        """Alternative routes must never inherit Route 0's traffic metrics."""
        coords_0 = [[51.5138, -0.0984], [51.5100, -0.0800]]
        coords_1 = [[51.5138, -0.0984], [51.5300, -0.0800]]
        r0 = make_candidate_route("r0", coords_0)
        r1 = make_candidate_route("r1", coords_1)

        metric_0 = LiveTrafficMetrics(congestion_pct=85.0, current_speed_kmh=10.0, free_flow_speed_kmh=60.0, status="available")
        metric_1 = LiveTrafficMetrics(congestion_pct=15.0, current_speed_kmh=51.0, free_flow_speed_kmh=60.0, status="available")

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("app.services.traffic_service.fetch_live_traffic_flow", new_callable=AsyncMock, side_effect=[metric_0, metric_1]), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            await enrich_routes_with_traffic_data([r0, r1])

            assert r0.environment.traffic_exposure.live_traffic.congestion_pct == 85.0
            assert r1.environment.traffic_exposure.live_traffic.congestion_pct == 15.0
            assert r0.environment.traffic_exposure.score != r1.environment.traffic_exposure.score


class TestTrafficFallback:
    """Verifies fallback behaviour when TomTom live traffic is missing, fails, or is unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_credentials_missing(self):
        """When TOMTOM_TRAFFIC_API_KEY is missing, routes independently calculate static road hierarchy proxy."""
        coords_a = [[51.5138, -0.0984], [51.5110, -0.0870], [51.5081, -0.0759]]
        coords_b = [[51.5138, -0.0984], [51.5250, -0.0850], [51.5081, -0.0759]]
        r_a = make_candidate_route("r_a", coords_a)
        r_b = make_candidate_route("r_b", coords_b)

        mock_osm_roads = [
            {
                "type": "way",
                "id": 101,
                "center": {"lat": 51.5111, "lon": -0.0871},
                "tags": {"highway": "primary", "name": "Main Arterial"},
            }
        ]

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", ""), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=mock_osm_roads):
            await enrich_routes_with_traffic_data([r_a, r_b])

            assert r_a.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r_a.environment.traffic_exposure.is_live_measurement is False
            assert r_b.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r_b.environment.traffic_exposure.is_live_measurement is False
            assert r_a.environment.traffic_exposure.score > r_b.environment.traffic_exposure.score

    @pytest.mark.asyncio
    async def test_fallback_when_tomtom_returns_empty_data(self):
        """Empty TomTom flow data falls back to static proxy."""
        r = make_candidate_route("r", [[51.51, -0.09], [51.52, -0.09]])
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"flowSegmentData": {}}

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            _tomtom_traffic_cache.clear()
            await enrich_routes_with_traffic_data([r])

            assert r.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r.environment.traffic_exposure.is_live_measurement is False

    @pytest.mark.asyncio
    async def test_fallback_when_tomtom_times_out(self):
        """Timeout connecting to TomTom falls back to static proxy without crashing."""
        r = make_candidate_route("r", [[51.51, -0.09], [51.52, -0.09]])

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Timeout")), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            _tomtom_traffic_cache.clear()
            await enrich_routes_with_traffic_data([r])

            assert r.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r.environment.traffic_exposure.is_live_measurement is False

    @pytest.mark.asyncio
    async def test_fallback_when_tomtom_http_error(self):
        """TomTom HTTP errors (e.g. 500) fall back to static proxy."""
        r = make_candidate_route("r", [[51.51, -0.09], [51.52, -0.09]])
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            _tomtom_traffic_cache.clear()
            await enrich_routes_with_traffic_data([r])

            assert r.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r.environment.traffic_exposure.is_live_measurement is False

    @pytest.mark.asyncio
    async def test_one_route_fails_while_other_succeeds(self):
        """When one route's live query fails, it falls back to static proxy while the other retains live traffic."""
        r0 = make_candidate_route("r0", [[51.51, -0.09], [51.52, -0.09]])
        r1 = make_candidate_route("r1", [[51.53, -0.08], [51.54, -0.08]])

        metric_0 = LiveTrafficMetrics(congestion_pct=55.0, current_speed_kmh=20.0, free_flow_speed_kmh=45.0, status="available")

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("app.services.traffic_service.fetch_live_traffic_flow", new_callable=AsyncMock, side_effect=[metric_0, Exception("Network error")]), \
             patch("app.services.traffic_service.fetch_overpass_major_roads", new_callable=AsyncMock, return_value=[]):
            await enrich_routes_with_traffic_data([r0, r1])

            assert r0.environment.traffic_exposure.is_live_measurement is True
            assert r0.environment.traffic_exposure.score == 55.0

            assert r1.environment.traffic_exposure.is_live_measurement is False
            assert r1.environment.traffic_exposure.metric_type == "static_road_hierarchy_proxy"
            assert r1.environment.traffic_exposure.score == 15.0


class TestTrafficApiEfficiency:
    """Verifies caching and request budget constraints."""

    @pytest.mark.asyncio
    async def test_duplicate_sampling_coordinates_reuse_cached_results(self):
        """Repeated queries for the same coordinates serve from cache without making external HTTP requests."""
        _tomtom_traffic_cache.clear()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "flowSegmentData": {"currentSpeed": 35, "freeFlowSpeed": 50}
        }

        with patch.object(settings, "TOMTOM_TRAFFIC_API_KEY", "test_key"), \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp) as mock_get:
            res1 = await query_tomtom_traffic_point(51.5138, -0.0984)
            assert mock_get.call_count == 1
            assert res1["congestion_pct"] == 30.0

            res2 = await query_tomtom_traffic_point(51.5138, -0.0984)
            assert mock_get.call_count == 1
            assert res2["congestion_pct"] == 30.0

    def test_sampling_stays_within_budget(self):
        """Representative points extractor returns at most 2 points even for long routes."""
        long_coords = [[51.5 + i * 0.001, -0.1 + i * 0.001] for i in range(100)]
        pts = extract_representative_traffic_points(long_coords, max_points=2)
        assert len(pts) <= 2


class TestTrafficRankingVarianceAndIntegration:
    """Verifies that route-specific traffic measurements differentiate routes in the ranking engine."""

    def test_different_traffic_measurements_distinguishable_when_normalized(self):
        """Different traffic scores normalize to 1.0 (best) and 0.0 (worst) rather than both collapsing to 1.0."""
        t_low = TrafficExposureData(score=20.0, unit="index (0-100)", status="live_measured", is_live_measurement=True)
        t_high = TrafficExposureData(score=80.0, unit="index (0-100)", status="live_measured", is_live_measurement=True)

        r_low = make_route_with_custom_env("r_low", distance_m=1000.0, traffic=t_low)
        r_high = make_route_with_custom_env("r_high", distance_m=1000.0, traffic=t_high)

        res = rank_routes([r_low, r_high], PreferenceSelection(traffic_exposure=True))

        assert res.ranked_routes[0].id == "r_low"
        assert res.ranked_routes[0].factor_details["traffic_exposure"].normalized_score == 1.0
        assert res.ranked_routes[1].factor_details["traffic_exposure"].normalized_score == 0.0

    def test_identical_traffic_measurements_do_not_produce_artificial_differences(self):
        """Genuinely identical traffic measurements both receive 1.0 without artificial manipulation."""
        t_same1 = TrafficExposureData(score=35.0, unit="index (0-100)", status="live_measured", is_live_measurement=True)
        t_same2 = TrafficExposureData(score=35.0, unit="index (0-100)", status="live_measured", is_live_measurement=True)

        r1 = make_route_with_custom_env("r1", distance_m=1000.0, traffic=t_same1)
        r2 = make_route_with_custom_env("r2", distance_m=1000.0, traffic=t_same2)

        res = rank_routes([r1, r2], PreferenceSelection(traffic_exposure=True))

        assert res.ranked_routes[0].factor_details["traffic_exposure"].normalized_score == 1.0
        assert res.ranked_routes[1].factor_details["traffic_exposure"].normalized_score == 1.0

