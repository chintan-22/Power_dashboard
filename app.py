"""
Durable Electric Power - Generation Forecast Dashboard.

This dashboard reads from a preprocessed Parquet analytics layer created by
preprocess.py. The raw SQLite database is no longer joined during interaction.
"""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

import charts
import styles
import utils


st.set_page_config(
    page_title="Durable Power Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

styles.inject_custom_css()


# ============================================================================
# Paths and Analytics Layer
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

files_ready, missing_files = utils.check_preprocessed_files(DATA_DIR)
if not files_ready:
    st.warning("Preprocessed data files not found. Run: python preprocess.py --force")
    st.caption("Missing files: " + ", ".join(missing_files))
    st.code("python preprocess.py --db assignment.db --out data --chunksize 100000 --force")
    st.stop()

with st.spinner("Loading preprocessed analytics layer..."):
    analytics = utils.load_analytics_layer(DATA_DIR)

matched_df = analytics["matched"]
metadata = analytics.get("metadata", {})

analytics_layer_message = (
    "Using preprocessed analytics layer for faster filtering and dashboard responsiveness."
)


# ============================================================================
# Sidebar Filters
# ============================================================================

min_date = pd.to_datetime(metadata.get("date_min", matched_df["DAY"].min())).date()
max_date = pd.to_datetime(metadata.get("date_max", matched_df["DAY"].max())).date()

plant_options = sorted(matched_df["PLANT_NAME"].dropna().unique().tolist())
device_options = sorted(matched_df["DEVICE_ID"].dropna().unique().tolist())
fuel_options = sorted(matched_df["FUEL_TYPE"].dropna().unique().tolist())

styles.control_panel_header()

with st.sidebar.form("filter_form"):
    st.markdown("#### Dispatch Filters")
    st.caption("Adjust controls, then apply once to refresh the command center.")

    date_range = st.date_input(
        "Market Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Select the date range for analysis.",
    )

    plants = st.multiselect(
        "Plant Name",
        options=plant_options,
        help="Filter by generating plant. Leave empty for all.",
    )

    devices = st.multiselect(
        "Device ID",
        options=device_options,
        help="Filter by generator device. Leave empty for all.",
    )

    fuel_types = st.multiselect(
        "Fuel Type",
        options=fuel_options,
        help="Filter by fuel type. Leave empty for all.",
    )

    exclude_unknown = st.checkbox(
        "Exclude unknown plant/fuel",
        value=False,
        help="Remove rows where plant or fuel type was unavailable in the raw data.",
    )

    error_threshold_value = st.number_input(
        "Minimum absolute error (MW)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        help="Use 0 to include all rows.",
    )

    frequency = st.selectbox(
        "Trend Frequency",
        options=["Daily", "Weekly", "Monthly"],
        index=0,
    )

    ranking_level = st.selectbox(
        "Ranking Level",
        options=["Device", "Plant", "Fuel Type"],
        index=0,
    )

    ranking_metric = st.selectbox(
        "Ranking Metric",
        options=["MAE", "RMSE", "MAPE", "Bias"],
        index=0,
    )

    top_n = st.slider("Top N", min_value=5, max_value=50, value=10, step=5)

    st.form_submit_button("Apply Filters", use_container_width=True)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

error_threshold = error_threshold_value if error_threshold_value > 0 else None

filtered_df = utils.filter_matched_data(
    matched_df,
    (start_date, end_date),
    plants=plants,
    devices=devices,
    fuel_types=fuel_types,
    error_threshold=error_threshold,
    exclude_unknown=exclude_unknown,
)

if filtered_df.empty:
    st.warning("No matching data found. Adjust filters and click Apply Filters.")
    st.stop()

metrics = utils.calculate_metrics_from_filtered_data(filtered_df)
rankings, best_rankings, worst_rankings = utils.calculate_rankings(
    filtered_df,
    ranking_level,
    ranking_metric,
    top_n,
)


# ============================================================================
# Helpers
# ============================================================================

def build_trend_data() -> tuple[pd.DataFrame, str]:
    """Use pre-aggregated trend summaries unless plant/device/error filters require row data."""
    summary_map = {
        "Daily": ("daily", "DAY"),
        "Weekly": ("weekly", "WEEK"),
        "Monthly": ("monthly", "MONTH"),
    }
    summary_key, date_col = summary_map[frequency]

    can_use_summary = (
        not plants
        and not devices
        and error_threshold is None
        and not exclude_unknown
    )
    if can_use_summary:
        summary_df = utils.filter_summary_data(
            analytics[summary_key],
            date_col,
            (start_date, end_date),
            fuel_types=fuel_types,
        )
        return summary_df, date_col

    grouped = (
        filtered_df.groupby([date_col, "FUEL_TYPE"], as_index=False)
        .agg(
            total_actual_mw=("ACTUAL_MW", "sum"),
            total_forecast_mw=("FORECAST_MW", "sum"),
            observation_count=("DEVICE_ID", "size"),
        )
    )
    return grouped, date_col


def ranking_label_column(level: str) -> str:
    if level == "Device":
        return "DEVICE_ID"
    if level == "Plant":
        return "PLANT_NAME"
    return "FUEL_TYPE"


def error_status(value: float, warning: float, danger: float) -> str:
    """Return a visual-only severity for forecast error KPI cards."""
    if pd.isna(value):
        return "neutral"
    if value >= danger:
        return "danger"
    if value >= warning:
        return "warning"
    return "success"


def rmse_status(mae: float, rmse: float) -> str:
    """Highlight RMSE when it suggests unusually large misses."""
    if pd.isna(mae) or pd.isna(rmse) or mae <= 0:
        return "neutral"
    ratio = rmse / mae
    if ratio >= 2.0:
        return "danger"
    if ratio >= 1.5:
        return "warning"
    return "success"


def bias_status(bias: float, mae: float) -> str:
    """Highlight directional bias relative to the average absolute error."""
    if pd.isna(bias) or pd.isna(mae):
        return "neutral"
    if abs(bias) <= max(mae * 0.15, 1.0):
        return "success"
    if abs(bias) <= max(mae * 0.50, 3.0):
        return "warning"
    return "danger"


def accuracy_status(value: float) -> str:
    """Return a visual-only severity for energy accuracy."""
    if pd.isna(value):
        return "neutral"
    if value >= 90:
        return "success"
    if value >= 75:
        return "warning"
    return "danger"


def insight_treatment(insight: dict) -> tuple[str, str]:
    """Map generated insight text to an operational alert style."""
    title = str(insight.get("title", "")).lower()
    detail = str(insight.get("detail", "")).lower()

    if "highest-error" in title:
        return "danger", "RISK"
    if "best-performing" in title:
        return "success", "STABLE"
    if "large-miss" in title:
        return ("warning", "RISK") if "much higher" in detail else ("success", "STABLE")
    if "capacity" in title:
        return "info", "OPERATIONS"
    if "difference" in title:
        return "info", "INSIGHT"
    if "tendency" in title:
        return ("success", "STABLE") if "balanced" in detail else ("warning", "INSIGHT")
    if "no data" in title:
        return "warning", "ACTION"
    return "info", "INSIGHT"


def data_quality_metric(dq_df: pd.DataFrame, metric_name: str) -> float:
    """Read a numeric data-quality metric from the summary table."""
    values = dq_df.loc[dq_df["metric"] == metric_name, "value"]
    if values.empty:
        return 0.0
    value = pd.to_numeric(values.iloc[0], errors="coerce")
    if pd.isna(value):
        return 0.0
    return float(value)


def show_data_quality_alerts(dq_df: pd.DataFrame) -> None:
    """Render severity-coded data quality cards."""
    matched_rows = data_quality_metric(dq_df, "matched_row_count")
    missing_metadata = sum(
        data_quality_metric(dq_df, metric_name)
        for metric_name in [
            "missing_actual_plant_name_count",
            "missing_forecast_plant_name_count",
            "missing_actual_fuel_type_count",
            "missing_forecast_fuel_type_count",
        ]
    )
    negative_generation = (
        data_quality_metric(dq_df, "negative_actual_gen_mw_count")
        + data_quality_metric(dq_df, "negative_forecast_gen_mw_count")
    )
    capacity_violations = (
        data_quality_metric(dq_df, "actual_gen_mw_greater_than_gen_mw_max_count")
        + data_quality_metric(dq_df, "forecast_gen_mw_greater_than_gen_mw_max_count")
    )
    missing_capacity = (
        data_quality_metric(dq_df, "zero_or_missing_actual_gen_mw_max_count")
        + data_quality_metric(dq_df, "zero_or_missing_forecast_gen_mw_max_count")
    )
    unmatched_rows = (
        data_quality_metric(dq_df, "actual_only_count")
        + data_quality_metric(dq_df, "forecast_only_count")
    )

    cards = [
        ("Matched Records", f"{matched_rows:,.0f}", "Rows available in the analytics layer.", "success"),
        ("Unmatched Records", f"{unmatched_rows:,.0f}", "Actual-only plus forecast-only raw rows.", "info"),
        ("Missing Metadata", f"{missing_metadata:,.0f}", "Plant or fuel values filled as unknown.", "warning" if missing_metadata else "success"),
        ("Negative Generation", f"{negative_generation:,.0f}", "Negative actual/forecast GEN_MW values.", "danger" if negative_generation else "success"),
        ("Above Capacity", f"{capacity_violations:,.0f}", "GEN_MW values greater than GEN_MW_MAX.", "danger" if capacity_violations else "success"),
        ("Missing Capacity", f"{missing_capacity:,.0f}", "Zero or missing GEN_MW_MAX values.", "warning" if missing_capacity else "success"),
    ]

    cols = st.columns(3)
    for index, (title, value, detail, severity) in enumerate(cards):
        with cols[index % 3]:
            styles.alert_card(title, value, detail, severity)


def display_metric_cards() -> None:
    bias_value = metrics["bias"]
    bias_indicator = (
        "Positive: underforecasting"
        if bias_value > 0
        else "Negative: overforecasting"
        if bias_value < 0
        else "Balanced forecast"
    )

    styles.kpi_grid(
        [
            {
                "label": "Total Actual",
                "value": f"{utils.format_large_number(metrics['total_actual_mw'])} MW",
                "subtitle": utils.format_mw(metrics["total_actual_mw"]),
                "status": "neutral",
                "tooltip": (
                    "Total Actual Generation is the sum of ACTUAL_MW for all matched "
                    "actual/forecast records in the selected filters. It represents "
                    "the electricity actually generated during the selected period.\n\n"
                    "Formula:\nTotal Actual = SUM(ACTUAL_MW)"
                ),
            },
            {
                "label": "Total Forecast",
                "value": f"{utils.format_large_number(metrics['total_forecast_mw'])} MW",
                "subtitle": utils.format_mw(metrics["total_forecast_mw"]),
                "status": "neutral",
                "tooltip": (
                    "Total Forecast Generation is the sum of FORECAST_MW for the same "
                    "matched records. It represents the generation that was forecasted "
                    "for the selected period.\n\n"
                    "Formula:\nTotal Forecast = SUM(FORECAST_MW)"
                ),
            },
            {
                "label": "MAE",
                "value": utils.format_mw(metrics["mae"]),
                "subtitle": "Average absolute error",
                "status": error_status(metrics["mae"], warning=25, danger=50),
                "tooltip": (
                    "Mean Absolute Error measures the average absolute difference "
                    "between actual and forecast generation. It is the primary ranking "
                    "metric because it is easy to interpret in MW and does not allow "
                    "positive and negative errors to cancel out.\n\n"
                    "Formula:\nMAE = AVG(|ACTUAL_MW - FORECAST_MW|)"
                ),
            },
            {
                "label": "RMSE",
                "value": utils.format_mw(metrics["rmse"]),
                "subtitle": "Large misses weighted more",
                "status": rmse_status(metrics["mae"], metrics["rmse"]),
                "tooltip": (
                    "Root Mean Squared Error also measures forecast error, but it "
                    "penalizes large misses more than MAE. If RMSE is much larger than "
                    "MAE, the forecast has occasional large errors.\n\n"
                    "Formula:\nRMSE = SQRT(AVG((ACTUAL_MW - FORECAST_MW)^2))"
                ),
            },
            {
                "label": "Bias",
                "value": utils.format_mw(bias_value),
                "subtitle": bias_indicator,
                "status": bias_status(bias_value, metrics["mae"]),
                "tooltip": (
                    "Bias shows the average direction of forecast error. Since Bias = "
                    "Actual - Forecast, positive bias means the forecast was too low, "
                    "while negative bias means the forecast was too high.\n\n"
                    "Formula:\nBias = AVG(ACTUAL_MW - FORECAST_MW)"
                ),
            },
            {
                "label": "Energy Accuracy",
                "value": utils.format_percentage(metrics["energy_accuracy_pct"]),
                "subtitle": f"100 - WAPE; MAPE is {utils.format_percentage(metrics['mape'])}",
                "status": accuracy_status(metrics["energy_accuracy_pct"]),
                "tooltip": (
                    "Energy Accuracy is based on WAPE, which is more stable than MAPE "
                    "for generation data with zero or very small actual values. It "
                    "compares total absolute error against total actual generation.\n\n"
                    "Formula:\n"
                    "WAPE = SUM(|ACTUAL_MW - FORECAST_MW|) / SUM(ACTUAL_MW)\n"
                    "Energy Accuracy = 100 - WAPE"
                ),
            },
        ]
    )


def show_insights() -> None:
    insights = utils.generate_insights(filtered_df, rankings)
    cols = st.columns(4)
    for index, insight in enumerate(insights):
        with cols[index % 4]:
            severity, label = insight_treatment(insight)
            styles.insight_card(
                insight["title"],
                insight["detail"],
                severity=severity,
                label=label,
            )


def metric_column(metric: str) -> str:
    return metric.lower()


# ============================================================================
# Dashboard Header
# ============================================================================

styles.power_header(
    "Generator Forecast Performance Command Center | 2025",
    [
        "Analytics Layer Active",
        "Matched Actual/Forecast Records",
        f"{len(filtered_df):,} Filtered Rows",
        f"{start_date} to {end_date}",
    ],
)
st.info(analytics_layer_message)

sidebar_col1, sidebar_col2 = st.sidebar.columns(2)
with sidebar_col1:
    st.metric("Rows", f"{len(filtered_df):,}")
with sidebar_col2:
    st.metric("Devices", f"{filtered_df['DEVICE_ID'].nunique():,}")

st.sidebar.metric("Plants", f"{filtered_df['PLANT_NAME'].nunique():,}")
st.sidebar.metric("Fuel Types", f"{filtered_df['FUEL_TYPE'].nunique():,}")

display_metric_cards()
styles.section_header(
    "Automatic Insights",
    "Business-friendly operating signals generated from the current filters.",
    accent="cyan",
)
show_insights()


# ============================================================================
# Tabs
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Overview",
        "Forecast Accuracy",
        "Top & Worst Performers",
        "Plant & Fuel Analysis",
        "Data Quality",
        "Drilldowns & Downloads",
    ]
)


