#!/usr/bin/env python3
"""
Visualize Sample Data from CSV
================================
Script untuk membuat berbagai visualisasi dari file sample_data.csv

Usage:
    python visualize_csv.py

Requirements:
    - pandas
    - matplotlib
    - numpy

Author: Brone Social Nav Team
Date: 2026-10-06
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
import numpy as np
import math
import os
from datetime import datetime


# Proxemic zones
R_INTIMATE = 0.45
R_PERSONAL = 1.20
R_SOCIAL = 3.60


def load_csv(filename='sample_data.csv'):
    """Load sample data from CSV"""
    if not os.path.exists(filename):
        print(f"❌ Error: File '{filename}' not found!")
        return None
    
    try:
        df = pd.read_csv(filename)
        print(f"✓ Loaded: {filename}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return None


def create_comprehensive_plots(df):
    """Create comprehensive visualization dashboard"""
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('Social Navigation Analysis Dashboard', 
                 fontsize=18, fontweight='bold', y=0.995)
    
    # Zone color mapping
    zone_colors = {'PUBLIC': 'green', 'SOCIAL': 'yellow', 
                   'PERSONAL': 'orange', 'INTIMATE': 'red'}
    
    # ========== Plot 1: Trajectory Map ==========
    ax1 = plt.subplot(2, 3, 1)
    
    x = df['Position_X_m']
    y = df['Position_Y_m']
    
    # Plot trajectory
    ax1.plot(x, y, 'b-', linewidth=2.5, alpha=0.7, label='Robot Path')
    
    # Plot points colored by zone
    for zone in zone_colors:
        mask = df['Zone'] == zone
        if mask.any():
            ax1.scatter(x[mask], y[mask], c=zone_colors[zone], 
                       s=150, alpha=0.8, edgecolors='black', linewidth=1.5,
                       label=f'{zone} zone')
    
    # Annotate sample numbers
    for idx, row in df.iterrows():
        ax1.annotate(f"{row['Sample']}", 
                    (row['Position_X_m'], row['Position_Y_m']),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='circle,pad=0.3', 
                             facecolor='white', alpha=0.8))
    
    # Start and end markers
    ax1.scatter(x.iloc[0], y.iloc[0], c='lime', s=300, 
               marker='o', edgecolors='darkgreen', linewidth=2, 
               label='Start', zorder=100)
    ax1.scatter(x.iloc[-1], y.iloc[-1], c='red', s=300, 
               marker='X', edgecolors='darkred', linewidth=2,
               label='End', zorder=100)
    
    # Draw proxemic zones at final position
    final_pos = (x.iloc[-1], y.iloc[-1])
    for radius, color, label in [(R_INTIMATE, 'red', 'Intimate'),
                                  (R_PERSONAL, 'orange', 'Personal'),
                                  (R_SOCIAL, 'yellow', 'Social')]:
        circle = Circle(final_pos, radius, fill=False, 
                       edgecolor=color, linestyle='--', linewidth=1.5)
        ax1.add_patch(circle)
    
    ax1.set_xlabel('X Position (m) →', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Y Position (m) →', fontsize=12, fontweight='bold')
    ax1.set_title('Robot Trajectory Map', fontsize=14, fontweight='bold')
    ax1.set_aspect('equal', adjustable='box')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(fontsize=9, loc='best', framealpha=0.9)
    
    # ========== Plot 2: Speed Over Time ==========
    ax2 = plt.subplot(2, 3, 2)
    
    time = df['Time_s']
    speed = df['Speed_ms']
    
    # Plot speed line
    ax2.plot(time, speed, 'b-', linewidth=2.5, label='Speed')
    ax2.fill_between(time, 0, speed, alpha=0.3, color='blue')
    
    # Color zones as background
    for i in range(len(df)):
        zone = df.iloc[i]['Zone']
        t_start = df.iloc[i]['Time_s']
        t_end = df.iloc[i+1]['Time_s'] if i < len(df)-1 else t_start + 50
        ax2.axvspan(t_start, t_end, alpha=0.2, 
                   color=zone_colors.get(zone, 'gray'))
    
    ax2.scatter(time, speed, c=[zone_colors[z] for z in df['Zone']], 
               s=100, edgecolors='black', linewidth=1, zorder=10)
    
    ax2.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Speed (m/s)', fontsize=12, fontweight='bold')
    ax2.set_title('Speed Over Time', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.legend(fontsize=9)
    
    # ========== Plot 3: Distance to Closest Human ==========
    ax3 = plt.subplot(2, 3, 3)
    
    # Filter out infinite values
    df_humans = df[df['Closest_Distance_m'] != np.inf].copy()
    
    if not df_humans.empty:
        ax3.plot(df_humans['Time_s'], df_humans['Closest_Distance_m'], 
                'go-', linewidth=2.5, markersize=8, label='Distance to Human')
        
        # Zone boundaries
        ax3.axhline(y=R_INTIMATE, color='red', linestyle='--', 
                   linewidth=2, label=f'Intimate ({R_INTIMATE}m)')
        ax3.axhline(y=R_PERSONAL, color='orange', linestyle='--', 
                   linewidth=2, label=f'Personal ({R_PERSONAL}m)')
        ax3.axhline(y=R_SOCIAL, color='yellow', linestyle='--', 
                   linewidth=2, label=f'Social ({R_SOCIAL}m)')
        
        # Fill zones
        ax3.fill_between([df_humans['Time_s'].min(), df_humans['Time_s'].max()], 
                        0, R_INTIMATE, alpha=0.2, color='red')
        ax3.fill_between([df_humans['Time_s'].min(), df_humans['Time_s'].max()], 
                        R_INTIMATE, R_PERSONAL, alpha=0.2, color='orange')
        ax3.fill_between([df_humans['Time_s'].min(), df_humans['Time_s'].max()], 
                        R_PERSONAL, R_SOCIAL, alpha=0.2, color='yellow')
    
    ax3.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Distance (m)', fontsize=12, fontweight='bold')
    ax3.set_title('Proximity to Humans', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, linestyle='--')
    ax3.legend(fontsize=9, loc='best')
    
    # ========== Plot 4: SFM Forces ==========
    ax4 = plt.subplot(2, 3, 4)
    
    # Calculate force magnitude
    force_mag = np.sqrt(df['SFM_Force_X_N']**2 + df['SFM_Force_Y_N']**2)
    
    ax4.plot(time, force_mag, 'r-', linewidth=2.5, label='Force Magnitude')
    ax4.fill_between(time, 0, force_mag, alpha=0.3, color='red')
    ax4.scatter(time, force_mag, c=[zone_colors[z] for z in df['Zone']], 
               s=100, edgecolors='black', linewidth=1, zorder=10)
    
    ax4.set_xlabel('Time (s)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Force (N)', fontsize=12, fontweight='bold')
    ax4.set_title('Social Force Model Forces', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, linestyle='--')
    ax4.legend(fontsize=9)
    
    # ========== Plot 5: Velocity Vector Field ==========
    ax5 = plt.subplot(2, 3, 5)
    
    # Plot trajectory
    ax5.plot(x, y, 'b-', linewidth=1.5, alpha=0.5)
    
    # Velocity vectors
    speed_normalized = df['Speed_ms']
    quiver = ax5.quiver(x, y, df['Velocity_X_ms'], df['Velocity_Y_ms'],
                       speed_normalized, cmap='coolwarm', 
                       scale=6, width=0.006, alpha=0.9)
    
    # Start/end markers
    ax5.scatter(x.iloc[0], y.iloc[0], c='lime', s=200, 
               marker='o', edgecolors='darkgreen', linewidth=2, zorder=100)
    ax5.scatter(x.iloc[-1], y.iloc[-1], c='red', s=200, 
               marker='X', edgecolors='darkred', linewidth=2, zorder=100)
    
    ax5.set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
    ax5.set_title('Velocity Vectors', fontsize=14, fontweight='bold')
    ax5.set_aspect('equal', adjustable='box')
    ax5.grid(True, alpha=0.3, linestyle='--')
    plt.colorbar(quiver, ax=ax5, label='Speed (m/s)')
    
    # ========== Plot 6: Force Vector Field ==========
    ax6 = plt.subplot(2, 3, 6)
    
    # Plot trajectory
    ax6.plot(x, y, 'b-', linewidth=1.5, alpha=0.5)
    
    # Force vectors
    quiver2 = ax6.quiver(x, y, df['SFM_Force_X_N'], df['SFM_Force_Y_N'],
                        force_mag, cmap='Reds', 
                        scale=6, width=0.006, alpha=0.9)
    
    # Start/end markers
    ax6.scatter(x.iloc[0], y.iloc[0], c='lime', s=200, 
               marker='o', edgecolors='darkgreen', linewidth=2, zorder=100)
    ax6.scatter(x.iloc[-1], y.iloc[-1], c='red', s=200, 
               marker='X', edgecolors='darkred', linewidth=2, zorder=100)
    
    ax6.set_xlabel('X Position (m)', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Y Position (m)', fontsize=12, fontweight='bold')
    ax6.set_title('SFM Force Vectors', fontsize=14, fontweight='bold')
    ax6.set_aspect('equal', adjustable='box')
    ax6.grid(True, alpha=0.3, linestyle='--')
    plt.colorbar(quiver2, ax=ax6, label='Force (N)')
    
    plt.tight_layout()
    
    return fig


def print_statistics(df):
    """Print statistical summary"""
    print("\n" + "="*70)
    print("📊 STATISTICAL SUMMARY")
    print("="*70)
    
    print(f"\n📍 Position & Movement:")
    print(f"   Start position: ({df['Position_X_m'].iloc[0]:.3f}, {df['Position_Y_m'].iloc[0]:.3f}) m")
    print(f"   End position: ({df['Position_X_m'].iloc[-1]:.3f}, {df['Position_Y_m'].iloc[-1]:.3f}) m")
    
    distance = math.hypot(
        df['Position_X_m'].iloc[-1] - df['Position_X_m'].iloc[0],
        df['Position_Y_m'].iloc[-1] - df['Position_Y_m'].iloc[0]
    )
    print(f"   Total distance: {distance:.3f} m")
    
    print(f"\n⏱️  Time:")
    print(f"   Duration: {df['Time_s'].iloc[-1] - df['Time_s'].iloc[0]:.1f} s")
    print(f"   Total samples: {len(df)}")
    
    print(f"\n🚀 Speed:")
    print(f"   Average: {df['Speed_ms'].mean():.3f} m/s")
    print(f"   Maximum: {df['Speed_ms'].max():.3f} m/s")
    print(f"   Minimum: {df['Speed_ms'].min():.3f} m/s")
    
    print(f"\n👥 Human Detection:")
    print(f"   Samples with humans: {(df['Humans_Count'] > 0).sum()}/{len(df)}")
    df_with_humans = df[df['Closest_Distance_m'] != np.inf]
    if not df_with_humans.empty:
        print(f"   Closest approach: {df_with_humans['Closest_Distance_m'].min():.2f} m")
        print(f"   Average distance: {df_with_humans['Closest_Distance_m'].mean():.2f} m")
    
    print(f"\n🔵 Zones:")
    zone_counts = df['Zone'].value_counts()
    for zone, count in zone_counts.items():
        percentage = (count / len(df)) * 100
        print(f"   {zone}: {count} samples ({percentage:.1f}%)")
    
    print(f"\n⚡ SFM Forces:")
    force_mag = np.sqrt(df['SFM_Force_X_N']**2 + df['SFM_Force_Y_N']**2)
    print(f"   Average magnitude: {force_mag.mean():.3f} N")
    print(f"   Maximum magnitude: {force_mag.max():.3f} N")
    
    print(f"\n🎯 Commands:")
    if 'Command' in df.columns:
        cmd_counts = df['Command'].value_counts()
        for cmd, count in cmd_counts.items():
            print(f"   {cmd}: {count} times")
    
    print("="*70)


def main():
    """Main function"""
    print("\n" + "="*70)
    print("📊 CSV DATA VISUALIZER - Social Navigation Analysis")
    print("="*70)
    
    # Load data
    df = load_csv('sample_data.csv')
    if df is None:
        return
    
    # Print statistics
    print_statistics(df)
    
    # Create plots
    print("\n📈 Creating visualizations...")
    fig = create_comprehensive_plots(df)
    
    # Save figure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"social_nav_analysis_{timestamp}.png"
    
    try:
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✓ Saved plot: {filename}")
    except Exception as e:
        print(f"⚠ Could not save plot: {e}")
    
    # Display
    print("\n📊 Displaying plots...")
    print("   Close the window to exit.")
    print("="*70)
    
    try:
        plt.show(block=True)
    except Exception as e:
        print(f"⚠ Could not display: {e}")
    
    print("\n✓ Done!")


if __name__ == '__main__':
    main()
