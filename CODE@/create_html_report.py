"""
Create HTML Summary Report for EVCS Optimization Results

This module creates a comprehensive HTML report with all results,
metrics, and explanations.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def create_html_report(csv_path='optimal_solution.csv', output_path='evcs_report.html'):
    """
    Create comprehensive HTML report from optimization results.
    
    Parameters:
    -----------
    csv_path : str
        Path to optimal_solution.csv
    output_path : str
        Path to save HTML report
    """
    print("Creating HTML summary report...")
    
    # Read solution data
    df = pd.read_csv(csv_path)
    
    # Calculate summary statistics
    total_sites = len(df)
    base_setup_cost = df['setup_cost_inr'].sum() / 1e6  # In millions
    total_investment = df['total_setup_cost_inr'].sum() / 1e6 if 'total_setup_cost_inr' in df.columns else base_setup_cost
    total_coverage = df['coverage_evs'].sum()
    total_profit = df['annual_profit_inr'].sum() / 1e6  # In millions
    avg_density = df['density_per_km2'].mean()
    total_upgrade_cost = df['grid_upgrade_cost_inr'].sum() / 1e6 if 'grid_upgrade_cost_inr' in df.columns else 0.0
    avg_grid_distance = df['distance_to_grid_km'].mean() if 'distance_to_grid_km' in df.columns else np.nan
    if 'grid_capacity_ok' in df.columns:
        grid_ok_series = df['grid_capacity_ok']
        if grid_ok_series.dtype != bool:
            grid_ok_series = grid_ok_series.astype(str).str.lower().isin(['true', '1', 'yes'])
        sites_needing_upgrade = int((~grid_ok_series).sum())
    else:
        sites_needing_upgrade = 0
    
    # Count by category
    category_counts = df['demand_category'].value_counts()
    high_demand = category_counts.get('High', 0)
    medium_demand = category_counts.get('Medium', 0)
    low_demand = category_counts.get('Low', 0)
    very_low_demand = category_counts.get('Very Low', 0)
    
    # Top sites
    top_profit_sites = df.nlargest(10, 'annual_profit_inr')
    top_coverage_sites = df.nlargest(10, 'coverage_evs')
    
    # Create HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EV Charging Station Optimization - Indore City - Results Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .summary-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .summary-box h3 {{
            margin-top: 0;
            color: white;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #3498db;
        }}
        .stat-card h4 {{
            margin: 0;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .stat-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .high-demand {{ background-color: #d5f4e6; }}
        .medium-demand {{ background-color: #dae8fc; }}
        .low-demand {{ background-color: #fff2cc; }}
        .very-low-demand {{ background-color: #f8cecc; }}
        .category-badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-high {{ background-color: #2ecc71; color: white; }}
        .badge-medium {{ background-color: #3498db; color: white; }}
        .badge-low {{ background-color: #f39c12; color: white; }}
        .badge-very-low {{ background-color: #e74c3c; color: white; }}
        .explanation {{
            background-color: #e8f4f8;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ EV Charging Station Optimization - Indore City</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary-box">
            <h3>Executive Summary</h3>
            <p>This report presents the optimal solution for EV charging station placement in Indore city, 
            using hybrid optimization (Benders Decomposition + NSGA-II). The solution balances cost, 
            coverage, and profit to maximize return on investment while serving maximum EV demand.</p>
        </div>
        
        <h2>📊 Overall Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h4>Total Stations</h4>
                <div class="value">{total_sites}</div>
            </div>
            <div class="stat-card">
                <h4>Base Setup Cost</h4>
                <div class="value">₹{base_setup_cost:.2f}M</div>
            </div>
            <div class="stat-card">
                <h4>Total Investment</h4>
                <div class="value">₹{total_investment:.2f}M</div>
                <p style="font-size: 12px; color: #7f8c8d;">Base + upgrades</p>
            </div>
            <div class="stat-card">
                <h4>Total Coverage</h4>
                <div class="value">{total_coverage:.1f} EVs</div>
            </div>
            <div class="stat-card">
                <h4>Total Annual Profit</h4>
                <div class="value">₹{total_profit:.2f}M</div>
            </div>
            <div class="stat-card">
                <h4>Average Density</h4>
                <div class="value">{avg_density:.2f}/km²</div>
            </div>
            <div class="stat-card">
                <h4>ROI</h4>
                <div class="value">{(total_profit/total_investment*100 if total_investment else 0):.1f}%</div>
            </div>
            <div class="stat-card">
                <h4>Total Upgrade Cost</h4>
                <div class="value">₹{total_upgrade_cost:.2f}M</div>
                <p style="font-size: 12px; color: #7f8c8d;">Distribution upgrades</p>
            </div>
            <div class="stat-card">
                <h4>Sites Needing Upgrade</h4>
                <div class="value">{sites_needing_upgrade}</div>
                <p style="font-size: 12px; color: #7f8c8d;">Grid reinforcement required</p>
            </div>
            <div class="stat-card">
                <h4>Avg Grid Distance</h4>
                <div class="value">{avg_grid_distance:.2f} km</div>
                <p style="font-size: 12px; color: #7f8c8d;">Site to nearest node</p>
            </div>
        </div>
        
        <h2>📈 Sites by Demand Category</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h4>High Demand</h4>
                <div class="value">{high_demand}</div>
                <p style="font-size: 12px; color: #7f8c8d;">≥100 EVs coverage</p>
            </div>
            <div class="stat-card">
                <h4>Medium Demand</h4>
                <div class="value">{medium_demand}</div>
                <p style="font-size: 12px; color: #7f8c8d;">50-99 EVs coverage</p>
            </div>
            <div class="stat-card">
                <h4>Low Demand</h4>
                <div class="value">{low_demand}</div>
                <p style="font-size: 12px; color: #7f8c8d;">1-49 EVs coverage</p>
            </div>
            <div class="stat-card">
                <h4>Very Low Demand</h4>
                <div class="value">{very_low_demand}</div>
                <p style="font-size: 12px; color: #7f8c8d;">0 EVs (strategic)</p>
            </div>
        </div>
        
        <h2>🏆 Top 10 Most Profitable Sites</h2>
        <table>
            <thead>
                <tr>
                    <th>Site ID</th>
                    <th>Location</th>
                    <th>Demand Category</th>
                    <th>Coverage (EVs)</th>
                    <th>Density (/km²)</th>
                    <th>Annual Profit (₹)</th>
                    <th>Price (₹/kWh)</th>
                    <th>Setup Cost (₹)</th>
                    <th>Nearest Grid</th>
                    <th>Voltage (kV)</th>
                    <th>Avail (kW)</th>
                    <th>Need (kW)</th>
                    <th>Upgrade (₹)</th>
                    <th>Grid Dist (km)</th>
                    <th>Grid OK?</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for idx, row in top_profit_sites.iterrows():
        category_class = f"{row['demand_category'].lower().replace(' ', '-')}-demand"
        badge_class = f"badge-{row['demand_category'].lower().replace(' ', '-')}"
        html_content += f"""
                <tr class="{category_class}">
                    <td><strong>{int(row['site_id'])}</strong></td>
                    <td>{row['location_name'] if pd.notna(row['location_name']) else 'N/A'}</td>
                    <td><span class="category-badge {badge_class}">{row['demand_category']}</span></td>
                    <td>{row['coverage_evs']:.1f}</td>
                    <td>{row['density_per_km2']:.2f}</td>
                    <td><strong>₹{row['annual_profit_inr']:,.0f}</strong></td>
                    <td>₹{row['price_per_kwh_inr']:.2f}</td>
                    <td>₹{row['setup_cost_inr']:,.0f}</td>
                    <td>{row.get('nearest_grid_name', 'N/A')}</td>
                    <td>{row.get('grid_voltage_kv', float('nan')):.1f}</td>
                    <td>{row.get('grid_available_kw', 0.0):.0f}</td>
                    <td>{row.get('grid_required_kw', 0.0):.0f}</td>
                    <td>₹{row.get('grid_upgrade_cost_inr', 0.0):,.0f}</td>
                    <td>{row.get('distance_to_grid_km', float('nan')):.2f}</td>
                    <td>{'Yes' if str(row.get('grid_capacity_ok', 'True')).lower() in ['true', '1', 'yes'] else 'No'}</td>
                </tr>