with tab1:
    styles.section_header(
        "Actual vs Forecast Trend",
        "Compare delivered generation against the forecast curve at the selected frequency.",
    )
    trend_df, trend_date_col = build_trend_data()
    st.plotly_chart(
        charts.actual_vs_forecast_line(
            trend_df,
            trend_date_col,
            f"{frequency} Actual vs Forecasted Generation",
        ),
        use_container_width=True,
    )
    st.caption("Actual generation is shown in electric blue; the dashed cyan line is the matched forecast.")

    col1, col2 = st.columns(2)
    with col1:
        styles.section_header("Generation by Fuel Type", "Fuel mix contribution across the active filters.")
        fuel_data = (
            filtered_df.groupby("FUEL_TYPE", as_index=False)
            .agg(total_actual_mw=("ACTUAL_MW", "sum"))
            .sort_values("total_actual_mw", ascending=False)
        )
        fig_fuel = px.bar(
            fuel_data,
            x="total_actual_mw",
            y="FUEL_TYPE",
            orientation="h",
            title="Total Actual Generation",
            labels={"total_actual_mw": "MW", "FUEL_TYPE": ""},
            color="FUEL_TYPE",
            color_discrete_map=charts.FUEL_COLORS,
        )
        fig_fuel.update_layout(showlegend=False)
        st.plotly_chart(
            charts.apply_power_grid_layout(
                fig_fuel,
                title="Total Actual Generation by Fuel Type",
                height=410,
            ),
            use_container_width=True,
        )
        st.caption("Use this view to spot which fuel groups dominate the selected period.")

    with col2:
        styles.section_header("Top 10 Plants", "Largest plants by actual generation in the selected filters.")
        plant_data = (
            filtered_df.groupby("PLANT_NAME", as_index=False)
            .agg(total_actual_mw=("ACTUAL_MW", "sum"))
            .sort_values("total_actual_mw", ascending=False)
            .head(10)
        )
        fig_plant = px.bar(
            plant_data,
            x="total_actual_mw",
            y="PLANT_NAME",
            orientation="h",
            title="Top Plants by Actual Generation",
            labels={"total_actual_mw": "MW", "PLANT_NAME": ""},
            color_discrete_sequence=[charts.ACTUAL_COLOR],
        )
        st.plotly_chart(
            charts.apply_power_grid_layout(
                fig_plant,
                title="Top Plants by Actual Generation",
                height=410,
            ),
            use_container_width=True,
        )
        st.caption("High-generation plants carry the largest energy volume impact.")


