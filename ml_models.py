"""Train, compare, forecast, and persist CSEE GPA and pass-rate models."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from metrics import weighted_rate

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover - handled at runtime for missing optional dependency
    XGBRegressor = None

try:
    import torch
    from torch import nn
    TORCH_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - handled at runtime
    torch = None
    nn = None
    TORCH_IMPORT_ERROR = str(exc)


RANDOM_STATE = 42
ARTIFACT_DIR = Path(__file__).resolve().parent / "model_artifacts"
VISUALIZATION_DIR = Path(__file__).resolve().parent / "model_visualizations"
TARGETS = {
    "gpa": {
        "label": "GPA",
        "lower_bound": 0.0,
        "upper_bound": 5.0,
        "lower_is_better": True,
    },
    "pass_rate": {
        "label": "Pass Rate",
        "lower_bound": 0.0,
        "upper_bound": 100.0,
        "lower_is_better": False,
    },
}

NUMERIC_FEATURES = [
    "year",
    "year_index",
    "lag1_gpa",
    "lag1_pass_rate",
    "lag1_sat",
    "lag1_division_0_rate",
    "lag1_division_1_rate",
    "lag1_attendance_rate",
    "lag2_gpa",
    "lag2_pass_rate",
]
FEATURES = NUMERIC_FEATURES + ["region"]
LSTM_SEQUENCE_FEATURES = [
    "year_index",
    "gpa",
    "pass_rate",
    "sat",
    "division_0_rate",
    "division_1_rate",
    "attendance_rate",
]


def _one_hot_encoder():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # Older scikit-learn compatibility.
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _preprocessor(scale_numeric=False):
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), NUMERIC_FEATURES),
            ("cat", _one_hot_encoder(), ["region"]),
        ],
        remainder="drop",
    )


def prepare_school_panel(school_df):
    """Build a clean school-year feature panel for model training."""
    required = {"school_id", "school_name", "region", "year", "gpa", "sat", "total_passed_candidates"}
    if school_df.empty or not required.issubset(school_df.columns):
        return pd.DataFrame()

    source = school_df.copy()
    source = source[
        source["region"].notna()
        & (source["region"].astype("string").str.strip().str.upper() != "UNKNOWN")
    ]
    source = source.dropna(subset=["school_id", "year", "gpa"])
    if source.empty:
        return pd.DataFrame()

    panel = (
        source
        .groupby(["school_id", "school_name", "region", "year"], as_index=False)
        .agg({
            "gpa": "mean",
            "sat": "sum",
            "regist": "sum",
            "total_passed_candidates": "sum",
            "division_1": "sum",
            "division_0": "sum",
        })
    )

    panel["pass_rate"] = panel.apply(
        lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
        axis=1,
    )
    panel["division_0_rate"] = panel.apply(
        lambda row: weighted_rate(row["division_0"], row["sat"]),
        axis=1,
    )
    panel["division_1_rate"] = panel.apply(
        lambda row: weighted_rate(row["division_1"], row["sat"]),
        axis=1,
    )
    panel["attendance_rate"] = panel.apply(
        lambda row: weighted_rate(row["sat"], row["regist"]),
        axis=1,
    )

    panel = panel.sort_values(["school_id", "year"]).reset_index(drop=True)
    min_year = int(panel["year"].min())
    panel["year_index"] = panel["year"] - min_year

    lag_cols = ["gpa", "pass_rate", "sat", "division_0_rate", "division_1_rate", "attendance_rate"]
    for col in lag_cols:
        panel[f"lag1_{col}"] = panel.groupby("school_id")[col].shift(1)

    panel["lag2_gpa"] = panel.groupby("school_id")["gpa"].shift(2)
    panel["lag2_pass_rate"] = panel.groupby("school_id")["pass_rate"].shift(2)
    panel[["pass_rate", "division_0_rate", "division_1_rate", "attendance_rate"]] = (
        panel[["pass_rate", "division_0_rate", "division_1_rate", "attendance_rate"]].fillna(0)
    )
    return panel


def supervised_dataset(panel, target):
    """Return lag-complete feature rows and a numeric target series."""
    if panel.empty or target not in panel.columns:
        return pd.DataFrame(), pd.Series(dtype=float)

    data = panel.dropna(subset=["lag1_gpa", "lag1_pass_rate", target]).copy()
    data["lag2_gpa"] = data["lag2_gpa"].fillna(data["lag1_gpa"])
    data["lag2_pass_rate"] = data["lag2_pass_rate"].fillna(data["lag1_pass_rate"])
    data[NUMERIC_FEATURES] = data[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan)
    data[NUMERIC_FEATURES] = data[NUMERIC_FEATURES].fillna(data[NUMERIC_FEATURES].median(numeric_only=True))
    data["region"] = data["region"].fillna("Unknown")
    return data, data[target].astype(float)


def regression_metrics(y_true, y_pred):
    """Calculate MAE, RMSE, R2, and MAPE for finite predictions."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    if len(y_true) == 0:
        return {"MAE": np.nan, "RMSE": np.nan, "R2": np.nan, "MAPE": np.nan}

    denominator = np.where(np.abs(y_true) < 1e-9, np.nan, np.abs(y_true))
    mape = np.nanmean(np.abs((y_true - y_pred) / denominator)) * 100
    if np.isnan(mape):
        mape = 0.0

    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "R2": r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan,
        "MAPE": mape,
    }


