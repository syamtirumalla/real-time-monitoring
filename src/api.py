from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client import InfluxDBClient
import os
from dotenv import load_dotenv
import pandas as pd

from src.model_inference import get_all_forecasts

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

app = FastAPI(title="Real-Time Monitoring API")

# Allow the React dev server (usually localhost:3000) to call this API.
# Without CORS, browsers block requests from a different origin/port by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "message": "Real-Time Monitoring API is running"}


@app.get("/live-metrics")
def live_metrics():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    flux_query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -10m)
      |> filter(fn: (r) => r._measurement == "cpu" or r._measurement == "mem")
      |> filter(fn: (r) => r._field == "usage_active" or r._field == "available_percent")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: 5)
    '''

    result = query_api.query_data_frame(flux_query)
    client.close()

    if isinstance(result, list):
        result = pd.concat(result, ignore_index=True) if result else pd.DataFrame()

    if result.empty:
        return {"cpu": None, "memory": None, "timestamp": None}

    # Take the most recent non-null value for each metric, since cpu and
    # mem readings can land in separate rows even within the same window
    latest_cpu = result["usage_active"].dropna().iloc[0] if "usage_active" in result and not result["usage_active"].dropna().empty else None
    latest_memory = result["available_percent"].dropna().iloc[0] if "available_percent" in result and not result["available_percent"].dropna().empty else None
    latest_time = str(result["_time"].iloc[0])

    return {
        "cpu": latest_cpu,
        "memory": latest_memory,
        "timestamp": latest_time,
    }


@app.get("/forecast")
def forecast(steps: int = 48):
    return get_all_forecasts(steps=steps)