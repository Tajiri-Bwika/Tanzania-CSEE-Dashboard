"""Build Version 4 decision-support artifacts as an explicit offline task."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from data_loader import (
    SCHOOL_COMBINED_FILE,
    SUBJECT_COMBINED_FILE,
    load_data,
)
from decision_config import (
    DECISION_ARTIFACT_DIR,
    DECISION_ENGINE_VERSION,
    INTERVENTION_FILE,
    MANIFEST_FILE,
    PRIORITY_FILES,
    PRIORITY_WEIGHTS,
    RISK_FILES,
    RISK_WEIGHTS,
)
from intervention_engine import build_intervention_recommendations
from priority_engine import build_priority_rankings
from risk_engine import build_risk_scores


def _write_csv(df, path):
    """Write a stable UTF-8 CSV without modifying source data."""
    df.to_csv(path, index=False, encoding="utf-8")


def build_decision_artifacts(output_dir=DECISION_ARTIFACT_DIR):
    """Generate validated CSV and JSON files consumed by Streamlit pages."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    school_df, subject_df = load_data(strict=True)
    school_priority, regional_priority = build_priority_rankings(school_df)
    school_risk, regional_risk = build_risk_scores(school_df, subject_df)
    interventions = build_intervention_recommendations(
        school_priority,
        school_risk,
        regional_risk,
        subject_df,
    )
    outputs = {
        PRIORITY_FILES["school_priority"]: school_priority,
        PRIORITY_FILES["regional_priority"]: regional_priority,
        RISK_FILES["school_risk"]: school_risk,
        RISK_FILES["regional_risk"]: regional_risk,
        INTERVENTION_FILE: interventions,
    }
    for filename, dataframe in outputs.items():
        if dataframe.empty:
            raise ValueError(f"Refusing to write empty decision artifact: {filename}")
        _write_csv(dataframe, output_path / filename)

    manifest = {
        "decision_engine_version": DECISION_ENGINE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generation_mode": "offline",
        "source_files": [
            SCHOOL_COMBINED_FILE.name,
            SUBJECT_COMBINED_FILE.name,
        ],
        "source_rows": {
            "school": int(len(school_df)),
            "subject": int(len(subject_df)),
        },
        "year_coverage": {
            "school_min": int(pd.to_numeric(school_df["year"]).min()),
            "school_max": int(pd.to_numeric(school_df["year"]).max()),
            "subject_min": int(pd.to_numeric(subject_df["year"]).min()),
            "subject_max": int(pd.to_numeric(subject_df["year"]).max()),
        },
        "artifact_rows": {
            filename: int(len(dataframe))
            for filename, dataframe in outputs.items()
        },
        "priority_weights": PRIORITY_WEIGHTS,
        "risk_weights": RISK_WEIGHTS,
        "scenario_disclosure": (
            "Intervention improvement ranges are assumption-based planning "
            "scenario estimates, not observed, causal, or guaranteed outcomes."
        ),
        "data_origin_policy": (
            "Decision scores use observed-derived data. Any future simulated "
            "outcome must remain separate from training data and use data_origin=synthetic."
        ),
        "policy_scenario_policy": (
            "Any 2032 cohort-pressure output is a configurable hypothetical "
            "policy scenario, not a confirmed government policy outcome."
        ),
    }
    with (output_path / MANIFEST_FILE).open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")
    return outputs, manifest


def main():
    """Build artifacts only when this module is run directly."""
    outputs, manifest = build_decision_artifacts()
    print(f"Decision artifacts written to: {DECISION_ARTIFACT_DIR}")
    for filename, dataframe in outputs.items():
        print(f"- {filename}: {len(dataframe):,} rows")
    print(f"- {MANIFEST_FILE}: version {manifest['decision_engine_version']}")


if __name__ == "__main__":
    main()