class TorchLSTMRegressor:
    """Small LSTM wrapper for short annual school sequences.

    Annual school histories remain short compared with typical sequence-model
    datasets, so the LSTM is trained conservatively and evaluated honestly
    instead of being tuned to look better.
    """

    def __init__(self, lookback=3, epochs=18, hidden_size=12, learning_rate=0.015):
        self.lookback = lookback
        self.epochs = epochs
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.model = None
        self.x_mean = None
        self.x_std = None
        self.y_mean = None
        self.y_std = None
        self.available = torch is not None

    def fit(self, x_train, y_train):
        if not self.available or len(x_train) == 0:
            return self

        torch.manual_seed(RANDOM_STATE)
        x_train = np.asarray(x_train, dtype=np.float32)
        y_train = np.asarray(y_train, dtype=np.float32).reshape(-1, 1)

        self.x_mean = x_train.mean(axis=(0, 1), keepdims=True)
        self.x_std = x_train.std(axis=(0, 1), keepdims=True) + 1e-6
        self.y_mean = y_train.mean(axis=0, keepdims=True)
        self.y_std = y_train.std(axis=0, keepdims=True) + 1e-6

        x_scaled = (x_train - self.x_mean) / self.x_std
        y_scaled = (y_train - self.y_mean) / self.y_std

        class _Model(nn.Module):
            def __init__(self, input_size, hidden_size):
                super().__init__()
                self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
                self.head = nn.Sequential(
                    nn.Linear(hidden_size, 8),
                    nn.ReLU(),
                    nn.Linear(8, 1),
                )

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.head(out[:, -1, :])

        self.model = _Model(x_scaled.shape[-1], self.hidden_size)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        loss_fn = nn.MSELoss()
        x_tensor = torch.tensor(x_scaled, dtype=torch.float32)
        y_tensor = torch.tensor(y_scaled, dtype=torch.float32)

        self.model.train()
        for _ in range(self.epochs):
            optimizer.zero_grad()
            loss = loss_fn(self.model(x_tensor), y_tensor)
            loss.backward()
            optimizer.step()
        return self

    def predict(self, x):
        if self.model is None:
            return np.array([])
        x = np.asarray(x, dtype=np.float32)
        x_scaled = (x - self.x_mean) / self.x_std
        self.model.eval()
        with torch.no_grad():
            pred_scaled = self.model(torch.tensor(x_scaled, dtype=torch.float32)).numpy()
        return (pred_scaled * self.y_std + self.y_mean).reshape(-1)


def lstm_sequences(panel, target, lookback=3):
    """Build fixed-length annual sequences for optional LSTM evaluation."""
    if torch is None or panel.empty:
        return np.empty((0, lookback, len(LSTM_SEQUENCE_FEATURES))), np.array([]), np.array([])

    x_rows, y_rows, years = [], [], []
    for _, group in panel.dropna(subset=[target]).groupby("school_id"):
        group = group.sort_values("year").reset_index(drop=True)
        if len(group) <= lookback:
            continue
        seq_data = group[LSTM_SEQUENCE_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0).to_numpy(dtype=float)
        target_values = group[target].to_numpy(dtype=float)
        year_values = group["year"].to_numpy(dtype=int)
        for idx in range(lookback, len(group)):
            x_rows.append(seq_data[idx - lookback:idx])
            y_rows.append(target_values[idx])
            years.append(year_values[idx])
    return np.asarray(x_rows), np.asarray(y_rows), np.asarray(years)


