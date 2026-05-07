"""Streamlit styling helpers for the Durable Power Dashboard."""

from __future__ import annotations

import html

import streamlit as st


THEME = {
    "background": "#070B12",
    "panel": "#101827",
    "panel_2": "#172033",
    "header": "#071A33",
    "electric_blue": "#00AEEF",
    "cyan": "#22D3EE",
    "text": "#F8FAFC",
    "text_secondary": "#CBD5E1",
    "muted": "#94A3B8",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "neutral": "#64748B",
    "border": "rgba(148, 163, 184, 0.25)",
    "grid_line": "rgba(34, 211, 238, 0.12)",
}

SEVERITY_COLORS = {
    "info": THEME["cyan"],
    "success": THEME["success"],
    "warning": THEME["warning"],
    "danger": THEME["danger"],
    "neutral": THEME["neutral"],
}


def inject_custom_css() -> None:
    """Inject the electric grid control-room theme CSS."""
    st.markdown(
        f"""
<style>
:root {{
    --power-bg: {THEME["background"]};
    --power-panel: {THEME["panel"]};
    --power-panel-2: {THEME["panel_2"]};
    --power-header: {THEME["header"]};
    --power-blue: {THEME["electric_blue"]};
    --power-cyan: {THEME["cyan"]};
    --power-text: {THEME["text"]};
    --power-text-secondary: {THEME["text_secondary"]};
    --power-muted: {THEME["muted"]};
    --power-success: {THEME["success"]};
    --power-warning: {THEME["warning"]};
    --power-danger: {THEME["danger"]};
    --power-neutral: {THEME["neutral"]};
    --power-border: {THEME["border"]};
    --power-grid-line: {THEME["grid_line"]};
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}

.stApp {{
    background:
        linear-gradient(var(--power-grid-line) 1px, transparent 1px),
        linear-gradient(90deg, var(--power-grid-line) 1px, transparent 1px),
        radial-gradient(circle at top right, rgba(0, 174, 239, 0.16), transparent 34rem),
        radial-gradient(circle at 18% 6%, rgba(34, 211, 238, 0.10), transparent 28rem),
        var(--power-bg);
    background-size: 44px 44px, 44px 44px, auto, auto, auto;
    color: var(--power-text);
}}

.block-container {{
    padding-top: 1.2rem;
    padding-bottom: 2.2rem;
}}

.stMarkdown,
.stCaption,
p,
li {{
    color: var(--power-text-secondary);
}}

h1, h2, h3, h4, h5, h6 {{
    color: var(--power-text);
}}

[data-testid="stSidebar"] {{
    background:
        linear-gradient(180deg, rgba(7, 26, 51, 0.98), rgba(11, 16, 32, 0.98)),
        linear-gradient(var(--power-grid-line) 1px, transparent 1px),
        linear-gradient(90deg, var(--power-grid-line) 1px, transparent 1px);
    background-size: auto, 36px 36px, 36px 36px;
    border-right: 1px solid var(--power-border);
}}

[data-testid="stSidebar"] * {{
    color: var(--power-text);
}}

[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
    color: var(--power-text-secondary);
}}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] div[data-baseweb="input"] > div {{
    background-color: rgba(16, 24, 39, 0.95);
    border-color: var(--power-border);
    color: var(--power-text);
}}

[data-testid="stSidebar"] [data-testid="stForm"] {{
    background: rgba(16, 24, 39, 0.38);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 10px;
    padding: 0.85rem;
}}

[data-testid="stSidebar"] [data-testid="stMetric"] {{
    background: rgba(16, 24, 39, 0.78);
    border: 1px solid rgba(34, 211, 238, 0.20);
    border-radius: 8px;
    padding: 0.75rem 0.8rem;
}}

[data-testid="stMetric"] {{
    background: rgba(16, 24, 39, 0.76);
    border: 1px solid var(--power-border);
    border-radius: 8px;
    padding: 0.75rem 0.8rem;
}}

[data-testid="stMetricLabel"] p {{
    color: var(--power-muted);
    font-size: 0.76rem;
    font-weight: 850;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

[data-testid="stMetricValue"] {{
    color: var(--power-text);
}}

.stDateInput input,
.stNumberInput input,
.stTextInput input,
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {{
    background-color: rgba(16, 24, 39, 0.95);
    border-color: var(--power-border);
    color: var(--power-text);
}}

.stButton > button,
[data-testid="stFormSubmitButton"] button,
.stDownloadButton > button {{
    background: linear-gradient(135deg, var(--power-blue), var(--power-cyan));
    border: 1px solid rgba(34, 211, 238, 0.55);
    border-radius: 8px;
    color: #02111f;
    font-weight: 800;
    box-shadow: 0 0 18px rgba(0, 174, 239, 0.20);
}}

.stButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover,
.stDownloadButton > button:hover {{
    border-color: var(--power-cyan);
    box-shadow: 0 0 24px rgba(34, 211, 238, 0.34);
}}

.power-header {{
    background:
        linear-gradient(135deg, rgba(7, 26, 51, 0.96), rgba(16, 24, 39, 0.92)),
        linear-gradient(90deg, rgba(0, 174, 239, 0.08), transparent);
    border: 1px solid var(--power-border);
    border-radius: 10px;
    box-shadow: 0 0 32px rgba(0, 174, 239, 0.14);
    margin: 0 0 1.15rem 0;
    padding: 1.25rem 1.35rem 1.05rem 1.35rem;
    position: relative;
}}

.power-header::after {{
    background: linear-gradient(90deg, var(--power-blue), var(--power-cyan), transparent);
    bottom: 0;
    content: "";
    height: 2px;
    left: 1.35rem;
    position: absolute;
    right: 1.35rem;
}}

.power-header-title {{
    color: var(--power-text);
    font-size: clamp(1.65rem, 3vw, 2.65rem);
    font-weight: 850;
    letter-spacing: 0.08em;
    line-height: 1;
}}

.power-subtitle {{
    color: var(--power-text-secondary);
    font-size: 0.98rem;
    margin-top: 0.55rem;
}}

.status-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 0.95rem;
}}

.status-pill {{
    align-items: center;
    background: rgba(34, 211, 238, 0.10);
    border: 1px solid rgba(34, 211, 238, 0.34);
    border-radius: 999px;
    color: var(--power-cyan);
    display: inline-flex;
    font-size: 0.76rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    padding: 0.35rem 0.7rem;
    text-transform: uppercase;
}}

.control-panel {{
    border-bottom: 1px solid var(--power-border);
    margin-bottom: 1rem;
    padding-bottom: 0.85rem;
}}

.control-panel-title {{
    color: var(--power-text);
    font-size: 1.1rem;
    font-weight: 850;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

.control-panel-detail {{
    color: var(--power-muted);
    font-size: 0.84rem;
    line-height: 1.35;
    margin-top: 0.35rem;
}}

.grid-panel {{
    background: rgba(16, 24, 39, 0.82);
    border: 1px solid var(--power-border);
    border-radius: 10px;
    box-shadow: 0 0 24px rgba(0, 174, 239, 0.10);
    padding: 1rem;
}}

.kpi-grid {{
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    margin: 1rem 0 1.25rem 0;
}}

.kpi-card {{
    background:
        linear-gradient(180deg, rgba(23, 32, 51, 0.94), rgba(16, 24, 39, 0.96));
    border: 1px solid rgba(34, 211, 238, 0.28);
    border-radius: 10px;
    box-shadow: 0 0 22px rgba(0, 174, 239, 0.10);
    min-height: 132px;
    padding: 18px 18px 16px 18px;
    position: relative;
}}

.kpi-card::before {{
    background: linear-gradient(90deg, var(--kpi-accent, var(--power-blue)), transparent);
    border-radius: 10px 10px 0 0;
    content: "";
    height: 3px;
    left: 0;
    position: absolute;
    right: 0;
    top: 0;
}}

.kpi-card:hover {{
    border-color: rgba(34, 211, 238, 0.55);
    box-shadow: 0 0 30px rgba(34, 211, 238, 0.18);
}}

.kpi-card-success {{ --kpi-accent: var(--power-success); }}
.kpi-card-warning {{ --kpi-accent: var(--power-warning); }}
.kpi-card-danger {{ --kpi-accent: var(--power-danger); }}
.kpi-card-neutral {{ --kpi-accent: var(--power-blue); }}

.kpi-title-row {{
    align-items: center;
    display: flex;
    gap: 7px;
    margin-bottom: 10px;
    min-height: 20px;
}}

.kpi-label {{
    color: var(--power-muted);
    font-size: 0.78rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}}

.kpi-info-icon {{
    align-items: center;
    border: 1px solid rgba(34, 211, 238, 0.50);
    border-radius: 999px;
    color: var(--power-cyan);
    display: inline-flex;
    font-size: 0.7rem;
    font-weight: 850;
    height: 18px;
    justify-content: center;
    line-height: 1;
    width: 18px;
}}

.kpi-tooltip {{
    background: rgba(7, 11, 18, 0.98);
    border: 1px solid rgba(34, 211, 238, 0.36);
    border-radius: 8px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38);
    color: var(--power-text-secondary);
    font-size: 0.78rem;
    left: 14px;
    line-height: 1.38;
    max-width: 320px;
    opacity: 0;
    padding: 11px 12px;
    pointer-events: none;
    position: absolute;
    top: calc(100% + 8px);
    transform: translateY(-4px);
    transition: opacity 0.14s ease, transform 0.14s ease, visibility 0.14s ease;
    visibility: hidden;
    width: max-content;
    z-index: 50;
}}

.kpi-card:hover .kpi-tooltip {{
    opacity: 1;
    transform: translateY(0);
    visibility: visible;
}}

.kpi-value {{
    color: var(--power-text);
    font-size: clamp(1.75rem, 2.55vw, 2.55rem);
    font-weight: 850;
    letter-spacing: 0;
    line-height: 1.05;
    overflow-wrap: anywhere;
    text-shadow: 0 0 16px rgba(0, 174, 239, 0.10);
    white-space: normal;
}}

.kpi-subtitle {{
    color: var(--power-text-secondary);
    font-size: 0.82rem;
    line-height: 1.25;
    margin-top: 10px;
}}

.insight-card {{
    background: rgba(16, 24, 39, 0.92);
    border: 1px solid var(--power-border);
    border-left: 4px solid var(--insight-accent, var(--power-cyan));
    border-radius: 9px;
    box-shadow: 0 0 20px rgba(0, 174, 239, 0.08);
    min-height: 126px;
    padding: 14px 16px;
}}

.insight-label {{
    color: var(--insight-accent, var(--power-cyan));
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    text-transform: uppercase;
}}

.insight-title {{
    color: var(--power-text);
    font-size: 0.9rem;
    font-weight: 800;
    margin-bottom: 7px;
}}

.insight-detail {{
    color: var(--power-text-secondary);
    font-size: 0.88rem;
    line-height: 1.36;
}}

.insight-info {{ --insight-accent: var(--power-cyan); }}
.insight-success {{ --insight-accent: var(--power-success); }}
.insight-warning {{ --insight-accent: var(--power-warning); }}
.insight-danger {{ --insight-accent: var(--power-danger); }}

.section-header {{
    margin: 1.15rem 0 0.8rem 0;
}}

.section-kicker {{
    color: var(--section-accent, var(--power-blue));
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

.section-title {{
    color: var(--power-text);
    font-size: 1.32rem;
    font-weight: 850;
    line-height: 1.12;
    margin-top: 0.2rem;
}}

.section-subtitle {{
    color: var(--power-muted);
    font-size: 0.88rem;
    margin-top: 0.35rem;
}}

.section-rule {{
    background: linear-gradient(90deg, var(--section-accent, var(--power-blue)), transparent);
    height: 2px;
    margin-top: 0.55rem;
    width: 160px;
}}

.alert-card {{
    background: rgba(16, 24, 39, 0.92);
    border: 1px solid var(--power-border);
    border-left: 4px solid var(--alert-accent, var(--power-cyan));
    border-radius: 9px;
    min-height: 96px;
    padding: 0.9rem 1rem;
}}

.alert-title {{
    color: var(--power-muted);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}

.alert-value {{
    color: var(--power-text);
    font-size: 1.5rem;
    font-weight: 850;
    margin-top: 0.3rem;
}}

.alert-detail {{
    color: var(--power-text-secondary);
    font-size: 0.82rem;
    margin-top: 0.25rem;
}}

.alert-info {{ --alert-accent: var(--power-cyan); }}
.alert-success {{ --alert-accent: var(--power-success); }}
.alert-warning {{ --alert-accent: var(--power-warning); }}
.alert-danger {{ --alert-accent: var(--power-danger); }}

[data-testid="stDataFrame"] {{
    border: 1px solid var(--power-border);
    border-radius: 9px;
    overflow: hidden;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
}}

.stTabs [data-baseweb="tab"] {{
    background: rgba(16, 24, 39, 0.72);
    border: 1px solid var(--power-border);
    border-radius: 8px 8px 0 0;
    color: var(--power-text-secondary);
    font-weight: 750;
}}

.stTabs [aria-selected="true"] {{
    border-color: rgba(34, 211, 238, 0.48);
    color: var(--power-text);
    box-shadow: inset 0 2px 0 var(--power-blue);
}}

.stAlert {{
    background: rgba(16, 24, 39, 0.92);
    border: 1px solid var(--power-border);
    color: var(--power-text);
}}

.stAlert p {{
    color: var(--power-text-secondary);
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def _escape_multiline(value: str) -> str:
    """Escape text for HTML and preserve line breaks."""
    return html.escape(str(value)).replace("\n", "<br>")


def _severity_class(prefix: str, severity: str | None) -> str:
    if severity not in SEVERITY_COLORS:
        severity = "info"
    return f"{prefix}-{severity}"


def _kpi_card_html(
    title: str,
    value: str,
    subtitle: str = "",
    tooltip: str | None = None,
    status: str = "neutral",
) -> str:
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_subtitle = html.escape(str(subtitle))
    status_class = _severity_class("kpi-card", status)

    tooltip_icon = ""
    tooltip_html = ""
    if tooltip:
        tooltip_icon = '<span class="kpi-info-icon">i</span>'
        tooltip_html = f'<div class="kpi-tooltip">{_escape_multiline(tooltip)}</div>'

    return (
        f'<div class="kpi-card {status_class}">'
        '<div class="kpi-title-row">'
        f'<div class="kpi-label">{safe_title}</div>'
        f"{tooltip_icon}"
        "</div>"
        f'<div class="kpi-value">{safe_value}</div>'
        f'<div class="kpi-subtitle">{safe_subtitle}</div>'
        f"{tooltip_html}"
        "</div>"
    )


def kpi_card(title, value, subtitle="", tooltip=None, status="neutral") -> None:
    """Render one KPI card with optional tooltip and status color."""
    st.markdown(
        _kpi_card_html(title, value, subtitle=subtitle, tooltip=tooltip, status=status),
        unsafe_allow_html=True,
    )


def kpi_grid(cards: list[dict]) -> None:
    """Render responsive KPI cards that do not clip large values."""
    card_html = []
    for card in cards:
        card_html.append(
            _kpi_card_html(
                card.get("label", ""),
                card.get("value", ""),
                subtitle=card.get("subtitle", ""),
                tooltip=card.get("tooltip"),
                status=card.get("status", "neutral"),
            )
        )

    st.markdown(
        f'<div class="kpi-grid">{"".join(card_html)}</div>',
        unsafe_allow_html=True,
    )


def insight_card(
    title: str,
    detail: str,
    severity: str = "info",
    label: str = "INSIGHT",
    marker: str = "",
) -> None:
    """Render an operational insight card."""
    safe_title = html.escape(str(title))
    safe_detail = html.escape(str(detail))
    safe_label = html.escape(str(label))
    safe_marker = html.escape(str(marker))
    severity_class = _severity_class("insight", severity)
    marker_html = f"{safe_marker} " if safe_marker else ""
    st.markdown(
        f'<div class="insight-card {severity_class}">'
        f'<div class="insight-label">{marker_html}{safe_label}</div>'
        f'<div class="insight-title">{safe_title}</div>'
        f'<div class="insight-detail">{safe_detail}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None, accent: str = "electric_blue") -> None:
    """Render a utility-dashboard section header."""
    color = THEME.get(accent, THEME["electric_blue"])
    safe_title = html.escape(str(title))
    subtitle_html = ""
    if subtitle:
        subtitle_html = f'<div class="section-subtitle">{html.escape(str(subtitle))}</div>'

    st.markdown(
        '<div class="section-header" style="--section-accent: '
        f'{color};">'
        '<div class="section-kicker">Operations View</div>'
        f'<div class="section-title">{safe_title}</div>'
        f"{subtitle_html}"
        '<div class="section-rule"></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def power_header(subtitle: str, status_items: list[str]) -> None:
    """Render the dashboard command-center header."""
    pills = "".join(
        f'<span class="status-pill">{html.escape(str(item))}</span>'
        for item in status_items
    )
    st.markdown(
        '<div class="power-header">'
        '<div class="power-header-title">DURABLE ELECTRIC POWER</div>'
        f'<div class="power-subtitle">{html.escape(str(subtitle))}</div>'
        f'<div class="status-row">{pills}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def control_panel_header() -> None:
    """Render sidebar control-panel intro."""
    st.sidebar.markdown(
        '<div class="control-panel">'
        '<div class="control-panel-title">Control Panel</div>'
        '<div class="control-panel-detail">Filter generation data by date, plant, device, and fuel.</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def alert_card(title: str, value: str, detail: str = "", severity: str = "info") -> None:
    """Render a compact severity-coded alert/data-quality card."""
    severity_class = _severity_class("alert", severity)
    st.markdown(
        f'<div class="alert-card {severity_class}">'
        f'<div class="alert-title">{html.escape(str(title))}</div>'
        f'<div class="alert-value">{html.escape(str(value))}</div>'
        f'<div class="alert-detail">{html.escape(str(detail))}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
