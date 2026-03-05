from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import geopandas as gpd
import pandas as pd

from data.fetch_osm import fetch_city_data
from data.demand_estimation import estimate_demand
from models.master_benders import solve_master_benders
from models.sub_nsga2 import nsga2_optimize_prices
from utils.config import DEFAULT_NUM_SITES, DEFAULT_SEED, Tariff
from utils.helpers import ensure_outputs_dir, save_geojson, setup_logger


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hybrid EVCS placement and pricing")
    p.add_argument("--city", type=str, required=True, help="City name, e.g., 'Hefei, Anhui, China'")
    p.add_argument("--n_sites", type=int, default=DEFAULT_NUM_SITES, help="Number of stations to place")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    p.add_argument("--output_dir", type=str, default="evcs-hybrid/outputs", help="Output directory")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logger = setup_logger()

    out_dir = ensure_outputs_dir(args.output_dir)
    logger.info(f"Outputs will be written to: {out_dir}")

    # Step 1: Fetch
    G, pois, existing, candidates = fetch_city_data(args.city)

    # Step 2: Demand
    demand_df = estimate_demand(G, pois, candidates)

    # Step 3: Master placement
    selected_gdf, cuts = solve_master_benders(candidates, demand_df, n_sites=args.n_sites)

    # Step 4: NSGA-II pricing
    tariff = Tariff()
    site_demands: Dict[str, float] = {
        row["cand_id"]: float(row["demand_score"]) * 1000.0  # scale to kWh proxy
        for _, row in selected_gdf.iterrows()
    }
    pricing = nsga2_optimize_prices(site_demands, tariff=tariff, seed=args.seed)

    # Step 5: Save outputs
    selected_out = selected_gdf.copy()
    selected_out["p_off"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("p_off"))
    selected_out["p_mid"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("p_mid"))
    selected_out["p_peak"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("p_peak"))
    selected_out["profit"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("profit"))
    selected_out["consumer_cost"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("consumer_cost"))
    selected_out["rerouting"] = selected_out["cand_id"].map(lambda cid: pricing.get(cid, {}).get("rerouting"))

    # GeoJSON
    save_geojson(selected_out.to_crs(epsg=4326), Path(out_dir) / "selected_sites.geojson")

    # CSV
    selected_out.drop(columns=["geometry"]).to_csv(Path(out_dir) / "selected_sites.csv", index=False)

    # Existing EVCS snapshot
    if not existing.empty:
        save_geojson(existing.to_crs(epsg=4326), Path(out_dir) / "existing_evcs.geojson")

    logger.info("Workflow completed successfully.")


if __name__ == "__main__":
    main()


