"""Load, validate, and normalize the CSEE dashboard datasets."""

import pandas as pd
import streamlit as st
from pathlib import Path
import runpy


DATA_DIR = Path(__file__).resolve().parent
SCRAPING_DIR = DATA_DIR.parent / "scraping"
COMBINER_SCRIPT = SCRAPING_DIR / "combined_data.py"

SCHOOL_COMBINED_FILE = DATA_DIR / "school_combined_2016_2025_national.csv"
SUBJECT_COMBINED_FILE = DATA_DIR / "subject_combined_2016_2025_national.csv"

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

UNKNOWN_REGION = "UNKNOWN"


class DashboardDataError(Exception):
    """Base exception for data errors that can be shown safely in the UI."""


class DataLoadError(DashboardDataError):
    """Raised when a dashboard data file cannot be read."""


class DataSchemaError(DashboardDataError):
    """Raised when a dashboard dataset is missing required columns."""


def validate_required_columns(df, required_columns, dataset_name):
    """Raise DataSchemaError when a loaded dataset lacks dashboard fields."""
    missing_columns = sorted(set(required_columns) - set(df.columns))
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise DataSchemaError(
            f"{dataset_name} dataset is missing required columns: {missing_text}"
        )


def read_dashboard_csv(file_path, dtype, dataset_name):
    """Read one dashboard CSV and convert parser/encoding failures to DataLoadError."""
    try:
        return pd.read_csv(
            file_path,
            dtype=dtype,
            low_memory=False,
        )
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise DataLoadError(
            f"Unable to read {dataset_name} data file '{file_path.name}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def normalize_region(region):
    """Normalize one region label while preserving unmatched source values."""
    region = str(region).strip().upper()
    if "DAR" in region:
        return "DAR ES SALAAM"
    return region


def normalize_region_series(series):
    """Vectorized region normalization used while loading large CSV files."""
    normalized = series.astype("string").str.strip().str.upper()
    return normalized.mask(
        normalized.str.contains("DAR", na=False),
        "DAR ES SALAAM",
    )


def ensure_national_combined_files():
    """Ensure both national files exist, rebuilding them when source files allow."""
    if SCHOOL_COMBINED_FILE.exists() and SUBJECT_COMBINED_FILE.exists():
        return

    missing_files = [
        path.name
        for path in (SCHOOL_COMBINED_FILE, SUBJECT_COMBINED_FILE)
        if not path.exists()
    ]
    if not COMBINER_SCRIPT.exists():
        raise DataLoadError(
            "Required dashboard data files are missing "
            f"({', '.join(missing_files)}), and the CSEE combiner is unavailable: "
            f"{COMBINER_SCRIPT}"
        )

    try:
        runpy.run_path(str(COMBINER_SCRIPT), run_name="__main__")
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise DataLoadError(
            "Unable to rebuild the missing dashboard data files "
            f"({', '.join(missing_files)}): {type(exc).__name__}: {exc}"
        ) from exc

    still_missing = [
        path.name
        for path in (SCHOOL_COMBINED_FILE, SUBJECT_COMBINED_FILE)
        if not path.exists()
    ]
    if still_missing:
        raise DataLoadError(
            "The dashboard data rebuild completed without producing required files: "
            f"{', '.join(still_missing)}"
        )


@st.cache_resource(show_spinner="Loading the national CSEE dataset...")
def _load_data_strict():
    """Load validated national data or raise a controlled dashboard data error."""
    ensure_national_combined_files()

    school_df = read_dashboard_csv(
        SCHOOL_COMBINED_FILE,
        SCHOOL_TEXT_DTYPES,
        "school",
    )
    subject_df = read_dashboard_csv(
        SUBJECT_COMBINED_FILE,
        SUBJECT_TEXT_DTYPES,
        "subject",
    )

    validate_required_columns(school_df, SCHOOL_REQUIRED_COLUMNS, "School")
    validate_required_columns(subject_df, SUBJECT_REQUIRED_COLUMNS, "Subject")

    for col in ["school_name", "region", "letter"]:
        if col in school_df.columns:
            school_df[col] = school_df[col].astype("string").str.strip()

    for col in ["school_name", "region", "letter", "subject_code", "subject_name"]:
        if col in subject_df.columns:
            subject_df[col] = subject_df[col].astype("string").str.strip()

    if "region" in school_df.columns:
        school_df["region"] = normalize_region_series(school_df["region"])
    if "region" in subject_df.columns:
        subject_df["region"] = normalize_region_series(subject_df["region"])

    school_numeric_cols = [
        "year", "gpa", "regist", "absent", "sat", "withheld", "no_ca", "clean",
        "total_passed_candidates", "division_1", "division_2", "division_3",
        "division_4", "division_0"
    ]
    for col in school_numeric_cols:
        if col in school_df.columns:
            school_df[col] = pd.to_numeric(school_df[col], errors="coerce")

    subject_numeric_cols = [
        "year", "registered", "sat", "no_ca", "withheld", "clean", "pass", "subject_gpa"
    ]
    for col in subject_numeric_cols:
        if col in subject_df.columns:
            subject_df[col] = pd.to_numeric(subject_df[col], errors="coerce")

    if {"total_passed_candidates", "sat"}.issubset(school_df.columns):
        # Pass rate is candidate-weighted: each passing candidate contributes equally.
        sat_denominator = school_df["sat"].where(school_df["sat"] != 0)
        school_df["pass_rate"] = (
            school_df["total_passed_candidates"] /
            sat_denominator
        ) * 100
        school_df["pass_rate"] = school_df["pass_rate"].fillna(0)
    else:
        school_df["pass_rate"] = 0

    if {"pass", "sat"}.issubset(subject_df.columns):
        sat_denominator = subject_df["sat"].where(subject_df["sat"] != 0)
        subject_df["pass_rate"] = (
            subject_df["pass"] /
            sat_denominator
        ) * 100
        subject_df["pass_rate"] = subject_df["pass_rate"].fillna(0)
    else:
        subject_df["pass_rate"] = 0

    return school_df, subject_df


def empty_dashboard_data():
    """Return schema-compatible empty frames for a safe UI fallback."""
    school_columns = sorted(
        SCHOOL_REQUIRED_COLUMNS
        | set(SCHOOL_TEXT_DTYPES)
        | {
            "regist", "absent", "withheld", "no_ca", "clean",
            "division_1", "division_2", "division_3", "division_4",
            "division_0", "pass_rate",
        }
    )
    subject_columns = sorted(
        SUBJECT_REQUIRED_COLUMNS
        | set(SUBJECT_TEXT_DTYPES)
        | {"registered", "no_ca", "withheld", "clean", "pass_rate"}
    )
    return pd.DataFrame(columns=school_columns), pd.DataFrame(columns=subject_columns)


def load_data(strict=False, return_error=False):
    """Load dashboard data, returning safe empty frames unless strict mode is requested."""
    try:
        school_df, subject_df = _load_data_strict()
        error_message = None
    except DashboardDataError as exc:
        if strict:
            raise
        school_df, subject_df = empty_dashboard_data()
        error_message = str(exc)

    if return_error:
        return school_df, subject_df, error_message
    return school_df, subject_df


load_data.clear = _load_data_strict.clear


def build_options(school_df, subject_df):
    """Build sorted public filter options from the validated datasets."""
    if "region" in school_df.columns:
        region_series = school_df["region"].dropna().astype("string").str.strip()
        # UNKNOWN rows are retained in source data for auditability but are not
        # meaningful public region choices or regional chart series.
        all_regions = sorted(
            region_series[
                region_series.ne("")
                & region_series.str.upper().ne(UNKNOWN_REGION)
            ].unique().tolist()
        )
    else:
        all_regions = []
    all_years = sorted(school_df["year"].dropna().astype(int).unique().tolist()) if "year" in school_df.columns else []
    all_schools = sorted(school_df["school_name"].dropna().unique().tolist()) if "school_name" in school_df.columns else []
    all_subjects = sorted(subject_df["subject_name"].dropna().unique().tolist()) if "subject_name" in subject_df.columns else []
    return all_regions, all_years, all_schools, all_subjects
