"""Convert CSEE metrics into concise trends, risks, rankings, and policy insights."""

import html

import numpy as np
import pandas as pd
import streamlit as st

from charts import weighted_pass_rate_by_group
from metrics import format_metric_value, lower_is_better, metric_display_name, safe_int, weighted_rate
from styles import localize_phrase, render_insight_card, tr, use_swahili


def performance_change(df, group_col, value_col):
    """Rank groups by change between the two latest available years."""
    if df.empty or "year" not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "change", "improvement_score"])

    years = sorted(df["year"].dropna().unique().tolist())
    if len(years) < 2:
        return pd.DataFrame(columns=[group_col, "change", "improvement_score"])

    latest_year = years[-1]
    prev_year = years[-2]

    if value_col == "pass_rate" and {"total_passed_candidates", "sat"}.issubset(df.columns):
        temp = (
            df[df["year"].isin([prev_year, latest_year])]
            .groupby(["year", group_col], as_index=False)
            .agg({
                "total_passed_candidates": "sum",
                "sat": "sum"
            })
        )
        temp["pass_rate"] = temp.apply(
            lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
            axis=1
        )
        latest = temp[temp["year"] == latest_year].set_index(group_col)[value_col]
        prev = temp[temp["year"] == prev_year].set_index(group_col)[value_col]
    elif value_col == "pass_rate" and {"pass", "sat"}.issubset(df.columns):
        temp = (
            df[df["year"].isin([prev_year, latest_year])]
            .groupby(["year", group_col], as_index=False)
            .agg({
                "pass": "sum",
                "sat": "sum"
            })
        )
        temp["pass_rate"] = temp.apply(
            lambda row: weighted_rate(row["pass"], row["sat"]),
            axis=1
        )
        latest = temp[temp["year"] == latest_year].set_index(group_col)[value_col]
        prev = temp[temp["year"] == prev_year].set_index(group_col)[value_col]
    else:
        latest = df[df["year"] == latest_year].groupby(group_col)[value_col].mean()
        prev = df[df["year"] == prev_year].groupby(group_col)[value_col].mean()

    change = (latest - prev).dropna().reset_index()
    change.columns = [group_col, "change"]

    if value_col in ["gpa", "subject_gpa"]:
        change["improvement_score"] = -change["change"]
    else:
        change["improvement_score"] = change["change"]

    return change.sort_values("improvement_score", ascending=False)

def regional_gap(df):
    """Return the strongest, weakest, and GPA gap between named regions."""
    if df.empty or "region" not in df.columns or "gpa" not in df.columns:
        return None

    df = df[df["gpa"].notna() & (df["region"].astype(str).str.upper() != "UNKNOWN")]
    if df.empty:
        return None

    region_avg = (
        df.groupby("region", as_index=False)["gpa"]
        .mean()
        .dropna(subset=["gpa"])
        .sort_values("gpa", ascending=True)
    )

    if region_avg.empty or len(region_avg) < 2:
        return None

    best_region = region_avg.iloc[0]
    worst_region = region_avg.iloc[-1]
    gap = worst_region["gpa"] - best_region["gpa"]

    return {
        "best_region": best_region["region"],
        "best_gpa": best_region["gpa"],
        "worst_region": worst_region["region"],
        "worst_gpa": worst_region["gpa"],
        "gap": gap
    }

def risk_schools(df, threshold=15):
    """Return school-year rows whose Division 0 rate exceeds a threshold."""
    if df.empty or "division_0" not in df.columns or "sat" not in df.columns:
        return pd.DataFrame()

    temp = df.copy()
    temp = temp[temp["sat"] > 0].copy()
    if temp.empty:
        return pd.DataFrame()

    temp["div0_rate"] = (temp["division_0"] / temp["sat"]) * 100
    return temp[temp["div0_rate"] > threshold].sort_values("div0_rate", ascending=False)

def attendance_efficiency(df):
    """Return mean school attendance efficiency for valid registration rows."""
    if df.empty or "regist" not in df.columns or "sat" not in df.columns:
        return None

    temp = df.copy()
    temp = temp[temp["regist"] > 0]
    if temp.empty:
        return None

    temp["attendance_rate"] = (temp["sat"] / temp["regist"]) * 100
    return temp["attendance_rate"].mean()

def subject_strength_table(df):
    """Aggregate and rank subjects using GPA and candidate-weighted pass rate."""
    if df.empty or not {"subject_name", "subject_gpa", "pass", "sat"}.issubset(df.columns):
        return pd.DataFrame()

    df = df[df["subject_gpa"].notna()].copy()
    if df.empty:
        return pd.DataFrame()

    out = (
        df.groupby("subject_name", as_index=False)
        .agg({
            "subject_gpa": "mean",
            "pass": "sum",
            "sat": "sum"
        })
    )
    out["pass_rate"] = out.apply(
        lambda row: weighted_rate(row["pass"], row["sat"]),
        axis=1
    )
    out["pass_rate"] = out["pass_rate"].fillna(0)
    out = out.sort_values(["subject_gpa", "pass_rate"], ascending=[True, False])
    return out[["subject_name", "subject_gpa", "pass_rate"]]

