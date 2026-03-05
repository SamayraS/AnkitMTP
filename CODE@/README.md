# EV Charging Station Optimization for Indore City - Complete Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Input and Output](#input-and-output)
3. [Data Sources](#data-sources)
4. [Assumptions and Estimations](#assumptions-and-estimations)
5. [How Calculations Are Done](#how-calculations-are-done)
6. [How We're Doing It](#how-were-doing-it)
7. [Code Structure Explained](#code-structure-explained)
8. [Output Files Explained](#output-files-explained)
9. [Installation & Usage](#installation--usage)
10. [Understanding the Results](#understanding-the-results)
11. [Detailed Algorithm Explanation](#detailed-algorithm-explanation)
12. [Metrics Calculation Explained](#metrics-calculation-explained)
13. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

This project solves a **real-world optimization problem**: Where should we place electric vehicle (EV) charging stations in Indore city to maximize profit while serving the maximum number of EVs?

**The Challenge:**
- Indore has many potential locations for charging stations
- Each location has different costs, capacities, and potential demand
- We need to balance: **Cost** (minimize), **Coverage** (maximize), and **Profit** (maximize)
- These objectives often conflict with each other!

**Our Solution:**
We use a **hybrid optimization approach** combining two powerful algorithms:
1. **NSGA-II** (Genetic Algorithm) - Finds the best locations
2. **Benders Decomposition** - Optimizes pricing for those locations

---

## 📥📤 Input and Output

### **Input Parameters**

#### **1. Demand Zones** (Source: OpenStreetMap + Predefined Locations)
**What it is:** Geographic areas where electric vehicles (EVs) are located or expected to be located in Indore city.

**Data Fields:**
- `zone_id`: Unique identifier for each demand zone
- `latitude`: Geographic latitude (decimal degrees)
- `longitude`: Geographic longitude (decimal degrees)
- `population`: Estimated population in the zone
- `ev_density`: Fraction of population that owns EVs (0.02-0.06, i.e., 2-6%)
- `demand`: Total EV demand = population × ev_density
  

**How it's obtained:**
- Primary: Fetched from OpenStreetMap (OSM) using `osmnx` library
- Fallback: Predefined list of 25 known Indore neighborhoods with real coordinates
- Estimation method: If population data missing, estimated from area × population density (5000 per km² for residential, 8000 per km² for commercial)

**Example Input:**
```
zone_id: 1
latitude: 22.7486
longitude: 75.8889
population: 45000
ev_density: 0.03
demand: 1350 EVs
name: "Vijay Nagar"
```

#### **2. Candidate Sites** (Source: OpenStreetMap + Predefined Locations)
**What it is:** Potential locations where EV charging stations can be installed.

**Data Fields:**
- `site_id`: Unique identifier
- `latitude`: Geographic latitude
- `longitude`: Geographic longitude
- `capacity`: Number of charging points (connectors) at the station (4, 8, 12, or 16)
- `setup_cost`: One-time installation cost including land and equipment (INR)
- `land_cost`: Cost of land/preparation (INR)
- `site_type`: Type of location (`"mall"`, `"parking"`, `"fuel_station"`, `"restaurant"`)
- `name`: Name of location (if available)

**How it's obtained:**
- Primary: OSM queries for `amenity=parking`, `shop=mall`, `amenity=fuel`, `amenity=restaurant`
- Fallback: Predefined list of 15 known Indore locations (C21 Mall, MG Road, etc.)
- Cost estimation: Based on site type, capacity, and distance from city center

**Example Input:**
```
site_id: 108
latitude: 22.7196
longitude: 75.8577
capacity: 12 charging points
setup_cost: 2,500,000 INR
site_type: "mall"
name: "C21 Mall"
```

#### **3. Power Grid Nodes** (Source: OpenStreetMap)
**What it is:** Electrical infrastructure (substations, transformers) that can supply power to charging stations.

**Data Fields:**
- `grid_id`: Unique identifier
- `name`: Name of substation/transformer
- `latitude`: Geographic latitude
- `longitude`: Geographic longitude
- `power`: Type (`"substation"` or `"transformer"`)
- `voltage_kv`: Voltage level (e.g., 33 kV, 11 kV)
- `available_kw`: Estimated available power capacity (kW)

**How it's obtained:**
- OSM query: `power=['substation', 'transformer']` within 15km of Indore center
- Voltage parsing: Extracts voltage from OSM tags (handles formats like "33", "33000", "33;11")
- Capacity estimation: Maps voltage levels to typical capacity using lookup table

**Example Input:**
```
grid_id: 5
name: "AB Road Substation"
latitude: 22.7220
longitude: 75.8500
power: "substation"
voltage_kv: 33.0
available_kw: 6200
```

#### **4. Distance Matrix**
**What it is:** Precomputed matrix of distances between all demand zones and candidate sites.

**Calculation:** Uses **Haversine formula** for great-circle distance on Earth's surface.

**Dimensions:** `(n_zones, n_sites)` - each cell `[i, j]` = distance from zone i to site j in kilometers.

---

### **Output Results**

#### **1. Optimal Solution CSV** (`optimal_solution.csv`)
**What it contains:** Detailed metrics for each selected charging station.

**Key Output Columns:**
- `site_id`, `location_name`, `latitude`, `longitude`: Site identification and location
- `demand_category`: Classification (High/Medium/Low/Very Low)
- `coverage_evs`: Number of EVs within 5km service radius
- `density_per_km2`: EV density in coverage area
- `annual_profit_inr`: Expected annual profit in Indian Rupees
- `price_per_kwh_inr`: Optimal charging price (INR/kWh)
- `capacity_charging_points`: Number of charging connectors
- `setup_cost_inr`: Base installation cost
- `grid_upgrade_cost_inr`: Additional cost if grid upgrade needed
- `total_setup_cost_inr`: Total investment = setup_cost + grid_upgrade_cost
- `nearest_grid_id/name`: Closest power grid node
- `grid_voltage_kv`, `grid_available_kw`, `grid_required_kw`: Grid capacity details
- `grid_capacity_gap_kw`: Available - required capacity
- `grid_capacity_ok`: Boolean flag (True if grid can support, False if upgrade needed)
- `distance_to_grid_km`: Distance to nearest grid node

#### **2. Visual Maps & Graphs**
- **`evcs_map.png`**: Map visualization showing selected sites, demand zones, and coverage areas.
- **`objectives_tradeoff.png`**: Pareto front plots showing trade-offs between objectives (Cost vs Coverage vs Profit).
- **`convergence_curve.png`**: Convergence graph showing Best and Average fitness (Cost, Coverage, Distance) over 150 generations.
- **`solution_summary.png`**: Summary dashboards with key statistics.

#### **3. Logs**
- **`fitness_log.csv`**: Detailed generation-wise statistics (Best/Avg/Worst for all objectives).

#### **4. HTML Report** (`evcs_report.html`)
- Comprehensive summary with all metrics, top sites, and recommendations

---

## 📊 Data Sources

### **Primary Data Sources**

#### **1. OpenStreetMap (OSM)**
**Website:** https://www.openstreetmap.org/

**What we fetch:**
- **Demand Zones:** Residential areas (`landuse=residential`), commercial areas (`landuse=commercial`), neighborhoods (`place=neighbourhood`)
- **Candidate Sites:** Parking areas (`amenity=parking`), shopping malls (`shop=mall`), fuel stations (`amenity=fuel`)
- **Power Grid:** Substations and transformers (`power=['substation', 'transformer']`)

**How we access it:**
- Library: `osmnx` (Python wrapper for OSM)
- API calls: `ox.features_from_place()`, `ox.features_from_point()`, `ox.geocode_to_gdf()`
- Caching: Results cached locally in `cache/` directory to reduce API calls

**Limitations:**
- OSM data may be incomplete or sparse for some areas
- Some locations may have missing attributes (population, voltage levels)
- We use fallback data when OSM queries return insufficient results

**Why we use it:**
- Free and open-source
- Global coverage including Indore city
- Real geographic coordinates and infrastructure data
- Regularly updated by community

#### **2. Predefined Indore Locations**
**Source:** Known locations in Indore city with real coordinates

**What we include:**
- **Demand Zones:** 25 known neighborhoods (Vijay Nagar, New Palasia, Sapna Sangeeta, Bhawarkua, Rau, etc.)
  - Real coordinates from Google Maps / GPS
  - Estimated populations based on census data and area sizes
  - Income estimates based on area characteristics

- **Candidate Sites:** 15 known locations (C21 Mall, Treasure Island, MG Road, etc.)
  - Real coordinates
  - Site types (mall, parking, fuel station, commercial)
  - Cost estimates based on location and site type

**Why we use it:**
- Ensures data quality when OSM is sparse
- Includes well-known commercial areas that may not be in OSM
- Provides baseline population and income estimates

#### **3. Electrical Grid Capacity Estimation**
**Source:** Industry-standard voltage-to-capacity mappings

**Method:**
- Voltage levels extracted from OSM tags
- Capacity estimated using lookup table:
  - 33 kV substation → 6,200 kW (with +20% buffer for substations)
  - 11 kV transformer → 210 kW (with -20% derating for transformers)
  - Other voltages mapped similarly

**Reference:** Standard Indian power distribution system capacity ratings

---

## 🔍 Assumptions and Estimations

### **1. EV Adoption Rates**
**Assumptions:**
- **Residential areas:** 2-4% of population owns EVs (uniform random distribution)
- **Commercial areas:** 3-6% of population owns EVs (higher adoption)
- **Overall average:** ~3% EV penetration rate in Indore

**Rationale:**
- Based on current Indian EV market penetration (2023-2024 estimates)
- Commercial areas have higher adoption due to commercial EV fleets
- Conservative estimate to ensure realistic planning

**Source:** Industry reports on EV adoption in tier-2 Indian cities

### **2. Population Density**
**Assumptions:**
- **Residential areas:** 5,000 people per km²
- **Commercial areas:** 8,000 people per km² (includes daytime population)

**Rationale:**
- Indore city average population density: ~5,000/km²
- Commercial areas have higher daytime density due to workers and visitors
- Used when OSM area data is missing

**Source:** Census of India 2011 and Indore Municipal Corporation estimates

### **3. Charging Behavior**
**Assumptions:**
- **Sessions per EV per month:** 12 sessions
- **Energy per session:** 12.5 kWh per charging session
- **Monthly energy per EV:** 150 kWh/month (12 × 12.5)
- **Utilization rate:** 20-50% of covered EVs actually use the station
  - Base utilization: 20%
  - Increases with coverage: +0.3% per EV covered (up to 50% max)
  - Formula: `utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)`

**Rationale:**
- Average EV charging frequency from industry surveys
- Typical fast charging session size
- Utilization increases with higher coverage (more convenience)

**Source:** EV charging behavior studies and industry benchmarks

### **4. Pricing Model**
**Assumptions:**
- **Base price:** ₹10/kWh
- **Price range:** ₹8-13/kWh (varies by demand density)
- **Price adjustment:** Based on local demand density (higher demand → higher price)
- **Price elasticity:** -0.5 (demand decreases 0.5% for every 1% price increase)

**Rationale:**
- Competitive market pricing based on current Indian EV charging rates
- Dynamic pricing reflects demand and competition
- Price elasticity reflects consumer sensitivity

**Source:** Current market rates and price elasticity studies

### **5. Cost Structure**
**Assumptions:**
- **Setup costs:**
  - Land cost: ₹800,000 - ₹1,200,000 (varies by site type and location)
  - Equipment cost: ₹450,000 - ₹500,000 per charging point
  - Total setup: Land cost + (Capacity × Equipment cost per point)

- **Operating costs:**
  - Electricity cost: ₹4/kWh (purchased from grid)
  - Fixed maintenance: ₹5,000/month per station

- **Grid upgrade costs:**
  - If grid capacity insufficient: ₹850/kW for distribution upgrades
  - Only charged if `grid_required_kw > grid_available_kw`

**Rationale:**
- Based on Indian market rates for EV charging infrastructure (2023-2024)
- Grid upgrade costs from power distribution utility estimates
- Maintenance costs from industry benchmarks

**Source:** EV charging infrastructure cost studies and utility tariff sheets

### **6. Service Radius**
**Assumptions:**
- **Maximum service distance:** 5 km
- EVs within 5 km of a station are considered "covered"
- Partial coverage for zones 5-7 km away (weighted by distance)

**Rationale:**
- Typical maximum distance EV owners are willing to travel for charging
- Balances convenience with coverage area
- Based on EV charging behavior studies

**Source:** EV charging accessibility studies

### **7. Charger Power Rating**
**Assumptions:**
- **Charger power:** 50 kW per charging point (DC fast charger)
- **Total station load:** `capacity_charging_points × 50 kW`

**Rationale:**
- Standard DC fast charging power rating in India
- Used to calculate required grid capacity

**Source:** Standard EV charging infrastructure specifications

### **8. Grid Capacity Estimation**
**Assumptions:**
- **Voltage-to-capacity mapping:**
  - 33 kV substation: 6,200 kW base capacity
  - 22 kV substation: 3,500 kW
  - 11 kV transformer: 210 kW
  - Other voltages mapped proportionally
- **Substation buffer:** +20% capacity buffer for substations
- **Transformer derating:** -20% capacity reduction for transformers

**Rationale:**
- Standard Indian power distribution system ratings
- Substations typically have more headroom
- Transformers operate closer to capacity

**Source:** Indian power distribution system standards and utility capacity ratings

### **9. Spatial Interpolation**
**Assumptions:**
- If a demand zone has zero demand, estimate from nearby zones
- **Interpolation radius:** 10 km
- **Weighting:** Inverse distance weighting (closer zones have more influence)
- **Formula:** `weight = 1.0 / (1.0 + distance)`

**Rationale:**
- Demand patterns are spatially correlated
- Nearby zones likely have similar EV adoption rates
- Smooths out missing data points

### **10. Optimization Parameters**
**Assumptions:**
- **Budget constraint:** ₹50,000,000 (50 million INR)
- **NSGA-II generations:** 50 generations
- **Population size:** 50 individuals per generation
- **Benders iterations:** 30 iterations per site selection
- **Convergence tolerance:** 1e-4

**Rationale:**
- Reasonable budget for city-wide EV charging network
- Algorithm parameters tuned for solution quality vs. computation time

---

## 🧮 How Calculations Are Done

### **1. Distance Calculation (Haversine Formula)**

**Purpose:** Calculate great-circle distance between two points on Earth's surface.

**Formula:**
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = R × c
```

Where:
- `Δlat` = latitude difference in radians
- `Δlon` = longitude difference in radians
- `lat1`, `lat2` = latitudes in radians
- `R` = Earth's radius = 6,371 km

**Implementation:**
```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
```

**Why Haversine:**
- Accounts for Earth's curvature (accurate for distances >1 km)
- Standard formula for geographic distance calculations
- More accurate than Euclidean distance for geographic coordinates

---

### **2. Coverage Calculation**

**Purpose:** Count number of EVs within service radius of a charging station.

**Step-by-step process:**

1. **Find zones within 5 km:**
   ```
   For each demand zone i:
       distance = haversine(zone_i, site_j)
       if distance <= 5.0 km:
           include in coverage
   ```

2. **Get zone demand:**
   ```
   zone_demand = zone['demand']
   
   # If demand is zero, estimate from population
   if zone_demand == 0 and zone['population'] > 0:
       zone_demand = zone['population'] × zone['ev_density']
   ```

3. **Spatial interpolation (if still zero):**
   ```
   if zone_demand == 0:
       nearby_demand = []
       for nearby_zone within 10 km:
           if nearby_zone['demand'] > 0:
               weight = 1.0 / (1.0 + distance)
               nearby_demand.append(nearby_zone['demand'] × weight)
       
       if nearby_demand:
           zone_demand = mean(nearby_demand)
       else:
           zone_demand = baseline_demand_per_zone
   ```

4. **Sum coverage:**
   ```
   coverage = sum(zone_demand for all zones within 5 km)
   ```

**Handling edge cases:**
- Zones 5-7 km away: Partial coverage with distance weighting
- Zero demand zones: Spatial interpolation from nearby zones
- Missing population data: Estimated from area × population density

---

### **3. Density Calculation**

**Purpose:** Calculate EV density (EVs per km²) in coverage area.

**Formula:**
```
coverage_area_km2 = π × (service_radius)² = π × 5² = 78.54 km²
density = coverage / coverage_area_km2
```

**Example:**
- Coverage: 500 EVs
- Coverage area: 78.54 km²
- Density: 500 / 78.54 = 6.37 EVs/km²

**Interpretation:**
- Higher density = more concentrated demand = better for station placement
- Lower density = sparse demand = may need larger service radius

---

### **4. Profit Calculation**

**Purpose:** Calculate expected annual profit from operating a charging station.

**Step-by-step calculation:**

**Step 1: Utilization rate**
```
utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)
```
- Base utilization: 20%
- Increases by 0.3% per EV covered (up to 50% maximum)

**Step 2: Served EVs**
```
served_evs = coverage × utilization_rate
```

**Step 3: Monthly revenue**
```
charging_sessions_per_ev_per_month = 12
kwh_per_session = 12.5
monthly_kwh_per_ev = 12 × 12.5 = 150 kWh/month

monthly_revenue = served_evs × monthly_kwh_per_ev × price_per_kwh
```

**Step 4: Monthly operating cost**
```
electricity_cost_per_kwh = 4.0 INR
monthly_electricity_cost = served_evs × monthly_kwh_per_ev × electricity_cost_per_kwh
monthly_maintenance = 5000.0 INR

monthly_operating_cost = monthly_electricity_cost + monthly_maintenance
```

**Step 5: Monthly profit**
```
monthly_profit = monthly_revenue - monthly_operating_cost
```

**Step 6: Annual profit**
```
annual_profit = monthly_profit × 12
```

**Example calculation:**
- Coverage: 100 EVs
- Utilization rate: min(0.5, 0.2 + (100/100)*0.3) = 0.5 = 50%
- Served EVs: 100 × 0.5 = 50 EVs
- Monthly revenue: 50 × 150 × ₹10 = ₹75,000
- Monthly electricity cost: 50 × 150 × ₹4 = ₹30,000
- Monthly maintenance: ₹5,000
- Monthly operating cost: ₹30,000 + ₹5,000 = ₹35,000
- Monthly profit: ₹75,000 - ₹35,000 = ₹40,000
- **Annual profit: ₹40,000 × 12 = ₹480,000**

---

### **5. Grid Capacity Calculation**

**Purpose:** Determine if existing grid infrastructure can support charging station load, and calculate upgrade costs if needed.

**Step-by-step process:**

**Step 1: Required load**
```
charger_power_kw = 50 kW per charging point
grid_required_kw = capacity_charging_points × charger_power_kw
```

**Step 2: Available capacity (from OSM)**
```
# Parse voltage from OSM tag
voltage_kv = parse_voltage(osm_tag['voltage'])

# Map voltage to capacity
voltage_capacity_map = {
    33: 6200,   # 33 kV substation
    22: 3500,   # 22 kV substation
    11: 210     # 11 kV transformer
}
base_capacity = voltage_capacity_map[nearest_voltage]

# Apply adjustments
if power_type == 'substation':
    grid_available_kw = base_capacity × 1.2  # +20% buffer
elif power_type == 'transformer':
    grid_available_kw = base_capacity × 0.8  # -20% derating
```

**Step 3: Capacity gap**
```
grid_capacity_gap_kw = grid_available_kw - grid_required_kw
```

**Step 4: Upgrade cost (if needed)**
```
if grid_required_kw > grid_available_kw:
    upgrade_needed_kw = grid_required_kw - grid_available_kw
    grid_upgrade_cost = upgrade_needed_kw × 850 INR/kW
else:
    grid_upgrade_cost = 0
```

**Step 5: Total setup cost**
```
total_setup_cost = setup_cost + grid_upgrade_cost
```

**Example calculation:**
- Capacity: 12 charging points
- Required: 12 × 50 = 600 kW
- Nearest grid: 33 kV substation
- Available: 6,200 × 1.2 = 7,440 kW
- Capacity gap: 7,440 - 600 = 6,840 kW (positive = OK)
- **Upgrade needed:** No (capacity OK)
- **Upgrade cost:** ₹0

**If capacity insufficient:**
- Required: 10,000 kW
- Available: 7,440 kW
- Upgrade needed: 10,000 - 7,440 = 2,560 kW
- **Upgrade cost:** 2,560 × ₹850 = ₹2,176,000

---

### **6. Distance to Grid Calculation**

**Purpose:** Calculate distance from candidate site to nearest grid node.

**Method:**
1. Build spatial index (BallTree) of all grid nodes
2. For each candidate site, find nearest grid node
3. Calculate Haversine distance

**Formula:** Same as distance calculation (Haversine)

**Usage:** Used to estimate cable trenching costs and feasibility

---

### **7. Price Optimization (Benders Decomposition)**

**Purpose:** Find optimal charging price for each site to maximize profit.

**Method:**
1. **Master Problem:** Determine prices (decision variables)
   - Objective: Maximize profit
   - Constraints: Price bounds (₹8-13/kWh)

2. **Subproblem:** Evaluate profit given prices
   - Calculate demand based on prices (with elasticity)
   - Calculate revenue and costs
   - Return profit

3. **Benders Cuts:** Add constraints to master problem
   - If subproblem shows low profit, add cut: "Prices must be higher"
   - Iteratively refine solution

4. **Convergence:** Repeat until profit improvement < threshold

**Price adjustment formula:**
```
base_price = 10.0 INR/kWh
demand_density = sum(demand for zones within 5 km)
price_adjustment = min(demand_density / 1000.0, 3.0)
optimal_price = base_price + price_adjustment
```

**Demand elasticity:**
```
price_factor = (price / 10.0)^(-0.5)
adjusted_demand = original_demand × price_factor
```
- If price increases 10%, demand decreases ~5%

---

### **8. Site Selection (NSGA-II)**

**Purpose:** Find optimal combination of sites to select.

**Multi-objective optimization:**

**Objective 1: Minimize Cost**
```
total_cost = sum(setup_cost for all selected sites)
```

**Objective 2: Maximize Coverage**
```
total_coverage = 0
for each demand zone:
    if zone is within 5 km of ANY selected site:
        total_coverage += zone['demand']
```

**Objective 3: Minimize Average Distance**
```
total_distance = 0
zones_covered = 0
for each demand zone:
    nearest_site = min(distance to all selected sites)
    if nearest_site <= 5 km:
        total_distance += nearest_site
        zones_covered += 1

avg_distance = total_distance / zones_covered
```

**NSGA-II process:**
1. Initialize population of 50 random site selections
2. Evaluate each solution on 3 objectives
3. Rank by Pareto dominance (non-dominated sorting)
4. Select best solutions for next generation
5. Apply crossover and mutation to create new solutions
6. Repeat for 50 generations
7. Return Pareto-optimal solutions

**Pareto dominance:**
- Solution A dominates B if: A is better in ALL objectives
- Pareto front = set of non-dominated solutions
- Different solutions represent different trade-offs

---

### **9. Best Solution Selection**

**Purpose:** Select single best solution from Pareto front.

**Method: Weighted scoring**
```
# Normalize objectives to [0, 1]
cost_norm = (cost - cost_min) / (cost_max - cost_min)
coverage_norm = (coverage - coverage_min) / (coverage_max - coverage_min)
profit_norm = (profit - profit_min) / (profit_max - profit_min)

# Weighted score (higher is better)
weights = [0.5, 0.3, 0.2]  # [profit, coverage, -cost]
score = (profit_norm × 0.5) + (coverage_norm × 0.3) + ((1 - cost_norm) × 0.2)

# Select solution with highest score
best_solution = argmax(scores)
```

**Weights rationale:**
- Profit (50%): Primary objective - ensures financial viability
- Coverage (30%): Secondary objective - ensures good service
- Cost (20%): Tertiary objective - minimizes investment

---

## 🔧 How We're Doing It

### Step-by-Step Process

```
1. Load Real Data
   ↓
2. Calculate Distances
   ↓
3. Run Hybrid Optimization
   ├─ NSGA-II: Find best site combinations
   └─ Benders: Optimize prices for each combination
   ↓
4. Select Best Solution
   ↓
5. Calculate Metrics (Coverage, Profit, Density)
   ↓
6. Generate Visualizations & Reports
```

### Detailed Process Flow

#### **Step 1: Data Loading** (`data_loader.py`)

**What it does:**
- Fetches real geographic data from OpenStreetMap (OSM) for Indore city
- Gets residential areas, commercial zones, parking areas, malls, fuel stations
- Falls back to predefined Indore locations if OSM data is sparse
- Estimates EV demand from population data
- Downloads substations & transformers, estimates available grid capacity, and links each candidate site to its nearest grid node

**Key Functions:**
- `load_real_demand_zones()`: Fetches residential/commercial areas from OSM
- `load_real_candidate_sites()`: Fetches parking/malls/fuel stations from OSM
- `_load_indore_neighborhoods()`: Predefined Indore neighborhoods with real coordinates
- `_get_indore_real_locations()`: Predefined real locations (C21 Mall, MG Road, etc.)
- `load_power_grid_nodes()`: Pulls Indore substations/transformers and estimates available kW by voltage level
- `link_sites_to_grid()`: Maps every candidate site to the nearest grid node, computing distance, capacity gap, and upgrade cost

**Output:**
- `demand_zones`: DataFrame with columns: `zone_id`, `latitude`, `longitude`, `population`, `demand`, `ev_density`
- `candidate_sites`: DataFrame with columns: `site_id`, `latitude`, `longitude`, `capacity`, `setup_cost`, `site_type`, `name`, `grid_available_kw`, `grid_required_kw`, `grid_upgrade_cost`
- `grid_nodes`: DataFrame with columns: `grid_id`, `name`, `latitude`, `longitude`, `power`, `voltage_kV`, `available_kw`
- `distance_matrix`: NumPy array (n_zones × n_sites) with Haversine distances in km

**Example:**
```python
# Demand zone example
zone = {
    'zone_id': 1,
    'latitude': 22.7486,
    'longitude': 75.8889,
    'population': 45000,
    'demand': 1350.0,  # population × ev_density (3%)
    'ev_density': 0.03
}

# Candidate site example
site = {
    'site_id': 108,
    'latitude': 22.7196,
    'longitude': 75.8577,
    'capacity': 12,  # 12 charging points
    'setup_cost': 2500000.0,  # ₹2.5M
    'site_type': 'mall',
    'name': 'C21 Mall',
    'nearest_grid_id': 5,
    'grid_available_kw': 6200,
    'grid_required_kw': 600,
    'grid_upgrade_cost': 0.0
}

# Grid node example
grid_node = {
    'grid_id': 5,
    'name': 'AB Road Substation',
    'latitude': 22.7220,
    'longitude': 75.8500,
    'power': 'substation',
    'voltage_kv': 33.0,
    'available_kw': 6200
}
```

#### **Step 2: Distance Calculation**

**What it does:**
- Calculates great-circle distance between every demand zone and every candidate site
- Uses **Haversine formula** (accounts for Earth's curvature)
- Stores in `distance_matrix[i, j]` = distance from zone i to site j (in km)

**Formula:**
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = R × c  (R = 6371 km, Earth's radius)
```

**Why it matters:**
- Determines which EVs can be served by which stations (5km service radius)
- Used to calculate coverage for each site

#### **Step 3: Hybrid Optimization** (`hybrid_optimizer.py`)

**What it does:**
- Combines NSGA-II (location selection) and Benders Decomposition (pricing)

**NSGA-II (Non-dominated Sorting Genetic Algorithm II):**
- **Purpose**: Find best combinations of sites to select
- **How it works**:
  1. Creates initial population of random site selections
  2. Evaluates each solution on 3 objectives: cost, coverage, distance
  3. Ranks solutions by dominance (Pareto front)
  4. Selects best solutions for next generation
  5. Applies crossover and mutation to create new solutions
  6. Repeats for 50 generations
- **Output**: 50 Pareto-optimal solutions (different trade-offs)

**Benders Decomposition** (`benders_decomposition.py`):
- **Purpose**: Optimize pricing for a given set of selected sites
- **How it works**:
  1. Takes a site selection from NSGA-II
  2. Solves pricing subproblem (maximize profit given demand)
  3. Updates master problem with Benders cuts
  4. Iterates until convergence (30 iterations)
- **Output**: Optimal price for each selected site

**Key Functions:**
- `HybridOptimizer.solve()`: Main optimization loop
- `NSGA2Optimizer.optimize()`: Runs NSGA-II
- `BendersOptimizer.solve()`: Optimizes pricing

#### **Step 4: Solution Selection**

**What it does:**
- From 50 Pareto-optimal solutions, selects the best one
- Uses weighted scoring: `score = 0.3 × (normalized_profit) + 0.4 × (normalized_coverage) + 0.3 × (1 - normalized_cost)`
- Best solution = highest score

**Why this approach:**
- Pareto front shows all possible trade-offs
- Weighted scoring lets you prioritize (e.g., more weight on profit if profit-focused)

#### **Step 5: Metrics Calculation** (`site_metrics_calculator.py`)

**What it does:**
- Calculates detailed metrics for each selected site
- **Centralized calculator** ensures consistency across CSV, visualization, and HTML report

**Key Metrics:**

1. **Coverage (EVs)**
   - **Definition**: Number of EVs within 5km service radius
   - **Calculation**:
     ```python
     coverage = 0
     for each demand zone within 5km:
         zone_demand = zone['demand']
         if zone_demand == 0:
             # Estimate from population
             zone_demand = zone['population'] × zone['ev_density']
         if zone_demand == 0:
             # Spatial interpolation from nearby zones
             zone_demand = interpolate_from_nearby_zones()
         coverage += zone_demand
     ```
   - **Spatial Interpolation**: If a zone has zero demand but is near zones with demand, we estimate demand using inverse distance weighting

2. **Density (EVs/km²)**
   - **Definition**: Average EV density in coverage area
   - **Calculation**: `density = coverage / (π × 5²)` = `coverage / 78.54 km²`
   - **Interpretation**: Higher density = more concentrated demand

3. **Annual Profit (₹)**
   - **Definition**: Expected annual profit from operating the station
   - **Calculation Steps**:
     ```python
     # Utilization rate (20-50% based on coverage)
     utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)
     
     # EVs that actually use the station
     served_evs = coverage × utilization_rate
     
     # Monthly revenue
     monthly_kwh_per_ev = 12 sessions/month × 12.5 kWh = 150 kWh/month
     monthly_revenue = served_evs × 150 kWh × price_per_kwh
     
     # Monthly cost
     electricity_cost = served_evs × 150 kWh × ₹4/kWh
     maintenance = ₹5,000/month
     monthly_cost = electricity_cost + maintenance
     
     # Monthly profit
     monthly_profit = monthly_revenue - monthly_cost
     
     # Annual profit
     annual_profit = monthly_profit × 12
     ```
   - **Assumptions**:
     - Average EV charges 12 times/month
     - 12.5 kWh per session (150 kWh/month total)
     - Electricity cost: ₹4/kWh
     - Fixed maintenance: ₹5,000/month

4. **Demand Category**
   - **High**: ≥100 EVs coverage
   - **Medium**: 50-99 EVs coverage
   - **Low**: 1-49 EVs coverage
   - **Very Low**: 0 EVs coverage (strategic/connectivity sites)

#### **Step 6: Visualization & Reports**

**What it does:**
- Creates visual maps, plots, CSV, and HTML reports
- All use the same centralized calculator for consistency

---

## 📁 Code Structure Explained

### File Organization

```
code/
├── main.py                      # Main entry point
├── data_loader.py               # Loads real Indore data from OSM
├── hybrid_optimizer.py          # Orchestrates NSGA-II + Benders
├── nsga2_optimizer.py           # NSGA-II genetic algorithm
├── benders_decomposition.py    # Benders pricing optimization
├── site_metrics_calculator.py   # Centralized metrics calculation
├── visualization.py             # Creates all plots and maps
├── create_html_report.py        # Generates HTML summary report
├── requirements.txt              # Python dependencies
└── README.md                    # This file
```

### Module-by-Module Explanation

#### **1. `main.py` - Main Entry Point**

**Purpose**: Orchestrates the entire optimization process

**What it does:**
1. Loads data using `IndoreDataLoader`
2. Runs optimization using `HybridOptimizer`
3. Creates visualizations using `EVCSVisualizer`
4. Generates CSV and HTML reports
5. Prints summary statistics

**Key Code:**
```python
def main():
    # Step 1: Load data
    data_loader = IndoreDataLoader(
        city_center_lat=22.7196,  # Indore center
        city_center_lon=75.8577,
        city_radius_km=15.0
    )
    data = data_loader.load_all_data()
    
    # Step 2: Optimize
    optimizer = HybridOptimizer(data, nsga2_generations=50, benders_iterations=30)
    solution_result = optimizer.solve()
    best_solution = solution_result['best_solution']
    
    # Step 3: Visualize
    visualizer = EVCSVisualizer(data)
    visualizer.create_static_map(best_solution, "evcs_map.png")
    visualizer.plot_objectives(solution_result['pareto_solutions'], "objectives_tradeoff.png")
    visualizer.plot_solution_summary(best_solution, "solution_summary.png")
    
    # Step 4: Save CSV
    # ... (saves to optimal_solution.csv)
    
    # Step 5: Generate HTML report
    create_html_report('optimal_solution.csv', 'evcs_report.html')
```

**Run it:**
```bash
python main.py
```

#### **2. `data_loader.py` - Data Loading Module**

**Purpose**: Fetches and preprocesses real Indore city data

**Key Class: `IndoreDataLoader`**

**Methods:**

**`load_real_demand_zones()`**
- Fetches residential and commercial areas from OpenStreetMap
- Uses `osmnx` library to query OSM
- Falls back to predefined Indore neighborhoods if OSM data is sparse
- Estimates demand from population: `demand = population × ev_density` (default 3%)

**`load_real_candidate_sites()`**
- Fetches parking areas, malls, and fuel stations from OSM
- Falls back to predefined real Indore locations (C21 Mall, MG Road, etc.)
- Calculates setup cost based on capacity and land cost

**`load_all_data()`**
- Main method that loads everything
- Returns dictionary with:
  - `demand_zones`: DataFrame
  - `candidate_sites`: DataFrame
  - `distance_matrix`: NumPy array

**Example Usage:**
```python
loader = IndoreDataLoader(
    city_center_lat=22.7196,
    city_center_lon=75.8577,
    city_radius_km=15.0
)
data = loader.load_all_data()
print(f"Loaded {len(data['demand_zones'])} demand zones")
print(f"Loaded {len(data['candidate_sites'])} candidate sites")
```

#### **3. `hybrid_optimizer.py` - Hybrid Optimization Orchestrator**

**Purpose**: Combines NSGA-II and Benders Decomposition

**Key Class: `HybridOptimizer`**

**Methods:**

**`solve()`**
- Main optimization loop
- Runs NSGA-II to find site combinations
- For each combination, runs Benders to optimize prices
- Returns Pareto-optimal solutions and best solution

**How it works:**
```python
def solve(self):
    # Step 1: Run NSGA-II to find site selections
    nsga2_result = self.nsga2_optimizer.optimize()
    
    # Step 2: For each Pareto solution, optimize prices
    pareto_solutions = []
    for solution in nsga2_result['solutions']:
        # Optimize prices using Benders
        prices = self.benders_optimizer.solve(solution)
        solution['prices'] = prices
        pareto_solutions.append(solution)
    
    # Step 3: Select best solution
    best_solution = self._select_best_solution(pareto_solutions)
    
    return {
        'best_solution': best_solution,
        'pareto_solutions': pareto_solutions
    }
```

#### **4. `nsga2_optimizer.py` - NSGA-II Genetic Algorithm**

**Purpose**: Finds optimal site combinations using genetic algorithm

**Key Class: `NSGA2Optimizer`**

**How NSGA-II Works:**

1. **Initialization**: Creates random population of site selections
   - Each individual = binary array (1 = select site, 0 = don't select)
   - Population size = 50

2. **Evaluation**: Calculates objectives for each solution
   - Cost: Total setup cost
   - Coverage: Total EVs covered
   - Distance: Average distance to stations

3. **Non-dominated Sorting**: Ranks solutions by Pareto dominance
   - Solution A dominates B if: A is better in all objectives
   - Creates Pareto fronts (Front 1 = best, Front 2 = second best, etc.)

4. **Selection**: Selects best solutions for next generation
   - Uses tournament selection
   - Prefers solutions in better fronts

5. **Crossover & Mutation**: Creates new solutions
   - Crossover: Combines two parent solutions
   - Mutation: Randomly flips some site selections

6. **Repeat**: For 50 generations

**Key Functions:**
- `_evaluate_individual()`: Calculates objectives for a solution
- `_non_dominated_sort()`: Ranks solutions by dominance
- `_tournament_selection()`: Selects parents for next generation

#### **5. `benders_decomposition.py` - Pricing Optimization**

**Purpose**: Optimizes charging prices for a given set of sites

**Key Class: `BendersOptimizer`**

**How Benders Decomposition Works:**

1. **Master Problem**: Determines prices (decision variables)
2. **Subproblem**: Evaluates profit given prices
3. **Benders Cuts**: Adds constraints to master problem
4. **Iterate**: Until convergence (30 iterations)

**Pricing Model:**
- Base price: ₹10/kWh
- Price adjustment based on demand density
- Higher demand = can charge higher price (up to ₹13/kWh)

**Key Functions:**
- `solve()`: Main Benders loop
- `_solve_master_problem()`: Optimizes prices
- `_solve_subproblem()`: Evaluates profit

#### **6. `site_metrics_calculator.py` - Centralized Metrics Calculator**

**Purpose**: Single source of truth for calculating site metrics

**Key Function: `calculate_site_metrics()`**

**Why it exists:**
- Ensures CSV, visualization, and HTML report all use the same calculations
- Prevents inconsistencies

**What it calculates:**
- Coverage (EVs)
- Density (EVs/km²)
- Annual Profit (₹)
- Demand Category (High/Medium/Low/Very Low)
- Location name

**Usage:**
```python
metrics = calculate_site_metrics(
    site_idx=j,
    selected_sites=selected_sites,
    candidate_sites=candidate_sites,
    demand_zones=demand_zones,
    distance_matrix=distance_matrix,
    prices=prices
)
# Returns: {
#     'site_id': 108,
#     'coverage': 783.4,
#     'density': 9.98,
#     'annual_profit': 5674039.0,
#     'demand_category': 'High',
#     ...
# }
```

#### **7. `visualization.py` - Visualization Module**

**Purpose**: Creates all plots and maps

**Key Class: `EVCSVisualizer`**

**Methods:**

**`create_static_map()`**
- Creates PNG map showing:
  - Demand zones (colored by demand level: red = high, orange = medium, yellow = low)
  - Selected charging stations (gray squares, size = capacity)
  - Coverage circles (5km radius, light gray)
  - Labels for each station showing: Site ID, Location, Coverage, Profit, Density, Price

**`plot_objectives()`**
- Creates 3 scatter plots showing Pareto front:
  1. Cost vs Coverage (colored by profit)
  2. Cost vs Profit (colored by coverage)
  3. Coverage vs Distance (colored by profit)

**`plot_solution_summary()`**
- Creates 4 subplots:
  1. Sites by Demand Category (bar chart)
  2. Price Distribution (histogram)
  3. Key Metrics (bar chart: Cost, Coverage, Profit, Distance)
  4. Coverage vs Profit (scatter, colored by demand category)

#### **8. `create_html_report.py` - HTML Report Generator**

**Purpose**: Creates comprehensive HTML summary report

**Function: `create_html_report()`**

**What it includes:**
- Executive summary
- Overall statistics (total sites, cost, coverage, profit, ROI)
- Sites by demand category
- Top 10 most profitable sites
- Top 10 sites by coverage
- Complete site list with all metrics
- Detailed explanations of each metric
- Key insights and recommendations

---

## 📊 Output Files Explained

### 1. `optimal_solution.csv` - Detailed Site Information

**What it contains:**
Each row = one selected charging station with all metrics

**Columns Explained:**

| Column | Description | Example | How to Use |
|--------|-------------|---------|------------|
| `site_id` | Unique identifier | 108 | Reference ID |
| `location_name` | Name of location | "C21 Mall" or "parking" | Identify location |
| `latitude` | Geographic latitude | 22.7486 | For mapping |
| `longitude` | Geographic longitude | 75.8889 | For mapping |
| `demand_category` | High/Medium/Low/Very Low | "High" | Filter by demand |
| `coverage_evs` | EVs within 5km | 783.4 | Sort by coverage |
| `density_per_km2` | EV density | 9.98 | Identify high-density areas |
| `annual_profit_inr` | Expected annual profit | 5674039.0 | **Sort by profit** |
| `price_per_kwh_inr` | Charging price | 10.12 | Check pricing |
| `capacity_charging_points` | Number of charging points | 12 | Check capacity |
| `setup_cost_inr` | One-time base setup cost | 2500000.0 | Calculate civil + equipment spend |
| `grid_upgrade_cost_inr` | Additional distribution upgrade budget | 0.0 | Identify weak feeders |
| `total_setup_cost_inr` | Base + upgrade cost | 2500000.0 | Use for ROI and budgeting |
| `nearest_grid_id` / `nearest_grid_name` | Closest grid node | 5 / "AB Road Substation" | Coordinate work with utility |
| `grid_voltage_kv` | Grid voltage level | 33.0 | Infer available capacity |
| `grid_available_kw` | Estimated available capacity | 6200 | Check if grid can support load |
| `grid_required_kw` | Load drawn by chargers | 600 | Compare vs available |
| `grid_capacity_gap_kw` | Available - required | 5600 | Prioritize reinforcements |
| `distance_to_grid_km` | Distance to nearest node | 0.45 | Cable trenching estimate |
| `grid_capacity_ok` | Boolean flag (True/False) | True | Filter feasible sites |
| `site_type` | Type of location | "mall", "parking", "fuel_station" | Filter by type |

**How to Use:**
```python
import pandas as pd
df = pd.read_csv('optimal_solution.csv')

# Find most profitable sites
top_profit = df.nlargest(10, 'annual_profit_inr')
print(top_profit[['site_id', 'location_name', 'annual_profit_inr', 'coverage_evs']])

# Analyze by demand category
category_stats = df.groupby('demand_category').agg({
    'annual_profit_inr': 'mean',
    'coverage_evs': 'mean',
    'site_id': 'count'
})
print(category_stats)

# Calculate ROI using total investment (setup + upgrades)
df['roi_total'] = (df['annual_profit_inr'] / df['total_setup_cost_inr']) * 100
print(df[['site_id', 'total_setup_cost_inr', 'annual_profit_inr', 'roi_total']].sort_values('roi_total', ascending=False))

# Identify sites needing grid reinforcement
grid_upgrades = df[~df['grid_capacity_ok']]
print(grid_upgrades[['site_id', 'nearest_grid_name', 'grid_upgrade_cost_inr']])
```

### 2. `evcs_map.png` - Visual Map

**What it shows:**
- **Demand Zones**: Colored circles
  - Red = High demand (>2 EVs)
  - Orange = Medium demand (1-2 EVs)
  - Yellow = Low demand (<1 EV)
- **Selected Stations**: Gray squares (size = capacity)
- **Coverage Circles**: Light gray circles (5km radius)
- **Labels**: For each station showing:
  - Site ID
  - Location name or coordinates
  - Demand category (High/Medium/Low/Very Low)
  - Coverage (EVs)
  - Profit (₹)
  - Density (EVs/km²)
  - Price (₹/kWh)
  - Grid summary: nearest node, voltage, available vs required kW, upgrade cost, distance

**How to Read:**
- **Clustered stations** = High-demand areas (multiple stations needed)
- **Isolated stations** = Strategic locations (connectivity, future growth)
- **Overlapping circles** = Good coverage (redundancy)
- **Gaps between circles** = Uncovered areas (may need more stations)

### 3. `objectives_tradeoff.png` - Pareto Front

**What it shows:**
Three scatter plots showing trade-offs between objectives:

1. **Cost vs Coverage** (colored by profit)
   - X-axis: Total setup cost
   - Y-axis: Total EVs covered
   - Color: Annual profit
   - **Interpretation**: Lower-left = cheap but low coverage, Upper-right = expensive but high coverage

2. **Cost vs Profit** (colored by coverage)
   - X-axis: Total setup cost
   - Y-axis: Total annual profit
   - Color: Coverage
   - **Interpretation**: Upper-left = high profit with low cost (best ROI)

3. **Coverage vs Distance** (colored by profit)
   - X-axis: Total EVs covered
   - Y-axis: Average distance to stations
   - Color: Annual profit
   - **Marker shape**: Circles = grid OK, X = upgrade required

**What is Pareto Front?**
- **Pareto-optimal solution**: Cannot improve one objective without worsening another
- Example: Solution A (Cost ₹50M, Coverage 400 EVs) vs Solution B (Cost ₹60M, Coverage 500 EVs)
  - Both are Pareto-optimal (different trade-offs)
  - You choose based on priorities

### 4. `solution_summary.png` - Statistical Dashboard

**What it shows:**
Four subplots:

1. **Sites by Demand Category** (bar chart)
   - Shows count of High/Medium/Low/Very Low demand sites
   - Colors: Green (High), Blue (Medium), Orange (Low), Red (Very Low)

2. **Price Distribution** (histogram)
   - Shows distribution of charging prices across all sites
   - Red dashed line = mean price

3. **Key Metrics** (bar chart)
   - Total Cost (Millions)
   - Coverage (EVs, in thousands)
   - Profit (Millions)
   - Average Distance (km)

4. **Coverage vs Profit** (scatter plot)
   - X-axis: Coverage (EVs)
   - Y-axis: Annual Profit (₹)
   - Color: Demand Category
   - **Interpretation**: Upper-right = high coverage + high profit (best sites)

### 5. `evcs_report.html` - Comprehensive HTML Report

**What it includes:**
- **Executive Summary**: Overview of results
- **Overall Statistics**: Total sites, cost, coverage, profit, ROI
- **Sites by Demand Category**: Counts and explanations
- **Top 10 Most Profitable Sites**: Table with all metrics
- **Top 10 Sites by Coverage**: Table with all metrics
- **Complete Site List**: All sites with full details
- **Understanding the Metrics**: Detailed explanations of:
  - Coverage (EVs)
  - Density (EVs/km²)
  - Annual Profit (₹)
  - Price (₹/kWh)
  - Demand Category
- **Key Insights**: What the results tell us
- **Recommendations**: Actionable advice

**How to Use:**
- Open `evcs_report.html` in any web browser
- Scroll through sections
- Use browser search (Ctrl+F) to find specific sites
- Print or save as PDF for sharing

---

## 🚀 Installation & Usage

### Prerequisites

- Python 3.8 or higher
- Internet connection (for downloading OSM data)

### Installation

1. **Clone or download the project**
   ```bash
   cd code
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   **Required packages:**
   - `numpy`: Numerical computations
   - `pandas`: Data manipulation
   - `geopandas`: Geographic data handling
   - `osmnx`: OpenStreetMap data access
   - `matplotlib`: Plotting
   - `deap`: Genetic algorithms (NSGA-II)
   - `ortools`: Optimization (Benders)
   - `scikit-learn`: Machine learning utilities
   - And more (see `requirements.txt`)

3. **Run the optimization**
   ```bash
   python main.py
   ```

### Expected Runtime

- **Data Loading**: 1-2 minutes (downloads from OSM)
- **Optimization**: 5-10 minutes (50 NSGA-II generations × 30 Benders iterations)
- **Visualization**: 10-30 seconds
- **Total**: ~10-15 minutes

### Output Files

After running, you'll get:
- `optimal_solution.csv` - Site data
- `evcs_map.png` - Visual map
- `objectives_tradeoff.png` - Pareto front
- `solution_summary.png` - Dashboard
- `evcs_report.html` - HTML report

---


## 🏙️ Using Real Indore Data

You can configure the project to use **real ground-truth data** from local CSV files instead of the default hybrid/synthetic data.

### 1. Enable Real Data Mode

Open `config.py` and set the flag:
```python
USE_REAL_DATA = True
```

### 2. Prepare Data Files

Create a directory named `data_real` in the project root. Place the following CSV files inside it:

#### **A. `indore_wards.csv`**
Ward-level population and demographic data.
**Required Columns:**
- `ward_id`: Unique ID
- `ward_name`: Name of the ward
- `population`: Total population
- `area_km2`: Area in square kilometers
- `population_density`: Persons per km²
- `lat`: Latitude of ward centroid
- `lon`: Longitude of ward centroid

#### **B. `indore_ev_stations.csv`**
Existing EV charging stations (if any).
**Required Columns:**
- `station_id`: Unique ID
- `lat`: Latitude
- `lon`: Longitude
- `num_piles`: Number of charging points
- `max_power_kw`: Power capacity (e.g., 50)
- `current_price_inr_per_kwh`: Current charging tariff

#### **C. `indore_ev_tariffs.csv`**
Grid electricity tariffs for EV charging.
**Required Columns:**
- `time_window_id`: ID for time slot
- `start_hour`: Start time (0-23)
- `end_hour`: End time (0-23)
- `grid_price_inr_per_kwh`: Cost of electricity from grid

#### **D. `ev_specs_india.csv`**
Specifications of EV models available in India.
**Required Columns:**
- `ev_model`: Model name
- `range_km`: Driving range
- `battery_kwh`: Battery capacity
- `consumption_wh_per_km`: Energy consumption

### 3. Run the Pipeline

Run `python main.py` as usual. The system will:
1. Load your CSV files.
2. Automatically download the **Indore road network** and **power grid infrastructure** from OpenStreetMap (via `osmnx`).
3. Map your wards and stations to the road network.
4. Run the optimization using this real-world baseline.

> **Note:** If any CSV file is missing, the system will raise an error with instructions.

---

## 📖 Understanding the Results

### What the Outputs Tell You

#### **1. CSV File (`optimal_solution.csv`)**

**Key Questions Answered:**
- ✅ Which sites should we build? (All rows in CSV)
- ✅ How much will it cost? (Sum of `setup_cost_inr`)
- ✅ How many EVs can we serve? (Sum of `coverage_evs`)
- ✅ How much profit will we make? (Sum of `annual_profit_inr`)
- ✅ What's the ROI? (`annual_profit_inr / setup_cost_inr × 100`)

**Example Analysis:**
```python
import pandas as pd
df = pd.read_csv('optimal_solution.csv')

# Total investment
total_cost = df['setup_cost_inr'].sum() / 1e6  # In millions
print(f"Total Investment: ₹{total_cost:.2f}M")

# Total coverage
total_coverage = df['coverage_evs'].sum()
print(f"Total Coverage: {total_coverage:.0f} EVs")

# Total profit
total_profit = df['annual_profit_inr'].sum() / 1e6  # In millions
print(f"Annual Profit: ₹{total_profit:.2f}M")

# ROI
roi = (total_profit / total_cost) * 100
print(f"ROI: {roi:.1f}%")

# Best sites
best_sites = df.nlargest(5, 'annual_profit_inr')
print("\nTop 5 Most Profitable Sites:")
print(best_sites[['site_id', 'location_name', 'annual_profit_inr', 'coverage_evs']])
```

#### **2. Map (`evcs_map.png`)**

**Key Questions Answered:**
- ✅ Where are the stations located? (Gray squares on map)
- ✅ Which areas have high demand? (Red/orange circles)
- ✅ Are there coverage gaps? (Gaps between gray circles)
- ✅ Which stations serve the most EVs? (Check labels)

**How to Read:**
- **High-density clusters** = Multiple stations in same area (high demand)
- **Isolated stations** = Strategic locations (connectivity)
- **Overlapping circles** = Good coverage (redundancy)
- **Large gaps** = Uncovered areas (may need more stations)

#### **3. Pareto Front (`objectives_tradeoff.png`)**

**Key Questions Answered:**
- ✅ What are the trade-offs? (Different solutions on Pareto front)
- ✅ Should we spend more for better coverage? (Cost vs Coverage plot)
- ✅ What's the best ROI? (Cost vs Profit plot)

**Interpretation:**
- **Lower-left** = Cheap but low coverage/profit
- **Upper-right** = Expensive but high coverage/profit
- **Upper-left** = High profit with low cost (best ROI)

#### **4. Summary Dashboard (`solution_summary.png`)**

**Key Questions Answered:**
- ✅ How many high-demand sites? (Bar chart)
- ✅ What's the price range? (Histogram)
- ✅ What are the overall metrics? (Key metrics bars)
- ✅ Which sites have best coverage+profit? (Scatter plot)

#### **5. HTML Report (`evcs_report.html`)**

**Key Questions Answered:**
- ✅ Everything! (Comprehensive summary)
- ✅ Detailed explanations of each metric
- ✅ Top sites by profit and coverage
- ✅ Recommendations

---

## 🔬 Detailed Algorithm Explanation

### NSGA-II (Non-dominated Sorting Genetic Algorithm II)

**What it is:**
A multi-objective genetic algorithm that finds Pareto-optimal solutions.

**How it works:**

1. **Initialization**
   - Creates 50 random solutions (each = binary array: 1 = select site, 0 = don't)
   - Each solution represents a set of selected sites

2. **Evaluation**
   - For each solution, calculates 3 objectives:
     - **Cost**: Sum of setup costs for selected sites
     - **Coverage**: Total EVs within 5km of any selected site
     - **Distance**: Average distance from EVs to nearest station

3. **Non-dominated Sorting**
   - Ranks solutions by Pareto dominance:
     - Solution A dominates B if: A is better in ALL objectives
     - Creates fronts: Front 1 (best), Front 2 (second best), etc.

4. **Selection**
   - Uses tournament selection to pick parents
   - Prefers solutions in better fronts

5. **Crossover & Mutation**
   - **Crossover**: Combines two parent solutions (e.g., take first half from parent 1, second half from parent 2)
   - **Mutation**: Randomly flips some site selections (1→0 or 0→1)

6. **Repeat**
   - For 50 generations
   - Each generation improves the population

**Output:**
- 50 Pareto-optimal solutions
- Each represents a different trade-off (e.g., low cost vs high coverage)

### Benders Decomposition

**What it is:**
A mathematical optimization technique for solving two-stage problems.

**How it works:**

1. **Master Problem**: Determines prices (decision variables)
   - Objective: Maximize profit
   - Constraints: Price bounds (₹8-13/kWh)

2. **Subproblem**: Evaluates profit given prices
   - Calculates demand based on prices
   - Calculates revenue and costs
   - Returns profit

3. **Benders Cuts**: Adds constraints to master problem
   - If subproblem shows low profit, add cut: "Prices must be higher"
   - Iteratively refines solution

4. **Convergence**
   - Repeats for 30 iterations
   - Stops when profit improvement < threshold

**Output:**
- Optimal price for each selected site
- Prices range from ₹10-10.2/kWh (competitive market pricing)

---

## 📐 Metrics Calculation Explained

### Coverage Calculation (Detailed)

**Step 1: Find zones within 5km**
```python
for each demand zone:
    distance = haversine_distance(zone, site)
    if distance <= 5.0:  # Within service radius
        # Include in coverage
```

**Step 2: Get zone demand**
```python
zone_demand = zone['demand']
if zone_demand == 0:
    # Try to estimate from population
    if zone['population'] > 0:
        zone_demand = zone['population'] × zone['ev_density']
```

**Step 3: Spatial interpolation (if still zero)**
```python
if zone_demand == 0:
    # Find nearby zones with demand (within 10km)
    nearby_demand = []
    for nearby_zone:
        if distance <= 10.0 and nearby_zone['demand'] > 0:
            weight = 1.0 / (1.0 + distance)  # Inverse distance weighting
            nearby_demand.append(nearby_zone['demand'] × weight)
    
    if nearby_demand:
        zone_demand = mean(nearby_demand)  # Weighted average
    else:
        zone_demand = baseline_demand  # Conservative estimate
```

**Step 4: Sum coverage**
```python
coverage = sum(zone_demand for all zones within 5km)
```

### Profit Calculation (Detailed)

**Step 1: Utilization rate**
```python
# Base utilization: 30%
# Higher coverage = higher utilization (up to 50%)
utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)
```

**Step 2: Served EVs**
```python
served_evs = coverage × utilization_rate
```

**Step 3: Monthly revenue**
```python
# Average EV: 12 sessions/month × 12.5 kWh = 150 kWh/month
monthly_kwh_per_ev = 12.0 × 12.5  # 150 kWh/month
monthly_revenue = served_evs × monthly_kwh_per_ev × price_per_kwh
```

**Step 4: Monthly cost**
```python
electricity_cost = served_evs × monthly_kwh_per_ev × 4.0  # ₹4/kWh
maintenance = 5000.0  # Fixed ₹5,000/month
monthly_cost = electricity_cost + maintenance
```

**Step 5: Monthly profit**
```python
monthly_profit = monthly_revenue - monthly_cost
```

**Step 6: Annual profit**
```python
annual_profit = monthly_profit × 12
```

**Example:**
- Coverage: 100 EVs
- Utilization: 30% → Served: 30 EVs
- Monthly revenue: 30 × 150 × ₹10 = ₹45,000
- Monthly cost: (30 × 150 × ₹4) + ₹5,000 = ₹23,000
- Monthly profit: ₹45,000 - ₹23,000 = ₹22,000
- **Annual profit: ₹264,000**

### Grid Capacity & Upgrade Calculation

**Step 1: Required load from chargers**
```python
charger_power_kw = 50  # assumed DC fast charger size
required_kw = capacity_charging_points * charger_power_kw
```

**Step 2: Available grid capacity**
- Each grid node carries a voltage tag (33 kV, 11 kV, etc.) from OSM
- We map voltage → typical available kW (e.g., 33 kV ≈ 6,200 kW, 11 kV ≈ 210 kW)
- Substations get a +20% buffer, transformers a -20% derating

**Step 3: Capacity gap & upgrade cost**
```python
upgrade_needed_kw = max(0, required_kw - available_kw)
upgrade_cost_inr = upgrade_needed_kw * 850  # ₹850 per kW for distribution upgrades
```

**Step 4: Distance to grid node**
- Nearest substation/transformer found using a BallTree on lat/lon
- Distance recorded in km to highlight trenching / cabling effort

**Step 5: Total investment per site**
```python
total_setup_cost = setup_cost + upgrade_cost_inr
```

**Interpretation:**
- `grid_capacity_ok = True` → existing grid can absorb the load
- `grid_capacity_ok = False` → allocate upgrade budget before construction
- High upgrade cost spots pinpoint weak feeders to reinforce or avoid

---

## 🐛 Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'geopandas'"**
- **Solution**: `pip install -r requirements.txt`

**2. "OSM data download is slow"**
- **Solution**: This is normal. OSM data download takes 1-2 minutes. Be patient.

**3. "Zero coverage/profit at some sites"**
- **Explanation**: Some sites may be selected for strategic reasons (connectivity, future growth)
- **Solution**: Check `min_distance` in CSV. If >5km, site is outside service radius.

**4. "All sites show high profit"**
- **Fixed**: Updated profit calculation to be more realistic (150 kWh/month instead of 200)

**5. "Distance matrix shape mismatch"**
- **Solution**: Ensure `distance_matrix.shape == (n_zones, n_sites)`. Check data loading.

**6. "Optimization takes too long"**
- **Solution**: Reduce `nsga2_generations` or `benders_iterations` in `main.py`

### Getting Help

- Check error messages carefully
- Verify all dependencies are installed
- Ensure internet connection for OSM data
- Check that Indore coordinates are correct (22.7196°N, 75.8577°E)

---

## 📚 Additional Resources

### Key Concepts

- **Pareto Optimality**: A solution is Pareto-optimal if you cannot improve one objective without worsening another
- **Multi-objective Optimization**: Optimizing multiple conflicting objectives simultaneously
- **Genetic Algorithms**: Evolutionary algorithms that mimic natural selection
- **Benders Decomposition**: Mathematical technique for two-stage optimization

### References

- NSGA-II: Deb et al. (2002) "A fast and elitist multiobjective genetic algorithm"
- Benders Decomposition: Benders (1962) "Partitioning procedures for solving mixed-variables programming problems"
- Haversine Formula: For calculating great-circle distances

---

## 📝 Summary

**What this project does:**
- Optimizes EV charging station placement and pricing for Indore city
- Uses hybrid approach: NSGA-II (locations) + Benders (pricing)
- Generates comprehensive reports and visualizations

**Key outputs:**
- `optimal_solution.csv`: All selected sites with metrics
- `evcs_map.png`: Visual map with labeled stations
- `objectives_tradeoff.png`: Pareto front showing trade-offs
- `solution_summary.png`: Statistical dashboard
- `evcs_report.html`: Comprehensive HTML report

**How to use:**
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python main.py`
3. View outputs: Open CSV, PNG files, and HTML report
4. Analyze: Use CSV for detailed analysis, maps for visualization

**Questions?**
- Check this README for detailed explanations
- Review code comments for implementation details
- Check HTML report for metric explanations

---

**Happy Optimizing! 🚀⚡**
