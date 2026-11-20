"""Algorithm Package
Multi-criteria pedestrian route evaluation, Pareto-dominance, and transparent ranking.
"""
from app.algorithm.ranking_engine import (
    FACTOR_SPECS,
    ALGORITHMIC_EXPLANATION,
    extract_raw_metric,
    normalize_factor_values,
    compute_pareto_dominance,
    generate_trade_off_summary,
    rank_routes,
)

__all__ = [
    "FACTOR_SPECS",
    "ALGORITHMIC_EXPLANATION",
    "extract_raw_metric",
    "normalize_factor_values",
    "compute_pareto_dominance",
    "generate_trade_off_summary",
    "rank_routes",
]
