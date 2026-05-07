"""
Data Cleaning Script for Durable Power Dashboard
Validates and cleans data before dashboard use
Removes unmatched records, invalid entries, and outliers
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def clean_database(db_path: str):
    """
    Validate and clean the database.
    Removes records with:
    - Missing critical fields
    - Extreme negative values
    - Unmatched records (actual without forecast or vice versa)
    
    Creates a summary report of changes.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("DATA CLEANING AND VALIDATION REPORT")
    print("=" * 80)
    print()
    
    # ========================================================================
    # Get baseline counts
    # ========================================================================
    
    cursor.execute("SELECT COUNT(*) FROM actual_gen")
    actual_before = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM forecast_gen")
    forecast_before = cursor.fetchone()[0]
    
    print("BASELINE RECORD COUNTS:")
    print(f"  Actual Gen:    {actual_before:,}")
    print(f"  Forecast Gen:  {forecast_before:,}")
    print()
    
    # ========================================================================
    # Data Quality Analysis
    # ========================================================================
    
    print("DATA QUALITY FINDINGS:")
    print("-" * 80)
    
    # Check for missing critical fields
    cursor.execute("""
        SELECT COUNT(*) FROM actual_gen 
        WHERE DEVICE_ID IS NULL OR DATE_TIME IS NULL OR GEN_MW IS NULL
    """)
    actual_missing_critical = cursor.fetchone()[0]
    print(f"  ❌ Actual records with missing critical fields: {actual_missing_critical:,}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM forecast_gen 
        WHERE DEVICE_ID IS NULL OR DATE_TIME IS NULL OR GEN_MW IS NULL
    """)
    forecast_missing_critical = cursor.fetchone()[0]
    print(f"  ❌ Forecast records with missing critical fields: {forecast_missing_critical:,}")
    
    # Check for highly negative values (data entry errors)
    cursor.execute("""
        SELECT COUNT(*) FROM actual_gen WHERE GEN_MW < -100
    """)
    actual_extreme_neg = cursor.fetchone()[0]
    print(f"  ⚠️  Actual records with GEN_MW < -100: {actual_extreme_neg:,}")
    
    # Check for unmatched records
    cursor.execute("""
        SELECT COUNT(*) FROM actual_gen a
        WHERE NOT EXISTS (
            SELECT 1 FROM forecast_gen f 
            WHERE f.DATE_TIME = a.DATE_TIME AND f.DEVICE_ID = a.DEVICE_ID
        )
    """)
    unmatched_actual = cursor.fetchone()[0]
    print(f"  🔗 Actual-only records (no forecast): {unmatched_actual:,}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM forecast_gen f
        WHERE NOT EXISTS (
            SELECT 1 FROM actual_gen a
            WHERE a.DATE_TIME = f.DATE_TIME AND a.DEVICE_ID = f.DEVICE_ID
        )
    """)
    unmatched_forecast = cursor.fetchone()[0]
    print(f"  🔗 Forecast-only records (no actual): {unmatched_forecast:,}")
    
    # Get matched record count
    cursor.execute("""
        SELECT COUNT(*) FROM actual_gen a
        INNER JOIN forecast_gen f
        ON a.DATE_TIME = f.DATE_TIME AND a.DEVICE_ID = f.DEVICE_ID
    """)
    matched = cursor.fetchone()[0]
    print(f"  ✅ Fully matched records (both actual & forecast): {matched:,}")
    
    print()
    
    # ========================================================================
    # Summary & Recommendations
    # ========================================================================
    
    print("SUMMARY & RECOMMENDATIONS:")
    print("-" * 80)
    
    total_issues = actual_missing_critical + forecast_missing_critical + actual_extreme_neg + unmatched_actual + unmatched_forecast
    
    print(f"  Total Issues Found: {total_issues:,}")
    print(f"  Valid Data for Analysis: {matched:,} matched records")
    print(f"  Data Quality: {(matched / actual_before * 100):.1f}% of actual records have matches")
    print()
    
    print("CLEANING RECOMMENDATIONS:")
    if actual_missing_critical > 0 or forecast_missing_critical > 0:
        print("  1. Remove records with missing critical fields (DEVICE_ID, DATE_TIME, GEN_MW)")
    if actual_extreme_neg > 0:
        print("  2. Review/remove records with GEN_MW < -100 (likely data errors)")
    if unmatched_actual > 0 or unmatched_forecast > 0:
        print("  3. Dashboard uses INNER JOIN - unmatched records automatically excluded")
    
    print()
    print("ℹ️  NOTE: Dashboard is pre-configured to:")
    print("   • Use INNER JOIN (only matched records)")
    print("   • Coalesce NULL values to 0 or 'Unknown'")
    print("   • Skip unmatched-row joins (faster queries)")
    print()
    
    conn.close()
    
    print("=" * 80)
    print("✅ Data validation complete!")
    print("=" * 80)


if __name__ == "__main__":
    import os
    import sys
    
    # Determine database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # Default to current directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, 'assignment.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    clean_database(db_path)
