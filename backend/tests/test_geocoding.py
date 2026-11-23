"""Tests for /api/geocode and /api/geocode/reverse endpoints and geocoding_service.
Covers:
- Forward geocoding query length validation (min 3 chars)
- Successful forward geocoding with parsed results
- Empty forward results handling
- Forward geocoding rate limits and timeout handling
- Reverse geocoding service unit tests (success, params, cache, rate limiter, bounds, errors)
- Reverse geocoding API endpoint tests (validation, success, errors)
"""
import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi import HTTPException
from app.main import app
from app.core.config import settings
from app.schemas.geocoding import GeocodeResult, ReverseGeocodeResult
from app.services.geocoding_service import (
    search_locations,
    reverse_geocode,
    _geocode_cache,
    _reverse_geocode_cache,
)

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

MOCK_NOMINATIM_REVERSE_SUCCESS = {
    "place_id": 1058204,
    "licence": "Data © OpenStreetMap contributors, ODbL 1.0",
    "osm_type": "way",
    "osm_id": 26829700,
    "lat": "51.51381",
    "lon": "-0.09836",
    "display_name": "St. Paul's Cathedral, St Paul's Churchyard, City of London, Greater London, England, EC4M 8AD, United Kingdom",
    "address": {
        "amenity": "St. Paul's Cathedral",
        "road": "St Paul's Churchyard",
        "city": "London",
        "postcode": "EC4M 8AD",
        "country": "United Kingdom",
        "country_code": "gb",
    },
    "boundingbox": ["51.5133", "51.5143", "-0.0990", "-0.0977"],
}


class TestGeocodeEndpoint:
    """Tests for GET /api/geocode."""

    @pytest.mark.asyncio
    async def test_short_query_returns_422(self, async_client: httpx.AsyncClient):
        """Query with less than 3 characters should fail query validation."""
        res = await async_client.get("/api/geocode?q=ab")
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_successful_geocoding(self, async_client: httpx.AsyncClient):
        """Valid query returns parsed location candidates."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_SUCCESS

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = await async_client.get("/api/geocode?q=St%20Pauls")

            assert res.status_code == 200
            data = res.json()
            assert len(data) == 2
            assert data[0]["place_id"] == 1058204
            assert data[0]["lat"] == pytest.approx(51.51381, rel=1e-4)
            assert data[0]["lon"] == pytest.approx(-0.09836, rel=1e-4)
            assert "St. Paul's Cathedral" in data[0]["display_name"]

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self, async_client: httpx.AsyncClient):
        """Query with no matches returns empty list without error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = await async_client.get("/api/geocode?q=NonexistentPlace123456")

            assert res.status_code == 200
            data = res.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_geocoding_rate_limit_429(self, async_client: httpx.AsyncClient):
        """Provider 429 maps to 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = await async_client.get("/api/geocode?q=Oxford%20Street")

            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_geocoding_timeout_504(self, async_client: httpx.AsyncClient):
        """Provider timeout maps to 504."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")
            res = await async_client.get("/api/geocode?q=Kensington%20Palace")

            assert res.status_code == 504
            assert "timed out" in res.json()["detail"].lower()


