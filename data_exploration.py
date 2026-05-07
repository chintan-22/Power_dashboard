"""
Data Exploration Script for Durable Power Dashboard
Prints comprehensive statistics about the database structure and content
"""

import sqlite3
import pandas as pd
from datetime import datetime

def explore_database(db_path: str):
    """
    Explore the database and print comprehensive statistics.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DURABLE POWER DASHBOARD - DATABASE EXPLORATION")
    print("=" * 80)
    print()
    
    # ========================================================================
    # Table Overview
    # ========================================================================
    
    print("📊 TABLE OVERVIEW")
    print("-" * 80)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Total Tables: {len(tables)}")
    print(f"Tables: {', '.join([t[0] for t in tables])}")
    print()
    
    # ========================================================================
    # Actual Generation Table Analysis
    # ========================================================================
    
    print("🔍 ACTUAL GENERATION TABLE")
    print("-" * 80)
    
    # Row count
    cursor.execute("SELECT COUNT(*) FROM actual_gen;")
    actual_count = cursor.fetchone()[0]
    print(f"Total Records: {actual_count:,}")
    
    # Column info
    cursor.execute("PRAGMA table_info(actual_gen);")
    columns = cursor.fetchall()
    print(f"Columns ({len(columns)}):")
    for col in columns:
        print(f"  - {col[1]}: {col[2]}")
    print()
    
    # Date range
    cursor.execute("""
        SELECT 
            MIN(DATE_TIME) as min_datetime,
            MAX(DATE_TIME) as max_datetime,
            MIN(MARKET_DATE) as min_date,
            MAX(MARKET_DATE) as max_date,
            COUNT(DISTINCT DATE(DATE_TIME)) as unique_dates
        FROM actual_gen
    """)
    date_info = cursor.fetchone()
    print(f"Date Range (DATE_TIME): {date_info[0]} to {date_info[1]}")
    print(f"Market Date Range: {date_info[2]} to {date_info[3]}")
    print(f"Unique Date Records: {date_info[4]}")
    print()
    
    # Device and Plant statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT DEVICE_ID) as unique_devices,
            COUNT(DISTINCT PLANT_NAME) as unique_plants,
            COUNT(DISTINCT FUEL_TYPE) as unique_fuels
        FROM actual_gen
    """)
    device_info = cursor.fetchone()
    print(f"Unique Devices: {device_info[0]}")
    print(f"Unique Plants: {device_info[1]}")
    print(f"Unique Fuel Types: {device_info[2]}")
    print()
    
    # Fuel types
    cursor.execute("""
        SELECT FUEL_TYPE, COUNT(*) as count
        FROM actual_gen
        WHERE FUEL_TYPE IS NOT NULL
        GROUP BY FUEL_TYPE
        ORDER BY count DESC
    """)
    fuel_types = cursor.fetchall()
    print(f"Fuel Type Distribution:")
    for fuel, count in fuel_types:
        pct = (count / actual_count) * 100
        print(f"  - {fuel}: {count:,} ({pct:.1f}%)")
    print()
    
    # Missing values
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN DEVICE_ID IS NULL THEN 1 ELSE 0 END) as missing_device,
            SUM(CASE WHEN GEN_MW IS NULL THEN 1 ELSE 0 END) as missing_gen,
            SUM(CASE WHEN GEN_MW_MAX IS NULL THEN 1 ELSE 0 END) as missing_capacity,
            SUM(CASE WHEN STATUS IS NULL THEN 1 ELSE 0 END) as missing_status,
            SUM(CASE WHEN FUEL_TYPE IS NULL THEN 1 ELSE 0 END) as missing_fuel,
            SUM(CASE WHEN PLANT_NAME IS NULL THEN 1 ELSE 0 END) as missing_plant,
            SUM(CASE WHEN DATE_TIME IS NULL THEN 1 ELSE 0 END) as missing_datetime
        FROM actual_gen
    """)
    missing = cursor.fetchone()
    print(f"Missing Values (Actual):")
    print(f"  - DEVICE_ID: {missing[0]:,}")
    print(f"  - GEN_MW: {missing[1]:,}")
    print(f"  - GEN_MW_MAX: {missing[2]:,}")
    print(f"  - STATUS: {missing[3]:,}")
    print(f"  - FUEL_TYPE: {missing[4]:,}")
    print(f"  - PLANT_NAME: {missing[5]:,}")
    print(f"  - DATE_TIME: {missing[6]:,}")
    print()
    
    # Generation statistics
    cursor.execute("""
        SELECT 
            MIN(GEN_MW) as min_gen,
            MAX(GEN_MW) as max_gen,
            AVG(GEN_MW) as avg_gen,
            MIN(GEN_MW_MAX) as min_capacity,
            MAX(GEN_MW_MAX) as max_capacity,
            AVG(GEN_MW_MAX) as avg_capacity
        FROM actual_gen
    """)
    gen_stats = cursor.fetchone()
    print(f"Generation Statistics (Actual):")
    print(f"  - GEN_MW Range: {gen_stats[0]:.2f} to {gen_stats[1]:.2f}")
    print(f"  - GEN_MW Average: {gen_stats[2]:.2f}")
    print(f"  - Capacity Range: {gen_stats[3]:.2f} to {gen_stats[4]:.2f}")
    print(f"  - Capacity Average: {gen_stats[5]:.2f}")
    print()
    
    # Status values
    cursor.execute("""
        SELECT STATUS, COUNT(*) as count
        FROM actual_gen
        WHERE STATUS IS NOT NULL
        GROUP BY STATUS
        ORDER BY count DESC
    """)
    statuses = cursor.fetchall()
    print(f"Status Distribution (Actual):")
    for status, count in statuses:
        pct = (count / actual_count) * 100
        print(f"  - {status}: {count:,} ({pct:.1f}%)")
    print()
    
    # ========================================================================
    # Forecast Generation Table Analysis
    # ========================================================================
    
    print("🔍 FORECAST GENERATION TABLE")
    print("-" * 80)
    
    # Row count
    cursor.execute("SELECT COUNT(*) FROM forecast_gen;")
    forecast_count = cursor.fetchone()[0]
    print(f"Total Records: {forecast_count:,}")
    
    # Date range
    cursor.execute("""
        SELECT 
            MIN(DATE_TIME) as min_datetime,
            MAX(DATE_TIME) as max_datetime,
            MIN(MARKET_DATE) as min_date,
            MAX(MARKET_DATE) as max_date,
            COUNT(DISTINCT DATE(DATE_TIME)) as unique_dates
        FROM forecast_gen
    """)
    date_info = cursor.fetchone()
    print(f"Date Range (DATE_TIME): {date_info[0]} to {date_info[1]}")
    print(f"Market Date Range: {date_info[2]} to {date_info[3]}")
    print(f"Unique Date Records: {date_info[4]}")
    print()
    
    # Device and Plant statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT DEVICE_ID) as unique_devices,
            COUNT(DISTINCT PLANT_NAME) as unique_plants,
            COUNT(DISTINCT FUEL_TYPE) as unique_fuels
        FROM forecast_gen
    """)
    device_info = cursor.fetchone()
    print(f"Unique Devices: {device_info[0]}")
    print(f"Unique Plants: {device_info[1]}")
    print(f"Unique Fuel Types: {device_info[2]}")
    print()
    
    # Fuel types
    cursor.execute("""
        SELECT FUEL_TYPE, COUNT(*) as count
        FROM forecast_gen
        WHERE FUEL_TYPE IS NOT NULL
        GROUP BY FUEL_TYPE
        ORDER BY count DESC
    """)
    fuel_types = cursor.fetchall()
    print(f"Fuel Type Distribution:")
    for fuel, count in fuel_types:
        pct = (count / forecast_count) * 100
        print(f"  - {fuel}: {count:,} ({pct:.1f}%)")
    print()
    
    # Missing values
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN DEVICE_ID IS NULL THEN 1 ELSE 0 END) as missing_device,
            SUM(CASE WHEN GEN_MW IS NULL THEN 1 ELSE 0 END) as missing_gen,
            SUM(CASE WHEN GEN_MW_MAX IS NULL THEN 1 ELSE 0 END) as missing_capacity,
            SUM(CASE WHEN STATUS IS NULL THEN 1 ELSE 0 END) as missing_status,
            SUM(CASE WHEN FUEL_TYPE IS NULL THEN 1 ELSE 0 END) as missing_fuel,
            SUM(CASE WHEN PLANT_NAME IS NULL THEN 1 ELSE 0 END) as missing_plant,
            SUM(CASE WHEN DATE_TIME IS NULL THEN 1 ELSE 0 END) as missing_datetime
        FROM forecast_gen
    """)
    missing = cursor.fetchone()
    print(f"Missing Values (Forecast):")
    print(f"  - DEVICE_ID: {missing[0]:,}")
    print(f"  - GEN_MW: {missing[1]:,}")
    print(f"  - GEN_MW_MAX: {missing[2]:,}")
    print(f"  - STATUS: {missing[3]:,}")
    print(f"  - FUEL_TYPE: {missing[4]:,}")
    print(f"  - PLANT_NAME: {missing[5]:,}")
    print(f"  - DATE_TIME: {missing[6]:,}")
    print()
    
    # Generation statistics
    cursor.execute("""
        SELECT 
            MIN(GEN_MW) as min_gen,
            MAX(GEN_MW) as max_gen,
            AVG(GEN_MW) as avg_gen,
            MIN(GEN_MW_MAX) as min_capacity,
            MAX(GEN_MW_MAX) as max_capacity,
            AVG(GEN_MW_MAX) as avg_capacity
        FROM forecast_gen
    """)
    gen_stats = cursor.fetchone()
    print(f"Generation Statistics (Forecast):")
    print(f"  - GEN_MW Range: {gen_stats[0]:.2f} to {gen_stats[1]:.2f}")
    print(f"  - GEN_MW Average: {gen_stats[2]:.2f}")
    print(f"  - Capacity Range: {gen_stats[3]:.2f} to {gen_stats[4]:.2f}")
    print(f"  - Capacity Average: {gen_stats[5]:.2f}")
    print()
    
    # Status values
    cursor.execute("""
        SELECT STATUS, COUNT(*) as count
        FROM forecast_gen
        WHERE STATUS IS NOT NULL
        GROUP BY STATUS
        ORDER BY count DESC
    """)
    statuses = cursor.fetchall()
    print(f"Status Distribution (Forecast):")
    for status, count in statuses:
        pct = (count / forecast_count) * 100
        print(f"  - {status}: {count:,} ({pct:.1f}%)")
    print()
    
    # ========================================================================
    # Data Matching Analysis
    # ========================================================================
    
    print("🔗 DATA MATCHING ANALYSIS")
    print("-" * 80)
    
    # Matched records
    cursor.execute("""
        SELECT COUNT(*) as matched_count
        FROM actual_gen a
        INNER JOIN forecast_gen f
            ON a.DATE_TIME = f.DATE_TIME
            AND a.DEVICE_ID = f.DEVICE_ID
    """)
    matched = cursor.fetchone()[0]
    print(f"Fully Matched Records (DATE_TIME + DEVICE_ID): {matched:,}")
    
    # Actual-only
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM actual_gen
        WHERE NOT EXISTS (
            SELECT 1 FROM forecast_gen
            WHERE forecast_gen.DATE_TIME = actual_gen.DATE_TIME
            AND forecast_gen.DEVICE_ID = actual_gen.DEVICE_ID
        )
    """)
    actual_only = cursor.fetchone()[0]
    print(f"Actual-Only Records: {actual_only:,}")
    
    # Forecast-only
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM forecast_gen
        WHERE NOT EXISTS (
            SELECT 1 FROM actual_gen
            WHERE actual_gen.DATE_TIME = forecast_gen.DATE_TIME
            AND actual_gen.DEVICE_ID = forecast_gen.DEVICE_ID
        )
    """)
    forecast_only = cursor.fetchone()[0]
    print(f"Forecast-Only Records: {forecast_only:,}")
    print()
    
    # ========================================================================
    # Data Quality Issues
    # ========================================================================
    
    print("⚠️  DATA QUALITY ISSUES")
    print("-" * 80)
    
    # Negative generation
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW < 0) as actual_negative,
            (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW < 0) as forecast_negative
    """)
    neg_gen = cursor.fetchone()
    print(f"Negative Generation Records:")
    print(f"  - Actual: {neg_gen[0]:,}")
    print(f"  - Forecast: {neg_gen[1]:,}")
    print()
    
    # Generation exceeding capacity
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0) as actual_exceeds,
            (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0) as forecast_exceeds
    """)
    exceed = cursor.fetchone()
    print(f"Generation Exceeding Capacity:")
    print(f"  - Actual: {exceed[0]:,}")
    print(f"  - Forecast: {exceed[1]:,}")
    print()
    
    # Zero capacity
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW_MAX = 0 OR GEN_MW_MAX IS NULL) as actual_zero_cap,
            (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW_MAX = 0 OR GEN_MW_MAX IS NULL) as forecast_zero_cap
    """)
    zero_cap = cursor.fetchone()
    print(f"Zero/Missing Capacity:")
    print(f"  - Actual: {zero_cap[0]:,}")
    print(f"  - Forecast: {zero_cap[1]:,}")
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("📈 SUMMARY STATISTICS")
    print("-" * 80)
    print(f"Actual Generation Records: {actual_count:,}")
    print(f"Forecast Generation Records: {forecast_count:,}")
    print(f"Matched Records: {matched:,}")
    print(f"Coverage: {(matched / actual_count * 100):.1f}%")
    print()
    
    conn.close()
    
    print("=" * 80)
    print("✅ Database exploration complete!")
    print("=" * 80)


if __name__ == "__main__":
    import os
    import sys
    
    # Determine database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default to current directory first, then parent
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, 'assignment.db')
        if not os.path.exists(db_path):
            parent_dir = os.path.dirname(script_dir)
            db_path = os.path.join(parent_dir, 'assignment.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print(f"Looked in: {script_dir} and {os.path.dirname(script_dir)}")
        sys.exit(1)
    
    explore_database(db_path)