def last_n_year_slope(df, year_col, value_col, n=3):
    """Estimate recent annual direction from the latest available years."""
    if df.empty or not {year_col, value_col}.issubset(df.columns):
        return None

    temp = (
        df[[year_col, value_col]]
        .dropna()
        .groupby(year_col, as_index=False)[value_col]
        .mean()
        .sort_values(year_col)
        .tail(n)
    )

    if len(temp) < 2:
        return None

    x = temp[year_col].astype(float).to_numpy()
    y = temp[value_col].astype(float).to_numpy()
    slope, _ = np.polyfit(x, y, 1)
    return slope

def momentum_status(slope, metric):
    """Translate a recent slope into Improving, Stable, or Declining."""
    if slope is None or pd.isna(slope):
        return "Stable", "neutral"

    if lower_is_better(metric):
        if slope < -0.05:
            return "Improving", "good"
        if slope > 0.05:
            return "Declining", "danger"
        return "Stable", "neutral"

    if slope > 1:
        return "Improving", "good"
    if slope < -1:
        return "Declining", "danger"
    return "Stable", "neutral"

def render_momentum_indicator(df, year_col, value_col, label, context="selected data"):
    """Render a plain-language momentum card and return its status and slope."""
    slope = last_n_year_slope(df, year_col, value_col)
    status, badge_status = momentum_status(slope, value_col)
    slope_text = "Not enough history" if slope is None else f"Last-3-year slope {slope:+.2f} points/year"
    render_insight_card(
        f"{label} Momentum",
        status,
        f"{slope_text} for {context}",
        badge_status
    )
    return status, slope

def trend_insight_text(df, year_col, value_col, label, group_col=None, context="selected data"):
    """Describe trend direction, latest value, and comparison spread."""
    if df.empty or not {year_col, value_col}.issubset(df.columns):
        if use_swahili():
            return f"Hakuna data ya {localize_phrase(label).lower()} kwa uchaguzi wa sasa."
        return f"No {label.lower()} data is available for the current selection."

    if group_col and group_col in df.columns:
        history = (
            df[[year_col, group_col, value_col]]
            .dropna()
            .groupby([year_col, group_col], as_index=False)[value_col]
            .mean()
            .sort_values([year_col, group_col])
        )
    else:
        history = (
            df[[year_col, value_col]]
            .dropna()
            .groupby(year_col, as_index=False)[value_col]
            .mean()
            .sort_values(year_col)
        )

    if history.empty:
        if use_swahili():
            return f"Hakuna data ya {localize_phrase(label).lower()} kwa uchaguzi wa sasa."
        return f"No {label.lower()} data is available for the current selection."

    if group_col and group_col in history.columns:
        latest_year = history[year_col].max()
        latest = history[history[year_col] == latest_year].copy()
        latest = latest.sort_values(value_col, ascending=lower_is_better(value_col))
        best = latest.iloc[0]
        worst = latest.iloc[-1]
        gap = abs(best[value_col] - worst[value_col])
        if use_swahili():
            return (
                f"Mwaka {int(latest_year)}, {best[group_col]} inaongoza kwenye {localize_phrase(label)} kwa "
                f"{format_metric_value(best[value_col], value_col)}, wakati {worst[group_col]} ina "
                f"{format_metric_value(worst[value_col], value_col)}. Tofauti ni pointi {gap:.2f}, "
                f"ikionyesha pengo ndani ya {localize_phrase(context)}."
            )

        return (
            f"In {int(latest_year)}, {best[group_col]} leads on {label} at "
            f"{format_metric_value(best[value_col], value_col)}, while {worst[group_col]} records "
            f"{format_metric_value(worst[value_col], value_col)}. The gap is {gap:.2f} points, "
            f"showing the spread across {context}."
        )

    first = history.iloc[0]
    latest = history.iloc[-1]
    change = latest[value_col] - first[value_col]
    slope = last_n_year_slope(history, year_col, value_col)
    status, _ = momentum_status(slope, value_col)
    direction = "improved" if (change < 0 if lower_is_better(value_col) else change > 0) else "declined"
    if abs(change) < 0.01:
        direction = "remained broadly stable"
    if use_swahili():
        if direction == "improved":
            sw_direction = "imeimarika"
        elif direction == "declined":
            sw_direction = "imeshuka"
        else:
            sw_direction = "imebaki karibu bila mabadiliko makubwa"
        return (
            f"Kuanzia {int(first[year_col])} hadi {int(latest[year_col])}, {localize_phrase(context)} "
            f"{sw_direction} kwenye {localize_phrase(label)} kwa pointi {abs(change):.2f}. "
            f"Thamani ya karibuni ni {format_metric_value(latest[value_col], value_col)}, "
            f"na mwenendo wa miaka 3 ya mwisho ni {localize_phrase(status)}."
        )
    return (
        f"From {int(first[year_col])} to {int(latest[year_col])}, {context} {direction} on {label} "
        f"by {abs(change):.2f} points. The latest value is {format_metric_value(latest[value_col], value_col)}, "
        f"and the last-3-year momentum is {status}."
    )