def train_standard_models(train_df, test_df, target):
    """Train and evaluate the non-sequence candidate models."""
    x_train = train_df[FEATURES]
    y_train = train_df[target]
    x_test = test_df[FEATURES]
    y_test = test_df[target]

    specs = [
        (
            "Baseline Linear Regression",
            "Existing baseline: linear regression using engineered lag and region features.",
            Pipeline([
                ("preprocess", _preprocessor(scale_numeric=True)),
                ("model", LinearRegression()),
            ]),
        ),
        (
            "Random Forest",
            "Tree ensemble that captures non-linear relationships and interactions.",
            Pipeline([
                ("preprocess", _preprocessor(scale_numeric=False)),
                ("model", RandomForestRegressor(
                    n_estimators=140,
                    max_depth=9,
                    min_samples_leaf=4,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                )),
            ]),
        ),
    ]

    if XGBRegressor is not None:
        specs.append(
            (
                "XGBoost",
                "Gradient-boosted decision trees with regularisation.",
                Pipeline([
                    ("preprocess", _preprocessor(scale_numeric=False)),
                    ("model", XGBRegressor(
                        objective="reg:squarederror",
                        n_estimators=120,
                        max_depth=3,
                        learning_rate=0.045,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        reg_lambda=1.0,
                        random_state=RANDOM_STATE,
                        n_jobs=1,
                    )),
                ]),
            )
        )

    results = []
    fitted = {}
    prediction_frames = []
    for name, note, model in specs:
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        metrics = regression_metrics(y_test, predictions)
        results.append({
            "Model": name,
            "MAE": metrics["MAE"],
            "RMSE": metrics["RMSE"],
            "R2": metrics["R2"],
            "MAPE": metrics["MAPE"],
            "Notes": note,
            "Status": "Trained",
        })
        fitted[name] = model
        prediction_frames.append(pd.DataFrame({
            "Target": TARGETS[target]["label"],
            "Model": name,
            "Year": test_df["year"].to_numpy(),
            "Actual": y_test.to_numpy(dtype=float),
            "Predicted": np.asarray(predictions, dtype=float),
        }))

    predictions_df = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    return results, fitted, predictions_df


def train_lstm_model(panel, target, test_year):
    """Train and evaluate the optional LSTM on the same holdout year."""
    lookback = 3
    x_seq, y_seq, years = lstm_sequences(panel, target, lookback=lookback)
    if torch is None:
        return {
            "Model": "LSTM",
            "MAE": np.nan,
            "RMSE": np.nan,
            "R2": np.nan,
            "MAPE": np.nan,
            "Notes": f"PyTorch could not be imported, so LSTM could not be trained. {TORCH_IMPORT_ERROR or ''}".strip(),
            "Status": "Unavailable",
        }, None, pd.DataFrame()

    train_mask = years < test_year
    test_mask = years == test_year
    if train_mask.sum() < 5 or test_mask.sum() < 2:
        return {
            "Model": "LSTM",
            "MAE": np.nan,
            "RMSE": np.nan,
            "R2": np.nan,
            "MAPE": np.nan,
            "Notes": "Too few annual sequences for a defensible LSTM train/test split.",
            "Status": "Insufficient sequence data",
        }, None, pd.DataFrame()

    train_indices = np.flatnonzero(train_mask)
    if len(train_indices) > 15000:
        rng = np.random.default_rng(RANDOM_STATE)
        train_indices = np.sort(rng.choice(train_indices, size=15000, replace=False))

    model = TorchLSTMRegressor(lookback=lookback)
    model.fit(x_seq[train_indices], y_seq[train_indices])
    predictions = model.predict(x_seq[test_mask])
    metrics = regression_metrics(y_seq[test_mask], predictions)
    predictions_df = pd.DataFrame({
        "Target": TARGETS[target]["label"],
        "Model": "LSTM",
        "Year": years[test_mask],
        "Actual": y_seq[test_mask],
        "Predicted": predictions,
    })
    return {
        "Model": "LSTM",
        "MAE": metrics["MAE"],
        "RMSE": metrics["RMSE"],
        "R2": metrics["R2"],
        "MAPE": metrics["MAPE"],
        "Notes": "Sequence model trained on 3-year windows; constrained by short annual history.",
        "Status": "Trained",
    }, model, predictions_df


