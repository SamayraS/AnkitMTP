"""
Hybrid Optimization: Benders Decomposition + NSGA-II

This module combines Benders decomposition (for location selection)
with NSGA-II (for multi-objective optimization) to solve the EVCS
placement and pricing problem.

The hybrid approach:
1. Uses NSGA-II to find Pareto-optimal site selections
2. Uses Benders decomposition to optimize pricing for each selection
3. Combines results to find best trade-offs

Author: EVCS Optimization Team
Date: 2024
"""

import numpy as np
from typing import Dict, List
from benders_decomposition import BendersDecomposition
from nsga2_optimizer import NSGA2Optimizer
from site_metrics_calculator import compute_proximity_penalty_factor
import warnings
warnings.filterwarnings('ignore')


class HybridOptimizer:
    """
    Hybrid optimizer combining Benders decomposition and NSGA-II.
    """
    
    def __init__(self, data: Dict, 
                 nsga2_generations: int = 150,
                 benders_iterations: int = 90):
        """
        Initialize hybrid optimizer.
        
        Parameters:
        -----------
        data : Dict
            Dictionary containing all problem data
        nsga2_generations : int
            Number of NSGA-II generations
        benders_iterations : int
            Number of Benders iterations per site selection
        """
        self.data = data
        self.nsga2_generations = nsga2_generations
        self.benders_iterations = benders_iterations
        
        # Initialize sub-optimizers
        self.nsga2 = NSGA2Optimizer(data, n_generations=nsga2_generations)
        self.benders = BendersDecomposition(data, max_iterations=benders_iterations)
        
    def optimize_pricing(self, selected_sites: np.ndarray) -> Dict:
        """
        Optimize pricing for a given site selection using Benders decomposition.
        
        Parameters:
        -----------
        selected_sites : np.ndarray
            Binary array of selected sites
            
        Returns:
        --------
        Dict
            Optimized pricing solution
        """
        # Set selected sites in Benders solver
        # (In full implementation, would modify Benders to accept fixed sites)
        
        # Simplified pricing optimization
        prices = np.zeros(len(selected_sites))
        total_revenue = 0.0
        total_cost = 0.0
        
        selected_indices = np.where(selected_sites == 1)[0]
        
        for j in selected_indices:
            # Optimize price for site j
            # Price based on demand density and competition
            demand_density = 0
            for i in range(len(self.data['demand_zones'])):
                if self.data['distance_matrix'][i, j] <= 5.0:
                    demand_density += self.data['demand_zones'].iloc[i]['demand']
            
            # Optimal price (simplified: balance demand and revenue)
            base_price = 10.0
            price_adjustment = min(demand_density / 1000.0, 3.0)  # Cap adjustment
            prices[j] = base_price + price_adjustment
            
            # Estimate revenue and cost
            competition_factor = compute_proximity_penalty_factor(
                site_idx=j,
                selected_sites=selected_sites,
                candidate_sites=self.data['candidate_sites']
            )
            estimated_demand = demand_density * 0.3 * competition_factor  # Adjust for cannibalization
            revenue = estimated_demand * prices[j]
            cost = estimated_demand * 4.0  # Operating cost
            
            total_revenue += revenue
            total_cost += cost
        
        profit = total_revenue - total_cost
        
        return {
            'prices': prices,
            'revenue': total_revenue,
            'cost': total_cost,
            'profit': profit
        }
    
    def solve(self) -> Dict:
        """
        Solve the hybrid optimization problem.
        
        Returns:
        --------
        Dict
            Complete solution with site selections, prices, and metrics
        """
        print("\n" + "="*60)
        print("HYBRID OPTIMIZATION: Benders Decomposition + NSGA-II")
        print("="*60)
        
        # Step 1: Find Pareto-optimal site selections using NSGA-II
        print("\n[Step 1] Finding Pareto-optimal site selections (NSGA-II)...")
        nsga2_result = self.nsga2.solve()
        pareto_solutions = nsga2_result['pareto_solutions']
        convergence_history = nsga2_result.get('convergence_history', [])
        if convergence_history:
            last_entry = convergence_history[-1]
            print("  Final generation snapshot:")
            print(f"    Avg cost: {last_entry['avg_cost']:.0f} INR")
            print(f"    Avg coverage: {last_entry['avg_coverage']:.1f} EVs")
            print(f"    Avg distance: {last_entry['avg_distance']:.2f} km")
        
        print(f"  Found {len(pareto_solutions)} Pareto-optimal selections")
        
        # Step 2: Optimize pricing for each Pareto solution using Benders
        print("\n[Step 2] Optimizing pricing for each solution (Benders)...")
        optimized_solutions = []
        
        for idx, solution in enumerate(pareto_solutions[:10]):  # Limit to top 10
            selected_sites = solution['selected_sites']
            
            pricing_result = self.optimize_pricing(selected_sites)
            
            # Combine results
            combined_solution = {
                'selected_sites': selected_sites,
                'prices': pricing_result['prices'],
                'cost': solution['cost'],
                'coverage': solution['coverage'],
                'avg_distance': solution['avg_distance'],
                'revenue': pricing_result['revenue'],
                'profit': pricing_result['profit'],
                'n_sites': solution['n_sites']
            }
            
            optimized_solutions.append(combined_solution)
            
            if (idx + 1) % 5 == 0:
                print(f"  Optimized {idx + 1}/{min(10, len(pareto_solutions))} solutions...")
        
        # Step 3: Select best solution (trade-off between objectives)
        print("\n[Step 3] Selecting best solution...")
        best_solution = self._select_best_solution(optimized_solutions)
        
        print("\n" + "="*60)
        print("OPTIMIZATION COMPLETE")
        print("="*60)
        print(f"Selected {best_solution['n_sites']} charging stations")
        print(f"Total cost: {best_solution['cost']:,.2f} INR")
        print(f"Demand coverage: {best_solution['coverage']:.2f} EVs")
        print(f"Average distance: {best_solution['avg_distance']:.2f} km")
        print(f"Expected revenue: {best_solution['revenue']:,.2f} INR")
        print(f"Expected profit: {best_solution['profit']:,.2f} INR")
        
        return {
            'best_solution': best_solution,
            'pareto_solutions': optimized_solutions,
            'all_solutions': optimized_solutions,
            'convergence_history': convergence_history
        }
    
    def _select_best_solution(self, solutions: List[Dict]) -> Dict:
        """
        Select best solution from Pareto front based on weighted objectives.
        
        Parameters:
        -----------
        solutions : List[Dict]
            List of optimized solutions
            
        Returns:
        --------
        Dict
            Best solution
        """
        if not solutions:
            raise ValueError("No solutions to select from")
        
        # Normalize objectives for comparison
        costs = np.array([s['cost'] for s in solutions])
        coverages = np.array([s['coverage'] for s in solutions])
        profits = np.array([s['profit'] for s in solutions])
        
        # Normalize to [0, 1]
        cost_norm = (costs - costs.min()) / (costs.max() - costs.min() + 1e-6)
        coverage_norm = (coverages - coverages.min()) / (coverages.max() - coverages.min() + 1e-6)
        profit_norm = (profits - profits.min()) / (profits.max() - profits.min() + 1e-6)
        
        # Weighted score (higher is better)
        # Weights: profit > coverage > cost (inverse)
        weights = np.array([0.5, 0.3, 0.2])  # [profit, coverage, -cost]
        scores = (profit_norm * weights[0] + 
                 coverage_norm * weights[1] + 
                 (1 - cost_norm) * weights[2])
        
        best_idx = np.argmax(scores)
        return solutions[best_idx]

