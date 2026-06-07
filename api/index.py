import os
import json
import statistics
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CRITICAL FIX: Removed allow_credentials=True so the "*" origin works correctly!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

class TelemetryRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

# Ensure Vercel can find the JSON file in its cloud environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(BASE_DIR, "q-vercel-latency.json")

def load_data():
    with open(JSON_PATH, "r") as f:
        return json.load(f)

@app.post("/metrics")
def get_metrics(req: TelemetryRequest):
    telemetry_data = load_data()
    results = {}
    
    for region in req.regions:
        # Filter down to just the region we care about right now
        region_data = [d for d in telemetry_data if d.get("region") == region]
        
        if not region_data:
            continue
            
        latencies = [d["latency_ms"] for d in region_data]
        uptimes = [d["uptime_pct"] for d in region_data]
        
        # Calculate the required metrics
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for lat in latencies if lat > req.threshold_ms)
        
        # 95th Percentile logic
        if len(latencies) > 1:
            p95_latency = statistics.quantiles(latencies, n=100, method='inclusive')[94]
        else:
            p95_latency = latencies[0]
            
        # Format exactly as requested
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }
        
    return results
