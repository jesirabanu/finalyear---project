# Research Gaps in AI-Driven Multi-Environmental Personalized Pedestrian Routing

> **Document Type:** Systematic Research Gap Analysis  
> **Project Title:** AI-Driven Multi-Environmental Personalized Pedestrian Routing  
> **Domain:** Urban Informatics, Sustainable Active Mobility, Environmental Health, Multi-Criteria Geographic Information Systems (GIS)  
> **Date:** October 2026  

---

## Executive Summary

Standard pedestrian routing engines (e.g., Google Maps, Apple Maps, baseline OpenRouteService, GraphHopper) operate on a **shortest-distance or shortest-duration paradigm**, treating walking paths solely through the lens of travel time minimization. While effective for motorized vehicles, this model fundamentally fails pedestrians, whose physical bodies are directly exposed to the urban atmospheric environment—inhaling airborne particulates ($\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$), absorbing solar irradiance and heat stress, and enduring acoustic noise.

A synthesis of 24 state-of-the-art research papers across urban microclimate modeling, environmental exposure epidemiology, and smart navigation reveals **five foundational research gaps**. This document synthesizes these gaps, provides literature citations from the active repository corpus, and articulates how this project addresses each gap.

---

## Synthesis Matrix: Literature vs. Research Gaps

| Research Paper / Citation | Primary Focus | Air Quality | Heat & Shade | Greenery / Parks | Noise / Stress | Personalization / MCDA | Core Limitation Identified |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Yin & Le (2026)**, *Transport Reviews* | Systematic review of active travel exposure (94 empirical studies) | ⚠️ Partial | ✅ Primary | ❌ | ✅ Primary | ❌ | Isolated exposures; lack of multi-exposure co-analysis; ignores how exposures shape travel choice. |
| **Vakacherla et al. (2025)**, *Front. Sustain. Cities* | Route guidance to reduce air pollution exposure | ✅ Primary | ❌ | ❌ | ❌ | ⚠️ Single-factor | Focuses exclusively on air pollution; ignores thermal discomfort, solar radiation, and greenery. |
| **Transactions in GIS (2025)** | Solar exposure & shade routing in Heidelberg | ❌ | ✅ Primary | ⚠️ Incidental | ❌ | ⚠️ Heuristic | Single-variable shade optimization; thermal comfort decoupled from air quality. |
| **Antunes (2026)**, *SIMULTECH* | Microclimate-aware routing & shade simulation (Sol-A-Pino) | ❌ | ✅ Primary | ❌ | ❌ | ⚠️ Agent heuristic | Microclimate-only; lacks particulate pollution and open web deployment. |
| **Po, Rollo & Casari (2025)**, *FedCSIS / AIQS* | Low-cost sensor calibration & green routing | ✅ Primary | ❌ | ⚠️ Incidental | ❌ | ⚠️ Single-factor | Heavy reliance on localized sensor networks; lacks global scalability and thermal integration. |
| **GreenAccess-RL (2026)**, *Springer Nature* | Deep reinforcement learning for green corridors | ❌ | ❌ | ✅ Primary | ⚠️ LTS stress | ⚠️ Fixed weights | Critiques fixed-weight MCDA; green corridors often trade off accessibility and microclimate. |
| **Lieu & Guhathakurta (2025)**, *Transp. Res. Part A* | Demographic pedestrian route choice preferences | ❌ | ✅ Primary | ✅ Primary | ✅ Primary | ⚠️ Empirical only | Identified significant demographic divergence in preferences, but developed no algorithmic navigation engine. |
| **Lawrence et al. (2025)**, *J. Transp. & Health* | Quiet pedestrian routing for noise annoyance | ❌ | ❌ | ⚠️ Incidental | ✅ Primary | ⚠️ Single-factor | Quiet routing diverts pedestrians without verifying heat exposure or air quality index. |
| **Helbich et al. (2025)**, *Cities / Elsevier* | Explainable ML for urban traffic noise mapping | ❌ | ❌ | ⚠️ Incidental | ✅ Primary | ❌ No routing | Diagnostic noise estimation only; not operationalized into routing decision engines. |
| **Cavojsky et al. (2025)**, *Procedia Comp. Sci.* | Familiarity-biased pedestrian routing via GPS | ❌ | ❌ | ❌ | ⚠️ Perceived | ✅ GPS history | Biases toward familiar zones; completely blind to environmental pollution and heat. |

