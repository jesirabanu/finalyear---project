# Technical Project Analysis & Second Review Dossier
**Project Title:** AI-Driven Multi-Environmental Personalized Pedestrian Routing  
**Author / Candidate:** Final-Year Computer Science Project Team  
**Review Stage:** Second Review (Technical Architecture, Design, Methodology, and Algorithmic Evaluation)  
**Academic Year:** 2026  
**Document Generated:** October 2026  
**Status:** Codebase Inspected & Automated Test Suite Verified (72 Backend Tests Passing, 0 Frontend Lint/Build Errors)

---

## Executive Summary

This dossier presents an exhaustive, code-grounded architectural and technical analysis prepared for the **Second Review** of the final-year undergraduate project titled **"AI-Driven Multi-Environmental Personalized Pedestrian Routing."**

The primary purpose of this document is to provide an academically rigorous, technically authentic, and beginner-friendly defense of the existing system. Every statement, metric, architecture diagram, flow description, and algorithmic formula presented here is directly derived from the inspected project source code located across `backend/` and `frontend/`. 

Crucially, this analysis strictly distinguishes between **what has been genuinely engineered and tested** (such as real OpenRouteService alternative routing, multi-location Open-Meteo environmental batch sampling, Overpass greenery buffers, defensible static road hierarchy traffic proxies, astronomical NOAA solar position calculations, and an in-house deterministic Pareto-dominance multi-criteria ranking engine) and **what remains future or planned work** (such as 3D microscale LiDAR tree-shade ray-casting, edge GPS turn-by-turn navigation, and personalized pairwise preference learning).

---

## 1. Project Overview

### 1.1 Project Introduction
Walking is the most fundamental, sustainable, and accessible mode of active urban mobility. However, pedestrians moving through modern cities are directly immersed in the ambient outdoor environment. Unlike drivers inside air-conditioned automobile cabins equipped with cabin air filters, pedestrians physically inhale airborne pollutants, absorb intense solar thermal radiation and heat stress, and endure vehicular noise and traffic safety risks.

Current digital mapping systems (e.g., Google Maps, Apple Maps, standard navigation devices) remain architecturally trapped within a **motorized transportation paradigm**: they compute walking paths almost exclusively to minimize geographical distance or travel time. 

The **AI-Driven Multi-Environmental Personalized Pedestrian Routing** project fundamentally rethinks pedestrian navigation. It treats walking routes not merely as shortest geometric segments, but as **environmental exposure corridors**. The system queries, harmonizes, evaluates, and ranks alternative pedestrian paths across five multi-environmental dimensions:
1. **Air Pollution Exposure** ($\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, European Air Quality Index)
2. **Thermal Comfort & Heat Stress** (ambient temperature, apparent "feels-like" temperature, solar elevation)
3. **Traffic Exposure & Road Proximity** (vehicular roadway hierarchy and proximity to major arterials)
4. **Urban Greenery & Natural Spaces** (proximity buffer to public parks, tree rows, and gardens)
5. **Physical Walking Distance & Duration** (metres and estimated walking minutes)

Rather than requiring non-expert pedestrians to invent arbitrary numerical weights (e.g., *"give 0.35 weight to air quality and 0.65 to distance"*), the platform allows users to select qualitative environmental preferences and employs a transparent, deterministic multi-criteria decision and Pareto-dominance ranking model.

---

### 1.2 Problem Statement
Pedestrian navigation platforms currently suffer from three interrelated deficiencies:

1. **The "Shortest-Path" Fallacy:** Existing navigation tools optimize exclusively for distance minimization. As a result, walkers are consistently directed along heavy, asphalt-dominated multi-lane arterial roadways because they are physically straight and wide, exposing pedestrians to peak concentrations of harmful vehicle tailpipe emissions ($\text{NO}_2$, ultrafine particulates) and elevated surface heat island temperatures.
2. **The "Single-Factor Environmental Silo":** Emerging research prototypes typically consider only one environmental parameter in isolation. For instance, an air-pollution avoidance router frequently diverts walkers into unshaded, treeless streets with intense solar radiation, while a thermal shade router may direct pedestrians into enclosed street canyons where vehicular exhaust gas is trapped.
3. **The Multi-Criteria Cognitive Burden:** Academic Multi-Criteria Decision Analysis (MCDA) algorithms commonly force users to provide precise numerical weights or solve complex pairwise comparison matrices (such as in the classical Analytic Hierarchy Process). Ordinary citizens cannot quantify how many micrograms of particulate matter ($\text{PM}_{2.5}$) they are willing to inhale in exchange for 300 metres less walking distance.

---

### 1.3 Aim and Objectives

#### Primary Aim:
To design, implement, test, and empirically validate an open-access, full-stack pedestrian routing platform that computes genuine alternative walking paths, enriches them with multi-source environmental indicators, and recommends personalized routes using a transparent multi-criteria decision framework without imposing numerical weighting burdens on the user.

#### Specific Objectives:
1. **Interactive Cartographic Interface:** Build a responsive web GIS frontend using OpenStreetMap and Leaflet that enables users to search addresses, place pins interactively, select environmental criteria, view alternative paths in distinct colours, and inspect comparative trade-offs.
2. **Decoupled Backend Architecture & API-Key Security:** Implement a modular Python FastAPI backend that securely manages external API credentials, acts as a rate-limiting proxy, and insulates client browsers from external service limits.
3. **Pedestrian Routing & Genuine Alternatives:** Integrate OpenRouteService's pedestrian direction engine (`foot-walking`) with spatial dispersion factors (`weight_factor`, `share_factor`) to generate geometrically diverse candidate walking paths between the user's selected origin and destination.
4. **Multi-Source Environmental Sampling:** Develop batch data-enrichment pipelines connecting Open-Meteo Air Quality (Copernicus CAMS), Open-Meteo Weather (ECMWF/ICON models), and OpenStreetMap Overpass (greenery and road hierarchy) to sample conditions along candidate corridors without exceeding external rate limits.
5. **Transparent Preference-Based Multi-Criteria Ranking:** Engineer an in-house, deterministic route-ranking engine in Python that clips outliers, performs min-max dimensionless normalization, identifies Pareto-dominated alternatives, and calculates equal-priority composite scores with deterministic distance tie-breaking.
6. **Data Freshness and Change Re-evaluation:** Implement a pre-trip environmental refresh mechanism (`POST /api/routes/refresh`) that tracks meteorological and air quality fluctuations, explains changes in recommendations, and provides explicit data provenance notices.
7. **Empirical Quality Assurance:** Validate system stability, boundary safety, rate-limiting, and algorithmic correctness via an automated test suite.

---

### 1.4 Existing Systems and Their Limitations

| System / Platform | Primary Optimization Metric | Environmental Awareness | Multi-Criteria Decision Model | Core Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Google Maps / Apple Maps** | Shortest duration / shortest distance | None (incidental air quality widget in select regions; no route optimization) | None (single cost function based on road network speed limits and traffic) | Directs pedestrians alongside high-traffic, polluted roadways; treats walking as motorized travel without vehicle cabin protection. |
| **Baseline OpenRouteService / OSRM** | Shortest path on OpenStreetMap pedestrian network | None in baseline API | None (Dijkstra / Contraction Hierarchies on geometric length) | Identifies walkable sidewalks and crossings, but ignores atmospheric pollution, heat, shade, and greenery. |
| **Research Prototypes (e.g., Vakacherla et al., 2025)** | Air pollution minimization ($\text{PM}_{2.5}$) | Air quality only | Single-objective or fixed-weight additive sum | Silo problem: completely ignores thermal stress, solar radiation, and greenery; diverts users into scorching unshaded boulevards. |
| **Shade Navigation Prototypes (e.g., Antunes, 2026)** | Solar shadow fraction | Building shadow only | Heuristic agent-based or ray-tracing | High computational latency; decoupled from air quality; fails when 3D building height data is missing in OSM. |
| **Classical MCDA Routing Models** | Multi-objective weighted sum | Multiple | Manual numerical weights ($w_1, w_2, \dots$) | Imposes severe cognitive burden; arbitrary user weight selection distorts mathematical normalization; masks Pareto trade-offs. |

---

### 1.5 Proposed System and Its Advantages

The proposed **AI-Driven Multi-Environmental Personalized Pedestrian Routing** system introduces a balanced, transparent, and academically defensible alternative:

1. **Holistic Multi-Environmental Evaluation:** Instead of optimizing one metric in isolation, the system evaluates routes simultaneously across air quality, thermal heat, traffic exposure, greenery, and walking distance.
2. **Zero-Guessing Qualitative Preference Model:** Users simply toggle boolean preferences (e.g., *Air Quality*, *Greenery*, *Thermal Comfort*). The backend transparently converts active selections into an equal-priority dimensionless evaluation ($1/k$), eliminating arbitrary numerical slider guesswork.
3. **Formal Pareto-Dominance Analysis:** The system identifies non-dominated alternatives on the multi-criteria efficiency frontier. If Route A is no worse than Route B across all chosen factors and strictly superior in at least one, Route B is formally classified as *Pareto-dominated*, ensuring that inferior routes are never recommended.
4. **Academic Defensibility & Data Honesty:** The system never fabricates synthetic data. If external 3D building heights are unmapped in OpenStreetMap, shade is transparently reported as unavailable rather than guessed. If air quality data is missing, it is excluded without zero-substitution.
5. **Decoupled API Security & Rate Control:** Third-party credentials (OpenRouteService API key, optional TomTom key) are strictly contained on the backend. Nominatim geocoding and Overpass queries are throttled through backend locks to respect upstream open-source server policies.

