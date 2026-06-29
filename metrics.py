"""KPI, weighted-rate, and ranking calculations for CSEE dashboard pages."""

import pandas as pd


def safe_int(value):
    """Convert a nullable aggregate to an integer suitable for display."""
    return int(value) if pd.notna(value) else 0

def metric_display_name(metric):
    """Map internal metric fields to user-facing labels."""
    from styles import tr

    return tr({
        "gpa": "GPA",
        "subject_gpa": "Subject GPA",
        "pass_rate": "Pass Rate (%)",
        "Count": "Candidate Count"
    }.get(metric, metric.replace("_", " ").title()))

def lower_is_better(metric):
    """Return True for NECTA GPA metrics where a lower value is stronger."""
    return metric in ["gpa", "subject_gpa"]

def format_metric_value(value, metric):
    """Format one metric consistently for insight and narrative text."""
    if pd.isna(value):
        return "N/A"
    if metric == "pass_rate":
        return f"{value:.1f}%"
    if metric in ["gpa", "subject_gpa"]:
        return f"{value:.2f}"
    return f"{value:,.0f}" if abs(value) >= 10 else f"{value:.2f}"


def weighted_rate(numerator, denominator):
    """Return a percentage from aggregate counts, or None for no candidates."""
    if denominator is None or pd.isna(denominator) or denominator <= 0:
        return None
    return (numerator / denominator) * 100


def weighted_school_pass_rate(df):
    """Calculate school pass rate from total passed and sat candidate counts."""
    if df.empty or not {"total_passed_candidates", "sat"}.issubset(df.columns):
        return None

    total_passed = df["total_passed_candidates"].sum()
    total_sat = df["sat"].sum()
    return weighted_rate(total_passed, total_sat)


def weighted_subject_pass_rate(df):
    """Calculate subject pass rate from total pass and sat candidate counts."""
    if df.empty or not {"pass", "sat"}.issubset(df.columns):
        return None

    total_passed = df["pass"].sum()
    total_sat = df["sat"].sum()
    return weighted_rate(total_passed, total_sat)


def school_kpi_values(filtered_school_df):
    """Build display-ready school KPIs without mutating the filtered data."""
    total_schools = (
        filtered_school_df["school_name"].nunique()
        if "school_name" in filtered_school_df.columns else 0
    )

    avg_gpa = filtered_school_df["gpa"].mean() if "gpa" in filtered_school_df.columns else None
    total_sat = filtered_school_df["sat"].sum() if "sat" in filtered_school_df.columns else 0
    total_passed = filtered_school_df["total_passed_candidates"].sum() if "total_passed_candidates" in filtered_school_df.columns else 0
    # Weighting by candidates prevents a small school from influencing the
    # national or regional pass rate as strongly as a much larger school.
    avg_pass_rate = weighted_rate(total_passed, total_sat)
    total_div1 = filtered_school_df["division_1"].sum() if "division_1" in filtered_school_df.columns else 0
    total_div0 = filtered_school_df["division_0"].sum() if "division_0" in filtered_school_df.columns else 0

    div1_percent = (total_div1 / total_sat * 100) if total_sat and total_sat > 0 else 0

    return {
        "total_schools": total_schools,
        "avg_gpa_display": f"{avg_gpa:.2f}" if pd.notna(avg_gpa) else "N/A",
        "avg_pass_rate_display": f"{avg_pass_rate:.1f}%" if pd.notna(avg_pass_rate) else "N/A",
        "total_sat_display": f"{safe_int(total_sat):,}",
        "total_passed_display": f"{safe_int(total_passed):,}",
        "div1_percent_display": f"{div1_percent:.1f}%",
        "div1_count": safe_int(total_div1),
        "div0_count": safe_int(total_div0),
    }

