# EV Charging Station Optimization for Indore City - Comprehensive Documentation

**Generated:** December 2025
**Project:** EV Charging Station Optimization for Indore City
**Method:** NSGA-II + Benders Decomposition + CAGR Population Model

---

## 1. Executive Summary

*(Source: M.Tech Project Report)*

This document presents a comprehensive optimization study for deploying an Electric Vehicle (EV) Charging Station (EVCS) network across Indore city. The project employs a hybrid approach combining **NSGA-II multi-objective optimization** with **Benders pricing decomposition** to identify cost-effective station placements and dynamic pricing strategies. The population growth model uses **CAGR (Compound Annual Growth Rate)** based on official 2021 census data from the Government of India Data Portal, projecting EV demand through 2031.

**Key Contributions:**
- Integrated CAGR-based population projection model for realistic demand estimation (7.04% annual growth).
- Multi-objective optimization balancing cost, coverage, service distance, and profit.
- Queue modeling (M/M/c, M/M/c/K) for charging wait-time analysis.
- Dynamic pricing via Benders decomposition for revenue maximization.
- Comprehensive analysis of 288 demand zones and 232 candidate sites in Indore.

**Optimal Solution Highlights (2021 Baseline):**
- **Stations:** 90 selected sites
- **Investment:** ₹50.72 Crore
- **Coverage:** 100% of demand zones
- **Annual Profit:** ₹64.55 Lakh
- **Average Service Distance:** 0.70 km

---

## 2. Quick Start Guide

*(Source: Cheat Sheet & README)*

### How to Run the Project

**1. Complete Optimization (Recommended)**
Generates new solutions, runs full optimization, and creates all reports.
```powershell
python main.py
```
*Runtime: 45-60 minutes*

**2. Fast Report Regeneration**
If you already have `optimal_solution.csv` and `fitness_log.csv` and just want to update plots/HTML:
```powershell
python generate_report_from_csv.py
```
*Runtime: < 5 seconds*

**3. Verify Consistency**
Checks if the CSVs and generated reports are synchronized.
```powershell
python check_consistency.py
```

### Outputs Generated
- `evcs_report.html`: Interactive full report (Open in browser).
- `optimal_solution.csv`: Detailed metrics for every selected station.
- `fitness_log.csv`: Convergence data for the genetic algorithm.
- `evcs_map.png`: Map of stations and demand zones.
- `solution_summary.png`: Dashboard of key metrics.
- `objectives_tradeoff.png`: Pareto front visualizations.

---

## 3. Project Overview & Data Sources

### The Problem
Indore needs an EV charging network that balances conflicting goals: minimizing cost, maximizing coverage, minimizing user travel distance, and ensuring financial viability (profit).

### Solution Approach
We use a **Hybrid Optimization Framework**:
1.  **NSGA-II (Non-dominated Sorting Genetic Algorithm II)**: Optimizes site selection (binary decisions) to balance Cost, Coverage, and Distance.
2.  **Benders Decomposition**: For each site configuration, solves a sub-problem to find the optimal charging price (continuous decision) that maximizes Profit.

### Data Sources
1.  **Indore Population Data**: Government of India Census 2011 & 2021.
2.  **Geographic Data**: OpenStreetMap (OSM) via `osmnx` for demand zones (residential/commercial) and candidate sites (parking/malls/fuel stations).
3.  **Power Grid**: Transformer and substation locations from OSM, with capacity estimated by voltage level (33kV, 11kV, etc.).

---

## 4. Key Assumptions & Inputs

*(Source: README)*

### EV Estimations
-   **EV Adoption**: ~3% of population (varies 2-6% by zone type).
-   **Charging Behavior**: 12 sessions/month per EV, 12.5 kWh/session.
-   **Utilization**: 20-50% of covered EVs will use the station (scales with coverage).

### Financial Assumptions
-   **Setup Cost**: ₹25-40 Lakhs per station (Land + Equipment).
-   **Operating Cost**: ₹4/kWh (Electricity) + ₹5,000/month (Maintenance).
-   **Pricing**: Base ₹10/kWh, optimized dynamically between ₹8-15/kWh.
-   **Grid Upgrade**: ₹850 per kW if existing grid capacity is exceeded.

### Technical Constraints
-   **Service Radius**: 5 km maximum.
-   **Charger Power**: 50 kW DC Fast Chargers.
-   **Grid Capacity**: 33kV Substation (~6.2 MW), 11kV Transformer (~210 kW).

---

## 5. Mathematical Model Architecture

*(Adapted from MODEL_ARCHITECTURE.tex)*

### 5.1 Objectives
The multi-objective function $\mathbf{f}(\mathbf{x}, \mathbf{c}, \mathbf{p})$ minimizes/maximizes four components:

1.  **Minimize Cost ($f_1$):**
    $$ f_1(\mathbf{x}) = \sum_{j=1}^{N} x_j (C_{\text{setup},j} + C_{\text{grid},j}) $$
    Where $x_j \in \{0,1\}$ is the selection binary.

