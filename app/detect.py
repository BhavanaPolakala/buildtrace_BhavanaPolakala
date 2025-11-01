from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from typing import List
from math import sqrt
from datetime import datetime
import time
import os

# Google Cloud BigQuery
from google.cloud import bigquery

app = FastAPI(
    title="BuildTrace API",
    description="Detects and logs changes between building design drawings.",
    version="2.3.0",
)

# ==========================================
# 🔹 Pydantic Models
# ==========================================

class DrawingObject(BaseModel):
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float


class CompareRequest(BaseModel):
    old: List[DrawingObject]
    new: List[DrawingObject]


class CompareResponse(BaseModel):
    added: List[str]
    removed: List[str]
    moved: List[str]
    summary: str


# ==========================================
# 🔹 Metrics (in-memory)
# ==========================================

metrics = {
    "processed": 0,
    "avg_latency_ms": 0.0,
    "total_added": 0,
    "total_removed": 0,
    "total_moved": 0,
    "last_summary": None,
}

# ==========================================
# 🔹 BigQuery Setup
# ==========================================

try:
    PROJECT_ID = os.getenv("PROJECT_ID", "buildtrace-demo")
    DATASET_ID = "buildtrace_metrics"
    TABLE_ID = f"{PROJECT_ID}.{DATASET_ID}.daily_stats"
    bq_client = bigquery.Client()
    print(f"✅ BigQuery client initialized for table: {TABLE_ID}")
except Exception as e:
    print(f"⚠️ BigQuery initialization failed: {e}")
    bq_client = None


def record_metrics_to_bigquery(record: dict):
    """Insert a single record into BigQuery table."""
    if not bq_client:
        print("⚠️ Skipping BigQuery insert — client not initialized.")
        return
    try:
        errors = bq_client.insert_rows_json(TABLE_ID, [record])
        if errors:
            print("❌ BigQuery insert error:", errors)
        else:
            print(f"✅ Logged metrics to BigQuery: {record}")
    except Exception as e:
        print("⚠️ Failed to write to BigQuery:", e)


# ==========================================
# 🔹 Core Detection Logic
# ==========================================

def detect_changes(old_objects: List[DrawingObject], new_objects: List[DrawingObject]) -> CompareResponse:
    """Detect added, removed, and moved objects between two drawings."""
    old_dict = {obj.id: obj for obj in old_objects}
    new_dict = {obj.id: obj for obj in new_objects}

    added, removed, moved = [], [], []

    for new_id, new_obj in new_dict.items():
        if new_id not in old_dict:
            added.append(f"{new_id} ({new_obj.type} at {new_obj.x},{new_obj.y})")

    for old_id, old_obj in old_dict.items():
        if old_id not in new_dict:
            removed.append(f"{old_id} ({old_obj.type} removed)")

    for obj_id in set(old_dict.keys()) & set(new_dict.keys()):
        old_obj = old_dict[obj_id]
        new_obj = new_dict[obj_id]
        dx = new_obj.x - old_obj.x
        dy = new_obj.y - old_obj.y
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            dist = round(sqrt(dx**2 + dy**2), 2)
            moved.append(f"{obj_id} moved ({dx:.1f},{dy:.1f},{dist} units)")

    summary_parts = []
    if moved:
        summary_parts.append("; ".join(moved))
    if added:
        summary_parts.append("; ".join(added))
    if removed:
        summary_parts.append("; ".join(removed))
    summary = "; ".join(summary_parts) if summary_parts else "No changes detected."

    return CompareResponse(added=added, removed=removed, moved=moved, summary=summary)


# ==========================================
# 🔹 API Endpoints
# ==========================================

