"""Calculate hypothetical 2032 examination-demand and priority scenarios."""

from __future__ import annotations

import numpy as np
import pandas as pd

from decision_features import require_columns
from policy_config import (
    FUTURE_PRIORITY_WEIGHTS,
    SCENARIOS,
    TARGET_YEAR,
    demand_category,
)


POLICY_SCHOOL_COLUMNS = {
    "school_id",
    "school_name",
    "region",
    "year",
    "sat",
}


def normalize_demand_pressure(series, maximum_reference_ratio=2.0):
    """Scale ratios consistently so 1.0=50 and 2.0 or more=100."""
    values = pd.to_numeric(series, errors="coerce")
    return (values / maximum_reference_ratio * 100).clip(0, 100)


def _school_candidate_history(school_df):
    """Build one candidate-count row per school and examination year."""
    require_columns(school_df, POLICY_SCHOOL_COLUMNS, "School dataset")
    source = school_df.copy()
    source["year"] = pd.to_numeric(source["year"], errors="coerce")
    source["sat"] = pd.to_numeric(source["sat"], errors="coerce")
    source = source[
        source["school_id"].notna()
        & source["year"].notna()
        & source["sat"].notna()
        & source["region"].notna()
        & source["region"].astype("string").str.upper().ne("UNKNOWN")
    ].copy()
    return (
        source.sort_values(["school_id", "year"])
        .groupby(["school_id", "year"], as_index=False)
        .agg(
            school_name=("school_name", "last"),
            region=("region", "last"),
            candidates=("sat", "sum"),
        )
    )


def build_policy_baselines(school_df, decision_artifacts):
    """Return school and regional observed-derived baselines for simulation."""
    history = _school_candidate_history(school_df)
    if history.empty:
        return pd.DataFrame(), pd.DataFrame()

    latest = (
        history.sort_values(["school_id", "year"])
        .groupby("school_id", as_index=False)
        .tail(1)
        .rename(
            columns={
                "year": "baseline_year",
                "candidates": "current_candidates",
            }
        )
    )
    historical = (
        history.groupby("school_id", as_index=False)
        .agg(
            historical_average_candidates=("candidates", "mean"),
            evidence_years=("year", "nunique"),
        )
    )
    school_baseline = (
        latest.merge(historical, on="school_id", how="left")
        .merge(
            decision_artifacts["school_priority"][
                ["school_id", "priority_rank", "priority_score", "priority_category"]
            ],
            on="school_id",
            how="inner",
        )
        .merge(
            decision_artifacts["school_risk"][
                ["school_id", "risk_score", "risk_level"]
            ],
            on="school_id",
            how="inner",
        )
    )

    region_history = (
        history.groupby(["region", "year"], as_index=False)["candidates"]
        .sum()
    )
    region_latest = (
        region_history.sort_values(["region", "year"])
        .groupby("region", as_index=False)
        .tail(1)
        .rename(
            columns={
                "year": "baseline_year",
                "candidates": "current_candidates",
            }
        )
    )
    region_historical = (
        region_history.groupby("region", as_index=False)
        .agg(
            historical_average_candidates=("candidates", "mean"),
            evidence_years=("year", "nunique"),
        )
    )
    regional_baseline = (
        region_latest.merge(region_historical, on="region", how="left")
        .merge(
            decision_artifacts["regional_priority"][
                ["region", "priority_rank", "priority_score", "priority_category"]
            ],
            on="region",
            how="inner",
        )
        .merge(
            decision_artifacts["regional_risk"][
                ["region", "risk_score", "risk_level"]
            ],
            on="region",
            how="inner",
        )
    )
    return school_baseline, regional_baseline