class TestReverseGeocodingService:
    """Unit tests for reverse_geocode service function."""

    @pytest.mark.asyncio
    async def test_successful_reverse_geocode(self):
        """Valid coordinates return structured ReverseGeocodeResult."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_REVERSE_SUCCESS

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            result = await reverse_geocode(51.51381, -0.09836)

            assert isinstance(result, ReverseGeocodeResult)
            assert result.place_id == 1058204
            assert "St. Paul's Cathedral" in result.display_name
            assert result.lat == pytest.approx(51.51381, rel=1e-4)
            assert result.lon == pytest.approx(-0.09836, rel=1e-4)
            assert result.address is not None
            assert result.address.get("city") == "London"

    @pytest.mark.asyncio
    async def test_nominatim_request_parameters(self):
        """Service passes lat, lon, format=jsonv2, and custom academic User-Agent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_REVERSE_SUCCESS

        test_lat, test_lon = 51.5007, -0.1246
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            await reverse_geocode(test_lat, test_lon)

            assert mock_get.called
            call_args, call_kwargs = mock_get.call_args
            assert call_args[0] == settings.NOMINATIM_REVERSE_API_URL
            params = call_kwargs.get("params", {})
            headers = call_kwargs.get("headers", {})
            assert params["lat"] == test_lat
            assert params["lon"] == test_lon
            assert params["format"] == "jsonv2"
            assert params["addressdetails"] == 1
            assert headers["User-Agent"] == settings.NOMINATIM_USER_AGENT

    @pytest.mark.asyncio
    async def test_cache_hit_behaviour(self):
        """Repeated reverse geocoding for identical/nearby coordinates returns cached result without network request."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_REVERSE_SUCCESS

        test_lat, test_lon = 51.5033, -0.1195
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            first_res = await reverse_geocode(test_lat, test_lon)
            assert mock_get.call_count == 1

            # Second call for identical coordinates
            second_res = await reverse_geocode(test_lat, test_lon)
            # HTTP get should not have been called a second time
            assert mock_get.call_count == 1
            assert second_res.display_name == first_res.display_name

    @pytest.mark.asyncio
    async def test_rate_limiter_behaviour(self):
        """Enforces minimum 1.0s interval between outbound Nominatim requests."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_REVERSE_SUCCESS

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("app.services.geocoding_service._last_request_timestamp", time.time()):
            mock_get.return_value = mock_resp
            await reverse_geocode(52.2053, 0.1218)
            assert mock_sleep.called
            assert mock_sleep.call_args[0][0] > 0.0

    @pytest.mark.asyncio
    async def test_invalid_latitude_and_longitude(self):
        """Out of bounds coordinates raise HTTPException 400."""
        with pytest.raises(HTTPException) as exc_lat_high:
            await reverse_geocode(95.0, 0.0)
        assert exc_lat_high.value.status_code == 400

        with pytest.raises(HTTPException) as exc_lat_low:
            await reverse_geocode(-95.0, 0.0)
        assert exc_lat_low.value.status_code == 400

        with pytest.raises(HTTPException) as exc_lon_high:
            await reverse_geocode(0.0, 185.0)
        assert exc_lon_high.value.status_code == 400

        with pytest.raises(HTTPException) as exc_lon_low:
            await reverse_geocode(0.0, -185.0)
        assert exc_lon_low.value.status_code == 400

    @pytest.mark.asyncio
    async def test_nominatim_http_errors(self):
        """Upstream HTTP error codes (e.g. 500, 403) raise HTTPException with matching status."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            with pytest.raises(HTTPException) as exc_info:
                await reverse_geocode(51.4990, -0.1200)
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_connection_errors_and_timeouts(self):
        """Timeouts raise 504 and request errors raise 502."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Connection timed out")
            with pytest.raises(HTTPException) as exc_timeout:
                await reverse_geocode(51.4991, -0.1201)
            assert exc_timeout.value.status_code == 504

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            with pytest.raises(HTTPException) as exc_conn:
                await reverse_geocode(51.4992, -0.1202)
            assert exc_conn.value.status_code == 502

    @pytest.mark.asyncio
    async def test_missing_or_malformed_response_fields(self):
        """Missing display_name falls back gracefully to formatted coordinate label, and errors raise 404."""
        # 1. Missing display_name
        mock_resp_missing_name = MagicMock()
        mock_resp_missing_name.status_code = 200
        mock_resp_missing_name.json.return_value = {
            "place_id": 99999,
            "lat": "51.4993",
            "lon": "-0.1203",
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp_missing_name
            res = await reverse_geocode(51.4993, -0.1203)
            assert "Location (51.49930, -0.12030)" in res.display_name

        # 2. Upstream returns error object
        mock_resp_error = MagicMock()
        mock_resp_error.status_code = 200
        mock_resp_error.json.return_value = {"error": "Unable to geocode"}
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp_error
            with pytest.raises(HTTPException) as exc_error:
                await reverse_geocode(51.4994, -0.1204)
            assert exc_error.value.status_code == 404


class TestReverseGeocodeEndpoint:
    """Tests for GET /api/geocode/reverse endpoint."""

    @pytest.mark.asyncio
    async def test_successful_reverse_geocode_endpoint(self, async_client: httpx.AsyncClient):
        """Valid lat and lon parameters return 200 with structured reverse geocode response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_NOMINATIM_REVERSE_SUCCESS

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = await async_client.get("/api/geocode/reverse?lat=51.51381&lon=-0.09836")

            assert res.status_code == 200
            data = res.json()
            assert data["place_id"] == 1058204
            assert "St. Paul's Cathedral" in data["display_name"]
            assert data["lat"] == pytest.approx(51.51381, rel=1e-4)
            assert data["lon"] == pytest.approx(-0.09836, rel=1e-4)
            assert data["address"]["city"] == "London"

    @pytest.mark.asyncio
    async def test_invalid_coordinate_parameters(self, async_client: httpx.AsyncClient):
        """Coordinates outside valid bounds or non-numeric types return 422 Unprocessable Entity."""
        # Latitude > 90
        res = await async_client.get("/api/geocode/reverse?lat=95.0&lon=-0.0984")
        assert res.status_code == 422

        # Latitude < -90
        res = await async_client.get("/api/geocode/reverse?lat=-95.0&lon=-0.0984")
        assert res.status_code == 422

        # Longitude > 180
        res = await async_client.get("/api/geocode/reverse?lat=51.5&lon=185.0")
        assert res.status_code == 422

        # Non-numeric
        res = await async_client.get("/api/geocode/reverse?lat=abc&lon=-0.0984")
        assert res.status_code == 422

        # Missing parameters
        res = await async_client.get("/api/geocode/reverse?lat=51.5")
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_upstream_service_failure(self, async_client: httpx.AsyncClient):
        """Connection errors to Nominatim return 502 Bad Gateway."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Service unreachable")
            res = await async_client.get("/api/geocode/reverse?lat=51.5138&lon=-0.0984")

            assert res.status_code == 502
            assert "unable to connect" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upstream_timeout_504(self, async_client: httpx.AsyncClient):
        """Timeout connecting to Nominatim returns 504 Gateway Timeout."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timed out")
            res = await async_client.get("/api/geocode/reverse?lat=51.5138&lon=-0.0984")

            assert res.status_code == 504
            assert "timed out" in res.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upstream_rate_limit_429(self, async_client: httpx.AsyncClient):
        """Nominatim rate limit response returns 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            res = await async_client.get("/api/geocode/reverse?lat=51.5138&lon=-0.0984")

            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"].lower()

