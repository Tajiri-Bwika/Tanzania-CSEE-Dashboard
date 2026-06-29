"""Generate reproducible offline CSEE trend and linear-projection CSV outputs."""

import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


DATA_DIR = Path(__file__).resolve().parent
SCRAPING_DIR = DATA_DIR.parent / "scraping"
COMBINER_SCRIPT = SCRAPING_DIR / "combined_data.py"

SCHOOL_FILE = DATA_DIR / "school_combined_2016_2025_national.csv"
SUBJECT_FILE = DATA_DIR / "subject_combined_2016_2025_national.csv"

SCHOOL_TEXT_DTYPES = {
    "school_id": "string",
    "school_name": "string",
    "region": "string",
    "letter": "string",
}

SUBJECT_TEXT_DTYPES = {
    **SCHOOL_TEXT_DTYPES,
    "subject_code": "string",
    "subject_name": "string",
    "competency_level": "string",
    "reg_rank": "string",
    "nat_rank": "string",
}


def ensure_national_combined_files():
    """Rebuild national CSVs through the scraper combiner when either is absent."""
    if SCHOOL_FILE.exists() and SUBJECT_FILE.exists():
        return
    runpy.run_path(str(COMBINER_SCRIPT), run_name="__main__")


def fit_linear_prediction(df, target_col, year=2026, min_points=2):
    """Fit a simple year trend and return one projected value or None."""
    model_df = df[["year", target_col]].dropna()
    if len(model_df) < min_points:
        return None

    x = model_df["year"].to_numpy().reshape(-1, 1)
    y = model_df[target_col].to_numpy()

    model = LinearRegression()
    model.fit(x, y)
    return model.predict(np.array([[year]]))[0]


def main():
    """Load national data and write regional, school, and subject analysis files."""
    ensure_national_combined_files()

    school = pd.read_csv(SCHOOL_FILE, dtype=SCHOOL_TEXT_DTYPES, low_memory=False)
    subject = pd.read_csv(SUBJECT_FILE, dtype=SUBJECT_TEXT_DTYPES, low_memory=False)

    for col in ["year", "gpa", "sat", "total_passed_candidates"]:
        if col in school.columns:
            school[col] = pd.to_numeric(school[col], errors="coerce")

    for col in ["year", "subject_gpa", "sat", "pass"]:
        if col in subject.columns:
            subject[col] = pd.to_numeric(subject[col], errors="coerce")

    # Candidate-weighted pass rates preserve the contribution of every learner.
    school["pass_rate"] = np.where(
        school["sat"] > 0,
        (school["total_passed_candidates"] / school["sat"]) * 100,
        np.nan,
    )

    valid_region_school = school[
        school["region"].notna()
        & (school["region"].astype("string").str.strip().str.upper() != "UNKNOWN")
    ].copy()

    region_year = (
        valid_region_school.groupby(["region", "year"], as_index=False)
        .agg(
            avg_gpa=("gpa", "mean"),
            total_sat=("sat", "sum"),
            total_passed=("total_passed_candidates", "sum"),
        )
    )
    region_year["pass_rate"] = np.where(
        region_year["total_sat"] > 0,
        (region_year["total_passed"] / region_year["total_sat"]) * 100,
        np.nan,
    )
    region_year.to_csv(DATA_DIR / "analysis_region_trend.csv", index=False)

    region_predictions = []
    for region, df in region_year.groupby("region"):
        pred_gpa = fit_linear_prediction(df, "avg_gpa")
        pred_pass = fit_linear_prediction(df, "pass_rate")
        if pred_gpa is None or pred_pass is None:
            continue

        region_predictions.append({
            "region": region,
            "year": 2026,
            "predicted_gpa": pred_gpa,
            "predicted_pass_rate": pred_pass,
        })

    prediction_df = pd.DataFrame(region_predictions)
    prediction_df.to_csv(DATA_DIR / "prediction_region_2026.csv", index=False)

    school_predictions = []
    for school_id, df in school.sort_values("year").groupby("school_id"):
        pred = fit_linear_prediction(df, "gpa", min_points=3)
        if pred is None:
            continue

        latest = df.sort_values("year").iloc[-1]
        school_predictions.append({
            "school_id": school_id,
            "school_name": latest["school_name"],
            "region": latest["region"],
            "predicted_gpa_2026": pred,
        })

    school_pred_df = pd.DataFrame(school_predictions)
    school_pred_df.to_csv(DATA_DIR / "prediction_school_gpa_2026.csv", index=False)

    subject_year = (
        subject.groupby(["subject_code", "subject_name", "year"], as_index=False)
        .agg(avg_gpa=("subject_gpa", "mean"))
    )

    subject_predictions = []
    for (subject_code, subject_name), df in subject_year.groupby(["subject_code", "subject_name"]):
        pred = fit_linear_prediction(df, "avg_gpa", min_points=3)
        if pred is None:
            continue

        subject_predictions.append({
            "subject_code": subject_code,
            "subject_name": subject_name,
            "predicted_gpa_2026": pred,
        })

    subject_pred_df = pd.DataFrame(subject_predictions)
    subject_pred_df.to_csv(DATA_DIR / "prediction_subject_gpa_2026.csv", index=False)

    print("\nAnalysis outputs")
    print(f"Region trend rows: {len(region_year):,}")
    print(f"Region predictions: {len(prediction_df):,}")
    print(f"School predictions: {len(school_pred_df):,}")
    print(f"Subject predictions: {len(subject_pred_df):,}")
    print("\nDONE.")


if __name__ == "__main__":
    main()
