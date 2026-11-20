"""Unit and integration tests for time-aware route evaluation, data freshness,
configurable cache expiry, and re-evaluation change tracking.
"""
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.schemas.routes import RouteModel, CoordinatePoint
from app.schemas.preferences import (
    PreferenceSelection,
    RouteRefreshRequest,
)
from app.services.environmental_service import (
    fetch_air_quality_batch,
    fetch_weather_batch,
    _build_cache_key,
    _env_cache,
)
from app.services.traffic_service import (
    is_time_non_current,
    compute_route_traffic_profile,
    LiveTrafficMetrics,
)
from app.algorithm.ranking_engine import (
    rank_routes,
    compute_reevaluation_summary,
)
from app.services.routing_service import refresh_route_environments

client = TestClient(app)


def _make_dummy_route(
    route_id: str,
    name: str,
    distance_m: float,
    air_quality: float = 30.0,
    temperature: float = 20.0,
    traffic: float = 25.0,
    greenery: float = 40.0,
) -> RouteModel:
    return RouteModel(
        id=route_id,
        name=name,
        distance_m=distance_m,
        distance_km=round(distance_m / 1000.0, 2),
        duration_s=round(distance_m / 1.3, 1),
        duration_min=round((distance_m / 1.3) / 60.0, 1),
        coordinates=[[51.51, -0.09], [51.52, -0.08]],
        available_environmental_metrics={
            "walking_distance": distance_m,
            "air_quality": air_quality,
            "temperature": temperature,
            "traffic_exposure": traffic,
            "greenery": greenery,
        },
        metric_units={
            "walking_distance": "m",
            "air_quality": "EAQI",
            "temperature": "°C",
            "traffic_exposure": "index (0-100)",
            "greenery": "%",
        },
        timestamps={
            "retrieval_timestamp": "2026-10-22T12:00:00Z",
            "observation_or_forecast_timestamp": "2026-10-22T12:00:00Z",
            "is_forecast": False,
            "is_stale": False,
        },
        source_metadata={"provider": "Test"},
        data_quality_status="complete",
        missing_factors=[],
    )


class TestDataFreshnessAndCache:
    """Tests for cache TTL expiry, force refresh, and retaining stale cache on failure."""

    @pytest.mark.asyncio
    async def test_cache_hit_within_ttl(self):
        """Query within TTL returns cached data without calling upstream network."""
        lat, lon = 51.501, -0.081
        ck = _build_cache_key("aq", lat, lon, None)
        _env_cache[ck] = (datetime.now(timezone.utc).timestamp(), {"current": {"pm2_5": 12.3}})

        with patch("httpx.AsyncClient.get") as mock_get:
            results = await fetch_air_quality_batch([(lat, lon)], time_str=None, force_refresh=False)
            mock_get.assert_not_called()
            assert len(results) == 1
            assert results[0]["current"]["pm2_5"] == 12.3

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self):
        """When force_refresh=True, queries provider even if cache entry exists."""
        lat, lon = 51.502, -0.082
        ck = _build_cache_key("aq", lat, lon, None)
        _env_cache[ck] = (datetime.now(timezone.utc).timestamp(), {"current": {"pm2_5": 5.0}})

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"current": {"pm2_5": 22.0}}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            results = await fetch_air_quality_batch([(lat, lon)], time_str=None, force_refresh=True)
            mock_get.assert_called_once()
            assert results[0]["current"]["pm2_5"] == 22.0

    @pytest.mark.asyncio
    async def test_provider_failure_retains_stale_cache_with_warning(self):
        """When upstream provider fails during refresh, retains previous cache with _is_stale=True."""
        lat, lon = 51.503, -0.083
        ck = _build_cache_key("aq", lat, lon, None)
        old_time = datetime.now(timezone.utc).timestamp() - 300  # 5 min ago
        _env_cache[ck] = (old_time, {"current": {"pm2_5": 14.5}})

        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timed out")):
            results = await fetch_air_quality_batch([(lat, lon)], time_str=None, force_refresh=True)
            assert len(results) == 1
            assert results[0]["current"]["pm2_5"] == 14.5
            assert results[0].get("_is_stale") is True
            assert "unreachable" in results[0].get("_stale_warning", "")


