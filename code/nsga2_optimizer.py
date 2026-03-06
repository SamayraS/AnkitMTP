"""
Clean NSGA-II implementation (single top-level class).
This file replaces previous corrupted/duplicated content.
"""

import numpy as np
from typing import List, Tuple, Dict
from deap import base, creator, tools, algorithms
import random
import warnings
warnings.filterwarnings('ignore')
from site_metrics_calculator import calculate_site_metrics


class NSGA2Optimizer:
    def __init__(self, data: Dict, population_size: int = 50, n_generations: int = 100):
        self.data = data
        self.demand_zones = data['demand_zones']
        self.candidate_sites = data['candidate_sites']
        self.distance_matrix = data['distance_matrix']

        self.n_zones = len(self.demand_zones)
        self.n_sites = len(self.candidate_sites)
        self.population_size = 60  # Increased for better exploration
        self.n_generations = n_generations

        self.max_service_distance = 5.0
        self.budget = 6e8
        self.min_sites = 5
        self.max_sites = min(100, self.n_sites)

        self.cost_column = 'total_setup_cost' if 'total_setup_cost' in self.candidate_sites.columns else 'setup_cost'
        self.site_costs = self.candidate_sites[self.cost_column].values.astype(float)
        self.sorted_site_indices = list(np.argsort(self.site_costs))
        self.cheapest_site_idx = int(self.sorted_site_indices[0])

        # DEAP setup
        try:
            # 4 objectives: min Cost, max Coverage, min Distance, max Profit
            creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0, -1.0, 1.0))
        except Exception:
            if hasattr(creator, 'FitnessMulti'):
                del creator.FitnessMulti
            creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0, -1.0, 1.0))

        try:
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        except Exception:
            if hasattr(creator, 'Individual'):
                del creator.Individual
            creator.create("Individual", list, fitness=creator.FitnessMulti)

        self.toolbox = base.Toolbox()

        def gen_ind():
            target = random.randint(self.min_sites, self.max_sites)
            inds = random.sample(range(self.n_sites), target)
            g = [0] * self.n_sites
            for i in inds:
                g[i] = 1
            return creator.Individual(g)

        self.toolbox.register('individual', gen_ind)
        self.toolbox.register('population', tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register('mate', tools.cxTwoPoint)
        self.toolbox.register('mutate', tools.mutFlipBit, indpb=0.05)
        self.toolbox.register('select', tools.selNSGA2)
        self.toolbox.register('evaluate', self._evaluate_individual)

    def _evaluate_individual(self, individual: List[int]) -> Tuple[float, float, float, float]:
        sel = np.array(individual)
        idx = np.where(sel == 1)[0]
        total_cost = float(self.site_costs[idx].sum()) if len(idx) > 0 else 1e9
        if len(idx) < self.min_sites:
            return (1e10, 0.0, 1e3, -1e10)
        if total_cost > self.budget:
            return (1e10, -1e10, 1e3, -1e10)

        coverage = 0.0
        dist_sum = 0.0
        covered = 0
        for i in range(self.n_zones):
            demand = self.demand_zones.iloc[i]['demand']
            min_d = np.inf
            served = False
            for j in idx:
                d = self.distance_matrix[i, j]
                if d <= self.max_service_distance:
                    served = True
                    min_d = min(min_d, d)
            if served:
                coverage += demand
                dist_sum += min_d
                covered += 1

        avg_dist = dist_sum / max(covered, 1)
        
        # Calculate approximate profit for optimization guidance
        # Use default price of 10.0 for initial optimization
        prices = np.ones(self.n_sites) * 10.0
        total_profit = 0.0
        
        # We need queue metrics anyway for wait times
        peak_waits = []
        normal_waits = []
        overall_waits = []
        
        for j in idx:
            try:
                metrics = calculate_site_metrics(
                    site_idx=int(j),
                    selected_sites=sel,
                    candidate_sites=self.candidate_sites,
                    demand_zones=self.demand_zones,
                    distance_matrix=self.distance_matrix,
                    prices=prices
                )
                total_profit += metrics.get('annual_profit', 0.0)
                
                q = metrics.get('queue', {})
                peak = q.get('peak', {})
                normal = q.get('normal', {})
                peak_waits.append(peak.get('avg_wait_time_min', 0.0) or 0.0)
                normal_waits.append(normal.get('avg_wait_time_min', 0.0) or 0.0)
                overall_waits.append(q.get('avg_wait_time_min', 0.0) or 0.0)
            except Exception:
                peak_waits.append(0.0)
                normal_waits.append(0.0)
                overall_waits.append(0.0)

        if coverage <= 0:
             try:
                individual.avg_wait_min = 0.0
                individual.avg_wait_peak_min = 0.0
                individual.avg_wait_normal_min = 0.0
             except Exception:
                pass
             return (1e9, 0.0, 1e3, -1e10)

        try:
            individual.avg_wait_peak_min = float(np.mean(peak_waits)) if peak_waits else 0.0
            individual.avg_wait_normal_min = float(np.mean(normal_waits)) if normal_waits else 0.0
            individual.avg_wait_min = float(np.mean(overall_waits)) if overall_waits else 0.0
        except Exception:
            individual.avg_wait_peak_min = 0.0
            individual.avg_wait_normal_min = 0.0
            individual.avg_wait_min = 0.0

        return (total_cost, -coverage, avg_dist, total_profit)

    def _repair_individual(self, individual):
        sel = [i for i, v in enumerate(individual) if v == 1]
        if not sel:
            individual[self.cheapest_site_idx] = 1
        return individual

    def solve(self) -> Dict:
        population = self.toolbox.population(n=self.population_size)
        population = [self._repair_individual(ind) for ind in population]
        for ind in population:
            ind.fitness.values = self.toolbox.evaluate(ind)
        # Convergence tracking
        convergence_history = []

        for gen in range(self.n_generations):
            # Variation
            offspring = algorithms.varAnd(population, self.toolbox, cxpb=0.9, mutpb=0.1)
            offspring = [self._repair_individual(ind) for ind in offspring]

            # Evaluate invalid individuals and compute their queue metrics via _evaluate_individual
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            for ind in invalid:
                ind.fitness.values = self.toolbox.evaluate(ind)

            # Select next generation
            population = self.toolbox.select(population + offspring, self.population_size)

            # Compute generation-level aggregates
            costs = np.array([ind.fitness.values[0] for ind in population], dtype=float)
            coverages = np.array([-ind.fitness.values[1] for ind in population], dtype=float)
            distances = np.array([ind.fitness.values[2] for ind in population], dtype=float)
            sites_counts = np.array([int(np.sum(ind)) for ind in population], dtype=int)
            avg_waits = np.array([getattr(ind, 'avg_wait_min', 0.0) for ind in population], dtype=float)
            avg_waits_peak = np.array([getattr(ind, 'avg_wait_peak_min', 0.0) for ind in population], dtype=float)
            avg_waits_normal = np.array([getattr(ind, 'avg_wait_normal_min', 0.0) for ind in population], dtype=float)

            # Count unstable sites (where queue wait is infinite) before sanitization
            unstable_sites = 0
            if avg_waits.size > 0:
                avg_waits = avg_waits.astype(float)
                unstable_sites = int(np.count_nonzero(~np.isfinite(avg_waits)))
                avg_waits[~np.isfinite(avg_waits)] = np.nan
            if avg_waits_peak.size > 0:
                avg_waits_peak = avg_waits_peak.astype(float)
                # peak-wise unstable sites are counted separately if needed
                avg_waits_peak[~np.isfinite(avg_waits_peak)] = np.nan
            if avg_waits_normal.size > 0:
                avg_waits_normal = avg_waits_normal.astype(float)
                avg_waits_normal[~np.isfinite(avg_waits_normal)] = np.nan

            # Find best individual (minimum cost, maximum coverage)
            best_idx = np.argmin(costs)
            best_ind_sites = sites_counts[best_idx]
            
            gen_record = {
                'generation': gen,
                'avg_cost': float(np.nanmean(costs)),
                'best_cost': float(np.nanmin(costs)),
                'avg_coverage': float(np.nanmean(coverages)),
                'best_coverage': float(np.nanmax(coverages)),
                'avg_distance': float(np.nanmean(distances)),
                'best_distance': float(np.nanmin(distances)),
                'avg_sites': float(np.nanmean(sites_counts)),
                'min_sites': int(np.nanmin(sites_counts)),
                'max_sites': int(np.nanmax(sites_counts)),
                'best_sites': int(best_ind_sites),  # NEW: Best individual's station count
                'avg_wait_min': float(np.nanmean(avg_waits)) if avg_waits.size>0 else float('nan'),
                'avg_wait_peak_min': float(np.nanmean(avg_waits_peak)) if avg_waits_peak.size>0 else float('nan'),
                'avg_wait_normal_min': float(np.nanmean(avg_waits_normal)) if avg_waits_normal.size>0 else float('nan'),
                'unstable_sites_count': unstable_sites
            }

            convergence_history.append(gen_record)

        # After evolution, extract Pareto front
        pareto = tools.sortNondominated(population, len(population), first_front_only=True)[0]
        solutions = []
        for ind in pareto:
            cost, neg_cov, avg_d, profit = ind.fitness.values
            solutions.append({'selected_sites': np.array(ind), 'cost': float(cost), 'coverage': float(-neg_cov), 'avg_distance': float(avg_d), 'profit': float(profit), 'n_sites': int(np.sum(ind))})

        return {'pareto_solutions': solutions, 'population': population, 'convergence_history': convergence_history}

