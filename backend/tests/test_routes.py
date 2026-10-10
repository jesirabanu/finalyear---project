"""Tests for /api/routes endpoint and routing_service.
Covers:
- Request validation (out of bounds, identical coordinates, missing fields)
- Missing ORS_API_KEY handling
- Provider response parsing (multiple routes, single route, genuine coordinates)
- Provider failure cases (404 no route, 401 unauthorized, 429 rate limit, 504 timeout)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import httpx
from app.main import app
from app.core.config import settings

client = TestClient(app)

MOCK_ORS_FEATURE_COLLECTION_MULTIPLE = {
    "type": "FeatureCollection",
    "bbox": [-0.0984, 51.5081, -0.0759, 51.5138],
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-0.0984, 51.5138],
                    [-0.0870, 51.5100],
                    [-0.0759, 51.5081],
                ],
            },
            "properties": {
                "summary": {
                    "distance": 1820.5,
                    "duration": 1310.0,
                },
                "segments": [{"distance": 1820.5, "duration": 1310.0}],
            },
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-0.0984, 51.5138],
                    [-0.0920, 51.5090],
                    [-0.0810, 51.5075],
                    [-0.0759, 51.5081],
                ],
            },
            "properties": {
                "summary": {
                    "distance": 2150.0,
                    "duration": 1548.0,
                },
                "segments": [{"distance": 2150.0, "duration": 1548.0}],
            },
        },
    ],
    "metadata": {"query": {"profile": "foot-walking"}},
}

MOCK_ORS_FEATURE_COLLECTION_SINGLE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-0.0984, 51.5138],
                    [-0.0759, 51.5081],
                ],
            },
            "properties": {
                "summary": {
                    "distance": 1900.0,
                    "duration": 1368.0,
                },
            },
        }
    ],
}


class TestRouteValidation:
    """Tests for request payload validation."""

    def test_missing_coordinates(self):
        """Omitting origin or destination should return 422 Unprocessable Entity."""
        res = client.post("/api/routes", json={"source": {"lat": 51.5, "lon": -0.1}})
        assert res.status_code == 422

    def test_out_of_bounds_latitude(self):
        """Latitude > 90.0 or < -90.0 must be rejected."""
        res = client.post(
            "/api/routes",
            json={
                "source": {"lat": 95.0, "lon": -0.1},
                "destination": {"lat": 51.5, "lon": -0.07},
            },
        )
        assert res.status_code == 422

    def test_out_of_bounds_longitude(self):
        """Longitude > 180.0 or < -180.0 must be rejected."""
        res = client.post(
            "/api/routes",
            json={
                "source": {"lat": 51.5, "lon": -195.0},
                "destination": {"lat": 51.5, "lon": -0.07},
            },
        )
        assert res.status_code == 422

    def test_identical_source_and_destination(self):
        """Identical origin and destination should fail validation."""
        res = client.post(
            "/api/routes",
            json={
                "source": {"lat": 51.5138, "lon": -0.0984},
                "destination": {"lat": 51.5138, "lon": -0.0984},
            },
        )
        assert res.status_code == 422
        assert "Source and destination must be distinct locations" in res.text


class TestApiKeyHandling:
    """Tests handling of missing or placeholder ORS API keys."""

    def test_missing_api_key_returns_503(self):
        """When ORS_API_KEY is not configured, API must return HTTP 503."""
        with patch.object(settings, "ORS_API_KEY", ""):
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 503
            assert "ORS_API_KEY" in res.json()["detail"]


class TestProviderParsingAndAlternatives:
    """Tests provider response parsing with mock responses."""

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_multiple_routes_parsed_correctly(self, mock_key):
        """Multiple provider routes must yield multiple distinct RouteModel items with genuine Leaflet coords."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_ORS_FEATURE_COLLECTION_MULTIPLE

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984, "label": "Start"},
                    "destination": {"lat": 51.5081, "lon": -0.0759, "label": "End"},
                    "alternatives": 2,
                },
            )

            assert res.status_code == 200
            data = res.json()
            assert data["total_routes"] == 2
            assert data["has_alternatives"] is True
            assert len(data["routes"]) == 2

            # Check Route 0 (Primary)
            r0 = data["routes"][0]
            assert r0["id"] == "route_0"
            assert r0["is_primary"] is True
            assert r0["distance_m"] == 1820.5
            assert r0["distance_km"] == 1.82
            assert r0["duration_s"] == 1310.0
            # Leaflet coordinates must be [lat, lon]
            assert r0["coordinates"][0] == [51.5138, -0.0984]

            # Check Route 1 (Alternative A)
            r1 = data["routes"][1]
            assert r1["id"] == "route_1"
            assert r1["is_primary"] is False
            assert r1["distance_m"] == 2150.0
            assert r1["coordinates"][0] == [51.5138, -0.0984]
            assert r0["color"] != r1["color"]

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_single_route_not_duplicated(self, mock_key):
        """When ORS returns only 1 route, the API must honestly report 1 route and NOT duplicate."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_ORS_FEATURE_COLLECTION_SINGLE

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                    "alternatives": 2,
                },
            )

            assert res.status_code == 200
            data = res.json()
            assert data["total_routes"] == 1
            assert data["has_alternatives"] is False
            assert len(data["routes"]) == 1
            assert "1 walking route found" in data["message"]


class TestProviderFailureCases:
    """Tests failure and error responses from provider."""

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_no_walking_route_found_404(self, mock_key):
        """When provider returns 404 or 400 not found, API responds with 404 and readable error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {
            "error": {"code": 2010, "message": "Could not find routable point within a radius of 350.0 meters."}
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 0.0, "lon": 0.0},
                    "destination": {"lat": 0.1, "lon": 0.1},
                },
            )
            assert res.status_code == 404
            assert "Could not find routable point" in res.json()["detail"]

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_unauthorized_key_401(self, mock_key):
        """Invalid API key returns 401."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": "Invalid API Key"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 401
            assert "authorization failed" in res.json()["detail"]

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_rate_limit_429(self, mock_key):
        """Rate limited provider returns 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"error": "Rate limit exceeded"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"]

    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    def test_timeout_504(self, mock_key):
        """Timeout connecting to provider returns 504."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            res = client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 504
            assert "timed out" in res.json()["detail"]
