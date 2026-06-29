"""Configure and route the NECTA CSEE Streamlit decision-support application."""

from pathlib import Path
import sys

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

st.set_page_config(
    page_title="NECTA CSEE Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from data_loader import build_options, load_data
from pages.dashboard import render_dashboard
from pages.policy_planning import render_policy_planning
from pages.rankings import render_rankings
from pages.school import render_school
from pages.subject import render_subject
from styles import apply_styles, render_top_nav


apply_styles()

school_df, subject_df, load_error = load_data(return_error=True)
if load_error:
    st.error("The NECTA dashboard data could not be loaded.")
    st.info(load_error)
    st.caption(
        "Check the combined CSV files or regenerate them from the CSEE scraping data, "
        "then restart the dashboard."
    )
    st.stop()

all_regions, all_years, all_schools, all_subjects = build_options(school_df, subject_df)

page_options = ["Dashboard", "School", "Subject", "Rankings", "2032 Policy Planning"]
language_options = ["English", "Kiswahili"]

page = st.query_params.get("page", "Dashboard")
language = st.query_params.get(
    "lang",
    st.session_state.get("chart_interpretation_language", "English"),
)

if isinstance(page, list):
    page = page[0]
if isinstance(language, list):
    language = language[0]
if page not in page_options:
    page = "Dashboard"
if language not in language_options:
    language = "English"

st.session_state["chart_interpretation_language"] = language
render_top_nav(page, language)

if page == "Dashboard":
    render_dashboard(school_df, subject_df, all_regions, all_years, all_subjects)
elif page == "School":
    render_school(school_df, subject_df, all_regions, all_years, all_schools)
elif page == "Subject":
    render_subject(subject_df, all_years, all_subjects)
elif page == "Rankings":
    render_rankings(school_df, subject_df, all_regions, all_years)
elif page == "2032 Policy Planning":
    render_policy_planning()
