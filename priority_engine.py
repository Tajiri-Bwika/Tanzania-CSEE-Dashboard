"""Calculate auditable school and regional intervention priority rankings."""

from __future__ import annotations

import numpy as np
import pandas as pd

from decision_config import PRIORITY_WEIGHTS, priority_category
from decision_features import (
    build_school_year_panel,
    clipped_score,
    data_quality_label,
    latest_school_records,
    linear_slope,
)


def _severity_score(gpa, pass_rate):
    """Combine current GPA and pass-rate weakness on a fixed 0-100 scale."""
    gpa_weakness = clipped_score(((gpa - 1.0) / 4.0) * 100)
    pass_weakness = clipped_score(100 - pass_rate)
    values = [value for value in (gpa_weakness, pass_weakness) if np.isfinite(value)]
    return float(np.mean(values)) if values else np.nan


def _trend_decline_score(gpa_slope, pass_rate_slope):
    """Score unfavorable annual change while treating stable/improving trends as zero."""
    gpa_decline = clipped_score(max(gpa_slope, 0) / 0.25 * 100)
    pass_decline = clipped_score(max(-pass_rate_slope, 0) / 10.0 * 100)
    values = [value for value in (gpa_decline, pass_decline) if np.isfinite(value)]
    return float(np.mean(values)) if values else 0.0


def _historical_recovery_score(group):
    """Measure the strongest observed annual recovery for one school."""
    history = (
        group[["year", "gpa", "pass_rate"]]
        .dropna(subset=["year"])
        .sort_values("year")
        .copy()
    )
    if len(history) < 2:
        return 0.0
    pass_improvement = history["pass_rate"].diff().clip(lower=0) / 10.0 * 100
    gpa_improvement = (-history["gpa"].diff()).clip(lower=0) / 0.25 * 100
    recovery = pd.concat(
        [
            pass_improvement.clip(upper=100),
            gpa_improvement.clip(upper=100),
        ],
        axis=1,
    ).mean(axis=1)
    return float(recovery.max()) if recovery.notna().any() else 0.0


def build_priority_rankings(school_df):
    """Return school and regional Priority Index tables from historical data."""
    panel = build_school_year_panel(school_df)
    if panel.empty:
        return pd.DataFrame(), pd.DataFrame()

    latest = latest_school_records(panel)
    slopes = []
    recoveries = []
    for school_id, history in panel.groupby("school_id"):
        slopes.append(
            {
                "school_id": school_id,
                "gpa_slope": linear_slope(history, "gpa"),
                "pass_rate_slope": linear_slope(history, "pass_rate"),
            }
        )
        recoveries.append(
            {
                "school_id": school_id,
                "historical_recovery_score": _historical_recovery_score(history),
            }
        )
    school_scores = (
        latest.merge(pd.DataFrame(slopes), on="school_id", how="left")
        .merge(pd.DataFrame(recoveries), on="school_id", how="left")
    )
    school_scores["severity_score"] = school_scores.apply(
        lambda row: _severity_score(row["gpa"], row["pass_rate"]),
        axis=1,
    )
    school_scores["trend_decline_score"] = school_scores.apply(
        lambda row: _trend_decline_score(
            row["gpa_slope"],
            row["pass_rate_slope"],
        ),
        axis=1,
    )
    school_scores["severity_band"] = pd.cut(
        school_scores["severity_score"],
        bins=[-0.01, 35, 65, 100],
        labels=["Lower", "Moderate", "Higher"],
        include_lowest=True,
    ).astype("string")

    peer_keys = ["size_band", "severity_band"]
    peer_stats = (
        school_scores.groupby(peer_keys, dropna=False)["historical_recovery_score"]
        .agg(["median", "count"])
        .reset_index()
        .rename(
            columns={
                "median": "recoverability_score",
                "count": "similar_school_count",
            }
        )
    )
    school_scores = school_scores.merge(peer_stats, on=peer_keys, how="left")
    school_scores["recoverability_score"] = (
        school_scores["recoverability_score"].fillna(
            school_scores["historical_recovery_score"]
        )
    )
    school_scores["priority_score"] = (
        PRIORITY_WEIGHTS["severity"] * school_scores["severity_score"]
        + PRIORITY_WEIGHTS["trend_decline"] * school_scores["trend_decline_score"]
        + PRIORITY_WEIGHTS["recoverability"] * school_scores["recoverability_score"]
    ).clip(0, 100)
    school_scores["priority_category"] = school_scores["priority_score"].map(
        priority_category
    )
    school_scores["priority_rank"] = (
        school_scores["priority_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    school_scores["data_quality"] = school_scores["evidence_years"].map(
        lambda years: data_quality_label(years, has_subject=True)
    )
    school_scores = school_scores.rename(
        columns={
            "year": "latest_year",
            "gpa": "latest_gpa",
            "pass_rate": "latest_pass_rate",
            "sat": "latest_sat",
        }
    )
    school_columns = [
        "priority_rank",
        "school_id",
        "school_name",
        "region",
        "latest_year",
        "latest_gpa",
        "latest_pass_rate",
        "latest_sat",
        "size_band",
        "severity_score",
        "trend_decline_score",
        "recoverability_score",
        "priority_score",
        "priority_category",
        "gpa_slope",
        "pass_rate_slope",
        "similar_school_count",
        "evidence_years",
        "first_year",
        "data_quality",
    ]
    school_scores = school_scores[school_columns].sort_values("priority_rank")

    regional_rows = []
    for region, group in school_scores.groupby("region"):
        weights = group["latest_sat"].fillna(0).clip(lower=1)
        regional_score = float(np.average(group["priority_score"], weights=weights))
        regional_rows.append(
            {
                "region": region,
                "priority_score": regional_score,
                "priority_category": priority_category(regional_score),
                "school_count": int(group["school_id"].nunique()),
                "critical_school_count": int(
                    group["priority_category"].eq("Critical").sum()
                ),
                "high_priority_school_count": int(
                    group["priority_category"].isin(["Critical", "High"]).sum()
                ),
                "candidate_count": float(group["latest_sat"].sum()),
                "average_severity_score": float(group["severity_score"].mean()),
                "average_trend_decline_score": float(
                    group["trend_decline_score"].mean()
                ),
                "average_recoverability_score": float(
                    group["recoverability_score"].mean()
                ),
            }
        )
    regional_scores = pd.DataFrame(regional_rows)
    regional_scores["priority_rank"] = (
        regional_scores["priority_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    regional_scores = regional_scores[
        [
            "priority_rank",
            "region",
            "priority_score",
            "priority_category",
            "school_count",
            "critical_school_count",
            "high_priority_school_count",
            "candidate_count",
            "average_severity_score",
            "average_trend_decline_score",
            "average_recoverability_score",
        ]
    ].sort_values("priority_rank")
    return school_scores.reset_index(drop=True), regional_scores.reset_index(drop=True)

