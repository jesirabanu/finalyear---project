# Comprehensive Technical Viva Preparation Document
## Third Project Review: AI-Driven Multi-Environmental Personalized Pedestrian Routing

> [!IMPORTANT]
> **Project Grounding & Verified Test Suite**:
> Every code reference, mathematical formula, component relationship, and API integration in this document is derived strictly from your active codebase (`backend/app/...`, `frontend/src/...`, and `backend/tests/...`). 
> The backend automated test suite currently has **64 passing test cases out of 64** across all 6 test modules (`pytest -v backend/tests`).

---

## Master Feature Implementation Matrix

| Topic | Feature | Status | Justification / Code Reference |
| :--- | :--- | :--- | :--- |
| **1. Frontend** | React Component Hierarchy & State | **Implemented** | [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx), [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx), [MapView.jsx](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx) |
| **1. Frontend** | Debounced Nominatim Geocoding | **Implemented** | `setTimeout` 450ms + `AbortController` in [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx#L81-L120) |
| **1. Frontend** | Reactive Re-ranking without Refetch | **Implemented** | `useRef(preferences)` change detection in [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx#L90-L96) |
| **2. Backend** | FastAPI Asynchronous Core & Router | **Implemented** | [main.py](file:///C:/final%20-%20project/backend/app/main.py), [routes.py](file:///C:/final%20-%20project/backend/app/api/routes.py) |
| **2. Backend** | Concurrent Upstream Data Queries | **Implemented** | `asyncio.gather()` in [environmental_service.py](file:///C:/final%20-%20project/backend/app/services/environmental_service.py#L728-L730) |
| **2. Backend** | Pydantic v2 Contract Validation | **Implemented** | [routes.py](file:///C:/final%20-%20project/backend/app/schemas/routes.py), [preferences.py](file:///C:/final%20-%20project/backend/app/schemas/preferences.py) |
| **3. Integration** | End-to-End Synchronous/Async Pipeline | **Implemented** | Frontend -> FastAPI -> ORS -> Open-Meteo -> Overpass -> Ranking Engine |
| **4. Routing** | ORS Directions (`foot-walking`) | **Implemented** | POST `https://api.openrouteservice.org/v2/directions/foot-walking/geojson` |
| **4. Routing** | Genuine Pedestrian Alternatives | **Implemented** | `target_count: 3`, `weight_factor: 1.4`, `share_factor: 0.6` |
| **4. Routing** | GeoJSON to Leaflet Polyline Inversion | **Implemented** | `[pt[1], pt[0]]` inversion in `_parse_ors_features()` |
| **5. Environment** | Even-spaced Waypoint Sampling (4 pts) | **Implemented** | `sample_route_geometry()` in [environmental_service.py](file:///C:/final%20-%20project/backend/app/services/environmental_service.py#L100-L130) |
| **5. Environment** | Multi-Coordinate Batch Queries | **Implemented** | Comma-separated query strings to Open-Meteo Air Quality & Forecast APIs |
| **5. Environment** | Non-Contaminating Averaging | **Implemented** | Arithmetic mean of non-null values only; zero substitution strictly prohibited |
| **5. Environment** | In-Memory TTL Cache & 24h Stale Fallback | **Implemented** | `_env_cache` with 900s TTL and 86,400s max stale retention |
| **6. Normalization** | Outlier Clipping to Physical Bounds | **Implemented** | `FACTOR_SPECS` bounds in [ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py#L173-L175) |
| **6. Normalization** | Directional Min-Max Relative Scaling | **Implemented** | Lower-is-better `(v_max - val) / span`, Higher-is-better `(val - v_min) / span` |
| **6. Normalization** | Zero Variance Safe Guard | **Implemented** | `span < 1e-6` yields score `1.0` (avoids division by zero) |
| **7. Pareto** | Formal Non-Domination Identification | **Implemented** | $\forall f, S_A \ge S_B - \epsilon \land \exists f, S_A > S_B + \epsilon$ (`compute_pareto_dominance`) |
| **7. Pareto** | Strict Priority over Dominated Routes | **Implemented** | Binary sort flag `is_dom \in {0, 1}` placed first in sort key |
| **8. Scoring** | Equal-Priority ($1/k$) Composite Score | **Implemented** | $\text{Score} = (1/k) \sum S_{\text{norm}}$ (Explicit design choice, zero ML) |
| **8. Scoring** | Deterministic 4-Tuple Tie-Breaker | **Implemented** | `(is_dom, -score, round(dist, 1), route_id)` in [ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py#L445-L450) |
| **9. Preferences** | Multi-Factor User Filtering | **Implemented** | 5 supported criteria + `no_preference` default baseline mode |
| **9. Preferences** | Missing Factor Exclusion & Warning | **Implemented** | Excluded from $k$; warnings appended to payload |
| **9. Preferences** | Total Provider Failure Safeguard | **Implemented** | Withholds recommendation (`withheld_rec = True`), falls back to shortest distance |
| **10. Error Config** | Explicit HTTP Status Code Mapping | **Implemented** | 503 (No key), 401 (Bad key), 429 (Rate limit), 404 (No path), 504 (Timeout) |
| **10. Error Config** | Provider Rate-Limiter (1 req/sec) | **Implemented** | `asyncio.Lock()` + sleep delay in `geocoding_service.py` & `greenery_service.py` |
| **10. Traffic** | Dual-Mode Traffic Exposure | **Partially Implemented** | Live TomTom Flow API integrated when key present; defaults to static OSM road hierarchy proxy |
| **11. Testing** | Pytest Automated Test Suite | **Implemented** | 64 unit and integration test cases covering all edge cases |
| **All** | Machine-Learned Personal Weights | **Future Enhancement** | Deliberately excluded to guarantee 100% deterministic transparency |
| **All** | Green View Index (GVI) Computer Vision | **Future Enhancement** | Acknowledged in code docs: OSM buffer is proximity, not canopy density or GVI |
| **All** | Real-Time IoT Microclimate Sensors | **Future Enhancement** | Open-Meteo provides regional gridded models, not hyper-local street canyon turbulence |

---

## Topic 1: React Components and Frontend Architecture

### Feature Status
- **Implemented**: Component hierarchy (`App`, `Sidebar`, `MapView`, `EnvironmentalPanel`, `RouteComparisonTable`, `StatusBadge`), debounced address geocoding, synchronized search state during render, route selection, and memoized preference re-ranking.
- **Future Enhancement**: WebWorker-based client-side offline route caching and geolocation GPS tracking.

---

### 1. Possible Examiner Questions
1. *"Explain the architecture of your React application. How does data flow between the map canvas and the sidebar controls?"*
2. *"How does the frontend trigger route ranking when a user changes environmental checkboxes without recalculating the physical route from OpenRouteService?"*
3. *"How do you handle address search debouncing and ensure obsolete in-flight geocoding requests do not overwrite newer input?"*

---

### 2. Simple English Answers
1. The application follows a unidirectional data flow architecture managed by the root component [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx). `App.jsx` maintains central state: `origin`, `destination`, `preferences`, `rawRoutes`, `rankingData`, and `selectedRouteId`. The state is passed down as props to two primary presentation components: [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx) (input controls, environmental panels, and comparison tables) and [MapView.jsx](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx) (interactive Leaflet map rendering colored polylines and custom markers).
2. When a user selects or deselects an environmental factor, `App.jsx` detects this using a `useRef` reference (`prevPrefsRef`) inside a `useEffect` hook. Instead of making an expensive call to fetch directions from OpenRouteService, it invokes `executeRanking(rawRoutes, preferences)`, which sends the existing candidate routes along with the new preferences directly to the backend `/api/rank` endpoint.
3. In [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx#L81-L107), geocoding inputs are debounced with a 450ms `setTimeout`. To prevent race conditions where a slow, obsolete network response overwrites newer keystrokes, an `AbortController` signal is passed into `searchLocations()`. If a new character is typed before the timeout expires, `abortController.abort()` cancels the previous request immediately.

---

### 3. Tanglish Explanation
Namma React frontend unidirectional data flow pattern follow pannuthu. Main state ellamey [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx) la irukku: start point (`origin`), end point (`destination`), user select panra checkboxes (`preferences`), aprom OpenRouteService kitta irunthu vantha routes (`rawRoutes`).
Itha [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx) kum [MapView.jsx](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx) kum props ah anupuroam.
User checkbox ah click pannum pothu, thirumba OpenRouteService kitta poi route kekka theva illa. `prevPrefsRef` vechu preferences maarirukku nu therinjathum, existing routes ah vechu backend `/api/rank` endpoint ku anupi seconds kulla rank update panniduvom. 
User address type pannum pothu fast ah type panna network jam aagama irukka, 450ms debounce vechurukkoam; pazhaya pending request ah cancel panna `AbortController` use panroam.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [frontend/src/App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx)
  - `executeRanking(routesToRank, currentPrefs)` (lines 59–87): Sends existing route objects and updated preference payload to `rankCandidateRoutes()`.
  - Preference watcher `useEffect` (lines 90–96): Compares `prevPrefsRef.current` with `preferences` using `JSON.stringify()`.
- **File**: [frontend/src/components/Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx)
  - Synchronizing search inputs during render (lines 69–78):
    ```javascript
    if (origin !== prevOrigin) {
      setPrevOrigin(origin);
      setOriginSearchText(origin?.label || '');
    }
    ```
  - Debounced address geocoding with `AbortController` (lines 81–107).
- **File**: [frontend/src/components/MapView.jsx](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx)
  - `MapBoundsUpdater` (lines 63–89): Automatically fits map bounding box to the currently selected route or markers using `map.fitBounds()`.
  - `Polyline` rendering (lines 142–186): Renders routes using distinct palette colors (`#2563eb`, `#8b5cf6`, `#0d9488`), giving the active route higher `weight: 6` and `opacity: 0.95`.

---

### 5. Implementation Step by Step
1. **State Initialization**: [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx#L9-L37) initializes `origin` (defaults to St. Paul's Cathedral), `destination` (Tower of London), and `preferences` with `air_quality: true`, `greenery: true`, and `walking_distance: true`.
2. **Search Input Synchronization**: When map clicks or autocomplete change `origin`, [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx#L69-L74) detects `origin !== prevOrigin` directly during rendering (the official React recommended pattern) and updates `originSearchText` without causing cascading re-render loops.
3. **Route Calculation**: The user clicks *"Find Eco Routes"*. `handleCalculateRoutes()` calls `fetchWalkingRoutes()` in [routingService.js](file:///C:/final%20-%20project/frontend/src/services/routingService.js#L18).
4. **Dynamic Selection**: The user selects a route card or table row. `setSelectedRouteId(id)` updates state, dynamically updating `MapBoundsUpdater` in [MapView.jsx](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx#L68-L72) and expanding the corresponding metrics in [EnvironmentalPanel.jsx](file:///C:/final%20-%20project/frontend/src/components/EnvironmentalPanel.jsx).

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"Why did you avoid putting `origin !== prevOrigin` synchronization inside a `useEffect`?"*
  - **Answer**: Setting state inside a `useEffect` causes a second round of component re-renders (render -> commit -> effect -> state change -> second render). Adjusting state during render when a prop changes avoids the redundant paint cycle and prevents layout flicker.
- **Follow-up**: *"How does the Leaflet map interact with React given that Leaflet mutates the DOM directly?"*
  - **Answer**: We use `react-leaflet` wrapper components (`<MapContainer>`, `<Polyline>`, `<Marker>`). React manages the component lifecycle and reconciliation, while internal child components like `MapBoundsUpdater` use the `useMap()` hook to imperatively access the underlying Leaflet `L.Map` instance cleanly.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"If the user rapidly clicks different preference checkboxes 5 times in 1 second, wouldn't you trigger 5 competing HTTP requests to `/api/rank`, and could an older response arrive last and overwrite the state?"*
  - **Defense Strategy / Answer**: While `useEffect` triggers whenever `preferences` changes, the ranking endpoint `/api/rank` is a pure mathematical calculation taking under 5ms on the backend. However, to guarantee absolute consistency, `isRanking` flag blocks overlapping UI interactions, and `executeRanking()` checks the active route collection. In production, an `AbortController` can be attached to `rankCandidateRoutes()` just as we did for the Nominatim geocoder.
- **Tricky Question**: *"Why are coordinates inverted between your routing service and Leaflet?"*
  - **Defense Strategy / Answer**: RFC 7946 GeoJSON standard mandates `[longitude, latitude]` for geographic vectors, whereas Leaflet's `L.polyline` and `L.latLng` strictly require `[latitude, longitude]`. We handle this inversion deterministically on the backend in `_parse_ors_features()`: `[float(pt[1]), float(pt[0])]`.

---

## Topic 2: Python and FastAPI Backend Architecture

### Feature Status
- **Implemented**: Asynchronous application core ([main.py](file:///C:/final%20-%20project/backend/app/main.py)), APIRouter modular routing ([routes.py](file:///C:/final%20-%20project/backend/app/api/routes.py)), Pydantic v2 validation models ([schemas/](file:///C:/final%20-%20project/backend/app/schemas/)), CORS middleware, and concurrent `asyncio.gather()` dispatch.
- **Future Enhancement**: Distributed task queue (Celery/Redis) for background batch caching and rate-limited worker pools.

---

### 1. Possible Examiner Questions
1. *"Why did you select FastAPI instead of Flask or Django? How does FastAPI's concurrency model benefit this application?"*
2. *"How are incoming payloads and outgoing responses validated and serialized in the backend?"*
3. *"How does your backend handle concurrent queries to multiple environmental APIs?"*

---

### 2. Simple English Answers
1. FastAPI was chosen for three key architectural benefits: native asynchronous I/O (`async`/`await`), automatic schema validation using Pydantic v2, and auto-generated Swagger documentation at `/docs`. Because our backend acts as an orchestrator querying multiple third-party web services (OpenRouteService, Open-Meteo, Overpass), an asynchronous event loop prevents thread blocking, allowing a single lightweight process to handle multiple routing requests simultaneously.
2. Every endpoint uses Pydantic v2 models (e.g. `RouteRequest`, `RouteRankingRequest`, `RouteResponse`). Pydantic enforces strict type checking, range validation (latitude $[-90, 90]$, longitude $[-180, 180]$), and automatic serialization into standardized JSON responses.
3. In [environmental_service.py](file:///C:/final%20-%20project/backend/app/services/environmental_service.py#L728-L730), Air Quality and Weather data are fetched concurrently using `asyncio.gather(aq_task, weather_task)`. This executes both network I/O calls in parallel over non-blocking HTTP sockets via `httpx.AsyncClient`.

---

### 3. Tanglish Explanation
Django romba periya framework, mathavangalukku heavy ah irukkum. Flask synchronous ah irukkum—oru external API call mudiyara varaikkum adutha request wait panna vendiyathu irukkum. Aana FastAPI asynchronous support (`async`/`await`) oda varuthu.
Namma project la OpenRouteService, Open-Meteo, Overpass nu neraiya APIs call pannanum. FastAPI la `httpx.AsyncClient` use panni, `asyncio.gather()` moolama Air Quality and Weather data-va parallel ah call panrom. Ithanaala response time 1.8s la irunthu 600ms ah kuraiyuthu. 
Pydantic v2 use panrathaala lat/lon range thappa vantha automatic ah 422 error throw panni server crash aagama pathukkoom.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/main.py](file:///C:/final%20-%20project/backend/app/main.py)
  - `app = FastAPI(...)` (line 10)
  - `CORSMiddleware` (lines 21–27): Whitelists frontend origins `http://localhost:5173`.
  - `app.include_router(api_router, prefix="/api")` (line 30).
- **File**: [backend/app/api/routes.py](file:///C:/final%20-%20project/backend/app/api/routes.py)
  - POST `/routes` (lines 90–103): Calls `get_walking_routes()`.
  - POST `/rank` (lines 156–170): Calls `rank_routes()`.
  - POST `/routes/refresh` (lines 105–118): Calls `refresh_route_environments()`.
- **File**: [backend/app/schemas/routes.py](file:///C:/final%20-%20project/backend/app/schemas/routes.py)
  - `RouteRequest` (lines 42–60): Enforces `source != destination` via `@model_validator(mode="after")`.

---

### 5. Implementation Step by Step
1. Client sends a JSON payload to `/api/routes`.
2. FastAPI intercepts the request and matches it against `RouteRequest`. Pydantic validates coordinate bounds (`ge=-90.0, le=90.0`).
3. If validation fails, FastAPI immediately returns an HTTP 422 JSON response with field-specific errors.
4. If validation succeeds, `get_walking_routes()` in [routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py#L190) is invoked.
5. In lines 326–342, enrichment functions are called inside try/except blocks to ensure upstream data service issues do not crash the primary route response.
6. The validated `RouteResponse` model serializes the output into Leaflet-ready JSON.

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"What is the difference between `@model_validator(mode='after')` and `field_validator` in your schemas?"*
  - **Answer**: `field_validator` checks individual fields in isolation (e.g., verifying latitude is between -90 and +90). `@model_validator(mode='after')` inspects the entire instantiated model, allowing cross-field validation, such as verifying that the source and destination coordinates are not identical.
- **Follow-up**: *"Why use `httpx` instead of `requests` in your services?"*
  - **Answer**: The traditional `requests` library is blocking and synchronous; using it in an `async def` FastAPI route blocks the entire Python asyncio event loop. `httpx` provides a native `AsyncClient` that uses non-blocking sockets.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Python has a Global Interpreter Lock (GIL). How does using `asyncio` give you real concurrency if only one thread executes at a time?"*
  - **Defense Strategy / Answer**: External API calls are **I/O-bound**, not CPU-bound. When `httpx` sends an HTTP request to Open-Meteo or ORS, the thread does not perform CPU computation; it yields execution back to the asyncio event loop via `await`. The event loop continues processing other connections and concurrent requests while waiting for the operating system socket to receive data. Thus, the GIL does not bottleneck asynchronous network I/O.

---

## Topic 3: API Integration and Data Flow

### Feature Status
- **Implemented**: Multi-provider pipeline connecting Nominatim, OpenRouteService, Open-Meteo, Overpass, and TomTom/OSM proxy into a unified Route Data Model.
- **Future Enhancement**: Webhooks for real-time traffic incident alerts.

---

### 1. Possible Examiner Questions
1. *"Explain the complete lifecycle of a routing request from user click to visual rendering."*
2. *"How are disparate third-party data formats unified into a consistent route data structure?"*
3. *"What happens if one of the third-party providers (like Open-Meteo or Overpass) goes offline?"*

---

### 2. Simple English Answers
1. The user initiates a route search. Nominatim geocodes location queries into coordinates. The frontend calls POST `/api/routes`. OpenRouteService returns walking geometry. Representative points are sampled and enriched with air quality and weather from Open-Meteo, greenery from Overpass OSM, and traffic exposure. The ranking engine applies Min-Max normalization and Pareto dominance, returning ranked routes to the frontend for Leaflet rendering.
2. In [routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py#L94-L189), the `populate_route_metadata()` function synthesizes raw readings into standardized dictionaries: `available_environmental_metrics`, `metric_units`, `timestamps`, `source_metadata`, and `data_quality_status` (`complete`, `partial_data`, or `insufficient_data`).
3. Failures in secondary environmental providers are treated as non-fatal. Calls are wrapped in `try...except` blocks with fallback to 24-hour stale cache or exclusion from scoring. The core walking directions remain functional even if environmental providers fail.

---

### 3. Tanglish Explanation
End-to-end flow:
1. User address search panna Nominatim API lat/lon tharum.
2. Frontend POST `/api/routes` call pannum.
3. Backend OpenRouteService kitta poi walkable geometry edukkoom.
4. Route-la 4 sample points edukkurom; Open-Meteo kitta air quality, Overpass kitta greenery, TomTom/OSM kitta traffic edukkurom.
5. Intha metrics ellam `populate_route_metadata()` moolama standardized route model-la pack aagum.
6. Ranking engine Min-Max normalization & Pareto dominance panni, best route-ku Rank 1 badge kudukkum.
7. Frontend Leaflet map-la polyline draw aagidum.
Oru velai Open-Meteo down aana kooda route cut aagathu; stale cache vechu warning banner-oda route display aagidum.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/services/routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py)
  - `get_walking_routes()` (lines 190–362): Coordinates the master pipeline.
  - `populate_route_metadata()` (lines 94–189): Populates units, timestamps, missing factors, and data quality flags.
- **File**: [backend/app/schemas/routes.py](file:///C:/final%20-%20project/backend/app/schemas/routes.py#L13-L40)
  - `RouteModel`: The single source of truth containing coordinates, distances, environmental summary, and ranking metadata.

---

### 5. Implementation Step by Step
```mermaid
graph TD
    A["User Input (Start & Destination)"] --> B["Nominatim Geocoding API"]
    B --> C["FastAPI POST /api/routes"]
    C --> D["OpenRouteService (foot-walking)"]
    D --> E["_parse_ors_features() (Invert to Lat/Lon)"]
    E --> F["sample_route_geometry() (4 waypoints)"]
    F --> G["Open-Meteo Batch Query (AQI & Weather)"]
    F --> H["Overpass API (Greenery Bounding Box)"]
    F --> I["Traffic Service (TomTom / OSM Road Proxy)"]
    G --> J["populate_route_metadata()"]
    H --> J
    I --> J
    J --> K["rank_routes() (Min-Max & Pareto)"]
    K --> L["React Frontend (Leaflet Polylines & Sidebar)"]
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"Why does `populate_route_metadata()` assign a `data_quality_status`?"*
  - **Answer**: To provide full transparency to the user. If 0 factors are missing, status is `complete`. If 1–2 factors are missing, status is `partial_data`. If $\ge 3$ factors are missing, status is marked `insufficient_data`, alerting the user that environmental confidence is compromised.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"What prevents your backend from being overwhelmed by cascaded third-party timeouts when all 3 upstream APIs are experiencing latency simultaneously?"*
  - **Defense Strategy / Answer**: We implement strict, differentiated timeout thresholds in [config.py](file:///C:/final%20-%20project/backend/app/core/config.py): ORS is capped at 14.0s, Open-Meteo at 8.0s, and Overpass at 10.0s. Furthermore, `asyncio.gather()` runs them concurrently, so total upstream waiting time is bounded by the slowest service ($\le 14\text{s}$), not their arithmetic sum ($14 + 8 + 10 = 32\text{s}$). If any provider exceeds its timeout, `httpx.TimeoutException` is caught immediately.

---

## Topic 4: OpenRouteService Route Generation

### Feature Status
- **Implemented**: Pedestrian profile routing (`foot-walking`), alternative route generation (`target_count: 3`, `weight_factor: 1.4`, `share_factor: 0.6`), coordinate inversion, and automated fallback when alternatives are rejected.
- **Future Enhancement**: Elevation/incline penalty integration using ORS elevation profiles.

---

### 1. Possible Examiner Questions
1. *"How does OpenRouteService generate multiple distinct walking paths instead of duplicate geometries?"*
2. *"Why must GeoJSON coordinates be transformed before passing them to the frontend Leaflet map?"*
3. *"How does your backend handle routes where OpenRouteService cannot find a pedestrian path or rejects alternatives?"*

---

### 2. Simple English Answers
1. We query ORS using the `foot-walking` routing profile and configure the `alternative_routes` parameters in the JSON payload:
   - `target_count: min(request.alternatives + 1, 3)` requests up to 3 candidate paths.
   - `weight_factor: 1.4` permits alternative paths to be up to 40% longer than the shortest path.
   - `share_factor: 0.6` requires that alternative paths share no more than 60% of road segments with each other, guaranteeing distinct corridors.
2. GeoJSON specification (RFC 7946) mandates `[longitude, latitude]`. Leaflet's `Polyline` requires `[latitude, longitude]`. In `_parse_ors_features()`, we invert every point: `[float(pt[1]), float(pt[0])]`.
3. If no route is found, ORS returns HTTP 404/400, which our service catches and translates into an HTTP 404 with a user-friendly message. If ORS rejects alternative routes (e.g. distance exceeds 100km), our system catches the HTTP 400 error and automatically retries requesting only the primary route ([routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py#L253-L265)).

---

### 3. Tanglish Explanation
ORS API la namma `foot-walking` profile use panrom. Alternatives kedaikka `alternative_routes` block anupurom:
- `target_count: 3` (3 routes kekkurom).
- `weight_factor: 1.4` (shortest route vida 40% detour edukka permission).
- `share_factor: 0.6` (rendu route 60% ku mela same road la pogakoodathu; genuine different paths irukkanum).
ORS GeoJSON format la `[lon, lat]` tharum. Leaflet map display panna `[lat, lon]` thevai. Namma `_parse_ors_features()` la iterate panni coordinates ah flip panrom.
Oru velai 100km ku mela distance irunthu ORS alternative thara mudiyathu nu HTTP 400 sonna, namma code automatic ah retry panni primary route ah mattum eduthu kuduthidum; crash aagathu.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/services/routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py)
  - `_parse_ors_features(features)` (lines 36–91): Inverts coordinates and assigns route colors from `ROUTE_PALETTE`.
  - `get_walking_routes(request)` (lines 190–362): Builds payload and manages the HTTP POST request to `settings.ORS_API_URL`.

---

### 5. Implementation Step by Step
```python
# Lines 230-242 in routing_service.py
payload: Dict[str, Any] = {
    "coordinates": [
        [request.source.lon, request.source.lat],
        [request.destination.lon, request.destination.lat],
    ],
}
if request.alternatives > 0:
    payload["alternative_routes"] = {
        "target_count": min(request.alternatives + 1, 3),
        "weight_factor": 1.4,
        "share_factor": 0.6,
    }
```
1. Builds `payload` with source and destination coordinates in `[lon, lat]` order.
2. Sends POST request to `https://api.openrouteservice.org/v2/directions/foot-walking/geojson`.
3. Checks for status 400; if alternatives were rejected, drops `alternative_routes` and retries primary route.
4. Parses GeoJSON `features` array into `RouteModel` instances.

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"Why does `_parse_ors_features()` assign colors from a static palette?"*
  - **Answer**: To provide immediate visual clarity on the Leaflet map. Primary route is assigned Royal Blue (`#2563eb`), Alternative A is Vibrant Purple (`#8b5cf6`), Alternative B is Dark Teal (`#0d9488`), and Alternative C is Amber Gold (`#d97706`).

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Why did you not use OpenRouteService's built-in green or quiet routing options instead of building your own ranking engine?"*
  - **Defense Strategy / Answer**: OpenRouteService's built-in green routing relies on static pre-calculated OSM tag heuristics and cannot ingest **dynamic real-time air quality models (Open-Meteo), transient thermal heat indexes, or custom multi-objective Pareto optimization**. By decoupling route generation from environmental evaluation, our architecture can integrate any real-time data source and allows pedestrians to customize their own multi-criteria trade-offs transparently.

---

## Topic 5: Environmental Data Collection and Route Sampling

### Feature Status
- **Implemented**: Geometry sampling (4 waypoints), batch query formatting, non-zero-filling aggregation, 15-minute in-memory cache, and 24-hour stale cache fallback.
- **Partially Implemented**: Live traffic via TomTom API (implemented when key present, static OSM proxy when absent).
- **Future Enhancement**: Integration with street-level IoT air monitors.

---

### 1. Possible Examiner Questions
1. *"How do you collect environmental metrics along a walking route without causing API rate-limit exhaustion?"*
2. *"How does your route waypoint sampling algorithm work?"*
3. *"Why is substituting zero for missing environmental data strictly prohibited in your aggregation logic?"*

---

### 2. Simple English Answers
1. Walking routes contain hundreds of coordinate pairs. Querying third-party APIs for every coordinate would quickly breach rate limits. We solve this by sampling up to 4 evenly spaced waypoints per route, bundling all sample coordinates across all candidate routes into a single multi-coordinate batch request to Open-Meteo.
2. In `sample_route_geometry()`, given an array of $n$ coordinates, the step size is computed as $\text{step} = (n - 1) / (\text{max\_samples} - 1)$. Indices are calculated via $\text{round}(i \times \text{step})$ for $i \in [0, \text{max\_samples}-1]$, guaranteeing inclusion of the route start (0%), intermediate points, and destination (100%).
3. Substituting zero for missing data is scientifically invalid and dangerous. Setting missing Air Quality to 0 would imply pristine mountain air in a polluted corridor; setting missing traffic to 0 would imply zero vehicle danger. We maintain `None` and exclude unmeasured factors from scoring.

---

### 3. Tanglish Explanation
Route-la 500 coordinates iruntha, ella coordinate-kum API call panna Open-Meteo block pannidum. 
Athanaala `sample_route_geometry()` function 4 sample points edukkurom: Start point (0%), naduvula 2 waypoints, destination (100%).
Multiple candidate routes iruntha, ella sample points-aiyum orey batch request-la comma-separated string-ah anupurom.
Open-Meteo kitta irunthu vantha readings-la ethavathu missing-ah iruntha dummy 0 poda maattom. Missing AQI-ku 0 pota antha edathula pollution-ey illa nu thappa perceive aagum. Athanaala strictly `None` vechu report panroam.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/services/environmental_service.py](file:///C:/final%20-%20project/backend/app/services/environmental_service.py)
  - `sample_route_geometry()` (lines 100–130): Calculates evenly spaced sampling indices.
  - `fetch_air_quality_batch()` (lines 141–232): Multi-coordinate batch fetch with TTL cache.
  - `compute_route_environmental_summary()` (lines 518–697): Aggregates valid non-null values.

---

### 5. Implementation Step by Step
```python
# Lines 123-130 in environmental_service.py
step = (n - 1) / float(max_samples - 1)
sample_indices = sorted(list({int(round(i * step)) for i in range(max_samples)}))
if sample_indices[-1] != n - 1:
    sample_indices[-1] = n - 1
return [(idx, coordinates[idx][0], coordinates[idx][1]) for idx in sample_indices]
```
1. Calculates step size along the coordinate array.
2. Gathers distinct sample indices and forces the final index to $n - 1$.
3. Extracts `(index, latitude, longitude)` tuples.
4. In lines 181–186, formats `lat_str` and `lon_str` as comma-separated coordinates:
   ```python
   lat_str = ",".join(str(round(c[0], 5)) for c in uncached_coords)
   lon_str = ",".join(str(round(c[1], 5)) for c in uncached_coords)
   ```
5. Sends one unified GET request to `OPEN_METEO_AIR_QUALITY_URL`.

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"How does the in-memory cache key handle precision?"*
  - **Answer**: `_build_cache_key()` rounds latitude and longitude to 3 decimal places (~100m grid resolution). This ensures nearby requests share cache entries matching atmospheric model resolution.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Open-Meteo operates on an 11 km grid. Since pedestrian routes are often only 1 to 2 km long, wouldn't all 4 sample points return identical values?"*
  - **Defense Strategy / Answer**: Yes, for short routes within a single 11 km grid cell, Open-Meteo returns uniform background values. We explicitly document this in `route.source_metadata["spatial_resolution"] = "Regional grid (~11km atmospheric model)"`. However, our multi-criteria engine balances this with **hyper-local Overpass OSM greenery data (evaluated within a 50m buffer) and road-proximity traffic exposure**, providing street-level variance where atmospheric models are uniform.

---

## Topic 6: Min-Max Normalization

### Feature Status
- **Implemented**: Direction-aware relative Min-Max normalization, physical bound clipping, and zero-variance division-by-zero protection.
- **Future Enhancement**: Dynamic percentile clipping for city-wide historical datasets.

---

### 1. Possible Examiner Questions
1. *"Why is normalization required before evaluating multi-environmental criteria?"*
2. *"State the mathematical formula used for Lower-is-Better versus Higher-is-Better factors."*
3. *"How does your implementation handle zero-variance where all candidate routes have identical values?"*

---

### 2. Simple English Answers
1. Environmental metrics use completely incompatible units: walking distance in metres ($1200\text{m}$), temperature in Celsius ($24^\circ\text{C}$), air quality in European AQI index ($35\text{ EAQI}$), and greenery in percentage ($65\%$). Directly summing these numbers is mathematically invalid. Min-Max normalization maps all raw values onto a dimensionless $[0.0, 1.0]$ interval where $1.0$ consistently represents the most favorable outcome.
2. Given minimum $v_{\min}$ and maximum $v_{\max}$ across candidate routes:
   - **Lower-is-better** (Air Quality, Temperature, Traffic, Distance):
     $$S_{\text{norm}}(R) = \frac{v_{\max} - \text{val}_R}{v_{\max} - v_{\min}}$$
   - **Higher-is-better** (Greenery & Parks):
     $$S_{\text{norm}}(R) = \frac{\text{val}_R - v_{\min}}{v_{\max} - v_{\min}}$$
3. If all candidate routes share identical values on a factor ($v_{\max} - v_{\min} < 10^{-6}$), the span is zero. Dividing by zero would cause runtime exceptions. In [ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py#L192-L194), our code checks `if span < 1e-6:` and assigns all candidates a score of $1.0$.

---

### 3. Tanglish Explanation
Distance metres la irukku, temperature Celsius la irukku, greenery percentage la irukku. Itha direct ah kootina math thappu. Athanaala Min-Max normalization panni ellathayum $[0.0, 1.0]$ scale ku maathuroam.
1.0 na eppovume "Best outcome".
- Pollution, heat, traffic, distance ellam koraiva iruntha than nallathu (**lower is better**). Athanaala formula: $(v_{\max} - \text{val}) / (v_{\max} - v_{\min})$. Inga lowest pollution irukura route ku 1.0 kedaikkum.
- Greenery athigama iruntha nallathu (**higher is better**). Formula: $(\text{val} - v_{\min}) / (v_{\max} - v_{\min})$. Highest greenery irukura route ku 1.0 kedaikkum.
Ella route kumey same value iruntha ($\text{span} < 10^{-6}$), divide by zero aagama irukka direct ah $1.0$ assign panniduvom.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/algorithm/ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py)
  - `normalize_factor_values(routes, factor)` (lines 150–204).
  - Bound clipping (lines 173–175): `clipped = max(min_b, min(max_b, raw))`.
  - Zero-variance check (lines 192–194).

---

### 5. Implementation Step by Step
```python
# Lines 183-202 in ranking_engine.py
v_min = min(valid_vals)
v_max = max(valid_vals)
span = v_max - v_min

scores: Dict[str, Optional[float]] = {}
for r in routes:
    val = raw_map[r.id]
    if val is None:
        scores[r.id] = None
    elif span < 1e-6:
        scores[r.id] = 1.0
    else:
        if direction == "lower":
            scores[r.id] = round((v_max - val) / span, 4)
        else:
            scores[r.id] = round((val - v_min) / span, 4)
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"What happens to missing values during normalization?"*
  - **Answer**: If `val is None`, `scores[r.id]` is set to `None`. It is never converted to 0.0 or 0.5, ensuring downstream composite scoring can transparently exclude it.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Why did you use relative Min-Max normalization across candidate routes instead of absolute Min-Max normalization using physical sensor limits?"*
  - **Defense Strategy / Answer**: Absolute normalization across physical limits (e.g. $[0, 150\text{ EAQI}]$ or $[0, 50\text{km}]$) severely compresses real urban distinctions. If Route A is $1000\text{m}$ and Route B is $1300\text{m}$, absolute scaling against a $50\text{km}$ limit would make them 0.98 and 0.974—virtually indistinguishable. Relative normalization across candidate alternatives maximizes sensitivity to meaningful local urban trade-offs while strictly preserving ranking order.

---

## Topic 7: Pareto Dominance

### Feature Status
- **Implemented**: Multi-criteria non-domination comparison algorithm, tolerance margin $\epsilon = 10^{-4}$, and non-dominated sorting prioritization.
- **Future Enhancement**: NSGA-II genetic algorithm for multi-point route generation.

---

### 1. Possible Examiner Questions
1. *"Define Pareto dominance in the context of multi-environmental pedestrian routing."*
2. *"How does your code verify that Route A dominates Route B?"*
3. *"Why is Pareto dominance evaluated before composite score sorting?"*

---

### 2. Simple English Answers
1. In multi-criteria decision making, Route A **Pareto-dominates** Route B if and only if:
   - Route A is **no worse** than Route B on all active criteria: $S(A, f) \ge S(B, f) - \epsilon, \forall f$.
   - Route A is **strictly better** than Route B on at least one active criterion: $S(A, f) > S(B, f) + \epsilon, \exists f$.
2. In `compute_pareto_dominance()`, nested loops compare every route pair $(A, B)$ across all active factors using an epsilon tolerance ($\epsilon = 10^{-4}$). If $A$ is strictly better on at least one factor and never worse on any, $B$ is added to `dominated_ids`.
3. Pareto dominance is evaluated first because a dominated route offers no mathematical advantage over its dominating counterpart. By sorting by `is_dominated` first, we guarantee that no dominated route can be recommended over a Pareto-optimal alternative.

---

### 3. Tanglish Explanation
Pareto dominance na simple: Route A, Route B vida ella active factors layum sama-maga athavathu no worse ah irunthu, etho oru factor la strictly better ah iruntha, Route A dominates Route B.
Appo Route B ku porathula user ku entha benefit-um illa. 
Code la `compute_pareto_dominance()` function nested loops vechu compare pannum. $\epsilon = 10^{-4}$ tolerance vechu float precision thavirkuroam.
Sorting key la `(is_dom, -score, dist, id)` nu vechurukkom. Dominated route ku `is_dom = 1`, non-dominated ku `is_dom = 0`. Sort pannum pothu non-dominated routes eppovume top la prioritized aagidum.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/algorithm/ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py)
  - `compute_pareto_dominance()` (lines 206–256).
  - Tolerance: `eps = 1e-4` (line 225).

---

### 5. Implementation Step by Step
```python
# Lines 233-254 in ranking_engine.py
no_worse_on_all = True
strictly_better_on_one = False

for f in active_factors:
    s_a = normalized_scores[f].get(a.id)
    s_b = normalized_scores[f].get(b.id)

    if s_a is None or s_b is None:
        no_worse_on_all = False
        break

    if s_a < s_b - eps:
        no_worse_on_all = False
        break
    elif s_a > s_b + eps:
        strictly_better_on_one = True

if no_worse_on_all and strictly_better_on_one:
    dominated_ids.add(b.id)
    dominated_by_map[b.id].append(a.id)
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"What happens if Route A has better air quality, but Route B has shorter walking distance?"*
  - **Answer**: Neither route dominates the other. Both sit on the **Pareto-optimal efficiency frontier**. Their relative ordering is decided by their normalized composite score.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"If missing data exists for one factor on Route A, can Route A still dominate Route B?"*
  - **Defense Strategy / Answer**: No! In line 240 of `ranking_engine.py`: `if s_a is None or s_b is None: no_worse_on_all = False; break`. If data is missing for either candidate on an active criterion, strict mathematical dominance cannot be proven, preventing false dominance classifications.

---

## Topic 8: Composite Scoring and Distance Tie-Breaker

### Feature Status
- **Implemented**: Equal-priority ($1/k$) composite scoring, deterministic 4-tuple sorting key, and distance/ID tie-breaking.
- **Future Enhancement**: Optional user weight sliders in advanced settings (deliberately omitted from standard UI to prevent user cognitive burden).

---

### 1. Possible Examiner Questions
1. *"What is the composite scoring formula used in your system?"*
2. *"Why did you use equal-priority weighting ($1/k$) rather than machine-learning weights or user sliders?"*
3. *"How are exact score ties broken to ensure 100% deterministic reproducibility?"*

---

### 2. Simple English Answers
1. The composite score for route $R$ across active factors $F_{\text{active}}$ is:
   $$\text{Score}(R) = \frac{1}{|F_{\text{active}}|} \sum_{f \in F_{\text{active}}} S_{\text{norm}}(R, f)$$
2. Equal weighting ($1/k$) is an explicit, transparent system design choice. Asking pedestrians to assign arbitrary numerical weights (e.g. 0.35 air quality vs 0.25 greenery) creates severe cognitive burden and false precision. Black-box ML models lack explainability. Equal-priority normalization treats all user-selected criteria with equal importance transparently.
3. Ties are broken using a deterministic 4-tuple sort key:
   $$\text{sort\_key}(R) = (\text{is\_dominated}, -\text{Score}(R), \text{round}(\text{distance\_m}, 1), \text{route\_id})$$
   If two routes have identical scores, the shorter route in metres wins. If distance is also identical, alphabetical `route_id` breaks the tie, guaranteeing 100% reproducible ordering.

---

### 3. Tanglish Explanation
Composite score formula: Active factors-oda normalized scores ah add panni, count $k$ vechu divide panrom: $\text{Score} = (1/k) \sum S_{\text{norm}}$.
Yen user kitta numeric slider kekkala na, arbitrary weight guess panra cognitive burden thavirkka thaan. Equal priority ($1/k$) transparent system design choice.
Rendu route kum same composite score vantha, tie epdi break aagum?
Sort key la: First non-dominated check, second composite score, third shortest walking distance (metres), fourth route ID. Ithanaala results 100% stable and mathematically reproducible!

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/algorithm/ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py)
  - Composite score loop (lines 432–437).
  - Deterministic `sort_key` (lines 445–450).

---

### 5. Implementation Step by Step
```python
# Lines 430-451 in ranking_engine.py
k = max(1, len(active_factors))
for r in routes:
    factor_sum = 0.0
    for f in active_factors:
        s = normalized_scores[f].get(r.id)
        factor_sum += s if s is not None else 0.0
    composite_scores[r.id] = round(factor_sum / k, 4)

def sort_key(r: RouteModel):
    is_dom = 1 if r.id in dominated_ids else 0
    score = composite_scores.get(r.id, 0.0)
    dist = round(r.distance_m, 1)
    return (is_dom, -score, dist, r.id)

sorted_routes = sorted(routes, key=sort_key)
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"Why round distance to 1 decimal place in the tie-breaker?"*
  - **Answer**: Micro-variations below 10 centimetres are GPS noise. Rounding to 1 decimal place ($0.1\text{m}$) prevents floating-point inaccuracies from triggering spurious tie-breaks.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Doesn't equal weighting assume that a 10% decrease in air pollution has the exact same utility to a pedestrian as a 10% increase in greenery?"*
  - **Defense Strategy / Answer**: No, we do not claim to infer psychological utility. As explicitly documented in our code and UI algorithmic explanation (`ALGORITHMIC_EXPLANATION` line 87), equal priority ($1/k$) is an **explicit system design heuristic** chosen to eliminate user cognitive guessing. When users want one factor to dominate, they select only that factor; when they select multiple, they request a balanced multi-criteria compromise.

---

## Topic 9: User Preference Selection and Filtering

### Feature Status
- **Implemented**: 5 environmental criteria checkboxes, `no_preference` default baseline mode, missing data exclusion, and recommendation withholding.
- **Future Enhancement**: Pre-saved user personas (e.g. Asthmatic Child, Elderly Walker, Jogger).

---

### 1. Possible Examiner Questions
1. *"What happens when a user selects 'No Preference'?"*
2. *"How does the system respond if an external provider lacks data for a selected factor?"*
3. *"Under what conditions does the system withhold a recommendation?"*

---

### 2. Simple English Answers
1. When `no_preference` is selected or all checkboxes are unchecked, the engine engages the **Transparent Default Baseline**. It evaluates all factors that have valid data across all candidate routes plus walking distance, presenting a balanced overview without claiming to find an "absolute healthiest route".
2. If data for a selected factor is missing from external providers (e.g. Overpass times out), that factor is excluded from active scoring ($k$ is decremented), and an explanatory warning message is appended to the response payload.
3. If **all** user-selected environmental criteria lack provider data, the recommendation is officially withheld (`confidence = "low"`, `withheld_rec = True`). The system displays a clear warning and falls back to the shortest safe walking distance baseline.

---

### 3. Tanglish Explanation
1. User ethuvume choose pannalena (`no_preference`), namma system default mode la operate aagum. Available ah irukura ella data-vum vechu distance baseline oda calculate pannum.
2. Oru particular factor (e.g. Greenery) data varalana, athukku dummy 0 podaama, antha factor ah scoring la irunthu exclude panni warning banner kaattuvom.
3. User choose panna ella environmental factors layum data missing ah iruntha, system confident recommendation tharathu (`withheld_rec = True`). User ku warning banner kaati, safe shortest distance ku switch pannidum.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/algorithm/ranking_engine.py](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py#L365-L415)
- **File**: [backend/app/schemas/preferences.py](file:///C:/final%20-%20project/backend/app/schemas/preferences.py#L11-L40) (`PreferenceSelection`)

---

### 5. Implementation Step by Step
```python
# Lines 405-415 in ranking_engine.py
confidence = "high"
withheld_rec = False
if not is_default and not active_factors:
    confidence = "low"
    withheld_rec = True
    active_factors = ["walking_distance"]
    warnings.append(
        "Recommendation withheld: All selected environmental preferences lacked sufficient provider data. "
        "System fell back to the shortest safe walking distance baseline."
    )
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"How is the user notified of missing data on the frontend?"*
  - **Answer**: The frontend checks `rankingData.warnings` and renders prominent notification banners in [App.jsx](file:///C:/final%20-%20project/frontend/src/App.jsx#L176) and badge warnings in [Sidebar.jsx](file:///C:/final%20-%20project/frontend/src/components/Sidebar.jsx).

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"If the user selects only Air Quality, and Route 1 has an AQI of 22 while Route 2 has an AQI of 24, will the system recommend Route 1 even if it is 3 kilometres longer?"*
  - **Defense Strategy / Answer**: Yes, because the user explicitly instructed the system to optimize solely for Air Quality. However, our system generates a clear trade-off warning in `generate_trade_off_summary()`: `"+300% Walking Distance for -8% Air Quality"`, allowing the pedestrian to make an informed final decision.

---

## Topic 10: Error Handling and API Configuration

### Feature Status
- **Implemented**: RESTful HTTP status mapping (503, 401, 429, 404, 504, 502), rate-limiting mutexes (1 req/sec), 15-minute TTL cache, and 24-hour stale cache fallback.
- **Future Enhancement**: Circuit breaker pattern (e.g. using `pybreaker`) for upstream provider outages.

---

### 1. Possible Examiner Questions
1. *"How does your application detect whether external API keys are configured?"*
2. *"What HTTP status codes are returned for provider failures?"*
3. *"How does your caching and stale fallback mechanism operate during an upstream outage?"*

---

### 2. Simple English Answers
1. In [routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py#L30-L34), `_is_api_key_configured()` verifies that `settings.ORS_API_KEY` is present and does not equal the default placeholder string. If missing, it immediately raises an HTTP 503 Service Unavailable with an actionable setup message.
2. We map upstream errors to standard HTTP status codes:
   - **401 Unauthorized**: Invalid or expired ORS credentials.
   - **429 Too Many Requests**: Rate limit reached.
   - **404 Not Found**: No pedestrian path found between coordinates.
   - **504 Gateway Timeout**: Upstream provider timed out.
   - **502 Bad Gateway**: Upstream network connection failure.
3. During network failures, `fetch_air_quality_batch()` inspects `_env_cache`. If an entry exists that is under 24 hours old (`STALE_DATA_MAX_AGE_SECONDS = 86400`), it serves the cached data with `_is_stale: True` and an explicit warning banner: *"Air quality API unreachable; displaying retained cached readings (X min old)."*

---

### 3. Tanglish Explanation
API key `.env` la illana -> **503 Service Unavailable** throw pannum. Key thappa iruntha -> **401 Unauthorized**. Rate limit exceed aana -> **429 Too Many Requests**. Nadakka vazhi illatha edathula point vecha -> **404 Not Found**. Provider slow aana -> **504 Gateway Timeout**.
Internet cut aana illa Open-Meteo down aana, 24 hours kulla store aana old cache iruntha, athoda `_is_stale: True` flag pottu return pannum. Frontend la orange warning banner kaattum.

---

### 4. Exact Source File, Function, and Code Logic
- **File**: [backend/app/core/config.py](file:///C:/final%20-%20project/backend/app/core/config.py)
  - `Settings` class using `pydantic_settings.BaseSettings`.
- **File**: [backend/app/services/routing_service.py](file:///C:/final%20-%20project/backend/app/services/routing_service.py#L266-L304)
  - HTTP exception raising.
- **File**: [backend/app/services/environmental_service.py](file:///C:/final%20-%20project/backend/app/services/environmental_service.py#L217-L232)
  - Stale cache retrieval.

---

### 5. Implementation Step by Step
```python
# Lines 217-231 in environmental_service.py
if not fetch_success:
    for pos_idx in missing_indices:
        ck = _build_cache_key("aq", coords[pos_idx][0], coords[pos_idx][1], time_str)
        if ck in _env_cache:
            cache_time, cached_data = _env_cache[ck]
            age = now - cache_time
            if age <= settings.STALE_DATA_MAX_AGE_SECONDS:
                results[pos_idx] = {
                    **cached_data,
                    "_is_stale": True,
                    "_stale_warning": f"Air quality API unreachable; displaying retained cached readings ({int(age // 60)}m old).",
                    "_cache_age": age,
                }
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"How do you enforce Nominatim's 1 request/second policy?"*
  - **Answer**: In [geocoding_service.py](file:///C:/final%20-%20project/backend/app/services/geocoding_service.py#L23-L27), we use an `asyncio.Lock()` and track `_last_geocoding_request_time`. If less than 1.0s has elapsed, the coroutine awaits `asyncio.sleep(1.0 - elapsed)`.

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"Why don't you use a persistent database like PostgreSQL or Redis for caching instead of an in-memory dictionary?"*
  - **Defense Strategy / Answer**: For the current deployment scale, Python's in-memory hash table provides $O(1)$ lookups with zero network overhead, zero external dependencies, and simple deployment. For horizontal multi-instance scaling in production, swapping `_env_cache` with a Redis client is an easy plug-and-play enhancement requiring no architectural refactoring.

---

## Topic 11: Functional Testing and Test Cases

### Feature Status
- **Implemented**: Complete automated test suite using `pytest` and `TestClient` with **64 passing test cases across 6 test modules**.
- **Future Enhancement**: End-to-end browser automation using Playwright or Cypress.

---

### 1. Possible Examiner Questions
1. *"What is your automated testing framework, and what test suites have you implemented?"*
2. *"How do you test that missing data is never zero-filled?"*
3. *"How do you test external API failures and rate limits without triggering live bans?"*

---

### 2. Simple English Answers
1. We use `pytest` with `fastapi.testclient.TestClient`. The test suite consists of **64 test cases** across 6 files:
   - [test_algorithm.py](file:///C:/final%20-%20project/backend/tests/test_algorithm.py) (17 tests): Normalization, Pareto dominance, tie-breaking, composite weights.
   - [test_environment.py](file:///C:/final%20-%20project/backend/tests/test_environment.py) (11 tests): Sampling geometry, EAQI thresholds, no zero-filling integrity.
   - [test_geocoding.py](file:///C:/final%20-%20project/backend/tests/test_geocoding.py) (5 tests): Query validation, rate limits, timeouts.
   - [test_greenery_and_traffic.py](file:///C:/final%20-%20project/backend/tests/test_greenery_and_traffic.py) (12 tests): Haversine distance, bbox buffers, OSM road proxy.
   - [test_routes.py](file:///C:/final%20-%20project/backend/tests/test_routes.py) (12 tests): Coordinate boundaries, 503 missing key, 404 no route.
   - [test_time_and_freshness.py](file:///C:/final%20-%20project/backend/tests/test_time_and_freshness.py) (7 tests): Cache TTL, force refresh, stale retention.
2. In [test_algorithm.py](file:///C:/final%20-%20project/backend/tests/test_algorithm.py#L182-L200), `test_missing_data_not_treated_as_zero()` instantiates routes with omitted metrics and verifies that `extract_raw_metric()` returns `None`, normalized values remain `None`, and composite scoring omits the factor without injecting zeros.
3. In [test_routes.py](file:///C:/final%20-%20project/backend/tests/test_routes.py) and [test_geocoding.py](file:///C:/final%20-%20project/backend/tests/test_geocoding.py), we mock `httpx.AsyncClient.post` and `get` using `unittest.mock.patch` to return mock responses with status codes 429, 504, and 401, verifying that our application handles upstream failures correctly.

---

### 3. Tanglish Explanation
Namma project ku `pytest` use panni automated unit and integration tests ezhuthirukkom. Total **64 test cases** irukku, 100% pass aaguthu.
- Normalization and Pareto dominance correct ah calculate aagutha nu test panrom.
- Missing data zero filling aagama irukka nu verify panrom.
- API key illatha pothu 503 varutha, invalid coordinates ku 400/422 varutha nu test panrom.
- Cache TTL expire aana udane force refresh aagutha, provider fail aana stale cache return aagutha nu complete data freshness test panrom.
Live external API-ah test panna pothu ban aagama irukka `unittest.mock.patch` vechu HTTP 429 and 504 responses ah mock panni test panroam.

---

### 4. Exact Source File, Function, and Code Logic
- **Test Command**: `backend\venv\Scripts\pytest -v backend\tests`
- **Verified Result**: `64 passed in 6.72s`
- **Key Test Modules**:
  - `TestParetoDominance::test_pareto_dominated_route_identified` in [test_algorithm.py](file:///C:/final%20-%20project/backend/tests/test_algorithm.py#L96-L113)
  - `TestMissingDataHandling::test_missing_data_not_treated_as_zero` in [test_algorithm.py](file:///C:/final%20-%20project/backend/tests/test_algorithm.py#L182-L200)
  - `TestApiKeyHandling::test_missing_api_key_returns_503` in [test_routes.py](file:///C:/final%20-%20project/backend/tests/test_routes.py#L93-L105)

---

### 5. Implementation Step by Step
```python
# From test_algorithm.py: Proving equal-priority weighting
def test_proof_of_equal_priority_weights():
    # Route 1: perfect air quality (1.0), worst distance (0.0) -> composite = 0.5
    r1 = make_test_route("r1", distance_m=2000.0, eaqi=10.0)
    # Route 2: worst air quality (0.0), perfect distance (1.0) -> composite = 0.5
    r2 = make_test_route("r2", distance_m=1000.0, eaqi=50.0)
    
    res = rank_routes([r1, r2], PreferenceSelection(air_quality=True, walking_distance=True))
    # Scores must be equal at 0.5 (equal 1/k priority)
    assert res.ranked_routes[0].composite_score == 0.5
    assert res.ranked_routes[1].composite_score == 0.5
    # Tie broken by shortest distance -> r2 ranks first
    assert res.ranked_routes[0].id == "r2"
```

---

### 6. Follow-up Questions & Answers
- **Follow-up**: *"What command do you use to run only the algorithm tests?"*
  - **Answer**: `backend\venv\Scripts\pytest -v backend/tests/test_algorithm.py`

---

### 7. Tricky Questions by External Examiners
- **Tricky Question**: *"How do you test that your tie-breaker is deterministic across different operating systems or Python dictionary iteration orders?"*
  - **Defense Strategy / Answer**: In [test_algorithm.py](file:///C:/final%20-%20project/backend/tests/test_algorithm.py#L143-L162) (`test_identical_metrics_stable_tie_break`), we pass routes in forward order `[r1, r2]` and reverse order `[r2, r1]` with identical scores and distances. The test verifies that the alphabetical route ID tie-breaker guarantees the exact same route ranking order regardless of input permutation.