"""
    
    html_content += """
            </tbody>
        </table>
        
        <h2>📊 Top 10 Sites by Coverage</h2>
        <table>
            <thead>
                <tr>
                    <th>Site ID</th>
                    <th>Location</th>
                    <th>Demand Category</th>
                    <th>Coverage (EVs)</th>
                    <th>Density (/km²)</th>
                    <th>Annual Profit (₹)</th>
                    <th>Price (₹/kWh)</th>
                    <th>Nearest Grid</th>
                    <th>Voltage (kV)</th>
                    <th>Avail (kW)</th>
                    <th>Need (kW)</th>
                    <th>Upgrade (₹)</th>
                    <th>Grid Dist (km)</th>
                    <th>Grid OK?</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for idx, row in top_coverage_sites.iterrows():
        category_class = f"{row['demand_category'].lower().replace(' ', '-')}-demand"
        badge_class = f"badge-{row['demand_category'].lower().replace(' ', '-')}"
        html_content += f"""
                <tr class="{category_class}">
                    <td><strong>{int(row['site_id'])}</strong></td>
                    <td>{row['location_name'] if pd.notna(row['location_name']) else 'N/A'}</td>
                    <td><span class="category-badge {badge_class}">{row['demand_category']}</span></td>
                    <td><strong>{row['coverage_evs']:.1f}</strong></td>
                    <td>{row['density_per_km2']:.2f}</td>
                    <td>₹{row['annual_profit_inr']:,.0f}</td>
                    <td>₹{row['price_per_kwh_inr']:.2f}</td>
                    <td>{row.get('nearest_grid_name', 'N/A')}</td>
                    <td>{row.get('grid_voltage_kv', float('nan')):.1f}</td>
                    <td>{row.get('grid_available_kw', 0.0):.0f}</td>
                    <td>{row.get('grid_required_kw', 0.0):.0f}</td>
                    <td>₹{row.get('grid_upgrade_cost_inr', 0.0):,.0f}</td>
                    <td>{row.get('distance_to_grid_km', float('nan')):.2f}</td>
                    <td>{'Yes' if str(row.get('grid_capacity_ok', 'True')).lower() in ['true', '1', 'yes'] else 'No'}</td>
                </tr>
"""
    
    html_content += f"""
            </tbody>
        </table>
        
        <h2>📋 Complete Site List</h2>
        <p>All {total_sites} selected charging stations with full details:</p>
        <table>
            <thead>
                <tr>
                    <th>Site ID</th>
                    <th>Location Name</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                    <th>Demand Category</th>
                    <th>Coverage (EVs)</th>
                    <th>Density (/km²)</th>
                    <th>Annual Profit (₹)</th>
                    <th>Price (₹/kWh)</th>
                    <th>Capacity</th>
                    <th>Setup Cost (₹)</th>
                    <th>Total Setup (₹)</th>
                    <th>Nearest Grid</th>
                    <th>Voltage (kV)</th>
                    <th>Avail (kW)</th>
                    <th>Need (kW)</th>
                    <th>Upgrade (₹)</th>
                    <th>Grid Dist (km)</th>
                    <th>Grid OK?</th>
                    <th>Site Type</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for idx, row in df.iterrows():
        category_class = f"{row['demand_category'].lower().replace(' ', '-')}-demand"
        badge_class = f"badge-{row['demand_category'].lower().replace(' ', '-')}"
        location_name = row['location_name'] if pd.notna(row['location_name']) and row['location_name'] != '' else 'N/A'
        html_content += f"""
                <tr class="{category_class}">
                    <td>{int(row['site_id'])}</td>
                    <td>{location_name}</td>
                    <td>{row['latitude']:.4f}</td>
                    <td>{row['longitude']:.4f}</td>
                    <td><span class="category-badge {badge_class}">{row['demand_category']}</span></td>
                    <td>{row['coverage_evs']:.1f}</td>
                    <td>{row['density_per_km2']:.2f}</td>
                    <td>₹{row['annual_profit_inr']:,.0f}</td>
                    <td>₹{row['price_per_kwh_inr']:.2f}</td>
                    <td>{int(row['capacity_charging_points'])}</td>
                    <td>₹{row['setup_cost_inr']:,.0f}</td>
                    <td>₹{row.get('total_setup_cost_inr', row['setup_cost_inr']):,.0f}</td>
                    <td>{row.get('nearest_grid_name', 'N/A')}</td>
                    <td>{row.get('grid_voltage_kv', float('nan')):.1f}</td>
                    <td>{row.get('grid_available_kw', 0.0):.0f}</td>
                    <td>{row.get('grid_required_kw', 0.0):.0f}</td>
                    <td>₹{row.get('grid_upgrade_cost_inr', 0.0):,.0f}</td>
                    <td>{row.get('distance_to_grid_km', float('nan')):.2f}</td>
                    <td>{'Yes' if str(row.get('grid_capacity_ok', 'True')).lower() in ['true', '1', 'yes'] else 'No'}</td>
                    <td>{row['site_type']}</td>
                </tr>
