"""
Site Metrics Calculator - Centralized calculation logic

This module provides a single source of truth for calculating
coverage, density, profit, and demand categories for charging stations.
Used by both visualization and CSV generation to ensure consistency.

Author: EVCS Optimization Team
Date: 2024
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple


PROXIMITY_PENALTY_RADIUS_KM = 2.5
PROXIMITY_PENALTY_STRENGTH = 0.35


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometers."""
    R = 6371.0
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def compute_proximity_penalty_factor(site_idx: int,
                                     selected_sites: np.ndarray,
                                     candidate_sites: pd.DataFrame,
                                     radius_km: float = PROXIMITY_PENALTY_RADIUS_KM,
                                     strength: float = PROXIMITY_PENALTY_STRENGTH) -> float:
    """
    Compute demand dilution factor due to nearby selected stations.
    Returns a multiplier in [0, 1].
    """
    if candidate_sites is None or len(candidate_sites) == 0:
        return 1.0
    
    selected_mask = np.array(selected_sites).astype(int)
    selected_indices = np.where(selected_mask == 1)[0]
    if len(selected_indices) <= 1 or site_idx not in selected_indices:
        return 1.0
    
    site = candidate_sites.iloc[site_idx]
    lat1 = float(site['latitude'])
    lon1 = float(site['longitude'])
    
    penalty = 0.0
    for other_idx in selected_indices:
        if other_idx == site_idx:
            continue
        other_site = candidate_sites.iloc[other_idx]
        lat2 = float(other_site['latitude'])
        lon2 = float(other_site['longitude'])
        dist = _haversine_distance(lat1, lon1, lat2, lon2)
        if dist < radius_km:
            penalty += max(0.0, (radius_km - dist) / radius_km)
    
    penalty_factor = max(0.2, 1.0 - strength * penalty)
    return penalty_factor


