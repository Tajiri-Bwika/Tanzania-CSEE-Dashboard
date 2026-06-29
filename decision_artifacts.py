"""Load and validate offline decision-support artifacts for Streamlit pages."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from decision_config import (
    DECISION_ARTIFACT_DIR,
    INTERVENTION_FILE,
    MANIFEST_FILE,
    PRIORITY_FILES,
    RISK_FILES,
)


REQUIRED_COLUMNS = {
    "school_priority": {
        "priority_rank",
        "school_id",
        "school_name",
        "region",
        "priority_score",
        "priority_category",
    },
    "regional_priority": {
        "priority_rank",
        "region",
        "priority_score",
        "priority_category",
    },
    "school_risk": {
        "school_id",
        "school_name",
        "region",
        "risk_score",
        "risk_level",
    },
    "regional_risk": {
        "risk_rank",
        "region",
        "risk_score",
        "risk_level",
    },
    "interventions": {
        "priority_rank",
        "school_id",
        "school_name",
        "region",
        "problem_detected",
        "recommended_intervention",
        "expected_improvement_range",
        "assumption_basis",
        "data_origin",
        "scenario_origin",
    },
}


class DecisionArtifactError(Exception):
    """Raised when required decision artifacts are missing or invalid."""


def _read_csv(file_path, label):
    try:
        return pd.read_csv(file_path, low_memory=False)
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        ValueError,
    ) as exc:
        raise DecisionArtifactError(
            f"Unable to read {label} file '{file_path.name}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _validate_columns(df, required_columns, label):
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise DecisionArtifactError(
            f"{label} file is missing required columns: {', '.join(missing)}"
        )


@st.cache_data(show_spinner=False)
def load_decision_artifacts(artifact_dir=DECISION_ARTIFACT_DIR, strict=False):
    """Load precomputed decision artifacts without generating or training models."""
    artifact_path = Path(artifact_dir)
    files = {
        "school_priority": artifact_path / PRIORITY_FILES["school_priority"],
        "regional_priority": artifact_path / PRIORITY_FILES["regional_priority"],
        "school_risk": artifact_path / RISK_FILES["school_risk"],
        "regional_risk": artifact_path / RISK_FILES["regional_risk"],
        "interventions": artifact_path / INTERVENTION_FILE,
    }
    manifest_file = artifact_path / MANIFEST_FILE

    try:
        missing = [
            path.name
            for path in [*files.values(), manifest_file]
            if not path.exists()
        ]
        if missing:
            raise DecisionArtifactError(
                f"Required decision artifact files are missing: {', '.join(missing)}"
            )

        artifacts = {}
        for key, path in files.items():
            artifacts[key] = _read_csv(path, key.replace("_", " "))
            _validate_columns(
                artifacts[key],
                REQUIRED_COLUMNS[key],
                key.replace("_", " ").title(),
            )

        try:
            with manifest_file.open("r", encoding="utf-8") as file:
                manifest = json.load(file)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DecisionArtifactError(
                f"Unable to read decision manifest '{manifest_file.name}': "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if not manifest.get("decision_engine_version"):
            raise DecisionArtifactError(
                "Decision manifest is missing decision_engine_version."
            )

        artifacts["manifest"] = manifest
        return artifacts
    except DecisionArtifactError:
        if strict:
            raise
        return None
