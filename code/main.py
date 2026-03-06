

import numpy as np
import pandas as pd
from data_loader import IndoreDataLoader
from hybrid_optimizer import HybridOptimizer
from visualization import EVCSVisualizer
from site_metrics_calculator import calculate_site_metrics
import warnings
warnings.filterwarnings('ignore')


def main():
    """
    Main execution function for EVCS optimization simulation.
    """
    print("="*60)
    print("EV CHARGING STATION OPTIMIZATION - INDORE CITY")
    print("Hybrid Approach: Benders Decomposition + NSGA-II")
    print("="*60)
    
    # ====================================================================
    # STEP 1: Load Data
    # ====================================================================
    print("\n[STEP 1] Loading Indore city data...")
    data_loader = IndoreDataLoader(
        city_center_lat=22.7196,
        city_center_lon=75.8577,
        city_radius_km=15.0
    )
    
    # Load all real data from OpenStreetMap and real sources
    data = data_loader.load_all_data()
    
    print(f"\nData Summary:")
    print(f"  - Demand zones: {len(data['demand_zones'])}")
    print(f"  - Candidate sites: {len(data['candidate_sites'])}")
    print(f"  - Total demand: {data['demand_zones']['demand'].sum():.2f} EVs")
    print(f"  - Distance matrix shape: {data['distance_matrix'].shape}")
    
    # ====================================================================
    # STEP 2: Run Hybrid Optimization (NSGA-II + Benders)
    # ====================================================================
    print("\n[STEP 2] Running hybrid optimization...")
    optimizer = HybridOptimizer(
        data=data,
        nsga2_generations=150,
        benders_iterations=30
    )
    
    solution_result = optimizer.solve()
    best_solution = solution_result['best_solution']
    convergence_history = solution_result.get('convergence_history', [])
    
    # ====================================================================
    # STEP 3: Visualize Results
    # ====================================================================
    print("\n[STEP 3] Creating visualizations...")
    visualizer = EVCSVisualizer(data)
    
    # Create static map with labels
    map_obj = visualizer.create_static_map(
        solution=best_solution,
        output_path="evcs_map.png"
    )
    
    # Create Pareto front plot
    if len(solution_result['pareto_solutions']) > 1:
        visualizer.plot_objectives(
            solutions=solution_result['pareto_solutions'],
            output_path="objectives_tradeoff.png"
        )
    
    # Create solution summary
    visualizer.plot_solution_summary(
        solution=best_solution,
        output_path="solution_summary.png"
    )
    
    # Create convergence graph
    if 'convergence_history' in solution_result and solution_result['convergence_history']:
        visualizer.plot_convergence(
            convergence_history=solution_result['convergence_history'],
            output_path="convergence_graph.png"
        )
    
    # ====================================================================
    # STEP 4: Output Results
    # ====================================================================
    print("\n[STEP 4] Generating output files...")
    
    # Save solution to CSV with all metrics
    selected_indices = np.where(best_solution['selected_sites'] == 1)[0]
    
    # Calculate metrics for each site using centralized calculator
    distance_matrix = data['distance_matrix']
    prices = best_solution.get('prices', np.ones(len(best_solution['selected_sites'])) * 10.0)
    
    solution_rows = []
    for j in selected_indices:
        # Use centralized calculator for consistency
        metrics = calculate_site_metrics(
            site_idx=j,
            selected_sites=best_solution['selected_sites'],
            candidate_sites=data['candidate_sites'],
            demand_zones=data['demand_zones'],
            distance_matrix=distance_matrix,
            prices=prices
        )
        
        solution_rows.append({
            'site_id': metrics['site_id'],
            'location_name': metrics['location_name'],
            'latitude': metrics['latitude'],
            'longitude': metrics['longitude'],
            'demand_category': metrics['demand_category'],
            'coverage_evs': round(metrics['coverage'], 2),
            'density_per_km2': round(metrics['density'], 4),
            'annual_profit_inr': round(metrics['annual_profit'], 2),
            'price_per_kwh_inr': round(metrics['price'], 2),
            'capacity_charging_points': metrics['capacity'],
            'setup_cost_inr': metrics['setup_cost'],
            'grid_upgrade_cost_inr': metrics['grid_upgrade_cost'],
            'total_setup_cost_inr': metrics['total_setup_cost'],
            'nearest_grid_id': metrics['nearest_grid_id'],
            'nearest_grid_name': metrics['nearest_grid_name'],
            'grid_voltage_kv': metrics['grid_voltage_kv'],
            'grid_available_kw': metrics['grid_available_kw'],
            'grid_required_kw': metrics['grid_required_kw'],
            'grid_capacity_gap_kw': metrics['grid_capacity_gap_kw'],
            'distance_to_grid_km': metrics['distance_to_grid_km'],
            'grid_capacity_ok': metrics['grid_capacity_ok'],
            'site_type': metrics['site_type']
        })
        # Attach queue metrics (if available) to CSV row for reporting
        queue = metrics.get('queue', {})
        solution_rows[-1].update({
            'queue_arrival_rate_per_hour': queue.get('arrival_rate_per_hour', 0.0),
            'queue_service_rate_per_charger_per_hour': queue.get('service_rate_per_charger_per_hour', 0.0),
            'queue_chargers': queue.get('chargers', int(metrics.get('capacity', 1))),
            'queue_station_capacity_K': queue.get('station_capacity_K', None),
            'avg_charging_time_min': queue.get('avg_charging_time_min', None),
            'avg_wait_time_min': queue.get('avg_wait_time_min', None),
            'avg_time_in_station_min': queue.get('avg_time_in_station_min', None),
            'queue_Lq': queue.get('Lq', None),
            'queue_L': queue.get('L', None),
            'queue_P0': queue.get('P0', None),
            'queue_P_block': queue.get('P_block', 0.0),
            'queue_utilization': queue.get('utilization', None)
        })
    
    solution_df = pd.DataFrame(solution_rows)
    solution_df.to_csv('optimal_solution.csv', index=False)
    print("[OK] Solution saved to optimal_solution.csv with all metrics")
    
    if convergence_history:
        convergence_df = pd.DataFrame(convergence_history)
        convergence_df.to_csv('fitness_log.csv', index=False)  # Renamed as requested
        print("[OK] Generation fitness log saved to fitness_log.csv")

    total_upgrade_cost = solution_df['grid_upgrade_cost_inr'].sum() if 'grid_upgrade_cost_inr' in solution_df.columns else 0.0
    upgrade_site_count = int((solution_df['grid_capacity_ok'] == False).sum()) if 'grid_capacity_ok' in solution_df.columns else 0
    avg_grid_distance = solution_df['distance_to_grid_km'].mean() if 'distance_to_grid_km' in solution_df.columns else float('nan')
    
    # Create HTML report
    try:
        from create_html_report import create_html_report
        create_html_report('optimal_solution.csv', 'evcs_report.html')
    except Exception as e:
        print(f"Warning: Could not create HTML report: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("SOLUTION SUMMARY")
    print("="*60)
    print(f"\nSelected Charging Stations: {best_solution['n_sites']}")
    total_cost_crore = best_solution['cost'] / 1e7
    upgrade_cost_lakh = total_upgrade_cost / 1e5
    expected_revenue_lakh = best_solution['revenue'] / 1e5
    expected_profit_lakh = best_solution['profit'] / 1e5
    
    print(f"\nFinancial Metrics:")
    print(f"  Total Setup Cost: {total_cost_crore:.2f} Cr INR")
    print(f"  Grid Upgrade Cost: {upgrade_cost_lakh:.2f} Lakh INR")
    print(f"  Sites Needing Upgrades: {upgrade_site_count}")
    print(f"  Expected Revenue: {expected_revenue_lakh:.2f} Lakh INR")
    print(f"  Expected Profit: {expected_profit_lakh:.2f} Lakh INR")
    print(f"  ROI: {(best_solution['profit'] / best_solution['cost'] * 100):.2f}%")
    
    print(f"\nCoverage Metrics:")
    print(f"  Demand Covered: {best_solution['coverage']:.2f} EVs")
    print(f"  Average Distance: {best_solution['avg_distance']:.2f} km")
    if not np.isnan(avg_grid_distance):
        print(f"  Avg Distance to Grid: {avg_grid_distance:.2f} km")
    
    total_demand = data['demand_zones']['demand'].sum()
    coverage_pct = (best_solution['coverage'] / total_demand) * 100
    print(f"  Coverage Percentage: {coverage_pct:.2f}%")
    
    print(f"\nPricing:")
    selected_prices = [best_solution['prices'][j] for j in selected_indices 
                      if j < len(best_solution['prices'])]
    if selected_prices:
        print(f"  Average Price: {np.mean(selected_prices):.2f} INR/kWh")
        print(f"  Price Range: {np.min(selected_prices):.2f} - {np.max(selected_prices):.2f} INR/kWh")
    
    print("\n" + "="*60)
    print("OPTIMIZATION COMPLETE!")
    print("="*60)
    print("\n" + "="*60)
    print("FINAL RESULT SUMMARY")
    print("="*60)
    print(f"Final Best Solution: {best_solution['n_sites']} sites selected")
    print(f"Final Best Fitness (Profit): {best_solution['profit']:.2f} INR")
    print(f"Total Generations: 150")
    
    print("\nOutput files generated:")
    print("  - evcs_map.png (static map with labeled stations)")
    print("  - objectives_tradeoff.png (Pareto front)")
    print("  - solution_summary.png (solution metrics)")
    print("  - convergence_graph.png (optimization history)")
    print("  - optimal_solution.csv (selected sites)")
    print("\nView evcs_map.png to see the optimized charging station locations!")


if __name__ == "__main__":
    main()

