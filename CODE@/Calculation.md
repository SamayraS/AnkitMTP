# 📊 Calculation Guide - EV Charging Station Optimization

This document explains how the code runs, what estimations are used, and provides step-by-step calculation examples to help you understand the optimization process.

---

## 🚀 How to Run the Code

### **Step 1: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 2: Run the Main Script**
```bash
python main.py
```

### **Step 3: What Happens When You Run**

The code executes in **4 main steps**:

```
============================================================
EV CHARGING STATION OPTIMIZATION - INDORE CITY
Hybrid Approach: Benders Decomposition + NSGA-II
============================================================

[STEP 1] Loading Indore city data...
  - Fetching demand zones from OpenStreetMap...
  - Fetching candidate sites (parking, malls, fuel stations)...
  - Calculating distance matrix...
  - Loading power grid infrastructure...

Data Summary:
  - Demand zones: 45
  - Candidate sites: 28
  - Total demand: 1,250.50 EVs
  - Distance matrix shape: (45, 28)

[STEP 2] Running hybrid optimization...
  - Running NSGA-II (50 generations, population 50)...
  - Optimizing prices with Benders Decomposition...
  - Found 12 Pareto-optimal solutions...

[STEP 3] Creating visualizations...
  - Generating map visualization...
  - Creating Pareto front plot...
  - Creating solution summary...

[STEP 4] Generating output files...
  - Saving solution to optimal_solution.csv...
  - Creating HTML report...

============================================================
SOLUTION SUMMARY
============================================================

Selected Charging Stations: 8

Financial Metrics:
  Total Setup Cost: 42,500,000.00 INR
  Grid Upgrade Cost: 3,400,000.00 INR
  Expected Revenue: 15,600,000.00 INR
  Expected Profit: 8,200,000.00 INR
  ROI: 19.29%

Coverage Metrics:
  Demand Covered: 980.25 EVs
  Average Distance: 3.45 km
  Coverage Percentage: 78.42%

Pricing:
  Average Price: 10.85 INR/kWh
  Price Range: 10.00 - 12.50 INR/kWh

============================================================
OPTIMIZATION COMPLETE!
============================================================
```

---

## 📐 Key Estimations Used in the Code

### **1. EV Demand Estimation**

**How it works:**
- If a zone has zero demand, we estimate it from population:
  ```
  zone_demand = population × ev_density
  ```
- **Default EV density:** 3% (3 EVs per 100 people)
- **Rationale:** Based on current EV adoption rates in Indian cities

**Example:**
- Zone population: 10,000 people
- EV density: 3% (0.03)
- **Estimated demand:** 10,000 × 0.03 = **300 EVs**

---

### **2. Service Radius**

**Estimation:**
- **Primary service radius:** 5 km
- **Extended radius (partial coverage):** 7 km
- **Rationale:** Most EV owners are willing to travel up to 5 km for charging

**What this means:**
- All demand zones within 5 km of a station are fully covered
- Zones 5-7 km away get partial coverage (weighted by distance)

---

### **3. Utilization Rate**

**Formula:**
```
utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)
```

**Breakdown:**
- **Base utilization:** 20% (minimum)
- **Increases by:** 0.3% per EV covered
- **Maximum:** 50%

**Example:**
- Coverage: 150 EVs
- Utilization rate: min(0.5, 0.2 + (150/100) × 0.3) = min(0.5, 0.65) = **0.5 (50%)**
- **Served EVs:** 150 × 0.5 = **75 EVs**

---

### **4. Charging Behavior**

**Assumptions:**
- **Charging sessions per EV per month:** 12 sessions
- **kWh per session:** 12.5 kWh
- **Monthly kWh per EV:** 12 × 12.5 = **150 kWh/month**

**Rationale:** Based on average EV usage patterns in urban India

---

### **5. Pricing Model**

**Base price:** ₹10/kWh

**Price adjustment:**
- Higher demand density → Can charge higher price
- Price range: ₹10 - ₹13/kWh
- Optimized using Benders Decomposition algorithm

---

### **6. Cost Assumptions**

**Electricity cost:** ₹4/kWh (grid purchase rate)

**Maintenance cost:** ₹5,000/month per station

**Setup cost:** Based on capacity
- Small station (4 chargers): ~₹3,000,000
- Medium station (8 chargers): ~₹5,000,000
- Large station (16 chargers): ~₹8,000,000