@app.post("/process", response_model=CompareResponse, summary="Process Drawings")
def process_drawings(request: CompareRequest):
    """Compare old vs new drawings and log metrics to BigQuery."""
    start = time.time()
    try:
        result = detect_changes(request.old, request.new)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")

    elapsed = (time.time() - start) * 1000

    metrics["processed"] += 1
    metrics["avg_latency_ms"] = (metrics["avg_latency_ms"] + elapsed) / 2
    metrics["total_added"] += len(result.added)
    metrics["total_removed"] += len(result.removed)
    metrics["total_moved"] += len(result.moved)
    metrics["last_summary"] = result.summary

    record = {
        "date": datetime.utcnow().date().isoformat(),
        "total_added": len(result.added),
        "total_removed": len(result.removed),
        "total_moved": len(result.moved),
        "latency_ms": round(elapsed, 3),
        "summary_text": result.summary,
    }

    record_metrics_to_bigquery(record)

    return result


@app.get("/metrics", summary="Get Current Metrics")
def get_metrics():
    return metrics


@app.get("/metrics/summary", summary="Get Metrics Summary")
def get_metrics_summary():
    avg_changes = (
        (metrics["total_added"] + metrics["total_removed"] + metrics["total_moved"])
        / metrics["processed"]
        if metrics["processed"] > 0
        else 0
    )
    anomaly = avg_changes > 5
    return {
        "processed_drawings": metrics["processed"],
        "avg_latency_ms": round(metrics["avg_latency_ms"], 3),
        "avg_changes_per_drawing": round(avg_changes, 2),
        "total_added": metrics["total_added"],
        "total_removed": metrics["total_removed"],
        "total_moved": metrics["total_moved"],
        "anomaly_detected": anomaly,
        "note": "High activity detected" if anomaly else "Normal range",
    }


# ==========================================
# 🔹 Daily Metrics (BigQuery)
# ==========================================

@app.get("/metrics/daily", summary="Get Daily Metrics from BigQuery")
def get_daily_metrics():
    """Fetch last 7 days of aggregated metrics from BigQuery."""
    if not bq_client:
        raise HTTPException(status_code=500, detail="BigQuery client not initialized")

    try:
        query = f"""
            SELECT
                date,
                SUM(total_added) AS total_added,
                SUM(total_removed) AS total_removed,
                SUM(total_moved) AS total_moved,
                AVG(latency_ms) AS avg_latency_ms
            FROM `{PROJECT_ID}.{DATASET_ID}.daily_stats`
            GROUP BY date
            ORDER BY date DESC
            LIMIT 7
        """
        query_job = bq_client.query(query)
        results = [dict(row) for row in query_job.result()]
        return {"daily_metrics": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query BigQuery: {str(e)}")


# ==========================================
# 🔹 NEW: Anomaly Detection (BigQuery)
# ==========================================

@app.get("/metrics/anomalies", summary="Detect Anomalous Activity Days")
def detect_anomalies():
    """Identify days with unusually high change activity."""
    if not bq_client:
        raise HTTPException(status_code=500, detail="BigQuery client not initialized")

    try:
        query = f"""
            SELECT
                date,
                (total_added + total_removed + total_moved) AS total_changes
            FROM `{PROJECT_ID}.{DATASET_ID}.daily_stats`
            ORDER BY date DESC
            LIMIT 14
        """
        rows = [dict(row) for row in bq_client.query(query).result()]
        if not rows:
            return {"anomalies": [], "message": "No data available"}

        avg_changes = sum(r["total_changes"] for r in rows) / len(rows)
        threshold = avg_changes * 2.0

        anomalies = [r for r in rows if r["total_changes"] > threshold]

        return {
            "threshold": round(threshold, 2),
            "avg_changes": round(avg_changes, 2),
            "anomalies": anomalies,
            "total_days_checked": len(rows),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {str(e)}")


# ==========================================
# 🔹 Health Check
# ==========================================

@app.get("/health", summary="Health Check")
def health_check():
    return {"status": "ok", "service": "buildtrace", "version": "2.3.0"}


# ==========================================
# 🔹 Local Debug
# ==========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
