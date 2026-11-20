"""Transparent Multi-Criteria Pedestrian Route Ranking Engine
Evaluates candidate walking routes against user-selected environmental and distance factors.

Core Architectural Guarantees:
1. Zero ML: Completely deterministic, reproducible, and mathematically transparent.
2. No Manual Numeric Weights: Eliminates user cognitive burden via an equal-priority normalized model.
3. Explicit Algorithmic Design Choice: Transparently declares that equal weighting is a system
   design heuristic, not an inferred personal psychological preference.
4. Pareto Dominance: Formally identifies dominated alternatives (worse on >=1 factor, not better on any).
5. Non-Contamination & Unit Safety: Never adds raw incompatible units or converts missing data to zeros.
6. Transparent Defaults: Applies a balanced baseline across all available supported factors and distance
   when no preferences are selected, without claiming absolute health optimality.
7. Missing-Data Resilience: Transparently reports unavailable factors, excludes them from scoring,
   or withholds confident recommendations when critical data is absent.
8. Deterministic Tie-Breaking: Uses walking distance and stable route IDs for 100% reproducible ordering.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from app.schemas.preferences import (
    FactorMetricDetail,
    MetricChange,
    PreferenceSelection,
    RankedRoute,
    ReevaluationSummary,
    RouteComparisonRow,
    RouteRankingResponse,
)
from app.schemas.routes import RouteModel


# Registry of Supported Environmental & Routing Factors
FACTOR_SPECS: Dict[str, Dict[str, Any]] = {
    "air_quality": {
        "label": "Air Quality",
        "better_direction": "lower",  # Lower EAQI / PM2.5 concentration is cleaner
        "unit": "EAQI",
        "min_bound": 0.0,
        "max_bound": 150.0,
        "description": "European Air Quality Index / Particulate Matter (lower is cleaner)",
    },
    "temperature": {
        "label": "Thermal Comfort / Heat",
        "better_direction": "lower",  # Lower apparent temperature is preferred for heat stress avoidance
        "unit": "°C",
        "min_bound": -30.0,
        "max_bound": 60.0,
        "description": "Apparent 'feels-like' temperature (lower heat exposure is preferred)",
    },
    "traffic_exposure": {
        "label": "Traffic Exposure",
        "better_direction": "lower",  # Lower motor vehicle exposure is safer & quieter
        "unit": "index (0-100)",
        "min_bound": 0.0,
        "max_bound": 100.0,
        "description": "Estimated proximity to vehicular traffic and roadway classification",
    },
    "greenery": {
        "label": "Greenery & Parks",
        "better_direction": "higher",  # Higher vegetation and park presence is preferred
        "unit": "%",
        "min_bound": 0.0,
        "max_bound": 100.0,
        "description": "Tree canopy, urban park buffers, and vegetation presence along route",
    },
    "walking_distance": {
        "label": "Walking Distance",
        "better_direction": "lower",  # Shorter route requires less physical exertion and time
        "unit": "m",
        "min_bound": 0.0,
        "max_bound": 100000.0,
        "description": "Total pedestrian pathway distance in metres",
    },
}

ALGORITHMIC_EXPLANATION = (
    "Algorithm Formulation & Documentation:\n"
    "1. Factor Directionality: Each factor has a mathematically defined favorable direction (e.g., lower "
    "air pollution/heat/distance vs. higher greenery).\n"
    "2. Dimensionless Normalization: Raw values are clipped to physical bounds to prevent outlier distortion, "
    "then normalized onto [0.0, 1.0] across candidate routes using min-max relative scaling. A score of 1.0 "
    "denotes the most favorable candidate on that criterion, while 0.0 denotes the least favorable. If all "
    "candidates are identical on a factor, all receive 1.0.\n"
    "3. No Incompatible Unit Mixing: Raw measurements (metres, °C, EAQI) are NEVER added directly, and missing "
    "data is NEVER treated as zero.\n"
    "4. Pareto Dominance: Route A dominates Route B if A is no worse than B on all evaluated criteria and "
    "strictly superior on at least one. Non-dominated routes are always prioritized over dominated routes.\n"
    "5. Equal-Priority Ranking Rule: Non-dominated routes are scored via the arithmetic mean of normalized scores "
    "across active factors: Score(R) = (1/k) * sum(normalized_score_f). Equal priority (1/k) is an explicit "
    "algorithmic design choice to eliminate arbitrary user weight guessing, NOT a discovered psychological "
    "preference.\n"
    "6. Deterministic Tie-Breaking: Ties in score are broken first by walking distance (shorter is better), "
    "and then by alphabetical route ID to guarantee 100% reproducible output for identical inputs.\n"
    "7. Missing Data Policy: If a selected factor lacks data from providers, it is transparently reported and "
    "excluded from scoring. If all selected factors lack data, a confident recommendation is withheld and "
    "the distance baseline is applied.\n"
    "8. Default Rule: When no preferences are selected, the system evaluates all available environmental factors "
    "and distance without claiming to find an absolute healthiest path."
)


def extract_raw_metric(route: RouteModel, factor: str) -> Optional[float]:
    """Safely extract raw numerical metric for a specific factor from a route.
    Never substitutes missing data with zero.
    """
    # 1. Check pre-populated available_environmental_metrics dictionary
    if route.available_environmental_metrics and factor in route.available_environmental_metrics:
        val = route.available_environmental_metrics.get(factor)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass

    # 2. Direct route attribute fallbacks
    if factor == "walking_distance":
        return float(route.distance_m)

    env = route.environment
    if not env:
        return None

    if factor == "air_quality":
        if env.air_quality:
            if env.air_quality.european_aqi and env.air_quality.european_aqi.value is not None:
                return float(env.air_quality.european_aqi.value)
            if env.air_quality.pm2_5 and env.air_quality.pm2_5.value is not None:
                return float(env.air_quality.pm2_5.value)
        return None

    if factor == "temperature":
        if env.weather:
            if env.weather.apparent_temperature_c is not None:
                return float(env.weather.apparent_temperature_c)
            if env.weather.temperature_c is not None:
                return float(env.weather.temperature_c)
        return None

    if factor == "greenery":
        if env.greenery and env.greenery.score is not None:
            return float(env.greenery.score)
        return None

    if factor == "traffic_exposure":
        if env.traffic_exposure and env.traffic_exposure.score is not None:
            return float(env.traffic_exposure.score)
        return None

    return None


def normalize_factor_values(
    routes: List[RouteModel],
    factor: str,
) -> Dict[str, Optional[float]]:
    """Normalize raw values for a single factor across all routes onto [0.0, 1.0].
    Higher normalized score always indicates a more favorable outcome.

    Handles:
    - Outliers via clipping to physical bounds.
    - Zero variance (min == max) -> maps all to 1.0.
    - Missing values -> remains None (never 0.0).
    """
    spec = FACTOR_SPECS[factor]
    direction = spec["better_direction"]
    min_b = spec["min_bound"]
    max_b = spec["max_bound"]

    raw_map: Dict[str, Optional[float]] = {}
    valid_vals: List[float] = []

    for r in routes:
        raw = extract_raw_metric(r, factor)
        if raw is not None:
            # Clip outlier to valid range
            clipped = max(min_b, min(max_b, raw))
            raw_map[r.id] = clipped
            valid_vals.append(clipped)
        else:
            raw_map[r.id] = None

    if not valid_vals:
        return {r.id: None for r in routes}

    v_min = min(valid_vals)
    v_max = max(valid_vals)
    span = v_max - v_min

    scores: Dict[str, Optional[float]] = {}
    for r in routes:
        val = raw_map[r.id]
        if val is None:
            scores[r.id] = None
        elif span < 1e-6:
            # All candidates identical on this factor: full score
            scores[r.id] = 1.0
        else:
            if direction == "lower":
                # Lower raw value is better: min gets 1.0, max gets 0.0
                scores[r.id] = round((v_max - val) / span, 4)
            else:
                # Higher raw value is better: max gets 1.0, min gets 0.0
                scores[r.id] = round((val - v_min) / span, 4)

    return scores


def compute_pareto_dominance(
    routes: List[RouteModel],
    active_factors: List[str],
    normalized_scores: Dict[str, Dict[str, Optional[float]]],
) -> Tuple[Set[str], Dict[str, List[str]]]:
    """Identify Pareto-dominated routes across the active evaluated factors.

    Route A dominates Route B if and only if:
    1. A is no worse than B on EVERY active factor (score_A >= score_B - eps).
    2. A is strictly better than B on AT LEAST ONE active factor (score_A > score_B + eps).

    Returns:
        (dominated_route_ids, map_of_route_id_to_dominating_route_ids)
    """
    if not active_factors or len(routes) <= 1:
        return set(), {r.id: [] for r in routes}

    dominated_ids: Set[str] = set()
    dominated_by_map: Dict[str, List[str]] = {r.id: [] for r in routes}
    eps = 1e-4

    for i, a in enumerate(routes):
        for j, b in enumerate(routes):
            if i == j:
                continue

            # Compare Route A against Route B across all active factors
            no_worse_on_all = True
            strictly_better_on_one = False

            for f in active_factors:
                s_a = normalized_scores[f].get(a.id)
                s_b = normalized_scores[f].get(b.id)

                if s_a is None or s_b is None:
                    # Incomplete comparison on this factor; cannot establish strict dominance
                    no_worse_on_all = False
                    break

                if s_a < s_b - eps:
                    no_worse_on_all = False
                    break
                elif s_a > s_b + eps:
                    strictly_better_on_one = True

            if no_worse_on_all and strictly_better_on_one:
                dominated_ids.add(b.id)
                if a.id not in dominated_by_map[b.id]:
                    dominated_by_map[b.id].append(a.id)

    return dominated_ids, dominated_by_map


def generate_trade_off_summary(
    route: RouteModel,
    all_routes: List[RouteModel],
    rank: int,
    is_pareto_dominated: bool,
    dominating_ids: List[str],
    active_factors: List[str],
    factor_details: Dict[str, FactorMetricDetail],
) -> Tuple[List[str], str]:
    """Generate human-readable reasons and concise trade-off summary for a route."""
    reasons: List[str] = []
    trade_off_parts: List[str] = []

    # 1. Pareto Dominance Status
    if is_pareto_dominated:
        dom_names = [r.name for r in all_routes if r.id in dominating_ids]
        dom_str = ", ".join(dom_names) if dom_names else "another candidate route"
        reasons.append(f"Pareto-dominated alternative: strictly inferior or equal to {dom_str} across evaluated criteria.")
        trade_off_parts.append(f"Dominated by {dom_str} (offers no distinct advantage).")
    else:
        reasons.append("Pareto-optimal alternative: sits on the non-dominated multi-criteria efficiency frontier.")

    # 2. Factor-Specific Trade-offs vs Best / Other routes
    for f in active_factors:
        detail = factor_details.get(f)
        if not detail or detail.raw_value is None:
            continue

        raw = detail.raw_value
        unit = detail.unit
        label = detail.label
        direction = detail.better_direction

        # Find best route for this specific factor
        all_vals = [
            (r, extract_raw_metric(r, f))
            for r in all_routes
            if extract_raw_metric(r, f) is not None
        ]
        if not all_vals:
            continue

        best_route, best_val = (
            min(all_vals, key=lambda x: x[1])
            if direction == "lower"
            else max(all_vals, key=lambda x: x[1])
        )

        is_best_on_factor = abs(raw - best_val) < 1e-4

        if is_best_on_factor:
            reasons.append(f"Top-rated for {label}: best outcome ({raw} {unit}).")
            if rank == 1:
                trade_off_parts.append(f"Best {label} ({raw} {unit})")
        else:
            diff = abs(raw - best_val)
            pct = round((diff / best_val) * 100, 1) if best_val > 0 else 0
            if direction == "lower":
                reasons.append(f"{label}: {raw} {unit} (+{pct}% vs best {best_val} {unit}).")
                if pct > 5:
                    trade_off_parts.append(f"+{pct}% {label}")
            else:
                reasons.append(f"{label}: {raw} {unit} (-{pct}% vs best {best_val} {unit}).")
                if pct > 5:
                    trade_off_parts.append(f"-{pct}% {label}")

    # Build concise single-line trade-off summary
    if rank == 1:
        if is_pareto_dominated:
            trade_off_summary = "Recommended baseline, though technically dominated by alternative path."
        elif trade_off_parts:
            trade_off_summary = f"Best overall balance: {', '.join(trade_off_parts)}."
        else:
            trade_off_summary = f"Optimal choice for selected criteria ({route.distance_km} km)."
    else:
        if is_pareto_dominated:
            trade_off_summary = f"Dominated alternative ({route.distance_km} km); offers no advantage."
        elif trade_off_parts:
            trade_off_summary = f"Trade-off: {', '.join(trade_off_parts)} relative to top route."
        else:
            trade_off_summary = f"Viable alternative corridor ({route.distance_km} km)."

    return reasons, trade_off_summary


def rank_routes(
    routes: List[RouteModel],
    preferences: Optional[PreferenceSelection] = None,
) -> RouteRankingResponse:
    """Execute transparent multi-criteria evaluation and ranking on candidate walking routes.

    Args:
        routes: List of candidate walking routes with metrics.
        preferences: User-selected environmental criteria (or default if None).

    Returns:
        RouteRankingResponse with deterministic ranks, Pareto analysis, trade-offs, and comparison matrix.
    """
    if not routes:
        return RouteRankingResponse(
            ranked_routes=[],
            selected_factors=[],
            active_evaluation_factors=[],
            algorithmic_explanation=ALGORITHMIC_EXPLANATION,
        )

    prefs = preferences or PreferenceSelection()
    selected_factors = prefs.active_factors()
    is_default = (len(selected_factors) == 0) or prefs.no_preference

    # 1. Determine active evaluation factors
    warnings: List[str] = []
    missing_selected: List[str] = []

    if is_default:
        # Transparent Default Baseline: Evaluate all factors that have valid data across all routes, + distance
        candidate_factors = ["walking_distance", "air_quality", "temperature", "greenery", "traffic_exposure"]
        active_factors = []
        for f in candidate_factors:
            has_data_on_all = all(extract_raw_metric(r, f) is not None for r in routes)
            if has_data_on_all:
                active_factors.append(f)
            else:
                # Check if at least one route has data
                has_any_data = any(extract_raw_metric(r, f) is not None for r in routes)
                if not has_any_data:
                    pass  # Silently omit unmeasured factor in default mode

        if "walking_distance" not in active_factors:
            active_factors.append("walking_distance")
    else:
        # User selected specific preferences
        active_factors = []
        for f in selected_factors:
            has_data_on_all = all(extract_raw_metric(r, f) is not None for r in routes)
            if has_data_on_all:
                active_factors.append(f)
            else:
                missing_selected.append(f)
                label = FACTOR_SPECS[f]["label"]
                warnings.append(
                    f"Selected factor '{label}' is unavailable from external data providers for this route "
                    "corridor and has been transparently excluded from the ranking evaluation."
                )

    # 2. Check for total lack of selected data
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

    # 3. Compute normalized scores for all supported factors
    all_supported_factors = list(FACTOR_SPECS.keys())
    normalized_scores: Dict[str, Dict[str, Optional[float]]] = {}
    for f in all_supported_factors:
        normalized_scores[f] = normalize_factor_values(routes, f)

    # 4. Compute Pareto Dominance on active evaluation factors
    dominated_ids, dominated_by_map = compute_pareto_dominance(
        routes, active_factors, normalized_scores
    )

    # 5. Compute Equal-Priority Composite Score across active factors
    # Score(R) = (1 / |active_factors|) * sum(normalized_score(R, f))
    composite_scores: Dict[str, float] = {}
    k = max(1, len(active_factors))

    for r in routes:
        factor_sum = 0.0
        for f in active_factors:
            s = normalized_scores[f].get(r.id)
            factor_sum += s if s is not None else 0.0
        composite_scores[r.id] = round(factor_sum / k, 4)

    # 6. Deterministic Sort Key
    # Sort order:
    # 1. Non-dominated routes rank before dominated routes (0 before 1)
    # 2. Higher composite score descending (-score)
    # 3. Tie-breaker 1: Shortest walking distance (distance_m ascending)
    # 4. Tie-breaker 2: Stable route ID (id ascending)
    def sort_key(r: RouteModel):
        is_dom = 1 if r.id in dominated_ids else 0
        score = composite_scores.get(r.id, 0.0)
        dist = round(r.distance_m, 1)
        return (is_dom, -score, dist, r.id)

    sorted_routes = sorted(routes, key=sort_key)

    # 7. Construct RankedRoute instances
    ranked_route_objects: List[RankedRoute] = []
    comparison_rows: List[RouteComparisonRow] = []

    for rank_idx, r in enumerate(sorted_routes, start=1):
        is_dom = r.id in dominated_ids
        dom_by = dominated_by_map.get(r.id, [])
        score = composite_scores[r.id]
        is_rec = (rank_idx == 1 and not withheld_rec)

        if is_rec:
            status_desc = "Recommended (Rank 1)"
        elif not is_dom:
            status_desc = f"Pareto-Optimal Alternative (Rank {rank_idx})"
        else:
            status_desc = f"Dominated Alternative (Rank {rank_idx})"

        # Factor details for this route
        factor_details: Dict[str, FactorMetricDetail] = {}
        for f in all_supported_factors:
            spec = FACTOR_SPECS[f]
            raw_v = extract_raw_metric(r, f)
            norm_v = normalized_scores[f].get(r.id)
            is_avail = (raw_v is not None)
            factor_details[f] = FactorMetricDetail(
                factor=f,
                label=spec["label"],
                raw_value=raw_v,
                unit=spec["unit"],
                better_direction=spec["better_direction"],
                normalized_score=norm_v,
                is_available=is_avail,
                status_note="Available" if is_avail else "Missing / unrecorded by provider",
            )

        reasons, trade_offs = generate_trade_off_summary(
            route=r,
            all_routes=routes,
            rank=rank_idx,
            is_pareto_dominated=is_dom,
            dominating_ids=dom_by,
            active_factors=active_factors,
            factor_details=factor_details,
        )

        ranked_r = RankedRoute(
            **r.model_dump(),
            rank=rank_idx,
            multi_criteria_score=score,
            is_recommended=is_rec,
            is_pareto_dominated=is_dom,
            dominated_by=dom_by,
            recommendation_status=status_desc,
            reasons=reasons,
            trade_offs=trade_offs,
            factor_details=factor_details,
        )
        ranked_route_objects.append(ranked_r)

        # Comparison row for table display
        comparison_rows.append(
            RouteComparisonRow(
                route_id=r.id,
                route_name=r.name,
                rank=rank_idx,
                is_recommended=is_rec,
                is_pareto_dominated=is_dom,
                distance_km=r.distance_km,
                duration_min=r.duration_min,
                walking_distance_m=r.distance_m,
                distance_score=normalized_scores["walking_distance"].get(r.id),
                air_quality_raw=extract_raw_metric(r, "air_quality"),
                air_quality_score=normalized_scores["air_quality"].get(r.id),
                temperature_c=extract_raw_metric(r, "temperature"),
                temperature_score=normalized_scores["temperature"].get(r.id),
                traffic_score_raw=extract_raw_metric(r, "traffic_exposure"),
                traffic_score=normalized_scores["traffic_exposure"].get(r.id),
                greenery_raw=extract_raw_metric(r, "greenery"),
                greenery_score=normalized_scores["greenery"].get(r.id),
                overall_score=score,
            )
        )

    return RouteRankingResponse(
        ranked_routes=ranked_route_objects,
        selected_factors=selected_factors,
        active_evaluation_factors=active_factors,
        missing_selected_factors=missing_selected,
        is_default_evaluation=is_default,
        confidence=confidence,
        withheld_recommendation=withheld_rec,
        algorithmic_explanation=ALGORITHMIC_EXPLANATION,
        comparison_matrix=comparison_rows,
        warnings=warnings,
    )


def compute_reevaluation_summary(
    old_routes: List[RouteModel],
    new_ranking: RouteRankingResponse,
    old_rank_1_id: Optional[str] = None,
) -> ReevaluationSummary:
    """Compare previous candidate routes with newly refreshed routes to explain changes.

    Explains which data changed and whether the recommendation changed.
    Affirms that this is a pre-trip re-evaluation rather than in-walk live navigation.
    """
    old_map = {r.id: r for r in old_routes}
    metric_changes: List[MetricChange] = []

    factor_units = {
        "air_quality": "EAQI",
        "temperature": "°C",
        "traffic_exposure": "index",
        "greenery": "%",
        "walking_distance": "m",
    }

    for ranked_r in new_ranking.ranked_routes:
        old_r = old_map.get(ranked_r.id)
        if not old_r:
            continue

        for f, unit in factor_units.items():
            old_val = extract_raw_metric(old_r, f)
            new_val = extract_raw_metric(ranked_r, f)

            if old_val is not None and new_val is not None:
                diff = new_val - old_val
                if abs(diff) >= 0.05:
                    sign = "+" if diff > 0 else ""
                    change_desc = (
                        f"{FACTOR_SPECS[f]['label']} changed from {old_val} to {new_val} {unit} ({sign}{diff:.1f})"
                    )
                    metric_changes.append(
                        MetricChange(
                            route_id=ranked_r.id,
                            route_name=ranked_r.name,
                            factor=f,
                            previous_value=old_val,
                            new_value=new_val,
                            unit=unit,
                            change_summary=change_desc,
                        )
                    )
            elif (old_val is None) != (new_val is None):
                status_txt = (
                    f"{FACTOR_SPECS[f]['label']} transitioned from "
                    f"{'unavailable' if old_val is None else str(old_val)} to "
                    f"{'unavailable' if new_val is None else str(new_val)}"
                )
                metric_changes.append(
                    MetricChange(
                        route_id=ranked_r.id,
                        route_name=ranked_r.name,
                        factor=f,
                        previous_value=old_val,
                        new_value=new_val,
                        unit=unit,
                        change_summary=status_txt,
                    )
                )

    new_rank_1_id = new_ranking.ranked_routes[0].id if new_ranking.ranked_routes else None
    if old_rank_1_id and new_rank_1_id:
        rec_changed = (old_rank_1_id != new_rank_1_id)
        if rec_changed:
            rec_note = f"Recommendation changed: Route {new_rank_1_id} is now ranked #1 (previously {old_rank_1_id})."
        else:
            rec_note = f"Recommendation unchanged: Route {new_rank_1_id} remains the optimal recommendation (Rank #1)."
    elif new_rank_1_id:
        rec_changed = False
        rec_note = f"Recommendation: Route {new_rank_1_id} is ranked #1."
    else:
        rec_changed = False
        rec_note = "No candidate routes evaluated."

    return ReevaluationSummary(
        previous_recommended_route_id=old_rank_1_id,
        new_recommended_route_id=new_rank_1_id,
        recommendation_changed=rec_changed,
        recommendation_change_note=rec_note,
        metric_changes=metric_changes,
        has_changes=bool(metric_changes or rec_changed),
    )
