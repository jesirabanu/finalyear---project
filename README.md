# AI-Driven Multi-Environmental Personalized Pedestrian Routing

> **Final-Year Computer Science Project**  
> A full-stack web application designed to compute and rank walking routes based on multi-environmental indicators (air quality, thermal comfort, greenery presence, traffic exposure, and walking distance) tailored to individual pedestrian preferences.

---

## 📌 Project Architecture

```
final - project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry point, CORS & routing
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py              # Pydantic Settings (ORS, Nominatim, Overpass)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py              # Endpoints: /api/routes, /api/geocode, /api/environment, /api/rank, /api/health
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── coordinates.py         # Bounds-validated coordinate models
│   │   │   ├── routes.py              # Route request/response models & Leaflet coords
│   │   │   ├── geocoding.py           # Nominatim result schemas
│   │   │   ├── environment.py         # Air quality, weather & route summary schemas
│   │   │   └── preferences.py         # Multi-criteria preferences & ranking models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── routing_service.py     # OpenRouteService caller & alternative route parser
│   │   │   ├── geocoding_service.py   # Rate-limited & cached Nominatim geocoder
│   │   │   ├── environmental_service.py# Open-Meteo batch air quality & weather integration
│   │   │   ├── greenery_service.py    # Overpass OSM greenery buffer & corridor parser
│   │   │   └── traffic_service.py     # Live traffic flow and static major-road proxy
│   │   └── algorithm/
│   │       ├── __init__.py
│   │       └── ranking_engine.py      # Transparent multi-criteria & Pareto-dominance engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_routes.py             # Route validation, ORS parsing, failure tests
│   │   ├── test_geocoding.py          # Geocoding validation, rate limits, error tests
│   │   ├── test_environment.py        # Air quality, weather, sampling & missing field tests
│   │   ├── test_algorithm.py          # Factor directions, Pareto dominance, ties & proof of no fixed weights
│   │   └── test_greenery_and_traffic.py# Overpass greenery buffer, traffic proxy, rate limits & ranking
│   ├── requirements.txt               # Python dependencies (FastAPI, httpx, pytest, etc.)
│   ├── .env.example                   # Environment variable template with placeholders
│   ├── .env                           # Local environment settings
│   └── run.py                         # Server startup script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx            # Leaflet map, route polylines, fitBounds & selection
│   │   │   ├── Sidebar.jsx            # Preferences, accessible checkboxes, route cards & trade-offs
│   │   │   ├── RouteComparisonTable.jsx# Side-by-side multi-criteria comparison matrix
│   │   │   ├── StatusBadge.jsx        # Live backend & integration health monitor
│   │   │   └── EnvironmentalPanel.jsx # Route-level air quality & temperature profile panel
│   │   ├── services/
│   │   │   ├── routingService.js      # Backend routing and ranking API client
│   │   │   ├── geocodingService.js    # Decoupled backend geocoding API client
│   │   │   └── environmentService.js  # Decoupled environmental API client
│   │   ├── App.jsx                    # Application state management & dynamic re-ranking
│   │   ├── App.css                    # Responsive styling & accessible comparison table
│   │   └── main.jsx                   # React entry point
│   ├── package.json
│   └── vite.config.js                 # Vite config with backend API proxy (/api -> :8000)
├── RESEARCH_GAPS.md                   # Systematic analysis of 24 papers & 5 research gaps
└── README.md                          # Setup, execution, and testing guide
```

---

## 🛠️ Tech Stack & Services

