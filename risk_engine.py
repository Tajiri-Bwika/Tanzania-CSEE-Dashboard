"""Calculate composite school and regional education risk scores."""

from __future__ import annotations

import numpy as np
import pandas as pd

from decision_config import RISK_WEIGHTS, risk_level
from decision_features import (
    build_school_year_panel,
    clipped_score,
    data_quality_label,
    latest_school_records,
    latest_subject_failure_by_school,
    linear_slope,
)
from metrics import weighted_rate


def _pass_decline_score(pass_rate_slope):
    """Scale an annual pass-rate decline of ten points or more to maximum risk."""
    if pass_rate_slope is None or not np.isfinite(pass_rate_slope):
        return 0.0
    return clipped_score(max(-pass_rate_slope, 0) / 10.0 * 100)


def _instability_score(history):
    """Combine GPA and pass-rate volatility from recent annual evidence."""
    recent = history.sort_values("year").tail(5)
    gpa_volatility = clipped_score(recent["gpa"].std(ddof=0) / 0.50 * 100)
    pass_volatility = clipped_score(
        recent["pass_rate"].std(ddof=0) / 10.0 * 100
    )
    values = [
        value
        for value in (gpa_volatility, pass_volatility)
        if np.isfinite(value)
    ]
    return float(np.mean(values)) if values else 0.0


def _weighted_available_score(row):
    """Apply approved weights and re-normalize only when evidence is missing."""
    components = [
        (row["pass_rate_decline_score"], RISK_WEIGHTS["pass_rate_decline"]),
        (row["subject_failure_score"], RISK_WEIGHTS["subject_failure"]),
        (row["trend_instability_score"], RISK_WEIGHTS["trend_instability"]),
    ]
    available = [(value, weight) for value, weight in components if np.isfinite(value)]
    if not available:
        return np.nan
    total_weight = sum(weight for _, weight in available)
    return sum(value * weight for value, weight in available) / total_weight


def build_risk_scores(school_df, subject_df):
    """Return school and regional composite risk tables."""
    panel = build_school_year_panel(school_df)
    if panel.empty:
        return pd.DataFrame(), pd.DataFrame()

    latest = latest_school_records(panel)
    subject_failure = latest_subject_failure_by_school(subject_df)
    rows = []
    for school_id, history in panel.groupby("school_id"):
        latest_row = latest[latest["school_id"] == school_id].iloc[0]
        pass_slope = linear_slope(history, "pass_rate")
        rows.append(
            {
                "school_id": school_id,
                "school_name": latest_row["school_name"],
                "region": latest_row["region"],
                "latest_year": int(latest_row["year"]),
                "latest_gpa": latest_row["gpa"],
                "latest_pass_rate": latest_row["pass_rate"],
                "latest_sat": latest_row["sat"],
                "evidence_years": int(latest_row["evidence_years"]),
                "pass_rate_slope": pass_slope,
                "pass_rate_decline_score": _pass_decline_score(pass_slope),
                "trend_instability_score": _instability_score(history),
            }
        )
    school_scores = pd.DataFrame(rows).merge(
        subject_failure,
        on="school_id",
        how="left",
    )
    school_scores["subject_failure_score"] = school_scores[
        "subject_failure_rate"
    ].clip(0, 100)
    school_scores["risk_score"] = school_scores.apply(
        _weighted_available_score,
        axis=1,
    ).clip(0, 100)
    school_scores["risk_level"] = school_scores["risk_score"].map(risk_level)
    school_scores["data_quality"] = school_scores.apply(
        lambda row: data_quality_label(
            row["evidence_years"],
            has_subject=np.isfinite(row["subject_failure_score"]),
        ),
        axis=1,
    )
    school_scores = school_scores[
        [
            "school_id",
            "school_name",
            "region",
            "latest_year",
            "latest_gpa",
            "latest_pass_rate",
            "latest_sat",
            "pass_rate_decline_score",
            "subject_failure_score",
            "trend_instability_score",
            "risk_score",
            "risk_level",
            "pass_rate_slope",
            "subject_failure_rate",
            "subject_count",
            "evidence_years",
            "data_quality",
        ]
    ].sort_values(["risk_score", "school_name"], ascending=[False, True])

    region_panel = (
        panel.groupby(["region", "year"], as_index=False)
        .agg(
            gpa=("gpa", "mean"),
            sat=("sat", "sum"),
            passed=("total_passed_candidates", "sum"),
        )
    )
    region_panel["pass_rate"] = region_panel.apply(
        lambda row: weighted_rate(row["passed"], row["sat"]),
        axis=1,
    )
    region_subject = (
        latest_subject_failure_by_school(subject_df)
        .merge(
            latest[["school_id", "region"]],
            on="school_id",
            how="left",
        )
        .groupby("region", as_index=False)
        .agg(
            subject_sat=("subject_sat", "sum"),
            subject_passed=("subject_passed", "sum"),
        )
    )
    region_subject["subject_failure_rate"] = region_subject.apply(
        lambda row: (
            100
            - weighted_rate(row["subject_passed"], row["subject_sat"])
            if row["subject_sat"] > 0
            else np.nan
        ),
        axis=1,
    )

    regional_rows = []
    for region, history in region_panel.groupby("region"):
        pass_slope = linear_slope(history, "pass_rate")
        latest_row = history.sort_values("year").iloc[-1]
        regional_rows.append(
            {
                "region": region,
                "latest_year": int(latest_row["year"]),
                "latest_gpa": latest_row["gpa"],
                "latest_pass_rate": latest_row["pass_rate"],
                "candidate_count": latest_row["sat"],
                "evidence_years": int(history["year"].nunique()),
                "pass_rate_slope": pass_slope,
                "pass_rate_decline_score": _pass_decline_score(pass_slope),
                "trend_instability_score": _instability_score(history),
            }
        )
    regional_scores = pd.DataFrame(regional_rows).merge(
        region_subject[["region", "subject_failure_rate"]],
        on="region",
        how="left",
    )
    regional_scores["subject_failure_score"] = regional_scores[
        "subject_failure_rate"
    ].clip(0, 100)
    regional_scores["risk_score"] = regional_scores.apply(
        _weighted_available_score,
        axis=1,
    ).clip(0, 100)
    regional_scores["risk_level"] = regional_scores["risk_score"].map(risk_level)
    regional_scores["risk_rank"] = (
        regional_scores["risk_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    regional_scores["data_quality"] = regional_scores.apply(
        lambda row: data_quality_label(
            row["evidence_years"],
            has_subject=np.isfinite(row["subject_failure_score"]),
        ),
        axis=1,
    )
    regional_scores = regional_scores[
        [
            "risk_rank",
            "region",
            "latest_year",
            "latest_gpa",
            "latest_pass_rate",
            "candidate_count",
            "pass_rate_decline_score",
            "subject_failure_score",
            "trend_instability_score",
            "risk_score",
            "risk_level",
            "pass_rate_slope",
            "subject_failure_rate",
            "evidence_years",
            "data_quality",
        ]
    ].sort_values("risk_rank")
    return school_scores.reset_index(drop=True), regional_scores.reset_index(drop=True)

