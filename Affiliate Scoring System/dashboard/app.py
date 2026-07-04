"""
Affiliate Scoring Dashboard — Streamlit App
Upload SQL dump or Excel file → instant rule-based scoring + anomaly detection
"""

import io
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Affiliate Scoring",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── theme injection ───────────────────────────────────────────────────────────
INK        = "#0B0F14"
PANEL      = "#141A22"
PANEL_B    = "#232B36"
TEXT       = "#E7ECF2"
MUTED      = "#8B96A5"
GREEN      = "#3FB68A"
YELLOW     = "#E8A23F"
RED        = "#E0533F"
ACCENT     = "#5B8DEF"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; background-color: {INK}; color: {TEXT}; }}
.stApp {{ background-color: {INK}; }}
section[data-testid="stSidebar"] {{ background-color: #0E141C; border-right: 1px solid {PANEL_B}; }}
.block-container {{ padding-top: 2rem; max-width: 1280px; }}
h1,h2,h3 {{ color: {TEXT}; font-weight: 700; letter-spacing: -.01em; }}
div[data-testid="stMetric"] {{ background: {PANEL}; border: 1px solid {PANEL_B}; border-radius: 10px; padding: .9rem 1rem; }}
div[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; color: {TEXT}; }}
div[data-testid="stMetricLabel"] {{ color: {MUTED}; }}
.stButton button {{ border-radius: 8px; font-weight: 600; background: {ACCENT}; color: white; border: none; }}
.stButton button:hover {{ opacity: .88; }}
.pill {{ display:inline-block; font-family:'IBM Plex Mono',monospace; font-size:.72rem; font-weight:600;
         letter-spacing:.06em; text-transform:uppercase; padding:.18rem .6rem; border-radius:999px; }}
.pill-green  {{ background:rgba(63,182,138,.15); color:{GREEN}; border:1px solid rgba(63,182,138,.4); }}
.pill-yellow {{ background:rgba(232,162,63,.15);  color:{YELLOW}; border:1px solid rgba(232,162,63,.4); }}
.pill-red    {{ background:rgba(224,83,63,.15);   color:{RED};    border:1px solid rgba(224,83,63,.4); }}
.pill-muted  {{ background:rgba(139,150,165,.15); color:{MUTED};  border:1px solid rgba(139,150,165,.4); }}
.risk-rail {{ height:4px; width:100%; border-radius:999px;
              background:linear-gradient(90deg,{GREEN} 0%,{YELLOW} 50%,{RED} 100%);
              margin:.4rem 0 1.6rem 0; opacity:.85; }}
.card {{ background:{PANEL}; border:1px solid {PANEL_B}; border-radius:10px;
         padding:1.1rem 1.3rem; margin-bottom:.9rem; }}
.card-green  {{ border-left:4px solid {GREEN}; }}
.card-yellow {{ border-left:4px solid {YELLOW}; }}
.card-red    {{ border-left:4px solid {RED}; }}
.card-muted  {{ border-left:4px solid {MUTED}; }}
.mono {{ font-family:'IBM Plex Mono',monospace; }}
.eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:.72rem; letter-spacing:.14em;
            text-transform:uppercase; color:{MUTED}; margin-bottom:.25rem; }}