def calculate_site_metrics(site_idx: int, 
                         selected_sites: np.ndarray,
                         candidate_sites: pd.DataFrame,
                         demand_zones: pd.DataFrame,
                         distance_matrix: np.ndarray,
                         prices: np.ndarray) -> Dict:
    """
    Calculate all metrics for a single charging station site.
    
    This function ensures consistent calculations across visualization
    and CSV generation.
    
    Parameters:
    -----------
    site_idx : int
        Index of the site in candidate_sites
    selected_sites : np.ndarray
        Binary array indicating selected sites
    candidate_sites : pd.DataFrame
        DataFrame of all candidate sites
    demand_zones : pd.DataFrame
        DataFrame of all demand zones
    distance_matrix : np.ndarray
        Distance matrix (n_zones, n_sites)
    prices : np.ndarray
        Price array for all sites
        
    Returns:
    --------
    Dict
        Dictionary with all calculated metrics
    """
    site = candidate_sites.iloc[site_idx]
    price = float(prices[site_idx]) if site_idx < len(prices) else 10.0
    
    n_zones = len(demand_zones)
    
    # Calculate coverage (demand within 5km)
    coverage = 0.0
    density_sum = 0.0
    min_distance_to_demand = np.inf
    zones_in_range = 0
    
    # First, find average demand density from zones with actual demand
    zones_with_demand = []
    for i in range(n_zones):
        zone_demand = float(demand_zones.iloc[i]['demand'])
        if zone_demand == 0 and 'population' in demand_zones.columns:
            population = float(demand_zones.iloc[i]['population'])
            if population > 0:
                ev_density = float(demand_zones.iloc[i].get('ev_density', 0.03))
                zone_demand = population * ev_density
        if zone_demand > 0:
            zones_with_demand.append(zone_demand)
    
    avg_demand_density = np.mean(zones_with_demand) if zones_with_demand else 1.0
    baseline_demand_per_zone = avg_demand_density * 0.5
    
    # Pre-extract demand data as arrays for faster access (avoid repeated pandas indexing)
    demand_values = demand_zones['demand'].values
    has_population = 'population' in demand_zones.columns
    population_values = demand_zones['population'].values if has_population else np.zeros(n_zones)
    has_ev_density = 'ev_density' in demand_zones.columns
    ev_density_values = demand_zones['ev_density'].values if has_ev_density else np.full(n_zones, 0.03)
    
    # Iterate through all demand zones
    for i in range(n_zones):
        if i >= distance_matrix.shape[0] or site_idx >= distance_matrix.shape[1]:
            continue
            
        dist = float(distance_matrix[i, site_idx])
        
        if np.isnan(dist) or dist < 0:
            continue
            
        min_distance_to_demand = min(min_distance_to_demand, dist)
        
        if dist <= 5.0:  # 5km service radius
            zone_demand = float(demand_values[i])
            
            # If demand is zero, try to estimate from population
            if zone_demand == 0 and has_population:
                population = float(population_values[i])
                if population > 0:
                    ev_density = float(ev_density_values[i])
                    zone_demand = population * ev_density
            
            # If still zero, use baseline (skip expensive interpolation)
            if zone_demand == 0:
                zone_demand = baseline_demand_per_zone
            
            if zone_demand > 0:
                coverage += zone_demand
                density_sum += zone_demand
                zones_in_range += 1
    
    # Calculate density
    if coverage > 0 and zones_in_range > 0:
        coverage_area_km2 = np.pi * 5.0 * 5.0
        density = density_sum / coverage_area_km2
    else:
        density = 0.0
    
    # Handle partial coverage for sites just outside range
    if coverage == 0 and min_distance_to_demand < np.inf:
        if min_distance_to_demand <= 7.0:
            nearest_demand = 0.0
            for i in range(n_zones):
                if i >= distance_matrix.shape[0] or site_idx >= distance_matrix.shape[1]:
                    continue
                dist = float(distance_matrix[i, site_idx])
                if np.isnan(dist) or dist < 0:
                    continue
                if dist <= 7.0:
                    zone_demand = float(demand_values[i])
                    if zone_demand == 0 and has_population:
                        population = float(population_values[i])
                        if population > 0:
                            ev_density = float(ev_density_values[i])
                            zone_demand = population * ev_density
                    
                    if zone_demand > 0:
                        weight = max(0, 1 - (dist - 5.0) / 2.0)
                        nearest_demand += zone_demand * weight
            coverage = nearest_demand
            if coverage > 0:
                density = coverage / (np.pi * 7.0 * 7.0)
    
    # Apply proximity penalty
    competition_factor = compute_proximity_penalty_factor(
        site_idx=site_idx,
        selected_sites=selected_sites,
        candidate_sites=candidate_sites
    )
    if competition_factor < 1.0:
        coverage *= competition_factor
        density *= competition_factor
    
    # Calculate profit
    utilization_rate = 0.3
    if coverage > 0:
        utilization_rate = min(0.5, 0.2 + (coverage / 100.0) * 0.3)
    
    estimated_demand = coverage * utilization_rate
    
    # Revenue calculation
    charging_sessions_per_ev_per_month = 12.0
    kwh_per_session = 12.5
    monthly_kwh_per_ev = charging_sessions_per_ev_per_month * kwh_per_session
    
    actual_served_evs = estimated_demand
    monthly_revenue = actual_served_evs * monthly_kwh_per_ev * price
    
    # Operating cost
    electricity_cost_per_kwh = 4.0
    monthly_operating_cost = actual_served_evs * monthly_kwh_per_ev * electricity_cost_per_kwh
    monthly_maintenance = 5000.0
    
    # Monthly and annual profit
    monthly_profit = monthly_revenue - monthly_operating_cost - monthly_maintenance
    annual_profit = monthly_profit * 12

    # --- Queueing model (M/M/c or M/M/c/K) ---
    # Assumptions and defaults
    sessions_per_ev_per_month = 12.0
    avg_energy_kwh_per_session = float(site.get('avg_energy_kwh', 12.5))
    charger_power_kw = float(site.get('charger_power_kw', 50.0))
    # Number of parallel chargers (servers)
    try:
        c_servers = int(site.get('capacity', 1))
    except Exception:
        c_servers = 1

    # Optional station capacity K (charging + waiting). If not provided, treat as infinite (None)
    K_capacity = site.get('station_capacity_K', None)
    if K_capacity is not None:
        try:
            K_capacity = int(K_capacity)
        except Exception:
            K_capacity = None

    # Compute service parameters
    # Average charging time (hours per vehicle)
    T_chg_hours = avg_energy_kwh_per_session / max(0.0001, charger_power_kw)
    # service rate per charger in vehicles per hour
    mu_per_charger = 1.0 / T_chg_hours if T_chg_hours > 0 else 0.0

    # Estimate arrival rate (vehicles per hour) from estimated served EVs
    # estimated_demand (coverage * utilization) is number of EVs served per month approx
    # arrival_rate_per_hour = (estimated_served_evs * sessions_per_ev_per_month) / (30*24)
    arrival_rate_per_hour = 0.0
    if actual_served_evs > 0:
        arrival_rate_per_hour = (actual_served_evs * sessions_per_ev_per_month) / (30.0 * 24.0)

    # --- Split arrivals into peak and normal periods ---
    # Allow site-level overrides: 'peak_hours' (int), 'peak_fraction' (0-1 float), 'normal_hours' (int)
    peak_hours = site.get('peak_hours', 4)
    try:
        peak_hours = int(peak_hours)
    except Exception:
        peak_hours = 4

    peak_fraction = site.get('peak_fraction', 0.35)
    try:
        peak_fraction = float(peak_fraction)
        peak_fraction = max(0.0, min(1.0, peak_fraction))
    except Exception:
        peak_fraction = 0.35

    normal_hours = site.get('normal_hours', 12)
    try:
        normal_hours = int(normal_hours)
    except Exception:
        normal_hours = 12

    # Daily arrivals (vehicles per day)
    daily_arrivals = (actual_served_evs * sessions_per_ev_per_month) / 30.0 if actual_served_evs > 0 else 0.0
    peak_arrivals = daily_arrivals * peak_fraction
    normal_arrivals = daily_arrivals * (1.0 - peak_fraction)

    # Arrival rates per hour for each period
    arrival_rate_peak_per_hour = peak_arrivals / max(1.0, peak_hours)
    arrival_rate_normal_per_hour = normal_arrivals / max(1.0, normal_hours)

    def _mmc_metrics(lam: float, mu: float, c: int, K: int | None = None):
        """
        Compute M/M/c or M/M/c/K performance metrics.

        Returns dict with keys: rho, P0, Lq, Wq, W, L, P_block, utilization
        All time values in hours unless noted otherwise (Wq in hours).
        """
        metrics = {
            'rho': None,
            'P0': None,
            'Lq': None,
            'Wq': None,
            'W': None,
            'L': None,
            'P_block': 0.0,
            'utilization': None
        }

        if mu <= 0 or c <= 0:
            return metrics

        a = lam / mu if mu > 0 else 0.0
        rho = lam / (c * mu) if (c * mu) > 0 else float('inf')
        metrics['rho'] = rho

        # Helper to compute factorial safely
        from math import factorial

        if K is None:
            # M/M/c (infinite queue)
            # Compute P0
            sum_terms = 0.0
            for n in range(0, c):
                sum_terms += (a ** n) / factorial(n)
            # last term
            if 1 - rho == 0:
                P0 = 0.0
            else:
                P0 = 1.0 / (sum_terms + (a ** c) / (factorial(c) * (1.0 - rho)))
            metrics['P0'] = P0

            # Lq
            if rho >= 1.0:
                Lq = float('inf')
            else:
                Lq = P0 * (a ** c) * rho / (factorial(c) * ((1.0 - rho) ** 2))
            Wq = Lq / lam if lam > 0 else 0.0
            W = Wq + (1.0 / mu)
            L = lam * W
            metrics.update({'P0': P0, 'Lq': Lq, 'Wq': Wq, 'W': W, 'L': L, 'P_block': 0.0})
            metrics['utilization'] = min(1.0, a / c) if c > 0 else None
            return metrics
        else:
            # M/M/c/K finite capacity (blocking)
            # Use birth-death stationary probabilities
            N = K
            # Compute normalization constant
            denom = 0.0
            for n in range(0, c):
                denom += (a ** n) / factorial(n)
            for n in range(c, N + 1):
                denom += (a ** n) / (factorial(c) * (c ** (n - c)))
            P0 = 1.0 / denom if denom > 0 else 0.0
            probs = []
            for n in range(0, c):
                probs.append((a ** n) / factorial(n) * P0)
            for n in range(c, N + 1):
                probs.append((a ** n) / (factorial(c) * (c ** (n - c))) * P0)

            P_block = probs[-1] if len(probs) == (N + 1) else 0.0
            # Effective arrival rate (accepted) = lam * (1 - P_block)
            lam_eff = lam * (1.0 - P_block)

            # L = sum n * Pn
            L = sum(n * pn for n, pn in enumerate(probs))
            # Lq = sum_{n=c}^{N} (n-c) * Pn
            Lq = 0.0
            for n in range(c, N + 1):
                Lq += (n - c) * probs[n]

            W = L / lam_eff if lam_eff > 0 else float('inf')
            Wq = Lq / lam_eff if lam_eff > 0 else float('inf')

            metrics.update({'P0': P0, 'Lq': Lq, 'Wq': Wq, 'W': W, 'L': L, 'P_block': P_block})
            metrics['utilization'] = min(1.0, a / c) if c > 0 else None
            return metrics

    # Compute queue metrics for overall/average, peak and normal periods
    queue_metrics = _mmc_metrics(arrival_rate_per_hour, mu_per_charger, c_servers, K_capacity)
    peak_queue_metrics = _mmc_metrics(arrival_rate_peak_per_hour, mu_per_charger, c_servers, K_capacity)
    normal_queue_metrics = _mmc_metrics(arrival_rate_normal_per_hour, mu_per_charger, c_servers, K_capacity)

    # Convert waiting times to minutes for reporting convenience
    Wq_hours = queue_metrics.get('Wq', 0.0) or 0.0
    W_hours = queue_metrics.get('W', 0.0) or 0.0
    queue_wait_min = Wq_hours * 60.0
    total_time_min = W_hours * 60.0

    # Attach queue metrics to returned dict
    
    # Categorize demand
    if coverage >= 100:
        demand_category = 'High'
    elif coverage >= 50:
        demand_category = 'Medium'
    elif coverage > 0:
        demand_category = 'Low'
    else:
        demand_category = 'Very Low'
    
    # Get location name
    location_name = site.get('name', '')
    if not location_name and 'site_type' in site:
        location_name = str(site['site_type'])
    
    return {
        'site_id': int(site['site_id']),
        'location_name': location_name,
        'latitude': float(site['latitude']),
        'longitude': float(site['longitude']),
        'coverage': coverage,
        'density': density,
        'annual_profit': annual_profit,
        'price': price,
        'capacity': int(site['capacity']),
        'setup_cost': float(site['setup_cost']),
        'total_setup_cost': float(site.get('total_setup_cost', site['setup_cost'])),
        'grid_upgrade_cost': float(site.get('grid_upgrade_cost', 0.0)),
        'grid_available_kw': float(site.get('grid_available_kw', 0.0)),
        'grid_required_kw': float(site.get('grid_required_kw', 0.0)),
        'grid_capacity_gap_kw': float(site.get('grid_capacity_gap_kw', 0.0)),
        'distance_to_grid_km': float(site.get('distance_to_grid_km', np.nan)),
        'grid_voltage_kv': float(site.get('grid_voltage_kv', np.nan)) if not pd.isnull(site.get('grid_voltage_kv', np.nan)) else np.nan,
        'nearest_grid_id': int(site.get('nearest_grid_id', -1)),
        'nearest_grid_name': site.get('nearest_grid_name', ''),
        'grid_capacity_ok': bool(site.get('grid_capacity_ok', True)),
        'site_type': site.get('site_type', 'unknown'),
        'demand_category': demand_category,
        'min_distance': min_distance_to_demand,
        'competition_penalty': 1.0 - competition_factor,
        'queue': {
            'arrival_rate_per_hour': arrival_rate_per_hour,
            'service_rate_per_charger_per_hour': mu_per_charger,
            'chargers': c_servers,
            'station_capacity_K': K_capacity,
            'avg_charging_time_min': T_chg_hours * 60.0,
            'avg_wait_time_min': queue_wait_min,
            'avg_time_in_station_min': total_time_min,
            'Lq': queue_metrics.get('Lq', None),
            'L': queue_metrics.get('L', None),
            'P0': queue_metrics.get('P0', None),
            'P_block': queue_metrics.get('P_block', 0.0),
            'utilization': queue_metrics.get('utilization', None),
            # Peak/Normal breakdown
            'peak': {
                'arrival_rate_per_hour': arrival_rate_peak_per_hour,
                'Wq_hours': peak_queue_metrics.get('Wq', None),
                'W_hours': peak_queue_metrics.get('W', None),
                'Lq': peak_queue_metrics.get('Lq', None),
                'L': peak_queue_metrics.get('L', None),
                'P_block': peak_queue_metrics.get('P_block', 0.0),
                'utilization': peak_queue_metrics.get('utilization', None),
                'avg_wait_time_min': (peak_queue_metrics.get('Wq', 0.0) or 0.0) * 60.0,
                'avg_time_in_station_min': (peak_queue_metrics.get('W', 0.0) or 0.0) * 60.0
            },
            'normal': {
                'arrival_rate_per_hour': arrival_rate_normal_per_hour,
                'Wq_hours': normal_queue_metrics.get('Wq', None),
                'W_hours': normal_queue_metrics.get('W', None),
                'Lq': normal_queue_metrics.get('Lq', None),
                'L': normal_queue_metrics.get('L', None),
                'P_block': normal_queue_metrics.get('P_block', 0.0),
                'utilization': normal_queue_metrics.get('utilization', None),
                'avg_wait_time_min': (normal_queue_metrics.get('Wq', 0.0) or 0.0) * 60.0,
                'avg_time_in_station_min': (normal_queue_metrics.get('W', 0.0) or 0.0) * 60.0
            }
        }
    }