- **Frontend**: React (Vite), Modern CSS, Lucide Icons
- **Interactive Mapping**: Leaflet (`react-leaflet`) with OpenStreetMap (OSM) Cartographic tiles
- **Backend API**: Python FastAPI, Uvicorn, Pydantic v2, HTTPX
- **Routing Service**: OpenRouteService (ORS) Walking Directions API (`foot-walking`)
- **Geocoding Service**: OpenStreetMap Nominatim (Backend-proxied, rate-limited to 1 req/sec, cached, with custom User-Agent)
- **Environmental Data**: Open-Meteo Air Quality (PM2.5, PM10, NO2, EAQI from Copernicus CAMS) & Forecast (Temperature, Feels-Like, Humidity, Wind from ECMWF/ICON)
- **Greenery Presence**: OpenStreetMap Overpass API (Bounded corridor query, 50m buffer fraction & park proximity)
- **Traffic Exposure**: Live TomTom Traffic Flow API (optional) & Defensible Static Road Hierarchy Proxy (separating live from proxy)
- **Multi-Criteria Ranking**: Deterministic Equal-Priority Normalization with Pareto-Dominance Analysis
- **Unit & Integration Testing**: `pytest`, `pytest-asyncio`, `TestClient` (56 automated tests passing)

---

## 🌐 API Specification

### 1. `POST /api/routes`
Calculates walking paths between origin and destination, requesting genuine alternative routes from OpenRouteService.

**Request Body:**
```json
{
  "source": {
    "lat": 51.5138,
    "lon": -0.0984,
    "label": "St. Paul's Cathedral, London"
  },
  "destination": {
    "lat": 51.5081,
    "lon": -0.0759,
    "label": "Tower of London"
  },
  "alternatives": 2
}
```

**Response Format:**
```json
{
  "routes": [
    {
      "id": "route_0",
      "name": "Route 1: Primary Walking Route",
      "distance_m": 1820.5,
      "distance_km": 1.82,
      "duration_s": 1310.0,
      "duration_min": 21.8,
      "coordinates": [[51.5138, -0.0984], [51.51, -0.087], [51.5081, -0.0759]],
      "color": "#2563eb",
      "is_primary": true,
      "summary": "Shortest direct pedestrian path"
    },
    {
      "id": "route_1",
      "name": "Route 2: Alternative Route A",
      "distance_m": 2150.0,
      "distance_km": 2.15,
      "duration_s": 1548.0,
      "duration_min": 25.8,
      "coordinates": [[51.5138, -0.0984], [51.509, -0.092], [51.5081, -0.0759]],
      "color": "#8b5cf6",
      "is_primary": false,
      "summary": "Alternative pedestrian detour (+0.33 km)"
    }
  ],
  "total_routes": 2,
  "has_alternatives": true,
  "source": { "lat": 51.5138, "lon": -0.0984, "label": "St. Paul's Cathedral, London" },
  "destination": { "lat": 51.5081, "lon": -0.0759, "label": "Tower of London" },
  "message": "Found 2 walking routes (1 primary route and 1 alternative(s))."
}
```

> **📐 Coordinate Format & Ordering**:
> - OpenRouteService directions expect `[longitude, latitude]` according to GeoJSON RFC 7946 specifications.
> - Leaflet `Polyline` and `Marker` components expect `[latitude, longitude]`.
> - The backend handles this coordinate conversion transparently: the `coordinates` array returned in `RouteModel` contains `[latitude, longitude]` pairs ready for direct Leaflet rendering, while preserving standard GeoJSON in `geojson_geometry`.

---

### 2. `GET /api/geocode?q={query}&limit={limit}`
Searches for location suggestions via OpenStreetMap Nominatim.

- **Rate Limiting**: Strictly capped to a maximum of 1 outbound request per second.
- **Caching**: 10-minute in-memory TTL query cache eliminates redundant provider requests.
- **User-Agent Policy**: Identifies the academic application using `settings.NOMINATIM_USER_AGENT` per OpenStreetMap Foundation policy.
- **Input Validation**: Minimum 3 characters; returns `422` or `400` if invalid.

---

### 3. `GET /api/environment?lat={lat}&lon={lon}&time={iso_time}`
Retrieves air quality and meteorological forecast estimates from Open-Meteo for specific geographical coordinates.