with tab2:
    styles.section_header(
        "Forecast Accuracy Analysis",
        "Error, bias, and dispersion views for the active matched records.",
        accent="warning",
    )
    st.markdown(
        """
        - MAE: average absolute error, lower is better.
        - RMSE: penalizes large misses, lower is better.
        - Bias: Actual - Forecast. Positive is underforecasting; negative is overforecasting.
        - MAPE: percentage error for rows where actual generation is greater than zero.
        - Energy Accuracy: 100 - WAPE, where WAPE is total absolute error divided by total absolute actual generation.
        """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts.error_by_fuel_bar(filtered_df), use_container_width=True)
        st.caption("MAE shows typical absolute error; RMSE rises faster when large misses occur.")
    with col2:
        plant_rankings, _, plant_worst = utils.calculate_rankings(
            filtered_df, "Plant", "MAE", 20
        )
        st.plotly_chart(
            charts.ranking_bar_chart(
                plant_worst,
                "PLANT_NAME",
                "mae",
                "Highest Plant MAE",
            ),
            use_container_width=True,
        )
        st.caption("Worst plant rankings surface where forecast improvements may have the highest payoff.")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            charts.actual_vs_forecast_scatter(filtered_df),
            use_container_width=True,
        )
        st.caption("Points near the diagonal indicate close agreement between forecast and actual output.")
    with col2:
        st.plotly_chart(charts.error_histogram(filtered_df), use_container_width=True)
        st.caption("A centered, narrow error distribution indicates more stable forecast performance.")