def forecast_interpretation_text(df, year_col, value_col, label, context):
    """Explain a short trend forecast in planning language, including uncertainty."""
    slope = last_n_year_slope(df, year_col, value_col)
    if slope is None:
        if use_swahili():
            return "Historia haitoshi kutoa mwelekeo wa makadirio unaoaminika."
        return "There is not enough history to describe a reliable forecast direction."

    status, _ = momentum_status(slope, value_col)
    if use_swahili():
        sw_direction = {
            "Improving": "kuimarika",
            "Declining": "kushuka",
            "Stable": "kubaki karibu bila mabadiliko makubwa",
        }[status]
        return (
            f"Ikiwa mwenendo wa sasa utaendelea, {localize_phrase(context)} inatarajiwa "
            f"{sw_direction} kwenye {localize_phrase(label)} katika miaka miwili ijayo. "
            "Haya ni makadirio ya mipango, si matokeo rasmi ya NECTA."
        )

    direction = {
        "Improving": "improve",
        "Declining": "weaken",
        "Stable": "remain broadly stable",
    }[status]
    return (
        f"If the recent pattern continues, {context} is expected to {direction} on "
        f"{label} over the next two years. This is a planning estimate, not an "
        "official NECTA result."
    )


def _change_finding(
    label,
    previous_value,
    latest_value,
    lower_is_good,
    previous_year,
    latest_year,
    suffix="",
):
    """Build a concise year-over-year finding for one metric."""
    change = latest_value - previous_value
    improved = change < 0 if lower_is_good else change > 0
    if abs(change) < 0.01:
        direction = "remained broadly stable"
        implication = "Maintain current support and monitor the next result."
        sw_direction = "ilibaki karibu bila mabadiliko makubwa"
        sw_implication = "Endeleza msaada wa sasa na fuatilia matokeo yajayo."
    elif improved:
        direction = "improved"
        implication = "Protect the practices associated with this improvement."
        sw_direction = "iliimarika"
        sw_implication = "Linda mbinu zilizochangia uimarishaji huu."
    else:
        direction = "weakened"
        implication = "Review the affected teaching and learner-support priorities."
        sw_direction = "ilidhoofika"
        sw_implication = "Pitia vipaumbele vya ufundishaji na msaada kwa wanafunzi."
    if use_swahili():
        return (
            f"{localize_phrase(label)} {sw_direction} kutoka {previous_value:.2f}{suffix} mwaka {int(previous_year)} "
            f"hadi {latest_value:.2f}{suffix} mwaka {int(latest_year)}. {sw_implication}"
        )
    return (
        f"{label} {direction} from {previous_value:.2f}{suffix} in {int(previous_year)} to "
        f"{latest_value:.2f}{suffix} in {int(latest_year)}. {implication}"
    )