2.  **Maximize Coverage ($f_2$):**
    $$ f_2(\mathbf{x}) = \sum_{i \in \mathcal{I}} d_i \cdot \mathbb{1}(\exists j : x_j=1 \land \text{dist}_{ij} \leq 5\text{km}) $$

3.  **Minimize Distance ($f_3$):**
    $$ f_3(\mathbf{x}) = \frac{\sum_{i \in \mathcal{I}} d_i \cdot \min_{j: x_j=1} \text{dist}_{ij}}{\text{Total Demand}} $$

4.  **Maximize Profit ($f_4$):**
    $$ f_4(\mathbf{x}, \mathbf{p}) = \sum_{j: x_j=1} (p_j \cdot q_j(p_j) - C_{\text{ops},j}) $$
    Where $p_j$ is price and $q_j$ is demand function.

### 5.2 Benders Decomposition
Used to decouple the integer problem (site selection) from the continuous problem (pricing).
-   **Master Problem**: NSGA-II chooses $\mathbf{x}$ (sites).
-   **Subproblem**: For fixed $\mathbf{x}$, optimize $\mathbf{p}$ (prices).
    $$ \max_{\mathbf{p}} \sum (p_j \cdot q_j(p_j) - C_{\text{ops}}) $$
    Subject to $8 \le p_j \le 15$.
-   **Feedback**: Profit value is returned to NSGA-II as fitness for objective 4.

### 5.3 CAGR Population Model
Population $P_t$ in year $t$ (years after 2021):
$$ P_{2021+t} = P_{2021} \cdot (1 + r)^t $$
Where $r = 7.04\%$ (calculated from 2011-2021 Census data).

### 5.4 Queueing Theory (M/M/c)
Service quality is validated using M/M/c queue formulas.
-   **Utilization ($\rho$):** $\lambda / (c \mu)$
-   **Wait Probability ($P_W$):** Erlang-C formula $C(c, a)$
-   **Avg Wait Time ($W_q$):**
    $$ W_q = \frac{C(c, a)}{c \mu (1 - \rho)} $$
    If $\rho \ge 1$, the station is flagged as **unstable**.

---

## 6. Full Project Report: M.Tech Thesis Content

*(Source: MTECH_PROJECT_REPORT.md)*

### 1. Introduction
Electric vehicles (EVs) are critical to India's net-zero goals. This study focuses on Indore, a tier-2 city with rapid growth (96.2% population increase 2011-2021). The challenge is to place charging infrastructure that is both profitable and accessible.

### 2. Methodology
The study uses a unique "Hybrid Optimizer" written in Python (`hybrid_optimizer.py`).
-   **Step 1 Data Loading**: Used `osmnx` to scrape real Indore geometry.
-   **Step 2 Optimization**: Ran NSGA-II with 120 population size for 150 generations.
-   **Step 3 Pricing**: Integrated Benders cuts to refine pricing for every candidate network.

### 3. Results & Analysis
The algorithm converged effectively by Generation 50.
-   **Best Solution**: Configuration #42 in Gen 150.
-   **Strategic Insight**: High-demand zones (Rajwada, Palasia) get multiple stations. Outskirts get sparse coverage to maintain connectivity.
-   **Queue Stability**: ~60 sites operate near capacity in peak hours, suggesting a need for Phase 2 expansion by 2025.

### 4. Phased Deployment Plan
| Phase | Years | Stations | Cost (Cr) | Coverage |
|-------|-------|----------|-----------|----------|
| I | 2021-23 | 35 | 17.8 | Core Network |
| II | 2024-27 | 107 | 54.2 | 95% City |
| III | 2028-31 | 286 | 152.5 | Saturated |

### 5. Conclusion
The study successfully demonstrates that a mathematically rigorous approach using real Census and OpenStreetMap data can create a viable EV deployment plan for Indore. The code is modular and can be adapted for other cities.

---

## 7. Code Structure & Implementation Details

*(Source: README)*

### File Guide
-   `main.py`: Entry point. Orchestrates data loading, optimization, and reporting.
-   `data_loader.py`: Handles OSM downloads and data cleaning.
-   `nsga2_optimizer.py`: Implementation of the Genetic Algorithm.
-   `benders_decomposition.py`: Implementation of the Pricing Subproblem.
-   `site_metrics_calculator.py`: Central logic for Cost/Profit/Coverage math (used by all modules).
-   `visualization.py`: Generates Matplotlib plots.

### Key Python Libraries
-   `deap`: For Evolutionary Algorithms.
-   `osmnx` & `geopandas`: For GIS data.
-   `numpy` & `pandas`: For numeric processing.
-   `scipy`: For Queueing theory functions.

---

## 8. Appendix

### 8.1 Notation
-   $\mathcal{I}$: Demand Zones (288)
-   $\mathcal{J}$: Candidate Sites (232)
-   $r$: CAGR (0.0704)
-   $p_j$: Price at site $j$

### 8.2 References
1.  Deb, K. et al. (2002). NSGA-II Algorithm.
2.  Govt of India (2021). Indore City Profile.
3.  Gross, D. & Harris, C. (1998). Fundamentals of Queueing Theory.
