🏗️ BuildTrace — Intelligent Design Change Tracking System:
----------------------------------------------------------

BuildTrace is a cloud-native system that detects, stores, and visualizes design changes across construction or engineering drawings. It processes JSON-based design snapshots, identifies modifications (added, removed, moved entities), and provides real-time metrics, anomaly detection, and visualization through a web dashboard.

----------------------------------------------------------
🚀 Deployed Services
----------------------------------------------------------
Component              Platform             URL / Resource
----------------------------------------------------------
FastAPI backend        Google Cloud Run     https://buildtrace-114311994469.us-central1.run.app
Metrics database       Google BigQuery      buildtrace-demo.buildtrace_metrics.daily_stats
Dashboard (local)      Streamlit            streamlit run dashboard.py

----------------------------------------------------------
⚙️ System Architecture & Data Flow
----------------------------------------------------------
User → POST /process → FastAPI (Cloud Run)
       → Change Detection Engine → Metrics Aggregator
       → BigQuery (daily_stats) → Streamlit Dashboard
       → User Visualization

Components:
• FastAPI App: Handles /process, /metrics, /anomalies, /health.
• BigQuery: Stores aggregated daily metrics.
• Change Detection Engine: Compares JSON drawings, classifies added/removed/moved.
• Metrics Aggregator: Computes latency and totals.
• Streamlit + Plotly UI: Visualizes trends and anomalies.

----------------------------------------------------------
☁️ Scaling & Fault Tolerance Strategy
----------------------------------------------------------
Layer            Strategy                           Details
----------------------------------------------------------
API (FastAPI)    Stateless Cloud Run container       Auto-scales with traffic.
BigQuery         Serverless analytical backend       Scales automatically with data size.
UI (Streamlit)   Lightweight client                  Can run locally or on Streamlit Cloud.
Error Handling   Graceful + Cloud Logging            Clear error codes (422, 500).
Persistence      Append-only BigQuery model          Safe across restarts.

Fault-tolerance:
• Retries on BigQuery inserts.
• /health endpoint for uptime checks.
• Cached metrics (st.cache_data) for transient downtime.

----------------------------------------------------------
📊 Metrics Computation Design
----------------------------------------------------------
Metrics:
• total_added, total_removed, total_moved — entity change counts.
• avg_latency_ms — average request latency.
• processed_drawings — total comparisons.
• avg_changes_per_drawing — mean of all change counts.
• anomaly_detected — threshold flag.

P99 Latency Estimation:
Each request logs latency_ms.  
Approximation query:

SELECT APPROX_QUANTILES(latency_ms,100)[OFFSET(99)]
FROM `buildtrace-demo.buildtrace_metrics.daily_stats`;

----------------------------------------------------------
🔍 Anomaly Detection Logic
----------------------------------------------------------
Condition:
avg_changes_per_day > 2 × rolling_average(7d)
Default threshold: 4.0
Anomalies returned by /metrics/anomalies and shown as ⚠️ stars in dashboard.

----------------------------------------------------------
💡 Trade-Offs & Design Decisions
----------------------------------------------------------
Storage backend  : BigQuery (analytics) vs Firestore (realtime) — chose BigQuery for scalability.
Latency tracking : Simple mean vs percentile tracking — mean used for speed.
Anomaly logic    : Static threshold — easier to maintain than ML models.
Deployment       : Cloud Run — managed scaling with occasional cold starts.
Dashboard        : Streamlit — rapid visualization, limited custom styling.

----------------------------------------------------------
🧠 Future Extensions
----------------------------------------------------------
• Trend analytics (week-over-week % change).
• ML-based anomaly detection.
• Pub/Sub dead-letter queue for malformed JSONs.
• Slack/email alerting.
• Configurable thresholds (/config/threshold endpoint).
• Deploy Streamlit dashboard on Cloud Run or Streamlit Cloud.

----------------------------------------------------------
🧾 Example Workflow
----------------------------------------------------------
1️⃣ Send comparison:
curl -X POST 'https://buildtrace-114311994469.us-central1.run.app/process' \
     -H 'Content-Type: application/json' \
     -d '{"old":[{"id":"A1","type":"wall","x":10,"y":5}],
          "new":[{"id":"A1","type":"wall","x":12,"y":5}]}'

2️⃣ Retrieve summary:
curl https://buildtrace-114311994469.us-central1.run.app/metrics/summary

3️⃣ Check anomalies:
curl https://buildtrace-114311994469.us-central1.run.app/metrics/anomalies

4️⃣ Visualize dashboard:
streamlit run dashboard.py

----------------------------------------------------------
Author:
Bhavana Polakala

