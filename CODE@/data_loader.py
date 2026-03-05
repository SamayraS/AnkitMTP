

import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon
from typing import Tuple, Dict, List
import osmnx as ox
from sklearn.neighbors import BallTree
import warnings
warnings.filterwarnings('ignore')

# Configure OSMnx
ox.settings.use_cache = True
ox.settings.log_console = False


class IndoreDataLoader:
    """
    Loads and preprocesses Indore city data for EVCS optimization.
    
    This class handles:
    - Geographic boundaries and coordinates
    - Population density data
    - Road network information
    - Potential charging station candidate sites
    - Demand zones
    """
    
    def __init__(self, city_center_lat: float = 22.7196, 
                 city_center_lon: float = 75.8577,
                 city_radius_km: float = 15.0):
        """
        Initialize data loader with Indore city parameters.
        
        Parameters:
        -----------
        city_center_lat : float
            Latitude of Indore city center (default: 22.7196)
        city_center_lon : float
            Longitude of Indore city center (default: 75.8577)
        city_radius_km : float
            Radius of city area to consider in kilometers (default: 15.0)
        """
        self.city_center_lat = city_center_lat
        self.city_center_lon = city_center_lon
        self.city_radius_km = city_radius_km
        
        # Data storage
        self.demand_zones = None
        self.candidate_sites = None
        self.grid_nodes = None
        self.road_network = None
        self.population_data = None
        
        # Power grid parameters
        self.charger_power_kw = 50.0  # Assumed draw per charging connector
        self.grid_upgrade_cost_per_kw = 850.0  # INR per kW for distribution upgrades
        
    def load_real_demand_zones(self) -> pd.DataFrame:
        """
        Load real demand zones from OpenStreetMap data for Indore.
        
        Uses OSM to get residential areas, neighborhoods, and commercial zones
        as demand zones with real geographic locations.
        
        Returns:
        --------
        pd.DataFrame
            DataFrame with columns: zone_id, latitude, longitude, population, 
            ev_density, avg_income, demand
        """
        print("  - Fetching real demand zones from OpenStreetMap...")
        
        try:
            # Get city boundary
            city_boundary = ox.geocode_to_gdf("Indore, Madhya Pradesh, India")
            
            # Get residential and commercial areas from OSM
            tags = {
                'place': ['neighbourhood', 'suburb', 'town'],
                'landuse': ['residential', 'commercial', 'retail'],
                'amenity': ['residential']
            }
            
            zones = []
            zone_id = 0
            
            # Get residential areas
            try:
                gdf_residential = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'landuse': 'residential'}
                )
                
                for idx, row in gdf_residential.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        
                        # Estimate population based on area (if available)
                        area_km2 = row.geometry.area / 1e6 if hasattr(row.geometry, 'area') else 0.5
                        # Indore average population density: ~5000 per km²
                        population = int(area_km2 * 5000) if area_km2 > 0 else np.random.randint(1000, 5000)
                        
                        # EV density varies by area type (residential: 0.02-0.04)
                        ev_density = np.random.uniform(0.02, 0.04)
                        avg_income = np.random.uniform(40000, 120000)
                        
                        zones.append({
                            'zone_id': zone_id,
                            'latitude': lat,
                            'longitude': lon,
                            'population': population,
                            'ev_density': ev_density,
                            'avg_income': avg_income,
                            'demand': population * ev_density,
                            'area_km2': area_km2
                        })
                        zone_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch residential areas: {e}")
            
            # Get commercial areas
            try:
                gdf_commercial = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'landuse': 'commercial'}
                )
                
                for idx, row in gdf_commercial.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        
                        area_km2 = row.geometry.area / 1e6 if hasattr(row.geometry, 'area') else 0.2
                        # Commercial areas have higher daytime population
                        population = int(area_km2 * 8000) if area_km2 > 0 else np.random.randint(2000, 8000)
                        
                        # Commercial areas have higher EV density
                        ev_density = np.random.uniform(0.03, 0.06)
                        avg_income = np.random.uniform(60000, 200000)
                        
                        zones.append({
                            'zone_id': zone_id,
                            'latitude': lat,
                            'longitude': lon,
                            'population': population,
                            'ev_density': ev_density,
                            'avg_income': avg_income,
                            'demand': population * ev_density,
                            'area_km2': area_km2
                        })
                        zone_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch commercial areas: {e}")
            
            # If we don't have enough zones, add real Indore neighborhoods
            if len(zones) < 20:
                print("  - Adding known Indore neighborhoods...")
                # Real Indore neighborhoods with actual coordinates
                indore_neighborhoods = [
                    {"name": "Vijay Nagar", "lat": 22.7486, "lon": 75.8889, "pop": 45000},
                    {"name": "New Palasia", "lat": 22.7281, "lon": 75.8681, "pop": 35000},
                    {"name": "Sapna Sangeeta", "lat": 22.7350, "lon": 75.8750, "pop": 30000},
                    {"name": "Bhawarkua", "lat": 22.7100, "lon": 75.8500, "pop": 40000},
                    {"name": "Rau", "lat": 22.6800, "lon": 75.8200, "pop": 25000},
                    {"name": "Aerodrome", "lat": 22.7200, "lon": 75.8000, "pop": 20000},
                    {"name": "Rajendra Nagar", "lat": 22.7400, "lon": 75.9000, "pop": 28000},
                    {"name": "Sudama Nagar", "lat": 22.7150, "lon": 75.8700, "pop": 22000},
                    {"name": "Tilak Nagar", "lat": 22.7250, "lon": 75.8600, "pop": 18000},
                    {"name": "Gandhi Nagar", "lat": 22.7300, "lon": 75.8550, "pop": 15000},
                    {"name": "MG Road", "lat": 22.7180, "lon": 75.8570, "pop": 50000},
                    {"name": "MR 10", "lat": 22.7000, "lon": 75.8800, "pop": 32000},
                    {"name": "LIG Colony", "lat": 22.7500, "lon": 75.8750, "pop": 25000},
                    {"name": "Scheme 54", "lat": 22.7100, "lon": 75.8900, "pop": 20000},
                    {"name": "Nipania", "lat": 22.6900, "lon": 75.8400, "pop": 18000},
                ]
                
                for nh in indore_neighborhoods:
                    if zone_id >= len(zones) or nh['name'] not in [z.get('name', '') for z in zones]:
                        ev_density = np.random.uniform(0.02, 0.04)
                        zones.append({
                            'zone_id': zone_id,
                            'latitude': nh['lat'],
                            'longitude': nh['lon'],
                            'population': nh['pop'],
                            'ev_density': ev_density,
                            'avg_income': np.random.uniform(40000, 150000),
                            'demand': nh['pop'] * ev_density,
                            'area_km2': nh['pop'] / 5000,
                            'name': nh['name']
                        })
                        zone_id += 1
            
            if len(zones) == 0:
                raise ValueError("No zones loaded from OSM")
            
            self.demand_zones = pd.DataFrame(zones)
            print(f"    [OK] Loaded {len(self.demand_zones)} real demand zones")
            return self.demand_zones
            
        except Exception as e:
            print(f"    Error loading from OSM: {e}")
            print("    Falling back to real Indore neighborhoods...")
            return self._load_indore_neighborhoods()
    
    def _load_indore_neighborhoods(self) -> pd.DataFrame:
        """Load real Indore neighborhoods as demand zones."""
        # Real Indore neighborhoods with actual coordinates and estimated populations
        indore_neighborhoods = [
            {"name": "Vijay Nagar", "lat": 22.7486, "lon": 75.8889, "pop": 45000, "income": 120000},
            {"name": "New Palasia", "lat": 22.7281, "lon": 75.8681, "pop": 35000, "income": 100000},
            {"name": "Sapna Sangeeta", "lat": 22.7350, "lon": 75.8750, "pop": 30000, "income": 110000},
            {"name": "Bhawarkua", "lat": 22.7100, "lon": 75.8500, "pop": 40000, "income": 95000},
            {"name": "Rau", "lat": 22.6800, "lon": 75.8200, "pop": 25000, "income": 80000},
            {"name": "Aerodrome", "lat": 22.7200, "lon": 75.8000, "pop": 20000, "income": 90000},
            {"name": "Rajendra Nagar", "lat": 22.7400, "lon": 75.9000, "pop": 28000, "income": 85000},
            {"name": "Sudama Nagar", "lat": 22.7150, "lon": 75.8700, "pop": 22000, "income": 75000},
            {"name": "Tilak Nagar", "lat": 22.7250, "lon": 75.8600, "pop": 18000, "income": 70000},
            {"name": "Gandhi Nagar", "lat": 22.7300, "lon": 75.8550, "pop": 15000, "income": 65000},
            {"name": "MG Road", "lat": 22.7180, "lon": 75.8570, "pop": 50000, "income": 150000},
            {"name": "MR 10", "lat": 22.7000, "lon": 75.8800, "pop": 32000, "income": 90000},
            {"name": "LIG Colony", "lat": 22.7500, "lon": 75.8750, "pop": 25000, "income": 60000},
            {"name": "Scheme 54", "lat": 22.7100, "lon": 75.8900, "pop": 20000, "income": 70000},
            {"name": "Nipania", "lat": 22.6900, "lon": 75.8400, "pop": 18000, "income": 65000},
            {"name": "Tukoganj", "lat": 22.7200, "lon": 75.8600, "pop": 15000, "income": 80000},
            {"name": "Chhatripura", "lat": 22.7150, "lon": 75.8550, "pop": 12000, "income": 75000},
            {"name": "Banganga", "lat": 22.7300, "lon": 75.8800, "pop": 22000, "income": 85000},
            {"name": "Lasudia", "lat": 22.6800, "lon": 75.8600, "pop": 18000, "income": 70000},
            {"name": "Pardeshipura", "lat": 22.7250, "lon": 75.8500, "pop": 16000, "income": 75000},
            {"name": "Gomatgiri", "lat": 22.7500, "lon": 75.8600, "pop": 14000, "income": 90000},
            {"name": "Khandwa Road", "lat": 22.7050, "lon": 75.8700, "pop": 20000, "income": 80000},
            {"name": "Bicholi Mardana", "lat": 22.7400, "lon": 75.8200, "pop": 12000, "income": 65000},
            {"name": "Ralamandal", "lat": 22.7600, "lon": 75.9000, "pop": 10000, "income": 110000},
            {"name": "Super Corridor", "lat": 22.7000, "lon": 75.9000, "pop": 15000, "income": 130000},
        ]
        
        zones = []
        for i, nh in enumerate(indore_neighborhoods):
            ev_density = np.random.uniform(0.02, 0.05)  # 2-5% EV adoption
            zones.append({
                'zone_id': i,
                'latitude': nh['lat'],
                'longitude': nh['lon'],
                'population': nh['pop'],
                'ev_density': ev_density,
                'avg_income': nh['income'],
                'demand': nh['pop'] * ev_density,
                'name': nh['name']
            })
        
        self.demand_zones = pd.DataFrame(zones)
        return self.demand_zones
    
    def load_real_candidate_sites(self) -> pd.DataFrame:
        """
        Load real candidate sites from OpenStreetMap for Indore.
        
        Uses OSM to find suitable locations like:
        - Parking areas
        - Shopping malls
        - Fuel stations (can be converted)
        - Commercial complexes
        
        Returns:
        --------
        pd.DataFrame
            DataFrame with columns: site_id, latitude, longitude, 
            land_cost, capacity, setup_cost, max_price, site_type
        """
        print("  - Fetching real candidate sites from OpenStreetMap...")
        
        sites = []
        site_id = 0
        
        try:
            # Get parking areas
            try:
                gdf_parking = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'amenity': 'parking'}
                )
                
                for idx, row in gdf_parking.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        
                        # Distance from city center
                        dist = self._haversine(self.city_center_lat, self.city_center_lon, lat, lon)
                        if dist <= self.city_radius_km:
                            capacity = np.random.choice([4, 8, 12, 16], p=[0.2, 0.4, 0.3, 0.1])
                            land_cost = 800000 + dist * 50000  # Higher cost near center
                            setup_cost = land_cost + capacity * 500000
                            
                            sites.append({
                                'site_id': site_id,
                                'latitude': lat,
                                'longitude': lon,
                                'land_cost': land_cost,
                                'capacity': capacity,
                                'setup_cost': setup_cost,
                                'max_price': np.random.uniform(8, 14),
                                'site_type': 'parking'
                            })
                            site_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch parking areas: {e}")
            
            # Get shopping malls and commercial complexes
            try:
                gdf_malls = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'shop': 'mall', 'amenity': 'marketplace'}
                )
                
                for idx, row in gdf_malls.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        
                        dist = self._haversine(self.city_center_lat, self.city_center_lon, lat, lon)
                        if dist <= self.city_radius_km:
                            capacity = np.random.choice([8, 12, 16], p=[0.3, 0.5, 0.2])
                            land_cost = 1200000 + dist * 40000
                            setup_cost = land_cost + capacity * 500000
                            
                            sites.append({
                                'site_id': site_id,
                                'latitude': lat,
                                'longitude': lon,
                                'land_cost': land_cost,
                                'capacity': capacity,
                                'setup_cost': setup_cost,
                                'max_price': np.random.uniform(10, 15),
                                'site_type': 'mall'
                            })
                            site_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch malls: {e}")
            
            # Get fuel stations (good candidates for EVCS conversion)
            # Get restaurants (new candidate type - good for destination charging)
            try:
                gdf_restaurants = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'amenity': 'restaurant'}
                )
                if len(gdf_restaurants) > 80:
                    gdf_restaurants = gdf_restaurants.sample(80, random_state=42)
                for idx, row in gdf_restaurants.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        dist = self._haversine(self.city_center_lat, self.city_center_lon, lat, lon)
                        if dist <= self.city_radius_km:
                            capacity = np.random.choice([4, 6, 8], p=[0.4, 0.4, 0.2])
                            land_cost = 900000 + dist * 35000
                            setup_cost = land_cost + capacity * 450000
                            sites.append({
                                'site_id': site_id,
                                'latitude': lat,
                                'longitude': lon,
                                'land_cost': land_cost,
                                'capacity': capacity,
                                'setup_cost': setup_cost,
                                'max_price': np.random.uniform(9, 13),
                                'site_type': 'restaurant',
                                'name': row.get('name', 'Restaurant Site')
                            })
                            site_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch restaurants: {e}")

            try:
                gdf_fuel = ox.features_from_place(
                    "Indore, Madhya Pradesh, India",
                    tags={'amenity': 'fuel'}
                )
                
                for idx, row in gdf_fuel.iterrows():
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                        lat, lon = centroid.y, centroid.x
                        
                        dist = self._haversine(self.city_center_lat, self.city_center_lon, lat, lon)
                        if dist <= self.city_radius_km:
                            capacity = np.random.choice([4, 8, 12], p=[0.2, 0.5, 0.3])
                            land_cost = 1000000 + dist * 45000
                            setup_cost = land_cost + capacity * 450000  # Lower conversion cost
                            
                            sites.append({
                                'site_id': site_id,
                                'latitude': lat,
                                'longitude': lon,
                                'land_cost': land_cost,
                                'capacity': capacity,
                                'setup_cost': setup_cost,
                                'max_price': np.random.uniform(9, 13),
                                'site_type': 'fuel_station'
                            })
                            site_id += 1
            except Exception as e:
                print(f"    Warning: Could not fetch fuel stations: {e}")
            
        except Exception as e:
            print(f"    Error loading from OSM: {e}")
        
        # Add real Indore locations if we don't have enough
        if len(sites) < 20:
            print("  - Adding known Indore locations...")
            sites.extend(self._get_indore_real_locations(site_id))
        
        if len(sites) == 0:
            raise ValueError("No candidate sites loaded")
        
        self.candidate_sites = pd.DataFrame(sites)
        print(f"    [OK] Loaded {len(self.candidate_sites)} real candidate sites")
        return self.candidate_sites
    
    def _parse_voltage_value(self, voltage_raw) -> float:
        """Parse raw voltage values from OSM into representative kV."""
        if voltage_raw is None or (isinstance(voltage_raw, float) and np.isnan(voltage_raw)):
            return 11.0
        try:
            if isinstance(voltage_raw, (list, tuple)):
                values = voltage_raw
            else:
                values = str(voltage_raw).replace(',', ';').split(';')
            voltages = [float(v.strip()) for v in values if v.strip()]
            if not voltages:
                return 11.0
            voltages_kv = []
            for v in voltages:
                if v > 1000:
                    voltages_kv.append(v / 1000.0)
                else:
                    voltages_kv.append(v)
            return max(voltages_kv)
        except Exception:
            return 11.0
    
    def _estimate_available_kw(self, voltage_kv: float, power_type: str) -> float:
        """Estimate available capacity based on voltage level and asset type."""
        voltage_capacity_map = {
            400: 60000,
            220: 45000,
            132: 30000,
            110: 22000,
            66: 15000,
            55: 12000,
            44: 9000,
            33: 6200,
            22: 3500,
            16: 1500,
            13.8: 1000,
            11: 210,
            6.6: 150,
            3.3: 120
        }
        available_levels = np.array(list(voltage_capacity_map.keys()), dtype=float)
        idx = (np.abs(available_levels - voltage_kv)).argmin()
        base_capacity = voltage_capacity_map[available_levels[idx]]
        if power_type == 'substation':
            return base_capacity * 1.2
        if power_type == 'transformer':
            return base_capacity * 0.8
        return base_capacity
    
    def _fallback_grid_nodes(self) -> pd.DataFrame:
        """Fallback grid nodes for Indore when OSM data is sparse."""
        fallback_nodes = [
            {
                'name': 'Indore 33kV Substation',
                'latitude': 22.7196,
                'longitude': 75.8577,
                'power': 'substation',
                'voltage_kv': 33.0
            },
            {
                'name': 'Vijay Nagar 33kV Substation',
                'latitude': 22.7486,
                'longitude': 75.8889,
                'power': 'substation',
                'voltage_kv': 33.0
            },
            {
                'name': 'Rau 11kV Transformer',
                'latitude': 22.6800,
                'longitude': 75.8200,
                'power': 'transformer',
                'voltage_kv': 11.0
            },
            {
                'name': 'Bhawarkua 11kV Transformer',
                'latitude': 22.7100,
                'longitude': 75.8500,
                'power': 'transformer',
                'voltage_kv': 11.0
            },
            {
                'name': 'Super Corridor 22kV Substation',
                'latitude': 22.7000,
                'longitude': 75.9000,
                'power': 'substation',
                'voltage_kv': 22.0
            }
        ]
        for node in fallback_nodes:
            node['available_kw'] = self._estimate_available_kw(node['voltage_kv'], node['power'])
        df = pd.DataFrame(fallback_nodes)
        df['grid_id'] = np.arange(len(df))
        return df[['grid_id', 'name', 'latitude', 'longitude', 'power', 'voltage_kv', 'available_kw']]
    
    def load_power_grid_nodes(self) -> pd.DataFrame:
        """Download substations/transformers for Indore and estimate capacity."""
        print("  - Fetching power grid infrastructure from OpenStreetMap...")
        try:
            grid_gdf = ox.features_from_point(
                (self.city_center_lat, self.city_center_lon),
                dist=self.city_radius_km * 1000,
                tags={'power': ['substation', 'transformer']}
            )
            records = []
            grid_id = 0
            for _, row in grid_gdf.iterrows():
                geom = row.geometry
                if geom is None:
                    continue
                if geom.geom_type == 'Point':
                    point = geom
                else:
                    point = geom.centroid
                lat, lon = point.y, point.x
                power_type = row.get('power', 'substation')
                voltage_kv = self._parse_voltage_value(row.get('voltage'))
                available_kw = self._estimate_available_kw(voltage_kv, power_type)
                records.append({
                    'grid_id': grid_id,
                    'name': row.get('name', f"{power_type.title()} {grid_id}"),
                    'latitude': lat,
                    'longitude': lon,
                    'power': power_type,
                    'voltage_kv': voltage_kv,
                    'available_kw': available_kw
                })
                grid_id += 1
            if len(records) == 0:
                print("    Warning: No grid nodes found in OSM. Using fallback nodes.")
                self.grid_nodes = self._fallback_grid_nodes()
            else:
                self.grid_nodes = pd.DataFrame(records)
                self.grid_nodes['distance_to_center_km'] = self.grid_nodes.apply(
                    lambda r: self._haversine(self.city_center_lat, self.city_center_lon,
                                              r['latitude'], r['longitude']), axis=1)
                self.grid_nodes = self.grid_nodes[self.grid_nodes['distance_to_center_km'] <= self.city_radius_km * 1.2]
                self.grid_nodes.reset_index(drop=True, inplace=True)
                print(f"    [OK] Loaded {len(self.grid_nodes)} power grid nodes")
        except Exception as e:
            print(f"    Warning: Could not fetch grid infrastructure: {e}")
            print("    Falling back to predefined substations/transformers.")
            self.grid_nodes = self._fallback_grid_nodes()
        return self.grid_nodes
    
    def _get_indore_real_locations(self, start_id: int) -> List[Dict]:
        """Get real Indore locations suitable for EVCS."""
        # Real Indore locations: malls, major parking, commercial areas
        real_locations = [
            {"name": "C21 Mall", "lat": 22.7486, "lon": 75.8889, "type": "mall"},
            {"name": "Treasure Island", "lat": 22.7281, "lon": 75.8681, "type": "mall"},
            {"name": "Central Mall", "lat": 22.7350, "lon": 75.8750, "type": "mall"},
            {"name": "Sapna Sangeeta Mall", "lat": 22.7350, "lon": 75.8750, "type": "mall"},
            {"name": "MG Road Commercial", "lat": 22.7180, "lon": 75.8570, "type": "commercial"},
            {"name": "Vijay Nagar Square", "lat": 22.7486, "lon": 75.8889, "type": "parking"},
            {"name": "Palasia Square", "lat": 22.7281, "lon": 75.8681, "type": "parking"},
            {"name": "Regal Square", "lat": 22.7200, "lon": 75.8600, "type": "parking"},
            {"name": "Bhawarkua Square", "lat": 22.7100, "lon": 75.8500, "type": "parking"},
            {"name": "MR 10 Junction", "lat": 22.7000, "lon": 75.8800, "type": "parking"},
            {"name": "Airport Road", "lat": 22.7200, "lon": 75.8000, "type": "fuel_station"},
            {"name": "AB Road", "lat": 22.7000, "lon": 75.8700, "type": "fuel_station"},
            {"name": "Ring Road", "lat": 22.7300, "lon": 75.9000, "type": "fuel_station"},
            {"name": "Super Corridor", "lat": 22.7000, "lon": 75.9000, "type": "parking"},
            {"name": "Ralamandal", "lat": 22.7600, "lon": 75.9000, "type": "parking"},
            {"name": "56 Dukan Food Street", "lat": 22.7198, "lon": 75.8793, "type": "restaurant"},
            {"name": "Chappan Bhog Restaurant Hub", "lat": 22.7205, "lon": 75.8810, "type": "restaurant"},
            {"name": "Sayaji Hotel Complex", "lat": 22.7260, "lon": 75.8830, "type": "restaurant"},
            {"name": "Nakhrali Dhani", "lat": 22.6440, "lon": 75.8130, "type": "restaurant"}
        ]
        
        sites = []
        for i, loc in enumerate(real_locations):
            dist = self._haversine(self.city_center_lat, self.city_center_lon, 
                                  loc['lat'], loc['lon'])
            
            if loc['type'] == 'mall':
                capacity = np.random.choice([8, 12, 16], p=[0.3, 0.5, 0.2])
                land_cost = 1200000 + dist * 40000
                setup_cost = land_cost + capacity * 500000
                max_price = np.random.uniform(10, 15)
            elif loc['type'] == 'commercial':
                capacity = np.random.choice([4, 8, 12], p=[0.2, 0.5, 0.3])
                land_cost = 1000000 + dist * 45000
                setup_cost = land_cost + capacity * 500000
                max_price = np.random.uniform(9, 14)
            elif loc['type'] == 'fuel_station':
                capacity = np.random.choice([4, 8, 12], p=[0.2, 0.5, 0.3])
                land_cost = 1000000 + dist * 45000
                setup_cost = land_cost + capacity * 450000
                max_price = np.random.uniform(9, 13)
            elif loc['type'] == 'restaurant':
                capacity = np.random.choice([4, 6, 8], p=[0.4, 0.4, 0.2])
                land_cost = 900000 + dist * 35000
                setup_cost = land_cost + capacity * 450000
                max_price = np.random.uniform(9, 13)
            else:  # parking
                capacity = np.random.choice([4, 8, 12], p=[0.3, 0.5, 0.2])
                land_cost = 800000 + dist * 50000
                setup_cost = land_cost + capacity * 500000
                max_price = np.random.uniform(8, 13)
            
            sites.append({
                'site_id': start_id + i,
                'latitude': loc['lat'],
                'longitude': loc['lon'],
                'land_cost': land_cost,
                'capacity': capacity,
                'setup_cost': setup_cost,
                'max_price': max_price,
                'site_type': loc['type'],
                'name': loc['name']
            })
        
        return sites
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula."""
        R = 6371  # Earth radius in km
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        return R * c
    
    def calculate_distance_matrix(self) -> np.ndarray:
        """
        Calculate distance matrix between demand zones and candidate sites.
        
        Uses Haversine formula for great-circle distance.
        
        Returns:
        --------
        np.ndarray
            Distance matrix of shape (n_zones, n_sites) in kilometers
        """
        if self.demand_zones is None or self.candidate_sites is None:
            raise ValueError("Must generate demand zones and candidate sites first")
        
        n_zones = len(self.demand_zones)
        n_sites = len(self.candidate_sites)
        distance_matrix = np.zeros((n_zones, n_sites))
        
        # Haversine formula
        R = 6371  # Earth radius in km
        
        for i, zone in self.demand_zones.iterrows():
            lat1 = np.radians(zone['latitude'])
            lon1 = np.radians(zone['longitude'])
            
            for j, site in self.candidate_sites.iterrows():
                lat2 = np.radians(site['latitude'])
                lon2 = np.radians(site['longitude'])
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
                c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
                
                distance_matrix[i, j] = R * c
        
        return distance_matrix
    
    def load_all_data(self) -> Dict:
        """
        Load all required real data for optimization from OpenStreetMap and real sources.
        
        Returns:
        --------
        Dict
            Dictionary containing all loaded data
        """
        print("Loading real Indore city data...")
        
        # Load real demand zones
        self.load_real_demand_zones()
        
        # Load real candidate sites
        self.load_real_candidate_sites()
        
        # Load power grid nodes
        self.load_power_grid_nodes()

        # Link candidate sites to power grid infrastructure
        self.link_sites_to_grid()
        
        print("  - Calculating distance matrix...")
        distance_matrix = self.calculate_distance_matrix()
        
        data = {
            'demand_zones': self.demand_zones,
            'candidate_sites': self.candidate_sites,
            'distance_matrix': distance_matrix,
            'city_center': (self.city_center_lat, self.city_center_lon),
            'grid_nodes': self.grid_nodes
        }
        
        print("[OK] Real data loading complete!")
        return data

    def link_sites_to_grid(self):
        """Link candidate sites to nearest grid node and estimate upgrade cost."""
        if self.candidate_sites is None or self.candidate_sites.empty:
            raise ValueError("Candidate sites must be loaded before linking to grid nodes.")
        if self.grid_nodes is None or self.grid_nodes.empty:
            self.load_power_grid_nodes()
        grid_coords = np.radians(self.grid_nodes[['latitude', 'longitude']].values)
        site_coords = np.radians(self.candidate_sites[['latitude', 'longitude']].values)
        tree = BallTree(grid_coords, metric='haversine')
        distances, indices = tree.query(site_coords, k=1)
        distances_km = distances[:, 0] * 6371.0
        nearest_idx = indices[:, 0]
        grid_matches = self.grid_nodes.iloc[nearest_idx].reset_index(drop=True)
        required_kw = self.candidate_sites['capacity'].astype(float) * self.charger_power_kw
        available_kw = grid_matches['available_kw'].astype(float)
        upgrade_needed_kw = np.maximum(0, required_kw - available_kw)
        upgrade_cost = upgrade_needed_kw * self.grid_upgrade_cost_per_kw
        self.candidate_sites['nearest_grid_id'] = grid_matches['grid_id'].values
        self.candidate_sites['nearest_grid_name'] = grid_matches['name'].values
        self.candidate_sites['grid_voltage_kv'] = grid_matches['voltage_kv'].values
        self.candidate_sites['grid_available_kw'] = available_kw.values
        self.candidate_sites['distance_to_grid_km'] = distances_km
        self.candidate_sites['grid_required_kw'] = required_kw.values
        self.candidate_sites['grid_upgrade_cost'] = upgrade_cost.values
        self.candidate_sites['total_setup_cost'] = self.candidate_sites['setup_cost'] + self.candidate_sites['grid_upgrade_cost']
        self.candidate_sites['grid_capacity_gap_kw'] = available_kw.values - required_kw.values
        self.candidate_sites['grid_capacity_ok'] = (available_kw.values >= required_kw.values)
        numeric_cols = [
            'grid_voltage_kv', 'grid_available_kw', 'distance_to_grid_km',
            'grid_required_kw', 'grid_upgrade_cost', 'total_setup_cost',
            'grid_capacity_gap_kw'
        ]
        for col in numeric_cols:
            self.candidate_sites[col] = self.candidate_sites[col].astype(float)
        self.candidate_sites['grid_capacity_ok'] = self.candidate_sites['grid_capacity_ok'].astype(bool)
        print("    [OK] Linked candidate sites to nearest grid nodes")

