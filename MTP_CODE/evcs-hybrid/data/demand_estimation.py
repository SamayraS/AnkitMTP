"""
Demand estimation proxies using network betweenness centrality and amenity density.

Outputs a per-candidate demand score in [0, 1] to be used by the master problem.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
from typing import Tuple

from utils.config import AMENITY_BUFFER_M, CENTRALITY_SAMPLE_LIMIT
from utils.helpers import setup_logger


def _betweenness_node_scores(G: nx.Graph, sample_limit: int) -> pd.Series:
    # Work on an undirected projected graph for centrality with reasonable size
    G_proj = ox.project_graph(G)
    if G_proj.number_of_nodes() > sample_limit:
        nodes = list(G_proj.nodes())
        # Sample a subgraph for tractability
        rng = np.random.default_rng(0)
        keep = set(rng.choice(nodes, size=sample_limit, replace=False))
        G_sub = G_proj.subgraph(keep).copy()
    else:
        G_sub = G_proj
    # Use approximation by sampling sources if still large
    k = min(256, max(16, G_sub.number_of_nodes() // 20))
    sources = list(G_sub.nodes())[:k]
    bc = nx.betweenness_centrality(G_sub, k=len(sources), normalized=True, seed=0)
    # Map back to full graph nodes by nearest spatial join
    nodes_gdf, _ = ox.graph_to_gdfs(G_sub)
    nodes_gdf = nodes_gdf.to_crs(epsg=4326)
    nodes_gdf["bc"] = nodes_gdf.index.map(bc).astype(float)
    return nodes_gdf["bc"]


def estimate_demand(G: nx.MultiDiGraph, pois: gpd.GeoDataFrame, candidates: gpd.GeoDataFrame) -> pd.DataFrame:
    """Compute a normalized demand score for each candidate.

    Heuristic: demand = 0.6 * normalized(node betweenness near candidate)
                        + 0.4 * normalized(amenity density in buffer)
    """
    logger = setup_logger()
    logger.info("Estimating demand using centrality + amenity density")

    # Compute node centrality on subgraph and spatially join to candidates
    bc = _betweenness_node_scores(G, CENTRALITY_SAMPLE_LIMIT)
    nodes_full, _ = ox.graph_to_gdfs(G)
    nodes_full = nodes_full.to_crs(epsg=4326)
    nodes_full = nodes_full[["geometry"]].reset_index()
    old_idx_name = nodes_full.columns[0]
    nodes_full = nodes_full.rename(columns={old_idx_name: "node"})

    # Join nearest node to each candidate
    cand = candidates.to_crs(epsg=4326).copy()
    nodes_bc = nodes_full.copy()
    nodes_bc = nodes_bc.merge(bc.rename("bc"), left_on="node", right_index=True, how="left")
    nodes_bc["bc"] = nodes_bc["bc"].fillna(nodes_bc["bc"].median() if not nodes_bc["bc"].isna().all() else 0.0)
    cand = gpd.sjoin_nearest(cand, nodes_bc[["node", "bc", "geometry"]], how="left")

    # Amenity density in buffer
    pois_local = pois.to_crs(3857)
    cand_3857 = cand.to_crs(3857)
    cand_3857["buffer"] = cand_3857.geometry.buffer(AMENITY_BUFFER_M)
    join = gpd.sjoin(pois_local[["geometry"]], gpd.GeoDataFrame(cand_3857[["cand_id", "buffer"]], geometry="buffer"), predicate="within")
    density = join.groupby("cand_id").size().rename("amenity_cnt")
    cand = cand.merge(density, on="cand_id", how="left").fillna({"amenity_cnt": 0})

    # Normalize features
    def _norm(x: pd.Series) -> pd.Series:
        x = x.astype(float)
        lo, hi = x.min(), x.max()
        return (x - lo) / (hi - lo) if hi > lo else pd.Series(np.zeros(len(x)), index=x.index)

    cand["bc_norm"] = _norm(cand["bc"]) 
    cand["amen_norm"] = _norm(cand["amenity_cnt"]) 
    cand["demand_score"] = 0.6 * cand["bc_norm"] + 0.4 * cand["amen_norm"]

    return cand[["cand_id", "demand_score"]].reset_index(drop=True)


__all__ = ["estimate_demand"]



