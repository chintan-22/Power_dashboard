"""
Preprocessing pipeline for the Durable Power Dashboard.

Builds a dashboard-ready analytics layer from assignment.db:
raw SQLite tables -> matched Parquet dataset -> pre-aggregated summaries.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError as exc:  # pragma: no cover - exercised only without pyarrow
    raise SystemExit(
        "pyarrow is required for preprocessing. Install it with: pip install pyarrow"
    ) from exc


PIPELINE_VERSION = "1.1.0"

OUTPUT_FILES = [
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


# Core SQL extraction query.
#
# This is the primary SQL work for the assignment: it joins the two raw SQLite
# tables into a matched actual/forecast dataset. The dashboard intentionally
# uses only records that exist in both tables, so this must remain an INNER JOIN
# on DATE_TIME + DEVICE_ID. The resulting Parquet layer is an optimization on
# top of this SQL query, not a replacement for the SQL extraction requirement.
JOIN_QUERY = """
SELECT
    a.DATE_TIME AS DATE_TIME,
    a.MARKET_DATE AS MARKET_DATE,
    a.DEVICE_ID AS DEVICE_ID,
    COALESCE(a.PLANT_NAME, f.PLANT_NAME, 'Unknown Plant') AS PLANT_NAME,
    COALESCE(a.FUEL_TYPE, f.FUEL_TYPE, 'Unknown Fuel') AS FUEL_TYPE,
    a.GEN_MW AS ACTUAL_MW,
    f.GEN_MW AS FORECAST_MW,
    a.GEN_MW_MAX AS ACTUAL_GEN_MW_MAX,
    f.GEN_MW_MAX AS FORECAST_GEN_MW_MAX,
    a.STATUS AS ACTUAL_STATUS,
    f.STATUS AS FORECAST_STATUS
FROM actual_gen a
INNER JOIN forecast_gen f
    ON a.DATE_TIME = f.DATE_TIME
   AND a.DEVICE_ID = f.DEVICE_ID
"""


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_actual_market_date ON actual_gen (MARKET_DATE)",
    "CREATE INDEX IF NOT EXISTS idx_forecast_market_date ON forecast_gen (MARKET_DATE)",
    "CREATE INDEX IF NOT EXISTS idx_actual_datetime_device ON actual_gen (DATE_TIME, DEVICE_ID)",
    "CREATE INDEX IF NOT EXISTS idx_forecast_datetime_device ON forecast_gen (DATE_TIME, DEVICE_ID)",
    "CREATE INDEX IF NOT EXISTS idx_actual_device_id ON actual_gen (DEVICE_ID)",
    "CREATE INDEX IF NOT EXISTS idx_forecast_device_id ON forecast_gen (DEVICE_ID)",
    "CREATE INDEX IF NOT EXISTS idx_actual_plant_name ON actual_gen (PLANT_NAME)",
    "CREATE INDEX IF NOT EXISTS idx_forecast_plant_name ON forecast_gen (PLANT_NAME)",
    "CREATE INDEX IF NOT EXISTS idx_actual_fuel_type ON actual_gen (FUEL_TYPE)",
    "CREATE INDEX IF NOT EXISTS idx_forecast_fuel_type ON forecast_gen (FUEL_TYPE)",
]


def log(message: str) -> None:
    """Print a timestamped progress message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the dashboard analytics layer from assignment.db."
    )
    parser.add_argument("--db", default="assignment.db", help="Path to SQLite database.")
    parser.add_argument("--out", default="data", help="Output folder for analytics files.")
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Rows per SQLite chunk while building matched_generation.parquet.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing analytics files.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip creating SQLite performance indexes.",
    )
    return parser.parse_args()


