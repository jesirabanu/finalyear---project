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
│   │   │   └── routes.py              # Endpoints: /api/routes, /api/geocode, /api/health
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── coordinates.py         # Bounds-validated coordinate models
│   │   │   ├── routes.py              # Route request/response models & Leaflet coords
│   │   │   └── geocoding.py           # Nominatim result schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── routing_service.py     # OpenRouteService caller & alternative route parser
│   │   │   └── geocoding_service.py   # Rate-limited & cached Nominatim geocoder
│   │   └── algorithm/                 # Multi-criteria preference ranking engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_routes.py             # Route validation, ORS parsing, failure tests
│   │   └── test_geocoding.py          # Geocoding validation, rate limits, error tests
│   ├── requirements.txt               # Python dependencies (FastAPI, httpx, pytest, etc.)
│   ├── .env.example                   # Environment variable template with placeholders
│   ├── .env                           # Local environment settings
│   └── run.py                         # Server startup script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.jsx            # Leaflet map, route polylines, fitBounds & selection
│   │   │   ├── Sidebar.jsx            # Geocoding search, route cards, loading/errors
│   │   │   └── StatusBadge.jsx        # Live backend & integration health monitor
│   │   ├── services/
│   │   │   ├── routingService.js      # Decoupled backend routing API client
│   │   │   └── geocodingService.js    # Decoupled backend geocoding API client
│   │   ├── App.jsx                    # Application state management & interactions
│   │   ├── App.css                    # Responsive styling & route card indicators
│   │   └── main.jsx                   # React entry point
│   ├── package.json
│   └── vite.config.js                 # Vite config with backend API proxy (/api -> :8000)
└── README.md                          # Setup, execution, and testing guide
```

---

## 🛠️ Tech Stack & Services

- **Frontend**: React (Vite), Modern CSS, Lucide Icons
- **Interactive Mapping**: Leaflet (`react-leaflet`) with OpenStreetMap (OSM) Cartographic tiles
- **Backend API**: Python FastAPI, Uvicorn, Pydantic v2, HTTPX
- **Routing Service**: OpenRouteService (ORS) Walking Directions API (`foot-walking`)
- **Geocoding Service**: OpenStreetMap Nominatim (Backend-proxied, rate-limited to 1 req/sec, cached, with custom User-Agent)
- **Unit & Integration Testing**: `pytest`, `pytest-asyncio`, `TestClient`

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

### 3. `GET /api/health`
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

---

## ⚖️ Transparent Default Rule

To eliminate user cognitive burden, users do not need to guess numeric weights (e.g., 0.35 air quality vs 0.65 distance):
- **User Preference Driven**: Users select qualitative environmental preferences (Air Quality, Greenery, Thermal Comfort).
- **Default Baseline Rule**: When **no** environmental preferences are selected, the system optimizes exclusively for the **shortest safe walking distance** via designated pedestrian infrastructure.
- **Genuine Alternatives Policy**: If OpenRouteService returns only 1 route (e.g. for simple or isolated corridors), the system displays it honestly without artificial duplication.