def select_best_model(metrics_df):
    """Select the lowest-error model with a documented simplicity tie-break."""
    trained = metrics_df[metrics_df["Status"] == "Trained"].dropna(subset=["RMSE", "MAE", "MAPE"]).copy()
    if trained.empty:
        return None, "No model had enough valid predictions for selection."

    trained = trained.sort_values(["RMSE", "MAE", "MAPE"]).reset_index(drop=True)
    rmse_winner = trained.iloc[0]
    close = trained[trained["RMSE"] <= rmse_winner["RMSE"] * 1.03].copy()
    simplicity = {
        "Baseline Linear Regression": 1,
        "Random Forest": 2,
        "XGBoost": 3,
        "LSTM": 4,
    }
    close["simplicity"] = close["Model"].map(simplicity).fillna(99)
    selected = close.sort_values(["simplicity", "MAE", "MAPE"]).iloc[0]

    if selected["Model"] == rmse_winner["Model"]:
        reason = (
            f"{selected['Model']} was selected because it achieved the lowest RMSE "
            f"({selected['RMSE']:.4f}), with MAE {selected['MAE']:.4f} and MAPE {selected['MAPE']:.2f}%."
        )
    else:
        reason = (
            f"{selected['Model']} was selected because its RMSE ({selected['RMSE']:.4f}) was within 3% of "
            f"the lowest RMSE ({rmse_winner['RMSE']:.4f} from {rmse_winner['Model']}), while being simpler "
            "and easier to defend academically."
        )
    return selected["Model"], reason


def train_target_suite(panel, target):
    """Train all candidate models for one prediction target."""
    data, _ = supervised_dataset(panel, target)
    if data.empty or data["year"].nunique() < 2:
        empty = pd.DataFrame(columns=["Model", "MAE", "RMSE", "R2", "MAPE", "Notes", "Status"])
        return {
            "metrics": empty,
            "predictions": pd.DataFrame(),
            "models": {},
            "best_model": None,
            "selection_reason": "Not enough supervised rows to train models.",
            "test_year": None,
            "target": target,
        }

    test_year = int(data["year"].max())
    train_df = data[data["year"] < test_year].copy()
    test_df = data[data["year"] == test_year].copy()
    if train_df.empty or test_df.empty:
        test_year = int(sorted(data["year"].unique())[-2])
        train_df = data[data["year"] < test_year].copy()
        test_df = data[data["year"] == test_year].copy()

    results, fitted, standard_predictions = train_standard_models(train_df, test_df, target)
    lstm_result, lstm_model, lstm_predictions = train_lstm_model(panel, target, test_year)
    results.append(lstm_result)
    if lstm_model is not None:
        fitted["LSTM"] = lstm_model

    metrics_df = pd.DataFrame(results)
    prediction_frames = [
        frame for frame in [standard_predictions, lstm_predictions]
        if frame is not None and not frame.empty
    ]
    predictions_df = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    best_model, reason = select_best_model(metrics_df)
    return {
        "metrics": metrics_df,
        "predictions": predictions_df,
        "models": fitted,
        "best_model": best_model,
        "selection_reason": reason,
        "test_year": test_year,
        "target": target,
    }


@st.cache_resource(show_spinner=False)
def train_model_suite(school_df):
    """Train cached GPA and pass-rate suites from school-level data."""
    panel = prepare_school_panel(school_df)
    return {
        "panel": panel,
        "targets": {
            target: train_target_suite(panel, target)
            for target in TARGETS
        },
        "min_year": int(panel["year"].min()) if not panel.empty else None,
        "max_year": int(panel["year"].max()) if not panel.empty else None,
    }


def _latest_feature_row(history, target_year, min_year):
    history = history.sort_values("year").copy()
    latest = history.iloc[-1]
    prev = history.iloc[-2] if len(history) >= 2 else latest
    return {
        "year": target_year,
        "year_index": target_year - min_year,
        "region": latest["region"],
        "lag1_gpa": latest["gpa"],
        "lag1_pass_rate": latest["pass_rate"],
        "lag1_sat": latest["sat"],
        "lag1_division_0_rate": latest["division_0_rate"],
        "lag1_division_1_rate": latest["division_1_rate"],
        "lag1_attendance_rate": latest["attendance_rate"],
        "lag2_gpa": prev["gpa"],
        "lag2_pass_rate": prev["pass_rate"],
    }