.stDataFrame {{ background:{PANEL}; }}
div[data-baseweb="tab-list"] {{ background:{PANEL}; border-radius:10px; padding:.25rem; }}
div[data-baseweb="tab"] {{ color:{MUTED}; }}
div[data-baseweb="tab"][aria-selected="true"] {{ color:{TEXT}; background:{INK}; border-radius:8px; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SCORING LOGIC (inline, no external import needed)
# ═══════════════════════════════════════════════════════════════════════════════
BENCHMARKS = {
    "SEO": {
        "reg_rate":    {"dir":"high_is_bad","yellow":0.09,"red":0.14},
        "ftd_rate":    {"dir":"high_is_bad","yellow":0.42,"red":0.55},
        "ngr_per_ftd": {"dir":"low_is_bad", "yellow":90,  "red":40},
        "retention_30d":{"dir":"low_is_bad","yellow":0.40,"red":0.25},
        "_min_sample": {"clicks":1000,"registrations":50,"ftd_count":15},
    },
    "PPC": {
        "reg_rate":    {"dir":"high_is_bad","yellow":0.06,"red":0.06},
        "ftd_rate":    {"dir":"high_is_bad","yellow":0.32,"red":0.45},
        "ngr_per_ftd": {"dir":"low_is_bad", "yellow":45,  "red":20},
        "retention_30d":{"dir":"low_is_bad","yellow":0.22,"red":0.12},
        "_min_sample": {"clicks":3000,"registrations":60,"ftd_count":12},
    },
    "Streamer": {
        "reg_rate":    {"dir":"high_is_bad","yellow":0.14,"red":0.22},
        "ftd_rate":    {"dir":"high_is_bad","yellow":0.58,"red":0.70},
        "ngr_per_ftd": {"dir":"low_is_bad", "yellow":65,  "red":30},
        "retention_30d":{"dir":"low_is_bad","yellow":0.33,"red":0.18},
        "_min_sample": {"clicks":500,"registrations":40,"ftd_count":15},
    },
    "Email": {
        "reg_rate":    {"dir":"high_is_bad","yellow":0.07,"red":0.12},
        "ftd_rate":    {"dir":"high_is_bad","yellow":0.40,"red":0.52},
        "ngr_per_ftd": {"dir":"low_is_bad", "yellow":55,  "red":25},
        "retention_30d":{"dir":"low_is_bad","yellow":0.30,"red":0.18},
        "_min_sample": {"clicks":800,"registrations":40,"ftd_count":12},
    },
}

METRIC_WEIGHTS = {"ngr_per_ftd":0.40,"retention_30d":0.30,"ftd_rate":0.20,"reg_rate":0.10}
FLAG_SCORE     = {" Green":1.0," Yellow":0.5," Red":0.0}

def evaluate_row(row):
    profile = row.get("profile_name","")
    if profile not in BENCHMARKS:
        return {"status":"Banned/Fraud","flags":{},"final_score":0.0,"final_status":" Red"}
    mins = BENCHMARKS[profile]["_min_sample"]
    if row.get("clicks",0) < mins["clicks"]:
        return {"status":"Insufficient clicks","flags":{},"final_score":None,"final_status":" Not Enough Data"}
    if row.get("registrations",0) < mins["registrations"]:
        return {"status":"Insufficient registrations","flags":{},"final_score":None,"final_status":" Not Enough Data"}
    if row.get("ftd_count",0) < mins["ftd_count"]:
        return {"status":"Insufficient FTDs","flags":{},"final_score":None,"final_status":" Not Enough Data"}

    prof  = BENCHMARKS[profile]
    flags = {}
    score = 0.0
    for metric, thr in prof.items():
        if metric.startswith("_"): continue
        val = row.get(metric, 0)
        if thr["dir"] == "high_is_bad":
            flag = " Red" if val >= thr["red"] else (" Yellow" if val >= thr["yellow"] else " Green")
        else:
            flag = " Red" if val <= thr["red"] else (" Yellow" if val <= thr["yellow"] else " Green")
        flags[metric] = flag
        score += METRIC_WEIGHTS.get(metric,0) * FLAG_SCORE.get(flag,0)

    color = " Green" if score >= 0.75 else (" Yellow" if score >= 0.40 else " Red")
    return {"status":"Evaluated","flags":flags,"final_score":round(score,2),"final_status":color}

def score_dataframe(df):
    results = df.apply(evaluate_row, axis=1)
    df = df.copy()
    df["final_score"]  = results.apply(lambda r: r["final_score"])
    df["final_status"] = results.apply(lambda r: r["final_status"].strip())
    df["status"]       = results.apply(lambda r: r["status"])
    df["flags"]        = results.apply(lambda r: r["flags"])
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTION (Isolation Forest, no external import)
# ═══════════════════════════════════════════════════════════════════════════════
FEATURES = ["clicks","registrations","reg_rate","ftd_rate","ngr_per_ftd","retention_30d"]

def run_anomaly_detection(df, contamination=0.07):
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        df["anomaly_score"] = np.nan
        df["is_anomaly"]    = False
        return df

    df = df.copy()
    df["anomaly_score"] = np.nan
    df["is_anomaly"]    = False

    for profile, group in df.groupby("profile_name"):
        if len(group) < 10:
            continue
        feats = [f for f in FEATURES if f in group.columns]
        X     = group[feats].fillna(0)
        scaler = StandardScaler()
        Xs    = scaler.fit_transform(X)
        model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
        raw_pred  = model.fit_predict(Xs)
        raw_score = model.decision_function(Xs)
        norm = (raw_score.max() - raw_score) / (raw_score.max() - raw_score.min() + 1e-9)
        df.loc[group.index, "anomaly_score"] = norm
        df.loc[group.index, "is_anomaly"]    = raw_pred == -1
    return df

# ═══════════════════════════════════════════════════════════════════════════════
# FILE PARSERS
# ═══════════════════════════════════════════════════════════════════════════════
def parse_sql(content: str) -> pd.DataFrame:
    """Dependency-free SQL dump parser (no heavy regex required)."""
    import ast
    
    expected_columns = [
        "id", "name", "profile_name", "clicks", "registrations", 
        "ftd_count", "reg_rate", "ftd_rate", "ngr_per_ftd", 
        "total_ngr", "retention_30d"
    ]
    
    content_upper = content.upper()
    
    # Possible spellings of the table name
    table_markers = ["INTO `AFFILIATES`", "INTO AFFILIATES"]
    
    rows = []
    search_start = 0
    
    while True:
        # 1. Find the start of an INSERT statement
        table_idx = -1
        for marker in table_markers:
            idx = content_upper.find(marker, search_start)
            if idx != -1 and (table_idx == -1 or idx < table_idx):
                table_idx = idx
                
        if table_idx == -1:
            break  # No more INSERT statements
            
        # 2. Find the VALUES keyword
        values_idx = content_upper.find("VALUES", table_idx)
        if values_idx == -1:
            break
            
        start_idx = values_idx + len("VALUES")
        
        # 3. Find the end of the statement (semicolon)
        end_idx = content.find(";", start_idx)
        if end_idx == -1:
            end_idx = len(content)
            
        # Extract the data block: (1, 'A', ...), (2, 'B', ...)
        vals_str = content[start_idx:end_idx].strip()
        
        # Move the search pointer forward (in case the dump has multiple INSERTs)
        search_start = end_idx
        
        # 4. Clean up so it parses as Python syntax
        vals_str = vals_str.replace("NULL", "None").replace("null", "None")
        
        try:
            # Turn the SQL literal into a native list of Python tuples
            raw_data = ast.literal_eval(f"[{vals_str}]")
            for row in raw_data:
                rows.append(dict(zip(expected_columns, row)))
        except Exception as e:
            import streamlit as st
            st.warning(f"Error while parsing a data block: {e}")
            continue
            
    if not rows:
        import streamlit as st
        st.error("Could not find or parse any data. Make sure the dump contains a non-empty `affiliates` table.")
        return pd.DataFrame()
        
    return pd.DataFrame(rows)

def load_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".sql"):
        content = uploaded.read().decode("utf-8", errors="replace")
        return parse_sql(content)
    elif name.endswith((".xlsx",".xls")):
        return pd.read_excel(uploaded)
    elif name.endswith(".csv"):
        return pd.read_csv(uploaded)
    else:
        st.error("Supported formats: .sql, .xlsx, .xls, .csv")
        return pd.DataFrame()

# ═══════════════════════════════════════════════════════════════════════════════
# PLOTLY HELPERS — dark theme
# ═══════════════════════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TEXT),
    xaxis=dict(gridcolor=PANEL_B, zerolinecolor=PANEL_B),
    yaxis=dict(gridcolor=PANEL_B, zerolinecolor=PANEL_B),
    margin=dict(l=10, r=10, t=30, b=10),
)

