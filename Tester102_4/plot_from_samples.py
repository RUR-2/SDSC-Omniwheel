#!/usr/bin/env python3
"""
Plot Trajectory from Manual Sample Data
========================================
Script untuk membuat grafik trajectory dari data sample yang diambil manual.
Dapat membaca dari file CSV atau menggunakan data hardcoded.

Usage:
    python3 plot_from_samples.py                    # Gunakan CSV jika ada
    python3 plot_from_samples.py --hardcoded        # Paksa gunakan data hardcoded

Author: Brone Social Nav Team
Date: 2026-10-04
"""

import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import math
import pandas as pd
from datetime import datetime
import sys
import os

# Proxemic zones (same as main program)
R_INTIMATE = 0.45
R_PERSONAL = 1.20
R_SOCIAL = 3.60

# Sample data from your test
sample_data = [
    # Sample #1
    {
        'sample_id': 1,
        'timestamp': 228.57,
        'position_x': -0.054,
        'position_y': 0.244,
        'velocity_x': -0.217,
        'velocity_y': 0.976,
        'speed': 1.000,
        'zone': 'PUBLIC',
        'num_humans': 1,
        'closest_distance': 3.71,
        'force_x': -0.01,
        'force_y': -0.05,
        'displacement_x': -0.054,
        'displacement_y': 0.244
    },
    # Sample #2
    {
        'sample_id': 2,
        'timestamp': 370.74,
        'position_x': -0.033,
        'position_y': 0.393,
        'velocity_x': 0.083,
        'velocity_y': 0.594,
        'speed': 0.600,
        'zone': 'SOCIAL',
        'num_humans': 1,
        'closest_distance': 3.07,
        'force_x': 0.02,
        'force_y': -0.11,
        'displacement_x': 0.021,
        'displacement_y': 0.149
    },
    # Sample #3
    {
        'sample_id': 3,
        'timestamp': 545.18,
        'position_x': -0.012,
        'position_y': 0.541,
        'velocity_x': 0.086,
        'velocity_y': 0.594,
        'speed': 0.600,
        'zone': 'SOCIAL',
        'num_humans': 1,
        'closest_distance': 2.58,
        'force_x': 0.04,
        'force_y': -0.19,
        'displacement_x': 0.022,
        'displacement_y': 0.148
    },
    # Sample #4
    {
        'sample_id': 4,
        'timestamp': 733.19,
        'position_x': 0.052,
        'position_y': 0.677,
        'velocity_x': 0.254,
        'velocity_y': 0.544,
        'speed': 0.600,
        'zone': 'SOCIAL',
        'num_humans': 1,
        'closest_distance': 1.65,
        'force_x': 0.52,
        'force_y': -0.35,
        'displacement_x': 0.064,
        'displacement_y': 0.136
    },
    # Sample #5
    {
        'sample_id': 5,
        'timestamp': 893.01,
        'position_x': 0.115,
        'position_y': 0.813,
        'velocity_x': 0.254,
        'velocity_y': 0.543,
        'speed': 0.600,
        'zone': 'SOCIAL',
        'num_humans': 1,
        'closest_distance': 1.27,
        'force_x': 0.86,
        'force_y': -0.57,
        'displacement_x': 0.064,
        'displacement_y': 0.136
    },
    # Sample #6
    {
        'sample_id': 6,
        'timestamp': 923.40,
        'position_x': 0.147,
        'position_y': 0.881,
        'velocity_x': 0.127,
        'velocity_y': 0.272,
        'speed': 0.300,
        'zone': 'PERSONAL',
        'num_humans': 1,
        'closest_distance': 0.87,
        'force_x': 1.63,
        'force_y': -0.47,
        'displacement_x': 0.032,
        'displacement_y': 0.068
    },
    # Sample #7
    {
        'sample_id': 7,
        'timestamp': 938.01,
        'position_x': 0.179,
        'position_y': 0.949,
        'velocity_x': 0.126,
        'velocity_y': 0.272,
        'speed': 0.300,
        'zone': 'PERSONAL',
        'num_humans': 1,
        'closest_distance': 0.94,
        'force_x': 1.49,
        'force_y': -0.38,
        'displacement_x': 0.032,
        'displacement_y': 0.068
    },
    # Sample #8
    {
        'sample_id': 8,
        'timestamp': 960.55,
        'position_x': 0.210,
        'position_y': 1.017,
        'velocity_x': 0.126,
        'velocity_y': 0.272,
        'speed': 0.300,
        'zone': 'PERSONAL',
        'num_humans': 1,
        'closest_distance': 0.92,
        'force_x': 1.54,
        'force_y': -0.33,
        'displacement_x': 0.031,
        'displacement_y': 0.068
    },
    # Sample #9
    {
        'sample_id': 9,
        'timestamp': 1004.55,
        'position_x': 0.210,
        'position_y': 1.267,
        'velocity_x': 0.000,
        'velocity_y': 1.000,
        'speed': 1.000,
        'zone': 'PUBLIC',
        'num_humans': 0,
        'closest_distance': float('inf'),
        'force_x': 0.00,
        'force_y': 0.00,
        'displacement_x': 0.000,
        'displacement_y': 0.250
    }
]