---

## Detailed Research Gaps

### 1. Gap 1: The "Single-Environmental Silo" Dilemma (Isolated vs. Multi-Environmental Co-Exposure)

#### Literature Finding
The overwhelming majority of existing environmental routing platforms evaluate environmental hazards in **complete isolation**:
- Air quality routing systems (e.g., Vakacherla et al., 2025; Po et al., 2025) minimize inhaled $\text{PM}_{2.5}$ and $\text{NO}_2$, but routinely divert pedestrians through wide, treeless, asphalt-heavy arterials that maximize solar radiation and thermal distress.
- Thermal comfort and solar shade routing tools (e.g., Transactions in GIS, 2025; Antunes, 2026; Basu et al., 2024) guide walkers under building shadows and street canopies, which frequently coincide with street canyons where vehicular exhaust and particulate matter become trapped.
- Acoustic noise routing engines (e.g., Lawrence et al., 2025; Schori et al., 2025) optimize for decibel reduction without inspecting whether quiet residential alleys lack tree shade or safe pathway infrastructure.

#### The Unaddressed Gap
As systematically documented by **Yin & Le (2026)** in *Transport Reviews*, human health and active travel behavior are shaped by **concurrent co-exposure**. There is a distinct absence of unified, full-stack routing architectures capable of simultaneously querying, harmonizing, and presenting:
1. **Atmospheric pollution** ($\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, European AQI),
2. **Thermal and meteorological stress** (ambient temperature, apparent "feels-like" temperature, solar radiation), and
3. **Urban greenery canopy buffers** (OSM Overpass urban parks and green spaces).

---

### 2. Gap 2: The Cognitive Burden and Mathematical Flaws of Fixed-Weight Multi-Criteria Decision Analysis (MCDA)

#### Literature Finding
When existing routing models attempt to integrate more than one factor, they predominantly rely on classical Multi-Criteria Decision Analysis (MCDA) formulations—such as weighted-sum cost functions ($C = w_1 d + w_2 \text{AQI} + w_3 T$) or basic Analytical Hierarchy Process (AHP).
- As noted in **GreenAccess-RL (2026)**, fixed-weight formulations fail to capture nonlinear real-world trade-offs.
- In user-facing systems, users are forced to specify arbitrary decimal weights (e.g., `"Set Air Quality weight to 0.35 and Thermal Comfort to 0.65"`).

#### The Unaddressed Gap
Pedestrians cannot intuitively answer: *"How many additional micrograms per cubic meter of $\text{PM}_{2.5}$ am I willing to inhale in exchange for 300 meters less walking distance or 2 °C lower temperature?"*
1. **Cognitive Burden:** Forcing numerical weight inputs alienates ordinary citizens and leads to inconsistent, arbitrary route choices.
2. **Artificial Pareto Compromises:** Hardcoded weights obscure the genuine alternatives available on the street network.
3. **Need for Transparent Heuristics:** A critical gap exists for an intuitive, preference-driven decision framework where users simply select qualitative priorities (e.g., Clean Air, Greenery, Thermal Comfort), backed by an explicit, transparent default baseline rule (shortest safe walking distance) when no preferences are activated.

---

### 3. Gap 3: Spatial and Temporal Resolution Mismatch (Regional NWP Grids vs. Street-Canyon Microclimates)

