#!/usr/bin/env python3
"""
Quick Statistics from Sample Data CSV
=======================================
Script sederhana untuk menampilkan statistik cepat tanpa grafik.

Usage:
    python quick_stats.py [csv_file]

Example:
    python quick_stats.py
    python quick_stats.py sample_data.csv

Author: Brone Social Nav Team
Date: 2026-10-06
"""

import pandas as pd
import numpy as np
import math
import sys
import os


def load_and_analyze(csv_file='sample_data.csv'):
    """Load CSV and print statistics"""
    
    # Check file exists
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return False
    
    # Load CSV
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return False
    
    print("\n" + "="*80)
    print(f"📊 QUICK STATISTICS: {csv_file}")
    print("="*80)
    
    # ========== Basic Info ==========
    print(f"\n📋 BASIC INFO")
    print(f"{'─'*80}")
    print(f"   Total samples: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Data shape: {df.shape}")
    
    # ========== Time ==========
    print(f"\n⏱️  TIME")
    print(f"{'─'*80}")
    t_start = df['Time_s'].iloc[0]
    t_end = df['Time_s'].iloc[-1]
    duration = t_end - t_start
    print(f"   Start time: {t_start:.2f} s")
    print(f"   End time: {t_end:.2f} s")
    print(f"   Duration: {duration:.2f} s ({duration/60:.2f} min)")
    print(f"   Avg sampling interval: {duration/(len(df)-1):.2f} s")
    
    # ========== Position ==========
    print(f"\n📍 POSITION")
    print(f"{'─'*80}")
    x_start, y_start = df['Position_X_m'].iloc[0], df['Position_Y_m'].iloc[0]
    x_end, y_end = df['Position_X_m'].iloc[-1], df['Position_Y_m'].iloc[-1]
    
    print(f"   Start: ({x_start:.3f}, {y_start:.3f}) m")
    print(f"   End: ({x_end:.3f}, {y_end:.3f}) m")
    
    # Calculate distance
    distance = math.hypot(x_end - x_start, y_end - y_start)
    print(f"   Straight-line distance: {distance:.3f} m")
    
    # Calculate path length
    path_length = 0
    for i in range(1, len(df)):
        dx = df['Position_X_m'].iloc[i] - df['Position_X_m'].iloc[i-1]
        dy = df['Position_Y_m'].iloc[i] - df['Position_Y_m'].iloc[i-1]
        path_length += math.hypot(dx, dy)
    
    print(f"   Path length: {path_length:.3f} m")
    print(f"   Path efficiency: {(distance/path_length*100):.1f}%")
    
    # Position range
    print(f"\n   X range: [{df['Position_X_m'].min():.3f}, {df['Position_X_m'].max():.3f}] m")
    print(f"   Y range: [{df['Position_Y_m'].min():.3f}, {df['Position_Y_m'].max():.3f}] m")
    
    # ========== Speed ==========
    print(f"\n🚀 SPEED")
    print(f"{'─'*80}")
    print(f"   Average: {df['Speed_ms'].mean():.3f} m/s")
    print(f"   Median: {df['Speed_ms'].median():.3f} m/s")
    print(f"   Min: {df['Speed_ms'].min():.3f} m/s")
    print(f"   Max: {df['Speed_ms'].max():.3f} m/s")
    print(f"   Std dev: {df['Speed_ms'].std():.3f} m/s")
    
    # Speed distribution
    slow = (df['Speed_ms'] < 0.4).sum()
    medium = ((df['Speed_ms'] >= 0.4) & (df['Speed_ms'] < 0.8)).sum()
    fast = (df['Speed_ms'] >= 0.8).sum()
    
    print(f"\n   Speed distribution:")
    print(f"      Slow (<0.4 m/s): {slow} samples ({slow/len(df)*100:.1f}%)")
    print(f"      Medium (0.4-0.8 m/s): {medium} samples ({medium/len(df)*100:.1f}%)")
    print(f"      Fast (>0.8 m/s): {fast} samples ({fast/len(df)*100:.1f}%)")
    
    # ========== Zones ==========
    print(f"\n🔵 PROXEMIC ZONES")
    print(f"{'─'*80}")
    zone_counts = df['Zone'].value_counts()
    
    zone_order = ['INTIMATE', 'PERSONAL', 'SOCIAL', 'PUBLIC']
    for zone in zone_order:
        if zone in zone_counts:
            count = zone_counts[zone]
            percentage = (count / len(df)) * 100
            bar_length = int(percentage / 2)
            bar = '█' * bar_length
            
            emoji = {'INTIMATE': '🔴', 'PERSONAL': '🟠', 
                    'SOCIAL': '🟡', 'PUBLIC': '🟢'}
            
            print(f"   {emoji[zone]} {zone:10s}: {count:2d} samples ({percentage:5.1f}%) {bar}")
    
    # ========== Human Detection ==========
    print(f"\n👥 HUMAN DETECTION")
    print(f"{'─'*80}")
    with_humans = (df['Humans_Count'] > 0).sum()
    without_humans = (df['Humans_Count'] == 0).sum()
    
    print(f"   Samples with humans: {with_humans}/{len(df)} ({with_humans/len(df)*100:.1f}%)")
    print(f"   Samples without humans: {without_humans}/{len(df)} ({without_humans/len(df)*100:.1f}%)")
    
    # Closest distance statistics
    df_with_humans = df[df['Closest_Distance_m'] != np.inf]
    
    if not df_with_humans.empty:
        print(f"\n   Distance to closest human:")
        print(f"      Minimum: {df_with_humans['Closest_Distance_m'].min():.2f} m")
        print(f"      Average: {df_with_humans['Closest_Distance_m'].mean():.2f} m")
        print(f"      Maximum: {df_with_humans['Closest_Distance_m'].max():.2f} m")
        
        # Safety analysis
        intimate_violations = (df_with_humans['Closest_Distance_m'] < 0.45).sum()
        personal_intrusions = (df_with_humans['Closest_Distance_m'] < 1.20).sum()
        
        if intimate_violations > 0:
            print(f"\n   ⚠️  INTIMATE zone violations: {intimate_violations} samples")
        else:
            print(f"\n   ✓ No INTIMATE zone violations")
        
        if personal_intrusions > 0:
            print(f"   ⚠️  PERSONAL zone intrusions: {personal_intrusions} samples")
    
    # ========== Forces ==========
    print(f"\n⚡ SOCIAL FORCE MODEL")
    print(f"{'─'*80}")
    
    # Calculate force magnitude
    force_mag = np.sqrt(df['SFM_Force_X_N']**2 + df['SFM_Force_Y_N']**2)
    
    print(f"   Force magnitude:")
    print(f"      Average: {force_mag.mean():.3f} N")
    print(f"      Median: {force_mag.median():.3f} N")
    print(f"      Min: {force_mag.min():.3f} N")
    print(f"      Max: {force_mag.max():.3f} N")
    
    # Force by zone
    print(f"\n   Average force by zone:")
    for zone in zone_order:
        if zone in df['Zone'].values:
            zone_data = df[df['Zone'] == zone]
            zone_force = np.sqrt(zone_data['SFM_Force_X_N']**2 + 
                               zone_data['SFM_Force_Y_N']**2)
            print(f"      {zone:10s}: {zone_force.mean():.3f} N")
    
    # ========== Commands ==========
    if 'Command' in df.columns:
        print(f"\n🎯 ROBOT COMMANDS")
        print(f"{'─'*80}")
        
        cmd_counts = df['Command'].value_counts()
        for cmd, count in cmd_counts.items():
            percentage = (count / len(df)) * 100
            bar_length = int(percentage / 2)
            bar = '▓' * bar_length
            print(f"   {cmd:15s}: {count:2d} times ({percentage:5.1f}%) {bar}")
    
    # ========== Displacement ==========
    print(f"\n📏 DISPLACEMENT")
    print(f"{'─'*80}")
    
    total_disp_x = df['Displacement_X_m'].sum()
    total_disp_y = df['Displacement_Y_m'].sum()
    
    print(f"   Total X displacement: {total_disp_x:+.3f} m")
    print(f"   Total Y displacement: {total_disp_y:+.3f} m")
    print(f"   Net displacement: {math.hypot(total_disp_x, total_disp_y):.3f} m")
    
    # ========== Summary ==========
    print(f"\n{'='*80}")
    print(f"📈 SUMMARY")
    print(f"{'='*80}")
    print(f"   ✓ Processed {len(df)} samples over {duration:.1f} seconds")
    print(f"   ✓ Robot traveled {path_length:.3f} m")
    print(f"   ✓ Average speed: {df['Speed_ms'].mean():.2f} m/s")
    print(f"   ✓ Most time in: {zone_counts.idxmax()} zone")
    
    if intimate_violations == 0:
        print(f"   ✓ No safety violations")
    else:
        print(f"   ⚠️  {intimate_violations} safety violations detected")
    
    print(f"{'='*80}\n")
    
    return True


def main():
    """Main function"""
    
    # Get CSV filename from command line or use default
    csv_file = 'sample_data.csv'
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    # Analyze
    success = load_and_analyze(csv_file)
    
    if not success:
        print("\n💡 Usage: python quick_stats.py [csv_file]")
        print("   Example: python quick_stats.py sample_data.csv")
        sys.exit(1)


if __name__ == '__main__':
    main()
