"""
Utility functions for the Durable Power Dashboard
Handles database connections, data processing, and calculations
"""

from __future__ import annotations

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st


# ============================================================================
# Database Connection Functions
# ============================================================================

@st.cache_resource
def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a cached SQLite database connection.
    Uses Streamlit's caching to avoid repeated connections.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


@st.cache_resource
def ensure_performance_indexes(db_path: str) -> bool:
    """
    Create indexes used by the dashboard's date filtering and joins.
    This runs once per database file; CREATE INDEX IF NOT EXISTS is quick
    after the first run because the indexes are stored in SQLite.
    """
    conn = get_db_connection(db_path)
    conn.execute("PRAGMA busy_timeout = 5000")
    cursor = conn.cursor()

    index_statements = {
        'idx_actual_market_datetime_device': """
            CREATE INDEX idx_actual_market_datetime_device
            ON actual_gen (MARKET_DATE, DATE_TIME, DEVICE_ID)
        """,
        'idx_forecast_datetime_device': """
            CREATE INDEX idx_forecast_datetime_device
            ON forecast_gen (DATE_TIME, DEVICE_ID)
        """,
        'idx_actual_plant_name': """
            CREATE INDEX idx_actual_plant_name
            ON actual_gen (PLANT_NAME)
        """,
        'idx_actual_device_id': """
            CREATE INDEX idx_actual_device_id
            ON actual_gen (DEVICE_ID)
        """,
        'idx_actual_fuel_type': """
            CREATE INDEX idx_actual_fuel_type
            ON actual_gen (FUEL_TYPE)
        """,
    }

    existing_indexes = {
        row[0]
        for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }

    missing_indexes = [
        statement
        for name, statement in index_statements.items()
        if name not in existing_indexes
    ]

    if not missing_indexes:
        return True

    try:
        for statement in missing_indexes:
            cursor.execute(statement)

        cursor.execute("ANALYZE")
        conn.commit()
    except sqlite3.OperationalError as exc:
        conn.rollback()
        raise RuntimeError(
            "Could not create database performance indexes. "
            "Stop any running dashboard process and restart the app."
        ) from exc

    return True


@st.cache_data(ttl=3600)
def query_database(query: str, db_path: str) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a pandas DataFrame.
    Results are cached for 1 hour.
    """
    conn = get_db_connection(db_path)
    df = pd.read_sql_query(query, conn)
    return df


# ============================================================================
# Data Loading and Processing Functions
# ============================================================================

def load_and_process_data(
    db_path: str,
    date_range: tuple,
    plants: list,
    devices: list,
    fuel_types: list
) -> pd.DataFrame:
    """
    Load actual and forecast generation data from database,
    join them, and apply filters.
    Optimized for performance with INNER JOIN matched-record analysis.
    
    Args:
        db_path: Path to SQLite database
        date_range: Tuple of (start_date, end_date)
        plants: List of plant names to filter
        devices: List of device IDs to filter
        fuel_types: List of fuel types to filter
    
    Returns:
        Processed DataFrame with actual and forecast data joined
    """
    start_date, end_date = date_range
    
    # Build optimized SQL query with INNER JOIN (only matched records)
    # This is faster and removes unmatched records automatically
    query = f"""
    SELECT
        a.DATE_TIME,
        a.MARKET_DATE,
        a.DEVICE_ID,
        COALESCE(a.GEN_MW, 0) as ACTUAL_MW,
        COALESCE(f.GEN_MW, 0) as FORECAST_MW,
        COALESCE(a.GEN_MW_MAX, 0) as ACTUAL_GEN_MW_MAX,
        COALESCE(f.GEN_MW_MAX, 0) as FORECAST_GEN_MW_MAX,
        COALESCE(a.STATUS, f.STATUS) as STATUS,
        COALESCE(a.PLANT_NAME, f.PLANT_NAME, 'Unknown Plant') as PLANT_NAME,
        COALESCE(a.FUEL_TYPE, f.FUEL_TYPE, 'Unknown Fuel') as FUEL_TYPE
    FROM actual_gen a
    INNER JOIN forecast_gen f
        ON a.DATE_TIME = f.DATE_TIME
        AND a.DEVICE_ID = f.DEVICE_ID
    WHERE a.MARKET_DATE >= '{start_date}' 
      AND a.MARKET_DATE <= '{end_date}'
    """
    
    # Add plant filter if specified
    if plants:
        plant_list = "', '".join([p.replace("'", "''") for p in plants])
        query += f" AND COALESCE(a.PLANT_NAME, f.PLANT_NAME) IN ('{plant_list}')"
    
    # Add device filter if specified
    if devices:
        device_list = "', '".join([d.replace("'", "''") for d in devices])
        query += f" AND a.DEVICE_ID IN ('{device_list}')"
    
    # Add fuel type filter if specified
    if fuel_types:
        fuel_list = "', '".join([ft.replace("'", "''") for ft in fuel_types])
        query += f" AND COALESCE(a.FUEL_TYPE, f.FUEL_TYPE) IN ('{fuel_list}')"
    
    df = query_database(query, db_path)
    
    if df.empty:
        return df
    
    # Data type conversions (optimized)
    df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
    df['MARKET_DATE'] = pd.to_datetime(df['MARKET_DATE']).dt.date
    
    # Ensure numeric types
    df['ACTUAL_MW'] = pd.to_numeric(df['ACTUAL_MW'], errors='coerce').fillna(0)
    df['FORECAST_MW'] = pd.to_numeric(df['FORECAST_MW'], errors='coerce').fillna(0)
    
    return df


def calculate_error_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate error metrics for forecast accuracy.
    
    Adds columns:
    - ERROR_MW: Actual - Forecast
    - ABS_ERROR_MW: Absolute error
    - SQUARED_ERROR: Squared error
    - APE: Absolute percentage error (only when ACTUAL_MW != 0)
    """
    df = df.copy()
    
    df['ERROR_MW'] = df['ACTUAL_MW'] - df['FORECAST_MW']
    df['ABS_ERROR_MW'] = df['ERROR_MW'].abs()
    df['SQUARED_ERROR'] = df['ERROR_MW'] ** 2
    
    # Calculate APE only when ACTUAL_MW is not zero
    df['APE'] = np.where(
        df['ACTUAL_MW'] != 0,
        (df['ABS_ERROR_MW'] / df['ACTUAL_MW'].abs()) * 100,
        np.nan
    )
    
    return df