def national_key_findings(school_df, subject_df, artifacts=None):
    """Return up to five national performance, priority, and forecast findings."""
    findings = []
    years = sorted(school_df.get("year", pd.Series(dtype=float)).dropna().unique())
    if len(years) >= 2:
        previous_year, latest_year = years[-2], years[-1]
        gpa_by_year = (
            school_df.groupby("year", as_index=False)["gpa"]
            .mean()
            .dropna(subset=["gpa"])
            .set_index("year")["gpa"]
        )
        if previous_year in gpa_by_year and latest_year in gpa_by_year:
            findings.append(
                _change_finding(
                    "National GPA",
                    gpa_by_year.loc[previous_year],
                    gpa_by_year.loc[latest_year],
                    True,
                    previous_year,
                    latest_year,
                )
            )

        pass_by_year = weighted_pass_rate_by_group(school_df, ["year"]).set_index("year")
        if previous_year in pass_by_year.index and latest_year in pass_by_year.index:
            findings.append(
                _change_finding(
                    "Candidate-weighted pass rate",
                    pass_by_year.loc[previous_year, "pass_rate"],
                    pass_by_year.loc[latest_year, "pass_rate"],
                    False,
                    previous_year,
                    latest_year,
                    "%",
                )
            )

        region_history = (
            school_df[
                school_df["region"].notna()
                & school_df["gpa"].notna()
                & (school_df["region"].astype(str).str.upper() != "UNKNOWN")
            ]
            .groupby(["year", "region"], as_index=False)["gpa"]
            .mean()
        )
        latest_regions = region_history[region_history["year"] == latest_year].sort_values("gpa")
        if not latest_regions.empty:
            strongest = latest_regions.iloc[0]
            weakest = latest_regions.iloc[-1]
            comparison = region_history[region_history["year"].isin([previous_year, latest_year])]
            pivot = comparison.pivot(index="region", columns="year", values="gpa").dropna()
            improved_count = int((pivot[latest_year] < pivot[previous_year]).sum()) if not pivot.empty else 0
            if use_swahili():
                findings.append(
                    f"Mikoa {improved_count} kati ya {len(pivot)} inayolinganishwa iliimarisha GPA mwaka "
                    f"{int(latest_year)}. {strongest['region']} ilikuwa na ufaulu bora zaidi kwa "
                    f"{strongest['gpa']:.2f}, wakati {weakest['region']} inahitaji kipaumbele "
                    f"kwa GPA {weakest['gpa']:.2f}."
                )
            else:
                findings.append(
                    f"{improved_count} of {len(pivot)} comparable regions improved GPA in "
                    f"{int(latest_year)}. {strongest['region']} was strongest at "
                    f"{strongest['gpa']:.2f}, while {weakest['region']} needs priority "
                    f"attention at {weakest['gpa']:.2f}."
                )

        latest_subjects = subject_df[subject_df["year"] == latest_year]
        strength = subject_strength_table(latest_subjects)
        if not strength.empty:
            strongest_subject = strength.iloc[0]
            weakest_subject = strength.iloc[-1]
            if use_swahili():
                findings.append(
                    f"{strongest_subject['subject_name']} ndilo somo lenye nguvu zaidi "
                    f"(GPA {strongest_subject['subject_gpa']:.2f}); "
                    f"{weakest_subject['subject_name']} ndilo dhaifu zaidi "
                    f"(GPA {weakest_subject['subject_gpa']:.2f}) na linahitaji msaada "
                    "wa mtaala na ufundishaji uliolengwa."
                )
            else:
                findings.append(
                    f"{strongest_subject['subject_name']} was the strongest subject "
                    f"(GPA {strongest_subject['subject_gpa']:.2f}); "
                    f"{weakest_subject['subject_name']} was weakest "
                    f"(GPA {weakest_subject['subject_gpa']:.2f}) and should receive "
                    "targeted curriculum and teaching support."
                )

    if artifacts:
        gpa_forecast = artifacts.get("forecasts", {}).get("gpa", pd.DataFrame())
        pass_forecast = artifacts.get("forecasts", {}).get("pass_rate", pd.DataFrame())
        outlook_parts = []
        if not gpa_forecast.empty:
            gpa_years = gpa_forecast.groupby("year")["gpa"].mean().sort_index()
            gpa_change = gpa_years.iloc[-1] - gpa_years.iloc[0]
            gpa_direction = "improve" if gpa_change < -0.01 else "weaken" if gpa_change > 0.01 else "remain stable"
            if use_swahili():
                gpa_direction = "kuimarika" if gpa_change < -0.01 else "kudhoofika" if gpa_change > 0.01 else "kubaki imetulia"
                outlook_parts.append(f"GPA inatarajiwa {gpa_direction}")
            else:
                outlook_parts.append(f"GPA is expected to {gpa_direction}")
        if not pass_forecast.empty:
            pass_years = pass_forecast.groupby("year")["pass_rate"].mean().sort_index()
            pass_change = pass_years.iloc[-1] - pass_years.iloc[0]
            pass_direction = "improve" if pass_change > 0.1 else "decline" if pass_change < -0.1 else "remain stable"
            if use_swahili():
                pass_direction = "kuimarika" if pass_change > 0.1 else "kushuka" if pass_change < -0.1 else "kubaki imetulia"
                outlook_parts.append(f"kiwango cha ufaulu kinatarajiwa {pass_direction}")
            else:
                outlook_parts.append(f"pass rate is expected to {pass_direction}")
        if outlook_parts:
            if use_swahili():
                findings.append(
                    "Makadirio yaliyohifadhiwa ya miaka miwili yanaonyesha kuwa "
                    + " na ".join(outlook_parts)
                    + " ikiwa mwenendo wa karibuni utaendelea. Tumia hii kama ushahidi wa mipango, si matokeo rasmi."
                )
            else:
                findings.append(
                    "The saved two-year outlook suggests "
                    + " and ".join(outlook_parts)
                    + " if recent patterns continue. Treat this as planning evidence, not an official result."
                )
    return findings[:5]