---

### 1.6 Research Gaps Addressed by the Project
Based on the systematic analysis of 24 recent research publications documented in [`RESEARCH_GAPS.md`](file:///C:/final%20-%20project/RESEARCH_GAPS.md), this project directly addresses four fundamental research gaps:

* **Gap 1: The "Single-Environmental Silo" Dilemma:** Addressed by unifying particulate pollution ($\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, EAQI), meteorological heat stress, traffic exposure, and park greenery into a single routing architecture.
* **Gap 2: The Cognitive Burden and Mathematical Flaws of Fixed-Weight MCDA:** Addressed by eliminating manual numeric weights in favor of qualitative preference selections backed by dimensionless min-max normalization, equal-priority heuristics ($1/k$), and Pareto efficiency frontier analysis.
* **Gap 3: Spatial and Temporal Resolution Mismatch:** Addressed by sampling route geometry at representative waypoints, executing efficient batch queries, aggregating route summaries, and publishing explicit provenance metadata (identifying regional numerical forecast models vs. localized static proxies).
* **Gap 4: Commercial "Shortest-Path Dominance" vs. Human Route Selection:** Addressed by configuring OpenRouteService with realistic pedestrian detour parameters (`weight_factor: 1.4`, `share_factor: 0.6`) and enforcing an honest route availability policy (never duplicating a single route to fake alternative choices).

---

## 2. Technology Stack

Every component, library, and service reported below has been verified through direct inspection of [`package.json`](file:///C:/final%20-%20project/frontend/package.json), [`requirements.txt`](file:///C:/final%20-%20project/backend/requirements.txt), and the virtual environment.

```
+-----------------------------------------------------------------------------------+
|                                  TECHNOLOGY STACK                                 |
+-----------------------------------------------------------------------------------+
| Layer           | Technology / Tool             | Installed Version               |
+-----------------+-------------------------------+---------------------------------+
| Frontend Runtime| React                         | ^19.2.8                         |
| Frontend Tooling| Vite                          | ^8.3.0 (v8.3.4 running)         |
| Frontend Linter | Oxlint                        | ^1.81.0                         |
| Web GIS / Maps  | Leaflet & react-leaflet       | Leaflet 1.9.4 / react-leaflet 5 |
| UI Icons        | Lucide React                  | ^1.55.0                         |
| Backend Runtime | Python                        | 3.14.7                          |
| Backend Web API | FastAPI                       | 0.143.0                         |
| ASGI Server     | Uvicorn                       | 0.54.0                          |
| Schema & Typing | Pydantic & pydantic-settings  | Pydantic 2.14.0 / settings 2.15 |
| Async HTTP      | HTTPX                         | 0.28.1                          |
| Test Framework  | Pytest & pytest-asyncio       | Pytest 9.1.1 / asyncio 1.4.0    |
| Routing Provider| OpenRouteService (ORS) API    | Foot-walking GeoJSON v2         |
| Geocoding       | OSM Nominatim                 | Public search v1 (proxied)      |
| Weather & AQI   | Open-Meteo Air Quality & Wx   | Global CAMS & ECMWF APIs        |
| Spatial Data    | OpenStreetMap Overpass API    | Interpreter (Overpass QL)       |
| Solar Engine    | NOAA Solar Position Algorithm | In-house Python implementation  |
+-----------------------------------------------------------------------------------+
```

### Detailed Component Justification

#### 1. Frontend: React 19 (`^19.2.8`) & Vite (`^8.3.0`)
* **What it does:** Powers the single-page web user interface, managing state for coordinate selections, preference toggles, active route selection, comparison tables, and dynamic re-ranking.
* **Why it is used:** React’s declarative component architecture allows immediate synchronization between user preference toggles and route re-ranking without reloading the page. Vite provides fast Hot Module Replacement (HMR) and optimized Rollup-based production builds.
* **Where it is used:** [`frontend/src/App.jsx`](file:///C:/final%20-%20project/frontend/src/App.jsx), [`frontend/src/main.jsx`](file:///C:/final%20-%20project/frontend/src/main.jsx).

#### 2. Mapping: Leaflet (`^1.9.4`) & react-leaflet (`^5.0.0`)
* **What it does:** Renders the interactive cartographic canvas, displays OpenStreetMap tile layers, positions custom SVG start (A) and destination (B) markers, and renders route geometry polylines in distinct palette colours.
* **Why it is used:** Leaflet is lightweight, mobile-responsive, open-source, and does not require proprietary API access tokens (unlike Mapbox or Google Maps). `react-leaflet` integrates Leaflet’s imperative DOM manipulation cleanly into React’s lifecycle.
* **Where it is used:** [`frontend/src/components/MapView.jsx`](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx).

#### 3. Backend: Python 3.14 & FastAPI (`0.143.0`) with Uvicorn (`0.54.0`)
* **What it does:** Serves as the asynchronous backend API gateway, hosting endpoints for pedestrian route calculation (`/api/routes`), location geocoding (`/api/geocode`), multi-criteria ranking (`/api/rank`), route refresh (`/api/routes/refresh`), point environment lookups (`/api/environment`), and system health (`/api/health`).
* **Why it is used:** FastAPI provides high-performance asynchronous concurrency (`async`/`await`), automatic OpenAPI/Swagger interactive documentation (`/docs`), and rigorous runtime schema validation.
* **Where it is used:** [`backend/app/main.py`](file:///C:/final%20-%20project/backend/app/main.py), [`backend/app/api/routes.py`](file:///C:/final%20-%20project/backend/app/api/routes.py).

#### 4. Data Validation: Pydantic v2 (`2.14.0`) & pydantic-settings (`2.15.0`)
* **What it does:** Validates and parses all request payloads and response structures. Enforces coordinate latitude/longitude range boundaries ($[-90, 90]$, $[-180, 180]$), validates non-identical points, and parses configuration from `.env`.
* **Why it is used:** Pydantic v2 is implemented in Rust (via `pydantic-core`), providing rapid serialization, robust error messages, and strict typing.
* **Where it is used:** [`backend/app/schemas/`](file:///C:/final%20-%20project/backend/app/schemas/), [`backend/app/core/config.py`](file:///C:/final%20-%20project/backend/app/core/config.py).

#### 5. Asynchronous Client: HTTPX (`0.28.1`)
* **What it does:** Executes non-blocking outbound HTTP requests to OpenRouteService, Open-Meteo, Nominatim, and Overpass API endpoints.
* **Why it is used:** Enables parallel external requests using `asyncio.gather()`, allowing air quality and weather data to be retrieved concurrently, reducing network latency.
* **Where it is used:** [`backend/app/services/`](file:///C:/final%20-%20project/backend/app/services/).

#### 6. Routing Service: OpenRouteService (ORS) Walking Directions API
* **What it does:** Computes legitimate walking paths based on OpenStreetMap pedestrian network topology (`foot-walking` profile) and returns alternative paths with distance and duration metrics.
* **Why it is used:** ORS respects pedestrian-accessible infrastructure (sidewalks, footpaths, pedestrian crossings, parks) and supports alternative route generation via spatial penalty parameters.
* **Where it is used:** [`backend/app/services/routing_service.py`](file:///C:/final%20-%20project/backend/app/services/routing_service.py).

#### 7. Geocoding: OpenStreetMap Nominatim (Backend-Proxied)
* **What it does:** Converts location search queries into latitude and longitude coordinates.
* **Why it is used:** Open-access, worldwide geographic gazetteer. Proxied through the backend with a strict 1 request/second lock, in-memory TTL caching, and a compliant academic `User-Agent`.
* **Where it is used:** [`backend/app/services/geocoding_service.py`](file:///C:/final%20-%20project/backend/app/services/geocoding_service.py).

#### 8. Environmental APIs: Open-Meteo Air Quality & Weather Forecast APIs
* **What it does:** Supplies hourly estimates for particulate matter ($\text{PM}_{2.5}$, $\text{PM}_{10}$), $\text{NO}_2$, European AQI (EAQI), ambient temperature, apparent "feels-like" temperature, humidity, and wind speed.
* **Why it is used:** Open-access, keyless API with global coverage sourced from authoritative regional numerical models (Copernicus Atmosphere Monitoring Service CAMS and ECMWF/ICON weather models). Supports multi-coordinate batch queries.
* **Where it is used:** [`backend/app/services/environmental_service.py`](file:///C:/final%20-%20project/backend/app/services/environmental_service.py).

#### 9. Greenery & Traffic Infrastructure: OpenStreetMap Overpass API
* **What it does:** Executes bounded Overpass QL queries over the route corridor bounding box to locate parks, gardens, nature reserves, and major road classifications (`motorway`, `primary`, `secondary`).
* **Why it is used:** Provides vector spatial geometries directly from OSM, enabling buffer calculation (~50m) and road hierarchy proximity estimation.
* **Where it is used:** [`backend/app/services/greenery_service.py`](file:///C:/final%20-%20project/backend/app/services/greenery_service.py), [`backend/app/services/traffic_service.py`](file:///C:/final%20-%20project/backend/app/services/traffic_service.py).

#### 10. Quality Assurance: Pytest (`9.1.1`) & Oxlint (`1.81.0`)
* **What it does:** Automated testing and code health verification. Pytest runs 72 automated test cases verifying routing parsing, coordinate boundaries, API failures, missing data integrity, and ranking stability. Oxlint verifies frontend JavaScript/React code quality.
* **Current Verified Result:** **72 passed, 0 failed in backend; 0 warnings, 0 errors in frontend lint and build.**

---

## 3. System Design

### 3.1 Functional Requirements

* **FR-1: Location Search & Pin Placement:** The system shall allow users to search for origin and destination locations via text queries (minimum 3 characters, debounced) or by clicking directly on the interactive Leaflet map canvas.
* **FR-2: Pedestrian Route Generation:** The system shall request walking paths from OpenRouteService using the `foot-walking` profile, returning at least one primary route and up to two genuine alternative pedestrian corridors where physically available.
* **FR-3: Coordinate Conversion for Web GIS:** The backend shall translate OpenRouteService GeoJSON coordinate pairs (`[longitude, latitude]`) into Leaflet-compliant polyline coordinates (`[latitude, longitude]`) with unique route identifiers (`route_0`, `route_1`, etc.) and designated palette colours.
* **FR-4: Multi-Environmental Sampling:** The backend shall extract representative waypoint samples (3 to 5 points) along each candidate route corridor and query external environmental services (Open-Meteo, Overpass) to gather air quality, weather, greenery, and traffic exposure indicators.
* **FR-5: Qualitative Preference Selection:** The frontend shall present accessible toggles for 5 environmental factors (*Air Quality*, *Thermal Comfort*, *Traffic Exposure*, *Greenery*, *Walking Distance*) and an explicit *No Preference (Default Baseline)* option.
* **FR-6: Deterministic Multi-Criteria Route Ranking:** The backend ranking engine shall normalize metrics onto a dimensionless scale $[0.0, 1.0]$, identify Pareto-dominated alternatives, and compute equal-priority composite scores ($1/k$), placing the most optimal route at Rank 1.
* **FR-7: Missing Data Handling:** The system shall preserve `null` for unrecorded environmental variables, exclude missing criteria from multi-criteria scoring, and withhold confident recommendations if all selected factors lack data.
* **FR-8: Comparative Visualization:** The frontend shall display comparative route cards, an expandable multi-criteria comparison matrix, an environmental profile breakdown, and an integration health badge.
* **FR-9: Environmental Refresh & Change Tracking:** The system shall support on-demand re-evaluation of environmental conditions (`POST /api/routes/refresh`) without recalculating road geometries, detecting and explaining any change in route recommendation.

---

### 3.2 Non-Functional Requirements

* **NFR-1: Usability & Cognitive Simplicity:** The user interface shall eliminate numerical weight entry (sliders, percentage dials) so that non-technical pedestrians can select route priorities effortlessly.
* **NFR-2: Security & Credential Protection:** All external API secret keys (e.g., `ORS_API_KEY`) must reside strictly in the backend `.env` configuration file and never be exposed in client-side JavaScript bundles or network responses.
* **NFR-3: Upstream Rate Limit Compliance:** The backend shall implement asynchronous mutex locks and in-memory TTL caching to enforce upstream rate limits (e.g., maximum 1 request/sec for OpenStreetMap Nominatim and Overpass).
* **NFR-4: Performance & Concurrency:** Multi-point environmental requests shall be aggregated into batch calls and executed concurrently using asynchronous I/O (`asyncio.gather()`), maintaining route enrichment response times under acceptable thresholds (< 3 seconds on standard broadband).
* **NFR-5: Determinism & Reproducibility:** Given identical candidate route inputs and identical preference selections, the ranking algorithm shall return identical ranks, scores, and tie-break orders 100% of the time.
* **NFR-6: Fault Tolerance & Graceful Degradation:** If an external environmental provider times out or fails (HTTP 429, 500, 504), the system shall retain previously cached data with an explicit `is_stale: true` warning or omit the unavailable factor, never crashing or displaying blank route cards.

---

### 3.3 Input Design

```
+-------------------------------------------------------------------------------------------------+
|                                           INPUT DESIGN                                          |
+-------------------------------------------------------------------------------------------------+
| Input Element       | Type / Format                     | Validation Rules                      |
+---------------------+-----------------------------------+---------------------------------------+
| Origin (Point A)    | Lat/Lon float + text label        | -90 <= Lat <= 90; -180 <= Lon <= 180  |
| Destination (Point B| Lat/Lon float + text label        | Distinct from Origin (|diff| >= 1e-5) |
| Alternatives Count  | Integer (0 to 3)                  | Clamped between 0 and 3 (default 2)   |
| Departure Time      | ISO 8601 string or null           | Valid timestamp (e.g. 2026-10-31T...) |
| Preferences         | Boolean flags (6 options):        | Air Quality, Temperature, Traffic,    |
|                     | {air_quality, temperature, ...}   | Greenery, Distance, No Preference     |
| Map Click           | Leaflet Map canvas click          | Translates click pixel to Lat/Lng     |
+-------------------------------------------------------------------------------------------------+
```

---

### 3.4 Output Design

1. **Interactive Polyline Map Display:**
   * Primary route rendered in Royal Blue (`#2563eb`), Alternative A in Vibrant Purple (`#8b5cf6`), Alternative B in Dark Teal (`#0d9488`).
   * Selected route highlighted with higher z-index and bold stroke weight (6px vs. 4px).
   * Interactive tooltips and popups detailing route name, distance (km), walking duration (min), and ranking status.
2. **Ranked Route Cards (Sidebar):**
   * Prominent **"Recommended (Rank 1)"** card badge with composite score and Pareto-optimal status.
   * Quick-glance metrics: distance in km, walking time in mins, air quality (EAQI), temperature (°C), greenery coverage (%), and traffic indicator.
   * Natural language trade-off summary (e.g., *"Best overall balance: Best Air Quality (18.4 EAQI), +12% Greenery"*).
3. **Multi-Criteria Route Comparison Matrix:**
   * Expandable side-by-side data table distinguishing **raw physical measurements** (with units like m, °C, EAQI, %) from **dimensionless normalized scores** ($[0.0, 1.0]$).
4. **Environmental Profile Breakdown Panel:**
   * Detailed cards displaying individual particulate readings ($\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$), EAQI category indicator, apparent "feels-like" temperature, relative humidity, wind speed, weather description, park proximity count, and solar elevation angle.
   * Clear provenance and disclaimer notices informing the user of the regional numerical modeling scale (~11 km grid) and stating that the system is a pre-trip planning tool, not an in-walk GPS navigator.

---

### 3.5 Module Descriptions

* **`backend/app/main.py`:** Application entry point. Configures FastAPI, enables Cross-Origin Resource Sharing (CORS) for frontend origins, and registers the `/api` route handlers.
* **`backend/app/core/config.py`:** Centralized settings management powered by `pydantic-settings`. Loads environment variables from `.env`, managing API keys, timeouts, and cache TTL parameters.
* **`backend/app/api/routes.py`:** Defines HTTP endpoints:
  * `POST /api/routes`: Route calculation and automated multi-environmental enrichment.
  * `POST /api/rank`: Multi-criteria preference evaluation and route ranking.
  * `POST /api/routes/refresh`: Selective environmental refresh and recommendation change tracking.
  * `GET /api/geocode`: OpenStreetMap Nominatim location auto-complete.
  * `GET /api/environment`: Point-specific environmental queries.
  * `GET /api/health`: Comprehensive integration and backend health check.
* **`backend/app/services/routing_service.py`:** Orchestrates OpenRouteService directions queries, parses GeoJSON features, converts coordinates to Leaflet format, manages color assignments, and coordinates enrichment across environmental sub-services.
* **`backend/app/services/environmental_service.py`:** Manages Open-Meteo Air Quality and Weather API queries. Performs geometry sampling, multi-coordinate batch requests, in-memory TTL caching, and route-level metric aggregation.
* **`backend/app/services/greenery_service.py`:** Binds route corridors into geographic bounding boxes, constructs Overpass QL queries, calculates Haversine distances to mapped parks/gardens, and computes route greenery coverage fractions.
* **`backend/app/services/traffic_service.py`:** Evaluates pedestrian exposure to vehicular roadways. Handles optional live TomTom Traffic Flow integration and provides a static road hierarchy proxy based on OpenStreetMap highway tags.
* **`backend/app/services/shade_service.py`:** Implements the NOAA Solar Position Algorithm to calculate astronomical solar altitude and azimuth. Evaluates corridor 3D building height coverage and enforces academic defensibility by withholding unmapped shade scores.
* **`backend/app/services/geocoding_service.py`:** Manages Nominatim address queries with 1 req/sec rate-limiting, custom `User-Agent` headers, and a 10-minute in-memory query cache.
* **`backend/app/algorithm/ranking_engine.py`:** Core mathematical evaluation engine. Executes factor directionality mapping, min-max normalization, Pareto dominance identification, equal-priority scoring, deterministic tie-breaking, and change explanations.
* **`frontend/src/App.jsx`:** Main React application controller. Manages state for origin, destination, preferences, route collections, ranking outputs, and map interaction modes.
* **`frontend/src/components/MapView.jsx`:** Leaflet map rendering module with dynamic bounding box zooming, SVG markers, and route polyline interaction.
* **`frontend/src/components/Sidebar.jsx`:** User interaction sidebar hosting geocoding search bars, preference toggles, departure time inputs, route cards, and action buttons.
* **`frontend/src/components/RouteComparisonTable.jsx`:** Side-by-side tabular comparison component displaying raw metrics alongside normalized scores.
* **`frontend/src/components/EnvironmentalPanel.jsx`:** Route environmental profile viewer detailing atmospheric and meteorological parameters.
* **`frontend/src/components/StatusBadge.jsx`:** Real-time health monitor displaying backend connection status and external API configurations.

---

### 3.6 User Interaction Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Pedestrian User
    participant UI as React Frontend (Sidebar / MapView)
    participant API as FastAPI Backend (/api)
    participant ORS as OpenRouteService (foot-walking)
    participant Env as Open-Meteo & Overpass APIs
    participant Engine as Ranking Engine (Python)

    User->>UI: 1. Types location or clicks map for Origin & Destination
    UI->>API: GET /api/geocode?q=...
    API-->>UI: Returns location suggestions (lat, lon, label)
    User->>UI: 2. Toggles preferences (e.g. Clean Air, Greenery)
    User->>UI: 3. Clicks "Calculate Walking Routes"
    UI->>API: POST /api/routes (origin, destination, alternatives=2)
    API->>ORS: Request walking directions (weight_factor=1.4, share_factor=0.6)
    ORS-->>API: Returns GeoJSON walking paths (primary + alternatives)
    API->>API: Convert [lon, lat] to Leaflet [lat, lon]
    API->>Env: Batch query air quality, weather, greenery & traffic
    Env-->>API: Returns environmental indicators
    API->>Engine: Run multi-criteria evaluation with active preferences
    Engine-->>API: Returns ranked routes, Pareto status, trade-offs
    API-->>UI: Return complete RouteResponse
    UI->>UI: Render route polylines on Leaflet map & populate route cards
    User->>UI: 4. Selects a route card or adjusts preference toggles
    UI->>Engine: Re-evaluate ranking instantly via POST /api/rank
    Engine-->>UI: Updated ranking, comparison matrix, highlighted map polyline
```

---

## 4. System Architecture

### 4.1 Architectural Layers

The system follows a clean, decoupled **Five-Layer Architecture**:

1. **Presentation Layer (Frontend Single-Page Application):**
   * Implemented in React 19 and Vite.
   * Renders the interactive Leaflet map canvas and responsive sidebar.
   * Handles user input, geocoding auto-complete debouncing, preference checkbox states, route selection, and local caching.
   * Communicates with the backend exclusively via standard asynchronous JSON REST endpoints.
2. **API Gateway & Routing Layer (FastAPI Backend):**
   * Operates on Uvicorn ASGI server.
   * Enforces CORS policies, input validation (Pydantic models), query parameter constraints, and standardized JSON error responses (HTTP 400, 404, 429, 503, 504).
   * Manages system health checks and protects third-party credentials.
3. **Data Integration & Proxy Layer (External Service Gateways):**
   * Acts as a rate-limiting proxy and client for four independent external service ecosystems:
     * *OpenRouteService:* Pedestrian topological path calculation.
     * *OpenStreetMap Nominatim:* Forward address geocoding.
     * *Open-Meteo APIs:* Gridded numerical air quality and weather forecasts.
     * *OpenStreetMap Overpass API:* Spatial vector queries for greenery and roadway hierarchy.
   * Implements in-memory TTL caching and asynchronous mutex locks to ensure adherence to open-source fair-use policies.
4. **Data Processing & Analytics Layer (Route Enrichment & Ranking Engine):**
   * Performs geometry waypoint sampling (3–5 points per route).
   * Aggregates point readings into route-level environmental profiles.
   * Executes the deterministic multi-criteria ranking algorithm, outlier clipping, min-max normalization, Pareto dominance identification, and tie-breaking.
   * Implements the NOAA Solar Position Algorithm for astronomical solar angle calculation.
5. **Output & Visualization Layer:**
   * Delivers Leaflet-ready coordinate structures (`[latitude, longitude]`).
   * Formats side-by-side comparison tables, natural language trade-off summaries, and data freshness provenance metadata for direct UI consumption.

---

### 4.2 Architecture Diagram

```mermaid
graph TD
    subgraph ClientLayer ["1. Presentation Layer (React 19 + Leaflet)"]
        UI["User Interface (App.jsx)"]
        MapComp["Interactive Map (MapView.jsx / Leaflet 1.9.4)"]
        SideComp["Sidebar Controls (Sidebar.jsx)"]
        CompTable["Comparison Matrix (RouteComparisonTable.jsx)"]
        EnvPanel["Environmental Profile (EnvironmentalPanel.jsx)"]
        HealthBadge["Health Monitor (StatusBadge.jsx)"]
    end

    subgraph APILayer ["2. API Gateway & Controller Layer (FastAPI + Uvicorn)"]
        Router["API Router (/api/routes.py)"]
        HealthEP["GET /api/health"]
        GeocodeEP["GET /api/geocode"]
        RoutesEP["POST /api/routes"]
        RefreshEP["POST /api/routes/refresh"]
        RankEP["POST /api/rank"]
    end

    subgraph ServiceLayer ["3. Data Integration & Service Layer (Python Async HTTPX)"]
        GeoService["Geocoding Service (Nominatim Proxy + Cache)"]
        RouteService["Routing Service (ORS Client & Coordinate Converter)"]
        EnvService["Environmental Service (Open-Meteo Air Quality & Weather)"]
        GreenService["Greenery Service (Overpass API + Haversine Buffer)"]
        TrafficService["Traffic Exposure Service (OSM Road Hierarchy / TomTom)"]
        ShadeService["Shade Service (NOAA Solar Position Algorithm)"]
    end

    subgraph ExternalAPIs ["4. External Data Providers & Spatial Services"]
        NominatimAPI["OSM Nominatim API (Geocoding)"]
        ORSAPI["OpenRouteService API (Walking Directions)"]
        OpenMeteoAQ["Open-Meteo Air Quality API (CAMS Regional Grid)"]
        OpenMeteoWx["Open-Meteo Weather API (ECMWF/ICON Models)"]
        OverpassAPI["OSM Overpass API (Park & Road Vector Features)"]
        TomTomAPI["TomTom Traffic API (Optional Live Flow)"]
    end

    subgraph EngineLayer ["5. Analytical & Algorithmic Engine"]
        RankEngine["Multi-Criteria Ranking Engine (ranking_engine.py)"]
        ParetoEngine["Pareto Dominance Analyzer"]
        NormEngine["Min-Max Dimensionless Normalizer"]
        TradeOffEngine["Trade-Off & Change Explanation Generator"]
    end

    %% Client to API Gateway
    UI --> Router
    SideComp --> GeocodeEP
    SideComp --> RoutesEP
    SideComp --> RefreshEP
    SideComp --> RankEP
    HealthBadge --> HealthEP

    %% API Gateway to Services
    GeocodeEP --> GeoService
    RoutesEP --> RouteService
    RefreshEP --> RouteService
    RankEP --> RankEngine

    %% Route Service Coordination
    RouteService --> EnvService
    RouteService --> GreenService
    RouteService --> TrafficService
    RouteService --> ShadeService
    RouteService --> RankEngine

    %% Services to External APIs
    GeoService --> NominatimAPI
    RouteService --> ORSAPI
    EnvService --> OpenMeteoAQ
    EnvService --> OpenMeteoWx
    GreenService --> OverpassAPI
    TrafficService --> OverpassAPI
    TrafficService -.-> TomTomAPI

    %% Services to Ranking Engine
    RankEngine --> NormEngine
    RankEngine --> ParetoEngine
    RankEngine --> TradeOffEngine

    %% Output data flow back to UI
    RankEngine --> RoutesEP
    RoutesEP --> UI
    UI --> MapComp
    UI --> CompTable
    UI --> EnvPanel
```

---

## 5. Methodology

### 5.1 Complete End-to-End Workflow

The workflow of the system is structured into seven distinct stages:

```
[1. User Input] ➔ [2. Preprocessing & Validation] ➔ [3. Route Generation] ➔ 
[4. Environmental Sampling & Enrichment] ➔ [5. Preference Integration] ➔ 
[6. Multi-Criteria Ranking & Pareto Analysis] ➔ [7. Map Rendering & Comparison]
```

```mermaid
flowchart TD
    Start(["User Opens Application"]) --> Step1["Step 1: Input Origin & Destination (Search or Map Click)"]
    Step1 --> Step2["Step 2: Backend Coordinate Bounds & Distinctness Validation"]
    Step2 --> Step3["Step 3: Query OpenRouteService with Alternative Route Parameters"]
    Step3 --> Step4{"Alternatives Available?"}
    Step4 -- Yes --> Step5A["Parse Primary + Alternative Corridors"]
    Step4 -- No --> Step5B["Parse Single Primary Route (Honest Flag)"]
    Step5A --> Step6["Step 4: Sample Geometry Waypoints (3-5 points per route)"]
    Step5B --> Step6
    Step6 --> Step7["Step 5: Concurrent Multi-Service Environmental Enrichment"]
    
    subgraph EnrichmentSub ["Environmental Enrichment Pipeline"]
        Step7 --> AQ["Fetch Air Quality (PM2.5, PM10, NO2, EAQI)"]
        Step7 --> WX["Fetch Weather (Temp, Apparent Temp, Wind, Rain)"]
        Step7 --> GN["Query Overpass Greenery Buffer (50m park buffer)"]
        Step7 --> TR["Evaluate Traffic Exposure (OSM Road Hierarchy)"]
        Step7 --> SH["Compute Astronomical Solar Angles (NOAA Algorithm)"]
    end

    AQ --> Step8["Aggregate Route-Level Environmental Profiles"]
    WX --> Step8
    GN --> Step8
    TR --> Step8
    SH --> Step8

    Step8 --> Step9["Step 6: User Selects Qualitative Preference Factors"]
    Step9 --> Step10["Step 7: Execute Ranking Engine (ranking_engine.py)"]
    
    subgraph RankingSub ["Multi-Criteria Ranking Pipeline"]
        Step10 --> Clip["1. Clip Outliers to Physical Bounds"]
        Clip --> Norm["2. Direction-Aware Min-Max Normalization on [0.0, 1.0]"]
        Norm --> Pareto["3. Pareto-Dominance Evaluation"]
        Pareto --> CompScore["4. Equal-Priority Composite Scoring (1/k sum)"]
        CompScore --> TieBreak["5. Deterministic Distance & ID Tie-Breaking"]
    end

    TieBreak --> Step11["Step 8: Construct RankedRoute Objects & Comparison Rows"]
    Step11 --> Step12["Step 9: Render Polylines on Leaflet Map & Display Sidebar Cards"]
    Step12 --> End(["Interactive Exploration / Re-Ranking"])
```

---

### 5.2 Separation of Implemented vs. Planned Stages

To ensure complete transparency during the Second Review, the methodology stages are strictly categorized below:

#### Implemented & Verified Stages:
1. **Interactive Cartographic Geocoding & Marker Placement:** Live Nominatim search, pin placing on Leaflet, auto-bounds fitting.
2. **Real Pedestrian Route & Alternative Generation:** OpenRouteService integration with custom detour and overlap control (`weight_factor=1.4`, `share_factor=0.6`).
3. **Multi-Source Environmental Sampling:** Live batch querying of Open-Meteo Air Quality, Open-Meteo Forecast, and Overpass Greenery within a single request cycle.
4. **Defensible Traffic Exposure Modeling:** OpenStreetMap road hierarchy proximity proxy, with optional live TomTom Flow API hook.
5. **Solar Position Computation:** NOAA astronomical algorithm determining solar elevation and azimuth for route centroid and departure time.
6. **Transparent Multi-Criteria Ranking & Pareto Analysis:** Full min-max normalization, factor directionality, Pareto-dominance classification, equal-priority scoring, deterministic tie-breaking, and missing-data preservation.
7. **Pre-Trip Route Refresh & Re-evaluation:** Updating environmental readings without recalculating route geometries and generating natural language change explanations.

#### Planned Future Stages:
1. **3D Microscale Sidewalk Shade Modeling (LiDAR / DSM):** Calculating precise building shadow polygons along sidewalks using Digital Surface Models (currently withheld when OSM lacks 3D building heights).
2. **In-Walk Turn-by-Turn GPS Rerouting:** Mobile GPS tracking with dynamic rerouting if environmental conditions change mid-walk (the current system is strictly pre-trip route comparison).
3. **Localized Low-Cost Sensor Calibration:** Direct ingestion of calibrated roadside IoT sensor feeds (e.g., PurpleAir / AirGradient) to complement regional CAMS gridded forecasts.
4. **Adaptive Personal Preference Learning:** Machine learning models (e.g., contextual bandits) to infer user preference tendencies over time based on route acceptance history.

---

## 6. Algorithms

### 6.1 Route Generation Algorithm (Routing Provider)

#### Actual Provider Algorithm:
OpenRouteService is built on an open-source Java routing platform (GraphHopper). For standard, single-route vehicle or pedestrian queries, GraphHopper utilizes **Contraction Hierarchies (CH)** to achieve millisecond query speeds on pre-processed road graphs.

However, when generating **alternative walking routes** with the `alternative_routes` parameter (specifying `target_count: 3`, `weight_factor: 1.4`, and `share_factor: 0.6`), Contraction Hierarchies cannot easily produce geometrically diverse alternative paths without un-contracting the graph. 

Therefore, for alternative pedestrian paths, OpenRouteService executes an **Iterative Penalty / Plateau Algorithm** on a flexible graph representation using **Bidirectional Dijkstra** search:
* **Plateau Method / Via-Node Search:** Identifies optimal detour branch points ("via nodes") that produce candidate paths sharing no more than a specified threshold (`share_factor: 0.6`, meaning maximum 60% overlap with the primary path) and extending distance by no more than the allowable limit (`weight_factor: 1.4`, meaning at most 40% longer than the shortest path).
* **Penalty Iteration:** Edges along the shortest path are temporarily penalized with increased travel impedance, and a subsequent Dijkstra search identifies an alternative corridor that avoids the primary street.

> [!IMPORTANT]
> The project does **not** construct a custom graph traversal solver from scratch; it leverages OpenRouteService's verified, topology-aware pedestrian routing engine through the backend.

---

### 6.2 Project Route-Ranking Algorithm

The project features a **fully custom, in-house multi-criteria ranking algorithm** implemented in [`backend/app/algorithm/ranking_engine.py`](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py). It operates entirely deterministically without stochastic or "black-box" machine learning.

#### Step 1: Outlier Bounds Clipping
To prevent extreme anomalous readings from distorting the relative scale, raw physical metrics are clipped to realistic physical boundary thresholds:
$$\text{clipped}(v, f) = \max(\text{min\_bound}_f, \min(\text{max\_bound}_f, v))$$
* Air Quality (EAQI): $[0.0, 150.0]$
* Temperature (°C): $[-30.0, 60.0]$
* Traffic Exposure Index: $[0.0, 100.0]$
* Greenery Coverage (%): $[0.0, 100.0]$
* Walking Distance (m): $[0.0, 100000.0]$

#### Step 2: Direction-Aware Min-Max Dimensionless Normalization
Raw metrics possess incompatible physical units (metres, degrees Celsius, EAQI index, percentages) and differing favorable directions. The engine maps each valid value to a dimensionless score in $[0.0, 1.0]$, where **$1.0$ always represents the best outcome** among the candidate routes:

* **For Minimization Criteria** (Air Quality, Temperature, Traffic Exposure, Walking Distance — *lower is better*):
  $$\text{NormalizedScore}(R, f) = \frac{\max_{r \in \mathcal{R}}(v_{r, f}) - v_{R, f}}{\max_{r \in \mathcal{R}}(v_{r, f}) - \min_{r \in \mathcal{R}}(v_{r, f})}$$
* **For Maximization Criteria** (Greenery Presence — *higher is better*):
  $$\text{NormalizedScore}(R, f) = \frac{v_{R, f} - \min_{r \in \mathcal{R}}(v_{r, f})}{\max_{r \in \mathcal{R}}(v_{r, f}) - \min_{r \in \mathcal{R}}(v_{r, f})}$$
* **Zero Variance Case:** If all candidate routes have identical values for factor $f$ ($\max = \min$), all routes receive $\text{NormalizedScore}(R, f) = 1.0$.
* **Missing Data Case:** If a metric is unrecorded by the provider, its normalized score remains `None`. It is never substituted with zero.

#### Step 3: Formal Pareto-Dominance Evaluation
Before calculating composite numerical scores, the engine determines whether any route is mathematically dominated by another candidate route across the user's active criteria $K$:

Route $A$ **Pareto-dominates** Route $B$ ($A \succ B$) if and only if:
1. Route $A$ is **no worse** than Route $B$ on all active factors:
   $$\forall f \in K, \quad \text{NormalizedScore}(A, f) \ge \text{NormalizedScore}(B, f) - \epsilon$$
2. Route $A$ is **strictly superior** to Route $B$ on at least one active factor:
   $$\exists f \in K, \quad \text{NormalizedScore}(A, f) > \text{NormalizedScore}(B, f) + \epsilon$$
*(where $\epsilon = 10^{-4}$ provides floating-point stability).*

Routes that are Pareto-dominated are flagged (`is_pareto_dominated: true`) and relegated below non-dominated alternatives in the ranking.

#### Step 4: Equal-Priority Composite Scoring
For all active criteria $K = \{f_1, f_2, \dots, f_k\}$, the composite score is the arithmetic mean of the normalized scores:
$$\text{Score}(R) = \frac{1}{|K|} \sum_{f \in K} \text{NormalizedScore}(R, f)$$
*Equal priority ($w_f = 1/k$) is explicitly declared as an algorithmic design heuristic to eliminate user cognitive burden, not as an inferred psychological personal profile.*

#### Step 5: Deterministic Tie-Breaking
Routes are sorted according to a deterministic 4-tuple key:
$$\text{SortKey}(R) = \Big( \text{is\_dominated}(R), \; -\text{Score}(R), \; \text{distance\_m}(R), \; \text{route\_id}(R) \Big)$$
1. **Dominance Status:** Non-dominated routes ($0$) sort before dominated routes ($1$).
2. **Composite Score:** Higher score sorts first (descending).
3. **Tie-Breaker 1 (Walking Distance):** Shorter walking distance sorts first (ascending).
4. **Tie-Breaker 2 (Route Identifier):** Lexicographical route ID sorts first (guaranteeing 100% stability).

---

### 6.3 Ranking Algorithm Pseudocode

```text
ALGORITHM: TransparentMultiCriteriaRouteRanking
INPUT: 
    routes: List of candidate RouteModel objects (R_1, R_2, ..., R_n)
    preferences: User preference flags {air_quality, temperature, traffic, greenery, distance, no_preference}
OUTPUT:
    RouteRankingResponse containing sorted RankedRoute objects and trade-off explanations

BEGIN
    1. active_factors ← DetermineActiveFactors(preferences, routes)
    
    2. IF active_factors is empty THEN
           active_factors ← ["walking_distance"]
           is_default_evaluation ← TRUE
       END IF

    3. FOR EACH factor f IN SupportedFactors DO
           valid_values ← [ExtractRawMetric(r, f) FOR r IN routes IF metric is NOT NULL]
           IF valid_values is NOT empty THEN
               v_min ← MIN(valid_values)
               v_max ← MAX(valid_values)
               span ← v_max - v_min
               FOR EACH r IN routes DO
                   val ← ExtractRawMetric(r, f)
                   IF val is NULL THEN
                       normalized_scores[f][r.id] ← NULL
                   ELSE IF span < 1e-6 THEN
                       normalized_scores[f][r.id] ← 1.0
                   ELSE IF FactorDirection(f) == "lower" THEN
                       normalized_scores[f][r.id] ← ROUND((v_max - val) / span, 4)
                   ELSE
                       normalized_scores[f][r.id] ← ROUND((val - v_min) / span, 4)
                   END IF
               END FOR
           END IF
       END FOR

    4. dominated_ids ← Set()
       FOR EACH r_a IN routes DO
           FOR EACH r_b IN routes (WHERE r_b != r_a) DO
               no_worse ← TRUE
               strictly_better ← FALSE
               FOR EACH f IN active_factors DO
                   s_a ← normalized_scores[f][r_a.id]
                   s_b ← normalized_scores[f][r_b.id]
                   IF s_a < s_b - 1e-4 THEN no_worse ← FALSE; BREAK
                   IF s_a > s_b + 1e-4 THEN strictly_better ← TRUE
               END FOR
               IF no_worse AND strictly_better THEN
                   dominated_ids.ADD(r_b.id)
               END IF
           END FOR
       END FOR

    5. k ← LENGTH(active_factors)
       FOR EACH r IN routes DO
           sum_score ← SUM(normalized_scores[f][r.id] FOR f IN active_factors)
           composite_scores[r.id] ← ROUND(sum_score / k, 4)
       END FOR

    6. sorted_routes ← SORT routes BY KEY:
           (r.id IN dominated_ids ? 1 : 0, -composite_scores[r.id], r.distance_m, r.id)

    7. ranked_route_objects ← GenerateRankedRoutesWithTradeOffs(sorted_routes, composite_scores, dominated_ids)
    
    RETURN RouteRankingResponse(ranked_route_objects)
END
```

---

### 6.4 Small Illustrative Example (Clearly Labelled Example)

> [!NOTE]
> **ILLUSTRATIVE WORKED EXAMPLE**: Consider a scenario with **3 candidate routes** connecting St. Paul's Cathedral to the Tower of London. The user has selected two environmental preferences: **Air Quality** and **Greenery**.

#### Step 1: Raw Metrics Returned from Providers
* **Route 1 (Primary Direct):**
  * Walking Distance: $1,820\text{ m}$
  * Air Quality (EAQI): $35.0$ (Moderate pollution)
  * Greenery Coverage: $10.0\%$ (Urban road, few trees)
* **Route 2 (Park Corridor Detour):**
  * Walking Distance: $2,150\text{ m}$ ($+330\text{ m}$ detour)
  * Air Quality (EAQI): $15.0$ (Cleaner air)
  * Greenery Coverage: $60.0\%$ (Runs alongside public gardens)
* **Route 3 (Dominated Industrial Detour):**
  * Walking Distance: $2,200\text{ m}$
  * Air Quality (EAQI): $38.0$ (Worse air)
  * Greenery Coverage: $8.0\%$ (Asphalt alleys)

#### Step 2: Min-Max Dimensionless Normalization across Candidates
* **Air Quality (Lower is better: min = 15.0, max = 38.0, span = 23.0):**
  * Route 1: $(38.0 - 35.0) / 23.0 = 3.0 / 23.0 \approx \mathbf{0.1304}$
  * Route 2: $(38.0 - 15.0) / 23.0 = 23.0 / 23.0 = \mathbf{1.0000}$ *(Best)*
  * Route 3: $(38.0 - 38.0) / 23.0 = 0.0 / 23.0 = \mathbf{0.0000}$ *(Worst)*
* **Greenery (Higher is better: min = 8.0, max = 60.0, span = 52.0):**
  * Route 1: $(10.0 - 8.0) / 52.0 = 2.0 / 52.0 \approx \mathbf{0.0385}$
  * Route 2: $(60.0 - 8.0) / 52.0 = 52.0 / 52.0 = \mathbf{1.0000}$ *(Best)*
  * Route 3: $(8.0 - 8.0) / 52.0 = 0.0 / 52.0 = \mathbf{0.0000}$ *(Worst)*

#### Step 3: Pareto-Dominance Evaluation
* Compare Route 2 vs. Route 1: Route 2 is superior on Air Quality ($1.0 > 0.13$) and Greenery ($1.0 > 0.04$). Route 2 dominates Route 1 on these two selected factors.
* Compare Route 1 vs. Route 3: Route 1 is better on Air Quality ($0.13 > 0.0$) and Greenery ($0.04 > 0.0$). Route 3 is dominated by both Route 1 and Route 2.
* *Result:* Route 3 is formally Pareto-dominated (`is_pareto_dominated: true`).

#### Step 4: Composite Score ($k = 2$ active factors)
* **Route 2:** $\text{Score} = (1.0000 + 1.0000) / 2 = \mathbf{1.0000}$
* **Route 1:** $\text{Score} = (0.1304 + 0.0385) / 2 = \mathbf{0.0845}$
* **Route 3:** $\text{Score} = (0.0000 + 0.0000) / 2 = \mathbf{0.0000}$

#### Step 5: Final Deterministic Rank Order
1. **Rank 1 (Recommended):** Route 2 (Score: $1.00$, Non-dominated, Best Air & Greenery)
2. **Rank 2 (Alternative):** Route 1 (Score: $0.08$, Shorter distance trade-off)
3. **Rank 3 (Dominated):** Route 3 (Score: $0.00$, Pareto-dominated by Routes 1 and 2)

---

### 6.5 Recommended Algorithm for Future Extension

While the current equal-priority min-max normalization and Pareto-dominance engine is effective and transparent, an ideal future enhancement is the integration of **TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)**:
* **Why TOPSIS?** TOPSIS evaluates routes based on their Euclidean distance to a **Positive Ideal Solution ($A^+$)** (best score achieved on every factor) and a **Negative Ideal Solution ($A^-$)** (worst score achieved on every factor).
* **Relative Closeness Formula:**
  $$C_i = \frac{S_i^-}{S_i^+ + S_i^-}$$
* **Academic Merit:** TOPSIS provides smoother multi-factor trade-off gradients when evaluating 5 or more candidate corridors, avoiding extreme sensitivity to single-factor variations while preserving rank stability.

---

## 7. Feasibility Study

### 7.1 Technical Feasibility
* **Architecture:** The project employs a modern, loosely-coupled client-server architecture (FastAPI backend + React Vite frontend). REST APIs exchange standardized GeoJSON and JSON schemas.
* **Compatibility:** Python 3.10+ and Node.js 18+ run cross-platform across Windows, Linux, and macOS without proprietary hardware requirements.
* **Testing & Build Verification:** Backend automated testing with Pytest achieved **72 passed tests out of 72**. Frontend linting (`oxlint`) and production bundling (`vite build`) completed with **0 errors and 0 warnings**.

### 7.2 Economic Feasibility
* **Cost:** Zero monetary cost for ongoing academic development.
* **Licensing:**
  * OpenRouteService offers an academic free tier (up to 2,000 directions requests/day).
  * Open-Meteo Air Quality & Weather APIs are completely free for non-commercial and academic usage without mandatory API key generation.
  * OpenStreetMap, Nominatim, and Overpass API are public open-access community resources under ODbL (Open Database License).
  * TomTom Traffic Flow API provides a free non-commercial evaluation tier (2,500 daily transactions).

### 7.3 Operational Feasibility
* **User Accessibility:** The application runs in any modern web browser (Chrome, Firefox, Edge, Safari).
* **Zero Cognitive Overload:** The interface eliminates complex mathematical inputs. Pedestrians interact through intuitive map clicks and simple checkbox toggles.

### 7.4 Data & API Feasibility
* **Coverage:** OpenRouteService, Open-Meteo, and OpenStreetMap provide worldwide geographic coverage. The system operates in any urban center globally without requiring pre-calibrated local hardware installations.
* **Data Freshness:** Open-Meteo updates numerical model predictions hourly. Nominatim updates continuously with OpenStreetMap edits.

### 7.5 Implementation Feasibility within Final-Year Project Timeline
* **Scope Management:** The core functional pipeline (routing, batch environmental enrichment, multi-criteria ranking, and interactive Leaflet map) is **100% implemented and functioning**.
* **Realistic Boundaries:** Advanced features prone to timeline slippage (such as mobile GPS native wrappers, microscale 3D LiDAR point-cloud shade simulation, or IoT hardware fabrication) were correctly scoped as planned future work, ensuring the core web platform is fully defensible.

### 7.6 API Limitations, Rate Limits, and Technical Risks

| API / Provider | Stated Usage Policy & Limits | System Risk Mitigation Engineered in Code |
| :--- | :--- | :--- |
| **OpenStreetMap Nominatim** | Strictly 1 request/second; mandatory application `User-Agent`. | Backend asynchronous lock (`_rate_limit_lock`) enforces minimum 1.0s gap; 10-minute in-memory TTL query cache eliminates duplicate calls. |
| **OpenRouteService (ORS)** | Free tier capped at 40 requests/minute and 2,000 requests/day. | API key protected on backend; client-side debouncing; fallback to primary route if alternative parameters fail. |
| **Open-Meteo (AQ & Weather)** | Fair-use policy (~10,000 daily queries); gridded spatial resolution (~11 km). | Batch multi-coordinate querying (`lat=...,...`); in-memory TTL caching; explicit UI metadata noting gridded model resolution. |
| **OSM Overpass API** | Server capacity limits; queries capped at 10s execution timeout. | Corridor bounding-box restriction (`maxsize: 2MB`); 15-minute in-memory bbox cache; silent degradation to `null` on server timeout. |
| **Network Failure / Outages** | External APIs may time out (HTTP 504) or return rate limit errors (HTTP 429). | Graceful stale-data fallback (`is_stale: true`, retaining cached readings up to 24 hours with user warning notice). |

---

## 8. Implementation Status

The table below provides a verified status of every system module based on direct inspection of the codebase:

| System Module / Feature | Verified Status | Evidence in Inspected Codebase |
| :--- | :---: | :--- |
| **Interactive Leaflet Map Canvas** | **Completed** | [`frontend/src/components/MapView.jsx`](file:///C:/final%20-%20project/frontend/src/components/MapView.jsx): OSM cartographic tiles, polyline rendering, dynamic bounds fitting. |
| **Start (A) & Destination (B) Pin Placement** | **Completed** | Custom SVG Emerald Green (A) and Bright Red (B) markers with click-to-place handler in `App.jsx`. |
| **Debounced Address Geocoding Search** | **Completed** | [`frontend/src/services/geocodingService.js`](file:///C:/final%20-%20project/frontend/src/services/geocodingService.js) and [`backend/app/services/geocoding_service.py`](file:///C:/final%20-%20project/backend/app/services/geocoding_service.py). |
| **OpenRouteService Pedestrian Routing** | **Completed** | [`backend/app/services/routing_service.py`](file:///C:/final%20-%20project/backend/app/services/routing_service.py): `foot-walking` profile with GeoJSON parsing. |
| **Genuine Alternative Route Generation** | **Completed** | ORS `alternative_routes` (`weight_factor: 1.4`, `share_factor: 0.6`); honest reporting of single routes. |
| **Multi-Colour Polyline Visualization** | **Completed** | Distinct 4-colour palette (`#2563eb`, `#8b5cf6`, `#0d9488`, `#d97706`) with selected route highlighting. |
| **API-Key Security Architecture** | **Completed** | Backend `.env` configuration; zero credential leakage to frontend bundle. |
| **Open-Meteo Air Quality Integration** | **Completed** | [`backend/app/services/environmental_service.py`](file:///C:/final%20-%20project/backend/app/services/environmental_service.py): $\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, European AQI. |
| **Open-Meteo Meteorological Integration** | **Completed** | Temperature, Apparent "feels-like" temperature, humidity, wind, WMO weather codes. |
| **OSM Overpass Greenery Proximity Buffer** | **Completed** | [`backend/app/services/greenery_service.py`](file:///C:/final%20-%20project/backend/app/services/greenery_service.py): 50m buffer fraction and park counting. |
| **Defensible Traffic Exposure Modeling** | **Completed** | [`backend/app/services/traffic_service.py`](file:///C:/final%20-%20project/backend/app/services/traffic_service.py): OSM major road hierarchy proxy + TomTom hook. |
| **Astronomical Solar Position Engine** | **Completed** | [`backend/app/services/shade_service.py`](file:///C:/final%20-%20project/backend/app/services/shade_service.py): NOAA Solar Position Algorithm (altitude & azimuth). |
| **Defensible Shade Spatial Verification** | **Completed** | Validates 3D building height coverage; reports unavailable if unmapped (<70%). |
| **Transparent Multi-Criteria Ranking Engine**| **Completed** | [`backend/app/algorithm/ranking_engine.py`](file:///C:/final%20-%20project/backend/app/algorithm/ranking_engine.py): Outlier bounds, min-max normalization, tie-breaking. |
| **Pareto-Dominance Analysis** | **Completed** | Detects strictly dominated alternatives; prioritizes non-dominated routes. |
| **No-Preference Default Baseline Rule** | **Completed** | Evaluates all available factors with distance as tie-breaker when preferences are empty. |
| **Side-by-Side Comparison Matrix Table** | **Completed** | [`frontend/src/components/RouteComparisonTable.jsx`](file:///C:/final%20-%20project/frontend/src/components/RouteComparisonTable.jsx): Displays raw physical metrics alongside normalized scores. |
| **Environmental Refresh & Re-evaluation** | **Completed** | `POST /api/routes/refresh`: Selective environmental updates and natural language change tracking. |
| **Automated Unit & Integration Testing** | **Completed** | 72 tests passing in Pytest across routing, geocoding, environment, shade, and algorithm modules. |
| **Linguistic Pairwise Preference Input (AHP)**| **In Progress** | Mathematical equal-priority model is functional; interactive qualitative pairwise UI slider is in development. |
| **Historical Temporal Trend Comparison** | **In Progress** | ISO departure time parameter is functional; comparative time-slider UI is in development. |
| **In-Walk Real-Time GPS Turn-by-Turn Reroute**| **Planned** | Out of scope for pre-trip comparison; planned for mobile native build. |
| **3D LiDAR / DSM Microscale Sidewalk Shade** | **Planned** | Requires dense Digital Surface Models; planned for future urban digital twin deployment. |
| **Localized Low-Cost IoT Sensor Mesh** | **Planned** | Planned for smart campus sensor network integration. |

---

## 9. Second Review Preparation

### 9.1 Important Points to Explain to the Review Panel

1. **Academic Honesty & Data Grounding:** Clearly state that all environmental data is retrieved live from authoritative scientific providers (Copernicus CAMS via Open-Meteo, ECMWF forecasts, and OpenStreetMap). Emphasize that the system **never invents synthetic numbers or substitutes missing readings with zero**.
2. **Cognitive Burden Solution:** Highlight that the project eliminates arbitrary user numerical weight guessing. Pedestrians choose qualitative priorities, and the algorithm applies a mathematically defensible equal-priority normalized model ($1/k$) with Pareto-dominance classification.
3. **Spatial Scale Defensibility:** Acknowledge upfront that atmospheric models operate on regional grids (~11 km). The system samples multiple waypoints along the route corridor to capture spatial gradients, rather than claiming false millimetre-level sidewalk precision.
4. **Pedestrian vs. Motorized Distinction:** Emphasize that OpenRouteService directions are generated using the `foot-walking` profile with pedestrian detour and dispersion parameters (`weight_factor: 1.4`, `share_factor: 0.6`), ensuring candidate paths follow footways, sidewalks, and pedestrian crossings rather than highways.
5. **Architectural Robustness:** Explain that all third-party API credentials are sequestered on the FastAPI backend, and upstream rate limits (e.g., Nominatim's 1 req/sec policy) are strictly enforced via asynchronous locks and TTL caching.
6. **Empirical Quality Assurance:** Inform the panel that the backend is backed by **72 passing automated unit and integration tests**, and the frontend builds cleanly with **0 linting errors**.

---

### 9.2 Likely Technical Questions and Simple Answers

#### Q1: "Why did you use OpenRouteService instead of Google Maps Directions API?"
* **Simple Answer:** "Google Maps Directions API is commercial, closed-source, and does not provide customizable alternative dispersion parameters or transparent access to underlying OpenStreetMap pedestrian infrastructure. OpenRouteService allows us to request legitimate pedestrian walking paths (`foot-walking`), tune detour boundaries (`weight_factor`) and overlap restrictions (`share_factor`), and directly inspect the GeoJSON geometry. Furthermore, ORS aligns with open-access academic reproducibility."

#### Q2: "What routing algorithm actually calculates the walking path coordinates?"
* **Simple Answer:** "The road network paths are generated by OpenRouteService, which runs on the GraphHopper routing engine. For genuine alternative route generation, ORS uses an **Iterative Penalty / Plateau Algorithm with Bidirectional Dijkstra search** on an uncontracted OpenStreetMap pedestrian network graph. Our backend converts these GeoJSON coordinates from `[longitude, latitude]` into Leaflet `[latitude, longitude]` pairs."

#### Q3: "Did you build your own algorithm, or are you just displaying API data?"
* **Simple Answer:** "We engineered an original, in-house **multi-criteria ranking and Pareto-dominance engine** in Python (`ranking_engine.py`). While external APIs provide raw measurements, our algorithm:
  1. Clips physical outliers,
  2. Maps incompatible units (metres, °C, EAQI, %) onto a dimensionless normalized scale $[0.0, 1.0]$ respecting factor directions,
  3. Evaluates formal Pareto dominance to filter out inferior corridors,
  4. Computes equal-priority composite scores, and
  5. Implements deterministic distance tie-breaking and natural language trade-off explanations."

#### Q4: "Why don't users enter numerical weights (e.g. 0.4 Air Quality, 0.6 Distance)?"
* **Simple Answer:** "Empirical transport literature (e.g., GreenAccess-RL, 2026; Yin & Le, 2026) demonstrates that forcing non-expert pedestrians to assign arbitrary decimal weights introduces severe cognitive burden. A pedestrian cannot intuitively quantify how much particulate matter they are willing to inhale per 100 metres of extra walking. Our system allows users to select qualitative goals, applying a transparent equal-priority heuristic ($1/k$) and Pareto efficiency analysis."

#### Q5: "How does your system handle missing environmental data?"
* **Simple Answer:** "Our system enforces strict scientific integrity: it **never substitutes missing data with zero**, because treating missing air pollution as $0.0$ would falsely make an unmeasured corridor look like the cleanest route. If a provider lacks data for a selected factor, that factor is excluded from the ranking, a warning is issued to the user, and if all selected factors lack data, confident recommendation is withheld and the system falls back to the safe distance baseline."

#### Q6: "How do you model shade, and why is shade marked as unavailable in some corridors?"
* **Simple Answer:** "We implemented the standard NOAA Astronomical Solar Position Algorithm to calculate the exact solar elevation and azimuth angles. However, scientifically valid sidewalk shade modeling requires 3D building height data and tree crown geometry. In OpenStreetMap, over 85% of building footprints globally lack height tags. Rather than fabricating synthetic shadows, our system academically defensibly marks shade as unavailable when 3D data is insufficient (<70%), excluding it from ranking."

#### Q7: "Is this an in-walk GPS navigation app like Google Maps with voice guidance?"
* **Simple Answer:** "No. This system is designed as a **pre-trip multi-environmental route planning and comparison platform**. It evaluates alternative corridors before the pedestrian begins their journey. While our `/api/routes/refresh` endpoint can re-evaluate environmental fluctuations before departure, turn-by-turn in-walk GPS rerouting is reserved for future mobile development."

---

### 9.3 Claims That Must NOT Be Made (Functionality Not Implemented)

> [!CAUTION]
> Making inaccurate claims before the review panel will compromise academic integrity. **Do NOT make the following claims:**

1. ❌ **DO NOT CLAIM:** *"We wrote our own Dijkstra or A\* shortest-path graph solver from scratch on raw road shapefiles."*  
   * **Truth:** OpenRouteService calculates the underlying topological walking paths. Our custom algorithm is the **multi-criteria ranking and Pareto evaluation engine**.
2. ❌ **DO NOT CLAIM:** *"We measure hyper-local, street-level air pollution directly on the sidewalk using physical hardware sensors."*  
   * **Truth:** Air quality readings are regional gridded forecasts (~11 km resolution) provided by the Copernicus Atmosphere Monitoring Service (CAMS) via the Open-Meteo API.
3. ❌ **DO NOT CLAIM:** *"We perform real-time, in-walk GPS turn-by-turn navigation that reroutes walkers mid-stride."*  
   * **Truth:** The system is an interactive pre-trip comparison tool. Route environmental refresh is supported before departure, but live device GPS tracking is not implemented.
4. ❌ **DO NOT CLAIM:** *"Our system uses Artificial Intelligence Deep Neural Networks or Reinforcement Learning for route scoring."*  
   * **Truth:** The ranking engine is a deterministic, mathematically transparent multi-criteria decision model based on min-max normalization, equal-priority composite weighting, and Pareto-dominance logic. Zero "black-box" machine learning is used for route ranking.
5. ❌ **DO NOT CLAIM:** *"We have complete, accurate sidewalk shade simulation everywhere in the world."*  
   * **Truth:** We calculate astronomical solar angles via NOAA equations, but shade scores are transparently withheld unless explicit 3D building heights are mapped in OpenStreetMap.
6. ❌ **DO NOT CLAIM:** *"We have real-time live vehicular traffic volume everywhere."*  
   * **Truth:** Unless an optional TomTom Traffic API key is configured, traffic exposure operates in a defensible **static road hierarchy proxy mode** based on OpenStreetMap highway tags (`motorway`, `primary`, `secondary`).

---

## 10. Summary Verification of Inspected Files

This dossier was compiled following complete automated and manual inspection of the following workspace source files:

* **Backend Files Inspected:**
  * `backend/app/main.py` (FastAPI app configuration & CORS)
  * `backend/app/core/config.py` (Pydantic Settings & environment variables)
  * `backend/app/api/routes.py` (Endpoints: `/routes`, `/rank`, `/geocode`, `/environment`, `/refresh`, `/health`)
  * `backend/app/algorithm/ranking_engine.py` (In-house multi-criteria & Pareto ranking engine)
  * `backend/app/services/routing_service.py` (ORS pedestrian directions & metadata enrichment)
  * `backend/app/services/environmental_service.py` (Open-Meteo batch sampling, AQ & weather)
  * `backend/app/services/greenery_service.py` (Overpass greenery buffer & Haversine distance)
  * `backend/app/services/traffic_service.py` (OSM static road hierarchy proxy & TomTom flow)
  * `backend/app/services/shade_service.py` (NOAA solar position & defensible 3D shade check)
  * `backend/app/services/geocoding_service.py` (Rate-limited Nominatim geocoder with TTL cache)
  * `backend/app/schemas/` (`coordinates.py`, `routes.py`, `environment.py`, `geocoding.py`, `preferences.py`)
  * `backend/requirements.txt` & `backend/.env`
* **Test Suite Files Inspected & Executed:**
  * `backend/tests/test_routes.py`
  * `backend/tests/test_geocoding.py`
  * `backend/tests/test_environment.py`
  * `backend/tests/test_algorithm.py`
  * `backend/tests/test_greenery_and_traffic.py`
  * `backend/tests/test_shade.py`
  * `backend/tests/test_time_and_freshness.py`
  * **Result:** **72 passed, 1 warning (deprecation notice for httpx testclient) in 10.60s.**
* **Frontend Files Inspected & Built:**
  * `frontend/package.json` & `frontend/vite.config.js`
  * `frontend/src/App.jsx`, `frontend/src/App.css`, `frontend/src/main.jsx`
  * `frontend/src/components/MapView.jsx`
  * `frontend/src/components/Sidebar.jsx`
  * `frontend/src/components/RouteComparisonTable.jsx`
  * `frontend/src/components/EnvironmentalPanel.jsx`
  * `frontend/src/components/StatusBadge.jsx`
  * `frontend/src/services/routingService.js`
  * `frontend/src/services/geocodingService.js`
  * `frontend/src/services/environmentService.js`
  * **Result:** `oxlint` found **0 warnings, 0 errors** across 11 files; `vite build` completed in **1.04s** producing clean production bundles.
* **Academic Literature Documentation:**
  * `RESEARCH_GAPS.md` (Systematic review of 24 papers and 5 foundational gaps)
  * `README.md` (Project setup and architecture specification)

* **Unverified / External Details Not Present in Codebase:**
  * Live TomTom Traffic Flow API key (`TOMTOM_TRAFFIC_API_KEY`) is not populated in `.env`; system properly operates in verified static road hierarchy proxy mode.
  * Microscale 3D LiDAR Digital Surface Models are not present in the repository; system properly enforces academic defensibility by withholding unmapped shade scores.