STATUS_COLORS = {"Green": GREEN, "Yellow": YELLOW, "Red": RED, "Not Enough Data": MUTED, "Banned/Fraud": RED}

def pill(status: str) -> str:
    cls = {"Green":"green","Yellow":"yellow","Red":"red"}.get(status,"muted")
    return f'<span class="pill pill-{cls}">{status}</span>'

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p class="eyebrow">Affiliate Scoring</p>', unsafe_allow_html=True)
    st.markdown("## 🎯 Upload Data")
    uploaded = st.file_uploader(
        "SQL dump, Excel, or CSV with an affiliates table",
        type=["sql","xlsx","xls","csv"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown('<p class="eyebrow">Fraud Detection</p>', unsafe_allow_html=True)
    contamination = st.slider("Anomaly contamination", 0.02, 0.20, 0.07, 0.01,
                              help="Expected fraction of anomalies for Isolation Forest")
    run_ml = st.button("⚡ Run Anomaly Detection", use_container_width=True)
    st.markdown("---")
    st.markdown('<p class="eyebrow">Filters</p>', unsafe_allow_html=True)
    filter_profile = st.multiselect("Profile", ["SEO","PPC","Streamer","Email","Fraud"], default=[])
    filter_status  = st.multiselect("Status",  ["Green","Yellow","Red","Not Enough Data"], default=[])

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("# Affiliate Scoring Dashboard")
st.markdown('<div class="risk-rail"></div>', unsafe_allow_html=True)

if not uploaded:
    # landing state
    st.markdown("""
    <div class="card card-muted" style="text-align:center; padding: 3rem;">
        <p style="font-size:2.5rem; margin-bottom:.5rem;">📂</p>
        <p style="font-size:1.1rem; color:{TEXT}; font-weight:600;">Upload a file to start the analysis</p>
        <p style="color:{MUTED}; font-size:.9rem;">Supported: SQL dump, Excel (.xlsx), CSV</p>
        <p style="color:{MUTED}; font-size:.85rem; margin-top:1rem;">
            The file must contain the columns: <span class="mono">name, profile_name, clicks, registrations,
            ftd_count, reg_rate, ftd_rate, ngr_per_ftd, total_ngr, retention_30d</span>
        </p>
    </div>
    """.replace("{TEXT}", TEXT).replace("{MUTED}", MUTED), unsafe_allow_html=True)
    st.stop()

# ── load & score ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading and scoring data…")
def get_scored(file_bytes, file_name, contam):
    import io
    fake_upload = type("F", (), {"name": file_name, "read": lambda s: file_bytes})()
    fake_upload.read = lambda: file_bytes
    # re-create a BytesIO-like object
    buf = io.BytesIO(file_bytes)
    buf.name = file_name
    df = load_file(buf)
    if df.empty:
        return df
    return score_dataframe(df)

file_bytes = uploaded.read()
df_scored = get_scored(file_bytes, uploaded.name, contamination)

if df_scored.empty:
    st.stop()

# ── apply ML if requested ─────────────────────────────────────────────────────
if run_ml:
    with st.spinner("Running Isolation Forest…"):
        df_scored = run_anomaly_detection(df_scored, contamination)
    st.success("Anomaly detection complete!")

# ── apply sidebar filters ─────────────────────────────────────────────────────
df_view = df_scored.copy()
if filter_profile:
    df_view = df_view[df_view["profile_name"].isin(filter_profile)]
if filter_status:
    df_view = df_view[df_view["final_status"].isin(filter_status)]

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_overview, tab_profiles, tab_fraud, tab_table = st.tabs([
    "📊 Overview", "🏷️ Profiles", "🚨 Fraud Detection", "📋 Data Table"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab_overview:
    total   = len(df_view)
    greens  = (df_view["final_status"] == "Green").sum()
    yellows = (df_view["final_status"] == "Yellow").sum()
    reds    = (df_view["final_status"] == "Red").sum()
    nd      = (df_view["final_status"] == "Not Enough Data").sum()
    fraud_c = df_view["profile_name"].eq("Fraud").sum() if "profile_name" in df_view else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Affiliates", f"{total:,}")
    c2.metric("🟢 Green", f"{greens:,}", delta=f"{greens/total*100:.1f}%" if total else None)
    c3.metric("🟡 Yellow", f"{yellows:,}", delta=f"{yellows/total*100:.1f}%" if total else None)
    c4.metric("🔴 Red", f"{reds:,}", delta=f"{reds/total*100:.1f}%" if total else None)
    c5.metric("⚠️ Fraud/Unknown", f"{fraud_c:,}")

    st.markdown("---")
    col_left, col_right = st.columns([1,1])

    # donut — status distribution
    with col_left:
        st.markdown("#### Status Distribution")
        counts  = df_view["final_status"].value_counts()
        colors_ = [STATUS_COLORS.get(s, MUTED) for s in counts.index]
        fig_d = go.Figure(go.Pie(
            labels=counts.index, values=counts.values,
            hole=.55, marker_colors=colors_,
            textfont_color=TEXT,
        ))
        fig_d.update_layout(**PLOTLY_LAYOUT, showlegend=True,
                            legend=dict(font=dict(color=TEXT)))
        st.plotly_chart(fig_d, use_container_width=True)

    # bar — NGR per FTD by profile
    with col_right:
        st.markdown("#### Avg NGR/FTD by Profile")
        if "ngr_per_ftd" in df_view.columns and "profile_name" in df_view.columns:
            agg = df_view.groupby("profile_name")["ngr_per_ftd"].mean().sort_values()
            bar_colors = [GREEN if v > 60 else YELLOW if v > 30 else RED for v in agg.values]
            fig_b = go.Figure(go.Bar(
                x=agg.values, y=agg.index, orientation="h",
                marker_color=bar_colors,
                text=[f"{v:.1f}" for v in agg.values], textposition="outside",
                textfont=dict(color=TEXT, family="IBM Plex Mono"),
            ))
            fig_b.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig_b, use_container_width=True)

    # scatter — reg_rate vs ftd_rate coloured by status
    if "reg_rate" in df_view.columns and "ftd_rate" in df_view.columns:
        st.markdown("#### Registration Rate vs FTD Rate")
        sample = df_view.sample(min(600, len(df_view)), random_state=1)
        color_map = {"Green": GREEN, "Yellow": YELLOW, "Red": RED,
                     "Not Enough Data": MUTED, "Banned/Fraud": "#FF6B6B"}
        fig_s = px.scatter(
            sample,
            x="reg_rate", y="ftd_rate",
            color="final_status",
            color_discrete_map=color_map,
            hover_data=["name","profile_name","ngr_per_ftd"] if "name" in sample.columns else None,
            opacity=0.75,
        )
        fig_s.update_layout(**PLOTLY_LAYOUT,
                            legend=dict(font=dict(color=TEXT)),
                            xaxis_title="Reg Rate", yaxis_title="FTD Rate")
        st.plotly_chart(fig_s, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PROFILES
# ─────────────────────────────────────────────────────────────────────────────
with tab_profiles:
    if "profile_name" not in df_view.columns:
        st.info("Column profile_name not found.")
    else:
        profiles = df_view["profile_name"].unique()
        sel_prof = st.selectbox("Select a profile", sorted(profiles))
        sub = df_view[df_view["profile_name"] == sel_prof]

        s1,s2,s3,s4 = st.columns(4)
        s1.metric("Affiliates", len(sub))
        if "total_ngr" in sub.columns:
            s2.metric("Total NGR", f"${sub['total_ngr'].sum():,.0f}")
        if "ngr_per_ftd" in sub.columns:
            s3.metric("Avg NGR/FTD", f"${sub['ngr_per_ftd'].mean():.1f}")
        if "retention_30d" in sub.columns:
            s4.metric("Avg Retention 30d", f"{sub['retention_30d'].mean()*100:.1f}%")

        st.markdown("---")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"##### {sel_prof} — Status breakdown")
            cnt = sub["final_status"].value_counts()
            fig_p = go.Figure(go.Bar(
                x=cnt.index, y=cnt.values,
                marker_color=[STATUS_COLORS.get(s, MUTED) for s in cnt.index],
                text=cnt.values, textposition="auto",
                textfont=dict(color=TEXT, family="IBM Plex Mono"),
            ))
            fig_p.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig_p, use_container_width=True)

        with c2:
            st.markdown(f"##### {sel_prof} — Score distribution")
            scored_sub = sub[sub["final_score"].notna()]
            if len(scored_sub):
                fig_h = go.Figure(go.Histogram(
                    x=scored_sub["final_score"],
                    nbinsx=20,
                    marker_color=ACCENT,
                    opacity=0.8,
                ))
                fig_h.update_layout(**PLOTLY_LAYOUT, xaxis_title="Score", yaxis_title="Count")
                st.plotly_chart(fig_h, use_container_width=True)

        # metric distributions as box plots
        num_cols = [c for c in ["reg_rate","ftd_rate","ngr_per_ftd","retention_30d"] if c in sub.columns]
        if num_cols:
            st.markdown(f"##### {sel_prof} — Metric distributions by status")
            met_sel = st.selectbox("Metric", num_cols, key="met_sel")
            fig_box = go.Figure()
            for status, color in STATUS_COLORS.items():
                grp = sub[sub["final_status"] == status]
                if len(grp):
                    fig_box.add_trace(go.Box(
                        y=grp[met_sel], name=status,
                        marker_color=color, line_color=color,
                    ))
            fig_box.update_layout(**PLOTLY_LAYOUT, yaxis_title=met_sel)
            st.plotly_chart(fig_box, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — FRAUD DETECTION
# ─────────────────────────────────────────────────────────────────────────────
with tab_fraud:
    st.markdown("### 🚨 Fraud & Anomaly Detection")
    st.markdown("""
    <div class="card card-red">
        <p class="eyebrow">How it works</p>
        <p style="margin:0; font-size:.9rem;">
            Rule-based scoring flags known-bad patterns (high FTD rate, low NGR, zero retention).
            Isolation Forest additionally looks for <b>statistical outliers</b> within each profile —
            even when the metrics don't cross the hard thresholds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Rule-based fraud (profile_name == Fraud or unknown)
    rb_fraud = df_view[df_view["final_status"].isin(["Red","Banned/Fraud"])].copy()
    st.markdown(f"#### Rule-based Red flags — {len(rb_fraud)} affiliates")

    if not rb_fraud.empty:
        display_cols = [c for c in ["name","profile_name","reg_rate","ftd_rate","ngr_per_ftd",
                                    "retention_30d","final_score","final_status"] if c in rb_fraud.columns]
        st.dataframe(
            rb_fraud[display_cols].sort_values("final_score") if "final_score" in rb_fraud.columns
            else rb_fraud[display_cols],
            use_container_width=True, hide_index=True,
        )

        if "reg_rate" in rb_fraud.columns and "retention_30d" in rb_fraud.columns:
            st.markdown("#### Red affiliates — reg_rate vs retention_30d")
            fig_f = px.scatter(
                df_view,
                x="reg_rate", y="retention_30d",
                color="final_status",
                color_discrete_map=STATUS_COLORS,
                opacity=0.6, size_max=8,
                hover_data=["name","profile_name"] if "name" in df_view.columns else None,
            )
            # highlight red cluster
            fig_f.update_layout(**PLOTLY_LAYOUT,
                                xaxis_title="Reg Rate", yaxis_title="Retention 30d",
                                legend=dict(font=dict(color=TEXT)))
            st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.success("No affiliates with Red status.")

    # ML anomaly results
    if "is_anomaly" in df_view.columns:
        st.markdown("---")
        anomalies = df_view[df_view["is_anomaly"] == True]
        st.markdown(f"#### ML Anomalies (Isolation Forest) — {len(anomalies)} flagged")
        if not anomalies.empty:
            disp = [c for c in ["name","profile_name","anomaly_score","reg_rate","ftd_rate",
                                 "ngr_per_ftd","retention_30d","final_status"] if c in anomalies.columns]
            st.dataframe(
                anomalies[disp].sort_values("anomaly_score", ascending=False),
                use_container_width=True, hide_index=True,
            )
            # anomaly score distribution
            if "anomaly_score" in df_view.columns:
                st.markdown("#### Anomaly Score Distribution")
                fig_a = go.Figure()
                fig_a.add_trace(go.Histogram(
                    x=df_view[~df_view["is_anomaly"]]["anomaly_score"],
                    name="Normal", marker_color=GREEN, opacity=0.7, nbinsx=40,
                ))
                fig_a.add_trace(go.Histogram(
                    x=df_view[df_view["is_anomaly"]]["anomaly_score"],
                    name="Anomaly", marker_color=RED, opacity=0.8, nbinsx=40,
                ))
                fig_a.update_layout(**PLOTLY_LAYOUT, barmode="overlay",
                                    xaxis_title="Anomaly Score", yaxis_title="Count",
                                    legend=dict(font=dict(color=TEXT)))
                st.plotly_chart(fig_a, use_container_width=True)
        else:
            st.success("ML found no anomalies at the current contamination threshold.")
    else:
        st.info("Click **⚡ Run Anomaly Detection** in the sidebar to run the ML model.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — DATA TABLE
# ─────────────────────────────────────────────────────────────────────────────
with tab_table:
    st.markdown(f"### All Affiliates — {len(df_view):,} rows")

    search = st.text_input("🔍 Search by name", "")
    show_df = df_view.copy()
    if search and "name" in show_df.columns:
        show_df = show_df[show_df["name"].str.contains(search, case=False, na=False)]

    # format columns
    display_cols = [c for c in [
        "id","name","profile_name","clicks","registrations","ftd_count",
        "reg_rate","ftd_rate","ngr_per_ftd","total_ngr","retention_30d",
        "final_score","final_status","status"
    ] if c in show_df.columns]

    sort_col = st.selectbox("Sort by", [c for c in ["final_score","ngr_per_ftd","total_ngr","clicks"] if c in show_df.columns])
    asc      = st.checkbox("Ascending", False)

    show_df = show_df[display_cols].sort_values(sort_col, ascending=asc) if sort_col else show_df[display_cols]
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    # download button
    csv_buf = io.StringIO()
    show_df.to_csv(csv_buf, index=False)
    st.download_button("⬇️ Download CSV", csv_buf.getvalue(), "scored_affiliates.csv", "text/csv")