def school_key_findings(school_history, subject_history, school_name):
    """Return school trend, risk, subject, and outlook findings."""
    if school_history.empty or not school_name:
        return []
    findings = []
    years = sorted(school_history["year"].dropna().unique())
    if len(years) >= 2:
        previous_year, latest_year = years[-2], years[-1]
        gpa = school_history.groupby("year")["gpa"].mean()
        if previous_year in gpa and latest_year in gpa:
            findings.append(
                _change_finding(
                    f"{school_name} GPA",
                    gpa.loc[previous_year],
                    gpa.loc[latest_year],
                    True,
                    previous_year,
                    latest_year,
                )
            )
        pass_rate = weighted_pass_rate_by_group(school_history, ["year"]).set_index("year")
        if previous_year in pass_rate.index and latest_year in pass_rate.index:
            findings.append(
                _change_finding(
                    "Pass rate",
                    pass_rate.loc[previous_year, "pass_rate"],
                    pass_rate.loc[latest_year, "pass_rate"],
                    False,
                    previous_year,
                    latest_year,
                    "%",
                )
            )

    latest_year = int(school_history["year"].max())
    latest_school = school_history[school_history["year"] == latest_year]
    if {"division_0", "sat"}.issubset(latest_school.columns):
        div0_rate = weighted_rate(latest_school["division_0"].sum(), latest_school["sat"].sum())
        if div0_rate is not None:
            action = (
                "Prioritize remedial and exam-readiness support."
                if div0_rate >= 15
                else "Continue monitoring while protecting current learner support."
            )
            if use_swahili():
                sw_action = (
                    "Tanguliza msaada wa marekebisho na utayari wa mitihani."
                    if div0_rate >= 15
                    else "Endelea kufuatilia huku ukilinda msaada wa sasa kwa wanafunzi."
                )
                findings.append(
                    f"Division 0 iliwakilisha {div0_rate:.1f}% ya watahiniwa mwaka {latest_year}. {sw_action}"
                )
            else:
                findings.append(
                    f"Division 0 represented {div0_rate:.1f}% of candidates in {latest_year}. {action}"
                )

    if not subject_history.empty:
        latest_subject_year = int(subject_history["year"].max())
        strength = subject_strength_table(
            subject_history[subject_history["year"] == latest_subject_year]
        )
        if not strength.empty:
            if use_swahili():
                findings.append(
                    f"{strength.iloc[0]['subject_name']} ndilo somo lenye nguvu zaidi, wakati "
                    f"{strength.iloc[-1]['subject_name']} ndilo dhaifu zaidi. Elekeza msaada wa somo "
                    "kwenye eneo dhaifu bila kuvuruga eneo lenye nguvu."
                )
            else:
                findings.append(
                    f"{strength.iloc[0]['subject_name']} was the strongest subject, while "
                    f"{strength.iloc[-1]['subject_name']} was weakest. Direct subject-level "
                    "support to the weaker area without disrupting the stronger one."
                )

    slope = last_n_year_slope(school_history, "year", "gpa")
    if slope is not None:
        status, _ = momentum_status(slope, "gpa")
        if use_swahili():
            findings.append(
                f"Mwenendo wa karibuni wa GPA ni {localize_phrase(status).lower()}. Makadirio ya miaka miwili "
                "yatumike kama ishara ya awali ya mipango, si matokeo yaliyohakikishwa."
            )
        else:
            findings.append(
                f"Recent GPA momentum is {status.lower()}. The two-year forecast should be used "
                "as an early planning signal rather than a guaranteed result."
            )
    return findings[:5]


def subject_key_findings(subject_history, latest_scope, context):
    """Return subject performance, volume, priority, and outlook findings."""
    if subject_history.empty:
        return []
    findings = []
    years = sorted(subject_history["year"].dropna().unique())
    if len(years) >= 2:
        previous_year, latest_year = years[-2], years[-1]
        gpa = subject_history.groupby("year")["subject_gpa"].mean()
        if previous_year in gpa and latest_year in gpa:
            findings.append(
                _change_finding(
                    f"{context} subject GPA",
                    gpa.loc[previous_year],
                    gpa.loc[latest_year],
                    True,
                    previous_year,
                    latest_year,
                )
            )
        pass_rate = (
            subject_history.groupby("year", as_index=False)
            .agg({"pass": "sum", "sat": "sum"})
        )
        pass_rate["pass_rate"] = pass_rate.apply(
            lambda row: weighted_rate(row["pass"], row["sat"]),
            axis=1,
        )
        pass_rate = pass_rate.set_index("year")
        if previous_year in pass_rate.index and latest_year in pass_rate.index:
            findings.append(
                _change_finding(
                    "Subject pass rate",
                    pass_rate.loc[previous_year, "pass_rate"],
                    pass_rate.loc[latest_year, "pass_rate"],
                    False,
                    previous_year,
                    latest_year,
                    "%",
                )
            )

    strength = subject_strength_table(latest_scope)
    if not strength.empty:
        if use_swahili():
            findings.append(
                f"{strength.iloc[0]['subject_name']} ndilo lenye nguvu zaidi kwenye muhtasari uliochaguliwa, "
                f"wakati {strength.iloc[-1]['subject_name']} linahitaji uingiliaji mkubwa zaidi wa kitaaluma."
            )
        else:
            findings.append(
                f"{strength.iloc[0]['subject_name']} is strongest in the selected snapshot, "
                f"while {strength.iloc[-1]['subject_name']} needs the most academic intervention."
            )
    if "sat" in latest_scope.columns and not latest_scope.empty:
        if use_swahili():
            findings.append(
                f"Majaribio ya somo {safe_int(latest_scope['sat'].sum()):,} yalifanyiwa tathmini "
                "kwenye muhtasari uliochaguliwa, hivyo idadi ya watahiniwa izingatiwe pamoja na GPA."
            )
        else:
            findings.append(
                f"{safe_int(latest_scope['sat'].sum()):,} subject entries were assessed in "
                "the selected snapshot, so candidate volume should be considered alongside GPA."
            )
    slope = last_n_year_slope(subject_history, "year", "subject_gpa")
    if slope is not None:
        status, _ = momentum_status(slope, "subject_gpa")
        if use_swahili():
            findings.append(
                f"Mwenendo wa karibuni wa GPA ya somo ni {localize_phrase(status).lower()}. Tumia makadirio kupanga "
                "msaada wa ufundishaji, si kama matokeo rasmi ya baadaye."
            )
        else:
            findings.append(
                f"Recent subject GPA momentum is {status.lower()}. Use the forecast to plan "
                "teaching support, not as an official future result."
            )
    return findings[:5]


