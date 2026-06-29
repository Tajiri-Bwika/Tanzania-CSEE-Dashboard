"""Render school search, profile, benchmarking, trends, and projections."""

import pandas as pd
import plotly.express as px
import streamlit as st

from charts import (
    forecast_line_chart,
    polish_chart_legend,
    weighted_pass_rate_by_group,
    yoy_bar_chart,
)
from decision_artifacts import load_decision_artifacts
from decision_ui import render_school_decision_support
from filters import filter_school_data, filter_subject_data, resolve_school_name
from insights import (
    distribution_insight_text,
    forecast_interpretation_text,
    last_n_year_slope,
    momentum_status,
    render_momentum_indicator,
    school_key_findings,
    school_vs_region_insight,
    subject_strength_table,
    trend_insight_text,
)
from metrics import metric_display_name, school_kpi_values, weighted_rate
from styles import (
    note_box,
    render_chart_insight,
    render_insight_card,
    render_key_findings,
    render_measure_guide,
    render_page_hero,
    render_section_header,
    render_stat_strip,
    tr,
)

DIVISION_HISTORY_COLORS = {
    "Div I": "#2563EB",
    "Div II": "#0F766E",
    "Div III": "#D97706",
    "Div IV": "#DC2626",
}

DIVISION_FORECAST_COLORS = {
    "Div I": "#93C5FD",
    "Div II": "#5EEAD4",
    "Div III": "#FCD34D",
    "Div IV": "#FCA5A5",
}


def profile_status(value, good_limit, warning_limit, lower_is_good=False):
    """Map one KPI value to a neutral, good, warning, or danger status."""
    if value is None or pd.isna(value):
        return "neutral"
    if lower_is_good:
        if value <= good_limit:
            return "good"
        if value <= warning_limit:
            return "warning"
        return "danger"
    if value >= good_limit:
        return "good"
    if value >= warning_limit:
        return "warning"
    return "danger"