def _predict_next_value(target_suite, target, history, target_year, min_year):
    best_model = target_suite["best_model"]
    if not best_model or best_model not in target_suite["models"]:
        return np.nan

    model = target_suite["models"][best_model]
    if best_model == "LSTM":
        if len(history) < model.lookback:
            return np.nan
        seq = (
            history.sort_values("year")
            .tail(model.lookback)[LSTM_SEQUENCE_FEATURES]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
            .to_numpy(dtype=float)
            .reshape(1, model.lookback, len(LSTM_SEQUENCE_FEATURES))
        )
        pred = model.predict(seq)[0]
    else:
        feature_row = pd.DataFrame([_latest_feature_row(history, target_year, min_year)])
        pred = model.predict(feature_row[FEATURES])[0]

    config = TARGETS[target]
    return float(np.clip(pred, config["lower_bound"], config["upper_bound"]))


def forecast_regions_with_best_model(suite, source_df, target="gpa", periods=2):
    """Generate bounded regional forecasts from the selected target model."""
    panel = prepare_school_panel(source_df)
    if panel.empty or target not in suite["targets"]:
        return pd.DataFrame(), pd.DataFrame(), None

    target_suite = suite["targets"][target]
    best_model = target_suite.get("best_model")
    if not best_model:
        return pd.DataFrame(), pd.DataFrame(), None

    min_year = suite["min_year"] if suite["min_year"] is not None else int(panel["year"].min())

    if target == "pass_rate":
        history = (
            panel.groupby(["year", "region"], as_index=False)
            .agg({"total_passed_candidates": "sum", "sat": "sum"})
        )
        history[target] = history.apply(
            lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
            axis=1,
        )
        history = history[["year", "region", target]].fillna(0)
    else:
        history = (
            panel.groupby(["year", "region"], as_index=False)[target]
            .mean()
            .sort_values(["region", "year"])
        )

    forecasts = []
    forecast_base_year = int(panel["year"].max())
    running_histories = {
        school_id: group.sort_values("year").copy()
        for school_id, group in panel.groupby("school_id")
        if not group.empty and int(group["year"].max()) == forecast_base_year
    }

    model = target_suite["models"].get(best_model)
    config = TARGETS[target]
    for step in range(1, periods + 1):
        target_year = forecast_base_year + step
        school_ids = []
        feature_rows = []
        sequence_rows = []

        for school_id, running in running_histories.items():
            if best_model == "LSTM":
                if len(running) < model.lookback:
                    continue
                sequence = (
                    running.sort_values("year")
                    .tail(model.lookback)[LSTM_SEQUENCE_FEATURES]
                    .replace([np.inf, -np.inf], np.nan)
                    .fillna(0)
                    .to_numpy(dtype=float)
                )
                sequence_rows.append(sequence)
            else:
                feature_rows.append(_latest_feature_row(running, target_year, min_year))
            school_ids.append(school_id)

        if not school_ids:
            continue

        if best_model == "LSTM":
            raw_predictions = model.predict(np.asarray(sequence_rows, dtype=float))
        else:
            feature_df = pd.DataFrame(feature_rows)
            raw_predictions = model.predict(feature_df[FEATURES])

        predictions = np.clip(
            np.asarray(raw_predictions, dtype=float),
            config["lower_bound"],
            config["upper_bound"],
        )

        for school_id, pred in zip(school_ids, predictions):
            if not np.isfinite(pred):
                continue

            running = running_histories[school_id]
            last = running.iloc[-1].copy()
            last["year"] = target_year
            last["year_index"] = target_year - min_year
            last[target] = float(pred)
            running_histories[school_id] = pd.concat(
                [running, pd.DataFrame([last])],
                ignore_index=True,
            )

            forecasts.append({
                "school_id": last["school_id"],
                "school_name": last["school_name"],
                "region": last["region"],
                "year": target_year,
                target: float(pred),
                "sat_weight": last["sat"],
                "model": best_model,
            })

    forecast_df = pd.DataFrame(forecasts)
    if forecast_df.empty:
        return history, forecast_df, best_model

    if target == "pass_rate":
        regional_forecast = (
            forecast_df.groupby(["year", "region"], as_index=False)
            .apply(lambda g: pd.Series({
                target: np.average(g[target], weights=np.maximum(g["sat_weight"], 1))
            }), include_groups=False)
            .reset_index(drop=True)
        )
    else:
        regional_forecast = (
            forecast_df.groupby(["year", "region"], as_index=False)[target]
            .mean()
        )
    regional_forecast["model"] = best_model
    return history.sort_values(["region", "year"]), regional_forecast.sort_values(["region", "year"]), best_model


