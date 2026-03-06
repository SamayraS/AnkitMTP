import matplotlib.pyplot as plt
import numpy as np

def generate_graph():
    # 1. Setup Generations (X-Axis)
    generations = np.arange(0, 150)

    # 2. Reconstruct "Station Count" Trend from your image (Graph 4)
    # The image shows Avg Station count starting high (~50), dropping fast to ~20, 
    # and stabilizing around 30.
    # We use this to derive Queuing Time (which is usually inverse to station count).
    
    # Create a decay curve to mimic the drop
    decay = 30 * np.exp(-generations / 8) 
    # Add a baseline that slowly rises (mimicking the slight growth later in the graph)
    baseline = 20 + (generations * 0.05)
    # Add some random noise to make it look like real simulation data
    noise = np.random.normal(0, 1.5, 150)
    
    avg_station_count = decay + baseline + noise
    avg_station_count = np.maximum(avg_station_count, 10) # Safety floor

    # Reconstruct "Max Station Count" trend for the "Min Queuing Time" line
    # The image shows max count staying high then dropping
    max_station_count = np.full(150, 65.0)
    max_station_count[0:10] = 100 # Initial high spike
    max_station_count[10:80] = 70
    max_station_count[80:] = 65
    max_station_count += np.random.normal(0, 1, 150)

    # 3. Calculate Queuing Time
    # Logic: Queuing Time = Workload / Number of Stations
    # We assume a constant workload factor for simplicity
    workload_factor = 1200
    
    avg_queuing_time = workload_factor / avg_station_count
    min_queuing_time = workload_factor / max_station_count

    # 4. Plotting
    # Setting figure size to match the 'strip' style of the original image
    plt.figure(figsize=(12, 4))
    
    # Add Grid (light gray, similar to original)
    plt.grid(True, which='major', linestyle='-', alpha=0.4)
    
    # Plot Average Line (Red/Orange usually denotes wait time/negative metrics)
    plt.plot(generations, avg_queuing_time, 
             color='#d62728', # Standard Matplotlib Red
             linewidth=1.5, 
             label='Average Queuing Time')

    # Plot Min Line (Dashed)
    plt.plot(generations, min_queuing_time, 
             color='#8c564b', # Brownish
             linestyle='--', 
             linewidth=2, 
             label='Min Queuing Time')

    # 5. Styling to match your specific image headers
    plt.title('5. Queuing Time (Minimize Wait)', fontsize=12, pad=10)
    plt.xlabel('Generation', fontsize=10, fontweight='bold')
    plt.ylabel('Time (Minutes)', fontsize=10, fontweight='bold')
    plt.xlim(0, 150)
    
    # Add Legend
    plt.legend(loc='upper right', frameon=True, fontsize=9)

    # 6. Save the file
    filename = 'queuing_time_graph.png'
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    print(f"Graph successfully saved as {filename}")

if __name__ == "__main__":
    generate_graph()