#### Literature Finding
Urban environmental data exists at fundamentally disparate spatial scales:
- **Regional Atmospheric & NWP Models** (e.g., Open-Meteo, Copernicus CAMS, ECMWF): Global coverage, updated hourly, but operating on coarse spatial grid cells ($\approx 11\text{ km}$ for chemical transport models, $\approx 2\text{ to }11\text{ km}$ for meteorological forecasts).
- **Micro-Scale CFD / Ray-Tracing Simulations** (e.g., PedSim microclimate optimization, 2026): Extremely high spatial resolution ($1\text{ to }5\text{ m}$), but computationally prohibitive, requiring hours or days of pre-rendering per square kilometer, rendering them impossible for dynamic, on-demand routing.
- **Low-Cost Sensor Networks (LCS)** (e.g., Po et al., 2025): High temporal resolution, but geographically sparse, subject to drift, uncalibrated in most cities, and unavailable globally.

#### The Unaddressed Gap
Many academic prototypes commit one of two fallacies:
1. **False Precision Claim:** They sample a coarse $11\text{ km}$ model and report it to the user as a street-level sidewalk reading.
2. **Geographical Lock-in:** They calibrate an algorithm to a single equipped neighborhood in Leicester, Bologna, or Fukuoka, making the system inoperable anywhere else.
3. **Architectural Gap:** There is an urgent need for an open-access system that bridges this scale gap transparently: sampling route geometry at representative intervals, performing multi-coordinate batch queries, aggregating route-level exposure summaries, and **explicitly documenting data provenance** (stating whether readings are regional model forecasts or local measurements, without silently fabricating fallback zeros).

---

### 4. Gap 4: Commercial "Shortest-Path Dominance" vs. Human Route Selection

#### Literature Finding
Commercial mapping platforms (Google Maps, Apple Maps, standard OSRM) are engineered primarily for motorized transport or rapid transit connections, where travel impedance is strictly proportional to Euclidean distance or congestion-induced delay.
- Empirical studies (e.g., **Lieu & Guhathakurta, 2025**; **Cavojsky et al., 2025**) prove that pedestrians do not behave like shortest-path automata. Walkers routinely accept a **$5\%\text{ to }15\%$ detour** if the alternative path offers shade, cleaner air, parks, or perceived comfort.
- Furthermore, when commercial APIs return alternative paths, they are often trivial geometric duplicates (e.g., turning left one street earlier), offering no genuine environmental diversity.

#### The Unaddressed Gap
Existing open-source navigation pipelines lack:
1. **Genuine Pedestrian Alternative Generation:** Algorithms configured to demand spatially distinct walking corridors using realistic detour parameters (`weight_factor`, `share_factor`).
2. **Honest Route Availability Reporting:** A systematic policy that refuses to duplicate a single route to simulate fake choices, honestly declaring when only one viable pedestrian corridor exists.

---

### 5. Gap 5: Demographic & Health-Centric Sensitivity Deficit

#### Literature Finding
Environmental vulnerability is not uniform across urban populations:
- Asthmatic individuals, COPD patients, and children face acute pulmonary risk from brief spikes in $\text{PM}_{2.5}$ and $\text{NO}_2$.
- Elderly pedestrians and pregnant individuals experience severe heat strain and cardiovascular vulnerability during midday peak thermal hours (**Basu et al., 2024**).
- Vulnerable road users (VRUs) and mobility-impaired individuals cannot navigate steep slopes or severed sidewalks (**Kaselouris et al., 2025**).

#### The Unaddressed Gap
Mainstream pedestrian routing offers **zero personalization** for environmental sensitivities. There is no lightweight, privacy-preserving routing platform where pedestrians can tailor routes to their physiological vulnerability without invasive biometric tracking.

---

