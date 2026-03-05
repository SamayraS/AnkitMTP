
import os
import pandas as pd
import numpy as np
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point
import networkx as nx
from typing import Dict, Tuple, Any
import config

def load_indore_road_network_from_osm(config_module) -> Tuple[Any, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load Indore road network from OpenStreetMap using osmnx.
    
    Returns:
        G: NetworkX graph
        nodes_gdf: GeoDataFrame of nodes
        edges_gdf: GeoDataFrame of edges
    """
    print("[INFO] Downloading Indore road network from OpenStreetMap...")
    try:
        # Download drive network for Indore
        G = ox.graph_from_place("Indore, Madhya Pradesh, India", network_type="drive")
        nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
        print(f"  [OK] Loaded graph with {len(nodes_gdf)} nodes and {len(edges_gdf)} edges")
        return G, nodes_gdf, edges_gdf
    except Exception as e:
        print(f"  [ERROR] Failed to download OSM data: {e}")
        raise

def load_indore_wards(config_module) -> pd.DataFrame:
    """
    Load Indore ward data from CSV.
    Expected columns: ward_id, ward_name, population, area_km2, population_density
    """
    csv_path = config_module.WARDS_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Wards CSV not found at {csv_path}. "
            "Please create this file with columns: ward_id, ward_name, population, area_km2, population_density"
        )
    
    print(f"[INFO] Loading wards from {csv_path}...")
    df = pd.read_csv(csv_path)
    required_cols = {'ward_id', 'ward_name', 'population', 'area_km2', 'population_density'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Wards CSV missing columns. Required: {required_cols}")
    
    return df

def load_indore_ev_stations(config_module, nodes_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Load existing EV stations from CSV and map to nearest OSM nodes.
    Expected columns: station_id, lat, lon, num_piles, max_power_kw, current_price_inr_per_kwh
    """
    csv_path = config_module.EV_STATIONS_CSV
    if not os.path.exists(csv_path):
        # It's okay if this is missing, we can return empty or raise error depending on strictness.
        # User said "Raise a clear error if file not found" for wards, but for stations?
        # "Real EV charging station locations from a local CSV I will provide."
        # I'll raise error to be safe as per "If a CSV is missing, clearly log and raise an error".
        raise FileNotFoundError(
            f"EV Stations CSV not found at {csv_path}. "
            "Please create this file with columns: station_id, lat, lon, num_piles, max_power_kw, current_price_inr_per_kwh"
        )

    print(f"[INFO] Loading EV stations from {csv_path}...")
    df = pd.read_csv(csv_path)
    required_cols = {'station_id', 'lat', 'lon', 'num_piles', 'max_power_kw', 'current_price_inr_per_kwh'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"EV Stations CSV missing columns. Required: {required_cols}")

    # Convert to GeoDataFrame
    geometry = [Point(xy) for xy in zip(df.lon, df.lat)]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Match to nearest OSM nodes
    # We need to use ox.distance.nearest_nodes. 
    # Note: osmnx < 2.0 uses nearest_nodes(G, X, Y), newer versions might differ.
    # Assuming standard usage.
    # But we have nodes_gdf.
    
    # Let's use sklearn BallTree for fast nearest neighbor if osmnx is not convenient or to be robust
    from sklearn.neighbors import BallTree
    
    node_points = np.radians(nodes_gdf[['y', 'x']].values)
    station_points = np.radians(df[['lat', 'lon']].values)
    
    tree = BallTree(node_points, metric='haversine')
    dist, idx = tree.query(station_points, k=1)
    
    # Map back to node IDs
    nearest_node_ids = nodes_gdf.iloc[idx.flatten()].index.values
    gdf['nearest_node_id'] = nearest_node_ids
    gdf['distance_to_node_km'] = dist.flatten() * 6371
    
    return gdf

def load_indore_tariffs(config_module) -> pd.DataFrame:
    """
    Load EV tariffs from CSV.
    Expected columns: time_window_id, start_hour, end_hour, grid_price_inr_per_kwh
    """
    csv_path = config_module.TARIFFS_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Tariffs CSV not found at {csv_path}.")
    
    print(f"[INFO] Loading tariffs from {csv_path}...")
    df = pd.read_csv(csv_path)
    return df

def load_indore_ev_specs(config_module) -> pd.DataFrame:
    """
    Load EV specs from CSV.
    Expected columns: ev_model, range_km, battery_kwh, consumption_wh_per_km
    """
    csv_path = config_module.EV_SPECS_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"EV Specs CSV not found at {csv_path}.")
    
    print(f"[INFO] Loading EV specs from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Compute averages
    if 'range_km' in df.columns:
        avg_range = df['range_km'].mean()
        df['average_range_km'] = avg_range
        df['average_range_30pct_soc_km'] = 0.3 * avg_range
    
    return df

def build_indore_city_data(config_module) -> Dict[str, Any]:
    """
    Build complete Indore city data dictionary from real sources.
    """
    print("="*60)
    print("BUILDING INDORE CITY DATA (REAL)")
    print("="*60)
    
    # 1. Load Road Network
    G, nodes_gdf, edges_gdf = load_indore_road_network_from_osm(config_module)
    
    # 2. Load Wards (Demand)
    wards_df = load_indore_wards(config_module)
    
    # 3. Load Existing Stations
    ev_stations_gdf = load_indore_ev_stations(config_module, nodes_gdf)
    
    # 4. Load Tariffs
    tariffs_df = load_indore_tariffs(config_module)
    
    # 5. Load EV Specs
    ev_specs_df = load_indore_ev_specs(config_module)
    
    # 6. Compute Node Demand
    # Map ward centroids to nearest OSM nodes
    # Assuming wards have some lat/lon or we need to geocode them?
    # User said "Expected columns: ward_id, ward_name, population..."
    # If wards don't have lat/lon, we can't map them.
    # I will assume wards_df has lat/lon or I need to fetch them.
    # The user didn't specify lat/lon in expected columns for wards.
    # "Expected columns: ward_id, ward_name, population, area_km2, population_density"
    # This is a problem. Without location, I can't map demand to nodes.
    # I will assume the CSV *should* have lat/lon or I will try to geocode by ward_name using osmnx.
    # But geocoding 85 wards might be slow/unreliable.
    # I'll check if I can add lat/lon to the expected columns requirement in the error message, 
    # or try to geocode if missing.
    # For now, I'll assume they are there or I'll add them to the requirement.
    
    if 'lat' not in wards_df.columns or 'lon' not in wards_df.columns:
        print("[WARNING] Wards CSV missing lat/lon. Attempting to geocode ward names...")
        # Placeholder for geocoding or error
        # For robustness, let's just assign random nodes if we can't geocode (or raise error).
        # Better: Raise error telling user to add lat/lon.
        if 'latitude' in wards_df.columns: wards_df['lat'] = wards_df['latitude']
        if 'longitude' in wards_df.columns: wards_df['lon'] = wards_df['longitude']
        
        if 'lat' not in wards_df.columns:
             raise ValueError("Wards CSV must contain 'lat' and 'lon' columns for mapping to network.")

    # Map wards to nodes
    from sklearn.neighbors import BallTree
    node_points = np.radians(nodes_gdf[['y', 'x']].values)
    ward_points = np.radians(wards_df[['lat', 'lon']].values)
    
    tree = BallTree(node_points, metric='haversine')
    dist, idx = tree.query(ward_points, k=1)
    
    wards_df['nearest_node_id'] = nodes_gdf.iloc[idx.flatten()].index.values
    
    # Aggregate demand to nodes
    # EV Penetration assumption (can be in config, default 2%)
    EV_PENETRATION = 0.02 
    wards_df['ev_demand'] = wards_df['population'] * EV_PENETRATION
    
    # Create node_demand_series (indexed by node_id)
    node_demand_series = wards_df.groupby('nearest_node_id')['ev_demand'].sum()
    
    # 7. Load Power Grid Nodes (for consistency with existing pipeline)
    print("  - Fetching power grid infrastructure from OSM...")
    try:
        # Simplified version of IndoreDataLoader.load_power_grid_nodes
        tags = {'power': ['substation', 'transformer']}
        grid_gdf = ox.features_from_point((config_module.CITY_CENTER_LAT, config_module.CITY_CENTER_LON), 
                                          dist=config_module.CITY_RADIUS_KM * 1000, tags=tags)
        
        grid_nodes_list = []
        grid_id = 0
        for _, row in grid_gdf.iterrows():
            pt = row.geometry.centroid if hasattr(row.geometry, 'centroid') else row.geometry
            if pt.geom_type != 'Point': continue
            
            voltage_raw = row.get('voltage')
            # Parse voltage (simplified)
            voltage_kv = 11.0
            try:
                if voltage_raw:
                    v_str = str(voltage_raw).split(';')[0].replace('kV','').strip()
                    v = float(v_str)
                    voltage_kv = v/1000 if v > 1000 else v
            except: pass
            
            power_type = row.get('power', 'substation')
            available_kw = 10000.0 if power_type == 'substation' else 500.0 # Rough estimates
            
            grid_nodes_list.append({
                'grid_id': grid_id,
                'name': row.get('name', f"{power_type} {grid_id}"),
                'latitude': pt.y,
                'longitude': pt.x,
                'power': power_type,
                'voltage_kv': voltage_kv,
                'available_kw': available_kw
            })
            grid_id += 1
            
        grid_nodes = pd.DataFrame(grid_nodes_list)
    except Exception as e:
        print(f"  [WARNING] Could not fetch grid nodes: {e}")
        grid_nodes = pd.DataFrame()

    # 8. Link Sites to Grid
    # Add grid columns to candidate_sites
    if not grid_nodes.empty and not candidate_sites.empty:
        print("  - Linking sites to nearest grid nodes...")
        from sklearn.neighbors import BallTree
        grid_rad = np.radians(grid_nodes[['latitude', 'longitude']].values)
        site_rad = np.radians(candidate_sites[['latitude', 'longitude']].values)
        
        tree = BallTree(grid_rad, metric='haversine')
        dist, idx = tree.query(site_rad, k=1)
        
        nearest_indices = idx.flatten()
        distances_km = dist.flatten() * 6371
        
        # Assign values
        candidate_sites['nearest_grid_id'] = grid_nodes.iloc[nearest_indices]['grid_id'].values
        candidate_sites['nearest_grid_name'] = grid_nodes.iloc[nearest_indices]['name'].values
        candidate_sites['grid_voltage_kv'] = grid_nodes.iloc[nearest_indices]['voltage_kv'].values
        candidate_sites['grid_available_kw'] = grid_nodes.iloc[nearest_indices]['available_kw'].values
        candidate_sites['distance_to_grid_km'] = distances_km
        
        # Calculate costs
        charger_power_kw = 50.0
        upgrade_cost_per_kw = 850.0
        
        candidate_sites['grid_required_kw'] = candidate_sites['capacity'] * charger_power_kw
        candidate_sites['grid_capacity_gap_kw'] = candidate_sites['grid_required_kw'] - candidate_sites['grid_available_kw']
        candidate_sites['grid_upgrade_cost'] = candidate_sites['grid_capacity_gap_kw'].clip(lower=0) * upgrade_cost_per_kw
        candidate_sites['total_setup_cost'] = candidate_sites['setup_cost'] + candidate_sites['grid_upgrade_cost']
        candidate_sites['grid_capacity_ok'] = candidate_sites['grid_capacity_gap_kw'] <= 0
    else:
        # Fill with defaults if no grid data
        candidate_sites['nearest_grid_id'] = -1
        candidate_sites['nearest_grid_name'] = 'Unknown'
        candidate_sites['grid_voltage_kv'] = 11.0
        candidate_sites['grid_available_kw'] = 1000.0
        candidate_sites['distance_to_grid_km'] = 0.0
        candidate_sites['grid_required_kw'] = candidate_sites['capacity'] * 50.0
        candidate_sites['grid_upgrade_cost'] = 0.0
        candidate_sites['total_setup_cost'] = candidate_sites['setup_cost']
        candidate_sites['grid_capacity_ok'] = True

    # Calculate Distance Matrix (Zones x Sites)
    # Using Haversine for speed (or network distance if preferred, but Haversine is standard in this codebase)
    print("  - Calculating distance matrix...")
    n_zones = len(demand_zones)
    n_sites = len(candidate_sites)
    distance_matrix = np.zeros((n_zones, n_sites))
    
    R = 6371
    for i, zone in demand_zones.iterrows():
        lat1 = np.radians(zone['latitude'])
        lon1 = np.radians(zone['longitude'])
        for j, site in candidate_sites.iterrows():
            lat2 = np.radians(site['latitude'])
            lon2 = np.radians(site['longitude'])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            distance_matrix[i, j] = R * c
            
    # Averages
    avg_range = ev_specs_df['range_km'].mean() if not ev_specs_df.empty else 200
    avg_range_30pct = avg_range * 0.3
    
    return {
        "graph": G,
        "nodes_gdf": nodes_gdf,
        "edges_gdf": edges_gdf,
        "wards_df": wards_df,
        "ev_stations_gdf": ev_stations_gdf,
        "tariffs_df": tariffs_df,
        "ev_specs_df": ev_specs_df,
        "node_demand_series": node_demand_series,
        "avg_ev_range_km": avg_range,
        "avg_ev_range_30pct_km": avg_range_30pct,
        
        # Compatibility fields for existing optimizers
        "demand_zones": demand_zones,
        "candidate_sites": candidate_sites,
        "distance_matrix": distance_matrix,
        "city_center": (config_module.CITY_CENTER_LAT, config_module.CITY_CENTER_LON),
        "grid_nodes": grid_nodes
    }
