"""Load validated precomputed 2032 policy-planning artifacts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from policy_config import POLICY_ARTIFACT_DIR, POLICY_FILES


REQUIRED_COLUMNS = {
    "summary": {
        "scenario_id",
        "scenario_name",
        "growth_pct",
        "projected_candidates",
        "high_risk_regions",
        "school_rank_increases",
        "data_origin",
        "scenario_type",
    },
    "regions": {
        "scenario_id",
        "region",
        "current_candidates",
        "projected_candidates",
        "growth_pct",
        "demand_pressure_index",
        "future_priority_rank",
        "data_origin",
        "scenario_type",
    },
    "schools": {
        "scenario_id",
        "school_id",
        "school_name",
        "region",
        "current_candidates",
        "projected_candidates",
        "growth_pct",
        "demand_pressure_index",
        "future_priority_rank",
        "data_origin",
        "scenario_type",
    },
    "priority_shift": {
        "scenario_id",
        "entity_type",
        "school_name",
        "region",
        "priority_rank",
        "future_priority_rank",
        "rank_change",
        "future_priority_score",
        "data_origin",
        "scenario_type",
    },
}


class PolicyArtifactError(Exception):
    """Raised when policy scenario files are missing, malformed, or unsafe."""


def _read_csv(path, label):
    try:
        return pd.read_csv(path, low_memory=False)
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        ValueError,
    ) as exc:
        raise PolicyArtifactError(
            f"Unable to read {label} file '{path.name}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc


@st.cache_data(show_spinner=False)
def load_policy_artifacts(artifact_dir=POLICY_ARTIFACT_DIR, strict=False):
    """Load policy files without performing simulation during page imports."""
    artifact_path = Path(artifact_dir)
    try:
        missing = [
            filename
            for filename in POLICY_FILES.values()
            if not (artifact_path / filename).exists()
        ]
        if missing:
            raise PolicyArtifactError(
                f"Required policy artifact files are missing: {', '.join(missing)}"
            )

        outputs = {}
        for key, filename in POLICY_FILES.items():
            dataframe = _read_csv(artifact_path / filename, key)
            missing_columns = sorted(REQUIRED_COLUMNS[key] - set(dataframe.columns))
            if missing_columns:
                raise PolicyArtifactError(
                    f"{key.title()} file is missing required columns: "
                    f"{', '.join(missing_columns)}"
                )
            if set(dataframe["data_origin"].dropna()) != {"synthetic"}:
                raise PolicyArtifactError(
                    f"{key.title()} file contains invalid data_origin values."
                )
            if set(dataframe["scenario_type"].dropna()) != {
                "hypothetical_policy_scenario"
            }:
                raise PolicyArtifactError(
                    f"{key.title()} file contains invalid scenario_type values."
                )
            outputs[key] = dataframe
        return outputs
    except PolicyArtifactError:
        if strict:
            raise
        return None
