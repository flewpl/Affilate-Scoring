"""
Shared visual theme. One signature element: the "risk rail" - a horizontal
three-stop gradient bar (green -> amber -> red) used as a left border accent
on every scored card, echoing the Green/Yellow/Red logic that is the actual
core of this product. Numbers are set in a monospace face to read as
instrument-panel data, not marketing copy.
"""

import streamlit as st

# --- Design tokens -----------------------------------------------------
INK = "#0B0F14"
PANEL = "#141A22"
PANEL_BORDER = "#232B36"
TEXT_PRIMARY = "#E7ECF2"
TEXT_MUTED = "#8B96A5"
GREEN = "#3FB68A"
YELLOW = "#E8A23F"
RED = "#E0533F"
ACCENT = "#5B8DEF"


def inject_theme():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp {{
            background-color: {INK};
        }}

        section[data-testid="stSidebar"] {{
            background-color: #0E141C;
            border-right: 1px solid {PANEL_BORDER};
        }}

        .block-container {{
            padding-top: 2rem;
            max-width: 1200px;
        }}

        h1, h2, h3 {{
            color: {TEXT_PRIMARY};
            font-weight: 700;
            letter-spacing: -0.01em;
        }}

        p, li, span, label {{
            color: {TEXT_PRIMARY};
        }}

        .eyebrow {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: {TEXT_MUTED};
            margin-bottom: 0.25rem;
        }}

        /* ---- Risk rail card ---- */
        .risk-card {{
            background: {PANEL};
            border: 1px solid {PANEL_BORDER};
            border-left: 4px solid {ACCENT};
            border-radius: 10px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 0.9rem;
        }}
        .risk-card.green  {{ border-left-color: {GREEN}; }}
        .risk-card.yellow {{ border-left-color: {YELLOW}; }}
        .risk-card.red    {{ border-left-color: {RED}; }}

        .risk-card .metric-value {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.6rem;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        }}
        .risk-card .metric-label {{
            font-size: 0.82rem;
            color: {TEXT_MUTED};
        }}

        .status-pill {{
            display: inline-block;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.18rem 0.6rem;
            border-radius: 999px;
        }}
        .status-pill.green  {{ background: rgba(63,182,138,0.15); color: {GREEN}; border: 1px solid rgba(63,182,138,0.4); }}
        .status-pill.yellow {{ background: rgba(232,162,63,0.15); color: {YELLOW}; border: 1px solid rgba(232,162,63,0.4); }}
        .status-pill.red    {{ background: rgba(224,83,63,0.15); color: {RED}; border: 1px solid rgba(224,83,63,0.4); }}
        .status-pill.muted  {{ background: rgba(139,150,165,0.15); color: {TEXT_MUTED}; border: 1px solid rgba(139,150,165,0.4); }}

        /* Risk rail gradient strip used as section divider */
        .risk-rail {{
            height: 4px;
            width: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, {GREEN} 0%, {YELLOW} 50%, {RED} 100%);
            margin: 0.4rem 0 1.6rem 0;
            opacity: 0.85;
        }}

        div[data-testid="stMetric"] {{
            background: {PANEL};
            border: 1px solid {PANEL_BORDER};
            border-radius: 10px;
            padding: 0.9rem 1rem;
        }}
        div[data-testid="stMetricValue"] {{
            font-family: 'IBM Plex Mono', monospace;
        }}

        .stButton button {{
            border-radius: 8px;
            font-weight: 600;
        }}

        hr {{
            border-color: {PANEL_BORDER};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_class(status):
    """Maps a status string (with or without leading space) to a CSS class."""
    if not status:
        return "muted"
    s = status.strip().lower()
    if s == "green":
        return "green"
    if s == "yellow":
        return "yellow"
    if s == "red":
        return "red"
    return "muted"


def status_pill(status):
    cls = status_class(status)
    label = (status or "N/A").strip()
    return f'<span class="status-pill {cls}">{label}</span>'


def risk_rail():
    st.markdown('<div class="risk-rail"></div>', unsafe_allow_html=True)