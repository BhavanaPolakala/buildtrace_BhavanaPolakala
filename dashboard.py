import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# ========== CONFIG ==========
API_BASE = "https://buildtrace-114311994469.us-central1.run.app"

st.set_page_config(page_title="🏗️ BuildTrace Dashboard", page_icon="📊", layout="wide")

st.title("🏗️ BuildTrace — Metrics & Anomaly Dashboard")
st.caption("Interactive visualization of daily design change metrics from the BuildTrace API")

# ========== FETCH HELPERS ==========
@st.cache_data(ttl=300)
def fetch_daily_metrics():
    r = requests.get(f"{API_BASE}/metrics/daily")
    return pd.DataFrame(r.json().get("daily_metrics", [])) if r.status_code == 200 else pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_anomalies():
    r = requests.get(f"{API_BASE}/metrics/anomalies")
    return r.json() if r.status_code == 200 else {}

# ========== REFRESH + LOAD ==========
col1, col2 = st.columns([4, 1])
with col1:
    st.subheader("📈 Daily Change Metrics")
with col2:
    if st.button("Refresh Data"):
        st.cache_data.clear()

daily_df = fetch_daily_metrics()
anomaly_data = fetch_anomalies()

# ========== VALIDATION ==========
if daily_df.empty:
    st.warning("No data found in BigQuery yet. Run a few /process requests first.")
    st.stop()

daily_df["date"] = pd.to_datetime(daily_df["date"])
daily_df = daily_df.sort_values("date")

# ========== PLOTLY CHART ==========
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=daily_df["date"], y=daily_df["total_added"],
    mode="lines+markers", name="Added ",
    line=dict(color="limegreen", width=2),
    hovertemplate="Date: %{x|%Y-%m-%d}<br>Added: %{y}<extra></extra>"
))
fig.add_trace(go.Scatter(
    x=daily_df["date"], y=daily_df["total_removed"],
    mode="lines+markers", name="Removed ",
    line=dict(color="red", width=2),
    hovertemplate="Date: %{x|%Y-%m-%d}<br>Removed: %{y}<extra></extra>"
))
fig.add_trace(go.Scatter(
    x=daily_df["date"], y=daily_df["total_moved"],
    mode="lines+markers", name="Moved 🔵",
    line=dict(color="dodgerblue", width=2),
    hovertemplate="Date: %{x|%Y-%m-%d}<br>Moved: %{y}<extra></extra>"
))

# ========== ANOMALY OVERLAY ==========
anomalies = anomaly_data.get("anomalies", [])
if anomalies:
    anomaly_df = pd.DataFrame(anomalies)
    anomaly_df["date"] = pd.to_datetime(anomaly_df["date"])
    fig.add_trace(go.Scatter(
        x=anomaly_df["date"], y=anomaly_df["total_changes"],
        mode="markers",
        name=" ⚠️ Anomaly",
        marker=dict(color="orange", size=12, symbol="star"),
        hovertemplate=" Date: %{x|%Y-%m-%d}<br>Total Changes: %{y}<extra></extra>"
    ))

fig.update_layout(
    title="📊 Design Change Trends Over Time",
    xaxis_title="Date",
    yaxis_title="Count",
    template="plotly_dark",
    height=450,
    legend_title="Metrics",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# ========== METRICS ==========
c1, c2 = st.columns(2)
c1.metric("Average Daily Changes", f"{anomaly_data.get('avg_changes', 0):.2f}")
c2.metric("Anomaly Threshold", f"{anomaly_data.get('threshold', 0):.2f}")

# ========== ANOMALY TABLE ==========
st.subheader(" Detected Anomalies")
if anomalies:
    st.dataframe(anomaly_df, use_container_width=True)
else:
    st.success(" No anomalies detected — all systems normal.")

# ========== FOOTER ==========
st.markdown("---")
st.caption(f"Data from [{API_BASE}]({API_BASE}) • Last refreshed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

