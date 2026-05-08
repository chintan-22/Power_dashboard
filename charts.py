"""Reusable Plotly chart builders for the Durable Power Dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from styles import THEME


ACTUAL_COLOR = THEME["electric_blue"]
FORECAST_COLOR = THEME["cyan"]
ERROR_COLOR = THEME["warning"]
BEST_COLOR = THEME["success"]
WORST_COLOR = THEME["danger"]
UNKNOWN_COLOR = THEME["neutral"]

FUEL_COLORS = {
    "Wind": "#22D3EE",
    "Solar": "#F59E0B",
    "Natural Gas": "#00AEEF",
    "Combined Cycle Waste Heat": "#A78BFA",
    "Hydro": "#38BDF8",
    "Coal Lignite": "#F97316",
    "Fuel Oil No. 2 Distillate Diesel": "#EF4444",
    "Biomass": "#22C55E",
    "Battery": "#84CC16",
    "Unknown Fuel": UNKNOWN_COLOR,
}


def apply_power_grid_layout(fig, title=None, height=420):
    """Apply the utility control-room Plotly theme to a figure."""
    fig.update_layout(
        title=title if title is not None else fig.layout.title.text,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16,24,39,0.78)",
        font=dict(color=THEME["text"], family="Inter, system-ui, sans-serif"),
        margin=dict(l=48, r=24, t=58, b=48),
        title_font=dict(color=THEME["text"], size=18),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=THEME["text_secondary"]),
        ),
        hoverlabel=dict(
            bgcolor=THEME["panel"],
            bordercolor=THEME["cyan"],
            font=dict(color=THEME["text"]),
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.15)",
        linecolor="rgba(148, 163, 184, 0.30)",
        tickcolor=THEME["muted"],
        tickfont=dict(color=THEME["text_secondary"]),
        title_font=dict(color=THEME["text_secondary"]),
        zerolinecolor="rgba(148, 163, 184, 0.22)",
    )
    fig.update_yaxes(
        gridcolor="rgba(148, 163, 184, 0.15)",
        linecolor="rgba(148, 163, 184, 0.30)",
        tickcolor=THEME["muted"],
        tickfont=dict(color=THEME["text_secondary"]),
        title_font=dict(color=THEME["text_secondary"]),
        zerolinecolor="rgba(148, 163, 184, 0.22)",
    )
    return fig


def actual_vs_forecast_line(df: pd.DataFrame, date_col: str, title: str):
    """Line chart for total actual vs forecast generation over time."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title=title)

    chart_data = (
        df.groupby(date_col, as_index=False)
        .agg(
            total_actual_mw=("total_actual_mw", "sum"),
            total_forecast_mw=("total_forecast_mw", "sum"),
        )
        .sort_values(date_col)
    )
    fig = px.line(
        chart_data,
        x=date_col,
        y=["total_actual_mw", "total_forecast_mw"],
        markers=True,
        labels={
            "value": "Generation (MW)",
            date_col: "Date",
            "variable": "Series",
        },
        color_discrete_map={
            "total_actual_mw": ACTUAL_COLOR,
            "total_forecast_mw": FORECAST_COLOR,
        },
    )
    fig.for_each_trace(
        lambda trace: trace.update(
            name="Actual Generation" if trace.name == "total_actual_mw" else "Forecast Generation",
            line=dict(
                width=3.2 if trace.name == "total_actual_mw" else 2.6,
                dash=None if trace.name == "total_actual_mw" else "dash",
            ),
        )
    )
    return apply_power_grid_layout(fig, title=title, height=430)


def error_histogram(df: pd.DataFrame):
    """Histogram of forecast error in MW."""
    fig = px.histogram(
        df,
        x="ERROR_MW",
        nbins=100,
        title="Forecast Error Distribution",
        labels={"ERROR_MW": "Error (MW)", "count": "Frequency"},
        color_discrete_sequence=[ERROR_COLOR],
    )
    fig.add_vline(x=0, line_dash="dash", line_color=THEME["cyan"])
    return apply_power_grid_layout(fig, height=420)


