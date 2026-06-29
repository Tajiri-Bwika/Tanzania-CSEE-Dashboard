"""Build shared school, subject, trend, and peer features for decision engines."""

from __future__ import annotations

import numpy as np
import pandas as pd

from metrics import weighted_rate


SCHOOL_REQUIRED_COLUMNS = {
    "school_id",
    "school_name",
    "region",
    "year",
    "gpa",
    "sat",
    "total_passed_candidates",
}

SUBJECT_REQUIRED_COLUMNS = {
    "school_id",
    "school_name",
    "region",
    "year",
    "subject_name",
    "subject_gpa",
    "sat",
    "pass",
}


def require_columns(df, required_columns, label):
    """Raise ValueError when an engine input lacks required analytical fields."""
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def clipped_score(value):
    """Return a finite 0-100 score."""
    if value is None or not np.isfinite(value):
        return np.nan
    return float(np.clip(value, 0, 100))


def linear_slope(group, value_col, recent_years=4):
    """Estimate annual direction from the latest finite school or region values."""
    history = (
        group[["year", value_col]]
        .dropna()
        .groupby("year", as_index=False)[value_col]
        .mean()
        .sort_values("year")
        .tail(recent_years)
    )
    if len(history) < 2:
        return np.nan
    slope, _ = np.polyfit(
        history["year"].astype(float),
        history[value_col].astype(float),
        1,
    )
    return float(slope)


def build_school_year_panel(school_df):
    """Aggregate source rows to one validated school-year analytical record."""
    require_columns(school_df, SCHOOL_REQUIRED_COLUMNS, "School dataset")
    source = school_df.copy()
    source = source[
        source["school_id"].notna()
        & source["region"].notna()
        & source["year"].notna()
        & (source["region"].astype("string").str.strip().str.upper() != "UNKNOWN")
    ].copy()
    if source.empty:
        return pd.DataFrame()

    numeric_columns = [
        "year",
        "gpa",
        "sat",
        "regist",
        "total_passed_candidates",
        "division_0",
        "division_1",
    ]
    for column in numeric_columns:
        if column in source.columns:
            source[column] = pd.to_numeric(source[column], errors="coerce")

    aggregations = {
        "school_name": "last",
        "region": "last",
        "gpa": "mean",
        "sat": "sum",
        "total_passed_candidates": "sum",
    }
    for optional in ("regist", "division_0", "division_1"):
        if optional in source.columns:
            aggregations[optional] = "sum"

    panel = (
        source.sort_values(["school_id", "year"])
        .groupby(["school_id", "year"], as_index=False)
        .agg(aggregations)
        .sort_values(["school_id", "year"])
        .reset_index(drop=True)
    )
    panel["pass_rate"] = panel.apply(
        lambda row: weighted_rate(
            row["total_passed_candidates"],
            row["sat"],
        ),
        axis=1,
    )
    if "division_0" in panel.columns:
        panel["division_0_rate"] = panel.apply(
            lambda row: weighted_rate(row["division_0"], row["sat"]),
            axis=1,
        )
    if "division_1" in panel.columns:
        panel["division_1_rate"] = panel.apply(
            lambda row: weighted_rate(row["division_1"], row["sat"]),
            axis=1,
        )
    if "regist" in panel.columns:
        panel["attendance_rate"] = panel.apply(
            lambda row: weighted_rate(row["sat"], row["regist"]),
            axis=1,
        )
    return panel


def latest_school_records(panel):
    """Return one latest record per school with size and evidence metadata."""
    if panel.empty:
        return pd.DataFrame()
    latest = (
        panel.sort_values(["school_id", "year"])
        .groupby("school_id", as_index=False)
        .tail(1)
        .copy()
    )
    ranked_volume = latest["sat"].fillna(0).rank(method="first")
    latest["size_band"] = pd.qcut(
        ranked_volume,
        q=4,
        labels=["Small", "Medium", "Large", "Very Large"],
    ).astype("string")
    evidence = (
        panel.groupby("school_id", as_index=False)
        .agg(
            evidence_years=("year", "nunique"),
            first_year=("year", "min"),
            latest_evidence_year=("year", "max"),
        )
    )
    return latest.merge(evidence, on="school_id", how="left")


def latest_subject_profiles(subject_df):
    """Return latest school-subject GPA, pass rate, and candidate counts."""
    require_columns(subject_df, SUBJECT_REQUIRED_COLUMNS, "Subject dataset")
    source = subject_df.copy()
    source = source[
        source["school_id"].notna()
        & source["year"].notna()
        & source["subject_name"].notna()
    ].copy()
    for column in ("year", "subject_gpa", "sat", "pass"):
        source[column] = pd.to_numeric(source[column], errors="coerce")
    latest_years = (
        source.groupby("school_id", as_index=False)["year"]
        .max()
        .rename(columns={"year": "latest_subject_year"})
    )
    source = source.merge(latest_years, on="school_id", how="inner")
    source = source[source["year"] == source["latest_subject_year"]].copy()
    profiles = (
        source.groupby(
            [
                "school_id",
                "school_name",
                "region",
                "latest_subject_year",
                "subject_name",
            ],
            as_index=False,
        )
        .agg(
            subject_gpa=("subject_gpa", "mean"),
            sat=("sat", "sum"),
            passed=("pass", "sum"),
        )
    )
    profiles["pass_rate"] = profiles.apply(
        lambda row: weighted_rate(row["passed"], row["sat"]),
        axis=1,
    )
    profiles["failure_rate"] = 100 - profiles["pass_rate"]
    return profiles


def latest_subject_failure_by_school(subject_df):
    """Return candidate-weighted latest subject failure for every school."""
    profiles = latest_subject_profiles(subject_df)
    if profiles.empty:
        return pd.DataFrame()
    summary = (
        profiles.groupby("school_id", as_index=False)
        .agg(
            latest_subject_year=("latest_subject_year", "max"),
            subject_sat=("sat", "sum"),
            subject_passed=("passed", "sum"),
            subject_count=("subject_name", "nunique"),
        )
    )
    summary["subject_failure_rate"] = summary.apply(
        lambda row: (
            100
            - weighted_rate(row["subject_passed"], row["subject_sat"])
            if row["subject_sat"] > 0
            else np.nan
        ),
        axis=1,
    )
    return summary


def data_quality_label(evidence_years, has_subject=True):
    """Describe whether a score has enough trend and subject evidence."""
    if evidence_years < 2:
        return "Insufficient trend history"
    if not has_subject:
        return "Missing subject evidence"
    if evidence_years < 4:
        return "Limited trend history"
    return "Complete"