def load_data_from_csv(csv_file='sample_data.csv'):
    """Load data from CSV file"""
    if not os.path.exists(csv_file):
        print(f"⚠ CSV file not found: {csv_file}")
        return None
    
    try:
        df = pd.read_csv(csv_file)
        print(f"✓ Loaded CSV: {csv_file}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Rows: {len(df)}")
        
        # Convert DataFrame to sample_data format
        data = []
        for _, row in df.iterrows():
            closest = row['Closest_Distance_m']
            if closest == 'inf' or pd.isna(closest):
                closest = float('inf')
            else:
                closest = float(closest)
            
            data.append({
                'sample_id': int(row['Sample']),
                'timestamp': float(row['Time_s']),
                'position_x': float(row['Position_X_m']),
                'position_y': float(row['Position_Y_m']),
                'velocity_x': float(row['Velocity_X_ms']),
                'velocity_y': float(row['Velocity_Y_ms']),
                'speed': float(row['Speed_ms']),
                'zone': str(row['Zone']),
                'num_humans': int(row['Humans_Count']),
                'closest_distance': closest,
                'force_x': float(row['SFM_Force_X_N']),
                'force_y': float(row['SFM_Force_Y_N']),
                'displacement_x': float(row['Displacement_X_m']),
                'displacement_y': float(row['Displacement_Y_m'])
            })
        
        return data
    except Exception as e:
        print(f"⚠ Error loading CSV: {e}")
        return None


