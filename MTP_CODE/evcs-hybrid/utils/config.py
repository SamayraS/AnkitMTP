"""
Configuration constants and data structures for the EVCS hybrid optimization project.

This module centralizes tunable parameters and provides a `Tariff` dataclass
to pass pricing configurations between modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ----------------------
# Global default params
# ----------------------
DEFAULT_SEED: int = 42
DEFAULT_NUM_SITES: int = 20
DEFAULT_MAX_ITERS_BENDERS: int = 20
DEFAULT_MIN_SEPARATION_KM: float = 0.5
DEFAULT_MAX_CANDIDATES: int = 400

# NSGA-II parameters
NSGA_POP_SIZE: int = 60
NSGA_NGEN: int = 60
NSGA_CX_PB: float = 0.9
NSGA_MUT_PB: float = 0.2

# Pricing bounds (simple TOU with 3 periods)
PRICE_MIN: float = 0.05  # $/kWh
PRICE_MAX: float = 0.80  # $/kWh
BASELINE_PRICE: float = 0.20  # $/kWh baseline
MARGINAL_COST: float = 0.12  # $/kWh cost proxy (energy+losses)

# Demand modeling
AMENITY_BUFFER_M: float = 400.0
CENTRALITY_SAMPLE_LIMIT: int = 8000


@dataclass
class Tariff:
    """Simple Time-Of-Use tariff with three periods: off-peak, mid-peak, peak.

    Attributes
    ----------
    prices: list[float]
        Prices in $/kWh for [off_peak, mid_peak, peak].
    labels: list[str]
        Human-readable labels for the periods.
    baseline: float
        Baseline price for reference (e.g., current average retail rate).
    marginal_cost: float
        Approximate marginal cost of energy procurement in $/kWh.
    """

    prices: List[float] = field(default_factory=lambda: [0.15, 0.20, 0.30])
    labels: List[str] = field(default_factory=lambda: ["off_peak", "mid_peak", "peak"])
    baseline: float = BASELINE_PRICE
    marginal_cost: float = MARGINAL_COST


__all__ = [
    "Tariff",
    "DEFAULT_SEED",
    "DEFAULT_NUM_SITES",
    "DEFAULT_MAX_ITERS_BENDERS",
    "DEFAULT_MIN_SEPARATION_KM",
    "DEFAULT_MAX_CANDIDATES",
    "NSGA_POP_SIZE",
    "NSGA_NGEN",
    "NSGA_CX_PB",
    "NSGA_MUT_PB",
    "PRICE_MIN",
    "PRICE_MAX",
    "BASELINE_PRICE",
    "MARGINAL_COST",
    "AMENITY_BUFFER_M",
    "CENTRALITY_SAMPLE_LIMIT",
]