with tab3:
    styles.section_header(
        "Top & Worst Performers",
        "Rank devices, plants, or fuel types by the selected forecast metric.",
    )
    metric_col = metric_column(ranking_metric)
    label_col = ranking_label_column(ranking_level)

    st.caption(
        "Rankings exclude inactive groups where both actual and forecast generation are zero. "
        "Rows with actual = 0 but forecast != 0 remain eligible because they represent forecast misses."
    )

    if ranking_metric == "Bias":
        st.info("For Bias, best means closest to zero and worst means largest absolute bias.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"Best {top_n} by {ranking_metric}")
        st.dataframe(best_rankings.round(2), use_container_width=True, hide_index=True)
    with col2:
        st.subheader(f"Worst {top_n} by {ranking_metric}")
        st.dataframe(worst_rankings.round(2), use_container_width=True, hide_index=True)

    chart_metric = "bias" if ranking_metric == "Bias" else metric_col
    chart_df = worst_rankings.copy()
    if ranking_metric == "Bias" and not chart_df.empty:
        chart_df["abs_bias"] = chart_df["bias"].abs()
        chart_metric = "abs_bias"

    st.plotly_chart(
        charts.ranking_bar_chart(
            chart_df,
            label_col,
            chart_metric,
            f"Worst {ranking_level} Rankings by {ranking_metric}",
        ),
        use_container_width=True,
    )
    st.caption("Best error rankings use the lowest error; bias rankings use distance from zero.")


with tab4:
    styles.section_header(
        "Plant & Fuel Type Analysis",
        "Operational utilization and fuel mix views for generation planning.",
        accent="cyan",
    )
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            charts.capacity_utilization_bar(
                filtered_df,
                "PLANT_NAME",
                "Average Capacity Utilization by Plant",
            ),
            use_container_width=True,
        )
        st.caption("Higher utilization indicates assets running closer to available capacity.")

    with col2:
        st.plotly_chart(
            charts.capacity_utilization_bar(
                filtered_df,
                "FUEL_TYPE",
                "Average Capacity Utilization by Fuel Type",
            ),
            use_container_width=True,
        )
        st.caption("Fuel-level utilization helps compare operating patterns across resource classes.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Generation Mix by Fuel Type")
        fuel_mix = (
            filtered_df.groupby("FUEL_TYPE", as_index=False)
            .agg(total_actual_mw=("ACTUAL_MW", "sum"))
            .sort_values("total_actual_mw", ascending=False)
        )
        fig_pie = px.pie(
            fuel_mix,
            values="total_actual_mw",
            names="FUEL_TYPE",
            color="FUEL_TYPE",
            color_discrete_map=charts.FUEL_COLORS,
            title=None,
        )
        fig_pie.update_traces(
            marker=dict(line=dict(color="rgba(248,250,252,0.18)", width=1)),
            textfont=dict(color=styles.THEME["text"]),
        )
        fig_pie = charts.apply_power_grid_layout(
            fig_pie,
            title="",
            height=470,
        )
        fig_pie.update_layout(
            title=None,
            margin=dict(l=24, r=24, t=28, b=140),
            legend=dict(
                title=dict(text="Fuel Type", font=dict(color=styles.THEME["text_secondary"])),
                orientation="h",
                yanchor="top",
                y=-0.24,
                xanchor="left",
                x=0,
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=styles.THEME["text_secondary"]),
            ),
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        st.caption("Fuel mix shows how total actual generation is distributed by resource type.")

    with col2:
        st.markdown("#### Capacity Utilization vs Forecast Error")
        st.plotly_chart(
            charts.utilization_vs_error_scatter(filtered_df),
            use_container_width=True,
        )
        st.caption("Large bubbles indicate higher generation magnitude; higher Y values signal larger forecast misses.")

    styles.section_header("Fuel Type Summary", "Aggregated ranking metrics by fuel type.")
    fuel_rankings, _, _ = utils.calculate_rankings(filtered_df, "Fuel Type", "MAE", 50)
    st.dataframe(fuel_rankings.round(2), use_container_width=True, hide_index=True)


