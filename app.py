"""Configure and route the NECTA CSEE Streamlit decision-support application."""

from pathlib import Path
import sys

import streamlit as st


def add_google_site_verification():
    """Inject Google Search Console verification into Streamlit's HTML head."""
    verification_tag = '<meta name="google-site-verification" content="OYOchum_JhOFGE4Ey3FiwOiw3NRz84_Sk2j1UV5V_vY" />'
    index_path = Path(st.__file__).parent / "static" / "index.html"
    html = index_path.read_text(encoding="utf-8")

    if "google-site-verification" not in html:
        html = html.replace("<head>", f"<head>\n    {verification_tag}", 1)
        index_path.write_text(html, encoding="utf-8")


add_google_site_verification()

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
from styles import apply_styles, render_feedback_button, render_top_nav


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
render_feedback_button()

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