def model_metrics_table(suite):
    """Combine target evaluation results into one dashboard-ready table."""
    tables = []
    for target, target_suite in suite["targets"].items():
        df = target_suite["metrics"].copy()
        if df.empty:
            continue
        df.insert(0, "Target", TARGETS[target]["label"])
        df["Selected"] = df["Model"] == target_suite["best_model"]
        tables.append(df)
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, ignore_index=True)


def write_model_report(suite, school_df, output_path="model_comparison_report.txt"):
    """Write a human-readable model comparison and forecast report."""
    path = Path(output_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    lines = [
        "NECTA Dashboard ML Model Comparison Report",
        "=" * 48,
        "",
        "Baseline model: Linear Regression using engineered lag features and region encoding.",
        "Added models: Random Forest, XGBoost, LSTM.",
        "Evaluation metrics: MAE, RMSE, R2, MAPE.",
        "Selection rule: lowest RMSE, with MAE/MAPE checks and simpler model preference if RMSE is within 3%.",
        "",
    ]

    metrics_df = model_metrics_table(suite)
    if not metrics_df.empty:
        display_cols = ["Target", "Model", "MAE", "RMSE", "R2", "MAPE", "Status", "Selected"]
        lines.append("Model comparison and evaluation metrics")
        lines.append("-" * 48)
        lines.append(metrics_df[display_cols].to_string(index=False))
        lines.append("")

    for target, target_suite in suite["targets"].items():
        lines.append(f"Selected best model for {TARGETS[target]['label']}: {target_suite['best_model']}")
        lines.append(target_suite["selection_reason"])
        history, forecast, best_model = forecast_regions_with_best_model(suite, school_df, target=target, periods=2)
        if not forecast.empty:
            lines.append("")
            lines.append(f"Best-model forecast values for {TARGETS[target]['label']} ({best_model})")
            lines.append(forecast[["region", "year", target]].to_string(index=False))
        else:
            lines.append("No forecast values were generated for this target.")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_model_artifacts(suite, school_df, artifact_dir=ARTIFACT_DIR):
    """Persist metrics, metadata, predictions, and regional forecasts."""
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)

    metrics_df = model_metrics_table(suite)
    metrics_file = artifact_path / "model_metrics.csv"
    metrics_df.to_csv(metrics_file, index=False)

    metadata_rows = []
    forecast_files = {}
    prediction_files = {}
    for target, target_suite in suite["targets"].items():
        metadata_rows.append({
            "target": target,
            "target_label": TARGETS[target]["label"],
            "best_model": target_suite.get("best_model"),
            "selection_reason": target_suite.get("selection_reason"),
            "test_year": target_suite.get("test_year"),
        })
        _, forecast_df, best_model = forecast_regions_with_best_model(suite, school_df, target=target, periods=2)
        forecast_file = artifact_path / f"{target}_forecast.csv"
        forecast_df.to_csv(forecast_file, index=False)
        forecast_files[target] = forecast_file

        predictions_df = target_suite.get("predictions", pd.DataFrame())
        predictions_file = artifact_path / f"{target}_predictions.csv"
        predictions_df.to_csv(predictions_file, index=False)
        prediction_files[target] = predictions_file

    metadata_file = artifact_path / "model_metadata.csv"
    pd.DataFrame(metadata_rows).to_csv(metadata_file, index=False)
    return {
        "metrics": metrics_file,
        "metadata": metadata_file,
        "forecasts": forecast_files,
        "predictions": prediction_files,
    }


def load_model_artifacts(artifact_dir=ARTIFACT_DIR):
    """Load saved outputs through the dashboard's validated artifact loader."""
    from model_artifacts import load_model_artifacts as load_saved_artifacts

    return load_saved_artifacts(artifact_dir)