with tab5:
    styles.section_header(
        "Data Quality Summary",
        "Quality controls from the raw database and preprocessing pipeline.",
        accent="warning",
    )
    dq_df = analytics["data_quality"]
    show_data_quality_alerts(dq_df)
    st.dataframe(dq_df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        status_actual = dq_df[dq_df["metric"].str.startswith("actual_status_")].copy()
        status_actual["status"] = status_actual["metric"].str.replace("actual_status_", "", regex=False)
        st.subheader("Actual Status Distribution")
        st.dataframe(status_actual[["status", "value"]], use_container_width=True, hide_index=True)
    with col2:
        status_forecast = dq_df[dq_df["metric"].str.startswith("forecast_status_")].copy()
        status_forecast["status"] = status_forecast["metric"].str.replace("forecast_status_", "", regex=False)
        st.subheader("Forecast Status Distribution")
        st.dataframe(status_forecast[["status", "value"]], use_container_width=True, hide_index=True)

    styles.section_header("Preprocessing Metadata", "Pipeline run metadata for auditability.")
    st.json(metadata)


with tab6:
    styles.section_header(
        "Filtered Matched Dataset",
        "Detailed matched rows used by the current dashboard filters.",
    )
    display_cols = [
        "DATE_TIME",
        "MARKET_DATE",
        "DEVICE_ID",
        "PLANT_NAME",
        "FUEL_TYPE",
        "ACTUAL_MW",
        "FORECAST_MW",
        "ERROR_MW",
        "ABS_ERROR_MW",
        "APE",
        "CAPACITY_UTILIZATION",
    ]
    st.dataframe(
        filtered_df[display_cols].head(1000),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Showing the first 1,000 filtered rows.")

    download_limit = 200_000
    download_df = filtered_df[display_cols].head(download_limit)
    if len(filtered_df) > download_limit:
        st.info(
            f"Download is capped at the first {download_limit:,} rows to keep the browser responsive."
        )
    st.download_button(
        "Download filtered rows as CSV",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_matched_generation.csv",
        mime="text/csv",
    )


st.markdown("---")
st.caption(
    "Durable Electric Power - Generation Forecast Dashboard | "
    "Bias = Actual - Forecast; positive means underforecasting, negative means overforecasting."
)