def calculate_global_metrics(df: pd.DataFrame) -> dict:
    """
    Calculate global forecast accuracy metrics.
    
    Returns a dictionary containing:
    - total_actual_mw
    - total_forecast_mw
    - mae: Mean Absolute Error
    - rmse: Root Mean Squared Error
    - bias: Average (Actual - Forecast)
    - mape: Mean Absolute Percentage Error
    - record_count
    - unique_devices
    - unique_plants
    """
    metrics = {
        'total_actual_mw': df['ACTUAL_MW'].sum(),
        'total_forecast_mw': df['FORECAST_MW'].sum(),
        'mae': df['ABS_ERROR_MW'].mean(),
        'rmse': np.sqrt(df['SQUARED_ERROR'].mean()),
        'bias': df['ERROR_MW'].mean(),
        'mape': df['APE'].mean(),  # This will be NaN-aware
        'record_count': len(df),
        'unique_devices': df['DEVICE_ID'].nunique(),
        'unique_plants': df['PLANT_NAME'].nunique(),
    }
    return metrics


# ============================================================================
# Aggregation Functions
# ============================================================================

def aggregate_by_level(df: pd.DataFrame, level: str = 'Device') -> pd.DataFrame:
    """
    Aggregate metrics by specified level: Device, Plant, or Fuel Type.
    
    Returns DataFrame with aggregated metrics and error calculations.
    """
    if level == 'Device':
        group_cols = ['DEVICE_ID', 'FUEL_TYPE', 'PLANT_NAME']
    elif level == 'Plant':
        group_cols = ['PLANT_NAME', 'FUEL_TYPE']
        df = df.copy()
        df['DEVICE_ID'] = df['PLANT_NAME']  # For display purposes
    elif level == 'Fuel Type':
        group_cols = ['FUEL_TYPE']
        df = df.copy()
        df['DEVICE_ID'] = df['FUEL_TYPE']
        df['PLANT_NAME'] = 'All'
    else:
        raise ValueError(f"Unknown aggregation level: {level}")
    
    agg_dict = {
        'ACTUAL_MW': 'sum',
        'FORECAST_MW': 'sum',
        'ABS_ERROR_MW': 'mean',
        'SQUARED_ERROR': 'mean',
        'APE': 'mean',
        'DATE_TIME': 'count'
    }
    
    result = df.groupby(group_cols, as_index=False).agg(agg_dict)
    result.rename(columns={'DATE_TIME': 'OBSERVATION_COUNT'}, inplace=True)
    
    # Calculate RMSE from squared error
    result['RMSE'] = np.sqrt(result['SQUARED_ERROR'])
    result['BIAS'] = result['ACTUAL_MW'] - result['FORECAST_MW']
    result.rename(columns={'ABS_ERROR_MW': 'MAE'}, inplace=True)
    
    # Sort by MAE (worst performers first)
    result = result.sort_values('MAE', ascending=False)
    
    return result


