
from data_loader import IndoreDataLoader
import numpy as np

dl = IndoreDataLoader()
data = dl.load_all_data()

demand_zones = data['demand_zones']
candidate_sites = data['candidate_sites']
distance_matrix = data['distance_matrix']

# Check max possible coverage
max_coverage = 0
unreachable_demand = 0

for i, zone in demand_zones.iterrows():
    # Find min distance to ANY candidate site
    min_dist = np.min(distance_matrix[i, :])
    
    if min_dist <= 5.0:
        max_coverage += zone['demand']
    else:
        unreachable_demand += zone['demand']

print(f"Total Demand: {demand_zones['demand'].sum():.2f}")
print(f"Max Possible Coverage: {max_coverage:.2f}")
print(f"Unreachable Demand: {unreachable_demand:.2f}")

# Check if 60 random sites usually cover everything
print("\nChecking random 60-site selections...")
for _ in range(5):
    indices = np.random.choice(len(candidate_sites), 60, replace=False)
    current_coverage = 0
    for i, zone in demand_zones.iterrows():
        # Check if covered by ANY of the selected 60
        min_dist = np.min(distance_matrix[i, indices])
        if min_dist <= 5.0:
            current_coverage += zone['demand']
    print(f"Random selection coverage: {current_coverage:.2f}")
