from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
from typing import List

app = FastAPI()

# Professor's exact CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Expose-Headers": "Access-Control-Allow-Origin",
}

# Define request model
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

# Load telemetry data
with open("q-vercel-latency.json", "r") as f:
    telemetry_data = json.load(f)

@app.get("/")
def read_root():
    """Health check endpoint"""
    return JSONResponse(
        content={"status": "ok", "message": "Use POST / to analyze latency"},
        headers=CORS_HEADERS
    )

@app.post("/")
def analyze_latency(request: AnalyticsRequest):
    """Analyze latency data for specified regions"""
    results = {}
    
    for region in request.regions:
        # Filter data for this region
        region_records = [
            record for record in telemetry_data 
            if record.get("region") == region
        ]
        
        if not region_records:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
            continue
        
        # Extract values
        latencies = [r["latency_ms"] for r in region_records]
        uptimes = [r["uptime_pct"] for r in region_records]
        
        # Calculate average latency
        avg_latency = sum(latencies) / len(latencies)
        
        # Calculate 95th percentile using linear interpolation
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        # Use the formula: index = (n - 1) * 0.95
        # This gives us the position for interpolation
        percentile_index = (n - 1) * 0.95
        lower_index = int(percentile_index)
        upper_index = lower_index + 1
        
        if upper_index >= n:
            p95_latency = sorted_latencies[lower_index]
        else:
            # Linear interpolation between the two closest values
            fraction = percentile_index - lower_index
            p95_latency = sorted_latencies[lower_index] + fraction * (sorted_latencies[upper_index] - sorted_latencies[lower_index])
        
        # Calculate average uptime
        avg_uptime = sum(uptimes) / len(uptimes)
        
        # Count breaches (latency above threshold)
        breaches = sum(1 for lat in latencies if lat > request.threshold_ms)
        
        results[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }
    
    # Wrap results in "regions" key
    response_data = {"regions": results}
    
    return JSONResponse(
        content=response_data,
        headers=CORS_HEADERS
    )

@app.options("/")
def options_handler():
    """Handle OPTIONS preflight requests"""
    return JSONResponse(
        content={},
        headers=CORS_HEADERS
    )
