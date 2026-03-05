"""
Master problem: Benders-like ILP for selecting EVCS sites maximizing demand coverage
with simple separation cuts to discourage clustering.

This is a pragmatic, minimal implementation: binary selection per candidate, objective
weights are demand scores. After each solve, we add a cut forbidding pairs that are
closer than a threshold until no violations or max iterations reached.
"""

from __future__ import annotations

from typing import List, Tuple

import geopandas as gpd
import pandas as pd
from pulp import LpBinary, LpMaximize, LpProblem, LpStatus, LpVariable, value

from utils.config import DEFAULT_MAX_ITERS_BENDERS, DEFAULT_MIN_SEPARATION_KM
from utils.helpers import haversine_km, pairwise, setup_logger


def solve_master_benders(
    candidates: gpd.GeoDataFrame,
    demand_scores: pd.DataFrame,
    n_sites: int,
    min_separation_km: float = DEFAULT_MIN_SEPARATION_KM,
    max_iters: int = DEFAULT_MAX_ITERS_BENDERS,
) -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
    """Solve a Benders-like placement ILP with pairwise separation cuts.

    Parameters
    ----------
    candidates: GeoDataFrame
        Columns: ['cand_id', 'geometry']
    demand_scores: DataFrame
        Columns: ['cand_id', 'demand_score']
    n_sites: int
        Number of stations to select.
    min_separation_km: float
        Minimum allowed separation between any two selected sites.
    max_iters: int
        Maximum number of cut-adding iterations.

    Returns
    -------
    (selected_df, cuts)
        selected_df includes columns ['cand_id', 'demand_score', 'geometry', 'selected'] for selected ones.
        cuts is the list of pairwise cuts added (cand_id_i, cand_id_j).
    """
    logger = setup_logger()

    cand = candidates[["cand_id", "geometry"]].merge(demand_scores, on="cand_id", how="left")
    cand["demand_score"] = cand["demand_score"].fillna(0.0)
    cand = cand.reset_index(drop=True)

    # Precompute close pairs under threshold to potentially cut later
    close_pairs: List[Tuple[str, str]] = []
    for a, b in pairwise(cand["cand_id"].tolist()):
        ga = cand.loc[cand["cand_id"] == a, "geometry"].iloc[0]
        gb = cand.loc[cand["cand_id"] == b, "geometry"].iloc[0]
        d = haversine_km(ga.y, ga.x, gb.y, gb.x)
        if d < min_separation_km:
            close_pairs.append((a, b))

    added_cuts: List[Tuple[str, str]] = []

    for it in range(max_iters):
        model = LpProblem("EVCS_Placement", LpMaximize)
        x = {cid: LpVariable(f"x_{cid}", lowBound=0, upBound=1, cat=LpBinary) for cid in cand["cand_id"]}

        # Objective: maximize sum(demand_score * x)
        model += sum(float(cand.loc[cand["cand_id"] == cid, "demand_score"].iloc[0]) * x[cid] for cid in x)

        # Cardinality constraint
        model += sum(x.values()) == n_sites, "select_n_sites"

        # Add separation cuts accumulated so far
        for (a, b) in added_cuts:
            model += x[a] + x[b] <= 1, f"sep_cut_{a}_{b}"

        model.solve()  # default CBC if available via PuLP
        status = LpStatus[model.status]
        logger.info(f"Master iteration {it+1}: status={status}, objective={value(model.objective):.4f}")
        if status not in ("Optimal", "Integer Feasible"):
            break

        chosen = [cid for cid, var in x.items() if var.value() is not None and var.value() > 0.5]

        # Check for new violations among chosen
        violation = None
        for i in range(len(chosen)):
            for j in range(i + 1, len(chosen)):
                a, b = chosen[i], chosen[j]
                ga = cand.loc[cand["cand_id"] == a, "geometry"].iloc[0]
                gb = cand.loc[cand["cand_id"] == b, "geometry"].iloc[0]
                d = haversine_km(ga.y, ga.x, gb.y, gb.x)
                if d < min_separation_km and (a, b) not in added_cuts and (b, a) not in added_cuts:
                    violation = (a, b)
                    break
            if violation:
                break

        if violation is None:
            # Done
            cand["selected"] = cand["cand_id"].isin(chosen)
            return cand[cand["selected"]].copy(), added_cuts
        else:
            logger.info(f"Adding separation cut for pair: {violation}")
            added_cuts.append(violation)

    # Return best found (may be last solution)
    chosen = [cid for cid in cand["cand_id"] if cid in x and x[cid].value() is not None and x[cid].value() > 0.5]
    cand["selected"] = cand["cand_id"].isin(chosen)
    return cand[cand["selected"]].copy(), added_cuts


__all__ = ["solve_master_benders"]


