"""Render school and subject performance and momentum rankings."""

import plotly.express as px
import streamlit as st

from charts import polish_chart_legend
from decision_artifacts import load_decision_artifacts
from decision_ui import render_rankings_decision_support
from filters import (
    filter_school_data,
    filter_subject_data,
    region_filter_options,
    resolve_school_name,
    selected_region_values,
    sync_region_multiselect_state,
)
from insights import performance_change, ranking_insight_text, ranking_key_findings
from metrics import add_region_to_change, school_ranking_summary, subject_ranking_summary
from styles import (
    render_chart_insight,
    render_key_findings,
    render_measure_guide,
    render_page_hero,
    render_section_header,
    render_stat_strip,
    tr,
)


def render_rankings(school_df, subject_df, all_regions, all_years):
    """Render filtered top, bottom, improving, and declining rankings."""
    render_page_hero(
        tr("NECTA Ranking Intelligence", "Taarifa za Upangaji wa NECTA"),
        tr(
            "Identify excellence, weak performance, improvement, and decline across schools and subjects.",
            "Tambua ufaulu bora, ufaulu dhaifu, uimarishaji, na kushuka kwa shule na masomo.",
        ),
        kicker=tr("Performance League Tables", "Majedwali ya Upangaji wa Ufaulu"),
        panel_title=tr("Ranking Modes", "Aina za Upangaji"),
        panel_value=tr("Top + Bottom", "Juu + Chini"),
        panel_subtext=tr(
            "Snapshot rankings and multi-year momentum use one consistent control panel.",
            "Upangaji wa muhtasari na mwenendo wa miaka mingi hutumia paneli moja ya vidhibiti.",
        ),
    )
    render_measure_guide(include_forecast=False)

    render_section_header(
        tr("Ranking Controls", "Vidhibiti vya Upangaji"),
        tr(
            "Select region, ranking year, improvement window, and the number of records to display.",
            "Chagua mkoa, mwaka wa upangaji, kipindi cha uimarishaji, na idadi ya rekodi za kuonyesha.",
        ),
        tr("School + subject", "Shule + somo"),
    )

    r1, r2, r3 = st.columns([1.4, 1.0, 1.4])
    with r1:
        region_key = "ranking_region_options"
        if region_key in st.session_state:
            sync_region_multiselect_state(st.session_state, region_key, all_regions)

        def sync_ranking_region_options():
            sync_region_multiselect_state(st.session_state, region_key, all_regions)

        selected_region_options = st.multiselect(
            tr("Region"),
            options=region_filter_options(all_regions),
            default=["All"],
            format_func=lambda option: tr("All", "Yote") if option == "All" else option,
            key=region_key,
            on_change=sync_ranking_region_options
        )
        selected_regions = selected_region_values(selected_region_options, all_regions)
    with r2:
        selected_year = st.selectbox(
            tr("Ranking Year"),
            options=all_years,
            index=len(all_years) - 1,
            key="ranking_year"
        )
    with r3:
        selected_years = st.select_slider(
            tr("Improvement Window"),
            options=all_years,
            value=(min(all_years), max(all_years)),
            key="ranking_year_window"
        )

    s1, s2 = st.columns(2)
    with s1:
        top_option = st.segmented_control(
            tr("Top ranking size", "Ukubwa wa upangaji wa juu"),
            options=["Top 5", "Top 10", "Top 20"],
            default="Top 10",
            format_func=lambda option: option.replace("Top", tr("Top", "Juu")),
            key="ranking_top_size"
        )
    with s2:
        bottom_option = st.segmented_control(
            tr("Bottom ranking size", "Ukubwa wa upangaji wa chini"),
            options=["Bottom 5", "Bottom 10", "Bottom 20"],
            default="Bottom 10",
            format_func=lambda option: option.replace("Bottom", tr("Bottom", "Chini")),
            key="ranking_bottom_size"
        )

    top_option = top_option or "Top 10"
    bottom_option = bottom_option or "Bottom 10"
    top_count = int(top_option.split()[-1])
    bottom_count = int(bottom_option.split()[-1])
    top_chart_height = max(430, top_count * 28)
    bottom_chart_height = max(430, bottom_count * 28)

    render_stat_strip([
        ("Ranking Year", selected_year, "Snapshot for top and bottom tables"),
        ("Improvement Window", f"{selected_years[0]}-{selected_years[1]}", "History used for momentum"),
        ("Top View", top_option, "Best performance or improvement"),
        ("Bottom View", bottom_option, "Weakest performance or decline"),
    ])

    ranking_year_df = filter_school_data(
        school_df,
        regions=selected_regions,
        years=selected_year
    )
    ranking_window_df = filter_school_data(
        school_df,
        regions=selected_regions,
        years=selected_years
    )

    summary_df = school_ranking_summary(ranking_year_df)
    full_rank_df = (
        summary_df.sort_values(["gpa", "pass_rate"], ascending=[True, False])
        .reset_index(drop=True)
        .copy()
    )
    if not full_rank_df.empty:
        full_rank_df["Rank"] = range(1, len(full_rank_df) + 1)

    top_df = full_rank_df.head(top_count).copy()
    lowest_df = summary_df.sort_values(["gpa", "pass_rate"], ascending=[False, True]).head(bottom_count).copy()

    change_df = performance_change(ranking_window_df, "school_name", "gpa")
    change_df = add_region_to_change(change_df, ranking_window_df)
    improved_df = change_df.head(top_count).copy()
    decline_df = change_df.tail(bottom_count).sort_values("improvement_score", ascending=True).copy()

    subject_year_df = filter_subject_data(
        subject_df,
        regions=selected_regions,
        years=selected_year
    )
    subject_window_df = filter_subject_data(
        subject_df,
        regions=selected_regions,
        years=selected_years
    )

    subject_summary_df = subject_ranking_summary(subject_year_df)
    subject_top_df = (
        subject_summary_df.sort_values(["subject_gpa", "pass_rate"], ascending=[True, False])
        .head(top_count)
        .copy()
    )
    subject_lowest_df = (
        subject_summary_df.sort_values(["subject_gpa", "pass_rate"], ascending=[False, True])
        .head(bottom_count)
        .copy()
    )

    subject_change_df = performance_change(subject_window_df, "subject_name", "subject_gpa")
    subject_improved_df = subject_change_df.head(top_count).copy()
    subject_decline_df = (
        subject_change_df.tail(bottom_count)
        .sort_values("improvement_score", ascending=True)
        .copy()
    )
    render_key_findings(
        ranking_key_findings(
            top_df,
            lowest_df,
            improved_df,
            decline_df,
            subject_top_df,
            subject_lowest_df,
            selected_year,
        ),
        title="Key Findings",
        subtitle=tr(
            "Who leads, who needs support, and where momentum is changing.",
            "Nani anaongoza, nani anahitaji msaada, na wapi mwenendo unabadilika.",
        ),
    )
    render_rankings_decision_support(
        load_decision_artifacts(),
        selected_regions,
        top_count,
    )

    render_section_header(
        tr("School Rankings", "Upangaji wa Shule"),
        tr(
            "Search for one school or inspect top, bottom, improving, and declining groups.",
            "Tafuta shule moja au chunguza makundi ya juu, chini, yanayoimarika, na yanayoshuka.",
        ),
        tr(f"{len(full_rank_df):,} ranked", f"{len(full_rank_df):,} zimepangwa"),
    )

    searched_school = st.text_input(
        tr("Search School Ranking", "Tafuta Nafasi ya Shule"),
        placeholder=tr("Type a school name to find its rank", "Andika jina la shule ili kupata nafasi yake"),
        key="ranking_school_search"
    )
    if searched_school:
        searchable_schools = sorted(full_rank_df["school_name"].dropna().unique().tolist()) if not full_rank_df.empty else []
        resolved_school = resolve_school_name(searched_school, searchable_schools)
        if resolved_school:
            school_rank_row = full_rank_df[full_rank_df["school_name"] == resolved_school].head(1).copy()
            if not school_rank_row.empty:
                rank = int(school_rank_row["Rank"].iloc[0])
                total_ranked = len(full_rank_df)
                st.markdown(tr(
                    f"**{resolved_school}** ranks **#{rank:,}** of **{total_ranked:,}** schools in {selected_year}.",
                    f"**{resolved_school}** iko nafasi **#{rank:,}** kati ya shule **{total_ranked:,}** mwaka {selected_year}.",
                ))
                display_rank = school_rank_row[["Rank", "school_name", "region", "gpa", "pass_rate", "sat"]].copy()
                display_rank["gpa"] = display_rank["gpa"].round(2)
                display_rank["pass_rate"] = display_rank["pass_rate"].round(1)
                st.dataframe(
                    display_rank.rename(columns={
                        "school_name": tr("School"),
                        "region": tr("Region"),
                        "gpa": "GPA",
                        "pass_rate": tr("Pass Rate (%)"),
                        "sat": tr("Sat")
                    }),
                    width="stretch",
                    hide_index=True
                )
        else:
            st.warning(tr(
                "No ranked school matched that search for the selected year and region filter.",
                "Hakuna shule iliyopangwa iliyolingana na utafutaji huo kwa mwaka na kichujio cha mkoa kilichochaguliwa.",
            ))

    tab_top, tab_lowest, tab_improved, tab_decline = st.tabs([
        tr(f"Top {top_count} Schools", f"Shule {top_count} za Juu"),
        tr(f"Bottom {bottom_count}", f"Chini {bottom_count}"),
        tr(f"Most Improved {top_count}", f"Zilizoimarika Zaidi {top_count}"),
        tr(f"Steepest Decline {bottom_count}", f"Zilizoshuka Zaidi {bottom_count}"),
    ])

    with tab_top:
        if not top_df.empty:
            display_df = top_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["gpa"] = display_df["gpa"].round(2)
            display_df["pass_rate"] = display_df["pass_rate"].round(1)

            st.dataframe(
                display_df[["Rank", "school_name", "region", "gpa", "pass_rate", "sat"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "gpa": "GPA",
                    "pass_rate": tr("Pass Rate (%)"),
                    "sat": tr("Sat")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("gpa", ascending=False),
                x="gpa",
                y="school_name",
                orientation="h",
                color_discrete_sequence=["#16a34a"],
                text="gpa"
            )
            fig.update_layout(
                title=tr(f"Top {top_count} Schools by Average GPA", f"Shule {top_count} za Juu kwa Wastani wa GPA"),
                xaxis_title=tr("Average GPA"),
                yaxis_title=tr("School"),
                height=top_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                ranking_insight_text(top_df, "school_name", "gpa", f"Top {top_count} Schools", "gpa")
            )
        else:
            st.info(tr("No top school ranking data available.", "Hakuna data ya upangaji wa shule za juu."))

    with tab_lowest:
        if not lowest_df.empty:
            display_df = lowest_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["gpa"] = display_df["gpa"].round(2)
            display_df["pass_rate"] = display_df["pass_rate"].round(1)

            st.dataframe(
                display_df[["Rank", "school_name", "region", "gpa", "pass_rate", "division_0"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "gpa": "GPA",
                    "pass_rate": tr("Pass Rate (%)"),
                    "division_0": "Division 0"
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("gpa", ascending=True),
                x="gpa",
                y="school_name",
                orientation="h",
                color_discrete_sequence=["#dc2626"],
                text="gpa"
            )
            fig.update_layout(
                title=tr(f"Bottom {bottom_count} Schools by Average GPA", f"Shule {bottom_count} za Chini kwa Wastani wa GPA"),
                xaxis_title=tr("Average GPA"),
                yaxis_title=tr("School"),
                height=bottom_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                ranking_insight_text(lowest_df, "school_name", "gpa", f"Bottom {bottom_count} Schools", "gpa")
            )
        else:
            st.info(tr("No bottom school ranking data available.", "Hakuna data ya upangaji wa shule za chini."))

    with tab_improved:
        if not improved_df.empty:
            display_df = improved_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["change"] = display_df["change"].round(2)

            st.dataframe(
                display_df[["Rank", "school_name", "region", "change"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "change": tr("GPA Change", "Mabadiliko ya GPA")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("improvement_score", ascending=True),
                x="change",
                y="school_name",
                orientation="h",
                color_discrete_sequence=["#16a34a"],
                text="change"
            )
            fig.update_layout(
                title=tr(f"Most Improved {top_count} Schools by GPA Change", f"Shule {top_count} Zilizoimarika Zaidi kwa Mabadiliko ya GPA"),
                xaxis_title=tr("GPA Change", "Mabadiliko ya GPA"),
                yaxis_title=tr("School"),
                height=top_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                "These schools improved the most over the selected window. Negative GPA change is good because lower NECTA GPA indicates stronger performance.",
                "Shule hizi zimeimarika zaidi ndani ya kipindi kilichochaguliwa. Mabadiliko hasi ya GPA ni mazuri kwa sababu GPA ya chini ya NECTA inaonyesha ufaulu bora."
            )
        else:
            st.info(tr(
                "At least two years of school history are needed for improvement ranking.",
                "Inahitajika angalau miaka miwili ya historia ya shule kwa upangaji wa uimarishaji.",
            ))

    with tab_decline:
        if not decline_df.empty:
            display_df = decline_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["change"] = display_df["change"].round(2)

            st.dataframe(
                display_df[["Rank", "school_name", "region", "change"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "change": tr("GPA Change", "Mabadiliko ya GPA")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("improvement_score", ascending=False),
                x="change",
                y="school_name",
                orientation="h",
                color_discrete_sequence=["#dc2626"],
                text="change"
            )
            fig.update_layout(
                title=tr(f"Steepest {bottom_count} School GPA Declines", f"Shule {bottom_count} Zilizoshuka Zaidi kwa GPA"),
                xaxis_title=tr("GPA Change", "Mabadiliko ya GPA"),
                yaxis_title=tr("School"),
                height=bottom_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                "These schools have the steepest negative momentum over the selected window and should be prioritized for follow-up.",
                "Shule hizi zina mwenendo mbaya zaidi ndani ya kipindi kilichochaguliwa na zinapaswa kupewa kipaumbele kwa ufuatiliaji."
            )
        else:
            st.info(tr(
                "At least two years of school history are needed for decline ranking.",
                "Inahitajika angalau miaka miwili ya historia ya shule kwa upangaji wa kushuka.",
            ))

    render_section_header(
        tr("Subject Rankings", "Upangaji wa Masomo"),
        tr(
            "Compare subject performance and momentum using the same ranking window.",
            "Linganisha ufaulu na mwenendo wa masomo kwa kutumia kipindi hicho hicho cha upangaji.",
        ),
        tr("Curriculum view", "Mtazamo wa mtaala"),
    )
    subject_tab_top, subject_tab_lowest, subject_tab_improved, subject_tab_decline = st.tabs([
        tr(f"Top {top_count} Subjects", f"Masomo {top_count} ya Juu"),
        tr(f"Bottom {bottom_count}", f"Chini {bottom_count}"),
        tr(f"Most Improved {top_count}", f"Yaliyoimarika Zaidi {top_count}"),
        tr(f"Steepest Decline {bottom_count}", f"Yaliyoshuka Zaidi {bottom_count}"),
    ])

    with subject_tab_top:
        if not subject_top_df.empty:
            display_df = subject_top_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["subject_gpa"] = display_df["subject_gpa"].round(2)
            display_df["pass_rate"] = display_df["pass_rate"].round(1)

            st.dataframe(
                display_df[["Rank", "subject_name", "subject_gpa", "pass_rate", "sat"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "subject_name": tr("Subject"),
                    "subject_gpa": tr("Subject GPA"),
                    "pass_rate": tr("Pass Rate (%)"),
                    "sat": tr("Sat")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("subject_gpa", ascending=False),
                x="subject_gpa",
                y="subject_name",
                orientation="h",
                color_discrete_sequence=["#16a34a"],
                text="subject_gpa"
            )
            fig.update_layout(
                title=tr(f"Top {top_count} Subjects by Average Subject GPA", f"Masomo {top_count} ya Juu kwa Wastani wa GPA ya Somo"),
                xaxis_title=tr("Average Subject GPA"),
                yaxis_title=tr("Subject"),
                height=top_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                ranking_insight_text(
                    subject_top_df,
                    "subject_name",
                    "subject_gpa",
                    f"Top {top_count} Subjects",
                    "subject_gpa"
                )
            )
        else:
            st.info(tr("No top subject ranking data available.", "Hakuna data ya upangaji wa masomo ya juu."))

    with subject_tab_lowest:
        if not subject_lowest_df.empty:
            display_df = subject_lowest_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["subject_gpa"] = display_df["subject_gpa"].round(2)
            display_df["pass_rate"] = display_df["pass_rate"].round(1)

            st.dataframe(
                display_df[["Rank", "subject_name", "subject_gpa", "pass_rate", "sat"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "subject_name": tr("Subject"),
                    "subject_gpa": tr("Subject GPA"),
                    "pass_rate": tr("Pass Rate (%)"),
                    "sat": tr("Sat")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("subject_gpa", ascending=True),
                x="subject_gpa",
                y="subject_name",
                orientation="h",
                color_discrete_sequence=["#dc2626"],
                text="subject_gpa"
            )
            fig.update_layout(
                title=tr(f"Bottom {bottom_count} Subjects by Average Subject GPA", f"Masomo {bottom_count} ya Chini kwa Wastani wa GPA ya Somo"),
                xaxis_title=tr("Average Subject GPA"),
                yaxis_title=tr("Subject"),
                height=bottom_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                ranking_insight_text(
                    subject_lowest_df,
                    "subject_name",
                    "subject_gpa",
                    f"Bottom {bottom_count} Subjects",
                    "subject_gpa"
                )
            )
        else:
            st.info(tr("No bottom subject ranking data available.", "Hakuna data ya upangaji wa masomo ya chini."))

    with subject_tab_improved:
        if not subject_improved_df.empty:
            display_df = subject_improved_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["change"] = display_df["change"].round(2)

            st.dataframe(
                display_df[["Rank", "subject_name", "change"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "subject_name": tr("Subject"),
                    "change": tr("Subject GPA Change", "Mabadiliko ya GPA ya Somo")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("improvement_score", ascending=True),
                x="change",
                y="subject_name",
                orientation="h",
                color_discrete_sequence=["#16a34a"],
                text="change"
            )
            fig.update_layout(
                title=tr(f"Most Improved {top_count} Subjects by Subject GPA Change", f"Masomo {top_count} Yaliyoimarika Zaidi kwa Mabadiliko ya GPA ya Somo"),
                xaxis_title=tr("Subject GPA Change", "Mabadiliko ya GPA ya Somo"),
                yaxis_title=tr("Subject"),
                height=top_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                "These subjects improved the most over the selected window. Negative subject GPA change is good because lower subject GPA indicates stronger performance.",
                "Masomo haya yameimarika zaidi ndani ya kipindi kilichochaguliwa. Mabadiliko hasi ya GPA ya somo ni mazuri kwa sababu GPA ya chini ya somo inaonyesha ufaulu bora."
            )
        else:
            st.info(tr(
                "At least two years of subject history are needed for improvement ranking.",
                "Inahitajika angalau miaka miwili ya historia ya somo kwa upangaji wa uimarishaji.",
            ))

    with subject_tab_decline:
        if not subject_decline_df.empty:
            display_df = subject_decline_df.copy()
            display_df["Rank"] = range(1, len(display_df) + 1)
            display_df["change"] = display_df["change"].round(2)

            st.dataframe(
                display_df[["Rank", "subject_name", "change"]]
                .rename(columns={
                    "Rank": tr("Rank"),
                    "subject_name": tr("Subject"),
                    "change": tr("Subject GPA Change", "Mabadiliko ya GPA ya Somo")
                }),
                width="stretch",
                hide_index=True
            )

            fig = px.bar(
                display_df.sort_values("improvement_score", ascending=False),
                x="change",
                y="subject_name",
                orientation="h",
                color_discrete_sequence=["#dc2626"],
                text="change"
            )
            fig.update_layout(
                title=tr(f"Steepest {bottom_count} Subject GPA Declines", f"Masomo {bottom_count} Yaliyoshuka Zaidi kwa GPA"),
                xaxis_title=tr("Subject GPA Change", "Mabadiliko ya GPA ya Somo"),
                yaxis_title=tr("Subject"),
                height=bottom_chart_height
            )
            polish_chart_legend(fig, show=False)
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                "These subjects have the steepest negative momentum over the selected window and should be prioritized for curriculum, teaching, and resource follow-up.",
                "Masomo haya yana mwenendo mbaya zaidi ndani ya kipindi kilichochaguliwa na yanapaswa kupewa kipaumbele kwenye mtaala, ufundishaji, na rasilimali."
            )
        else:
            st.info(tr(
                "At least two years of subject history are needed for decline ranking.",
                "Inahitajika angalau miaka miwili ya historia ya somo kwa upangaji wa kushuka.",
            ))