**Grid upgrade cost:** ₹850/kW if grid capacity is insufficient

---

### **7. Grid Capacity Estimation**

**Voltage-based capacity mapping:**
- **33 kV substation:** 6,200 kW base capacity
- **22 kV substation:** 3,500 kW base capacity
- **11 kV transformer:** 210 kW base capacity

**Adjustments:**
- **Substations:** +20% buffer (more headroom)
- **Transformers:** -20% derating (operate closer to capacity)

**Example:**
- Nearest grid: 33 kV substation
- Base capacity: 6,200 kW
- **Available capacity:** 6,200 × 1.2 = **7,440 kW**

---

### **8. Spatial Interpolation**

**When used:** If a demand zone has zero demand and no population data

**Method:**
- Look at nearby zones within 10 km
- Use inverse distance weighting:
  ```
  weight = 1.0 / (1.0 + distance)
  ```
- Estimate demand from weighted average of nearby zones

**Example:**
- Zone A (distance 2 km, demand 200 EVs): weight = 1/(1+2) = 0.33
- Zone B (distance 5 km, demand 150 EVs): weight = 1/(1+5) = 0.17
- **Estimated demand:** (200×0.33 + 150×0.17) / (0.33+0.17) = **183 EVs**

---

## 🧮 Step-by-Step Calculation Examples

### **Example 1: Coverage Calculation**

**Scenario:** A charging station at location (22.72°N, 75.86°E)

**Step 1: Find zones within 5 km**
```
Zone 1: Distance = 3.2 km → Included
Zone 2: Distance = 4.8 km → Included
Zone 3: Distance = 6.1 km → Excluded (outside 5 km)
Zone 4: Distance = 2.1 km → Included
```

**Step 2: Get zone demands**
```
Zone 1: 120 EVs (from data)
Zone 2: 0 EVs (zero demand) → Estimate from population
        Population: 8,000
        EV density: 3%
        Estimated: 8,000 × 0.03 = 240 EVs
Zone 4: 95 EVs (from data)
```

**Step 3: Calculate total coverage**
```
Coverage = 120 + 240 + 95 = 455 EVs
```

---

### **Example 2: Profit Calculation**

**Given:**
- Coverage: 455 EVs
- Price: ₹11/kWh
- Setup cost: ₹5,000,000

**Step 1: Calculate utilization rate**
```
utilization_rate = min(0.5, 0.2 + (455/100) × 0.3)
                 = min(0.5, 0.2 + 1.365)
                 = min(0.5, 1.565)
                 = 0.5 (50%)
```

**Step 2: Calculate served EVs**
```
served_evs = 455 × 0.5 = 227.5 EVs
```

**Step 3: Calculate monthly revenue**
```
monthly_kwh_per_ev = 12 sessions × 12.5 kWh = 150 kWh
monthly_revenue = 227.5 × 150 × ₹11 = ₹3,753,750
```

**Step 4: Calculate monthly operating cost**
```
electricity_cost = 227.5 × 150 × ₹4 = ₹136,500
maintenance = ₹5,000
monthly_operating_cost = ₹136,500 + ₹5,000 = ₹141,500
```

**Step 5: Calculate monthly profit**
```
monthly_profit = ₹3,753,750 - ₹141,500 = ₹3,612,250
```

**Step 6: Calculate annual profit**
```
annual_profit = ₹3,612,250 × 12 = ₹43,347,000
```

**Step 7: Calculate ROI**
```
ROI = (annual_profit / setup_cost) × 100
    = (₹43,347,000 / ₹5,000,000) × 100
    = 866.94%
```

---

### **Example 3: Grid Capacity Check**

**Given:**
- Station capacity: 8 charging points
- Each charger: 50 kW
- Nearest grid: 22 kV substation

**Step 1: Calculate required load**
```
grid_required_kw = 8 × 50 = 400 kW
```

**Step 2: Calculate available capacity**
```
Base capacity (22 kV): 3,500 kW
Substation buffer: +20%
grid_available_kw = 3,500 × 1.2 = 4,200 kW
```

**Step 3: Check if capacity is sufficient**
```
Capacity gap = 4,200 - 400 = 3,800 kW
Since gap > 0, grid capacity is OK ✓
```

**If capacity was insufficient:**
```
If grid_required_kw = 5,000 kW
Capacity gap = 4,200 - 5,000 = -800 kW (insufficient)
Grid upgrade cost = 800 × ₹850 = ₹680,000
```