class TestDepartureTimeHandling:
    """Tests for departure time selection, future forecast detection, and traffic applicability."""

    def test_current_departure_time_detected(self):
        """Current or near-current departure time is identified as current."""
        now_iso = datetime.now(timezone.utc).isoformat()
        is_non_current, msg = is_time_non_current(now_iso)
        assert is_non_current is False
        assert msg is None

    def test_future_departure_time_disables_live_traffic(self):
        """Future departure time (>30 min) marks live vehicular traffic as unavailable."""
        future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        is_non_current, msg = is_time_non_current(future_time)
        assert is_non_current is True
        assert "future" in msg

        # Traffic profile evaluation with live metrics and future departure time
        live_m = LiveTrafficMetrics(
            congestion_pct=45.0,
            current_speed_kmh=15.0,
            free_flow_speed_kmh=30.0,
            status="available",
        )
        traffic_data = compute_route_traffic_profile(
            route_coordinates=[[51.5, -0.1], [51.51, -0.1]],
            osm_road_elements=[],
            live_traffic=live_m,
            departure_time=future_time,
        )

        assert traffic_data.status == "unavailable"
        assert traffic_data.score is None
        assert "Future traffic flow is unavailable" in traffic_data.limitation_note


class TestReevaluationChangeTracking:
    """Tests for comparing old and new environmental routes and detecting recommendation shifts."""

    def test_reevaluation_detects_recommendation_change(self):
        """When environmental data changes and a different route becomes Rank 1, change is explained."""
        r1_old = _make_dummy_route("r1", "Route A", distance_m=1000.0, air_quality=20.0, temperature=20.0)
        r2_old = _make_dummy_route("r2", "Route B", distance_m=1050.0, air_quality=50.0, temperature=25.0)

        # In refreshed conditions, Route B becomes much cleaner than Route A
        r1_new = _make_dummy_route("r1", "Route A", distance_m=1000.0, air_quality=65.0, temperature=28.0)
        r2_new = _make_dummy_route("r2", "Route B", distance_m=1050.0, air_quality=15.0, temperature=18.0)

        prefs = PreferenceSelection(air_quality=True, temperature=True, walking_distance=False)
        new_ranking = rank_routes([r1_new, r2_new], prefs)

        summary = compute_reevaluation_summary(
            old_routes=[r1_old, r2_old],
            new_ranking=new_ranking,
            old_rank_1_id="r1",
        )

        assert summary.recommendation_changed is True
        assert summary.new_recommended_route_id == "r2"
        assert "Recommendation changed" in summary.recommendation_change_note
        assert len(summary.metric_changes) >= 2
        assert "No live automatic in-walk navigation" in summary.disclaimer or "Pre-trip" in summary.disclaimer

    def test_reevaluation_retains_recommendation_when_unchanged(self):
        """When ranking remains stable after data refresh, states unchanged recommendation."""
        r1 = _make_dummy_route("r1", "Route A", distance_m=1000.0, air_quality=20.0)
        r2 = _make_dummy_route("r2", "Route B", distance_m=1100.0, air_quality=40.0)

        prefs = PreferenceSelection(air_quality=True)
        new_ranking = rank_routes([r1, r2], prefs)

        summary = compute_reevaluation_summary(
            old_routes=[r1, r2],
            new_ranking=new_ranking,
            old_rank_1_id="r1",
        )

        assert summary.recommendation_changed is False
        assert "unchanged" in summary.recommendation_change_note.lower()


class TestRefreshEndpoint:
    """Integration test for POST /api/routes/refresh endpoint."""

    @patch("app.services.routing_service.enrich_routes_with_environmental_data")
    @patch("app.services.routing_service.enrich_routes_with_traffic_data")
    def test_routes_refresh_endpoint(self, mock_traffic, mock_env):
        """Calling /api/routes/refresh re-evaluates routes and returns ReevaluationSummary."""
        r1 = _make_dummy_route("r1", "Route A", distance_m=1000.0)
        payload = {
            "routes": [r1.model_dump()],
            "preferences": {"air_quality": True, "walking_distance": True},
            "departure_time": "2026-10-22T16:00:00Z",
            "force_refresh": True,
        }

        res = client.post("/api/routes/refresh", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "routes" in data
        assert "ranking" in data
        assert "reevaluation" in data
        assert "Pre-trip" in data["reevaluation"]["disclaimer"]