def ranking_key_findings(
    top_schools,
    lowest_schools,
    improved_schools,
    declining_schools,
    top_subjects,
    lowest_subjects,
    ranking_year,
):
    """Return concise leaders, support priorities, and momentum findings."""
    findings = []
    if not top_schools.empty:
        leader = top_schools.iloc[0]
        if use_swahili():
            findings.append(
                f"{leader['school_name']} inaongoza upangaji wa shule mwaka {ranking_year} kwa GPA "
                f"{leader['gpa']:.2f}. Pitia mbinu zake kwa mafunzo yanayoweza kutumika kwingine."
            )
        else:
            findings.append(
                f"{leader['school_name']} leads the {ranking_year} school ranking with GPA "
                f"{leader['gpa']:.2f}. Review its practices for lessons that may transfer."
            )
    if not lowest_schools.empty:
        weakest = lowest_schools.iloc[0]
        if use_swahili():
            findings.append(
                f"{weakest['school_name']} ina GPA dhaifu zaidi iliyoonyeshwa kwa "
                f"{weakest['gpa']:.2f} na ipewe kipaumbele kwa uchunguzi wa msaada."
            )
        else:
            findings.append(
                f"{weakest['school_name']} records the weakest displayed GPA at "
                f"{weakest['gpa']:.2f} and should be prioritized for diagnostic support."
            )
    if not improved_schools.empty:
        improved = improved_schools.iloc[0]
        if use_swahili():
            findings.append(
                f"{improved['school_name']} iliimarika haraka zaidi ndani ya kipindi kilichochaguliwa "
                f"kwa mabadiliko ya GPA {improved['change']:+.2f}."
            )
        else:
            findings.append(
                f"{improved['school_name']} improved fastest over the selected window "
                f"with GPA change {improved['change']:+.2f}."
            )
    if not declining_schools.empty:
        declining = declining_schools.iloc[0]
        if use_swahili():
            findings.append(
                f"{declining['school_name']} inaonyesha kushuka zaidi kuliko zilizoonyeshwa "
                f"({declining['change']:+.2f} pointi za GPA) na inahitaji ufuatiliaji."
            )
        else:
            findings.append(
                f"{declining['school_name']} shows the steepest displayed decline "
                f"({declining['change']:+.2f} GPA points) and needs follow-up."
            )
    if not top_subjects.empty and not lowest_subjects.empty:
        if use_swahili():
            findings.append(
                f"{top_subjects.iloc[0]['subject_name']} ndilo somo lenye nguvu zaidi katika upangaji, "
                f"wakati {lowest_subjects.iloc[0]['subject_name']} ndilo dhaifu zaidi na linahitaji "
                "uangalizi wa mtaala."
            )
        else:
            findings.append(
                f"{top_subjects.iloc[0]['subject_name']} is the strongest ranked subject, "
                f"while {lowest_subjects.iloc[0]['subject_name']} is the weakest and needs "
                "curriculum attention."
            )
    return findings[:5]


