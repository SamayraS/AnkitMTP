
# Configuration for EVCS Optimization Project

# Data Source Configuration
# If True, use real data from CSV files and OpenStreetMap
# If False, use synthetic/hybrid data generation (existing behavior)
USE_REAL_DATA = True

# Directory for real data files
REAL_DATA_DIR = "data_real"

# Paths to real data CSV files
# User must provide these files in the REAL_DATA_DIR
WARDS_CSV = f"{REAL_DATA_DIR}/indore_wards.csv"
EV_STATIONS_CSV = f"{REAL_DATA_DIR}/indore_ev_stations.csv"
TARIFFS_CSV = f"{REAL_DATA_DIR}/indore_ev_tariffs.csv"
EV_SPECS_CSV = f"{REAL_DATA_DIR}/ev_specs_india.csv"

# City Parameters (Indore)
CITY_CENTER_LAT = 22.7196
CITY_CENTER_LON = 75.8577
CITY_RADIUS_KM = 15.0

# Optimization Parameters
NSGA2_GENERATIONS = 150
BENDERS_ITERATIONS = 30