- **Variables Returned**:
  - **Air Quality**: PM2.5, PM10, Nitrogen Dioxide ($\text{NO}_2$), and European Air Quality Index (EAQI with qualitative category and color indicator).
  - **Meteorological**: Ambient Temperature (°C), Apparent "Feels-Like" Temperature (°C), Relative Humidity (%), Wind Speed (km/h), and WMO Weather Interpretation.
- **Data Provenance & Transparency**:
  - `is_modeled: true`: Accurately identifies values as regional numerical model forecasts (Copernicus CAMS & ECMWF NWP) rather than street-level sensor readings.
  - `spatial_resolution_note`: Documents regional grid scale (~11 km).
  - Preserves `null` for unrecorded variables without artificial zero-substitution.
- **Route Association**: `POST /api/routes` automatically samples 3–5 representative waypoints along every candidate route and executes a single multi-coordinate batch query, attaching a `RouteEnvironmentalSummary` to each route.

---

### 4. `POST /api/rank`
Ranks candidate walking routes based on user-selected environmental and distance criteria using an equal-priority normalized model and formal Pareto-dominance analysis.

- **Formula**: $\text{Score}(R) = \frac{1}{|K|} \sum_{f \in K} \text{NormalizedScore}(R, f)$
- **Outlier Bounds**: Factors are clipped to physical limits before relative min-max scaling to prevent outlier distortion.
- **Pareto Dominance**: Non-dominated routes always rank ahead of dominated routes.
- **Zero Weight Guessing**: Equal priority ($1/k$) is an algorithmic design choice, not an inferred personal psychological profile.
- **Distance Baseline**: Default baseline evaluates all available factors with distance as documented tie-breaker.

---

### 5. `POST /api/routes/refresh`
Refreshes environmental data (air quality, thermal comfort, traffic exposure, solar shade) for candidate routes without re-requesting ORS walking geometries.

- **Selective Re-evaluation**: Updates route-level profiles, re-runs multi-criteria ranking, and tracks metric fluctuations.
- **Change Explanation**: Explains which factors fluctuated and whether the recommended route changed.
- **Resilient Stale Fallback**: If an upstream provider fails during refresh, previously cached readings are retained with an explicit `is_stale: true` and user warning rather than displaying blank route cards.
- **Explicit Scope Limitation**: Pre-trip comparison re-evaluation only; does not perform live turn-by-turn navigation or real-time GPS rerouting.

**Preference Factors Supported:**
- `air_quality`: Lower EAQI / PM2.5 ($\downarrow$)
- `temperature`: Lower apparent temperature / heat load ($\downarrow$)
- `traffic_exposure`: Lower vehicular traffic index ($\downarrow$)
- `greenery`: Higher tree canopy and park presence ($\uparrow$)
- `walking_distance`: Shorter route distance ($\downarrow$)
- `no_preference`: Applies the transparent default baseline

**Mathematical Formulation:**
$$\text{Score}(R) = \frac{1}{|F_{\text{eval}}|} \sum_{f \in F_{\text{eval}}} \text{normalized\_score}(R, f)$$

- **Equal Priority Heuristic**: $w_f = 1/k$ is explicitly an algorithmic design choice to eliminate user cognitive burden, NOT a discovered psychological personal preference.
- **Pareto Dominance**: Identifies routes strictly dominated by an alternative across evaluated criteria. Non-dominated routes always rank ahead of dominated alternatives.
- **Deterministic Tie-Breaking**: Breaks ties using walking distance (shorter is better), followed by stable alphabetical route ID.
- **Missing Data Handling**: Never zero-fills missing metrics. Unrecorded factors are excluded transparently, and recommendations are withheld if all selected criteria lack data.

---

### 5. `GET /api/health`
Verifies backend status and configuration of external integrations (ORS key presence, Nominatim, Open-Meteo, Overpass).

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher

---

### Step 1: Backend Setup (FastAPI)

1. Open a terminal in the `backend` folder:
   ```powershell
   cd "C:\final - project\backend"
   ```