def distribution_insight_text(df, label_col, value_col, context):
    """Describe the largest category and its share of a distribution."""
    if df.empty or not {label_col, value_col}.issubset(df.columns):
        if use_swahili():
            return f"Hakuna data ya mgawanyo kwa {localize_phrase(context)}."
        return f"No distribution data is available for {context}."

    temp = df.copy()
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce").fillna(0)
    total = temp[value_col].sum()
    if total <= 0:
        if use_swahili():
            return f"Hakuna idadi ya watahiniwa kwa {localize_phrase(context)}."
        return f"No candidate counts are available for {context}."

    largest = temp.sort_values(value_col, ascending=False).iloc[0]
    share = (largest[value_col] / total) * 100
    if use_swahili():
        return (
            f"{largest[label_col]} ndiyo kundi kubwa zaidi kwa {localize_phrase(context)}, ikiwa na "
            f"watahiniwa {safe_int(largest[value_col]):,} ({share:.1f}% ya jumla iliyoonyeshwa)."
        )
    return (
        f"{largest[label_col]} is the largest category for {context}, with "
        f"{safe_int(largest[value_col]):,} candidates ({share:.1f}% of the shown total)."
    )

def ranking_insight_text(df, name_col, value_col, label, metric, top_is_best=True):
    """Summarize the leader and spread in a displayed ranking."""
    if df.empty or not {name_col, value_col}.issubset(df.columns):
        if use_swahili():
            return f"Hakuna data ya upangaji kwa {localize_phrase(label).lower()}."
        return f"No ranking data is available for {label.lower()}."

    leader = df.iloc[0]
    tail = df.iloc[-1]
    if use_swahili():
        return (
            f"{leader[name_col]} inaongoza kwenye mwonekano huu wa {localize_phrase(label).lower()} kwa "
            f"{format_metric_value(leader[value_col], metric)}. Ndani ya kundi lililoonyeshwa, pengo hadi "
            f"{tail[name_col]} ni pointi {abs(leader[value_col] - tail[value_col]):.2f}."
        )
    return (
        f"{leader[name_col]} leads this {label.lower()} view with {format_metric_value(leader[value_col], metric)}. "
        f"Within the displayed group, the spread to {tail[name_col]} is "
        f"{abs(leader[value_col] - tail[value_col]):.2f} points."
    )

def school_vs_region_insight(school_history_df, region_history_df, metric, school_name, region_name):
    """Explain a selected school's latest standing against a region benchmark."""
    if school_history_df.empty or region_history_df.empty:
        if use_swahili():
            return "Ulinganisho wa kikanda haupatikani kwa sababu upande mmoja hauna data."
        return "Regional comparison is unavailable because one side has no data."

    latest_year = int(min(school_history_df["year"].max(), region_history_df["year"].max()))

    if metric == "pass_rate":
        school_latest_df = weighted_pass_rate_by_group(
            school_history_df[school_history_df["year"] == latest_year],
            ["year"]
        )
        school_latest = school_latest_df[metric].mean()
        region_latest_df = weighted_pass_rate_by_group(
            region_history_df[region_history_df["year"] == latest_year],
            ["year"]
        )
        region_latest = region_latest_df[metric].mean()
    else:
        school_latest = school_history_df[school_history_df["year"] == latest_year][metric].mean()
        region_latest = region_history_df[region_history_df["year"] == latest_year][metric].mean()

    if pd.isna(school_latest) or pd.isna(region_latest):
        if use_swahili():
            return "Ulinganisho wa kikanda haupatikani kwa sababu thamani za karibuni hazijakamilika."
        return "Regional comparison is unavailable because the latest values are incomplete."

    gap = abs(school_latest - region_latest)
    if lower_is_better(metric):
        standing = "above" if school_latest < region_latest else "below" if school_latest > region_latest else "level with"
    else:
        standing = "above" if school_latest > region_latest else "below" if school_latest < region_latest else "level with"

    if use_swahili():
        sw_standing = {
            "above": "juu ya",
            "below": "chini ya",
            "level with": "sawa na"
        }.get(standing, standing)
        return (
            f"Mwaka {latest_year}, {school_name} iko {sw_standing} wastani wa mkoa wa {region_name} kwenye "
            f"{localize_phrase(metric_display_name(metric))} kwa tofauti ya pointi {gap:.2f} "
            f"({format_metric_value(school_latest, metric)} dhidi ya {format_metric_value(region_latest, metric)})."
        )

    return (
        f"In {latest_year}, {school_name} is {standing} the {region_name} regional benchmark on "
        f"{metric_display_name(metric)} by {gap:.2f} points "
        f"({format_metric_value(school_latest, metric)} vs {format_metric_value(region_latest, metric)})."
    )

