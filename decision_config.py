"""Versioned assumptions and thresholds for offline decision-support engines."""

from pathlib import Path


DECISION_ENGINE_VERSION = "1.0.0"
APP_DIR = Path(__file__).resolve().parent
DECISION_ARTIFACT_DIR = APP_DIR / "decision_artifacts"

PRIORITY_WEIGHTS = {
    "severity": 0.50,
    "trend_decline": 0.30,
    "recoverability": 0.20,
}

RISK_WEIGHTS = {
    "pass_rate_decline": 0.40,
    "subject_failure": 0.30,
    "trend_instability": 0.30,
}

PRIORITY_FILES = {
    "school_priority": "priority_rankings.csv",
    "regional_priority": "regional_priority_rankings.csv",
}

RISK_FILES = {
    "school_risk": "school_risk_scores.csv",
    "regional_risk": "regional_risk_scores.csv",
}

INTERVENTION_FILE = "intervention_recommendations.csv"
MANIFEST_FILE = "decision_manifest.json"

INTERVENTION_RANGES = {
    "Mathematics Tutoring Program": (5, 12),
    "Laboratory Support Program": (2, 6),
    "Teacher Development Program": (3, 8),
    "Regional Support and Audit Program": (4, 10),
    "Targeted School Improvement Program": (3, 8),
    "Monitor and Maintain Support": (0, 2),
}

MATHEMATICS_SUBJECTS = {
    "BASIC MATHEMATICS",
    "ADDITIONAL MATHEMATICS",
    "MATHEMATICS",
}

SCIENCE_SUBJECTS = {
    "BIOLOGY",
    "CHEMISTRY",
    "PHYSICS",
    "AGRICULTURAL SCIENCE",
    "ENGINEERING SCIENCE",
}

WEAK_SUBJECT_GPA = 4.0
WEAK_SUBJECT_PASS_RATE = 50.0
MULTIPLE_WEAK_SUBJECT_COUNT = 3


def priority_category(score):
    """Map a 0-100 priority score to the approved intervention category."""
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def risk_level(score):
    """Map a 0-100 risk score to the approved school or region level."""
    if score <= 30:
        return "Safe"
    if score <= 60:
        return "Moderate"
    return "High"