def actual_vs_forecast_scatter(df: pd.DataFrame, sample_size: int = 3000):
    """Actual vs forecast scatter plot with a perfect forecast reference line."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title="")

    plot_df = df.sample(min(sample_size, len(df)), random_state=42)
    fig = px.scatter(
        plot_df,
        x="FORECAST_MW",
        y="ACTUAL_MW",
        color="FUEL_TYPE",
        color_discrete_map=FUEL_COLORS,
        hover_data=["DEVICE_ID", "PLANT_NAME"],
        title=None,
        labels={"FORECAST_MW": "Forecast (MW)", "ACTUAL_MW": "Actual (MW)"},
        opacity=0.62,
    )
    max_val = max(plot_df["FORECAST_MW"].max(), plot_df["ACTUAL_MW"].max())
    fig.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Perfect Forecast",
            line=dict(color=THEME["danger"], dash="dash", width=2),
            hovertemplate="Perfect Forecast<extra></extra>",
        )
    )
    fig = apply_power_grid_layout(fig, title="", height=500)
    fig.update_layout(
        title=None,
        margin=dict(l=56, r=24, t=28, b=150),
        legend=dict(
            title=dict(text="Fuel Type", font=dict(color=THEME["text_secondary"])),
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=THEME["text_secondary"]),
        ),
    )
    return fig


def error_by_fuel_bar(df: pd.DataFrame):
    """Bar chart showing MAE and RMSE by fuel type."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title="Error Metrics by Fuel Type")

    fuel_metrics = (
        df.groupby("FUEL_TYPE", as_index=False)
        .agg(
            mae=("ABS_ERROR_MW", "mean"),
            squared_error_mean=("SQUARED_ERROR", "mean"),
        )
    )
    fuel_metrics["rmse"] = fuel_metrics["squared_error_mean"] ** 0.5
    fig = px.bar(
        fuel_metrics,
        x="FUEL_TYPE",
        y=["mae", "rmse"],
        barmode="group",
        title="Error Metrics by Fuel Type",
        labels={"value": "Error (MW)", "FUEL_TYPE": "Fuel Type"},
        color_discrete_map={"mae": ERROR_COLOR, "rmse": THEME["danger"]},
    )
    fig.for_each_trace(lambda trace: trace.update(name=trace.name.upper()))
    return apply_power_grid_layout(fig, height=430)


def ranking_bar_chart(df: pd.DataFrame, label_col: str, metric_col: str, title: str):
    """Horizontal ranking bar chart."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title=title)

    chart_data = df.copy().sort_values(metric_col, ascending=True)
    color = WORST_COLOR if "Worst" in title or "Highest" in title else BEST_COLOR
    fig = px.bar(
        chart_data,
        x=metric_col,
        y=label_col,
        orientation="h",
        title=title,
        labels={metric_col: metric_col.upper(), label_col: ""},
        color_discrete_sequence=[color],
    )
    fig.update_traces(marker_line_color="rgba(255,255,255,0.18)", marker_line_width=1)
    return apply_power_grid_layout(fig, height=430)


def capacity_utilization_bar(df: pd.DataFrame, group_col: str, title: str, top_n: int = 20):
    """Capacity utilization bar chart grouped by a selected column."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title=title)

    chart_data = (
        df.groupby(group_col, as_index=False)
        .agg(avg_capacity_utilization=("CAPACITY_UTILIZATION", "mean"))
        .sort_values("avg_capacity_utilization", ascending=False)
        .head(top_n)
    )
    fig = px.bar(
        chart_data,
        x="avg_capacity_utilization",
        y=group_col,
        orientation="h",
        title=title,
        labels={"avg_capacity_utilization": "Avg Utilization (%)", group_col: ""},
        color="avg_capacity_utilization",
        color_continuous_scale=["#172033", THEME["electric_blue"], THEME["success"]],
    )
    fig.update_layout(coloraxis_colorbar=dict(title="Utilization"))
    return apply_power_grid_layout(fig, height=430)


def utilization_vs_error_scatter(df: pd.DataFrame):
    """Scatter plot comparing utilization and MAE by plant/fuel group."""
    if df.empty:
        return apply_power_grid_layout(go.Figure(), title="Capacity Utilization vs Forecast Error")

    chart_data = (
        df.groupby(["PLANT_NAME", "FUEL_TYPE"], as_index=False)
        .agg(
            avg_capacity_utilization=("CAPACITY_UTILIZATION", "mean"),
            mae=("ABS_ERROR_MW", "mean"),
            total_actual_mw=("ACTUAL_MW", "sum"),
        )
    )
    chart_data["generation_magnitude_mw"] = (
        chart_data["total_actual_mw"].abs().fillna(0)
    )
    fig = px.scatter(
        chart_data,
        x="avg_capacity_utilization",
        y="mae",
        size="generation_magnitude_mw",
        color="FUEL_TYPE",
        color_discrete_map=FUEL_COLORS,
        hover_data=["PLANT_NAME", "total_actual_mw"],
        title=None,
        labels={
            "avg_capacity_utilization": "Avg Utilization (%)",
            "mae": "MAE (MW)",
            "generation_magnitude_mw": "|Total Actual MW|",
            "total_actual_mw": "Total Actual MW",
        },
    )
    fig = apply_power_grid_layout(
        fig,
        title="",
        height=470,
    )
    fig.update_layout(
        title=None,
        margin=dict(l=56, r=24, t=28, b=140),
        legend=dict(
            title=dict(text="Fuel Type", font=dict(color=THEME["text_secondary"])),
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=THEME["text_secondary"]),
        ),
    )
    return fig
