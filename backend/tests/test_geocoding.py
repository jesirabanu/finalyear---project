"""Tests for /api/geocode endpoint and geocoding_service.
Covers:
- Query length validation (min 3 chars)
- Successful geocoding with parsed results
- Empty results handling
- Rate limits and timeout handling
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import httpx
from app.main import app

client = TestClient(app)

MOCK_NOMINATIM_SUCCESS = [
    {
        "place_id": 1058204,
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0",
        "osm_type": "way",
        "osm_id": 26829700,
        "lat": "51.51381",
        "lon": "-0.09836",
        "display_name": "St. Paul's Cathedral, St Paul's Churchyard, City of London, Greater London, England, EC4M 8AD, United Kingdom",
        "type": "place_of_worship",
        "importance": 0.824,
    },
    {
        "place_id": 892341,
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0",
        "osm_type": "node",
        "osm_id": 352345,
        "lat": "51.5142",
        "lon": "-0.0975",
        "display_name": "St Paul's Station, Cheapside, City of London, Greater London, England, EC2V 6AU, United Kingdom",
        "type": "station",
        "importance": 0.65,
    },
]


class TestGeocodeEndpoint:
    """Tests for GET /api/geocode."""

    def test_short_query_returns_422(self):
        """Query with less than 3 characters should fail query validation."""
        res = client.get("/api/geocode?q=ab")
        assert res.status_code == 422

    def test_successful_geocoding(self):
        """Valid query returns parsed location candidates."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_SUCCESS

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = client.get("/api/geocode?q=St%20Pauls")

            assert res.status_code == 200
            data = res.json()
            assert len(data) == 2
            assert data[0]["place_id"] == 1058204
            assert data[0]["lat"] == pytest.approx(51.51381, rel=1e-4)
            assert data[0]["lon"] == pytest.approx(-0.09836, rel=1e-4)
            assert "St. Paul's Cathedral" in data[0]["display_name"]

    def test_empty_results_returns_empty_list(self):
        """Query with no matches returns empty list without error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = client.get("/api/geocode?q=NonexistentPlace123456")

            assert res.status_code == 200
            data = res.json()
            assert data == []

    def test_geocoding_rate_limit_429(self):
        """Provider 429 maps to 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = client.get("/api/geocode?q=Oxford%20Street")

            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"].lower()

    def test_geocoding_timeout_504(self):
        """Provider timeout maps to 504."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")
            res = client.get("/api/geocode?q=Kensington%20Palace")

            assert res.status_code == 504
            assert "timed out" in res.json()["detail"].lower()