def connect_database(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def confirm_tables(conn: sqlite3.Connection) -> None:
    required = {"actual_gen", "forecast_gen"}
    found = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing = sorted(required - found)
    if missing:
        raise RuntimeError(f"Missing required table(s): {', '.join(missing)}")


def run_integrity_check(conn: sqlite3.Connection) -> None:
    result = conn.execute("PRAGMA integrity_check").fetchone()
    status = result[0] if result else "unknown"
    if status != "ok":
        log(f"WARNING: database integrity_check returned: {status}")
    else:
        log("Database integrity check passed.")


def create_indexes(conn: sqlite3.Connection) -> None:
    for statement in INDEX_STATEMENTS:
        conn.execute(statement)
    conn.execute("ANALYZE")
    conn.commit()


def prepare_output_folder(out_dir: Path, force: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [out_dir / name for name in OUTPUT_FILES if (out_dir / name).exists()]
    if existing and not force:
        files = "\n".join(f"  - {path}" for path in existing)
        raise FileExistsError(
            "Preprocessed files already exist. Use --force to overwrite:\n" + files
        )

    staging_dir = out_dir / ".preprocess_tmp"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    return staging_dir


def publish_outputs(staging_dir: Path, out_dir: Path) -> None:
    """Publish completed outputs from staging only after validation succeeds."""
    for filename in OUTPUT_FILES:
        src = staging_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"Expected output was not created: {src}")

    for filename in OUTPUT_FILES:
        src = staging_dir / filename
        dst = out_dir / filename
        if dst.exists():
            dst.unlink()
        src.replace(dst)

    shutil.rmtree(staging_dir)


def clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Clean one joined chunk and add dashboard calculation fields."""
    chunk = chunk.copy()

    chunk["DATE_TIME"] = pd.to_datetime(chunk["DATE_TIME"], errors="coerce")
    chunk["MARKET_DATE"] = pd.to_datetime(chunk["MARKET_DATE"], errors="coerce")

    for column, fallback in {
        "PLANT_NAME": "Unknown Plant",
        "FUEL_TYPE": "Unknown Fuel",
    }.items():
        chunk[column] = (
            chunk[column]
            .replace(r"^\s*$", pd.NA, regex=True)
            .fillna(fallback)
        )

    numeric_columns = [
        "ACTUAL_MW",
        "FORECAST_MW",
        "ACTUAL_GEN_MW_MAX",
        "FORECAST_GEN_MW_MAX",
    ]
    for column in numeric_columns:
        chunk[column] = pd.to_numeric(chunk[column], errors="coerce")

    chunk["ERROR_MW"] = chunk["ACTUAL_MW"] - chunk["FORECAST_MW"]
    chunk["ABS_ERROR_MW"] = chunk["ERROR_MW"].abs()
    chunk["SQUARED_ERROR"] = chunk["ERROR_MW"] ** 2

    chunk["APE"] = np.where(
        chunk["ACTUAL_MW"] > 0,
        (chunk["ABS_ERROR_MW"] / chunk["ACTUAL_MW"]) * 100,
        np.nan,
    )
    chunk["CAPACITY_UTILIZATION"] = np.where(
        chunk["ACTUAL_GEN_MW_MAX"] > 0,
        (chunk["ACTUAL_MW"] / chunk["ACTUAL_GEN_MW_MAX"]) * 100,
        np.nan,
    )

    chunk["DAY"] = chunk["MARKET_DATE"].dt.normalize()
    chunk["WEEK"] = (
        chunk["MARKET_DATE"]
        - pd.to_timedelta(chunk["MARKET_DATE"].dt.weekday, unit="D")
    ).dt.normalize()
    chunk["MONTH"] = chunk["MARKET_DATE"].dt.to_period("M").dt.to_timestamp()

    return chunk


def write_matched_parquet(
    conn: sqlite3.Connection,
    out_path: Path,
    chunksize: int,
) -> dict:
    writer = None
    matched_rows = 0
    date_min = None
    date_max = None
    devices = set()
    plants = set()
    fuels = set()

    try:
        for chunk_number, chunk in enumerate(
            # Execute the SQL join in chunks so the pipeline can process the
            # large SQLite result set without loading every matched row into
            # memory at once.
            pd.read_sql_query(JOIN_QUERY, conn, chunksize=chunksize),
            start=1,
        ):
            cleaned = clean_chunk(chunk)
            matched_rows += len(cleaned)

            if not cleaned.empty:
                chunk_min = cleaned["DAY"].min()
                chunk_max = cleaned["DAY"].max()
                date_min = chunk_min if date_min is None else min(date_min, chunk_min)
                date_max = chunk_max if date_max is None else max(date_max, chunk_max)
                devices.update(cleaned["DEVICE_ID"].dropna().unique())
                plants.update(cleaned["PLANT_NAME"].dropna().unique())
                fuels.update(cleaned["FUEL_TYPE"].dropna().unique())

            table = pa.Table.from_pandas(cleaned, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(out_path, table.schema, compression="snappy")
            writer.write_table(table)

            log(f"Processed chunk {chunk_number:,}; total rows: {matched_rows:,}")
    finally:
        if writer is not None:
            writer.close()

    return {
        "matched_row_count": matched_rows,
        "date_min": None if date_min is None else str(pd.Timestamp(date_min).date()),
        "date_max": None if date_max is None else str(pd.Timestamp(date_max).date()),
        "unique_devices": len(devices),
        "unique_plants": len(plants),
        "fuel_types": len(fuels),
    }


def add_forecast_metrics(summary: pd.DataFrame) -> pd.DataFrame:
    summary = summary.copy()
    summary["forecast_difference_mw"] = (
        summary["total_actual_mw"] - summary["total_forecast_mw"]
    )
    summary["mae"] = summary["total_abs_error"] / summary["observation_count"]
    summary["rmse"] = np.sqrt(
        summary["squared_error_sum"] / summary["observation_count"]
    )
    summary["bias"] = summary["error_sum"] / summary["observation_count"]
    summary["mape"] = summary["ape_sum"] / summary["ape_count"].replace(0, np.nan)
    summary["wape"] = (
        summary["total_abs_error"]
        / summary["total_actual_mw_magnitude"].replace(0, np.nan)
    ) * 100
    summary["energy_accuracy_pct"] = (100 - summary["wape"]).clip(lower=0, upper=100)
    summary["forecast_accuracy_pct"] = summary["energy_accuracy_pct"]
    summary["activity_mw"] = (
        summary["total_actual_mw_magnitude"]
        + summary["total_forecast_mw_magnitude"]
    )
    summary["avg_capacity_utilization"] = (
        summary["capacity_utilization_sum"]
        / summary["capacity_utilization_count"].replace(0, np.nan)
    )

    drop_cols = [
        "error_sum",
        "squared_error_sum",
        "ape_sum",
        "ape_count",
        "capacity_utilization_sum",
        "capacity_utilization_count",
    ]
    return summary.drop(columns=drop_cols)


def create_summary(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    df["ACTUAL_MW_ABS"] = df["ACTUAL_MW"].abs()
    df["FORECAST_MW_ABS"] = df["FORECAST_MW"].abs()
    df["IS_ACTIVE_OBSERVATION"] = (
        (df["ACTUAL_MW_ABS"] > 0)
        | (df["FORECAST_MW_ABS"] > 0)
    ).astype(int)

    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            total_actual_mw=("ACTUAL_MW", "sum"),
            total_forecast_mw=("FORECAST_MW", "sum"),
            total_actual_mw_magnitude=("ACTUAL_MW_ABS", "sum"),
            total_forecast_mw_magnitude=("FORECAST_MW_ABS", "sum"),
            active_observation_count=("IS_ACTIVE_OBSERVATION", "sum"),
            error_sum=("ERROR_MW", "sum"),
            total_abs_error=("ABS_ERROR_MW", "sum"),
            squared_error_sum=("SQUARED_ERROR", "sum"),
            ape_sum=("APE", "sum"),
            ape_count=("APE", "count"),
            capacity_utilization_sum=("CAPACITY_UTILIZATION", "sum"),
            capacity_utilization_count=("CAPACITY_UTILIZATION", "count"),
            observation_count=("DEVICE_ID", "size"),
            unique_devices=("DEVICE_ID", "nunique"),
            unique_plants=("PLANT_NAME", "nunique"),
        )
        .reset_index()
    )
    return add_forecast_metrics(grouped)


def create_summaries(matched_path: Path, out_dir: Path) -> None:
    df = pd.read_parquet(matched_path)

    summary_specs = {
        "daily_summary.parquet": ["DAY", "FUEL_TYPE"],
        "weekly_summary.parquet": ["WEEK", "FUEL_TYPE"],
        "monthly_summary.parquet": ["MONTH", "FUEL_TYPE"],
        "plant_summary.parquet": ["PLANT_NAME", "FUEL_TYPE"],
        "device_summary.parquet": ["DEVICE_ID", "PLANT_NAME", "FUEL_TYPE"],
        "fuel_summary.parquet": ["FUEL_TYPE"],
    }

    for filename, group_cols in summary_specs.items():
        summary = create_summary(df, group_cols)
        summary.to_parquet(out_dir / filename, index=False, engine="pyarrow", compression="snappy")
        log(f"Wrote {filename} ({len(summary):,} rows)")


def validate_january_totals(matched_path: Path, out_dir: Path) -> None:
    """Print January matched and monthly summary totals for sanity checking."""
    matched = pd.read_parquet(
        matched_path,
        columns=["DAY", "MONTH", "ACTUAL_MW", "FORECAST_MW"],
    )
    matched["DAY"] = pd.to_datetime(matched["DAY"], errors="coerce")
    matched["MONTH"] = pd.to_datetime(matched["MONTH"], errors="coerce")

    jan_start = pd.Timestamp("2025-01-01")
    feb_start = pd.Timestamp("2025-02-01")
    january = matched[(matched["DAY"] >= jan_start) & (matched["DAY"] < feb_start)]

    monthly = pd.read_parquet(out_dir / "monthly_summary.parquet")
    monthly["MONTH"] = pd.to_datetime(monthly["MONTH"], errors="coerce")
    january_monthly = monthly[monthly["MONTH"] == jan_start]

    jan_matched_rows = len(january)
    jan_actual = january["ACTUAL_MW"].sum()
    jan_forecast = january["FORECAST_MW"].sum()
    jan_summary_actual = january_monthly["total_actual_mw"].sum()
    jan_summary_forecast = january_monthly["total_forecast_mw"].sum()

    log("January validation")
    log(f"  January matched row count: {jan_matched_rows:,}")
    log(f"  January total ACTUAL_MW from matched_generation: {jan_actual:,.2f}")
    log(f"  January total FORECAST_MW from matched_generation: {jan_forecast:,.2f}")
    log(f"  January total actual from monthly_summary: {jan_summary_actual:,.2f}")
    log(f"  January total forecast from monthly_summary: {jan_summary_forecast:,.2f}")

    if jan_forecast == 0 or jan_summary_forecast == 0:
        log("WARNING: January total forecast is 0 after preprocessing. Investigate join and summary inputs.")


def _compare_summary_totals(
    matched: pd.DataFrame,
    summary: pd.DataFrame,
    matched_group_cols: list[str],
    summary_group_cols: list[str],
    label: str,
    tolerance: float = 1e-6,
) -> None:
    matched_grouped = (
        matched.groupby(matched_group_cols, dropna=False)
        .agg(
            expected_total_actual_mw=("ACTUAL_MW", "sum"),
            expected_total_forecast_mw=("FORECAST_MW", "sum"),
            expected_observation_count=("DEVICE_ID", "size"),
        )
        .reset_index()
    )
    summary_grouped = (
        summary.groupby(summary_group_cols, dropna=False)
        .agg(
            total_actual_mw=("total_actual_mw", "sum"),
            total_forecast_mw=("total_forecast_mw", "sum"),
            observation_count=("observation_count", "sum"),
        )
        .reset_index()
    )

    merged = matched_grouped.merge(
        summary_grouped,
        left_on=matched_group_cols,
        right_on=summary_group_cols,
        how="outer",
        indicator=True,
    )

    actual_diff = (
        merged["expected_total_actual_mw"] - merged["total_actual_mw"]
    ).abs()
    forecast_diff = (
        merged["expected_total_forecast_mw"] - merged["total_forecast_mw"]
    ).abs()
    count_diff = (
        merged["expected_observation_count"] - merged["observation_count"]
    ).abs()

    mismatches = merged[
        (merged["_merge"] != "both")
        | (actual_diff > tolerance)
        | (forecast_diff > tolerance)
        | (count_diff > 0)
    ]

    if mismatches.empty:
        log(f"  {label}: OK")
        return

    log(f"  WARNING: {label} summary mismatch count: {len(mismatches):,}")
    log(f"    Max actual diff: {actual_diff.max():,.8f}")
    log(f"    Max forecast diff: {forecast_diff.max():,.8f}")
    log(f"    Max count diff: {count_diff.max():,.0f}")
    preview_cols = matched_group_cols + [
        "expected_total_actual_mw",
        "total_actual_mw",
        "expected_total_forecast_mw",
        "total_forecast_mw",
        "expected_observation_count",
        "observation_count",
        "_merge",
    ]
    log("    First mismatches:")
    print(mismatches[preview_cols].head(10).to_string(index=False), flush=True)
    raise RuntimeError(f"{label} summary validation failed")


def validate_summaries(matched_path: Path, out_dir: Path) -> None:
    """Validate summary totals against the cleaned matched Parquet dataset."""
    log("Validating summary consistency")
    matched = pd.read_parquet(
        matched_path,
        columns=[
            "DAY",
            "MONTH",
            "PLANT_NAME",
            "DEVICE_ID",
            "ACTUAL_MW",
            "FORECAST_MW",
        ],
    )
    matched["DAY"] = pd.to_datetime(matched["DAY"], errors="coerce")
    matched["MONTH"] = pd.to_datetime(matched["MONTH"], errors="coerce")

    validations = [
        ("daily_summary.parquet", ["DAY"], ["DAY"], "daily"),
        ("monthly_summary.parquet", ["MONTH"], ["MONTH"], "monthly"),
        ("plant_summary.parquet", ["PLANT_NAME"], ["PLANT_NAME"], "plant"),
        ("device_summary.parquet", ["DEVICE_ID"], ["DEVICE_ID"], "device"),
    ]

    for filename, matched_cols, summary_cols, label in validations:
        summary = pd.read_parquet(out_dir / filename)
        for col in summary_cols:
            if col in ["DAY", "MONTH"]:
                summary[col] = pd.to_datetime(summary[col], errors="coerce")
        _compare_summary_totals(
            matched,
            summary,
            matched_cols,
            summary_cols,
            label,
        )


def scalar(conn: sqlite3.Connection, query: str) -> int:
    value = conn.execute(query).fetchone()[0]
    return 0 if value is None else int(value)


def write_data_quality_summary(conn: sqlite3.Connection, out_path: Path) -> None:
    # These SQL validation queries make the raw-data audit trail explicit.
    # They verify row counts, matched/unmatched records, duplicate keys,
    # missing metadata, negative generation, capacity issues, and status mixes
    # directly against the SQLite source tables before the dashboard reads
    # the optimized Parquet layer.
    rows = [
        ("actual_row_count", scalar(conn, "SELECT COUNT(*) FROM actual_gen")),
        ("forecast_row_count", scalar(conn, "SELECT COUNT(*) FROM forecast_gen")),
        (
            "matched_row_count",
            scalar(
                conn,
                """
                SELECT COUNT(*)
                FROM actual_gen a
                INNER JOIN forecast_gen f
                    ON a.DATE_TIME = f.DATE_TIME
                   AND a.DEVICE_ID = f.DEVICE_ID
                """,
            ),
        ),
        (
            "actual_only_count",
            scalar(
                conn,
                """
                SELECT COUNT(*)
                FROM actual_gen a
                WHERE NOT EXISTS (
                    SELECT 1 FROM forecast_gen f
                    WHERE f.DATE_TIME = a.DATE_TIME
                      AND f.DEVICE_ID = a.DEVICE_ID
                )
                """,
            ),
        ),
        (
            "forecast_only_count",
            scalar(
                conn,
                """
                SELECT COUNT(*)
                FROM forecast_gen f
                WHERE NOT EXISTS (
                    SELECT 1 FROM actual_gen a
                    WHERE a.DATE_TIME = f.DATE_TIME
                      AND a.DEVICE_ID = f.DEVICE_ID
                )
                """,
            ),
        ),
        (
            "duplicate_actual_records_by_datetime_device",
            scalar(
                conn,
                """
                SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                    SELECT DATE_TIME, DEVICE_ID, COUNT(*) as cnt
                    FROM actual_gen
                    GROUP BY DATE_TIME, DEVICE_ID
                    HAVING COUNT(*) > 1
                )
                """,
            ),
        ),
        (
            "duplicate_forecast_records_by_datetime_device",
            scalar(
                conn,
                """
                SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                    SELECT DATE_TIME, DEVICE_ID, COUNT(*) as cnt
                    FROM forecast_gen
                    GROUP BY DATE_TIME, DEVICE_ID
                    HAVING COUNT(*) > 1
                )
                """,
            ),
        ),
        (
            "missing_actual_plant_name_count",
            scalar(
                conn,
                "SELECT COUNT(*) FROM actual_gen WHERE PLANT_NAME IS NULL OR TRIM(PLANT_NAME) = ''",
            ),
        ),
        (
            "missing_forecast_plant_name_count",
            scalar(
                conn,
                "SELECT COUNT(*) FROM forecast_gen WHERE PLANT_NAME IS NULL OR TRIM(PLANT_NAME) = ''",
            ),
        ),
        (
            "missing_actual_fuel_type_count",
            scalar(
                conn,
                "SELECT COUNT(*) FROM actual_gen WHERE FUEL_TYPE IS NULL OR TRIM(FUEL_TYPE) = ''",
            ),
        ),
        (
            "missing_forecast_fuel_type_count",
            scalar(
                conn,
                "SELECT COUNT(*) FROM forecast_gen WHERE FUEL_TYPE IS NULL OR TRIM(FUEL_TYPE) = ''",
            ),
        ),
        ("missing_actual_gen_mw_count", scalar(conn, "SELECT COUNT(*) FROM actual_gen WHERE GEN_MW IS NULL")),
        ("missing_forecast_gen_mw_count", scalar(conn, "SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW IS NULL")),
        ("negative_actual_gen_mw_count", scalar(conn, "SELECT COUNT(*) FROM actual_gen WHERE GEN_MW < 0")),
        ("negative_forecast_gen_mw_count", scalar(conn, "SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW < 0")),
        (
            "actual_gen_mw_greater_than_gen_mw_max_count",
            scalar(conn, "SELECT COUNT(*) FROM actual_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0"),
        ),
        (
            "forecast_gen_mw_greater_than_gen_mw_max_count",
            scalar(conn, "SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW > GEN_MW_MAX AND GEN_MW_MAX > 0"),
        ),
        (
            "zero_or_missing_actual_gen_mw_max_count",
            scalar(conn, "SELECT COUNT(*) FROM actual_gen WHERE GEN_MW_MAX IS NULL OR GEN_MW_MAX = 0"),
        ),
        (
            "zero_or_missing_forecast_gen_mw_max_count",
            scalar(conn, "SELECT COUNT(*) FROM forecast_gen WHERE GEN_MW_MAX IS NULL OR GEN_MW_MAX = 0"),
        ),
    ]

    for prefix, table in [("actual", "actual_gen"), ("forecast", "forecast_gen")]:
        status_rows = conn.execute(
            f"""
            SELECT STATUS, COUNT(*)
            FROM {table}
            GROUP BY STATUS
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()
        for status, count in status_rows:
            rows.append((f"{prefix}_status_{status}", count))

    pd.DataFrame(rows, columns=["metric", "value"]).to_csv(out_path, index=False)


