import os
import json
import statistics
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

class TelemetryRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

# Construct the exact path to find the JSON file in Vercel's cloud environment
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
        region_data = [d for d in telemetry_data if d.get("region") == region]
        
        if not region_data:
            continue
            
        latencies = [d["latency_ms"] for d in region_data]
        uptimes = [d["uptime_pct"] for d in region_data]
        
        avg_latency = statistics.mean(latencies)
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for lat in latencies if lat > req.threshold_ms)
        
        if len(latencies) > 1:
            p95_latency = statistics.quantiles(latencies, n=100, method='inclusive')[94]
        else:
            p95_latency = latencies[0]
            
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": breaches
        }
        
    return results