def render_school_profile_cards(school_df, subject_df, historical_school_df, school_name, all_years):
    """Render the latest school profile and decision-support signals."""
    if not school_name or historical_school_df.empty:
        return

    latest_year = int(historical_school_df["year"].max())
    render_section_header(
        tr("School Profile", "Wasifu wa Shule"),
        tr(
            "A compact performance identity for the selected school.",
            "Utambulisho mfupi wa ufaulu wa shule iliyochaguliwa.",
        ),
        str(latest_year),
    )

    latest_school_df = historical_school_df[historical_school_df["year"] == latest_year].copy()
    latest_gpa = latest_school_df["gpa"].mean() if "gpa" in latest_school_df.columns else None
    total_sat = latest_school_df["sat"].sum() if "sat" in latest_school_df.columns else 0
    total_passed = latest_school_df["total_passed_candidates"].sum() if "total_passed_candidates" in latest_school_df.columns else 0
    total_div0 = latest_school_df["division_0"].sum() if "division_0" in latest_school_df.columns else 0
    total_registered = latest_school_df["regist"].sum() if "regist" in latest_school_df.columns else 0

    latest_pass_rate = weighted_rate(total_passed, total_sat)
    division_0_rate = weighted_rate(total_div0, total_sat)
    attendance_rate = weighted_rate(total_sat, total_registered)

    school_region = None
    if "region" in latest_school_df.columns and not latest_school_df["region"].dropna().empty:
        school_region = latest_school_df["region"].dropna().iloc[0]

    benchmark_text = tr("Regional data unavailable", "Data ya mkoa haipatikani")
    benchmark_value = "N/A"
    benchmark_status = "neutral"
    if school_region and latest_gpa is not None and pd.notna(latest_gpa):
        region_latest_df = filter_school_data(
            school_df,
            regions=[school_region],
            years=latest_year
        )
        region_gpa = region_latest_df["gpa"].mean() if not region_latest_df.empty and "gpa" in region_latest_df.columns else None
        if region_gpa is not None and pd.notna(region_gpa):
            gap = latest_gpa - region_gpa
            benchmark_value = f"{abs(gap):.2f}"
            if gap < -0.01:
                benchmark_text = tr(
                    f"Better than {school_region} average GPA {region_gpa:.2f}",
                    f"Bora kuliko wastani wa GPA wa {school_region} {region_gpa:.2f}",
                )
                benchmark_status = "good"
            elif gap > 0.01:
                benchmark_text = tr(
                    f"Behind {school_region} average GPA {region_gpa:.2f}",
                    f"Nyuma ya wastani wa GPA wa {school_region} {region_gpa:.2f}",
                )
                benchmark_status = "danger"
            else:
                benchmark_text = tr(
                    f"Level with {school_region} average GPA {region_gpa:.2f}",
                    f"Sawa na wastani wa GPA wa {school_region} {region_gpa:.2f}",
                )
                benchmark_status = "warning"

    school_subject_history_df = filter_subject_data(
        subject_df,
        years=(min(all_years), max(all_years)),
        school=school_name,
        exact_school=True
    )
    if not school_subject_history_df.empty:
        latest_subject_year = int(school_subject_history_df["year"].max())
        latest_subject_df = school_subject_history_df[school_subject_history_df["year"] == latest_subject_year]
    else:
        latest_subject_df = school_subject_history_df

    subject_profile_df = subject_strength_table(latest_subject_df)
    strongest_subject = subject_profile_df.iloc[0] if not subject_profile_df.empty else None
    weakest_subject = subject_profile_df.iloc[-1] if not subject_profile_df.empty else None

    gpa_trend_df = (
        historical_school_df.groupby("year", as_index=False)["gpa"]
        .mean()
        .sort_values("year")
    )
    gpa_slope = last_n_year_slope(gpa_trend_df, "year", "gpa")
    momentum, momentum_badge = momentum_status(gpa_slope, "gpa")
    momentum_text = (
        tr("Not enough history", "Historia haitoshi")
        if gpa_slope is None
        else f"{tr('Last-3-year GPA slope', 'Mteremko wa GPA wa miaka 3 ya mwisho')} {gpa_slope:+.2f}/{tr('year', 'mwaka')}"
    )

    p1, p2, p3, p4 = st.columns(4)
    p5, p6, p7, p8 = st.columns(4)

    with p1:
        render_insight_card(
            tr("Latest GPA", "GPA ya Karibuni"),
            f"{latest_gpa:.2f}" if pd.notna(latest_gpa) else "N/A",
            tr(f"NECTA GPA in {latest_year}", f"GPA ya NECTA mwaka {latest_year}"),
            profile_status(latest_gpa, 2.5, 3.5, lower_is_good=True)
        )
    with p2:
        render_insight_card(
            tr("Latest Pass Rate", "Kiwango cha Ufaulu cha Karibuni"),
            f"{latest_pass_rate:.1f}%" if pd.notna(latest_pass_rate) else "N/A",
            tr(
                f"{int(total_passed):,} passed of {int(total_sat):,} sat",
                f"{int(total_passed):,} walifaulu kati ya {int(total_sat):,} waliofanya",
            ),
            profile_status(latest_pass_rate, 75, 50)
        )
    with p3:
        render_insight_card(
            tr("Latest Division 0 Rate", "Kiwango cha Karibuni cha Division 0"),
            f"{division_0_rate:.1f}%" if pd.notna(division_0_rate) else "N/A",
            tr(
                f"{int(total_div0):,} Division 0 of {int(total_sat):,} sat",
                f"{int(total_div0):,} Division 0 kati ya {int(total_sat):,} waliofanya",
            ),
            profile_status(division_0_rate, 5, 15, lower_is_good=True)
        )
    with p4:
        render_insight_card(
            tr("Attendance Efficiency", "Ufanisi wa Mahudhurio"),
            f"{attendance_rate:.1f}%" if pd.notna(attendance_rate) else "N/A",
            tr(
                f"{int(total_sat):,} sat of {int(total_registered):,} registered",
                f"{int(total_sat):,} walifanya kati ya {int(total_registered):,} waliosajiliwa",
            ),
            profile_status(attendance_rate, 90, 80)
        )
    with p5:
        render_insight_card(
            tr("Regional Benchmark", "Ulinganisho wa Mkoa"),
            benchmark_value,
            benchmark_text,
            benchmark_status
        )
    with p6:
        if strongest_subject is not None:
            render_insight_card(
                tr("Strongest Subject", "Somo Lenye Nguvu"),
                str(strongest_subject["subject_name"]),
                f"GPA {strongest_subject['subject_gpa']:.2f}, {tr('Pass Rate')} {strongest_subject['pass_rate']:.1f}%",
                "good"
            )
        else:
            render_insight_card(
                tr("Strongest Subject", "Somo Lenye Nguvu"),
                "N/A",
                tr("No subject records found", "Hakuna rekodi za masomo zilizopatikana"),
                "neutral",
            )
    with p7:
        if weakest_subject is not None:
            render_insight_card(
                tr("Weakest Subject", "Somo Dhaifu"),
                str(weakest_subject["subject_name"]),
                f"GPA {weakest_subject['subject_gpa']:.2f}, {tr('Pass Rate')} {weakest_subject['pass_rate']:.1f}%",
                profile_status(weakest_subject["subject_gpa"], 2.5, 3.5, lower_is_good=True)
            )
        else:
            render_insight_card(
                tr("Weakest Subject", "Somo Dhaifu"),
                "N/A",
                tr("No subject records found", "Hakuna rekodi za masomo zilizopatikana"),
                "neutral",
            )
    with p8:
        render_insight_card(
            tr("Last-3-Year Momentum", "Mwenendo wa Miaka 3 ya Mwisho"),
            momentum,
            momentum_text,
            momentum_badge
        )


