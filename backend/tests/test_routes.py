"""Tests for /api/routes endpoint and routing_service.
Covers:
- Request validation (out of bounds, identical coordinates, missing fields)
- Missing ORS_API_KEY handling
- Provider response parsing (multiple routes, single route, genuine coordinates)
- Provider failure cases (404 no route, 401 unauthorized, 429 rate limit, 504 timeout)
"""
import math
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from app.main import app
from app.core.config import settings
from app.schemas.coordinates import CoordinatePoint
from app.schemas.routes import RouteModel, RouteRequest
from app.services.routing_service import (
    _parse_ors_features,
    _parse_osrm_route,
    generate_perpendicular_waypoints,
    is_valid_pedestrian_route,
    is_duplicate_route,
    _fetch_osrm_walking_routes,
    get_walking_routes,
)

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

    @pytest.mark.asyncio
    async def test_missing_coordinates(self, async_client: httpx.AsyncClient):
        """Omitting origin or destination should return 422 Unprocessable Entity."""
        res = await async_client.post("/api/routes", json={"source": {"lat": 51.5, "lon": -0.1}})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_out_of_bounds_latitude(self, async_client: httpx.AsyncClient):
        """Latitude > 90.0 or < -90.0 must be rejected."""
        res = await async_client.post(
            "/api/routes",
            json={
                "source": {"lat": 95.0, "lon": -0.1},
                "destination": {"lat": 51.5, "lon": -0.07},
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_out_of_bounds_longitude(self, async_client: httpx.AsyncClient):
        """Longitude > 180.0 or < -180.0 must be rejected."""
        res = await async_client.post(
            "/api/routes",
            json={
                "source": {"lat": 51.5, "lon": -195.0},
                "destination": {"lat": 51.5, "lon": -0.07},
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_identical_source_and_destination(self, async_client: httpx.AsyncClient):
        """Identical origin and destination should fail validation."""
        res = await async_client.post(
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

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_503(self, async_client: httpx.AsyncClient):
        """When ORS_API_KEY is not configured, API must return HTTP 503."""
        with patch.object(settings, "ORS_API_KEY", ""):
            res = await async_client.post(
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

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_multiple_routes_parsed_correctly(self, mock_key, async_client: httpx.AsyncClient):
        """Multiple provider routes must yield multiple distinct RouteModel items with genuine Leaflet coords."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_ORS_FEATURE_COLLECTION_MULTIPLE

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
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

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_single_route_not_duplicated(self, mock_key, async_client: httpx.AsyncClient):
        """When ORS returns only 1 route, the API must honestly report 1 route and NOT duplicate."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_ORS_FEATURE_COLLECTION_SINGLE

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
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

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_no_walking_route_found_404(self, mock_key, async_client: httpx.AsyncClient):
        """When provider returns 404 or 400 not found, API responds with 404 and readable error."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {
            "error": {"code": 2010, "message": "Could not find routable point within a radius of 350.0 meters."}
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
                "/api/routes",
                json={
                    "source": {"lat": 0.0, "lon": 0.0},
                    "destination": {"lat": 0.1, "lon": 0.1},
                },
            )
            assert res.status_code == 404
            assert "Could not find routable point" in res.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_unauthorized_key_401(self, mock_key, async_client: httpx.AsyncClient):
        """Invalid API key returns 401."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": "Invalid API Key"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 401
            assert "authorization failed" in res.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_rate_limit_429(self, mock_key, async_client: httpx.AsyncClient):
        """Rate limited provider returns 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"error": "Rate limit exceeded"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 429
            assert "rate limit" in res.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.services.routing_service._fetch_osrm_walking_routes", side_effect=httpx.TimeoutException("OSRM timed out"))
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_timeout_504(self, mock_key, mock_osrm, async_client: httpx.AsyncClient):
        """Timeout connecting to provider returns 504."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            res = await async_client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 504
            assert "timed out" in res.json()["detail"]


class TestTurnByTurnDirections:
    """Unit and regression tests for turn-by-turn walking maneuver instructions."""

    def test_ors_step_extraction_with_maneuvers(self):
        """Verify ORS maneuver steps are parsed with instruction, distance, duration, type, modifier, name, and location."""
        mock_features = [
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
                    "summary": {"distance": 520.5, "duration": 390.0},
                    "segments": [
                        {
                            "distance": 520.5,
                            "duration": 390.0,
                            "steps": [
                                {
                                    "distance": 120.5,
                                    "duration": 90.0,
                                    "type": 11,
                                    "instruction": "Depart walking on Queen Victoria St",
                                    "name": "Queen Victoria St",
                                    "way_points": [0, 1],
                                },
                                {
                                    "distance": 350.0,
                                    "duration": 260.0,
                                    "type": 1,
                                    "instruction": "Turn right onto Cannon St",
                                    "name": "Cannon St",
                                    "way_points": [1, 2],
                                },
                                {
                                    "distance": 50.0,
                                    "duration": 40.0,
                                    "type": 10,
                                    "instruction": "Arrive at destination",
                                    "name": "Cannon St",
                                    "way_points": [2, 2],
                                },
                            ],
                        }
                    ],
                },
            }
        ]

        routes = _parse_ors_features(mock_features)
        assert len(routes) == 1
        route = routes[0]
        assert len(route.steps) == 3

        step0 = route.steps[0]
        assert step0.instruction == "Depart walking on Queen Victoria St"
        assert step0.distance_m == 120.5
        assert step0.duration_s == 90.0
        assert step0.type == 11
        assert step0.modifier == "depart"
        assert step0.name == "Queen Victoria St"
        assert step0.location == [51.5138, -0.0984]

        step1 = route.steps[1]
        assert step1.instruction == "Turn right onto Cannon St"
        assert step1.type == 1
        assert step1.modifier == "right"
        assert step1.location == [51.5100, -0.0870]

        step2 = route.steps[2]
        assert step2.instruction == "Arrive at destination"
        assert step2.type == 10
        assert step2.modifier == "arrive"
        assert step2.location == [51.5081, -0.0759]

    def test_multiple_segments_steps_concatenated_in_order(self):
        """Verify that multi-segment routes concatenate steps sequentially."""
        mock_features = [
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
                    "summary": {"distance": 1000.0, "duration": 800.0},
                    "segments": [
                        {
                            "distance": 600.0,
                            "duration": 480.0,
                            "steps": [
                                {
                                    "distance": 600.0,
                                    "duration": 480.0,
                                    "type": 11,
                                    "instruction": "Head east on Queen Victoria St",
                                    "name": "Queen Victoria St",
                                    "way_points": [0, 1],
                                }
                            ],
                        },
                        {
                            "distance": 400.0,
                            "duration": 320.0,
                            "steps": [
                                {
                                    "distance": 400.0,
                                    "duration": 320.0,
                                    "type": 10,
                                    "instruction": "Arrive at Tower Hill",
                                    "name": "Tower Hill",
                                    "way_points": [1, 2],
                                }
                            ],
                        },
                    ],
                },
            }
        ]

        routes = _parse_ors_features(mock_features)
        assert len(routes) == 1
        assert len(routes[0].steps) == 2
        assert routes[0].steps[0].instruction == "Head east on Queen Victoria St"
        assert routes[0].steps[1].instruction == "Arrive at Tower Hill"

    def test_routes_without_steps_default_to_empty_list(self):
        """Provider responses without step properties must default steps to an empty list."""
        mock_features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                },
                "properties": {
                    "summary": {"distance": 500.0, "duration": 350.0},
                },
            }
        ]
        routes = _parse_ors_features(mock_features)
        assert len(routes) == 1
        assert routes[0].steps == []

    def test_malformed_steps_handled_gracefully(self):
        """Malformed step entries (missing instructions, empty objects, out-of-bounds indices) should not crash."""
        mock_features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                },
                "properties": {
                    "summary": {"distance": 500.0, "duration": 350.0},
                    "segments": [
                        {
                            "steps": [
                                {},  # Empty object
                                None,  # Null entry
                                {
                                    "distance": "invalid_dist",
                                    "duration": "invalid_dur",
                                    "type": 0,  # "left"
                                    "name": "Side Alley",
                                    "way_points": [999, 1000],  # Out of range index
                                },
                            ]
                        }
                    ],
                },
            }
        ]
        routes = _parse_ors_features(mock_features)
        assert len(routes) == 1
        # None step should be skipped, empty step and validly handled step should parse safely
        steps = routes[0].steps
        assert len(steps) == 2
        # First step had nothing: default instruction generated
        assert "walking path" in steps[0].instruction.lower()
        # Second step has type 0 -> "Walk left on Side Alley" synthesized because instruction missing
        assert "left" in steps[1].instruction.lower()
        assert steps[1].location is None  # Out-of-bounds index handled safely

    def test_osrm_step_extraction(self):
        """Verify that OSRM fallback route steps and coordinates are parsed correctly."""
        mock_osrm_route = {
            "distance": 800.0,
            "duration": 600.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-0.0984, 51.5138],
                    [-0.0870, 51.5100],
                    [-0.0759, 51.5081],
                ],
            },
            "legs": [
                {
                    "distance": 800.0,
                    "duration": 600.0,
                    "steps": [
                        {
                            "distance": 300.0,
                            "duration": 220.0,
                            "name": "Fleet Street",
                            "maneuver": {
                                "type": "depart",
                                "modifier": "straight",
                                "location": [-0.0984, 51.5138],
                            },
                        },
                        {
                            "distance": 500.0,
                            "duration": 380.0,
                            "name": "Ludgate Hill",
                            "maneuver": {
                                "type": "turn",
                                "modifier": "right",
                                "location": [-0.0870, 51.5100],
                            },
                        },
                    ],
                }
            ],
        }

        parsed = _parse_osrm_route(0, mock_osrm_route)
        assert len(parsed.steps) == 2
        assert "Fleet Street" in parsed.steps[0].instruction
        assert parsed.steps[0].distance_m == 300.0
        assert parsed.steps[0].location == [51.5138, -0.0984]

        assert "Ludgate Hill" in parsed.steps[1].instruction
        assert parsed.steps[1].modifier == "right"
        assert parsed.steps[1].location == [51.5100, -0.0870]

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_routes_api_endpoint_returns_steps(self, mock_key, async_client: httpx.AsyncClient):
        """Integration test: /api/routes response includes steps field in RouteModel."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                    },
                    "properties": {
                        "summary": {"distance": 500.0, "duration": 360.0},
                        "segments": [
                            {
                                "steps": [
                                    {
                                        "distance": 500.0,
                                        "duration": 360.0,
                                        "type": 6,
                                        "instruction": "Walk straight on High St",
                                        "name": "High St",
                                        "way_points": [0, 1],
                                    }
                                ]
                            }
                        ],
                    },
                }
            ],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            res = await async_client.post(
                "/api/routes",
                json={
                    "source": {"lat": 51.5138, "lon": -0.0984},
                    "destination": {"lat": 51.5081, "lon": -0.0759},
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert "routes" in data
            assert len(data["routes"]) == 1
            route = data["routes"][0]
            assert "steps" in route
            assert len(route["steps"]) == 1
            assert route["steps"][0]["instruction"] == "Walk straight on High St"
            assert route["steps"][0]["distance_m"] == 500.0
            assert route["steps"][0]["location"] == [51.5138, -0.0984]


class TestPerpendicularWaypointMathematics:
    """Tests for lateral detour waypoint generation and latitude-aware scaling."""

    def test_perpendicular_waypoint_direction(self):
        """Waypoints must be strictly perpendicular to the direct route vector."""
        src_lat, src_lon = 51.5000, -0.1000
        dst_lat, dst_lon = 51.5200, -0.0800

        waypoints = generate_perpendicular_waypoints(
            src_lat, src_lon, dst_lat, dst_lon, factors=[0.20, -0.20]
        )
        assert len(waypoints) == 2

        mid_lat = (src_lat + dst_lat) / 2.0
        mid_lon = (src_lon + dst_lon) / 2.0
        cos_lat = math.cos(math.radians(mid_lat))

        # Forward vector in metric-scaled space
        v_y = dst_lat - src_lat
        v_x = (dst_lon - src_lon) * cos_lat

        for wp in waypoints:
            # Offset vector from midpoint to waypoint
            off_y = wp["lat"] - mid_lat
            off_x = (wp["lon"] - mid_lon) * cos_lat

            # Dot product must be practically 0 (perpendicular)
            dot_product = v_x * off_x + v_y * off_y
            assert abs(dot_product) < 1e-7

    def test_latitude_aware_longitude_scaling(self):
        """Longitude displacement must scale inversely with cos(lat) due to meridian convergence."""
        d_lat = 0.02
        d_lon = 0.0

        # Case 1: Equator (cos(0) = 1.0)
        wp_eq = generate_perpendicular_waypoints(0.0, 0.0, d_lat, d_lon, factors=[0.20])
        # Case 2: 60 degrees North (cos(60 deg) = 0.5)
        wp_60 = generate_perpendicular_waypoints(60.0, 0.0, 60.0 + d_lat, d_lon, factors=[0.20])

        assert len(wp_eq) == 1
        assert len(wp_60) == 1

        delta_lon_eq = abs(wp_eq[0]["lon"] - 0.0)
        delta_lon_60 = abs(wp_60[0]["lon"] - 0.0)

        # At 60 deg lat, cos(60 deg) is 0.5, so delta_lon must be ~2x larger in degrees for equal physical distance
        ratio = delta_lon_60 / delta_lon_eq
        assert 1.95 < ratio < 2.05

    def test_northern_and_southern_hemisphere(self):
        """Perpendicular offsets must work symmetrically in both hemispheres."""
        wp_north = generate_perpendicular_waypoints(45.0, 10.0, 45.02, 10.03, factors=[0.25, -0.25])
        wp_south = generate_perpendicular_waypoints(-45.0, 10.0, -44.98, 10.03, factors=[0.25, -0.25])

        assert len(wp_north) == 2
        assert len(wp_south) == 2

        # Magnitude of offset should match
        dist_north = math.hypot(wp_north[0]["lat"] - 45.01, wp_north[0]["lon"] - 10.015)
        dist_south = math.hypot(wp_south[0]["lat"] - (-44.99), wp_south[0]["lon"] - 10.015)
        assert abs(dist_north - dist_south) < 1e-4

    def test_near_polar_safety(self):
        """Near-polar coordinates must not trigger ZeroDivisionError or non-finite values."""
        waypoints = generate_perpendicular_waypoints(88.5, 0.0, 89.0, 1.0, factors=[0.20, -0.20])
        assert len(waypoints) == 2
        for wp in waypoints:
            assert math.isfinite(wp["lat"])
            assert math.isfinite(wp["lon"])
            assert -90.0 <= wp["lat"] <= 90.0
            assert -180.0 <= wp["lon"] <= 180.0

    def test_zero_length_route_handling(self):
        """Identical origin and destination must safely yield an empty waypoint list."""
        waypoints = generate_perpendicular_waypoints(51.5, -0.1, 51.5, -0.1)
        assert waypoints == []

    def test_coordinate_boundary_validation(self):
        """Displaced coordinates near the antimeridian must be properly normalized within [-180, 180]."""
        waypoints = generate_perpendicular_waypoints(0.0, 179.9, 0.02, 179.95, factors=[0.50, -0.50])
        assert len(waypoints) == 2
        for wp in waypoints:
            assert -180.0 <= wp["lon"] <= 180.0
            assert -90.0 <= wp["lat"] <= 90.0


class TestAlternativeRouteValidationAndDeduplication:
    """Tests for route geometry validation and duplicate rejection."""

    def test_valid_route_passes_validation(self):
        """A well-formed route connecting origin and destination must be accepted."""
        src = CoordinatePoint(lat=51.5138, lon=-0.0984)
        dst = CoordinatePoint(lat=51.5081, lon=-0.0759)
        route = RouteModel(
            id="r1",
            name="Route 1",
            distance_m=1200.0,
            distance_km=1.2,
            duration_s=900.0,
            duration_min=15.0,
            coordinates=[[51.5138, -0.0984], [51.5110, -0.0850], [51.5081, -0.0759]],
        )
        assert is_valid_pedestrian_route(route, src, dst, primary_distance_m=1100.0) is True

    def test_invalid_geometry_rejected(self):
        """Routes with fewer than 2 coordinates or non-positive distance must be rejected."""
        src = CoordinatePoint(lat=51.5138, lon=-0.0984)
        dst = CoordinatePoint(lat=51.5081, lon=-0.0759)

        r_empty = RouteModel(
            id="r_empty",
            name="Empty Route",
            distance_m=100.0,
            distance_km=0.1,
            duration_s=100.0,
            duration_min=1.6,
            coordinates=[],
        )
        assert is_valid_pedestrian_route(r_empty, src, dst) is False

        r_zero = RouteModel(
            id="r_zero",
            name="Zero Route",
            distance_m=0.0,
            distance_km=0.0,
            duration_s=0.0,
            duration_min=0.0,
            coordinates=[[51.5138, -0.0984], [51.5081, -0.0759]],
        )
        assert is_valid_pedestrian_route(r_zero, src, dst) is False

    def test_endpoint_mismatch_rejected(self):
        """Routes failing to start or terminate near origin and destination must be rejected."""
        src = CoordinatePoint(lat=51.5138, lon=-0.0984)
        dst = CoordinatePoint(lat=51.5081, lon=-0.0759)
        r_far = RouteModel(
            id="r_far",
            name="Far Route",
            distance_m=1200.0,
            distance_km=1.2,
            duration_s=900.0,
            duration_min=15.0,
            coordinates=[[52.0000, 0.5000], [52.0100, 0.5100]],
        )
        assert is_valid_pedestrian_route(r_far, src, dst) is False

    def test_excessive_detour_rejected(self):
        """Routes with distance exceeding 2.5x the primary route must be rejected."""
        src = CoordinatePoint(lat=51.5138, lon=-0.0984)
        dst = CoordinatePoint(lat=51.5081, lon=-0.0759)
        r_long = RouteModel(
            id="r_long",
            name="Excessive Detour",
            distance_m=3500.0,
            distance_km=3.5,
            duration_s=2500.0,
            duration_min=41.0,
            coordinates=[[51.5138, -0.0984], [51.5081, -0.0759]],
        )
        # Primary distance is 1000m -> 3500m is 3.5x > 2.5x threshold
        assert is_valid_pedestrian_route(r_long, src, dst, primary_distance_m=1000.0) is False

    def test_duplicate_route_detection(self):
        """Routes with identical distance, duration, and midpoint coordinates must be flagged as duplicates."""
        r1 = RouteModel(
            id="r1",
            name="Route 1",
            distance_m=1000.0,
            distance_km=1.0,
            duration_s=800.0,
            duration_min=13.3,
            coordinates=[[51.5138, -0.0984], [51.5110, -0.0870], [51.5081, -0.0759]],
        )
        r2 = RouteModel(
            id="r2",
            name="Duplicate Route",
            distance_m=1002.0,
            distance_km=1.0,
            duration_s=801.0,
            duration_min=13.3,
            coordinates=[[51.5138, -0.0984], [51.5110, -0.0870], [51.5081, -0.0759]],
        )
        assert is_duplicate_route(r2, [r1]) is True

    def test_distinct_route_not_flagged_as_duplicate(self):
        """Routes with different distances or different spatial midpoints must not be flagged."""
        r1 = RouteModel(
            id="r1",
            name="Route 1",
            distance_m=1000.0,
            distance_km=1.0,
            duration_s=800.0,
            duration_min=13.3,
            coordinates=[[51.5138, -0.0984], [51.5110, -0.0870], [51.5081, -0.0759]],
        )
        r_diff = RouteModel(
            id="r_diff",
            name="Different Route",
            distance_m=1350.0,
            distance_km=1.35,
            duration_s=1100.0,
            duration_min=18.3,
            coordinates=[[51.5138, -0.0984], [51.5170, -0.0820], [51.5081, -0.0759]],
        )
        assert is_duplicate_route(r_diff, [r1]) is False


class TestORSAlternativeCorridors:
    """Tests for ORS alternative routing, HTTP 400 retries, and waypoint corridors."""

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_ors_http_400_fallback_and_waypoint_corridor(self, mock_key):
        """When ORS returns 400 for alternative_routes, retries primary, then generates waypoint corridors."""
        # 1st call (alternative_routes payload) -> 400
        resp_400 = MagicMock()
        resp_400.status_code = 400
        resp_400.text = "Alternative route calculation is not supported for foot-walking"

        # 2nd call (primary retry) -> 200 with 1 route
        resp_primary = MagicMock()
        resp_primary.status_code = 200
        resp_primary.json.return_value = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.0984, 51.5138], [-0.0870, 51.5100], [-0.0759, 51.5081]],
                    },
                    "properties": {
                        "summary": {"distance": 1500.0, "duration": 1100.0},
                    },
                }
            ],
        }

        # 3rd call (waypoint detour) -> 200 with genuine alternative corridor
        resp_alt = MagicMock()
        resp_alt.status_code = 200
        resp_alt.json.return_value = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [-0.0984, 51.5138],
                            [-0.0920, 51.5160],
                            [-0.0810, 51.5120],
                            [-0.0759, 51.5081],
                        ],
                    },
                    "properties": {
                        "summary": {"distance": 1850.0, "duration": 1380.0},
                    },
                }
            ],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [resp_400, resp_primary, resp_alt, resp_alt]
            req = RouteRequest(
                source=CoordinatePoint(lat=51.5138, lon=-0.0984),
                destination=CoordinatePoint(lat=51.5081, lon=-0.0759),
                alternatives=1,
            )
            result = await get_walking_routes(req)

            assert result.total_routes == 2
            assert result.has_alternatives is True
            assert result.routes[0].is_primary is True
            assert result.routes[0].distance_m == 1500.0
            assert result.routes[1].is_primary is False
            assert result.routes[1].distance_m == 1850.0

    @pytest.mark.asyncio
    @patch("app.services.routing_service._is_api_key_configured", return_value=True)
    async def test_ors_waypoint_failure_preserves_primary_route(self, mock_key):
        """When alternative waypoint requests fail, the primary walking route is strictly preserved."""
        resp_primary = MagicMock()
        resp_primary.status_code = 200
        resp_primary.json.return_value = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                    },
                    "properties": {
                        "summary": {"distance": 1200.0, "duration": 900.0},
                    },
                }
            ],
        }

        # Waypoint requests throw an exception
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                resp_primary,
                httpx.ConnectError("Waypoint route unreachable"),
                httpx.ConnectError("Waypoint route unreachable"),
            ]
            req = RouteRequest(
                source=CoordinatePoint(lat=51.5138, lon=-0.0984),
                destination=CoordinatePoint(lat=51.5081, lon=-0.0759),
                alternatives=1,
            )
            result = await get_walking_routes(req)

            assert result.total_routes == 1
            assert result.has_alternatives is False
            assert result.routes[0].is_primary is True
            assert result.routes[0].distance_m == 1200.0


class TestOSRMAlternativeCorridors:
    """Tests for OSRM fallback waypoint detour generation and deduplication."""

    @pytest.mark.asyncio
    async def test_osrm_waypoint_guided_alternatives_success(self):
        """OSRM generates waypoint-guided detour corridors when requested alternatives exceed direct routes."""
        resp_primary = MagicMock()
        resp_primary.status_code = 200
        resp_primary.json.return_value = {
            "routes": [
                {
                    "distance": 1000.0,
                    "duration": 750.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                    },
                    "legs": [],
                }
            ]
        }

        resp_waypoint = MagicMock()
        resp_waypoint.status_code = 200
        resp_waypoint.json.return_value = {
            "routes": [
                {
                    "distance": 1250.0,
                    "duration": 940.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [-0.0984, 51.5138],
                            [-0.0910, 51.5160],
                            [-0.0759, 51.5081],
                        ],
                    },
                    "legs": [],
                }
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [resp_primary, resp_waypoint, resp_waypoint]
            req = RouteRequest(
                source=CoordinatePoint(lat=51.5138, lon=-0.0984),
                destination=CoordinatePoint(lat=51.5081, lon=-0.0759),
                alternatives=1,
            )
            routes = await _fetch_osrm_walking_routes(req)

            assert len(routes) == 2
            assert routes[0].is_primary is True
            assert routes[0].distance_m == 1000.0
            assert routes[1].is_primary is False
            assert routes[1].distance_m == 1250.0

    @pytest.mark.asyncio
    async def test_osrm_unroutable_waypoint_gracefully_ignored(self):
        """When an OSRM waypoint query fails or returns 404, primary route is preserved."""
        resp_primary = MagicMock()
        resp_primary.status_code = 200
        resp_primary.json.return_value = {
            "routes": [
                {
                    "distance": 1000.0,
                    "duration": 750.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-0.0984, 51.5138], [-0.0759, 51.5081]],
                    },
                    "legs": [],
                }
            ]
        }

        resp_error = MagicMock()
        resp_error.status_code = 400
        resp_error.json.return_value = {"message": "Unroutable point"}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [resp_primary, resp_error, resp_error, resp_error]
            req = RouteRequest(
                source=CoordinatePoint(lat=51.5138, lon=-0.0984),
                destination=CoordinatePoint(lat=51.5081, lon=-0.0759),
                alternatives=1,
            )
            routes = await _fetch_osrm_walking_routes(req)

            assert len(routes) == 1
            assert routes[0].is_primary is True
            assert routes[0].distance_m == 1000.0


