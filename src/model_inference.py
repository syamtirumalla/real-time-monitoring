import pickle
import pandas as pd

CPU_MODEL_PATH = "models/cpu_sarima.pkl"
MEMORY_MODEL_PATH = "models/memory_sarima.pkl"


def load_model(path):
    with open(path, "rb") as f:
        model = pickle.load(f)
    return model


def forecast_metric(model, steps=48, freq="5min"):
    """
    Returns a DataFrame with columns: timestamp, forecast, lower_bound, upper_bound
    """
    result = model.get_forecast(steps=steps)
    predicted_mean = result.predicted_mean
    conf_int = result.conf_int()

    # The pickled model loses its datetime index, so we rebuild real future
    # timestamps manually, starting from now, spaced by our collection interval
    last_time = pd.Timestamp.now()
    future_timestamps = pd.date_range(start=last_time, periods=steps, freq=freq)

    df = pd.DataFrame({
        "timestamp": future_timestamps,
        "forecast": predicted_mean.values,
        "lower_bound": conf_int.iloc[:, 0].values,
        "upper_bound": conf_int.iloc[:, 1].values,
    })
    return df


def get_all_forecasts(steps=48):
    cpu_model = load_model(CPU_MODEL_PATH)
    memory_model = load_model(MEMORY_MODEL_PATH)

    cpu_forecast = forecast_metric(cpu_model, steps=steps)
    memory_forecast = forecast_metric(memory_model, steps=steps)

    return {
        "cpu": cpu_forecast.to_dict(orient="records"),
        "memory": memory_forecast.to_dict(orient="records"),
    }


if __name__ == "__main__":
    forecasts = get_all_forecasts(steps=12)  # smaller for a quick test, 1 hour ahead

    print("=== CPU Forecast (first 5) ===")
    for row in forecasts["cpu"][:5]:
        print(row)

    print("\n=== Memory Forecast (first 5) ===")
    for row in forecasts["memory"][:5]:
        print(row)