def render_school(school_df, subject_df, all_regions, all_years, all_schools):
    """Render the interactive school performance workspace."""
    render_page_hero(
        tr("School Performance Workspace", "Sehemu ya Ufaulu wa Shule"),
        tr(
            "Inspect a school across its latest outcomes, historical trajectory, subject profile, regional benchmark, and forecast.",
            "Chunguza shule kwa matokeo ya karibuni, historia ya mwenendo, wasifu wa masomo, ulinganisho wa mkoa, na makadirio.",
        ),
        kicker=tr("Institution Analysis", "Uchambuzi wa Taasisi"),
        panel_title=tr("Available Schools", "Shule Zilizopo"),
        panel_value=f"{len(all_schools):,}",
        panel_subtext=tr(
            f"Historical coverage from {min(all_years)} to {max(all_years)}.",
            f"Historia ya data kuanzia {min(all_years)} hadi {max(all_years)}.",
        ),
    )
    render_measure_guide(include_forecast=True)

    render_section_header(
        tr("School Controls", "Vidhibiti vya Shule"),
        tr(
            "Search for a school and choose the snapshot year used for current-performance cards.",
            "Tafuta shule na chagua mwaka wa muhtasari unaotumika kwenye kadi za ufaulu wa sasa.",
        ),
        tr("Search + year", "Utafutaji + mwaka"),
    )

    f1, f2 = st.columns([1.8, 1.0])

    with f1:
        selected_school_search = st.text_input(
            tr("Search School", "Tafuta Shule"),
            placeholder=tr("Type school name", "Andika jina la shule"),
            key="school_search_bar"
        )

    with f2:
        selected_year = st.selectbox(
            tr("Year"),
            options=all_years,
            index=len(all_years) - 1,
            key="school_page_year"
        )

    resolved_school_name = resolve_school_name(selected_school_search, all_schools)

    if selected_school_search and not resolved_school_name:
        st.warning(tr(
            "No school matched your search. Try a clearer school name.",
            "Hakuna shule iliyolingana na utafutaji wako. Jaribu jina la shule lililo wazi zaidi.",
        ))
        filtered_school_df = school_df.iloc[0:0].copy()
        historical_school_df = school_df.iloc[0:0].copy()
    elif resolved_school_name:
        filtered_school_df = filter_school_data(
            school_df,
            years=selected_year,
            school=resolved_school_name,
            exact_school=True
        )
        historical_school_df = filter_school_data(
            school_df,
            years=(min(all_years), max(all_years)),
            school=resolved_school_name,
            exact_school=True
        )
        st.caption(tr(f"Selected school: {resolved_school_name}", f"Shule iliyochaguliwa: {resolved_school_name}"))
    else:
        st.info(tr("Type a school name to load the School page.", "Andika jina la shule ili kupakia ukurasa wa Shule."))
        filtered_school_df = school_df.iloc[0:0].copy()
        historical_school_df = school_df.iloc[0:0].copy()

    kpis = school_kpi_values(filtered_school_df)

    render_stat_strip([
        ("School GPA", kpis["avg_gpa_display"], "Lower is better"),
        ("Pass Rate", kpis["avg_pass_rate_display"], "Selected year"),
        ("Candidates Sat", kpis["total_sat_display"], "Exam sitters"),
        ("Candidates Passed", kpis["total_passed_display"], "Passed candidates"),
    ])

    render_school_profile_cards(
        school_df,
        subject_df,
        historical_school_df,
        resolved_school_name,
        all_years
    )
    render_school_decision_support(
        load_decision_artifacts(),
        resolved_school_name,
    )
    school_subject_history_df = (
        filter_subject_data(
            subject_df,
            years=(min(all_years), max(all_years)),
            school=resolved_school_name,
            exact_school=True,
        )
        if resolved_school_name
        else subject_df.iloc[0:0].copy()
    )
    render_key_findings(
        school_key_findings(
            historical_school_df,
            school_subject_history_df,
            resolved_school_name,
        ),
        title=tr("Key Findings", "Matokeo Muhimu"),
        subtitle=tr(
            "The selected school's latest movement, risk, strength, and next priority.",
            "Mabadiliko ya karibuni ya shule, hatari, nguvu, na kipaumbele kinachofuata.",
        ),
    )

    render_section_header(
        tr("School Trend Analysis", "Uchambuzi wa Mwenendo wa Shule"),
        tr(
            f"Long-range charts always show {min(all_years)} to {max(all_years)} and do not change with the snapshot-year filter.",
            f"Chati za muda mrefu zinaonyesha {min(all_years)} hadi {max(all_years)} na hazibadiliki kwa kichujio cha mwaka wa muhtasari.",
        ),
        tr("Historical view", "Mtazamo wa kihistoria"),
    )

    c1, c2 = st.columns(2)

    with c1:
        school_gpa_df = (
            historical_school_df.groupby(["year"], as_index=False)["gpa"]
            .mean()
            .sort_values("year")
        )
        if not school_gpa_df.empty:
            fig = forecast_line_chart(
                school_gpa_df,
                "year",
                "gpa",
                tr("Average GPA"),
                lower_bound=0,
                upper_bound=5,
                height=380
            )
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
                render_chart_insight(
                    trend_insight_text(
                        school_gpa_df,
                        "year",
                        "gpa",
                        "GPA",
                        context=resolved_school_name or "the selected school"
                    )
                )
        else:
            st.info(tr("No school GPA trend data available.", "Hakuna data ya mwenendo wa GPA ya shule."))

    with c2:
        school_pass_df = weighted_pass_rate_by_group(
            historical_school_df,
            ["year"]
        ).sort_values("year")
        if not school_pass_df.empty:
            fig = forecast_line_chart(
                school_pass_df,
                "year",
                "pass_rate",
                tr("Pass Rate (%)"),
                lower_bound=0,
                upper_bound=100,
                height=380
            )
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
                render_chart_insight(
                    trend_insight_text(
                        school_pass_df,
                        "year",
                        "pass_rate",
                        "pass rate",
                        context=resolved_school_name or "the selected school"
                    )
                )
        else:
            st.info(tr("No school pass rate trend data available.", "Hakuna data ya mwenendo wa kiwango cha ufaulu wa shule."))

    sm1, sm2 = st.columns(2)
    with sm1:
        render_momentum_indicator(
            school_gpa_df,
            "year",
            "gpa",
            tr("School GPA"),
            resolved_school_name or "the selected school"
        )
    with sm2:
        render_momentum_indicator(
            school_pass_df,
            "year",
            "pass_rate",
            tr("School Pass Rate", "Kiwango cha Ufaulu cha Shule"),
            resolved_school_name or "the selected school"
        )

    st.markdown(f"#### {tr('School Year-over-Year Change', 'Mabadiliko ya Shule Mwaka hadi Mwaka')}")
    sy1, sy2 = st.columns(2)
    with sy1:
        fig_yoy, _ = yoy_bar_chart(
            school_gpa_df,
            "year",
            "gpa",
            tr("School GPA Year-over-Year Change", "Mabadiliko ya GPA ya Shule Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars mark years where the school's GPA improved; red bars mark years where GPA worsened.",
                "Mabao ya kijani yanaonyesha miaka ambayo GPA ya shule iliimarika; mabao mekundu yanaonyesha miaka ambayo GPA ilishuka."
            )
        else:
            st.info(tr(
                "At least two years of school GPA data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya GPA ya shule ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))
    with sy2:
        fig_yoy, _ = yoy_bar_chart(
            school_pass_df,
            "year",
            "pass_rate",
            tr("School Pass Rate Year-over-Year Change", "Mabadiliko ya Ufaulu wa Shule Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars mark years where pass rate improved; red bars mark years where pass rate declined.",
                "Mabao ya kijani yanaonyesha miaka ambayo kiwango cha ufaulu kiliongezeka; mabao mekundu yanaonyesha miaka ambayo kiwango hicho kilishuka."
            )
        else:
            st.info(tr(
                "At least two years of school pass rate data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya ufaulu wa shule ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))

    render_section_header(
        tr("School Performance Structure", "Muundo wa Ufaulu wa Shule"),
        tr(
            "Review how the selected school's candidates are distributed across NECTA divisions.",
            "Angalia jinsi watahiniwa wa shule iliyochaguliwa walivyogawanyika katika madaraja ya NECTA.",
        ),
        tr("Selected year", "Mwaka uliochaguliwa"),
    )
    note_box(tr(
        "Chart: Division Distribution. Shows the quality distribution of the selected school's performance using division categories.",
        "Chati: Mgawanyo wa Madaraja. Inaonyesha mgawanyo wa ubora wa ufaulu wa shule iliyochaguliwa kwa kutumia madaraja.",
    ))

    division_summary = pd.DataFrame({
        "Division": ["Div I", "Div II", "Div III", "Div IV", "Div 0"],
        "Count": [
            filtered_school_df["division_1"].sum() if "division_1" in filtered_school_df.columns else 0,
            filtered_school_df["division_2"].sum() if "division_2" in filtered_school_df.columns else 0,
            filtered_school_df["division_3"].sum() if "division_3" in filtered_school_df.columns else 0,
            filtered_school_df["division_4"].sum() if "division_4" in filtered_school_df.columns else 0,
            filtered_school_df["division_0"].sum() if "division_0" in filtered_school_df.columns else 0,
        ]
    })

    fig_div = px.bar(
        division_summary,
        x="Division",
        y="Count",
        text="Count"
    )
    fig_div.update_layout(
        title=tr("Selected School Division Distribution", "Mgawanyo wa Madaraja wa Shule Iliyochaguliwa"),
        xaxis_title=tr("Division"),
        yaxis_title=tr("Number of Candidates"),
        height=380
    )
    polish_chart_legend(fig_div, show=False)
    st.plotly_chart(fig_div, width="stretch")
    render_chart_insight(
        distribution_insight_text(
            division_summary,
            "Division",
            "Count",
            resolved_school_name or "the selected school"
        )
    )

    render_section_header(
        tr("Comparison Analysis", "Uchambuzi wa Ulinganisho"),
        tr(
            "Benchmark the selected school against another school or a regional average.",
            "Linganisha shule iliyochaguliwa na shule nyingine au wastani wa mkoa.",
        ),
        tr("Benchmarking", "Ulinganisho"),
    )
    note_box(tr(
        "The searched school is the default school. Choose only the school or region to compare against it.",
        "Shule iliyotafutwa ndiyo shule ya msingi. Chagua tu shule au mkoa wa kuilinganisha nayo.",
    ))
    comparison_metric = st.selectbox(
        tr("Comparison Metric", "Kipimo cha Ulinganisho"),
        options=["gpa", "pass_rate"],
        format_func=metric_display_name,
        key="school_comparison_metric"
    )

    st.markdown(f"#### {tr('School to School Comparison', 'Ulinganisho wa Shule kwa Shule')}")
    comp1, comp2 = st.columns([1, 2])

    comparison_school_options = [s for s in all_schools if s != resolved_school_name] if resolved_school_name else all_schools

    with comp1:
        selected_comparison_school = st.selectbox(
            tr("Compare with School", "Linganisha na Shule"),
            options=comparison_school_options if comparison_school_options else [tr("No other school", "Hakuna shule nyingine")],
            key="school_compare_school"
        )
    with comp2:
        note_box(tr(
            "Compares the selected school with another school across the full 2016 to 2025 history.",
            "Inalinganisha shule iliyochaguliwa na shule nyingine katika historia yote ya 2016 hadi 2025.",
        ))

    if resolved_school_name and selected_comparison_school not in {"No other school", "Hakuna shule nyingine"}:
        school_compare_df = school_df[
            school_df["school_name"].isin([resolved_school_name, selected_comparison_school])
        ].copy()
        if comparison_metric == "pass_rate":
            school_compare_trend = weighted_pass_rate_by_group(
                school_compare_df,
                ["year", "school_name"]
            ).sort_values(["school_name", "year"])
        else:
            school_compare_trend = (
                school_compare_df.groupby(["year", "school_name"], as_index=False)[comparison_metric]
                .mean()
                .sort_values(["school_name", "year"])
            )
        if not school_compare_trend.empty:
            fig_cmp = forecast_line_chart(
                school_compare_trend,
                "year",
                comparison_metric,
                metric_display_name(comparison_metric),
                group_col="school_name",
                lower_bound=0,
                upper_bound=100 if comparison_metric == "pass_rate" else 5,
                height=380
            )
            if fig_cmp is not None:
                st.plotly_chart(fig_cmp, width="stretch")
                render_chart_insight(
                    trend_insight_text(
                        school_compare_trend,
                        "year",
                        comparison_metric,
                        metric_display_name(comparison_metric),
                        group_col="school_name",
                        context="the two selected schools"
                    )
                )
        else:
            st.info(tr(
                "No comparison data available for the selected schools.",
                "Hakuna data ya ulinganisho kwa shule zilizochaguliwa.",
            ))
    else:
        st.info(tr(
            "Search and select a school to enable school-to-school comparison.",
            "Tafuta na chagua shule ili kuwezesha ulinganisho wa shule kwa shule.",
        ))

    st.markdown(f"#### {tr('School to Region Comparison', 'Ulinganisho wa Shule na Mkoa')}")
    comp3, comp4 = st.columns([1, 2])

    with comp3:
        selected_comparison_region = st.selectbox(
            tr("Compare with Region", "Linganisha na Mkoa"),
            options=all_regions,
            key="school_compare_region"
        )
    with comp4:
        note_box(tr(
            "Compares the selected school against the selected region average across 2016 to 2025.",
            "Inalinganisha shule iliyochaguliwa na wastani wa mkoa uliochaguliwa kuanzia 2016 hadi 2025.",
        ))

    if resolved_school_name and selected_comparison_region:
        if comparison_metric == "pass_rate":
            school_metric_df = weighted_pass_rate_by_group(
                historical_school_df,
                ["year"]
            ).sort_values("year")
        else:
            school_metric_df = (
                historical_school_df.groupby("year", as_index=False)[comparison_metric]
                .mean()
                .sort_values("year")
            )
        school_metric_df["Source"] = resolved_school_name

        region_history_df = filter_school_data(
            school_df,
            regions=[selected_comparison_region],
            years=(min(all_years), max(all_years))
        )
        if comparison_metric == "pass_rate":
            region_metric_df = weighted_pass_rate_by_group(
                region_history_df,
                ["year"]
            ).sort_values("year")
        else:
            region_metric_df = (
                region_history_df.groupby("year", as_index=False)[comparison_metric]
                .mean()
                .sort_values("year")
            )
        region_metric_df["Source"] = tr(
            f"{selected_comparison_region} Region Average",
            f"Wastani wa Mkoa wa {selected_comparison_region}",
        )

        school_region_compare_df = pd.concat(
            [
                school_metric_df[["year", comparison_metric, "Source"]],
                region_metric_df[["year", comparison_metric, "Source"]]
            ],
            ignore_index=True
        )

        if not school_region_compare_df.empty:
            fig_region_cmp = forecast_line_chart(
                school_region_compare_df,
                "year",
                comparison_metric,
                metric_display_name(comparison_metric),
                group_col="Source",
                lower_bound=0,
                upper_bound=100 if comparison_metric == "pass_rate" else 5,
                height=380
            )
            if fig_region_cmp is not None:
                st.plotly_chart(fig_region_cmp, width="stretch")
                render_chart_insight(
                    school_vs_region_insight(
                        historical_school_df,
                        region_history_df,
                        comparison_metric,
                        resolved_school_name,
                        selected_comparison_region
                    )
                )
        else:
            st.info(tr("No region comparison data available.", "Hakuna data ya ulinganisho wa mkoa."))
    else:
        st.info(tr(
            "Search and select a school to enable school-to-region comparison.",
            "Tafuta na chagua shule ili kuwezesha ulinganisho wa shule na mkoa.",
        ))

    render_section_header(
        tr("School Prediction Analysis", "Uchambuzi wa Makadirio ya Shule"),
        tr(
            "Use recent direction to support planning for the next two years. Forecasts are estimates, not official results.",
            "Tumia mwelekeo wa karibuni kusaidia mipango ya miaka miwili ijayo. Makadirio si matokeo rasmi.",
        ),
        tr("Forecast", "Makadirio"),
    )
    p1, p2 = st.columns(2)
    with p1:
        note_box(tr(
            "Solid lines show actual results; dashed lines show the two-year planning forecast.",
            "Mistari kamili inaonyesha matokeo halisi; mistari ya nukta inaonyesha makadirio ya mipango ya miaka miwili.",
        ))
        fig = forecast_line_chart(
            school_gpa_df,
            "year",
            "gpa",
            tr("Average GPA"),
            lower_bound=0,
            upper_bound=5,
            height=400
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                forecast_interpretation_text(
                    school_gpa_df,
                    "year",
                    "gpa",
                    "GPA",
                    resolved_school_name or "the selected school",
                )
            )
        else:
            st.info(tr(
                "At least two years of school GPA data are needed for prediction.",
                "Inahitajika angalau miaka miwili ya data ya GPA ya shule kwa makadirio.",
            ))
    with p2:
        note_box(tr(
            "Solid lines show actual results; dashed lines show the two-year planning forecast.",
            "Mistari kamili inaonyesha matokeo halisi; mistari ya nukta inaonyesha makadirio ya mipango ya miaka miwili.",
        ))
        fig = forecast_line_chart(
            school_pass_df,
            "year",
            "pass_rate",
            tr("Pass Rate (%)"),
            lower_bound=0,
            upper_bound=100,
            height=400
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                forecast_interpretation_text(
                    school_pass_df,
                    "year",
                    "pass_rate",
                    "pass rate",
                    resolved_school_name or "the selected school",
                )
            )
        else:
            st.info(tr(
                "At least two years of school pass rate data are needed for prediction.",
                "Inahitajika angalau miaka miwili ya data ya kiwango cha ufaulu wa shule kwa makadirio.",
            ))

    p3 = st.columns(1)[0]
    with p3:
        note_box(
            tr(
                "Solid lines show actual division counts; dashed lines extend recent patterns for planning and are not official results.",
                "Mistari kamili inaonyesha idadi halisi ya madaraja; mistari ya nukta inaendeleza mwenendo wa karibuni kwa mipango na si matokeo rasmi.",
            )
        )
        division_cols = {
            "division_1": "Div I",
            "division_2": "Div II",
            "division_3": "Div III",
            "division_4": "Div IV"
        }
        available_division_cols = [c for c in division_cols if c in historical_school_df.columns]
        if available_division_cols:
            division_prediction_df = (
                historical_school_df.groupby("year", as_index=False)[available_division_cols]
                .sum()
                .sort_values("year")
            )
            division_prediction_df = division_prediction_df.melt(
                id_vars="year",
                value_vars=available_division_cols,
                var_name="Division",
                value_name="Count"
            )
            division_prediction_df["Division"] = division_prediction_df["Division"].map(division_cols)
            fig = forecast_line_chart(
                division_prediction_df,
                "year",
                "Count",
                tr("Number of Candidates"),
                group_col="Division",
                lower_bound=0,
                height=430,
                color_discrete_map=DIVISION_HISTORY_COLORS,
                forecast_color_map=DIVISION_FORECAST_COLORS,
            )
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
                render_chart_insight(
                    trend_insight_text(
                        division_prediction_df,
                        "year",
                        "Count",
                        "Division I-IV candidate count",
                        group_col="Division",
                        context=resolved_school_name or "the selected school"
                    )
                )
            else:
                st.info(tr(
                    "At least two years of division data are needed for prediction.",
                    "Inahitajika angalau miaka miwili ya data ya madaraja kwa makadirio.",
                ))
        else:
            st.info(tr(
                "Division columns are missing for prediction.",
                "Safu za madaraja hazipo kwa makadirio.",
            ))