def plot_trajectory_from_data(data):
    """Create comprehensive plots from sample data"""
    print("=" * 70)
    print("Creating Comprehensive Plots from Sample Data")
    print("=" * 70)
    
    # Extract data
    positions_x = [s['position_x'] for s in data]
    positions_y = [s['position_y'] for s in data]
    times = [s['timestamp'] for s in data]
    speeds = [s['speed'] for s in data]
    forces = [math.hypot(s['force_x'], s['force_y']) for s in data]
    num_humans = [s['num_humans'] for s in data]
    
    print(f"\n📊 Data Summary:")
    print(f"   Total samples: {len(data)}")
    print(f"   Time range: {times[0]:.1f}s - {times[-1]:.1f}s")
    print(f"   Position start: ({positions_x[0]:.3f}, {positions_y[0]:.3f}) m")
    print(f"   Position end: ({positions_x[-1]:.3f}, {positions_y[-1]:.3f}) m")
    
    distance = math.hypot(positions_x[-1] - positions_x[0], 
                         positions_y[-1] - positions_y[0])
    print(f"   Distance traveled: {distance:.3f} m")
    
    # Create comprehensive figure with multiple subplots
    fig = plt.figure(figsize=(20, 12))
    
    # ===== Plot 1: Trajectory Map =====
    ax1 = plt.subplot(2, 3, 1)
    ax1.plot(positions_x, positions_y, 'b-', linewidth=2, label='Camera path')
    ax1.plot(positions_x, positions_y, 'bo', markersize=8, alpha=0.6)
    
    # Annotate samples
    for i, (x, y) in enumerate(zip(positions_x, positions_y), 1):
        ax1.annotate(f'{i}', (x, y), textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=9, 
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Start and end markers
    ax1.plot(positions_x[0], positions_y[0], 'go', markersize=15, 
            label='Start', zorder=10)
    ax1.plot(positions_x[-1], positions_y[-1], 'ro', markersize=15, 
            label='End', zorder=10)
    
    # Draw proxemic zones at end position
    last_pos = (positions_x[-1], positions_y[-1])
    circle_intimate = Circle(last_pos, R_INTIMATE, fill=False, edgecolor='r', 
                            linestyle='--', linewidth=2, label='Intimate (0.45m)')
    circle_personal = Circle(last_pos, R_PERSONAL, fill=False, edgecolor='orange', 
                            linestyle='--', linewidth=1.5, label='Personal (1.20m)')
    circle_social = Circle(last_pos, R_SOCIAL, fill=False, edgecolor='yellow', 
                          linestyle='--', linewidth=1, label='Social (3.60m)')
    ax1.add_patch(circle_intimate)
    ax1.add_patch(circle_personal)
    ax1.add_patch(circle_social)
    
    ax1.set_xlabel('X (m) - Right →', fontsize=12)
    ax1.set_ylabel('Y (m) - Forward ↑', fontsize=12)
    ax1.set_title('Camera Trajectory Map', fontsize=14, fontweight='bold')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8, loc='best')
    
    # Add annotation with key stats
    stats_text = f'Samples: {len(data)}\n'
    stats_text += f'Distance: {distance:.2f}m\n'
    stats_text += f'Duration: {times[-1]-times[0]:.1f}s'
    ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # ===== Plot 2: Speed over Time =====
    ax2 = plt.subplot(2, 3, 2)
    times_rel = [t - times[0] for t in times]
    
    colors = {'PUBLIC': 'green', 'SOCIAL': 'yellow', 'PERSONAL': 'orange', 'INTIMATE': 'red'}
    zone_colors = [colors.get(s['zone'], 'gray') for s in data]
    
    ax2.scatter(times_rel, speeds, c=zone_colors, s=100, alpha=0.7, edgecolors='black')
    ax2.plot(times_rel, speeds, 'b--', linewidth=1, alpha=0.5)
    
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Speed (m/s)', fontsize=12)
    ax2.set_title('Speed over Time (colored by Zone)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Add legend for zones
    for zone, color in colors.items():
        ax2.scatter([], [], c=color, s=100, alpha=0.7, edgecolors='black', label=zone)
    ax2.legend(fontsize=8, loc='best')
    
    # ===== Plot 3: SFM Forces =====
    ax3 = plt.subplot(2, 3, 3)
    forces_x = [s['force_x'] for s in data]
    forces_y = [s['force_y'] for s in data]
    force_mag = [math.hypot(fx, fy) for fx, fy in zip(forces_x, forces_y)]
    
    ax3.scatter(times_rel, force_mag, c=zone_colors, s=100, alpha=0.7, edgecolors='black')
    ax3.plot(times_rel, force_mag, 'r--', linewidth=1, alpha=0.5)
    
    ax3.set_xlabel('Time (s)', fontsize=12)
    ax3.set_ylabel('SFM Force Magnitude (N)', fontsize=12)
    ax3.set_title('Social Force Model Forces', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    # ===== Plot 4: Closest Distance to Human =====
    ax4 = plt.subplot(2, 3, 4)
    closest_distances = [s['closest_distance'] for s in data if s['closest_distance'] != float('inf')]
    times_with_humans = [times_rel[i] for i, s in enumerate(data) if s['closest_distance'] != float('inf')]
    
    if closest_distances:
        ax4.plot(times_with_humans, closest_distances, 'go-', linewidth=2, markersize=8)
        
        # Add zone lines
        ax4.axhline(y=R_INTIMATE, color='r', linestyle='--', linewidth=1, label=f'Intimate ({R_INTIMATE}m)')
        ax4.axhline(y=R_PERSONAL, color='orange', linestyle='--', linewidth=1, label=f'Personal ({R_PERSONAL}m)')
        ax4.axhline(y=R_SOCIAL, color='yellow', linestyle='--', linewidth=1, label=f'Social ({R_SOCIAL}m)')
    
    ax4.set_xlabel('Time (s)', fontsize=12)
    ax4.set_ylabel('Distance to Closest Human (m)', fontsize=12)
    ax4.set_title('Proximity to Humans', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=8, loc='best')
    
    # ===== Plot 5: Velocity Vector Field =====
    ax5 = plt.subplot(2, 3, 5)
    velocities_x = [s['velocity_x'] for s in data]
    velocities_y = [s['velocity_y'] for s in data]
    
    # Trajectory with velocity vectors
    ax5.plot(positions_x, positions_y, 'b-', linewidth=1, alpha=0.5)
    ax5.quiver(positions_x, positions_y, velocities_x, velocities_y, 
              speeds, cmap='coolwarm', scale=5, width=0.005, alpha=0.8)
    
    ax5.plot(positions_x[0], positions_y[0], 'go', markersize=12, label='Start')
    ax5.plot(positions_x[-1], positions_y[-1], 'ro', markersize=12, label='End')
    
    ax5.set_xlabel('X (m)', fontsize=12)
    ax5.set_ylabel('Y (m)', fontsize=12)
    ax5.set_title('Velocity Vectors', fontsize=14, fontweight='bold')
    ax5.set_aspect('equal')
    ax5.grid(True, alpha=0.3)
    ax5.legend(fontsize=8, loc='best')
    
    # ===== Plot 6: Force Vector Field =====
    ax6 = plt.subplot(2, 3, 6)
    
    # Trajectory with force vectors
    ax6.plot(positions_x, positions_y, 'b-', linewidth=1, alpha=0.5)
    ax6.quiver(positions_x, positions_y, forces_x, forces_y, 
              force_mag, cmap='Reds', scale=5, width=0.005, alpha=0.8)
    
    ax6.plot(positions_x[0], positions_y[0], 'go', markersize=12, label='Start')
    ax6.plot(positions_x[-1], positions_y[-1], 'ro', markersize=12, label='End')
    
    ax6.set_xlabel('X (m)', fontsize=12)
    ax6.set_ylabel('Y (m)', fontsize=12)
    ax6.set_title('SFM Force Vectors', fontsize=14, fontweight='bold')
    ax6.set_aspect('equal')
    ax6.grid(True, alpha=0.3)
    ax6.legend(fontsize=8, loc='best')
    
    # Add overall title
    fig.suptitle('Social Navigation Analysis - Manual Sampling Test', 
                fontsize=16, fontweight='bold', y=0.995)
    
    plt.tight_layout()
    
    # Save figure
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    figname = f"trajectory_plot_{timestamp_str}.png"
    
    try:
        plt.savefig(figname, dpi=150, bbox_inches='tight')
        print(f"\n✓ Plot saved: {figname}")
    except Exception as e:
        print(f"\n⚠ Could not save plot: {e}")
    
    # Save CSV
    csv_filename = f"trajectory_data_{timestamp_str}.csv"
    try:
        df = pd.DataFrame(data)
        df.to_csv(csv_filename, index=False)
        print(f"✓ CSV saved: {csv_filename}")
    except Exception as e:
        print(f"⚠ Could not save CSV: {e}")
    
    # Display plot
    print("\n📊 Displaying plot...")
    print("   Close the window to exit.")
    print("=" * 70)
    
    try:
        plt.show(block=True)
    except Exception as e:
        print(f"\n⚠ Could not display plot: {e}")
        print("   But the plot file was saved, you can open it manually.")


def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("TRAJECTORY PLOTTER - From Manual Sample Data")
    print("=" * 70)
    
    # Check command line arguments
    use_hardcoded = '--hardcoded' in sys.argv
    
    data = None
    
    # Try to load from CSV first (unless hardcoded is forced)
    if not use_hardcoded:
        csv_file = 'sample_data.csv'
        data = load_data_from_csv(csv_file)
    
    # Fall back to hardcoded data
    if data is None:
        print("\n📋 Using hardcoded sample data")
        data = sample_data
    
    # Generate plots
    plot_trajectory_from_data(data)
    
    print("\n✓ Done!")


if __name__ == '__main__':
    main()