def calculate_capacity_utilization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate capacity utilization for each record.
    
    Capacity utilization = Actual MW / Maximum Capacity
    Only calculated when maximum capacity > 0
    """
    df = df.copy()
    
    df['CAPACITY_UTILIZATION'] = np.where(
        df['ACTUAL_GEN_MW_MAX'] > 0,
        (df['ACTUAL_MW'] / df['ACTUAL_GEN_MW_MAX']) * 100,
        np.nan
    )
    
    return df


# ============================================================================
# Preprocessed Analytics Layer Functions
# ============================================================================

REQUIRED_ANALYTICS_FILES = [
    "matched_generation.parquet",
    "daily_summary.parquet",
    "weekly_summary.parquet",
    "monthly_summary.parquet",
    "plant_summary.parquet",
    "device_summary.parquet",
    "fuel_summary.parquet",
    "data_quality_summary.csv",
    "preprocess_metadata.json",
]


def check_preprocessed_files(data_dir: str | Path) -> tuple[bool, list[str]]:
    """Check whether the required Parquet analytics files exist."""
    data_path = Path(data_dir)
    missing = [
        filename
        for filename in REQUIRED_ANALYTICS_FILES
        if not (data_path / filename).exists()
    ]
    return len(missing) == 0, missing


@st.cache_data(ttl=3600, show_spinner=False)
def load_analytics_layer(data_dir: str | Path) -> dict:
    """Load all preprocessed dashboard analytics files from Parquet/CSV/JSON."""
    data_path = Path(data_dir)

    layer = {
        "matched": pd.read_parquet(data_path / "matched_generation.parquet"),
        "daily": pd.read_parquet(data_path / "daily_summary.parquet"),
        "weekly": pd.read_parquet(data_path / "weekly_summary.parquet"),
        "monthly": pd.read_parquet(data_path / "monthly_summary.parquet"),
        "plant": pd.read_parquet(data_path / "plant_summary.parquet"),
        "device": pd.read_parquet(data_path / "device_summary.parquet"),
        "fuel": pd.read_parquet(data_path / "fuel_summary.parquet"),
        "data_quality": pd.read_csv(data_path / "data_quality_summary.csv"),
    }

    metadata_path = data_path / "preprocess_metadata.json"
    if metadata_path.exists():
        import json

        layer["metadata"] = json.loads(metadata_path.read_text(encoding="utf-8"))
    else:
        layer["metadata"] = {}

    for key, date_cols in {
        "matched": ["DATE_TIME", "MARKET_DATE", "DAY", "WEEK", "MONTH"],
        "daily": ["DAY"],
        "weekly": ["WEEK"],
        "monthly": ["MONTH"],
    }.items():
        for column in date_cols:
            if column in layer[key].columns:
                layer[key][column] = pd.to_datetime(layer[key][column], errors="coerce")

    return layer


def _normalize_date_range(date_range: tuple) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_date, end_date = date_range
    start = pd.to_datetime(start_date).normalize()
    end = pd.to_datetime(end_date).normalize()
    return start, end


def filter_summary_data(
    df: pd.DataFrame,
    date_col: str,
    date_range: tuple,
    fuel_types: list | None = None,
) -> pd.DataFrame:
    """Filter a pre-aggregated summary by date range and fuel type."""
    if df.empty:
        return df.copy()

    filtered = df.copy()
    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")
    start, end = _normalize_date_range(date_range)
    filtered = filtered[(filtered[date_col] >= start) & (filtered[date_col] <= end)]

    if fuel_types:
        filtered = filtered[filtered["FUEL_TYPE"].isin(fuel_types)]

    return filtered


def filter_matched_data(
    df: pd.DataFrame,
    date_range: tuple,
    plants: list | None = None,
    devices: list | None = None,
    fuel_types: list | None = None,
    error_threshold: float | None = None,
    exclude_unknown: bool = False,
) -> pd.DataFrame:
    """Filter the cleaned matched generation dataset consistently for the dashboard."""
    if df.empty:
        return df.copy()

    filtered = df.copy()
    date_column = "DAY" if "DAY" in filtered.columns else "MARKET_DATE"
    filtered[date_column] = pd.to_datetime(filtered[date_column], errors="coerce")

    start, end = _normalize_date_range(date_range)
    filtered = filtered[
        (filtered[date_column] >= start)
        & (filtered[date_column] <= end)
    ]

    if plants:
        filtered = filtered[filtered["PLANT_NAME"].isin(plants)]
    if devices:
        filtered = filtered[filtered["DEVICE_ID"].isin(devices)]
    if fuel_types:
        filtered = filtered[filtered["FUEL_TYPE"].isin(fuel_types)]
    if error_threshold is not None:
        filtered = filtered[filtered["ABS_ERROR_MW"] >= error_threshold]
    if exclude_unknown:
        filtered = filtered[
            (filtered["PLANT_NAME"] != "Unknown Plant")
            & (filtered["FUEL_TYPE"] != "Unknown Fuel")
        ]

    return filtered


def safe_divide(numerator, denominator):
    """Divide while returning NaN when the denominator is zero or missing."""
    if pd.isna(denominator) or denominator == 0:
        return np.nan
    return numerator / denominator


def calculate_metrics_from_filtered_data(df: pd.DataFrame) -> dict:
    """Calculate dashboard KPI metrics from a filtered matched dataset."""
    if df.empty:
        return {
            "total_actual_mw": 0.0,
            "total_forecast_mw": 0.0,
            "forecast_difference_mw": 0.0,
            "mae": np.nan,
            "rmse": np.nan,
            "bias": np.nan,
            "mape": np.nan,
            "wape": np.nan,
            "energy_accuracy_pct": np.nan,
            "forecast_accuracy_pct": np.nan,
            "avg_capacity_utilization": np.nan,
            "observation_count": 0,
            "unique_devices": 0,
            "unique_plants": 0,
            "fuel_types": 0,
        }

    total_actual = df["ACTUAL_MW"].sum()
    total_forecast = df["FORECAST_MW"].sum()
    absolute_actual = df["ACTUAL_MW"].abs().sum()
    absolute_error = df["ABS_ERROR_MW"].sum()
    mape = df["APE"].mean()
    wape = safe_divide(absolute_error, absolute_actual) * 100
    energy_accuracy = (
        np.clip(100 - wape, 0, 100)
        if not pd.isna(wape)
        else np.nan
    )

    return {
        "total_actual_mw": total_actual,
        "total_forecast_mw": total_forecast,
        "forecast_difference_mw": total_actual - total_forecast,
        "mae": df["ABS_ERROR_MW"].mean(),
        "rmse": np.sqrt(df["SQUARED_ERROR"].mean()),
        "bias": df["ERROR_MW"].mean(),
        "mape": mape,
        "wape": wape,
        "energy_accuracy_pct": energy_accuracy,
        "forecast_accuracy_pct": energy_accuracy,
        "avg_capacity_utilization": df["CAPACITY_UTILIZATION"].mean(),
        "observation_count": len(df),
        "unique_devices": df["DEVICE_ID"].nunique(),
        "unique_plants": df["PLANT_NAME"].nunique(),
        "fuel_types": df["FUEL_TYPE"].nunique(),
    }


def _aggregate_for_rankings(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    ranking_df = df.copy()
    ranking_df["ACTUAL_MW_ABS"] = ranking_df["ACTUAL_MW"].abs()
    ranking_df["FORECAST_MW_ABS"] = ranking_df["FORECAST_MW"].abs()
    ranking_df["IS_ACTIVE_OBSERVATION"] = (
        (ranking_df["ACTUAL_MW_ABS"] > 0)
        | (ranking_df["FORECAST_MW_ABS"] > 0)
    ).astype(int)

    grouped = (
        ranking_df.groupby(group_cols, dropna=False)
        .agg(
            total_actual_mw=("ACTUAL_MW", "sum"),
            total_forecast_mw=("FORECAST_MW", "sum"),
            total_actual_mw_magnitude=("ACTUAL_MW_ABS", "sum"),
            total_forecast_mw_magnitude=("FORECAST_MW_ABS", "sum"),
            active_observation_count=("IS_ACTIVE_OBSERVATION", "sum"),
            observation_count=("DEVICE_ID", "size"),
            unique_devices=("DEVICE_ID", "nunique"),
            unique_plants=("PLANT_NAME", "nunique"),
            mae=("ABS_ERROR_MW", "mean"),
            abs_error_sum=("ABS_ERROR_MW", "sum"),
            squared_error_mean=("SQUARED_ERROR", "mean"),
            bias=("ERROR_MW", "mean"),
            mape=("APE", "mean"),
            avg_capacity_utilization=("CAPACITY_UTILIZATION", "mean"),
        )
        .reset_index()
    )
    grouped["rmse"] = np.sqrt(grouped["squared_error_mean"])
    grouped["forecast_difference_mw"] = (
        grouped["total_actual_mw"] - grouped["total_forecast_mw"]
    )
    grouped["total_activity_mw"] = (
        grouped["total_actual_mw_magnitude"]
        + grouped["total_forecast_mw_magnitude"]
    )
    grouped["wape"] = (
        grouped["abs_error_sum"]
        / grouped["total_actual_mw_magnitude"].replace(0, np.nan)
    ) * 100
    grouped["energy_accuracy_pct"] = (100 - grouped["wape"]).clip(0, 100)
    grouped["forecast_accuracy_pct"] = grouped["energy_accuracy_pct"]
    return grouped.drop(columns=["squared_error_mean"])


def calculate_rankings(
    df: pd.DataFrame,
    level: str,
    metric: str,
    top_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate best/worst rankings for Device, Plant, or Fuel Type."""
    if df.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    level_map = {
        "Device": ["DEVICE_ID", "PLANT_NAME", "FUEL_TYPE"],
        "Plant": ["PLANT_NAME", "FUEL_TYPE"],
        "Fuel Type": ["FUEL_TYPE"],
    }
    group_cols = level_map.get(level)
    if group_cols is None:
        raise ValueError(f"Unknown ranking level: {level}")

    metric_col = metric.lower()
    rankings = _aggregate_for_rankings(df, group_cols)

    active_rankings = rankings[
        (rankings["active_observation_count"] > 0)
        & (rankings["total_activity_mw"] > 0)
    ].copy()

    ranking_source = active_rankings if not active_rankings.empty else rankings.copy()

    if metric_col == "bias":
        ranking_source["_rank_value"] = ranking_source["bias"].abs()
    else:
        ranking_source["_rank_value"] = ranking_source[metric_col]

    best = ranking_source.nsmallest(top_n, "_rank_value").drop(columns=["_rank_value"])
    worst = ranking_source.nlargest(top_n, "_rank_value").drop(columns=["_rank_value"])
    return rankings, best, worst