def generate_model_visualizations(suite, school_df, output_dir=VISUALIZATION_DIR):
    """Generate documentation-ready ML plots without adding them to Streamlit."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    colors = {
        "Baseline Linear Regression": "#1E40AF",
        "Random Forest": "#0F766E",
        "XGBoost": "#F59E0B",
        "LSTM": "#DC2626",
    }
    short_names = {
        "Baseline Linear Regression": "Baseline\nLinear Regression",
        "Random Forest": "Random Forest",
        "XGBoost": "XGBoost",
        "LSTM": "LSTM",
    }
    generated = []

    def save(fig, filename):
        destination = output_path / filename
        fig.savefig(destination, dpi=220, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        generated.append(destination)

    metrics_df = model_metrics_table(suite)
    trained_metrics = metrics_df[metrics_df["Status"] == "Trained"].copy()

    for target_key, config in TARGETS.items():
        target_label = config["label"]
        target_metrics = trained_metrics[trained_metrics["Target"] == target_label].copy()
        target_suite = suite["targets"][target_key]
        best_model = target_suite.get("best_model")

        if not target_metrics.empty:
            fig, axes = plt.subplots(2, 2, figsize=(13, 9))
            for ax, metric in zip(axes.flat, ["MAE", "RMSE", "R2", "MAPE"]):
                plot_df = target_metrics.sort_values(metric, ascending=metric != "R2")
                bar_colors = [
                    "#16A34A" if model == best_model else colors.get(model, "#64748B")
                    for model in plot_df["Model"]
                ]
                bars = ax.bar(
                    [short_names.get(model, model) for model in plot_df["Model"]],
                    plot_df[metric],
                    color=bar_colors,
                    edgecolor="white",
                    linewidth=0.8,
                )
                ax.set_title(f"{metric} Comparison", fontweight="bold")
                ax.set_ylabel("Percentage" if metric == "MAPE" else metric)
                ax.grid(axis="y", alpha=0.25)
                ax.tick_params(axis="x", labelsize=9)
                for bar, value in zip(bars, plot_df[metric]):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(),
                        f"{value:.3f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )
            fig.suptitle(
                f"{target_label} Model Evaluation Metrics\nGreen indicates the selected model: {best_model}",
                fontsize=16,
                fontweight="bold",
            )
            fig.tight_layout(rect=(0, 0, 1, 0.93))
            save(fig, f"{target_key}_01_evaluation_metrics.png")

        predictions = target_suite.get("predictions", pd.DataFrame()).copy()
        if not predictions.empty:
            predictions["Residual"] = predictions["Actual"] - predictions["Predicted"]
            models = predictions["Model"].drop_duplicates().tolist()
            rows = 2
            cols = 2

            fig, axes = plt.subplots(rows, cols, figsize=(13, 10))
            for ax, model_name in zip(axes.flat, models):
                model_df = predictions[predictions["Model"] == model_name]
                model_color = colors.get(model_name, "#64748B")
                ax.scatter(
                    model_df["Actual"],
                    model_df["Predicted"],
                    alpha=0.55,
                    s=28,
                    color=model_color,
                    edgecolors="white",
                    linewidths=0.35,
                )
                lower = min(model_df["Actual"].min(), model_df["Predicted"].min())
                upper = max(model_df["Actual"].max(), model_df["Predicted"].max())
                ax.plot([lower, upper], [lower, upper], linestyle="--", color="#0F172A", linewidth=1.2)
                ax.set_title(model_name, fontweight="bold")
                ax.set_xlabel("Actual")
                ax.set_ylabel("Predicted")
                ax.grid(alpha=0.22)
            for ax in axes.flat[len(models):]:
                ax.axis("off")
            fig.suptitle(f"{target_label}: Actual vs Predicted on Holdout Data", fontsize=16, fontweight="bold")
            fig.tight_layout(rect=(0, 0, 1, 0.95))
            save(fig, f"{target_key}_02_actual_vs_predicted.png")

            fig, axes = plt.subplots(rows, cols, figsize=(13, 10))
            for ax, model_name in zip(axes.flat, models):
                model_df = predictions[predictions["Model"] == model_name]
                model_color = colors.get(model_name, "#64748B")
                ax.scatter(
                    model_df["Predicted"],
                    model_df["Residual"],
                    alpha=0.55,
                    s=28,
                    color=model_color,
                    edgecolors="white",
                    linewidths=0.35,
                )
                ax.axhline(0, linestyle="--", color="#0F172A", linewidth=1.2)
                ax.set_title(model_name, fontweight="bold")
                ax.set_xlabel("Predicted")
                ax.set_ylabel("Residual (Actual - Predicted)")
                ax.grid(alpha=0.22)
            for ax in axes.flat[len(models):]:
                ax.axis("off")
            fig.suptitle(f"{target_label}: Residual Diagnostics", fontsize=16, fontweight="bold")
            fig.tight_layout(rect=(0, 0, 1, 0.95))
            save(fig, f"{target_key}_03_residual_diagnostics.png")

            fig, axes = plt.subplots(rows, cols, figsize=(13, 10))
            for ax, model_name in zip(axes.flat, models):
                model_df = predictions[predictions["Model"] == model_name]
                model_color = colors.get(model_name, "#64748B")
                ax.hist(
                    model_df["Residual"],
                    bins=20,
                    color=model_color,
                    alpha=0.82,
                    edgecolor="white",
                )
                ax.axvline(0, linestyle="--", color="#0F172A", linewidth=1.2)
                ax.set_title(model_name, fontweight="bold")
                ax.set_xlabel("Residual")
                ax.set_ylabel("Frequency")
                ax.grid(axis="y", alpha=0.22)
            for ax in axes.flat[len(models):]:
                ax.axis("off")
            fig.suptitle(f"{target_label}: Residual Distributions", fontsize=16, fontweight="bold")
            fig.tight_layout(rect=(0, 0, 1, 0.95))
            save(fig, f"{target_key}_04_residual_distributions.png")

        history, forecast, selected_model = forecast_regions_with_best_model(
            suite,
            school_df,
            target=target_key,
            periods=2,
        )
        if not history.empty:
            fig, ax = plt.subplots(figsize=(13, 7))
            regions = sorted(history["region"].dropna().unique())
            palette = plt.cm.Set2(np.linspace(0, 1, max(len(regions), 1)))
            for region, color in zip(regions, palette):
                region_history = history[history["region"] == region].sort_values("year")
                ax.plot(
                    region_history["year"],
                    region_history[target_key],
                    marker="o",
                    linewidth=2,
                    color=color,
                    label=f"{region} historical",
                )
                region_forecast = forecast[forecast["region"] == region].sort_values("year")
                if not region_forecast.empty:
                    bridge = pd.concat(
                        [region_history[["year", target_key]].tail(1), region_forecast[["year", target_key]]],
                        ignore_index=True,
                    )
                    ax.plot(
                        bridge["year"],
                        bridge[target_key],
                        marker="o",
                        linestyle="--",
                        linewidth=2.3,
                        color=color,
                        label=f"{region} forecast",
                    )
            ax.set_title(
                f"{target_label}: Historical Performance and Two-Year Forecast\nSelected model: {selected_model}",
                fontsize=15,
                fontweight="bold",
            )
            ax.set_xlabel("Year")
            ax.set_ylabel(target_label)
            ax.grid(alpha=0.25)
            ax.legend(ncol=2, fontsize=9, frameon=False)
            if target_key == "gpa":
                ax.set_ylim(0, 5)
            else:
                ax.set_ylim(0, 100)
            fig.tight_layout()
            save(fig, f"{target_key}_05_selected_model_forecast.png")

    if not trained_metrics.empty:
        fig, axes = plt.subplots(1, 2, figsize=(15, 7))
        selected_lookup = {
            target_label: suite["targets"][target_key]["best_model"]
            for target_key, target_label in ((key, value["label"]) for key, value in TARGETS.items())
        }
        for ax, target_label in zip(axes, ["GPA", "Pass Rate"]):
            summary = (
                trained_metrics[trained_metrics["Target"] == target_label]
                .sort_values("RMSE", ascending=True)
            )
            bar_colors = [
                "#16A34A" if model == selected_lookup.get(target_label) else colors.get(model, "#64748B")
                for model in summary["Model"]
            ]
            bars = ax.barh(summary["Model"], summary["RMSE"], color=bar_colors)
            ax.invert_yaxis()
            ax.set_title(f"{target_label} RMSE Ranking", fontweight="bold")
            ax.set_xlabel("RMSE (lower is better)")
            ax.grid(axis="x", alpha=0.25)
            for bar, value in zip(bars, summary["RMSE"]):
                ax.text(value, bar.get_y() + bar.get_height() / 2, f" {value:.3f}", va="center", fontsize=9)
        fig.suptitle(
            "RMSE Model Ranking by Prediction Target\nGreen indicates the selected model",
            fontsize=16,
            fontweight="bold",
        )
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        save(fig, "00_rmse_model_ranking.png")

    return generated


if __name__ == "__main__":
    from data_loader import load_data

    school_data, _ = load_data()
    model_suite = train_model_suite(school_data)
    report_path = write_model_report(model_suite, school_data)
    write_model_artifacts(model_suite, school_data)
    visualization_paths = generate_model_visualizations(model_suite, school_data)
    print(f"Wrote {report_path}")
    print(f"Wrote {len(visualization_paths)} visualizations to {VISUALIZATION_DIR}")
