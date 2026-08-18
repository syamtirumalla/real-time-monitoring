import os
from datetime import datetime
from influxdb_client import InfluxDBClient
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

print("URL:", os.getenv("INFLUX_URL"))
print("TOKEN:", os.getenv("INFLUX_TOKEN"))

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

CSV_PATH = "data/system_metrics.csv"


def get_last_timestamp():
    """Check the CSV for the most recent timestamp we've already saved."""
    if not os.path.exists(CSV_PATH):
        return None
    df = pd.read_csv(CSV_PATH)
    if df.empty:
        return None
    last = pd.to_datetime(df["_time"]).max()
    return last.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_new_data():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    last_time = get_last_timestamp()
    range_start = f'time(v: "{last_time}")' if last_time else "-30d"

    flux_query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {range_start})
      |> filter(fn: (r) => r._measurement == "cpu" or r._measurement == "mem")
      |> filter(fn: (r) => r._field == "usage_active" or r._field == "available_percent")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    result = query_api.query_data_frame(flux_query)
    client.close()

    # query_data_frame can return a single DataFrame OR a list of them
    # depending on how many separate tables InfluxDB internally produced
    if isinstance(result, list):
        result = pd.concat(result, ignore_index=True)

    return result

if __name__ == "__main__":
    df = fetch_new_data()
    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print(df.head())
    print(f"Fetched {len(df)} rows")

    os.makedirs("data", exist_ok=True)
    df.to_csv(CSV_PATH, mode="a", header=not os.path.exists(CSV_PATH), index=False)
    print(f"Saved to {CSV_PATH}")