"""
    
    html_content += f"""
            </tbody>
        </table>
        
        <h2>📖 Understanding the Metrics</h2>
        
        <div class="explanation">
            <h3>Coverage (EVs)</h3>
            <p><strong>Definition:</strong> Total number of electric vehicles within 5km service radius of the charging station.</p>
            <p><strong>Calculation:</strong> Sum of all demand zone EVs within 5km distance. If a zone has zero demand but has population data, 
            we estimate demand = population × EV density (typically 2-5% adoption rate).</p>
            <p><strong>Interpretation:</strong> Higher coverage means more potential customers. Sites with ≥100 EVs coverage are "High Demand" 
            and typically most profitable.</p>
        </div>
        
        <div class="explanation">
            <h3>Density (EVs/km²)</h3>
            <p><strong>Definition:</strong> Average electric vehicle density in the coverage area (5km radius circle).</p>
            <p><strong>Calculation:</strong> Density = Total Coverage / (π × 5²) = Coverage / 78.54 km²</p>
            <p><strong>Interpretation:</strong> Higher density means more concentrated demand. Density >5 EVs/km² indicates 
            high-demand areas where stations are likely to be busy and profitable.</p>
        </div>
        
        <div class="explanation">
            <h3>Annual Profit (₹)</h3>
            <p><strong>Definition:</strong> Expected annual profit from operating the charging station.</p>
            <p><strong>Calculation Steps:</strong></p>
            <ol>
                <li><strong>Utilization Rate:</strong> Percentage of EVs in coverage area that actually use the station (20-50% based on coverage)</li>
                <li><strong>Served EVs:</strong> Coverage × Utilization Rate</li>
                <li><strong>Monthly Revenue:</strong> Served EVs × 150 kWh/month × Price per kWh</li>
                <li><strong>Monthly Cost:</strong> (Served EVs × 150 kWh × ₹4/kWh) + ₹5,000 maintenance</li>
                <li><strong>Monthly Profit:</strong> Revenue - Cost</li>
                <li><strong>Annual Profit:</strong> Monthly Profit × 12</li>
            </ol>
            <p><strong>Assumptions:</strong> Average EV charges 12 times/month, 12.5 kWh per session (150 kWh/month total). 
            Electricity cost ₹4/kWh, fixed maintenance ₹5,000/month.</p>
            <p><strong>Interpretation:</strong> Positive profit = viable station. Higher profit = better investment. 
            Check ROI = (Annual Profit / Setup Cost) × 100%.</p>
        </div>
        
        <div class="explanation">
            <h3>Price (₹/kWh)</h3>
            <p><strong>Definition:</strong> Charging price per kilowatt-hour set by the optimization algorithm.</p>
            <p><strong>Calculation:</strong> Base price (₹10) + adjustment based on demand density. Higher demand areas can 
            support higher prices (up to ₹13/kWh).</p>
            <p><strong>Interpretation:</strong> Price balances demand (lower price = more customers) and revenue (higher price = more profit). 
            Most sites cluster around ₹10-10.2/kWh, which is competitive in the Indian market.</p>
        </div>
        
        <div class="explanation">
            <h3>Demand Category</h3>
            <p><strong>Categories:</strong></p>
            <ul>
                <li><strong>High:</strong> ≥100 EVs coverage - Most profitable, high demand, best locations</li>
                <li><strong>Medium:</strong> 50-99 EVs coverage - Good profitability, moderate demand</li>
                <li><strong>Low:</strong> 1-49 EVs coverage - Lower profitability, but still viable</li>
                <li><strong>Very Low:</strong> 0 EVs coverage - Strategic locations for connectivity or future growth</li>
            </ul>
            <p><strong>Interpretation:</strong> Focus on High and Medium demand sites for immediate profitability. 
            Very Low sites may be selected for network connectivity or future expansion.</p>
        </div>
        
        <h2>🎯 Key Insights</h2>
        <div class="explanation">
            <h3>What the Results Tell Us</h3>
            <ul>
                <li><strong>Total Investment:</strong> ₹{total_investment:.2f} million to set up {total_sites} charging stations</li>
                <li><strong>Market Coverage:</strong> {total_coverage:.0f} EVs can be served (within 5km of a station)</li>
                <li><strong>Expected Returns:</strong> ₹{total_profit:.2f} million annual profit = {(total_profit/total_investment*100 if total_investment else 0):.1f}% ROI</li>
                <li><strong>Best Locations:</strong> {high_demand} high-demand sites provide the best returns</li>
                <li><strong>Strategic Sites:</strong> {very_low_demand} very low demand sites selected for network connectivity</li>
            </ul>
        </div>
        
        <div class="explanation">
            <h3>Recommendations</h3>
            <ol>
                <li><strong>Priority Sites:</strong> Focus on High and Medium demand sites first - they provide best ROI</li>
                <li><strong>Pricing Strategy:</strong> Current prices (₹10-10.2/kWh) are competitive and balanced</li>
                <li><strong>Network Coverage:</strong> Stations are well-distributed across Indore, ensuring good coverage</li>
                <li><strong>Grid Upgrades:</strong> Plan ₹{total_upgrade_cost:.2f}M for distribution reinforcement across {sites_needing_upgrade} constrained sites</li>
                <li><strong>Future Expansion:</strong> Very Low demand sites can be built later for network completeness</li>
            </ol>
        </div>
        
        <h2>📁 Related Files</h2>
        <ul>
            <li><strong>evcs_map.png:</strong> Visual map showing all stations with labels</li>
            <li><strong>objectives_tradeoff.png:</strong> Pareto front showing cost/coverage/profit trade-offs</li>
            <li><strong>solution_summary.png:</strong> Statistical dashboard with key metrics</li>
            <li><strong>optimal_solution.csv:</strong> Complete data in CSV format (this report is generated from it)</li>
        </ul>
        
        <div class="footer">
            <p><strong>EV Charging Station Optimization - Indore City</strong></p>
            <p>Hybrid Approach: Benders Decomposition + NSGA-II</p>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"[OK] HTML report saved to {output_path}")

