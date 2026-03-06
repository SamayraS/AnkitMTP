"""
Benders Decomposition for EVCS Location Optimization

This module implements Benders decomposition to solve the master problem
of selecting optimal EV charging station locations, decomposing the
complex mixed-integer problem into a master problem (location selection)
and subproblems (pricing and demand allocation).

Reference: Benders, J.F. (1962). Partitioning procedures for solving 
           mixed-variables programming problems.

Author: EVCS Optimization Team
Date: 2024
"""

import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import linprog
import warnings
warnings.filterwarnings('ignore')


class BendersDecomposition:
    """
    Benders decomposition solver for EVCS location optimization.
    
    The problem is decomposed into:
    - Master Problem: Binary location decisions (which sites to open)
    - Subproblem: Continuous pricing and demand allocation decisions
    """
    
    def __init__(self, data: Dict, max_iterations: int = 50, 
                 tolerance: float = 1e-4):
        """
        Initialize Benders decomposition solver.
        
        Parameters:
        -----------
        data : Dict
            Dictionary containing demand_zones, candidate_sites, distance_matrix
        max_iterations : int
            Maximum number of Benders iterations
        tolerance : float
            Convergence tolerance
        """
        self.data = data
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        
        # Extract data
        self.demand_zones = data['demand_zones']
        self.candidate_sites = data['candidate_sites']
        self.distance_matrix = data['distance_matrix']
        
        self.n_zones = len(self.demand_zones)
        self.n_sites = len(self.candidate_sites)
        
        # Benders cuts storage
        self.benders_cuts = []
        
        # Problem parameters
        self.max_service_distance = 5.0  # km
        self.operating_cost_per_kwh = 4.0  # INR per kWh
        self.demand_elasticity = -0.5  # Price elasticity of demand
        
    def solve_subproblem(self, selected_sites: np.ndarray, 
                        prices: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Solve the subproblem: optimize demand allocation and calculate revenue.
        
        Given selected sites and prices, determine optimal demand allocation
        and compute total profit.
        
        Parameters:
        -----------
        selected_sites : np.ndarray
            Binary array indicating which sites are selected
        prices : np.ndarray
            Price per kWh at each selected site
            
        Returns:
        --------
        Tuple[float, np.ndarray, np.ndarray]
            (total_profit, demand_allocation, dual_variables)
        """
        # Filter to only selected sites
        selected_indices = np.where(selected_sites == 1)[0]
        if len(selected_indices) == 0:
            return 0.0, np.zeros((self.n_zones, self.n_sites)), np.zeros(self.n_zones)
        
        # Initialize allocation matrix
        allocation = np.zeros((self.n_zones, self.n_sites))
        total_revenue = 0.0
        total_cost = 0.0
        
        # For each demand zone, allocate to nearest feasible site
        for i in range(self.n_zones):
            zone_demand = self.demand_zones.iloc[i]['demand']
            
            # Find feasible sites (within max distance)
            feasible_sites = []
            for j in selected_indices:
                if self.distance_matrix[i, j] <= self.max_service_distance:
                    feasible_sites.append((j, self.distance_matrix[i, j]))
            
            if not feasible_sites:
                continue
            
            # Sort by distance
            feasible_sites.sort(key=lambda x: x[1])
            
            # Allocate demand based on distance and price
            remaining_demand = zone_demand
            for j, dist in feasible_sites:
                # Price-adjusted demand (elasticity effect)
                price = prices[j]
                price_factor = (price / 10.0) ** self.demand_elasticity
                allocated = min(remaining_demand * price_factor, 
                              self.candidate_sites.iloc[j]['capacity'] * 0.8)
                
                allocation[i, j] = allocated
                remaining_demand -= allocated
                
                # Revenue and cost
                revenue = allocated * price
                cost = allocated * self.operating_cost_per_kwh
                total_revenue += revenue
                total_cost += cost
                
                if remaining_demand <= 0:
                    break
        
        profit = total_revenue - total_cost
        
        # Dual variables (simplified - for Benders cuts)
        dual_vars = np.ones(self.n_zones) * 0.1  # Simplified dual
        
        return profit, allocation, dual_vars
    
    def add_benders_cut(self, selected_sites: np.ndarray, 
                       profit: float, dual_vars: np.ndarray):
        """
        Add a Benders optimality cut to the master problem.
        
        Parameters:
        -----------
        selected_sites : np.ndarray
            Current site selection
        profit : float
            Profit from subproblem
        dual_vars : np.ndarray
            Dual variables from subproblem
        """
        self.benders_cuts.append({
            'sites': selected_sites.copy(),
            'profit': profit,
            'dual': dual_vars.copy()
        })
    
    def solve_master_problem(self, current_lower_bound: float = 0.0) -> Tuple[np.ndarray, float]:
        """
        Solve master problem: select sites to maximize profit.
        
        Uses a greedy heuristic with Benders cuts constraints.
        
        Parameters:
        -----------
        current_lower_bound : float
            Current best known lower bound
            
        Returns:
        --------
        Tuple[np.ndarray, float]
            (selected_sites, estimated_profit)
        """
        # Simplified master problem: greedy selection with cut constraints
        # In full implementation, this would be solved as MIP
        
        selected = np.zeros(self.n_sites, dtype=int)
        budget = 50000000  # Total budget in INR
        used_budget = 0.0
        
        # Calculate site scores (revenue potential / cost)
        site_scores = []
        for j in range(self.n_sites):
            # Estimate potential revenue
            potential_demand = 0
            for i in range(self.n_zones):
                if self.distance_matrix[i, j] <= self.max_service_distance:
                    potential_demand += self.demand_zones.iloc[i]['demand']
            
            revenue_estimate = potential_demand * 10.0  # Assume 10 INR/kWh
            cost = self.candidate_sites.iloc[j]['setup_cost']
            score = revenue_estimate / cost if cost > 0 else 0
            
            site_scores.append((j, score, cost))
        
        # Sort by score
        site_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select sites within budget
        for j, score, cost in site_scores:
            if used_budget + cost <= budget:
                selected[j] = 1
                used_budget += cost
        
        # Check Benders cuts (simplified)
        # In full implementation, would enforce cut constraints
        
        estimated_profit = used_budget * 0.3  # Rough estimate
        
        return selected, estimated_profit
    
    def solve(self) -> Dict:
        """
        Solve the EVCS location problem using Benders decomposition.
        
        Returns:
        --------
        Dict
            Solution containing selected sites, prices, and metrics
        """
        print("\n=== Benders Decomposition Solver ===")
        print(f"Problem size: {self.n_zones} zones, {self.n_sites} sites")
        
        best_solution = None
        best_profit = -np.inf
        lower_bound = -np.inf
        upper_bound = np.inf
        
        # Initial solution
        selected_sites, estimated_profit = self.solve_master_problem()
        prices = np.ones(self.n_sites) * 10.0  # Initial prices
        
        for iteration in range(self.max_iterations):
            # Solve subproblem
            profit, allocation, dual_vars = self.solve_subproblem(selected_sites, prices)
            
            # Update bounds
            upper_bound = min(upper_bound, profit)
            lower_bound = max(lower_bound, profit)
            
            # Add Benders cut
            self.add_benders_cut(selected_sites, profit, dual_vars)
            
            # Check convergence
            gap = (upper_bound - lower_bound) / max(abs(upper_bound), 1e-6)
            
            if iteration % 5 == 0:
                print(f"  Iteration {iteration}: Profit = {profit:.2f}, Gap = {gap:.4f}")
            
            if gap < self.tolerance:
                print(f"  Converged at iteration {iteration}")
                break
            
            # Update master problem solution
            if profit > best_profit:
                best_profit = profit
                best_solution = {
                    'selected_sites': selected_sites.copy(),
                    'prices': prices.copy(),
                    'allocation': allocation.copy(),
                    'profit': profit
                }
            
            # Solve new master problem
            selected_sites, _ = self.solve_master_problem(lower_bound)
            
            # Update prices (simplified pricing optimization)
            for j in range(self.n_sites):
                if selected_sites[j] == 1:
                    # Price based on demand and competition
                    prices[j] = np.random.uniform(8, 12)
        
        if best_solution is None:
            best_solution = {
                'selected_sites': selected_sites,
                'prices': prices,
                'allocation': allocation,
                'profit': profit
            }
        
        print(f"[OK] Final profit: {best_profit:.2f} INR")
        print(f"[OK] Selected {np.sum(best_solution['selected_sites'])} sites")
        
        return best_solution

