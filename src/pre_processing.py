import pandas as pd

RAW_CSV_PATH = "data/system_metrics.csv"
PROCESSED_CSV_PATH = "data/processed_metrics.csv"


def load_and_clean():
    df = pd.read_csv(RAW_CSV_PATH)

    # Parse the time column as actual datetime objects, not strings
    df["_time"] = pd.to_datetime(df["_time"])

    # Keep only the columns we actually care about for forecasting
    df = df[["_time", "usage_active", "available_percent"]]

    # Sort chronologically -- important since incremental ingestion runs
    # may have appended rows slightly out of order
    df = df.sort_values("_time")

    # Set _time as the index -- required for time-series operations
    # and for the SARIMA model later
    df = df.set_index("_time")

    #To avoid any dupliactes so we merge them using this 
    df = df.groupby(df.index).mean()
    
    # Fill gaps: forward-fill first (carry last known value forward),
    # then backward-fill any remaining gaps at the very start of the data
    df["usage_active"] = df["usage_active"].ffill().bfill()
    df["available_percent"] = df["available_percent"].ffill().bfill()

    return df


if __name__ == "__main__":
    df = load_and_clean()
    print("Shape after cleaning:", df.shape)
    print(df.head(10))
    print("\nAny remaining NaNs?")
    print(df.isna().sum())

    df.to_csv(PROCESSED_CSV_PATH)
    print(f"\nSaved cleaned data to {PROCESSED_CSV_PATH}")