def risk_scatter_data(df):
    """Aggregate school risk, attendance, pass-rate, and GPA scatter inputs."""
    required = {"school_name", "region", "gpa", "sat", "regist", "division_0", "total_passed_candidates"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame()

    temp = df.copy()
    temp = temp[temp["sat"] > 0].copy()
    if temp.empty:
        return pd.DataFrame()

    temp["division_0_rate"] = (temp["division_0"] / temp["sat"]) * 100
    temp["attendance_rate"] = (temp["sat"] / temp["regist"].where(temp["regist"] != 0)) * 100

    out = (
        temp.groupby(["school_name", "region"], as_index=False)
        .agg({
            "gpa": "mean",
            "total_passed_candidates": "sum",
            "division_0": "sum",
            "regist": "sum",
            "sat": "sum"
        })
    )
    out["pass_rate"] = out.apply(
        lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
        axis=1
    )
    out["division_0_rate"] = out.apply(
        lambda row: weighted_rate(row["division_0"], row["sat"]),
        axis=1
    )
    out["attendance_rate"] = out.apply(
        lambda row: weighted_rate(row["sat"], row["regist"]),
        axis=1
    )
    return out.fillna(0)

def policy_summary_items(school_data, subject_data, risk_df, gap_info, attendance):
    """Build action-oriented national or filtered planning statements."""
    items = []

    if gap_info:
        if use_swahili():
            items.append(
                f"Pengo la usawa wa kikanda: {gap_info['best_region']} inaongoza {gap_info['worst_region']} kwa "
                f"pointi {gap_info['gap']:.2f} za GPA, hivyo msaada ulenge mkoa dhaifu zaidi."
            )
        else:
            items.append(
                f"Regional equity gap: {gap_info['best_region']} leads {gap_info['worst_region']} by "
                f"{gap_info['gap']:.2f} GPA points, so support should focus on the weaker region."
            )

    if risk_df is not None and not risk_df.empty:
        high_risk_count = len(risk_df)
        worst = risk_df.iloc[0]
        if use_swahili():
            items.append(
                f"Kipaumbele cha urejeshaji wa ufaulu: shule {high_risk_count} zimevuka kiwango cha hatari cha Division 0; "
                f"{worst['school_name']} iko juu zaidi kwa {worst['div0_rate']:.1f}%."
            )
        else:
            items.append(
                f"School recovery priority: {high_risk_count} schools exceed the Division 0 risk threshold; "
                f"{worst['school_name']} is highest at {worst['div0_rate']:.1f}%."
            )
    else:
        if use_swahili():
            items.append("Hatari ya Division 0 iko chini ya kiwango kilichochaguliwa kwa vichujio vya sasa.")
        else:
            items.append("Division 0 risk is controlled under the selected threshold for the current filters.")

    if attendance is not None:
        if use_swahili():
            items.append(
                f"Ufanisi wa mahudhurio ni wastani wa {attendance:.1f}%; thamani chini ya 90% zinahitaji ukaguzi wa upatikanaji na ubaki shuleni."
            )
        else:
            items.append(
                f"Attendance efficiency averages {attendance:.1f}%; values below 90% should trigger access and retention checks."
            )

    strength_df = subject_strength_table(subject_data)
    if not strength_df.empty:
        weak_subject = strength_df.tail(1).iloc[0]
        strong_subject = strength_df.head(1).iloc[0]
        if use_swahili():
            items.append(
                f"Uelekezaji wa masomo: {weak_subject['subject_name']} linahitaji uangalizi "
                f"(GPA {weak_subject['subject_gpa']:.2f}), wakati {strong_subject['subject_name']} ndilo eneo lenye nguvu zaidi "
                f"(GPA {strong_subject['subject_gpa']:.2f})."
            )
        else:
            items.append(
                f"Subject targeting: {weak_subject['subject_name']} needs attention "
                f"(GPA {weak_subject['subject_gpa']:.2f}), while {strong_subject['subject_name']} is the strongest area "
                f"(GPA {strong_subject['subject_gpa']:.2f})."
            )

    pass_trend = weighted_pass_rate_by_group(school_data, ["year"]).sort_values("year")
    slope = last_n_year_slope(pass_trend, "year", "pass_rate")
    if slope is not None:
        status, _ = momentum_status(slope, "pass_rate")
        if use_swahili():
            items.append(
                f"Mwenendo wa mfumo ni {localize_phrase(status).lower()} ukiwa na mteremko wa kiwango cha ufaulu wa miaka 3 ya mwisho wa pointi {slope:+.2f} kwa mwaka."
            )
        else:
            items.append(f"System momentum is {status.lower()} with a last-3-year pass-rate slope of {slope:+.2f} points/year.")

    return items

def render_policy_summary(items, title=None):
    """Render policy statements as a concise accessible list."""
    if not items:
        items = ["Hakuna muhtasari wa kisera kwa vichujio vya sasa."] if use_swahili() else ["No policy summary is available for the current filters."]

    list_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in items)
    title = title or (
        "Muhtasari wa Taarifa za Kisera"
        if use_swahili()
        else "Policy Intelligence Summary"
    )
    st.markdown(
        f"""
        <div class="policy-panel">
            <h4>{title}</h4>
            <ul>{list_items}</ul>
        </div>
        """,
        unsafe_allow_html=True
    )

