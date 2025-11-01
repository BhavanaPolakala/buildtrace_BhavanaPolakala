# app/main.py
from fastapi import FastAPI
from app.models import CompareRequest, CompareResponse
from app.detect import detect_changes
import time

app = FastAPI(title="BuildTrace System")

# ✅ Global metrics storage
metrics = {
    "processed": 0,
    "avg_latency_ms": 0.0,
    "total_added": 0,
    "total_removed": 0,
    "total_moved": 0,
    "last_summary": None
}


@app.get("/")
def home():
    return {"message": "BuildTrace mini API running ✅"}


@app.post("/process", response_model=CompareResponse)
def process_drawings(req: CompareRequest):
    start = time.time()
    result = detect_changes(req.old, req.new)
    duration = (time.time() - start) * 1000

    # update metrics
    metrics["processed"] += 1
    metrics["avg_latency_ms"] = (
        (metrics["avg_latency_ms"] * (metrics["processed"] - 1) + duration)
        / metrics["processed"]
    )
    metrics["total_added"] += len(result.added)
    metrics["total_removed"] += len(result.removed)
    metrics["total_moved"] += len(result.moved)
    metrics["last_summary"] = result.summary


    return result


@app.get("/metrics")
def get_metrics():
    return metrics


@app.get("/metrics/summary")
def get_metrics_summary():
    """Returns analytics-style summary with anomaly flag."""
    avg_changes = (
        metrics["total_added"] + metrics["total_removed"] + metrics["total_moved"]
    ) / metrics["processed"] if metrics["processed"] else 0

    anomaly_flag = avg_changes > 5  # arbitrary threshold for “spike” in changes
    return {
        "processed_drawings": metrics["processed"],
        "avg_latency_ms": round(metrics["avg_latency_ms"], 2),
        "avg_changes_per_drawing": round(avg_changes, 2),
        "total_added": metrics["total_added"],
        "total_removed": metrics["total_removed"],
        "total_moved": metrics["total_moved"],
        "anomaly_detected": anomaly_flag,
        "note": "High anomaly rate" if anomaly_flag else "Normal range",
    }


@app.get("/health")
def get_health():
    return {"status": "healthy"}

