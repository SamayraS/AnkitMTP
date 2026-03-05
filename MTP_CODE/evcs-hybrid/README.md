# EVCS Hybrid Optimization (Placement + Pricing)

Minimal, runnable project implementing the spirit of the 2025 Applied Energy paper
“Hybrid optimization of EV charging station placement and pricing using Benders’ decomposition and NSGA-II.”

This open-data pipeline runs end-to-end for any city string resolvable by OpenStreetMap.

## Structure

```
 evcs-hybrid/
 ├── data/
 │   ├── fetch_osm.py          # road graph, POIs, existing EVCS
 │   └── demand_estimation.py  # demand field proxy
 ├── models/
 │   ├── master_benders.py     # ILP for station placement
 │   └── sub_nsga2.py          # NSGA-II pricing subproblem
 ├── utils/
 │   ├── config.py             # constants, tariff dataclass
 │   └── helpers.py            # misc helpers
 ├── outputs/                  # generated results (auto-created)
 ├── evcs_hybrid.py            # main orchestrator (CLI entrypoint)
 ├── requirements.txt
 └── README.md
```

## Setup

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run

Example for Hefei, Anhui, China:

```bash
python evcs_hybrid.py --city "Hefei, Anhui, China" --n_sites 40 --seed 42
```

Outputs go to `evcs-hybrid/outputs/`:
- `selected_sites.geojson`: chosen sites with demand and optimal TOU prices
- `selected_sites.csv`: same as CSV
- `existing_evcs.geojson`: existing stations from OpenChargeMap (if any)

## Data sources
- OpenStreetMap via `osmnx`
- OpenChargeMap API
- Amenity density/centrality computed on the fly; population proxies can be integrated from WorldPop if desired

## Citation
If you use this code, please cite the paper and data sources:
- Applied Energy (2025): “Hybrid optimization of EV charging station placement and pricing using Benders’ decomposition and NSGA-II.”
- OpenStreetMap contributors
- OpenChargeMap

## Notes
- This is a compact, open-data reference implementation meant to run quickly. It approximates key ideas from the paper rather than reproducing every modeling detail.