2. Activate the Python virtual environment:
   ```powershell
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   ```
   *(If script execution is disabled in PowerShell, activate using `.\venv\Scripts\activate.bat` in CMD, or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

3. Install/verify Python packages:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure environment variables in `backend/.env`:
   ```ini
   HOST=127.0.0.1
   PORT=8000
   DEBUG=True

   # Add your OpenRouteService API key:
   # Free registration at: https://openrouteservice.org/dev/#/signup
   ORS_API_KEY=your_openrouteservice_api_key_here

   # Endpoints & User-Agent (defaults populated)
   NOMINATIM_API_URL=https://nominatim.openstreetmap.org/search
   NOMINATIM_USER_AGENT=EcoWalk-PedestrianRouting/1.0 (academic-pedestrian-routing)
   OVERPASS_API_URL=https://overpass-api.de/api/interpreter
   ```

5. Run unit and integration tests:
   ```powershell
   python -m pytest -v
   ```

6. Start the backend server:
   ```powershell
   python run.py
   ```
   - API Server: `http://127.0.0.1:8000`
   - Interactive Swagger API docs: `http://127.0.0.1:8000/docs`
   - Health Check: `http://127.0.0.1:8000/api/health`

---

### Step 2: Frontend Setup (React + Vite)

1. Open a **second terminal** in the `frontend` folder:
   ```powershell
   cd "C:\final - project\frontend"
   ```

2. Install frontend dependencies:
   ```powershell
   cmd /c npm install
   ```

3. Run linting and production build checks:
   ```powershell
   cmd /c npm run lint
   cmd /c npm run build
   ```

4. Start the frontend development server:
   ```powershell
   cmd /c npm run dev
   ```
   The application will be accessible at: `http://localhost:5173`

---

## 🧪 Testing Summary

The project includes an automated test suite executed via `pytest`:

```powershell
.\backend\venv\Scripts\python.exe -m pytest -v
```

**Test Coverage Highlights:**
1. **Coordinate Validation**: Valid ranges `[-90, 90]` and `[-180, 180]`, identical coordinate rejection.
2. **Configuration Enforcement**: HTTP 503 response when `ORS_API_KEY` is missing with clear setup instructions.
3. **Provider Parsing & Alternatives**:
   - Parses multi-route responses into Leaflet `[lat, lon]` coordinates with stable IDs and color codes.
   - Genuine alternatives handling: never duplicates routes to fake alternatives; honestly flags single-route results.
4. **Failure & Error States**:
   - HTTP 404 (no routable path between points)
   - HTTP 401 (invalid/unauthorized API key)
   - HTTP 429 (rate limit exceeded)
   - HTTP 504 (network / gateway timeout)
5. **Geocoding Service**:
   - Query length validation (minimum 3 characters)
   - Result mapping & empty query handling
   - Rate limit (429) and timeout (504) handling
6. **Environmental Integration (Open-Meteo)** (27 tests total):
   - Route geometry sampling (even spacing, start/end boundary retention)
   - Response parsing for particulate matter (PM2.5, PM10), NO2, and European AQI
   - Strict missing-field validation (asserting nulls are preserved and never silently zero-filled)
   - WMO weather code descriptions and thermal parameter parsing
   - Multi-waypoint route summary aggregation with documented metadata
   - Open-Meteo failure and timeout resilience

---

## ⚖️ Transparent Default Rule

To eliminate user cognitive burden, users do not need to guess numeric weights (e.g., 0.35 air quality vs 0.65 distance):
- **User Preference Driven**: Users select qualitative environmental preferences (Air Quality, Greenery, Thermal Comfort).
- **Default Baseline Rule**: When **no** environmental preferences are selected, the system optimizes exclusively for the **shortest safe walking distance** via designated pedestrian infrastructure.
- **Genuine Alternatives Policy**: If OpenRouteService returns only 1 route (e.g. for simple or isolated corridors), the system displays it honestly without artificial duplication.
