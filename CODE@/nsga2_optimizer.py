"""
NSGA-II Multi-Objective Optimization for EVCS Placement

This module implements the Non-dominated Sorting Genetic Algorithm II (NSGA-II)
to optimize multiple objectives simultaneously:
1. Minimize total cost (setup + operating)
2. Maximize coverage (demand served)
3. Minimize average distance to charging stations

Reference: Deb, K., et al. (2002). A fast and elitist multiobjective 
           genetic algorithm: NSGA-II.

Author: EVCS Optimization Team
Date: 2024
"""

import numpy as np
from typing import List, Tuple, Dict
from deap import base, creator, tools, algorithms
import random
import warnings
warnings.filterwarnings('ignore')


class NSGA2Optimizer:
    """
    NSGA-II optimizer for multi-objective EVCS placement.
    
    Objectives:
    - Minimize total cost
    - Maximize demand coverage
    - Minimize average service distance
    """
    
    def __init__(self, data: Dict, 
                 population_size: int = 50,
                 n_generations: int = 100,
                 crossover_prob: float = 0.9,
                 mutation_prob: float = 0.1):
        """
        Initialize NSGA-II optimizer.
        
        Parameters:
        -----------
        data : Dict
            Dictionary containing demand_zones, candidate_sites, distance_matrix
        population_size : int
            Size of genetic algorithm population
        n_generations : int
            Number of generations to evolve
        crossover_prob : float
            Probability of crossover
        mutation_prob : float
            Probability of mutation
        """
        self.data = data
        self.demand_zones = data['demand_zones']
        self.candidate_sites = data['candidate_sites']
        self.distance_matrix = data['distance_matrix']
        
        self.n_zones = len(self.demand_zones)
        self.n_sites = len(self.candidate_sites)
        self.population_size = population_size
        self.n_generations = n_generations
        self.convergence_history: List[Dict[str, float]] = []
        
        # Problem parameters
        self.max_service_distance = 5.0  # km
        self.operating_cost_per_kwh = 4.0  # INR per kWh
        self.budget = 600000000  # 60 Crore INR budget to allow 60-100 sites
        self.min_sites = 5  # Relaxed from 60 to allow dynamic growth
        self.max_sites = min(100, self.n_sites)

        self.cost_column = 'total_setup_cost' if 'total_setup_cost' in self.candidate_sites.columns else 'setup_cost'
        self.site_costs = self.candidate_sites[self.cost_column].values.astype(float)
        self.sorted_site_indices = list(np.argsort(self.site_costs))
        self.cheapest_site_idx = int(self.sorted_site_indices[0])
        
        # Setup DEAP
        self._setup_deap()

    def _setup_deap(self):
        """Setup DEAP framework for NSGA-II."""
        # Create fitness classes (with error handling for multiple imports)
        try:
            creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0, -1.0))
        except RuntimeError:
            # Already exists, delete and recreate
            if hasattr(creator, "FitnessMulti"):
                del creator.FitnessMulti
            creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0, -1.0))
        
        # Negative weights: minimize cost, maximize coverage, minimize distance
        try:
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        except RuntimeError:
            if hasattr(creator, "Individual"):
                del creator.Individual
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        
        self.toolbox = base.Toolbox()
        
        def _generate_individual():
            target = random.randint(self.min_sites, self.max_sites)
            indices = random.sample(range(self.n_sites), target)
            genes = [0] * self.n_sites
            for idx in indices:
                genes[idx] = 1
            return creator.Individual(genes)
        
        self.toolbox.register("individual", _generate_individual)
        self.toolbox.register("population", tools.initRepeat, list, 
                             self.toolbox.individual)
        
        # Genetic operators
        self.toolbox.register("evaluate", self._evaluate_individual)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
        self.toolbox.register("select", tools.selNSGA2)
        
    def _evaluate_individual(self, individual: List[int]) -> Tuple[float, float, float]:
        """
        Evaluate an individual (site selection) on three objectives.
        
        Parameters:
        -----------
        individual : List[int]
            Binary vector representing site selection
            
        Returns:
        --------
        Tuple[float, float, float]
            (total_cost, -coverage, avg_distance)
            Note: coverage is negated because we maximize it
        """
        selected_sites = np.array(individual)
        selected_indices = np.where(selected_sites == 1)[0]
        
        # Objective 1: Total cost
        total_cost = self.site_costs[selected_indices].sum()
        
        # Enforce site count bounds
        site_count = len(selected_indices)
        if site_count < self.min_sites:
            shortage = self.min_sites - site_count
            penalty = 1e9 * shortage
            return (1e10 + penalty, 0.0, 1e3)
        if site_count > self.max_sites:
            excess = site_count - self.max_sites
            penalty = 1e9 * excess
            return (1e10 + penalty, 0.0, 1e3)

        # Budget constraint penalty
        if total_cost > self.budget:
            penalty = 1e8 * (total_cost - self.budget) / self.budget
            return (1e10 + penalty, -1e10, 1e10)  # Penalize infeasible solutions
        
        # Objective 2: Coverage (demand served)
        total_coverage = 0.0
        total_distance = 0.0
        zones_covered = 0
        
        for i in range(self.n_zones):
            zone_demand = self.demand_zones.iloc[i]['demand']
            min_distance = np.inf
            served = False
            
            # Find nearest selected site
            for j in selected_indices:
                dist = self.distance_matrix[i, j]
                if dist <= self.max_service_distance:
                    served = True
                    min_distance = min(min_distance, dist)
            
            if served:
                total_coverage += zone_demand
                total_distance += min_distance
                zones_covered += 1
        
        # Objective 3: Average distance (only for covered zones)
        avg_distance = total_distance / max(zones_covered, 1)
        
        # Penalize solutions that cover nothing
        if total_coverage <= 0:
            return (1e9, 0.0, 1e3)
        
        # Return: (cost, -coverage, avg_distance)
        # Coverage negated because DEAP maximizes, but we want to maximize coverage
        return (total_cost, -total_coverage, avg_distance)

    def _repair_individual(self, individual):
        """
        Enforce budget feasibility by turning off random sites until cost <= budget.
        """
        selected_indices = [idx for idx, val in enumerate(individual) if val == 1]

        # If nothing selected, start with cheapest feasible site
        if not selected_indices:
            individual[self.cheapest_site_idx] = 1
            selected_indices = [self.cheapest_site_idx]

        total_cost = self.site_costs[selected_indices].sum()

        # Ensure at least min_sites
        if len(selected_indices) < self.min_sites:
            for idx in self.sorted_site_indices:
                if len(selected_indices) >= self.min_sites:
                    break
                if individual[idx] == 0:
                    individual[idx] = 1
                    selected_indices.append(idx)
                    total_cost += self.site_costs[idx]

        # Trim to maximum site count (remove most expensive first)
        while len(selected_indices) > self.max_sites:
            idx_to_remove = max(selected_indices, key=lambda ix: self.site_costs[ix])
            individual[idx_to_remove] = 0
            selected_indices.remove(idx_to_remove)
            total_cost -= self.site_costs[idx_to_remove]

        # Enforce budget while keeping at least min_sites
        while total_cost > self.budget and len(selected_indices) > self.min_sites:
            idx_to_remove = max(selected_indices, key=lambda ix: self.site_costs[ix])
            individual[idx_to_remove] = 0
            selected_indices.remove(idx_to_remove)
            total_cost -= self.site_costs[idx_to_remove]

        # If still above budget (rare), swap expensive sites with cheaper ones
        if total_cost > self.budget:
            for idx in self.sorted_site_indices:
                if idx in selected_indices:
                    continue
                # Replace most expensive site with cheaper candidate
                expensive_idx = max(selected_indices, key=lambda ix: self.site_costs[ix])
                if self.site_costs[idx] < self.site_costs[expensive_idx]:
                    individual[expensive_idx] = 0
                    total_cost -= self.site_costs[expensive_idx]
                    selected_indices.remove(expensive_idx)
                    individual[idx] = 1
                    selected_indices.append(idx)
                    total_cost += self.site_costs[idx]
                if total_cost <= self.budget:
                    break

        # Final guarantee: if we somehow dipped below min_sites, add cheapest remaining
        if len(selected_indices) < self.min_sites:
            for idx in self.sorted_site_indices:
                if individual[idx] == 0:
                    if total_cost + self.site_costs[idx] <= self.budget:
                        individual[idx] = 1
                        selected_indices.append(idx)
                        total_cost += self.site_costs[idx]
                if len(selected_indices) >= self.min_sites:
                    break

        return individual

    def solve(self) -> Dict:
        """
        Solve multi-objective optimization using NSGA-II.
        
        Returns:
        --------
        Dict
            Pareto-optimal solutions with objectives and site selections
        """
        print("\n=== NSGA-II Multi-Objective Optimizer ===")
        print(f"Population size: {self.population_size}")
        print(f"Generations: {self.n_generations}")
        
        # Initialize population and repair infeasible individuals
        population = self.toolbox.population(n=self.population_size)
        population = [self._repair_individual(ind) for ind in population]
        
        # Evaluate initial population
        fitnesses = list(map(self.toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit
        
        # Evolution loop
        self.convergence_history = []
        for generation in range(self.n_generations):
            # Select parents
            offspring = algorithms.varAnd(population, self.toolbox, 
                                         cxpb=0.9, mutpb=0.1)
            offspring = [self._repair_individual(ind) for ind in offspring]
            
            # Evaluate offspring
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            # Select next generation
            population = self.toolbox.select(offspring + population, 
                                            self.population_size)
            
            # Track convergence metrics
            fits = [ind.fitness.values for ind in population]
            costs = np.array([f[0] for f in fits], dtype=float)
            coverages = np.array([-f[1] for f in fits], dtype=float)  # Negate back
            distances = np.array([f[2] for f in fits], dtype=float)
            
            # Track station counts
            site_counts = np.array([sum(ind) for ind in population], dtype=float)
            
            # Calculate stats
            stats = {
                'generation': generation,
                'best_cost': float(np.min(costs)),
                'avg_cost': float(np.mean(costs)),
                'worst_cost': float(np.max(costs)),
                'best_coverage': float(np.max(coverages)),
                'avg_coverage': float(np.mean(coverages)),
                'worst_coverage': float(np.min(coverages)),
                'best_distance': float(np.min(distances)),
                'avg_distance': float(np.mean(distances)),
                'worst_distance': float(np.max(distances)),
                'avg_sites': float(np.mean(site_counts)),
                'min_sites': float(np.min(site_counts)),
                'max_sites': float(np.max(site_counts))
            }
            self.convergence_history.append(stats)
            
            # Print stats for every generation as requested
            print(f"Generation {generation}: "
                  f"Cost [Avg: {stats['avg_cost']:.0f}] | "
                  f"Coverage [Avg: {stats['avg_coverage']:.0f}] | "
                  f"Sites [Avg: {stats['avg_sites']:.1f}]")
        
        # Extract Pareto front
        pareto_front = tools.sortNondominated(population, len(population),
                                            first_front_only=True)[0]
        
        print(f"\n[OK] Found {len(pareto_front)} Pareto-optimal solutions")
        
        # Convert to solution format
        solutions = []
        for ind in pareto_front:
            selected_sites = np.array(ind)
            cost, neg_coverage, avg_dist = ind.fitness.values
            coverage = -neg_coverage  # Convert back
            
            solutions.append({
                'selected_sites': selected_sites,
                'cost': cost,
                'coverage': coverage,
                'avg_distance': avg_dist,
                'n_sites': np.sum(selected_sites)
            })
        
        return {
            'pareto_solutions': solutions,
            'population': population,
            'convergence_history': self.convergence_history
        }

