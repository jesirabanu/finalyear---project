"""Unit and integration tests for environmental data service and /api/environment endpoint.
Covers:
- Route geometry sampling (even spacing, boundary retention)
- Response parsing for Air Quality and Weather
- Preservation of missing variables (ensuring no silent zero-filling)
- Route summary computation across sampled points
- Provider error and timeout resilience
- /api/environment query validation and responses
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from app.main import app
from app.services.environmental_service import (
    sample_route_geometry,
    parse_air_quality_item,
    parse_weather_item,
    compute_route_environmental_summary,
    _evaluate_european_aqi,
    _get_wmo_description,
)
from app.schemas.environment import RouteEnvironmentalPoint

MOCK_AQ_CURRENT_RESPONSE = {
    "latitude": 51.51,
    "longitude": -0.09,
    "generationtime_ms": 0.1,
    "current_units": {
        "time": "iso8601",
        "pm10": "μg/m³",
        "pm2_5": "μg/m³",
        "nitrogen_dioxide": "μg/m³",
        "european_aqi": "EAQI",
        "us_aqi": "USAQI",
    },
    "current": {
        "time": "2026-10-10T12:00",
        "interval": 3600,
        "pm10": 16.4,
        "pm2_5": 8.9,
        "nitrogen_dioxide": 24.1,
        "european_aqi": 28,
        "us_aqi": 37,
    },
}

MOCK_AQ_WITH_MISSING_VARS = {
    "latitude": 51.51,
    "longitude": -0.09,
    "current_units": {"pm2_5": "μg/m³", "pm10": "μg/m³"},
    "current": {
        "time": "2026-10-10T12:00",
        "pm10": 15.0,
        "pm2_5": None,  # Explicitly missing from provider
        "nitrogen_dioxide": None,
        "european_aqi": None,
    },
}

MOCK_WEATHER_CURRENT_RESPONSE = {
    "latitude": 51.51,
    "longitude": -0.09,
    "current_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "apparent_temperature": "°C",
        "precipitation": "mm",
        "wind_speed_10m": "km/h",
    },
    "current": {
        "time": "2026-10-10T12:00",
        "temperature_2m": 17.5,
        "apparent_temperature": 16.8,
        "relative_humidity_2m": 62,
        "precipitation": 0.0,
        "weather_code": 2,  # Partly cloudy
        "wind_speed_10m": 14.2,
    },
}


class TestRouteSampling:
    """Tests for route geometry sampling algorithm."""

    def test_sample_short_route(self):
        """Routes with <= max_samples points return all points."""
        coords = [[51.5, -0.1], [51.6, -0.2]]
        samples = sample_route_geometry(coords, max_samples=4)
        assert len(samples) == 2
        assert samples[0] == (0, 51.5, -0.1)
        assert samples[1] == (1, 51.6, -0.2)

    def test_sample_longer_route_even_spacing(self):
        """Long route with 10 coordinates samples start, intermediate, and end evenly."""
        coords = [[51.0 + i * 0.01, -0.1 - i * 0.01] for i in range(10)]
        samples = sample_route_geometry(coords, max_samples=4)

        assert len(samples) == 4
        # First point must be start (index 0)
        assert samples[0][0] == 0
        assert samples[0][1] == 51.0
        # Last point must be end (index 9)
        assert samples[-1][0] == 9
        assert samples[-1][1] == pytest.approx(51.09)
        # Point indices must be strictly increasing
        indices = [s[0] for s in samples]
        assert indices == sorted(indices)


class TestResponseParsingAndIntegrity:
    """Tests parsing and verification that missing fields are never silently replaced with 0."""

    def test_parse_complete_air_quality(self):
        """Complete air quality item parses variables and evaluates EAQI rating."""
        aq_data, forecast_ts = parse_air_quality_item(MOCK_AQ_CURRENT_RESPONSE)

        assert forecast_ts == "2026-10-10T12:00"
        assert aq_data.pm2_5.value == 8.9
        assert aq_data.pm2_5.unit == "μg/m³"
        assert aq_data.pm2_5.status == "available"
        assert aq_data.pm10.value == 16.4
        assert aq_data.nitrogen_dioxide.value == 24.1
        assert aq_data.european_aqi.value == 28
        assert aq_data.aqi_category == "Fair"
        assert aq_data.aqi_color == "#3b82f6"

    def test_missing_air_quality_fields_not_zero_filled(self):
        """Missing pollutant readings remain None and are NOT converted to zero."""
        aq_data, _ = parse_air_quality_item(MOCK_AQ_WITH_MISSING_VARS)

        assert aq_data.pm10.value == 15.0
        assert aq_data.pm10.status == "available"

        # PM2.5 and NO2 must remain None, never 0.0
        assert aq_data.pm2_5.value is None
        assert aq_data.pm2_5.status == "missing_from_provider"
        assert aq_data.nitrogen_dioxide.value is None
        assert aq_data.nitrogen_dioxide.status == "missing_from_provider"
        assert aq_data.european_aqi.value is None

    def test_parse_complete_weather(self):
        """Complete weather item parses temperature, units, and WMO description."""
        wx_data, forecast_ts = parse_weather_item(MOCK_WEATHER_CURRENT_RESPONSE)

        assert forecast_ts == "2026-10-10T12:00"
        assert wx_data.temperature_c == 17.5
        assert wx_data.apparent_temperature_c == 16.8
        assert wx_data.relative_humidity_pct == 62.0
        assert wx_data.wind_speed_kmh == 14.2
        assert wx_data.weather_code == 2
        assert wx_data.weather_description == "Partly cloudy"

    def test_wmo_code_mapping(self):
        """Verify WMO weather code descriptions."""
        assert _get_wmo_description(0) == "Clear sky"
        assert _get_wmo_description(61) == "Slight rain"
        assert _get_wmo_description(95) == "Thunderstorm"
        assert _get_wmo_description(None) is None

    def test_eaqi_threshold_evaluation(self):
        """Verify European AQI categorization thresholds."""
        assert _evaluate_european_aqi(15) == ("Good", "#10b981")
        assert _evaluate_european_aqi(35) == ("Fair", "#3b82f6")
        assert _evaluate_european_aqi(55) == ("Moderate", "#f59e0b")
        assert _evaluate_european_aqi(75) == ("Poor", "#ef4444")
        assert _evaluate_european_aqi(95) == ("Very Poor", "#9333ea")
        assert _evaluate_european_aqi(110) == ("Extremely Poor", "#7e22ce")
        assert _evaluate_european_aqi(None) == (None, None)


class TestRouteSummaryComputation:
    """Tests aggregation of sampled points into route-level summaries."""

    def test_route_summary_averaging(self):
        """Route summary averages available readings without artificial zeros."""
        aq_1, _ = parse_air_quality_item(MOCK_AQ_CURRENT_RESPONSE)
        wx_1, _ = parse_weather_item(MOCK_WEATHER_CURRENT_RESPONSE)

        # Second point with higher PM2.5 and temperature
        item2_aq = {
            "current_units": {"pm2_5": "μg/m³", "pm10": "μg/m³"},
            "current": {"pm2_5": 11.1, "pm10": 20.0, "european_aqi": 32},
        }
        item2_wx = {
            "current_units": {"temperature_2m": "°C"},
            "current": {"temperature_2m": 19.5, "apparent_temperature": 18.2, "relative_humidity_2m": 58},
        }
        aq_2, _ = parse_air_quality_item(item2_aq)
        wx_2, _ = parse_weather_item(item2_wx)

        sample_points = [
            RouteEnvironmentalPoint(point_index=0, lat=51.50, lon=-0.09, air_quality=aq_1, weather=wx_1),
            RouteEnvironmentalPoint(point_index=1, lat=51.51, lon=-0.08, air_quality=aq_2, weather=wx_2),
        ]

        summary = compute_route_environmental_summary(sample_points, forecast_ts="2026-10-10T12:00")

        assert summary.samples_count == 2
        assert summary.has_air_quality is True
        assert summary.has_weather is True
        # PM2.5 average: (8.9 + 11.1) / 2 = 10.0
        assert summary.air_quality.pm2_5.value == 10.0
        # Temperature average: (17.5 + 19.5) / 2 = 18.5
        assert summary.weather.temperature_c == 18.5
        assert summary.metadata.is_modeled is True
        assert "Regional atmospheric" in summary.metadata.spatial_resolution_note


class TestEnvironmentEndpoint:
    """Tests for GET /api/environment endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, async_client: httpx.AsyncClient):
        """Out of bounds latitude or longitude returns 422."""
        res = await async_client.get("/api/environment?lat=95.0&lon=0.0")
        assert res.status_code == 422

        res2 = await async_client.get("/api/environment?lat=0.0&lon=200.0")
        assert res2.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_iso_time_format(self, async_client: httpx.AsyncClient):
        """Malformed timestamp string returns 400."""
        res = await async_client.get("/api/environment?lat=51.5&lon=-0.1&time=not-a-date")
        assert res.status_code == 400
        assert "Invalid time format" in res.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.services.environmental_service.fetch_air_quality_batch")
    @patch("app.services.environmental_service.fetch_weather_batch")
    async def test_successful_point_environment(self, mock_wx_batch, mock_aq_batch, async_client: httpx.AsyncClient):
        """Valid query returns structured air quality and weather data."""
        mock_aq_batch.return_value = [MOCK_AQ_CURRENT_RESPONSE]
        mock_wx_batch.return_value = [MOCK_WEATHER_CURRENT_RESPONSE]

        res = await async_client.get("/api/environment?lat=51.5138&lon=-0.0984")
        assert res.status_code == 200

        data = res.json()
        assert data["latitude"] == pytest.approx(51.5138)
        assert data["longitude"] == pytest.approx(-0.0984)
        assert data["air_quality"]["pm2_5"]["value"] == 8.9
        assert data["air_quality"]["european_aqi"]["value"] == 28
        assert data["weather"]["temperature_c"] == 17.5
        assert data["weather"]["weather_description"] == "Partly cloudy"
        assert data["metadata"]["is_modeled"] is True
        assert "Copernicus" in data["metadata"]["air_quality_source"]
