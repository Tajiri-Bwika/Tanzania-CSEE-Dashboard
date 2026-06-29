"""Create transparent school intervention recommendations from offline scores."""

from __future__ import annotations

import numpy as np
import pandas as pd

from decision_config import (
    INTERVENTION_RANGES,
    MATHEMATICS_SUBJECTS,
    MULTIPLE_WEAK_SUBJECT_COUNT,
    SCIENCE_SUBJECTS,
    WEAK_SUBJECT_GPA,
    WEAK_SUBJECT_PASS_RATE,
)
from decision_features import latest_subject_profiles


def _subject_evidence(subject_df):
    """Summarize latest weak-subject evidence for each school."""
    profiles = latest_subject_profiles(subject_df)
    if profiles.empty:
        return pd.DataFrame()

    profiles["subject_key"] = (
        profiles["subject_name"].astype("string").str.strip().str.upper()
    )
    profiles["is_weak"] = (
        profiles["subject_gpa"].ge(WEAK_SUBJECT_GPA)
        | profiles["pass_rate"].lt(WEAK_SUBJECT_PASS_RATE)
    )
    profiles["is_weak_math"] = (
        profiles["is_weak"] & profiles["subject_key"].isin(MATHEMATICS_SUBJECTS)
    )
    profiles["is_weak_science"] = (
        profiles["is_weak"] & profiles["subject_key"].isin(SCIENCE_SUBJECTS)
    )

    rows = []
    for school_id, group in profiles.groupby("school_id"):
        weak = group[group["is_weak"]].copy()
        weakest = (
            group.sort_values(
                ["subject_gpa", "pass_rate"],
                ascending=[False, True],
                na_position="last",
            )
            .head(1)
        )
        weakest_row = weakest.iloc[0] if not weakest.empty else None
        rows.append(
            {
                "school_id": school_id,
                "weak_subject_count": int(weak["subject_name"].nunique()),
                "weak_subjects": ", ".join(
                    sorted(weak["subject_name"].dropna().astype(str).unique())
                ),
                "has_weak_mathematics": bool(weak["is_weak_math"].any()),
                "has_weak_science": bool(weak["is_weak_science"].any()),
                "weakest_subject": (
                    str(weakest_row["subject_name"])
                    if weakest_row is not None
                    else ""
                ),
                "weakest_subject_gpa": (
                    weakest_row["subject_gpa"]
                    if weakest_row is not None
                    else np.nan
                ),
                "weakest_subject_pass_rate": (
                    weakest_row["pass_rate"]
                    if weakest_row is not None
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def _select_intervention(row):
    """Apply one deterministic recommendation rule to a scored school."""
    if row["weak_subject_count"] >= MULTIPLE_WEAK_SUBJECT_COUNT:
        return (
            "Teacher Development Program",
            f"{int(row['weak_subject_count'])} weak subjects indicate a broad instructional challenge.",
        )
    if row["has_weak_mathematics"]:
        return (
            "Mathematics Tutoring Program",
            "Latest mathematics performance meets the weak-subject threshold.",
        )
    if row["has_weak_science"]:
        return (
            "Laboratory Support Program",
            "Latest science performance meets the weak-subject threshold.",
        )
    if (
        row["regional_risk_level"] == "High"
        and row["priority_category"] in {"Critical", "High", "Medium"}
    ):
        return (
            "Regional Support and Audit Program",
            "The school is in a high-risk region and has a material priority score.",
        )
    if row["priority_category"] in {"Critical", "High"}:
        return (
            "Targeted School Improvement Program",
            "The combined severity, decline, and recoverability score requires targeted support.",
        )
    return (
        "Monitor and Maintain Support",
        "Current evidence does not cross a targeted intervention threshold.",
    )


def _scenario_range(intervention):
    low, high = INTERVENTION_RANGES[intervention]
    return f"Assumption-based scenario estimate: +{low}% to +{high}% pass rate"


def build_intervention_recommendations(
    priority_df,
    school_risk_df,
    regional_risk_df,
    subject_df,
):
    """Return one assumption-labelled intervention recommendation per school."""
    if priority_df.empty or school_risk_df.empty:
        return pd.DataFrame()

    risk_columns = [
        "school_id",
        "risk_score",
        "risk_level",
        "pass_rate_decline_score",
        "subject_failure_score",
        "trend_instability_score",
    ]
    regional_columns = ["region", "risk_score", "risk_level"]
    recommendations = (
        priority_df.merge(
            school_risk_df[risk_columns],
            on="school_id",
            how="left",
        )
        .merge(
            regional_risk_df[regional_columns].rename(
                columns={
                    "risk_score": "regional_risk_score",
                    "risk_level": "regional_risk_level",
                }
            ),
            on="region",
            how="left",
        )
        .merge(_subject_evidence(subject_df), on="school_id", how="left")
    )

    defaults = {
        "weak_subject_count": 0,
        "weak_subjects": "",
        "has_weak_mathematics": False,
        "has_weak_science": False,
        "weakest_subject": "",
    }
    for column, default in defaults.items():
        recommendations[column] = recommendations[column].fillna(default)

    selected = recommendations.apply(_select_intervention, axis=1)
    recommendations["recommended_intervention"] = [
        item[0] for item in selected
    ]
    recommendations["problem_detected"] = [item[1] for item in selected]
    recommendations["expected_improvement_range"] = recommendations[
        "recommended_intervention"
    ].map(_scenario_range)
    recommendations["assumption_basis"] = (
        "Planning scenario only; the range is not a measured, causal, or guaranteed outcome."
    )
    recommendations["data_origin"] = "observed-derived"
    recommendations["scenario_origin"] = "assumption-based"
    recommendations["intervention_priority"] = recommendations[
        "priority_category"
    ]

    columns = [
        "priority_rank",
        "school_id",
        "school_name",
        "region",
        "priority_score",
        "priority_category",
        "risk_score",
        "risk_level",
        "regional_risk_score",
        "regional_risk_level",
        "problem_detected",
        "recommended_intervention",
        "intervention_priority",
        "expected_improvement_range",
        "assumption_basis",
        "weak_subject_count",
        "weak_subjects",
        "weakest_subject",
        "weakest_subject_gpa",
        "weakest_subject_pass_rate",
        "pass_rate_decline_score",
        "subject_failure_score",
        "trend_instability_score",
        "data_quality",
        "data_origin",
        "scenario_origin",
    ]
    return (
        recommendations[columns]
        .sort_values(["priority_rank", "risk_score"], ascending=[True, False])
        .reset_index(drop=True)
    )
