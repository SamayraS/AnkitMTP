"""
Visualization Module for EVCS Optimization Results

This module creates interactive maps and visualizations showing:
- Demand zones
- Candidate sites
- Selected charging stations
- Coverage areas
- Pricing information

Author: EVCS Optimization Team
Date: 2024
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from typing import Dict, List
from site_metrics_calculator import calculate_site_metrics
import warnings
warnings.filterwarnings('ignore')

# Try to import contextily for base maps
try:
    import contextily as ctx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False
    print("Note: contextily not available. Using simple coordinate plot.")


class EVCSVisualizer:
    """
    Creates visualizations for EVCS optimization results.
    """
    
    def __init__(self, data: Dict):
        """
        Initialize visualizer with data.
        
        Parameters:
        -----------
        data : Dict
            Dictionary containing demand_zones, candidate_sites, city_center
        """
        self.data = data
        self.demand_zones = data['demand_zones']
        self.candidate_sites = data['candidate_sites']
        self.city_center = data['city_center']
        
    def create_static_map(self, solution: Dict, output_path: str = "evcs_map.png"):
        """
        Create static matplotlib map showing optimization results with labels.
        
        Parameters:
        -----------
        solution : Dict
            Solution dictionary with selected_sites, prices, etc.
        output_path : str
            Path to save PNG map file
        """
        print(f"\nCreating static map with labels...")
        
        selected_sites = solution['selected_sites']
        # Ensure prices array matches selected_sites length
        if 'prices' in solution and len(solution['prices']) == len(selected_sites):
            prices = solution['prices']
        else:
            prices = np.ones(len(selected_sites)) * 10.0
        
        # Calculate metrics for each selected site
        selected_indices = np.where(selected_sites == 1)[0]
        distance_matrix = self.data['distance_matrix']
        
        # Verify distance matrix dimensions match
        n_zones = len(self.demand_zones)
        n_sites = len(self.candidate_sites)
        if distance_matrix.shape != (n_zones, n_sites):
            raise ValueError(f"Distance matrix shape {distance_matrix.shape} doesn't match "
                           f"expected ({n_zones}, {n_sites})")
        
        # Calculate coverage, profit, and density for each site using centralized calculator
        site_metrics = []
        for idx, j in enumerate(selected_indices):
            # Ensure j is within valid range
            if j >= n_sites:
                print(f"Warning: Site index {j} out of range (max: {n_sites-1})")
                continue
            
            # Use centralized calculator for consistency
            metrics = calculate_site_metrics(
                site_idx=j,
                selected_sites=selected_sites,
                candidate_sites=self.candidate_sites,
                demand_zones=self.demand_zones,
                distance_matrix=distance_matrix,
                prices=prices
            )
            
            site_metrics.append({
                'site_id': metrics['site_id'],
                'lat': metrics['latitude'],
                'lon': metrics['longitude'],
                'coverage': metrics['coverage'],
                'profit': metrics['annual_profit'],
                'density': metrics['density'],
                'price': metrics['price'],
                'capacity': metrics['capacity'],
                'min_distance': metrics['min_distance'],
                'demand_category': metrics['demand_category'],
                'location_name': metrics['location_name'],
                'grid_voltage_kv': metrics['grid_voltage_kv'],
                'grid_available_kw': metrics['grid_available_kw'],
                'grid_required_kw': metrics['grid_required_kw'],
                'grid_upgrade_cost': metrics['grid_upgrade_cost'],
                'grid_capacity_ok': metrics['grid_capacity_ok'],
                'distance_to_grid_km': metrics['distance_to_grid_km'],
                'nearest_grid_name': metrics['nearest_grid_name']
            })
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Set up coordinate bounds for Indore
        all_lats = [float(z['latitude']) for _, z in self.demand_zones.iterrows()]
        all_lons = [float(z['longitude']) for _, z in self.demand_zones.iterrows()]
        
        lat_margin = (max(all_lats) - min(all_lats)) * 0.1
        lon_margin = (max(all_lons) - min(all_lons)) * 0.1
        
        ax.set_xlim(min(all_lons) - lon_margin, max(all_lons) + lon_margin)
        ax.set_ylim(min(all_lats) - lat_margin, max(all_lats) + lat_margin)
        
        # Plot demand zones with density coloring
        for idx, zone in self.demand_zones.iterrows():
            demand = float(zone['demand'])
            lat = float(zone['latitude'])
            lon = float(zone['longitude'])
            
            # Color by demand density
            if demand > 2.0:
                color = '#ff4444'  # Red - high demand
                alpha = 0.6
                size = 30
            elif demand > 1.0:
                color = '#ff8844'  # Orange - medium demand
                alpha = 0.5
                size = 20
            else:
                color = '#ffdd44'  # Yellow - low demand
                alpha = 0.4
                size = 15
            
            ax.scatter(lon, lat, c=color, s=size, alpha=alpha, 
                      edgecolors='gray', linewidths=0.5, zorder=1)
        
        # Plot selected charging stations with labels (no color coding)
        for metric in site_metrics:
            lat, lon = metric['lat'], metric['lon']
            coverage = metric['coverage']
            profit = metric['profit']
            density = metric['density']
            price = metric['price']
            capacity = metric['capacity']
            site_id = metric['site_id']
            demand_category = metric['demand_category']
            location_name = metric['location_name']
            
            # Use neutral color for all markers (no profit-based coloring)
            marker_color = '#333333'  # Dark gray - neutral
            
            # Plot coverage circle (5km radius) - light gray
            radius_deg = 5.0 / 111.0
            circle = Circle((lon, lat), radius_deg, 
                         color='#cccccc', fill=True, alpha=0.1, 
                         edgecolor='#999999', linewidth=0.5, zorder=2)
            ax.add_patch(circle)
            
            # Plot station marker (size based on capacity) - neutral color
            marker_size = 80 + capacity * 15
            ax.scatter(lon, lat, c=marker_color, s=marker_size, 
                      edgecolors='black', linewidths=1.5, 
                      marker='s', zorder=3, alpha=0.7)
            
            # Add label with actual values (not expected), demand category, and location
            location_info = f"Loc: {location_name}" if location_name else f"Lat: {lat:.4f}, Lon: {lon:.4f}"
            
            grid_voltage = metric.get('grid_voltage_kv', np.nan)
            grid_available = metric.get('grid_available_kw', 0.0)
            grid_required = metric.get('grid_required_kw', 0.0)
            grid_upgrade = metric.get('grid_upgrade_cost', 0.0)
            grid_distance = metric.get('distance_to_grid_km', np.nan)
            grid_ok = metric.get('grid_capacity_ok', True)
            grid_name = metric.get('nearest_grid_name') or f"Grid {metric.get('nearest_grid_id', '-') }"
            voltage_text = f"{grid_voltage:.0f} kV" if not np.isnan(grid_voltage) else "N/A"
            distance_text = f"{grid_distance:.2f} km" if not np.isnan(grid_distance) else "N/A"
            upgrade_text = f"₹{grid_upgrade:.0f}" if grid_upgrade > 0 else "₹0"
            grid_status = "OK" if grid_ok else "Upgrade"
            grid_info = (
                f"{grid_name}\n"
                f"Grid: {voltage_text} | Avail: {grid_available:.0f} kW\n"
                f"Need: {grid_required:.0f} kW | Dist: {distance_text}\n"
                f"Upgrade: {upgrade_text} ({grid_status})"
            )

            if coverage == 0 or coverage < 0.01:
                if metric['min_distance'] < np.inf:
                    label_text = (
                        f"Site {site_id} - {demand_category} Demand\n"
                        f"{location_info}\n"
                        f"Coverage: 0 EVs (Nearest: {metric['min_distance']:.1f}km)\n"
                        f"Profit: ₹{profit:.0f}\n"
                        f"Density: 0/km²\n"
                        f"Price: ₹{price:.1f}/kWh\n"
                        f"{grid_info}"
                    )
                else:
                    label_text = (
                        f"Site {site_id} - {demand_category} Demand\n"
                        f"{location_info}\n"
                        f"Coverage: 0 EVs\n"
                        f"Profit: ₹{profit:.0f}\n"
                        f"Density: 0/km²\n"
                        f"Price: ₹{price:.1f}/kWh\n"
                        f"{grid_info}"
                    )
            else:
                label_text = (
                    f"Site {site_id} - {demand_category} Demand\n"
                    f"{location_info}\n"
                    f"Coverage: {coverage:.1f} EVs\n"
                    f"Profit: ₹{profit:.0f}\n"
                    f"Density: {density:.2f}/km²\n"
                    f"Price: ₹{price:.1f}/kWh\n"
                    f"{grid_info}"
                )
            
            ax.annotate(label_text, 
                       xy=(lon, lat), 
                       xytext=(10, 10), 
                       textcoords='offset points',
                       fontsize=7,
                       bbox=dict(boxstyle='round,pad=0.3', 
                                facecolor='white', 
                                edgecolor=marker_color,
                                linewidth=1.5,
                                alpha=0.9),
                       arrowprops=dict(arrowstyle='->', 
                                     connectionstyle='arc3,rad=0',
                                     color=marker_color,
                                     lw=1.5),
                       zorder=4)
        
        # Add title and labels
        ax.set_xlabel('Longitude', fontsize=12, fontweight='bold')
        ax.set_ylabel('Latitude', fontsize=12, fontweight='bold')
        ax.set_title('EV Charging Station Optimization - Indore City\n'
                    'Selected Stations: Actual Coverage, Profit, Density, and Location', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add legend - simplified, no color coding
        legend_elements = [
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='#333333', 
                      markersize=10, label='Selected Charging Station', markeredgecolor='black', markeredgewidth=1),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff4444', 
                      markersize=8, label='High Demand Zone (>2 EVs)', alpha=0.6),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff8844', 
                      markersize=8, label='Medium Demand Zone (1-2 EVs)', alpha=0.5),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#ffdd44', 
                      markersize=8, label='Low Demand Zone (<1 EV)', alpha=0.4),
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=9, 
                 framealpha=0.9, fancybox=True, shadow=True)
        
        # Calculate statistics
        total_coverage = sum(m['coverage'] for m in site_metrics)
        total_profit = sum(m['profit'] for m in site_metrics)
        sites_with_coverage = sum(1 for m in site_metrics if m['coverage'] > 0.01)
        sites_without_coverage = len(site_metrics) - sites_with_coverage
        avg_density = np.mean([m['density'] for m in site_metrics if m['density'] > 0]) if any(m['density'] > 0 for m in site_metrics) else 0.0
        total_upgrade_cost = sum(m['grid_upgrade_cost'] for m in site_metrics)
        sites_needing_upgrade = sum(1 for m in site_metrics if not m['grid_capacity_ok'])
        
        # Count by demand category
        high_demand_sites = sum(1 for m in site_metrics if m['demand_category'] == 'High')
        medium_demand_sites = sum(1 for m in site_metrics if m['demand_category'] == 'Medium')
        low_demand_sites = sum(1 for m in site_metrics if m['demand_category'] == 'Low')
        very_low_demand_sites = sum(1 for m in site_metrics if m['demand_category'] == 'Very Low')
        
        # Add text box with summary
        summary_text = (
            f"Total Stations: {len(site_metrics)}\n"
            f"High Demand: {high_demand_sites}\n"
            f"Medium Demand: {medium_demand_sites}\n"
            f"Low Demand: {low_demand_sites}\n"
            f"Very Low: {very_low_demand_sites}\n"
            f"Total Coverage: {total_coverage:.1f} EVs\n"
            f"Total Profit: ₹{total_profit:.0f}\n"
            f"Avg Density: {avg_density:.2f} EVs/km²\n"
            f"Upgrade Cost: ₹{total_upgrade_cost:.0f}\n"
            f"Sites Needing Upgrade: {sites_needing_upgrade}"
        )
        ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
               fontweight='bold')
        
        # Print diagnostic information
        if sites_without_coverage > 0:
            print(f"\n  Diagnostic: {sites_without_coverage} sites have zero coverage")
            zero_coverage_sites = [m for m in site_metrics if m['coverage'] <= 0.01]
            if zero_coverage_sites:
                avg_min_dist = np.mean([m['min_distance'] for m in zero_coverage_sites])
                print(f"    Average distance to nearest demand: {avg_min_dist:.2f} km")
                print(f"    These sites may be selected for strategic/connectivity reasons")
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Map saved to {output_path}")
        plt.close()
        
        return fig
    
    def plot_objectives(self, solutions: List[Dict], output_path: str = "objectives_tradeoff.png"):
        """
        Plot Pareto front showing trade-offs between objectives with detailed labels.
        
        Parameters:
        -----------
        solutions : List[Dict]
            List of Pareto-optimal solutions
        output_path : str
            Path to save plot
        """
        print(f"Creating objectives trade-off plot...")
        
        costs = [s['cost'] for s in solutions]
        coverages = [s['coverage'] for s in solutions]
        profits = [s.get('profit', 0) for s in solutions]
        avg_distances = [s.get('avg_distance', 0) for s in solutions]
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        # Cost vs Coverage (colored by profit)
        scatter1 = axes[0].scatter(costs, coverages, c=profits, cmap='viridis', s=100, alpha=0.7, edgecolors='black', linewidths=0.5)
        axes[0].set_xlabel('Total Setup Cost (INR)', fontsize=12, fontweight='bold')
        axes[0].set_ylabel('Demand Coverage (EVs)', fontsize=12, fontweight='bold')
        axes[0].set_title('Cost vs Coverage Trade-off\n(Color = Profit)', fontsize=13, fontweight='bold')
        axes[0].grid(True, alpha=0.3, linestyle='--')
        cbar1 = plt.colorbar(scatter1, ax=axes[0])
        cbar1.set_label('Annual Profit (INR)', fontsize=10, fontweight='bold')
        
        # Cost vs Profit (colored by coverage)
        costs_crore = [c / 1e7 for c in costs]
        profits_lakh = [p / 1e5 for p in profits]
        scatter2 = axes[1].scatter(costs_crore, profits_lakh, c=coverages, cmap='plasma', s=100, alpha=0.7, edgecolors='black', linewidths=0.5)
        axes[1].set_xlabel('Total Setup Cost (Crore INR)', fontsize=12, fontweight='bold')
        axes[1].set_ylabel('Annual Profit (Lakh INR)', fontsize=12, fontweight='bold')
        axes[1].set_title('Cost vs Profit Trade-off\n(Color = Coverage)', fontsize=13, fontweight='bold')
        axes[1].grid(True, alpha=0.3, linestyle='--')
        cbar2 = plt.colorbar(scatter2, ax=axes[1])
        cbar2.set_label('Coverage (EVs)', fontsize=10, fontweight='bold')
        
        # Coverage vs Average Distance (colored by profit)
        scatter3 = axes[2].scatter(coverages, avg_distances, c=profits, cmap='coolwarm', s=100, alpha=0.7, edgecolors='black', linewidths=0.5)
        axes[2].set_xlabel('Demand Coverage (EVs)', fontsize=12, fontweight='bold')
        axes[2].set_ylabel('Average Service Distance (km)', fontsize=12, fontweight='bold')
        axes[2].set_title('Coverage vs Service Distance\n(Color = Profit)', fontsize=13, fontweight='bold')
        axes[2].grid(True, alpha=0.3, linestyle='--')
        cbar3 = plt.colorbar(scatter3, ax=axes[2])
        cbar3.set_label('Annual Profit (INR)', fontsize=10, fontweight='bold')
        
        # Add text annotation with best solution
        if len(solutions) > 0:
            best_idx = np.argmax(profits)
            axes[0].annotate('Best Profit', 
                           xy=(costs[best_idx], coverages[best_idx]),
                           xytext=(10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
                           fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Objectives trade-off plot saved to {output_path}")
        plt.close()
    
    def plot_solution_summary(self, solution: Dict, output_path: str = "solution_summary.png"):
        """
        Create comprehensive summary visualization of the solution.
        
        Parameters:
        -----------
        solution : Dict
            Best solution dictionary
        output_path : str
            Path to save plot
        """
        print(f"Creating solution summary plot...")
        
        selected_sites = solution['selected_sites']
        selected_indices = np.where(selected_sites == 1)[0]
        distance_matrix = self.data['distance_matrix']
        prices = solution.get('prices', np.ones(len(selected_sites)) * 10.0)
        
        # Calculate metrics for each site using centralized calculator
        site_metrics_list = []
        for j in selected_indices:
            metrics = calculate_site_metrics(
                site_idx=j,
                selected_sites=selected_sites,
                candidate_sites=self.candidate_sites,
                demand_zones=self.demand_zones,
                distance_matrix=distance_matrix,
                prices=prices
            )
            site_metrics_list.append(metrics)
        
        # Extract lists for plotting
        site_coverages = [m['coverage'] for m in site_metrics_list]
        site_profits = [m['annual_profit'] for m in site_metrics_list]
        site_densities = [m['density'] for m in site_metrics_list]
        demand_categories = [m['demand_category'] for m in site_metrics_list]
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        
        # 1. Demand Category Distribution
        category_counts = pd.Series(demand_categories).value_counts()
        colors_cat = {'High': '#2ecc71', 'Medium': '#3498db', 'Low': '#f39c12', 'Very Low': '#e74c3c'}
        cat_colors = [colors_cat.get(cat, '#95a5a6') for cat in category_counts.index]
        axes[0, 0].bar(category_counts.index, category_counts.values, color=cat_colors, edgecolor='black', linewidth=1.5)
        axes[0, 0].set_xlabel('Demand Category', fontsize=11, fontweight='bold')
        axes[0, 0].set_ylabel('Number of Sites', fontsize=11, fontweight='bold')
        axes[0, 0].set_title('Sites by Demand Category', fontsize=12, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.3, axis='y')
        for i, (cat, count) in enumerate(category_counts.items()):
            axes[0, 0].text(i, count, str(count), ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 2. Price Distribution
        selected_prices = [prices[j] for j in selected_indices if j < len(prices)]
        if selected_prices:
            axes[0, 1].hist(selected_prices, bins=15, color='coral', edgecolor='black', linewidth=1.5)
            axes[0, 1].set_xlabel('Price (INR/kWh)', fontsize=11, fontweight='bold')
            axes[0, 1].set_ylabel('Number of Sites', fontsize=11, fontweight='bold')
            axes[0, 1].set_title('Price Distribution Across Selected Sites', fontsize=12, fontweight='bold')
            axes[0, 1].grid(True, alpha=0.3, axis='y')
            axes[0, 1].axvline(np.mean(selected_prices), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(selected_prices):.2f}')
            axes[0, 1].legend()
        
        # 3. Key Metrics Summary
        total_cost_crore = solution.get('cost', 0) / 1e7  # In crore INR
        total_coverage = sum(m['coverage'] for m in site_metrics_list)
        total_profit_crore = sum(m['annual_profit'] for m in site_metrics_list) / 1e7  # In crore INR
        avg_distance = solution.get('avg_distance', 0)
        total_upgrade_lakh = sum(m['grid_upgrade_cost'] for m in site_metrics_list) / 1e5  # In lakh INR
 
        metrics = {
            'Total Cost\n(Crore INR)': total_cost_crore,
            'Coverage\n(EVs)': total_coverage / 1000,  # In thousands
            'Profit\n(Crore INR)': total_profit_crore,
            'Upgrade Cost\n(Lakh INR)': total_upgrade_lakh,
            'Avg Distance\n(km)': avg_distance
        }
        
        metric_names = list(metrics.keys())
        metric_values = list(metrics.values())
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12']
        
        bars = axes[1, 0].bar(metric_names, metric_values, color=colors, edgecolor='black', linewidth=1.5)
        axes[1, 0].set_ylabel('Value', fontsize=11, fontweight='bold')
        axes[1, 0].set_title('Solution Key Metrics', fontsize=12, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, val, name in zip(bars, metric_values, metric_names):
            height = bar.get_height()
            if 'Total Cost' in name or 'Profit' in name:
                label = f'₹{val:.2f} Cr'
            elif 'Upgrade' in name:
                label = f'₹{val:.2f} L'
            elif 'Coverage' in name:
                label = f'{val:.1f}K EVs'
            else:
                label = f'{val:.2f} km'
            axes[1, 0].text(bar.get_x() + bar.get_width()/2., height,
                           label, ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # 4. Coverage vs Profit Scatter (colored by demand category)
        site_coverages = [m['coverage'] for m in site_metrics_list]
        site_profits = [m['annual_profit'] for m in site_metrics_list]
        site_profit_lakh = [p / 1e5 for p in site_profits]
        site_categories = [m['demand_category'] for m in site_metrics_list]
        grid_ok_flags = [m['grid_capacity_ok'] for m in site_metrics_list]
        category_colors = {'High': '#2ecc71', 'Medium': '#3498db', 'Low': '#f39c12', 'Very Low': '#e74c3c'}
        scatter_colors = [category_colors.get(cat, '#999999') for cat in site_categories]

        ok_indices = [i for i, ok in enumerate(grid_ok_flags) if ok]
        upgrade_indices = [i for i, ok in enumerate(grid_ok_flags) if not ok]

        if ok_indices:
            axes[1, 1].scatter(
                [site_coverages[i] for i in ok_indices],
                [site_profit_lakh[i] for i in ok_indices],
                c=[scatter_colors[i] for i in ok_indices],
                s=90, alpha=0.7, edgecolors='black', linewidths=0.6, marker='o'
            )
        if upgrade_indices:
            axes[1, 1].scatter(
                [site_coverages[i] for i in upgrade_indices],
                [site_profit_lakh[i] for i in upgrade_indices],
                c=[scatter_colors[i] for i in upgrade_indices],
                s=140, alpha=0.85, edgecolors='black', linewidths=1.2, marker='X'
            )

        axes[1, 1].set_xlabel('Coverage (EVs)', fontsize=11, fontweight='bold')
        axes[1, 1].set_ylabel('Annual Profit (Lakh INR)', fontsize=11, fontweight='bold')
        axes[1, 1].set_title('Coverage vs Profit\n(Color = Demand Category)', fontsize=12, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.3, linestyle='--')

        # Add legend for categories and grid status
        from matplotlib.patches import Patch
        unique_categories = ['High', 'Medium', 'Low', 'Very Low']
        category_handles = [Patch(facecolor=category_colors[cat], edgecolor='black', label=cat)
                            for cat in unique_categories if cat in site_categories]
        status_handles = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#666666', markeredgecolor='black',
                   label='Grid OK', markersize=7, markeredgewidth=0.8),
            Line2D([0], [0], marker='X', color='w', markerfacecolor='#e74c3c', markeredgecolor='black',
                   label='Upgrade Needed', markersize=8, markeredgewidth=1.2)
        ]
        axes[1, 1].legend(handles=category_handles + status_handles, loc='upper left', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Solution summary plot saved to {output_path}")
        plt.close()

    def plot_convergence(self, convergence_history: List[Dict], output_path: str = "convergence_curve.png"):
        """
        Plot NSGA-II convergence trends generation by generation.
        Plots:
        1. Investment (Cost)
        2. Coverage
        3. Service Distance
        4. Number of Stations
        """
        if not convergence_history:
            print("Warning: No convergence history to plot.")
            return

        history_df = pd.DataFrame(convergence_history)
        generations = history_df['generation']

        fig, axes = plt.subplots(4, 1, figsize=(12, 16), sharex=True)
        fig.suptitle('NSGA-II Convergence: Evolution of Objectives', fontsize=16, fontweight='bold')

        # 1. Investment (Cost)
        axes[0].plot(generations, history_df['avg_cost'] / 1e7, label='Average Investment', color='#3498db', linewidth=2)
        axes[0].plot(generations, history_df['best_cost'] / 1e7, label='Min Investment', color='#1f618d', linestyle='--', linewidth=2)
        axes[0].set_ylabel('Investment (Crore INR)', fontsize=11, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].set_title('1. Investment (Minimize Cost)', fontsize=12)

        # 2. Coverage
        axes[1].plot(generations, history_df['avg_coverage'], label='Average Coverage', color='#2ecc71', linewidth=2)
        axes[1].plot(generations, history_df['best_coverage'], label='Max Coverage', color='#196f3d', linestyle='--', linewidth=2)
        axes[1].set_ylabel('Coverage (EVs)', fontsize=11, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')
        axes[1].set_title('2. Coverage (Maximize Demand Served)', fontsize=12)

        # 3. Distance
        axes[2].plot(generations, history_df['avg_distance'], label='Average Distance', color='#e67e22', linewidth=2)
        axes[2].plot(generations, history_df['best_distance'], label='Min Distance', color='#ba4a00', linestyle='--', linewidth=2)
        axes[2].set_ylabel('Avg Distance (km)', fontsize=11, fontweight='bold')
        axes[2].grid(True, alpha=0.3)
        axes[2].legend(loc='upper right')
        axes[2].set_title('3. Service Distance (Minimize)', fontsize=12)

        # 4. Station Count
        if 'avg_sites' in history_df.columns:
            axes[3].plot(generations, history_df['avg_sites'], label='Average Count', color='#9b59b6', linewidth=2)
            axes[3].plot(generations, history_df['min_sites'], label='Min Count', color='#8e44ad', linestyle=':', linewidth=2)
            axes[3].plot(generations, history_df['max_sites'], label='Max Count', color='#8e44ad', linestyle='--', linewidth=2)
            axes[3].set_ylabel('Number of Stations', fontsize=11, fontweight='bold')
            axes[3].grid(True, alpha=0.3)
            axes[3].legend(loc='upper right')
            axes[3].set_title('4. Network Growth (Station Count)', fontsize=12)
        
        axes[3].set_xlabel('Generation', fontsize=12, fontweight='bold')

        plt.tight_layout(rect=[0, 0, 1, 0.97])
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Convergence curve saved to {output_path}")
        plt.close()

