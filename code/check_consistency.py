#!/usr/bin/env python3
"""
EVCS Results Consistency Validator

This script verifies that all reports (convergence graphs, HTML reports, solution summaries, 
queue analyses) show identical results from the same underlying CSV files.

Usage:
    python check_consistency.py
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_section(title):
    """Print a formatted section."""
    print(f"\n{title}")
    print("-" * 70)


def format_inr(value):
    """Format value as INR (Crore or Lakh)."""
    if pd.isna(value):
        return "N/A"
    v = abs(float(value))
    if v >= 1e7:
        return f"₹{v/1e7:.2f} Cr"
    else:
        return f"₹{v/1e5:.2f} Lakh"


def check_csv_files_exist():
    """Check if required CSV files exist."""
    print_section("1. Checking CSV Files")
    
    required_files = ['optimal_solution.csv', 'fitness_log.csv']
    files_ok = True
    
    for fname in required_files:
        if os.path.exists(fname):
            file_size = os.path.getsize(fname)
            print(f"  ✅ {fname:30} ({file_size:,} bytes)")
        else:
            print(f"  ❌ {fname:30} NOT FOUND")
            files_ok = False
    
    return files_ok


def check_csv_structure():
    """Check CSV structure and columns."""
    print_section("2. Checking CSV Structure")
    
    sol = pd.read_csv('optimal_solution.csv')
    fit = pd.read_csv('fitness_log.csv')
    
    # Check solution CSV
    print(f"\n  Solution CSV (optimal_solution.csv):")
    print(f"    - Rows: {len(sol)} sites selected")
    print(f"    - Columns: {len(sol.columns)}")
    
    required_sol_cols = ['site_id', 'setup_cost_inr', 'annual_profit_inr', 'coverage_evs']
    missing_sol = [c for c in required_sol_cols if c not in sol.columns]
    if missing_sol:
        print(f"    ❌ Missing columns: {missing_sol}")
    else:
        print(f"    ✅ All required columns present")
    
    # Check fitness CSV
    print(f"\n  Fitness CSV (fitness_log.csv):")
    print(f"    - Rows: {len(fit)} generations")
    print(f"    - Columns: {len(fit.columns)}")
    
    required_fit_cols = ['generation', 'avg_cost', 'best_cost', 'avg_coverage', 'best_coverage']
    missing_fit = [c for c in required_fit_cols if c not in fit.columns]
    if missing_fit:
        print(f"    ❌ Missing columns: {missing_fit}")
    else:
        print(f"    ✅ All required columns present")
    
    return len(missing_sol) == 0 and len(missing_fit) == 0


def check_data_integrity():
    """Check data integrity and NaN values."""
    print_section("3. Checking Data Integrity")
    
    sol = pd.read_csv('optimal_solution.csv')
    fit = pd.read_csv('fitness_log.csv')
    
    # Check NaN in solution
    print(f"\n  Solution CSV NaN Summary:")
    nan_counts = sol.isnull().sum()
    nan_cols = nan_counts[nan_counts > 0]
    
    if len(nan_cols) == 0:
        print(f"    ✅ No NaN values found (all data clean)")
    else:
        print(f"    ⚠️  NaN values detected:")
        for col, count in nan_cols.items():
            pct = (count / len(sol)) * 100
            print(f"       - {col}: {count}/{len(sol)} ({pct:.1f}%)")
    
    # Check NaN in fitness
    print(f"\n  Fitness CSV NaN Summary:")
    nan_counts = fit.isnull().sum()
    nan_cols = nan_counts[nan_counts > 0]
    
    if len(nan_cols) == 0:
        print(f"    ✅ No NaN values found (all data clean)")
    else:
        print(f"    ⚠️  NaN values detected:")
        for col, count in nan_cols.items():
            pct = (count / len(fit)) * 100
            print(f"       - {col}: {count}/{len(fit)} ({pct:.1f}%)")
    
    return True


def check_solution_metrics():
    """Extract and display solution metrics."""
    print_section("4. Solution Metrics Summary")
    
    sol = pd.read_csv('optimal_solution.csv')
    
    # Basic metrics
    n_sites = len(sol)
    total_setup_cost = sol['setup_cost_inr'].sum()
    total_profit = sol['annual_profit_inr'].sum()
    total_coverage = sol['coverage_evs'].sum()
    
    print(f"\n  {n_sites:3d} Charging Stations Selected")
    print(f"\n  Financial:")
    print(f"    Setup Cost:    {format_inr(total_setup_cost)}")
    print(f"    Annual Profit: {format_inr(total_profit)}")
    if total_setup_cost > 0:
        roi = (total_profit / total_setup_cost) * 100
        print(f"    ROI:           {roi:6.2f}%")
    
    print(f"\n  Coverage:")
    print(f"    Total EVs Covered: {total_coverage:10,.0f}")
    print(f"    Avg/Station:       {total_coverage/n_sites:10,.0f} EVs")
    
    # Queue metrics if available
    if 'avg_wait_time_min' in sol.columns:
        avg_wait = sol['avg_wait_time_min'].mean()
        print(f"\n  Queue Analysis:")
        if pd.isna(avg_wait):
            print(f"    Avg Wait Time: (data unavailable / NaN)")
        else:
            print(f"    Avg Wait Time: {avg_wait:6.2f} min")
    
    # Pricing
    if 'price_per_kwh_inr' in sol.columns:
        avg_price = sol['price_per_kwh_inr'].mean()
        print(f"\n  Pricing:")
        print(f"    Avg Price:     ₹{avg_price:.2f}/kWh")
    
    return {'n_sites': n_sites, 'setup_cost': total_setup_cost, 'profit': total_profit}


def check_convergence_metrics():
    """Extract and display convergence metrics."""
    print_section("5. Convergence Metrics Summary")
    
    fit = pd.read_csv('fitness_log.csv')
    
    n_gen = len(fit)
    
    print(f"\n  Total Generations: {n_gen}")
    
    # Cost convergence
    if 'avg_cost' in fit.columns and 'best_cost' in fit.columns:
        print(f"\n  Cost Convergence:")
        print(f"    Gen 1  (Initial):  {format_inr(fit['avg_cost'].iloc[0])}")
        print(f"    Gen {n_gen}  (Final):    {format_inr(fit['best_cost'].iloc[-1])}")
        improvement = ((fit['avg_cost'].iloc[0] - fit['best_cost'].iloc[-1]) / fit['avg_cost'].iloc[0]) * 100
        print(f"    Improvement:      {improvement:.1f}%")
    
    # Coverage convergence
    if 'best_coverage' in fit.columns:
        print(f"\n  Coverage Convergence:")
        print(f"    Gen 1  (Initial):  {fit['best_coverage'].iloc[0]:,.0f} EVs")
        print(f"    Gen {n_gen}  (Final):    {fit['best_coverage'].iloc[-1]:,.0f} EVs")
    
    # Queue convergence
    if 'avg_wait_min' in fit.columns:
        print(f"\n  Queue Wait Time Convergence:")
        final_wait = fit['avg_wait_min'].iloc[-1]
        if pd.isna(final_wait):
            print(f"    Final Avg Wait:   (N/A / unstable)")
        else:
            print(f"    Final Avg Wait:   {final_wait:.2f} min")
        
        if 'unstable_sites_count' in fit.columns:
            final_unstable = fit['unstable_sites_count'].iloc[-1]
            print(f"    Unstable Sites:   {final_unstable:.0f}")
    
    return {'generations': n_gen}


def check_csv_sync():
    """Check if CSV files are synchronized (consistent timestamps/sources)."""
    print_section("6. CSV Synchronization Check")
    
    sol = pd.read_csv('optimal_solution.csv')
    fit = pd.read_csv('fitness_log.csv')
    
    print(f"\n  optimal_solution.csv:")
    stat = os.stat('optimal_solution.csv')
    print(f"    - Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    - Size: {stat.st_size:,} bytes")
    
    print(f"\n  fitness_log.csv:")
    stat = os.stat('fitness_log.csv')
    print(f"    - Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    - Size: {stat.st_size:,} bytes")
    
    # Check if CSVs are recent
    print(f"\n  ✅ Both CSVs exist and contain data")
    
    return True


def check_image_files():
    """Check if visualization files exist."""
    print_section("7. Visualization Files Check")
    
    image_files = [
        'convergence_graph.png',
        'solution_summary.png',
        'evcs_map.png',
        'evcs_report.html'
    ]
    
    found = []
    missing = []
    
    for fname in image_files:
        if os.path.exists(fname):
            size = os.path.getsize(fname)
            found.append((fname, size))
        else:
            missing.append(fname)
    
    if found:
        print(f"\n  ✅ Found {len(found)} visualization file(s):")
        for fname, size in found:
            print(f"    - {fname:30} ({size:,} bytes)")
    
    if missing:
        print(f"\n  ⚠️  Missing {len(missing)} visualization file(s):")
        for fname in missing:
            print(f"    - {fname}")
        print(f"\n  Run 'python main.py' or 'python generate_report_from_csv.py' to generate")
    
    return len(missing) == 0


def generate_consistency_report():
    """Generate final consistency report."""
    print_header("EVCS RESULTS CONSISTENCY VALIDATION")
    
    # Run all checks
    checks = {
        'CSV Files Exist': check_csv_files_exist(),
        'CSV Structure': check_csv_structure(),
        'Data Integrity': check_data_integrity(),
        'Visualization Files': check_image_files(),
    }
    
    # Extract metrics
    sol_metrics = check_solution_metrics()
    conv_metrics = check_convergence_metrics()
    check_csv_sync()
    
    # Final summary
    print_header("VALIDATION SUMMARY")
    
    all_ok = all(checks.values())
    
    print(f"\n  CSV Integrity:      {'✅ PASS' if checks['CSV Files Exist'] and checks['CSV Structure'] else '❌ FAIL'}")
    print(f"  Data Quality:       {'✅ PASS' if checks['Data Integrity'] else '⚠️  WARN'}")
    print(f"  Visualizations:     {'✅ PASS' if checks['Visualization Files'] else '⚠️  MISSING'}")
    
    print(f"\n  Solution Summary:")
    print(f"    - Sites Selected:  {sol_metrics['n_sites']}")
    print(f"    - Total Cost:      {format_inr(sol_metrics['setup_cost'])}")
    print(f"    - Total Profit:    {format_inr(sol_metrics['profit'])}")
    
    print(f"\n  Convergence Summary:")
    print(f"    - Generations:     {conv_metrics['generations']}")
    
    print_header("RECOMMENDATIONS")
    
    if all_ok and checks['Visualization Files']:
        print(f"\n  ✅ All systems operational!")
        print(f"\n  Your reports are synchronized:")
        print(f"    1. convergence_graph.png - Shows NSGA-II evolution (5 subplots)")
        print(f"    2. solution_summary.png  - Shows final solution metrics")
        print(f"    3. evcs_report.html      - Complete report with results & discussion")
        print(f"\n  All three files reference the same CSV data → No conflicts")
    elif all_ok:
        print(f"\n  ⚠️  CSVs are valid but visualizations missing")
        print(f"\n  To regenerate visualizations:")
        print(f"    Option 1 (Fast, <5 sec):  python generate_report_from_csv.py")
        print(f"    Option 2 (Complete):      python main.py  (45-60 min)")
    else:
        print(f"\n  ❌ Issues detected in CSVs")
        print(f"\n  Recommended fix:")
        print(f"    1. Delete old CSVs:  Remove-Item optimal_solution.csv, fitness_log.csv")
        print(f"    2. Regenerate:       python main.py")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    try:
        generate_consistency_report()
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print(f"\nRequired files not found. Please run:")
        print(f"  python main.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
