"""Configuration for the offline 2032 policy-planning scenarios."""

from pathlib import Path


POLICY_ENGINE_VERSION = "1.0.0"
TARGET_YEAR = 2032
APP_DIR = Path(__file__).resolve().parent
POLICY_ARTIFACT_DIR = APP_DIR / "decision_artifacts"

SCENARIOS = {
    "A": {
        "scenario_name": "Conservative Growth",
        "growth_rate": 0.10,
    },
    "B": {
        "scenario_name": "Moderate Growth",
        "growth_rate": 0.25,
    },
    "C": {
        "scenario_name": "High Growth",
        "growth_rate": 0.40,
    },
}

POLICY_FILES = {
    "summary": "2032_policy_summary.csv",
    "regions": "2032_region_impacts.csv",
    "schools": "2032_school_impacts.csv",
    "priority_shift": "2032_priority_shift.csv",
}

FUTURE_PRIORITY_WEIGHTS = {
    "risk_score": 0.40,
    "priority_score": 0.40,
    "demand_pressure_index": 0.20,
}


def demand_category(score):
    """Map a normalized 0-100 demand score to a planning category."""
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Moderate"
    if score <= 80:
        return "High"
    return "Critical"