def write_metadata(
    out_path: Path,
    db_path: Path,
    out_dir: Path,
    chunk_size: int,
    matched_stats: dict,
) -> None:
    metadata = {
        "preprocessing_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_database_path": str(db_path.resolve()),
        "source_database_file_size": os.path.getsize(db_path),
        "matched_row_count": matched_stats["matched_row_count"],
        "output_file_names": OUTPUT_FILES,
        "date_min": matched_stats["date_min"],
        "date_max": matched_stats["date_max"],
        "number_of_unique_devices": matched_stats["unique_devices"],
        "number_of_unique_plants": matched_stats["unique_plants"],
        "number_of_fuel_types": matched_stats["fuel_types"],
        "chunk_size_used": chunk_size,
        "pipeline_version": PIPELINE_VERSION,
        "output_directory": str(out_dir.resolve()),
    }
    out_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    out_dir = Path(args.out)

    log("Starting preprocessing")
    log("Checking database")

    staging_dir = prepare_output_folder(out_dir, args.force)
    conn = connect_database(db_path)

    try:
        confirm_tables(conn)
        run_integrity_check(conn)

        if args.skip_index:
            log("Skipping index creation")
        else:
            log("Creating indexes")
            create_indexes(conn)

        matched_path = staging_dir / "matched_generation.parquet"
        log("Processing joined chunks")
        matched_stats = write_matched_parquet(conn, matched_path, args.chunksize)

        log("Saving matched_generation.parquet")
        log(f"Matched rows written: {matched_stats['matched_row_count']:,}")

        log("Creating summaries")
        create_summaries(matched_path, staging_dir)

        log("Running January validation")
        validate_january_totals(matched_path, staging_dir)

        validate_summaries(matched_path, staging_dir)

        log("Creating data quality summary")
        write_data_quality_summary(conn, staging_dir / "data_quality_summary.csv")

        log("Writing metadata")
        write_metadata(
            staging_dir / "preprocess_metadata.json",
            db_path,
            out_dir,
            args.chunksize,
            matched_stats,
        )

        log("Publishing completed files")
        publish_outputs(staging_dir, out_dir)

        log("Done")
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
