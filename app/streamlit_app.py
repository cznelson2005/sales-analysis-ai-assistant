import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sales AI Assistant",
    page_icon="📊",
    layout="wide"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #2563EB;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1e293b;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .anomaly-card {
        background: #fff7ed;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #f97316;
        margin-bottom: 12px;
        color: #1e293b;
    }
    .anomaly-high {
        border-left: 4px solid #ef4444;
        background: #fef2f2;
        color: #1e293b;
    }
    .section-divider {
        border-top: 1px solid #e2e8f0;
        margin: 24px 0;
    }
    .driver-card {
        background: #f0f9ff;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        border-left: 3px solid #0ea5e9;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# ── Load results ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

#st.write(RESULTS_DIR)
#st.write(os.listdir(RESULTS_DIR) if os.path.exists(RESULTS_DIR) else "folder not found")

@st.cache_data
def load_result(market: str) -> dict:
    path = os.path.join(RESULTS_DIR, f"{market}_2022_2024.json")
    with open(path, "r") as f:
        return json.load(f)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Sales AI Assistant")
    st.markdown("---")

    selected_market = st.selectbox(
        "Select Market",
        options=["All", "SG", "HK", "AU", "UK"],
        index=0
    )

    st.markdown("---")
    st.markdown("**Period**")
    st.markdown("Jan 2022 — Dec 2024")
    st.markdown("---")
    st.caption("Results are pre-computed. In production, this would call the API live with any selected date range.")

# ── Load data ──────────────────────────────────────────────────────────────────
try:
    data = load_result(selected_market)
except FileNotFoundError:
    st.error(f"Result file for {selected_market} not found. Please run the pipeline first.")
    st.stop()

overview   = data.get('overview', '')
anomaly    = data.get('anomaly', {})
deep_dive  = data.get('deep_dive', {})
summary    = data.get('summary', '')
context    = data.get('context', {})

# MRR data for charts
mrr_df    = pd.DataFrame(context.get('mrr_data', []))
churn_df  = pd.DataFrame(context.get('churn_data', []))

# ── Header ─────────────────────────────────────────────────────────────────────
st.title(f"Sales Analysis — {selected_market} Market")
st.markdown(f"**Period:** Jan 2022 — Dec 2024 &nbsp;|&nbsp; **Market:** {selected_market}")
st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Anomalies", "🔬 Deep Dive", "📝 Summary"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Headline metrics ───────────────────────────────────────────────────────
    metrics = data.get('headline_metrics', {})

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Current MRR", f"${metrics.get('curr_mrr', 0):,.0f}")
    with col2:
        mrr_growth = metrics.get('mrr_growth', 0)
        st.metric("MRR Growth", f"{mrr_growth:+.1f}%")
    with col3:
        st.metric("Active Customers", f"{metrics.get('active_customers', 0):,}")
    with col4:
        st.metric("Churn Rate", f"{metrics.get('churn_rate_pct', 0):.1f}%")
    with col5:
        st.metric("LTV:CAC", f"{metrics.get('ltv_cac_ratio', 0):.1f}x")

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    if not mrr_df.empty:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("MRR Trend")
            mrr_by_month = (
                mrr_df.groupby('month')['monthly_revenue']
                .sum().reset_index()
                .sort_values('month')
            )
            fig = px.line(
                mrr_by_month, x='month', y='monthly_revenue',
                labels={'monthly_revenue': 'MRR ($)', 'month': ''},
                color_discrete_sequence=['#2563EB']
            )
            fig.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("MRR by Market")
            if selected_market == 'All':
                mrr_by_market = (
                    mrr_df.groupby('market')['monthly_revenue']
                    .sum().reset_index()
                    .sort_values('monthly_revenue', ascending=False)
                )
                fig2 = px.bar(
                    mrr_by_market, x='market', y='monthly_revenue',
                    labels={'monthly_revenue': 'Total MRR ($)', 'market': ''},
                    color='market',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig2.update_layout(
                    height=300, margin=dict(l=0, r=0, t=10, b=0),
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                mrr_by_segment = (
                    mrr_df.groupby('segment')['monthly_revenue']
                    .sum().reset_index()
                )
                fig2 = px.pie(
                    mrr_by_segment, values='monthly_revenue', names='segment',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig2.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Overview commentary ────────────────────────────────────────────────────
    st.subheader("🤖 AI Analysis")
    
    import re
    
    # Parse overview into sections
    sections = re.split(r'─+', overview)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Split header from content
        if ':' in section:
            header, content = section.split(':', 1)
            header = header.strip()
            content = content.strip()
            if header:
                st.subheader(header)
            if content:
                st.markdown(content)
        else:
            st.markdown(section)
        
        st.markdown("")  # spacing between sections

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANOMALIES
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🔍 Anomaly Detection")
    st.caption(anomaly.get('summary', ''))
    st.markdown("---")

    if anomaly.get('has_anomaly') and anomaly.get('anomalies'):
        anomalies = anomaly['anomalies']
        st.markdown(f"**{len(anomalies)} anomaly/anomalies detected**")
        st.markdown("")

        for a in anomalies:
            severity  = a.get('severity', 'Medium')
            metric    = a.get('metric', '')
            month     = a.get('month', '')
            drill_mkt = a.get('drill_down_market', '')

            card_class = "anomaly-card anomaly-high" if severity == "High" else "anomaly-card"
            icon = "🔴" if severity == "High" else "🟡"
            month_str = f" · {month}" if month else ""
            market_str = f" · Drill down: **{drill_mkt}**" if drill_mkt else ""

            st.markdown(f"""
<div class="{card_class}">
    <strong>{icon} {metric}{month_str}</strong> [{severity}]{market_str}<br><br>
    <b>Observation:</b> {a.get('observation', '')}<br>
    <b>Possible Cause:</b> {a.get('possible_cause', '')}
</div>
""", unsafe_allow_html=True)

        # ── Churn trend chart ──────────────────────────────────────────────────
        if not churn_df.empty:
            st.markdown("---")
            st.subheader("Churn Trend")
            churn_by_month = (
                churn_df.groupby('month')['customers_lost']
                .sum().reset_index().sort_values('month')
            )
            fig3 = px.bar(
                churn_by_month, x='month', y='customers_lost',
                labels={'customers_lost': 'Churned Customers', 'month': ''},
                color_discrete_sequence=['#ef4444']
            )
            fig3.update_layout(
                height=300, margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig3, use_container_width=True)

    else:
        st.success("✅ No anomalies detected — all metrics within normal range")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔬 Deep Dive Analysis")

    if not deep_dive:
        st.info("No market-specific anomalies detected — Deep Dive not triggered.")
    else:
        for market, result in deep_dive.items():
            st.markdown(f"### {market} Market")
            st.markdown(f"_{result.get('anomaly_summary', '')}_")
            st.markdown("")

            # Drivers
            st.markdown("**Key Drivers**")
            for d in result.get('drivers', []):
                contribution = d.get('contribution', 'Medium')
                icon = "🔴" if contribution == "High" else "🟡"
                st.markdown(f"""
<div class="driver-card">
    {icon} <strong>[{d.get('dimension', '')}] {d.get('driver', '')}</strong> ({contribution})<br>
    {d.get('observation', '')}
</div>
""", unsafe_allow_html=True)

            st.markdown("")
            col_rc, col_ra = st.columns(2)
            with col_rc:
                st.markdown("**Root Cause**")
                st.info(result.get('root_cause', ''))
            with col_ra:
                st.markdown("**Recommended Action**")
                st.success(result.get('recommended_action', ''))

            if len(deep_dive) > 1:
                st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📝 Executive Summary")
    st.markdown("---")
    #st.markdown(summary)

    sections = re.split(r'─+', summary)
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Split header from content
        if ':' in section:
            header, content = section.split(':', 1)
            header = header.strip()
            content = content.strip()
            if header:
                st.subheader(header)
            if content:
                st.markdown(content)
        else:
            st.markdown(section)
        
        st.markdown("")  # spacing between sections
