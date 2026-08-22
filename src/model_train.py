import itertools
import warnings
import pickle
import os

import pandas as pd
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.statespace.sarimax import SARIMAX
import mlflow
import mlflow.statsmodels

warnings.filterwarnings("ignore")  # SARIMA fitting throws many harmless convergence warnings

PROCESSED_CSV_PATH = "data/processed_metrics.csv"


def load_data():
    df = pd.read_csv(PROCESSED_CSV_PATH, index_col="_time", parse_dates=True)
    return df


def check_stationarity(series, name=""):
    result = adfuller(series.dropna())
    print(f"\n--- ADF Test: {name} ---")
    print(f"ADF Statistic: {result[0]:.4f}")
    print(f"p-value: {result[1]:.4f}")
    if result[1] < 0.05:
        print(f"=> {name} is likely STATIONARY (p < 0.05)")
    else:
        print(f"=> {name} is likely NOT stationary (p >= 0.05), differencing needed")


def grid_search_sarima(series, d, seasonal_period=12):
    """
    Try a range of (p,d,q)(P,D,Q,s) combinations and return the one
    with the lowest AIC score.
    """
    p_values = range(0, 3)
    q_values = range(0, 3)
    P_values = range(0, 2)
    D_values = range(0, 2)
    Q_values = range(0, 2)

    best_aic = float("inf")
    best_order = None
    best_seasonal_order = None
    best_model = None

    for p, q, P, D, Q in itertools.product(p_values, q_values, P_values, D_values, Q_values):
        order = (p, d, q)
        seasonal_order = (P, D, Q, seasonal_period)
        try:
            model = SARIMAX(
                series,
                order=order,
                seasonal_order=seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fitted = model.fit(disp=False)
            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best_order = order
                best_seasonal_order = seasonal_order
                best_model = fitted
        except Exception:
            # Some parameter combinations fail to converge -- skip them
            continue

    return best_model, best_order, best_seasonal_order, best_aic


def generate_forecast(model, steps=48):
    """Forecast a number of steps ahead. 48 steps at 5-min intervals = 4 hours."""
    forecast = model.get_forecast(steps=steps)
    predicted_mean = forecast.predicted_mean
    conf_int = forecast.conf_int()
    return predicted_mean, conf_int


def log_to_mlflow(model, order, seasonal_order, aic, metric_name, forecast_steps=48):
    with mlflow.start_run(run_name=f"{metric_name}_sarima"):
        # Log the parameters that define this model
        mlflow.log_param("metric", metric_name)
        mlflow.log_param("order_p", order[0])
        mlflow.log_param("order_d", order[1])
        mlflow.log_param("order_q", order[2])
        mlflow.log_param("seasonal_P", seasonal_order[0])
        mlflow.log_param("seasonal_D", seasonal_order[1])
        mlflow.log_param("seasonal_Q", seasonal_order[2])
        mlflow.log_param("seasonal_period", seasonal_order[3])

        # Log the model's fit quality
        mlflow.log_metric("aic", aic)

        # Log the fitted model itself as an MLflow artifact
        mlflow.statsmodels.log_model(model, name=f"{metric_name}_model")

        # Also save a plain pickle, useful for the inference script later
        model_path = f"models/{metric_name}_sarima.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        mlflow.log_artifact(model_path)

        print(f"Logged {metric_name} model to MLflow (AIC: {aic:.2f})")


if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)

    df = load_data()
    print("Loaded data shape:", df.shape)
    print(df.head())

    check_stationarity(df["usage_active"], name="CPU usage_active")
    check_stationarity(df["available_percent"], name="Memory available_percent")

    print("\n--- Grid searching CPU model (d=1) ---")
    cpu_model, cpu_order, cpu_seasonal_order, cpu_aic = grid_search_sarima(
        df["usage_active"], d=1
    )
    print(f"Best CPU order: {cpu_order}, seasonal: {cpu_seasonal_order}, AIC: {cpu_aic:.2f}")

    print("\n--- Grid searching Memory model (d=0) ---")
    mem_model, mem_order, mem_seasonal_order, mem_aic = grid_search_sarima(
        df["available_percent"], d=0
    )
    print(f"Best Memory order: {mem_order}, seasonal: {mem_seasonal_order}, AIC: {mem_aic:.2f}")

    print("\n--- Logging CPU model to MLflow ---")
    log_to_mlflow(cpu_model, cpu_order, cpu_seasonal_order, cpu_aic, "cpu")

    print("\n--- Logging Memory model to MLflow ---")
    log_to_mlflow(mem_model, mem_order, mem_seasonal_order, mem_aic, "memory")