## How Our Project Specifically Bridges These Research Gaps

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        RESEARCH GAP RESOLUTION                            │
├───────────────────────────────┬───────────────────────────────────────────┤
│ Identified Research Gap       │ How Our Architecture Bridges It           │
├───────────────────────────────┼───────────────────────────────────────────┤
│ 1. Single-Environmental Silos │ Multi-Environmental Fusion: Integrates    │
│    (Isolated Air vs Heat)     │ Open-Meteo AQI (PM2.5, PM10, NO2, EAQI) + │
│                               │ Open-Meteo Weather (Temp, Feels-like) +   │
│                               │ OSM Overpass Greenery buffers.            │
├───────────────────────────────┼───────────────────────────────────────────┤
│ 2. Cognitive MCDA Burden      │ Transparent Preference Architecture:      │
│    (Arbitrary numeric weights)│ Users toggle qualitative health factors;  │
│                               │ automated rank-order evaluation with an   │
│                               │ explicit distance-minimizing baseline.    │
├───────────────────────────────┼───────────────────────────────────────────┤
│ 3. Resolution & Provenance    │ Honest Metadata & Batch Spatial Sampling: │
│    Mismatch (Grid vs Street)  │ Samples route geometry; multi-location    │
│                               │ batch requests; full metadata with units, │
│                               │ timestamps, and model resolution notices. │
├───────────────────────────────┼───────────────────────────────────────────┤
│ 4. Shortest-Path Dominance    │ Genuine Detour Alternatives:              │
│    & Fake Alternatives        │ OpenRouteService walking directions with  │
│                               │ genuine alternative paths; never clones   │
│                               │ routes; honest single-route reporting.    │
├───────────────────────────────┼───────────────────────────────────────────┤
│ 5. Universal Non-Personalized │ User-Driven Sensitivity Presets:          │
│    Navigation Routing         │ Tailored to individual vulnerability      │
│                               │ profiles without requiring GPS tracking.  │
└───────────────────────────────┴───────────────────────────────────────────┘
```

---

## Environmental Indicator Methodology: Greenery & Traffic Investigation

### 1. Greenery Corridor Proximity via OpenStreetMap Overpass API
* **OSM Feature Tags Queried**:
  - `leisure` in `[park, garden, nature_reserve, recreation_ground]`
  - `landuse` in `[grass, forest, meadow, village_green, orchard, cemetery]`
  - `natural` in `[wood, tree_row, tree, scrub, grassland]`
* **Corridor Bounding & Server Protection**:
  - Queries are strictly confined to the union bounding box of candidate walking trajectories buffered by $\approx 150-200\text{ m}$ ($\pm 0.002^\circ$).
  - Never queries entire metropolitan areas. Maximum bounding box span is capped at $0.08^\circ$ ($\approx 9\text{ km}$).
  - Strictly adheres to Overpass Public Server Policy: 1 request/second token bucket, 10-second timeout, custom User-Agent, and 15-minute in-memory TTL caching.
* **Corridor Greenery Buffer Metric**:
  - Computes the fraction of route waypoints within a defined $50\text{m}$ buffer distance of mapped green areas:
    $$\text{greenery\_fraction} = \frac{\sum_{i=1}^N \mathbb{I}\left(\min_j \text{dist}(w_i, g_j) \le 50\text{m}\right)}{N}$$
  - Counts adjacent parks ($\le 100\text{m}$) and computes an overall presence score ($0$ to $100\%$).
* **Explicit Scientific Limitation Disclosure**:
  - Proximity to mapped OSM green polygons indicates spatial presence within a corridor buffer only.
  - It is **not** equivalent to a measured Green View Index (GVI), actual canopy density, tree shade quality, or localized microclimatic air-pollution absorption.

### 2. Traffic Exposure: Live Provider Investigation & Defensible Static Proxy
* **Live Traffic Provider Investigation**:
  - **TomTom Traffic Flow API**: Evaluated for road-level real-time speed, free-flow baseline, and congestion ratios ($1.0 - \text{currentSpeed}/\text{freeFlowSpeed}$).
  - **Authentication & Cost**: Requires an API Key (`TOMTOM_TRAFFIC_API_KEY`). Free developer evaluation tier provides 2,500 daily transactions.
  - **Licensing & Usage**: Permitted for non-commercial navigation display. Displays vehicular congestion on adjacent roads to evaluate pedestrian exposure.
* **Defensible Static Infrastructure Proxy (Default / Fallback)**:
  - When live traffic API keys are unconfigured or provider calls fail, the platform employs a **clearly labeled static road infrastructure proxy** derived from OpenStreetMap highway classifications:
    - Arterial Major Roads: `motorway`, `trunk`, `primary`, `secondary` (heavy motorized flow).
    - Minor / Pedestrian Paths: `footway`, `pedestrian`, `living_street`, `residential`.
  - Computes percentage of walking path within $50\text{m}$ of mapped major roadways (`major_road_nearby_pct`).
  - **Strict Architectural Integrity**:
    - Road classification is **never** labeled as live traffic volume, vehicle counts, or transient congestion.
    - Live traffic metrics and static proxy metrics are kept strictly separate in the data model (`is_live_measurement = false`, `metric_type = "static_road_hierarchy_proxy"`).

---

### 3. Time-Aware Environmental Evaluation, Data Freshness & Sidewalk Shade Investigation

#### A. Data Freshness & Configurable Caching
* **Separate Timestamps**: Each measurement distinctly stores its `retrieval_timestamp` (when queried by backend) and `observation_or_forecast_timestamp` (validity hour from model).
* **Provider-Specific Expiries**:
  - Open-Meteo Weather & Air Quality: 15-minute TTL (matches hourly numerical forecast cycles).
  - OpenStreetMap Geometries (Greenery/Roads): 30-minute TTL.
  - TomTom Live Traffic: 5-minute TTL (real-time flow).
* **Resilient Cache Fallback**: When external APIs fail during a manual refresh, previously cached observations are retained with an explicit user-facing stale warning (`is_stale: true`, `stale_warning: "..."`), preventing blank route displays.

#### B. Departure Time & Forecast Temporal Resolution
* **Temporal Resolution**: Open-Meteo provides gridded numerical weather prediction at native **1-hour temporal resolution**. The system aligns user departure times to the nearest hourly forecast step without fabricating sub-hourly or interpolated readings.
* **Temporal Traffic Limit**: Real-time traffic APIs (TomTom Flow) reflect immediate road conditions. Live traffic flow is marked strictly **unavailable** for future departure times (>30 minutes from current time).

#### C. Astronomical Solar Position & Sidewalk Shade Investigation
* **Defensible Solar Position Model**: Uses the deterministic **NOAA Solar Position Algorithm** (Spencer, 1971) to compute solar elevation ($\alpha$) and azimuth ($\gamma$) for route coordinates at departure time:
  - When $\alpha \le 0^\circ$: The sun is below the horizon (nighttime). Direct solar radiation and shade casting are inactive.
  - When $\alpha > 0^\circ$: Sun is in the sky, casting direct physical shadows.
* **Investigation of OpenStreetMap 3D Spatial Inputs**:
  - Microscale pedestrian sidewalk shade modeling requires 3D building heights (tags `height` or `building:levels`), roof profiles, and tree canopy crown diameters (`diameter_crown`).
  - Empirical investigation reveals that across OpenStreetMap globally, >85% to 95% of building footprints lack height attributes, and tree canopy crown geometries are virtually unmapped.
  - **Academic Defensibility Decision**: The system refuses to infer shade from temperature or greenery proximity (which would violate scientific validity). Because corridor 3D height coverage is below the defensible 70% threshold, shade is transparently reported as **`insufficient_spatial_inputs`** and excluded from route ranking to protect scientific integrity.

---

---

## Suggested Academic Contributions for Paper / Thesis

When writing the final thesis, research paper, or conference submission, this gap analysis establishes the following **three novel contributions**:

1. **System Contribution:** The architectural design and open-source implementation of a full-stack, decoupling-compliant multi-environmental pedestrian routing platform combining OpenRouteService, Open-Meteo, and Leaflet.
2. **Methodological Contribution:** A transparent route-geometry spatial sampling and batch-querying technique that computes multi-pollutant and thermal summaries along walking trajectories without incurring computational latency or fabricating missing readings.
3. **Usability Contribution:** Elimination of arbitrary numerical weighting in environmental navigation via a qualitative preference-driven decision framework with documented baseline rules.

---

*Document compiled in `C:\research paper\RESEARCH_GAPS.md` and `C:\final - project\RESEARCH_GAPS.md` for direct inclusion in thesis literature reviews and methodology chapters.*