def subject_kpi_values(filtered_subject_df):
    """Build display-ready subject KPIs without mutating the filtered data."""
    avg_subject_gpa = filtered_subject_df["subject_gpa"].mean() if "subject_gpa" in filtered_subject_df.columns else None
    total_sat = filtered_subject_df["sat"].sum() if "sat" in filtered_subject_df.columns else 0
    total_passed = filtered_subject_df["pass"].sum() if "pass" in filtered_subject_df.columns else 0
    avg_pass_rate = weighted_rate(total_passed, total_sat)

    return {
        "avg_subject_gpa_display": f"{avg_subject_gpa:.2f}" if pd.notna(avg_subject_gpa) else "N/A",
        "avg_pass_rate_display": f"{avg_pass_rate:.1f}%" if pd.notna(avg_pass_rate) else "N/A",
        "registered_display": f"{safe_int(filtered_subject_df['registered'].sum()) if 'registered' in filtered_subject_df.columns else 0:,}",
        "sat_display": f"{safe_int(filtered_subject_df['sat'].sum()) if 'sat' in filtered_subject_df.columns else 0:,}",
        "passed_display": f"{safe_int(filtered_subject_df['pass'].sum()) if 'pass' in filtered_subject_df.columns else 0:,}",
        "withheld_display": f"{safe_int(filtered_subject_df['withheld'].sum()) if 'withheld' in filtered_subject_df.columns else 0:,}",
    }

def school_ranking_summary(df):
    """Aggregate one ranking row per normalized school identity."""
    if df.empty:
        return pd.DataFrame(columns=["school_name", "region", "gpa", "sat", "passed", "pass_rate", "division_0"])

    if "school_id" in df.columns:
        sort_columns = ["school_id"]
        if "year" in df.columns:
            sort_columns.append("year")
        identity_df = (
            df.sort_values(sort_columns)
            .groupby("school_id", as_index=False)
            .tail(1)[["school_id", "school_name", "region"]]
            .rename(columns={
                "school_name": "_display_name",
                "region": "_display_region",
            })
        )
        identity_df["_school_key"] = (
            identity_df["_display_name"]
            .astype("string")
            .str.upper()
            .str.replace(r"[^A-Z0-9]+", "", regex=True)
        )
        work_df = df.merge(identity_df, on="school_id", how="left")
        summary = (
            work_df.groupby(["_school_key", "_display_region"], as_index=False)
            .agg({
                "_display_name": "last",
                "gpa": "mean",
                "sat": "sum",
                "total_passed_candidates": "sum",
                "division_0": "sum"
            })
            .rename(columns={
                "_display_name": "school_name",
                "_display_region": "region",
            })
            .drop(columns="_school_key")
        )
    else:
        work_df = df.copy()
        work_df["_school_key"] = (
            work_df["school_name"]
            .astype("string")
            .str.upper()
            .str.replace(r"[^A-Z0-9]+", "", regex=True)
        )
        summary = (
            work_df.groupby(["_school_key", "region"], as_index=False)
            .agg({
                "school_name": "last",
                "gpa": "mean",
                "sat": "sum",
                "total_passed_candidates": "sum",
                "division_0": "sum"
            })
            .drop(columns="_school_key")
        )

    summary = summary[
        [
            "school_name",
            "region",
            "gpa",
            "sat",
            "total_passed_candidates",
            "division_0",
        ]
    ]
    summary["pass_rate"] = summary.apply(
        lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
        axis=1
    )
    summary["pass_rate"] = summary["pass_rate"].fillna(0)
    summary = summary.rename(columns={"total_passed_candidates": "passed"})
    return summary

def subject_ranking_summary(df):
    """Aggregate one ranking row per subject using candidate-weighted rates."""
    if df.empty:
        return pd.DataFrame(columns=["subject_name", "subject_gpa", "registered", "sat", "passed", "pass_rate"])

    summary = (
        df.groupby("subject_name", as_index=False)
        .agg({
            "subject_gpa": "mean",
            "registered": "sum",
            "sat": "sum",
            "pass": "sum"
        })
    )
    summary["pass_rate"] = summary.apply(
        lambda row: weighted_rate(row["pass"], row["sat"]),
        axis=1
    )
    summary["pass_rate"] = summary["pass_rate"].fillna(0)
    summary = summary.rename(columns={"pass": "passed"})
    return summary

def add_region_to_change(change_df, source_df):
    """Attach each school's latest known region to a change ranking."""
    if change_df.empty or source_df.empty:
        return change_df

    latest_regions = (
        source_df.sort_values("year")
        .groupby("school_name", as_index=False)
        .tail(1)[["school_name", "region"]]
    )
    return change_df.merge(latest_regions, on="school_name", how="left")