---

### **Example 4: Density Calculation**

**Given:**
- Coverage: 455 EVs
- Service radius: 5 km

**Step 1: Calculate coverage area**
```
coverage_area_km2 = π × (5)² = π × 25 = 78.54 km²
```

**Step 2: Calculate density**
```
density = 455 / 78.54 = 5.79 EVs/km²
```

**Interpretation:**
- **High density:** > 10 EVs/km² (excellent location)
- **Medium density:** 5-10 EVs/km² (good location)
- **Low density:** < 5 EVs/km² (may need larger service radius)

---

## 🔄 Complete Workflow Example

### **Input Data:**
```
City: Indore, Madhya Pradesh
Center: (22.7196°N, 75.8577°E)
Radius: 15 km
Budget: ₹50,000,000
```

### **Processing Steps:**

1. **Data Loading:**
   - Loads 45 demand zones from OpenStreetMap
   - Loads 28 candidate sites (malls, parking, fuel stations)
   - Calculates distance matrix (45 × 28 = 1,260 distances)

2. **Optimization:**
   - NSGA-II finds best site combinations (50 generations)
   - Benders Decomposition optimizes prices for each combination
   - Returns 8-12 Pareto-optimal solutions

3. **Best Solution Selection:**
   - Selects solution with best profit-to-cost ratio
   - Example: 8 stations selected

4. **Metrics Calculation:**
   - For each selected station:
     - Coverage: EVs within 5 km
     - Density: EVs per km²
     - Profit: Annual profit calculation
     - Grid check: Capacity verification

5. **Output Generation:**
   - CSV file with all metrics
   - Map visualization
   - HTML report

---

## 📋 Summary of All Estimations

| Parameter | Value | Source/Rationale |
|-----------|-------|------------------|
| EV Density | 3% | Current Indian EV adoption rate |
| Service Radius | 5 km | User convenience threshold |
| Utilization Rate | 20-50% | Based on coverage (20% base + 0.3% per EV) |
| Sessions/EV/Month | 12 | Average charging frequency |
| kWh/Session | 12.5 kWh | Typical charging session size |
| Electricity Cost | ₹4/kWh | Grid purchase rate |
| Maintenance | ₹5,000/month | Per-station maintenance |
| Base Price | ₹10/kWh | Market competitive price |
| Price Range | ₹10-13/kWh | Demand-based optimization |
| Charger Power | 50 kW | Standard fast charger |
| Grid Upgrade Cost | ₹850/kW | Distribution upgrade cost |
| Substation Buffer | +20% | Safety margin |
| Transformer Derating | -20% | Operating margin |

---

## 💡 Tips for Understanding the Results

1. **Coverage vs. Profit:**
   - High coverage doesn't always mean high profit
   - Profit depends on utilization rate and pricing

2. **Distance Matters:**
   - Stations closer to demand zones have better coverage
   - But may have higher land costs

3. **Grid Capacity:**
   - Always check if grid can support the station
   - Upgrade costs can significantly impact ROI

4. **Pricing Strategy:**
   - Higher prices → More revenue but less demand
   - Optimization finds the sweet spot

5. **Budget Constraint:**
   - Limited budget → Fewer stations
   - Need to balance coverage and cost

---

## 🎯 Quick Reference: Key Formulas

### **Coverage:**
```
coverage = Σ(zone_demand for zones within 5 km)
```

### **Density:**
```
density = coverage / (π × 5²)
```

### **Utilization:**
```
utilization_rate = min(0.5, 0.2 + (coverage / 100) × 0.3)
```

### **Profit:**
```
served_evs = coverage × utilization_rate
monthly_revenue = served_evs × 150 kWh × price
monthly_cost = served_evs × 150 kWh × ₹4 + ₹5,000
annual_profit = (monthly_revenue - monthly_cost) × 12
```

### **Distance (Haversine):**
```
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1-a))
distance = 6371 × c  (in km)
```

---

## 📞 Need Help?

If you have questions about:
- **Specific calculations:** Check the formulas above
- **Code execution:** Run `python main.py` and check the output
- **Results interpretation:** Review the CSV file and visualizations
- **Parameter tuning:** Modify values in `main.py` or `data_loader.py`

---

**Last Updated:** 2024  
**Version:** 1.0

