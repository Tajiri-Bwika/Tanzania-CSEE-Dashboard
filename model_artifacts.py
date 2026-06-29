"""Load trained model metrics, metadata, predictions, and forecasts safely."""

from pathlib import Path

import pandas as pd
import streamlit as st


ARTIFACT_DIR = Path(__file__).resolve().parent / "model_artifacts"
TARGETS = ("gpa", "pass_rate")
METRICS_REQUIRED_COLUMNS = {
    "Target", "Model", "MAE", "RMSE", "R2", "MAPE", "Selected"
}
METADATA_REQUIRED_COLUMNS = {
    "target", "target_label", "best_model", "selection_reason", "test_year"
}


class ModelArtifactError(Exception):
    """Raised when required model artifacts are missing or unreadable."""


def _read_artifact_csv(file_path, label):
    """Read an artifact CSV and raise a concise domain-specific error."""
    try:
        return pd.read_csv(file_path)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise ModelArtifactError(
            f"Unable to read {label} file '{file_path.name}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _validate_columns(df, required_columns, label):
    """Validate columns required by dashboard artifact visualizations."""
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ModelArtifactError(
            f"{label} file is missing required columns: {', '.join(missing)}"
        )


@st.cache_data(show_spinner=False)
def load_model_artifacts(artifact_dir=ARTIFACT_DIR, strict=False):
    """Load model artifacts; return None on failure unless strict=True."""
    artifact_path = Path(artifact_dir)
    metrics_file = artifact_path / "model_metrics.csv"
    metadata_file = artifact_path / "model_metadata.csv"
    try:
        missing_required = [
            path.name for path in (metrics_file, metadata_file) if not path.exists()
        ]
        if missing_required:
            raise ModelArtifactError(
                "Required model artifact files are missing: "
                f"{', '.join(missing_required)}"
            )

        metrics_df = _read_artifact_csv(metrics_file, "model metrics")
        metadata_df = _read_artifact_csv(metadata_file, "model metadata")
        _validate_columns(metrics_df, METRICS_REQUIRED_COLUMNS, "Model metrics")
        _validate_columns(metadata_df, METADATA_REQUIRED_COLUMNS, "Model metadata")

        metadata = {
            row["target"]: {
                "target_label": row.get("target_label"),
                "best_model": row.get("best_model"),
                "selection_reason": row.get("selection_reason"),
                "test_year": row.get("test_year"),
            }
            for _, row in metadata_df.iterrows()
        }

        forecasts = {}
        predictions = {}
        for target in TARGETS:
            forecast_file = artifact_path / f"{target}_forecast.csv"
            predictions_file = artifact_path / f"{target}_predictions.csv"

            # Forecast/prediction files are optional at load time. Missing files
            # become empty frames so historical dashboard sections remain usable.
            forecasts[target] = (
                _read_artifact_csv(forecast_file, f"{target} forecast")
                if forecast_file.exists()
                else pd.DataFrame()
            )
            predictions[target] = (
                _read_artifact_csv(predictions_file, f"{target} predictions")
                if predictions_file.exists()
                else pd.DataFrame()
            )

        return {
            "metrics": metrics_df,
            "metadata": metadata,
            "forecasts": forecasts,
            "predictions": predictions,
        }
    except ModelArtifactError:
        if strict:
            raise
        return None
