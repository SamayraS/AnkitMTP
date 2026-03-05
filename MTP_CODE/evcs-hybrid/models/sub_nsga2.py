"""
NSGA-II pricing subproblem using deap.

For each selected site, optimize a 3-period TOU price vector:
Objectives (to minimize):
 1) -profit (i.e., maximize profit)
 2) consumer_cost (total spending relative to baseline)
 3) rerouting_penalty (proxy increasing with price vs baseline)

This is a stylized proxy consistent with the paper's spirit, not an exact replica.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from deap import base, creator, tools

from utils.config import (
    NSGA_CX_PB,
    NSGA_MUT_PB,
    NSGA_NGEN,
    NSGA_POP_SIZE,
    PRICE_MAX,
    PRICE_MIN,
    Tariff,
)
from utils.helpers import setup_logger


def _evaluate_individual(ind: List[float], demand_kwh: float, tariff: Tariff) -> Tuple[float, float, float]:
    prices = np.array(ind, dtype=float)
    prices = np.clip(prices, PRICE_MIN, PRICE_MAX)

    # Demand elasticity proxy: higher price reduces energy demanded
    # Linear price-response around baseline
    baseline = max(1e-6, tariff.baseline)
    price_ratio = prices / baseline
    elasticity = -0.3  # mild elasticity
    adjusted_demand = demand_kwh * np.clip(1.0 + elasticity * (price_ratio - 1.0), 0.1, 1.5)

    # Split demand evenly across three periods for simplicity
    period_demand = adjusted_demand / 3.0
    revenue = float(np.sum(prices * period_demand))
    cost = float(np.sum(tariff.marginal_cost * period_demand))
    profit = revenue - cost

    consumer_cost = revenue
    rerouting_penalty = float(np.mean(np.maximum(0.0, prices - baseline)))

    return (-profit, consumer_cost, rerouting_penalty)


def nsga2_optimize_prices(
    site_demands: Dict[str, float],
    tariff: Tariff,
    seed: int = 0,
    pop_size: int = NSGA_POP_SIZE,
    ngen: int = NSGA_NGEN,
) -> Dict[str, Dict[str, float]]:
    """Run NSGA-II to derive TOU prices for each site.

    Returns a dict: site_id -> {p_off, p_mid, p_peak, profit, consumer_cost, rerouting}
    using the best compromise solution (crowding-distance from first front).
    """
    logger = setup_logger()
    rng = np.random.default_rng(seed)

    results: Dict[str, Dict[str, float]] = {}
    for site_id, demand_kwh in site_demands.items():
        creator.create("FitnessMulti", base.Fitness, weights=(-1.0, -1.0, -1.0))
        creator.create("Individual", list, fitness=creator.FitnessMulti)
        toolbox = base.Toolbox()
        toolbox.register("attr_price", rng.uniform, PRICE_MIN, PRICE_MAX)
        toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_price, n=3)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        def eval_ind(ind):
            return _evaluate_individual(ind, demand_kwh=demand_kwh, tariff=tariff)

        toolbox.register("evaluate", eval_ind)
        toolbox.register("mate", tools.cxSimulatedBinaryBounded, low=PRICE_MIN, up=PRICE_MAX, eta=20.0)
        toolbox.register("mutate", tools.mutPolynomialBounded, low=PRICE_MIN, up=PRICE_MAX, eta=20.0, indpb=1/3)
        toolbox.register("select", tools.selNSGA2)

        pop = toolbox.population(n=pop_size)
        # Evaluate initial population before NSGA2 sorting
        invalid = [ind for ind in pop if not ind.fitness.valid]
        fits = map(toolbox.evaluate, invalid)
        for ind, fit in zip(invalid, fits):
            ind.fitness.values = fit
        pop = tools.selNSGA2(pop, len(pop))

        for _ in range(ngen):
            offspring = tools.selTournamentDCD(pop, len(pop))
            offspring = [toolbox.clone(ind) for ind in offspring]
            for i in range(0, len(offspring), 2):
                if rng.random() < NSGA_CX_PB and i + 1 < len(offspring):
                    toolbox.mate(offspring[i], offspring[i + 1])
                    del offspring[i].fitness.values, offspring[i + 1].fitness.values
            for mutant in offspring:
                if rng.random() < NSGA_MUT_PB:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            fits = map(toolbox.evaluate, invalid)
            for ind, fit in zip(invalid, fits):
                ind.fitness.values = fit
            pop = tools.selNSGA2(pop + offspring, pop_size)

        # Choose representative: best by minimal sum of normalized objectives
        fits = np.array([ind.fitness.values for ind in pop], dtype=float)
        mins = fits.min(axis=0)
        maxs = fits.max(axis=0)
        span = np.where(maxs > mins, maxs - mins, 1.0)
        norm = (fits - mins) / span
        scores = norm.sum(axis=1)
        best_idx = int(np.argmin(scores))
        best = pop[best_idx]
        f1, f2, f3 = pop[best_idx].fitness.values

        prices = [float(np.clip(p, PRICE_MIN, PRICE_MAX)) for p in best]
        res = {
            "p_off": prices[0],
            "p_mid": prices[1],
            "p_peak": prices[2],
            "profit": float(-f1),
            "consumer_cost": float(f2),
            "rerouting": float(f3),
        }
        results[site_id] = res

        # Clean creator classes to avoid redefinition when iterating sites
        del creator.Individual
        del creator.FitnessMulti

        logger.info(f"NSGA-II completed for site {site_id}")

    return results


__all__ = ["nsga2_optimize_prices"]