def format_large_number(value: float) -> str:
    """Format large values with compact suffixes."""
    if pd.isna(value):
        return "N/A"
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:.2f}"


def generate_insights(
    filtered_df: pd.DataFrame,
    ranking_df: pd.DataFrame | None = None,
) -> list[dict]:
    """Generate business-friendly forecast insights for the filtered data."""
    if filtered_df.empty:
        return [
            {
                "title": "No data for selected filters",
                "detail": "Adjust the date, plant, device, or fuel filters to restore dashboard results.",
            }
        ]

    metrics = calculate_metrics_from_filtered_data(filtered_df)
    insights = []

    bias = metrics["bias"]
    if pd.isna(bias) or abs(bias) < 1e-9:
        tendency = "Forecasts were balanced against actual generation."
    elif bias < 0:
        tendency = "Forecasts generally overestimated actual generation."
    else:
        tendency = "Forecasts generally underestimated actual generation."
    insights.append({"title": "Overall forecast tendency", "detail": tendency})

    fuel_rankings, _, _ = calculate_rankings(filtered_df, "Fuel Type", "MAE", 1)
    if not fuel_rankings.empty:
        row = fuel_rankings.sort_values("mae", ascending=False).iloc[0]
        insights.append({
            "title": "Highest-error fuel type",
            "detail": f"{row['FUEL_TYPE']} has the highest MAE at {row['mae']:.2f} MW.",
        })

    plant_rankings, _, _ = calculate_rankings(filtered_df, "Plant", "MAE", 1)
    if not plant_rankings.empty:
        row = plant_rankings.sort_values("mae", ascending=False).iloc[0]
        insights.append({
            "title": "Highest-error plant",
            "detail": f"{row['PLANT_NAME']} has the highest MAE at {row['mae']:.2f} MW.",
        })

    device_rankings, best_device, _ = calculate_rankings(filtered_df, "Device", "MAE", 1)
    if not device_rankings.empty:
        row = device_rankings.sort_values("mae", ascending=False).iloc[0]
        insights.append({
            "title": "Highest-error device",
            "detail": f"{row['DEVICE_ID']} has the highest MAE at {row['mae']:.2f} MW.",
        })

    if not best_device.empty:
        row = best_device.iloc[0]
        insights.append({
            "title": "Best-performing device",
            "detail": f"{row['DEVICE_ID']} has the lowest MAE at {row['mae']:.2f} MW.",
        })

    mae = metrics["mae"]
    rmse = metrics["rmse"]
    if not pd.isna(mae) and mae > 0 and not pd.isna(rmse):
        if rmse >= mae * 1.5:
            detail = "RMSE is much higher than MAE, suggesting occasional large forecast misses."
        else:
            detail = "RMSE is close to MAE, suggesting errors are relatively consistent."
        insights.append({"title": "Large-miss signal", "detail": detail})

    pct_diff = safe_divide(metrics["forecast_difference_mw"], metrics["total_forecast_mw"])
    if not pd.isna(pct_diff):
        insights.append({
            "title": "Actual vs forecast difference",
            "detail": f"Total actual generation differs from forecast by {pct_diff * 100:.2f}%.",
        })

    utilization = metrics["avg_capacity_utilization"]
    if not pd.isna(utilization):
        insights.append({
            "title": "Capacity utilization",
            "detail": f"Average capacity utilization is {utilization:.2f}% for the selected data.",
        })

    return insights[:8]