def _simulate_entity(baseline, scenario_id, entity_type):
    """Apply one growth scenario and future-priority formula to an entity table."""
    scenario = SCENARIOS[scenario_id]
    growth_rate = scenario["growth_rate"]
    simulated = baseline.copy()
    simulated["scenario_id"] = scenario_id
    simulated["scenario_name"] = scenario["scenario_name"]
    simulated["growth_pct"] = growth_rate * 100
    simulated["target_year"] = TARGET_YEAR
    simulated["projected_candidates"] = (
        simulated["current_candidates"] * (1 + growth_rate)
    )
    simulated["candidate_increase"] = (
        simulated["projected_candidates"] - simulated["current_candidates"]
    )
    simulated["demand_pressure_ratio"] = (
        simulated["projected_candidates"]
        / simulated["historical_average_candidates"].replace(0, np.nan)
    )
    simulated["demand_pressure_index"] = normalize_demand_pressure(
        simulated["demand_pressure_ratio"]
    )
    simulated["demand_category"] = simulated["demand_pressure_index"].map(
        demand_category
    )
    simulated["future_priority_score"] = (
        FUTURE_PRIORITY_WEIGHTS["risk_score"] * simulated["risk_score"]
        + FUTURE_PRIORITY_WEIGHTS["priority_score"] * simulated["priority_score"]
        + FUTURE_PRIORITY_WEIGHTS["demand_pressure_index"]
        * simulated["demand_pressure_index"]
    ).clip(0, 100)
    simulated["future_priority_rank"] = (
        simulated["future_priority_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    simulated["rank_change"] = (
        simulated["priority_rank"] - simulated["future_priority_rank"]
    )
    simulated["entity_type"] = entity_type
    simulated["data_origin"] = "synthetic"
    simulated["scenario_type"] = "hypothetical_policy_scenario"
    return simulated


def build_policy_scenarios(school_df, decision_artifacts):
    """Return summary, regional, school, and priority-shift scenario outputs."""
    school_baseline, regional_baseline = build_policy_baselines(
        school_df,
        decision_artifacts,
    )
    if school_baseline.empty or regional_baseline.empty:
        return {
            "summary": pd.DataFrame(),
            "regions": pd.DataFrame(),
            "schools": pd.DataFrame(),
            "priority_shift": pd.DataFrame(),
        }

    school_outputs = []
    regional_outputs = []
    summaries = []
    priority_shifts = []
    for scenario_id in SCENARIOS:
        schools = _simulate_entity(school_baseline, scenario_id, "school")
        regions = _simulate_entity(regional_baseline, scenario_id, "region")
        school_outputs.append(schools)
        regional_outputs.append(regions)

        high_risk_regions = int(
            regions["demand_category"].isin(["High", "Critical"]).sum()
        )
        summaries.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": SCENARIOS[scenario_id]["scenario_name"],
                "growth_pct": SCENARIOS[scenario_id]["growth_rate"] * 100,
                "target_year": TARGET_YEAR,
                "current_candidates": float(schools["current_candidates"].sum()),
                "projected_candidates": float(
                    schools["projected_candidates"].sum()
                ),
                "candidate_increase": float(schools["candidate_increase"].sum()),
                "high_risk_regions": high_risk_regions,
                "school_rank_increases": int(schools["rank_change"].gt(0).sum()),
                "region_rank_increases": int(regions["rank_change"].gt(0).sum()),
                "data_origin": "synthetic",
                "scenario_type": "hypothetical_policy_scenario",
            }
        )

        school_shift = schools[
            [
                "scenario_id",
                "scenario_name",
                "entity_type",
                "school_id",
                "school_name",
                "region",
                "priority_rank",
                "future_priority_rank",
                "rank_change",
                "risk_score",
                "priority_score",
                "demand_pressure_index",
                "future_priority_score",
                "data_origin",
                "scenario_type",
            ]
        ].copy()
        region_shift = regions[
            [
                "scenario_id",
                "scenario_name",
                "entity_type",
                "region",
                "priority_rank",
                "future_priority_rank",
                "rank_change",
                "risk_score",
                "priority_score",
                "demand_pressure_index",
                "future_priority_score",
                "data_origin",
                "scenario_type",
            ]
        ].copy()
        region_shift["school_id"] = ""
        region_shift["school_name"] = region_shift["region"]
        priority_shifts.extend([school_shift, region_shift[school_shift.columns]])

    schools = pd.concat(school_outputs, ignore_index=True)
    regions = pd.concat(regional_outputs, ignore_index=True)
    summary = pd.DataFrame(summaries)
    priority_shift = pd.concat(priority_shifts, ignore_index=True)

    school_columns = [
        "scenario_id",
        "scenario_name",
        "target_year",
        "school_id",
        "school_name",
        "region",
        "baseline_year",
        "current_candidates",
        "historical_average_candidates",
        "projected_candidates",
        "candidate_increase",
        "growth_pct",
        "demand_pressure_ratio",
        "demand_pressure_index",
        "demand_category",
        "risk_score",
        "risk_level",
        "priority_score",
        "priority_category",
        "priority_rank",
        "future_priority_score",
        "future_priority_rank",
        "rank_change",
        "evidence_years",
        "data_origin",
        "scenario_type",
    ]
    region_columns = [
        "scenario_id",
        "scenario_name",
        "target_year",
        "region",
        "baseline_year",
        "current_candidates",
        "historical_average_candidates",
        "projected_candidates",
        "candidate_increase",
        "growth_pct",
        "demand_pressure_ratio",
        "demand_pressure_index",
        "demand_category",
        "risk_score",
        "risk_level",
        "priority_score",
        "priority_category",
        "priority_rank",
        "future_priority_score",
        "future_priority_rank",
        "rank_change",
        "evidence_years",
        "data_origin",
        "scenario_type",
    ]
    return {
        "summary": summary,
        "regions": regions[region_columns].sort_values(
            ["scenario_id", "demand_pressure_index"],
            ascending=[True, False],
        ),
        "schools": schools[school_columns].sort_values(
            ["scenario_id", "demand_pressure_index"],
            ascending=[True, False],
        ),
        "priority_shift": priority_shift.sort_values(
            ["scenario_id", "entity_type", "rank_change"],
            ascending=[True, True, False],
        ),
    }
