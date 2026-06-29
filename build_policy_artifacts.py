"""Generate all 2032 policy-planning scenario artifacts offline."""

from __future__ import annotations

from pathlib import Path

from data_loader import load_data
from decision_artifacts import load_decision_artifacts
from policy_config import POLICY_ARTIFACT_DIR, POLICY_FILES
from policy_planning_2032 import build_policy_scenarios


def build_policy_artifacts(output_dir=POLICY_ARTIFACT_DIR):
    """Build and write the four validated synthetic policy CSV outputs."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    school_df, _ = load_data(strict=True)
    decision_outputs = load_decision_artifacts(strict=True)
    outputs = build_policy_scenarios(school_df, decision_outputs)
    for key, filename in POLICY_FILES.items():
        dataframe = outputs[key]
        if dataframe.empty:
            raise ValueError(f"Refusing to write empty policy artifact: {filename}")
        dataframe.to_csv(output_path / filename, index=False, encoding="utf-8")
    return outputs


def main():
    """Build scenario files only when explicitly executed."""
    outputs = build_policy_artifacts()
    print(f"2032 policy artifacts written to: {POLICY_ARTIFACT_DIR}")
    for key, filename in POLICY_FILES.items():
        print(f"- {filename}: {len(outputs[key]):,} rows")


if __name__ == "__main__":
    main()