# ============================================================================
# Filtering and Retrieval Functions
# ============================================================================

@st.cache_data(ttl=3600)
def get_unique_values(db_path: str, column: str, table: str = 'actual_gen') -> list:
    """
    Get unique values for a column to populate multiselect filters.
    Results are cached for 1 hour.
    """
    query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
    df = query_database(query, db_path)
    return sorted(df[column].tolist())


@st.cache_data(ttl=3600)
def get_date_range(db_path: str) -> tuple:
    """
    Get the min and max MARKET_DATE from the database.
    Returns tuple of (min_date, max_date)
    """
    query = "SELECT MIN(MARKET_DATE), MAX(MARKET_DATE) FROM actual_gen"
    df = query_database(query, db_path)
    min_date = pd.to_datetime(df.iloc[0, 0]).date()
    max_date = pd.to_datetime(df.iloc[0, 1]).date()
    return (min_date, max_date)


# ============================================================================
# Data Quality Functions
# ============================================================================

@st.cache_data(ttl=3600)
def get_data_quality_report(db_path: str) -> dict:
    """
    Generate a comprehensive data quality report.
    
    Returns dictionary with various quality metrics and issues.
    """
    conn = get_db_connection(db_path)
    
    report = {}
    
    # 1. Missing values count
    actual_query = """
    SELECT 
        SUM(CASE WHEN DEVICE_ID IS NULL THEN 1 ELSE 0 END) as missing_device_id,
        SUM(CASE WHEN GEN_MW IS NULL THEN 1 ELSE 0 END) as missing_gen_mw,
        SUM(CASE WHEN GEN_MW_MAX IS NULL THEN 1 ELSE 0 END) as missing_gen_mw_max,
        SUM(CASE WHEN STATUS IS NULL THEN 1 ELSE 0 END) as missing_status,
        SUM(CASE WHEN FUEL_TYPE IS NULL THEN 1 ELSE 0 END) as missing_fuel_type,
        SUM(CASE WHEN PLANT_NAME IS NULL THEN 1 ELSE 0 END) as missing_plant_name
    FROM actual_gen
    """
    report['missing_values_actual'] = pd.read_sql_query(actual_query, conn).to_dict('records')[0]
    
    forecast_query = """
    SELECT 
        SUM(CASE WHEN DEVICE_ID IS NULL THEN 1 ELSE 0 END) as missing_device_id,
        SUM(CASE WHEN GEN_MW IS NULL THEN 1 ELSE 0 END) as missing_gen_mw,
        SUM(CASE WHEN GEN_MW_MAX IS NULL THEN 1 ELSE 0 END) as missing_gen_mw_max,
        SUM(CASE WHEN STATUS IS NULL THEN 1 ELSE 0 END) as missing_status,
        SUM(CASE WHEN FUEL_TYPE IS NULL THEN 1 ELSE 0 END) as missing_fuel_type,
        SUM(CASE WHEN PLANT_NAME IS NULL THEN 1 ELSE 0 END) as missing_plant_name
    FROM forecast_gen
    """
    report['missing_values_forecast'] = pd.read_sql_query(forecast_query, conn).to_dict('records')[0]
    
    # 2. Count of actual-only and forecast-only records
    match_query = """
    SELECT
        (SELECT COUNT(*) FROM actual_gen WHERE NOT EXISTS (
            SELECT 1 FROM forecast_gen f 
            WHERE f.DATE_TIME = actual_gen.DATE_TIME AND f.DEVICE_ID = actual_gen.DEVICE_ID
        )) as actual_only_count,
        (SELECT COUNT(*) FROM forecast_gen WHERE NOT EXISTS (
            SELECT 1 FROM actual_gen a
            WHERE a.DATE_TIME = forecast_gen.DATE_TIME AND a.DEVICE_ID = forecast_gen.DEVICE_ID
        )) as forecast_only_count
    """
    match_info = pd.read_sql_query(match_query, conn).to_dict('records')[0]
    report['unmatched'] = match_info
    
    # 3. Duplicates by DATE_TIME + DEVICE_ID
    dup_query = """
    SELECT 'actual' as table_name, COUNT(*) as duplicate_count
    FROM (
        SELECT DATE_TIME, DEVICE_ID, COUNT(*) as cnt
        FROM actual_gen
        GROUP BY DATE_TIME, DEVICE_ID
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'forecast' as table_name, COUNT(*) as duplicate_count
    FROM (
        SELECT DATE_TIME, DEVICE_ID, COUNT(*) as cnt
        FROM forecast_gen
        GROUP BY DATE_TIME, DEVICE_ID
        HAVING COUNT(*) > 1
    )
    """
    duplicates = pd.read_sql_query(dup_query, conn)
    report['duplicates'] = duplicates
    
    # 4. Negative values
    negative_query = """
    SELECT
        (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW < 0) as actual_negative_mw,
        (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW_MAX < 0) as actual_negative_max,
        (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW < 0) as forecast_negative_mw,
        (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW_MAX < 0) as forecast_negative_max
    """
    report['negative_values'] = pd.read_sql_query(negative_query, conn).to_dict('records')[0]
    
    # 5. Capacity violations (Actual > Max)
    capacity_query = """
    SELECT
        (SELECT COUNT(*) FROM actual_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0) as actual_exceeds_capacity,
        (SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0) as forecast_exceeds_capacity
    """
    report['capacity_violations'] = pd.read_sql_query(capacity_query, conn).to_dict('records')[0]
    
    # 6. Status distributions
    actual_status_query = """
    SELECT STATUS, COUNT(*) as count
    FROM actual_gen
    WHERE STATUS IS NOT NULL
    GROUP BY STATUS
    ORDER BY count DESC
    """
    report['actual_status_dist'] = pd.read_sql_query(actual_status_query, conn)
    
    forecast_status_query = """
    SELECT STATUS, COUNT(*) as count
    FROM forecast_gen
    WHERE STATUS IS NOT NULL
    GROUP BY STATUS
    ORDER BY count DESC
    """
    report['forecast_status_dist'] = pd.read_sql_query(forecast_status_query, conn)
    
    return report


# ============================================================================
# Formatting Functions
# ============================================================================

def format_mw(value: float) -> str:
    """Format a value as megawatts with 2 decimal places."""
    if pd.isna(value):
        return "N/A"
    return f"{value:,.2f} MW"


def format_percentage(value: float) -> str:
    """Format a value as percentage with 2 decimal places."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimal places."""
    if pd.isna(value):
        return "N/A"
    if decimals == 0:
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"
