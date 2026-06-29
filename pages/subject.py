"""Render subject strengths, weaknesses, trends, forecasts, and rankings."""

import pandas as pd
import streamlit as st

from charts import forecast_line_chart, weighted_subject_pass_rate_by_group, yoy_bar_chart
from filters import filter_subject_data
from insights import (
    forecast_interpretation_text,
    render_momentum_indicator,
    subject_key_findings,
    subject_strength_table,
    trend_insight_text,
)
from metrics import subject_kpi_values
from styles import (
    note_box,
    render_chart_insight,
    render_insight_card,
    render_key_findings,
    render_measure_guide,
    render_narrative,
    render_page_hero,
    render_section_header,
    render_stat_strip,
    tr,
)


def render_subject(subject_df, all_years, all_subjects):
    """Render the interactive national or school-level subject workspace."""
    render_page_hero(
        tr("Subject Performance Lab", "Kituo cha Ufaulu wa Masomo"),
        tr(
            "Review subject strength, weak areas, candidate outcomes, long-range trends, and forecasts across the national CSEE dataset.",
            "Pitia nguvu za masomo, maeneo dhaifu, matokeo ya watahiniwa, mienendo ya muda mrefu, na makadirio katika data ya kitaifa ya CSEE.",
        ),
        kicker=tr("Curriculum Intelligence", "Taarifa za Mtaala"),
        panel_title=tr("Subject Coverage", "Upeo wa Masomo"),
        panel_value=tr(f"{len(all_subjects)} subjects", f"Masomo {len(all_subjects)}"),
        panel_subtext=tr(
            f"Historical coverage from {min(all_years)} to {max(all_years)}.",
            f"Historia ya data kuanzia {min(all_years)} hadi {max(all_years)}.",
        ),
    )
    render_measure_guide(include_forecast=True)

    render_section_header(
        tr("Subject Controls", "Vidhibiti vya Masomo"),
        tr(
            "Filter by school, subject, and snapshot year before reviewing performance.",
            "Chuja kwa shule, somo, na mwaka wa muhtasari kabla ya kupitia ufaulu.",
        ),
        tr("Curriculum view", "Mtazamo wa mtaala"),
    )

    f1, f2, f3 = st.columns([1.5, 1.2, 1.0])

    with f1:
        selected_school = st.text_input(
            tr("Search School", "Tafuta Shule"),
            placeholder=tr(
                "Type school name or leave blank for all schools",
                "Andika jina la shule au acha wazi kwa shule zote",
            ),
            key="subject_page_school_search"
        )

    with f2:
        selected_subject = st.selectbox(
            tr("Subject"),
            options=["All Subjects"] + all_subjects,
            format_func=lambda subject: tr("All Subjects", "Masomo Yote") if subject == "All Subjects" else subject,
            key="subject_page_subject"
        )

    with f3:
        selected_year = st.selectbox(
            tr("Year"),
            options=all_years,
            index=len(all_years) - 1,
            key="subject_page_year"
        )

    filtered_subject_df = filter_subject_data(
        subject_df,
        years=selected_year,
        school=selected_school,
        subject=selected_subject
    )

    kpis = subject_kpi_values(filtered_subject_df)

    render_stat_strip([
        ("Subject GPA", kpis["avg_subject_gpa_display"], "Lower is better"),
        ("Pass Rate", kpis["avg_pass_rate_display"], "Selected filter"),
        ("Registered", kpis["registered_display"], "Subject entries"),
        ("Sat", kpis["sat_display"], "Exam sitters"),
    ])

    render_section_header(
        tr("Subject Insight Summary", "Muhtasari wa Maarifa ya Masomo"),
        tr(
            "Identify the strongest and weakest subjects under the current filter.",
            "Tambua masomo yenye nguvu na dhaifu chini ya kichujio cha sasa.",
        ),
        tr("Strength map", "Ramani ya nguvu"),
    )

    latest_subject_scope_df = filter_subject_data(
        subject_df,
        years=selected_year,
        school=selected_school,
        subject=None,
    )
    strength_df = subject_strength_table(latest_subject_scope_df)

    show_top_bottom_only = st.toggle(
        tr("Show only top 5 and bottom 5 subjects", "Onyesha masomo 5 ya juu na 5 ya chini tu"),
        value=True,
        key="subject_top_bottom_toggle",
    )

    top_df = pd.DataFrame()
    bottom_df = pd.DataFrame()
    if not strength_df.empty:
        top_df = strength_df.head(5).copy()
        bottom_df = strength_df.tail(5).sort_values(["subject_gpa", "pass_rate"], ascending=[False, True]).copy()

    i1, i2 = st.columns(2)

    with i1:
        if not bottom_df.empty:
            weakest = bottom_df.iloc[0]
            status = "danger" if weakest["pass_rate"] < 40 else "warning"
            render_insight_card(
                tr("Weakest Subject", "Somo Dhaifu"),
                str(weakest["subject_name"]),
                f"GPA {weakest['subject_gpa']:.2f}, {tr('Pass Rate')} {weakest['pass_rate']:.1f}%",
                status
            )
        else:
            render_insight_card(
                tr("Weakest Subject", "Somo Dhaifu"),
                "N/A",
                tr("No subject data available", "Hakuna data ya masomo"),
                "neutral"
            )

    with i2:
        if not top_df.empty:
            best = top_df.iloc[0]
            status = "good" if best["pass_rate"] >= 60 else "warning"
            render_insight_card(
                tr("Best Subject", "Somo Bora"),
                str(best["subject_name"]),
                f"GPA {best['subject_gpa']:.2f}, {tr('Pass Rate')} {best['pass_rate']:.1f}%",
                status
            )
        else:
            render_insight_card(
                tr("Best Subject", "Somo Bora"),
                "N/A",
                tr("No subject data available", "Hakuna data ya masomo"),
                "neutral"
            )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"#### {tr('Weakest Subjects', 'Masomo Dhaifu')}")
        if not bottom_df.empty:
            display_bottom = bottom_df if show_top_bottom_only else strength_df.sort_values(["subject_gpa", "pass_rate"], ascending=[False, True])
            display_bottom = display_bottom.copy()
            display_bottom["subject_gpa"] = display_bottom["subject_gpa"].round(2)
            display_bottom["pass_rate"] = display_bottom["pass_rate"].round(1)

            st.dataframe(
                display_bottom.rename(columns={
                    "subject_name": tr("Subject"),
                    "subject_gpa": tr("Avg GPA", "Wastani wa GPA"),
                    "pass_rate": tr("Pass Rate (%)")
                }),
                width="stretch",
                hide_index=True
            )
        else:
            st.info(tr("No weakest subject data available.", "Hakuna data ya masomo dhaifu."))

    with c2:
        st.markdown(f"#### {tr('Best Subjects', 'Masomo Bora')}")
        if not top_df.empty:
            display_top = top_df if show_top_bottom_only else strength_df
            display_top = display_top.copy()
            display_top["subject_gpa"] = display_top["subject_gpa"].round(2)
            display_top["pass_rate"] = display_top["pass_rate"].round(1)

            st.dataframe(
                display_top.rename(columns={
                    "subject_name": tr("Subject"),
                    "subject_gpa": tr("Avg GPA", "Wastani wa GPA"),
                    "pass_rate": tr("Pass Rate (%)")
                }),
                width="stretch",
                hide_index=True
            )
        else:
            st.info(tr("No best subject data available.", "Hakuna data ya masomo bora."))

    render_narrative(
        tr(
            "This section identifies both the strongest and weakest subjects. Teachers and administrators should protect strong-performing subjects while targeting support toward weak-performing ones.",
            "Sehemu hii inatambua masomo yenye nguvu na dhaifu. Walimu na wasimamizi walinde masomo yanayofanya vizuri huku wakielekeza msaada kwenye masomo dhaifu.",
        )
    )

    historical_subject_df = filter_subject_data(
        subject_df,
        years=(min(all_years), max(all_years)),
        school=selected_school,
        subject=selected_subject
    )
    findings_context = (
        selected_subject
        if selected_subject != "All Subjects"
        else (tr("the selected school", "shule iliyochaguliwa") if selected_school else tr("national subjects", "masomo ya kitaifa"))
    )
    render_key_findings(
        subject_key_findings(
            historical_subject_df,
            latest_subject_scope_df,
            findings_context,
        ),
        title=tr("Key Findings", "Matokeo Muhimu"),
        subtitle=tr(
            "The strongest signal, the weakest area, and the teaching priority.",
            "Ishara yenye nguvu zaidi, eneo dhaifu zaidi, na kipaumbele cha ufundishaji.",
        ),
    )

    render_section_header(
        tr("Subject Trend Analysis", "Uchambuzi wa Mwenendo wa Somo"),
        tr(
            f"Long-range charts always show {min(all_years)} to {max(all_years)} and do not change with the snapshot-year filter.",
            f"Chati za muda mrefu zinaonyesha {min(all_years)} hadi {max(all_years)} na hazibadiliki kwa kichujio cha mwaka wa muhtasari.",
        ),
        tr("Historical view", "Mtazamo wa kihistoria"),
    )

    c3, c4 = st.columns(2)

    with c3:
        trend_subject_gpa_df = (
            historical_subject_df.groupby(["year"], as_index=False)["subject_gpa"]
            .mean()
            .sort_values("year")
        )
        if not trend_subject_gpa_df.empty:
            fig = forecast_line_chart(
                trend_subject_gpa_df,
                "year",
                "subject_gpa",
                tr("Subject GPA"),
                lower_bound=0,
                upper_bound=5,
                height=380
            )
            if fig is not None:
                st.plotly_chart(fig, width="stretch")
                render_chart_insight(
                    trend_insight_text(
                        trend_subject_gpa_df,
                        "year",
                        "subject_gpa",
                        tr("subject GPA", "GPA ya somo"),
                        context=selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa")
                    )
                )
        else:
            st.info(tr("No subject GPA trend data available.", "Hakuna data ya mwenendo wa GPA ya somo."))

    with c4:
        trend_subject_pass_df = weighted_subject_pass_rate_by_group(
            historical_subject_df,
            ["year"]
        ).sort_values("year")
        if not trend_subject_pass_df.empty:
            fig = forecast_line_chart(
                trend_subject_pass_df,
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
                        trend_subject_pass_df,
                        "year",
                        "pass_rate",
                        tr("pass rate", "kiwango cha ufaulu"),
                        context=selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa")
                    )
                )
        else:
            st.info(tr("No subject pass rate trend data available.", "Hakuna data ya mwenendo wa kiwango cha ufaulu wa somo."))

    subj_m1, subj_m2 = st.columns(2)
    with subj_m1:
        render_momentum_indicator(
            trend_subject_gpa_df,
            "year",
            "subject_gpa",
            tr("Subject GPA"),
            selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa")
        )
    with subj_m2:
        render_momentum_indicator(
            trend_subject_pass_df,
            "year",
            "pass_rate",
            tr("Subject Pass Rate", "Kiwango cha Ufaulu wa Somo"),
            selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa")
        )

    st.markdown(f"#### {tr('Subject Year-over-Year Change', 'Mabadiliko ya Somo Mwaka hadi Mwaka')}")
    sub_y1, sub_y2 = st.columns(2)
    with sub_y1:
        fig_yoy, _ = yoy_bar_chart(
            trend_subject_gpa_df,
            "year",
            "subject_gpa",
            tr("Subject GPA Year-over-Year Change", "Mabadiliko ya GPA ya Somo Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars show years where subject GPA improved; red bars show years where subject GPA worsened.",
                "Mabao ya kijani yanaonyesha miaka ambayo GPA ya somo iliimarika; mabao mekundu yanaonyesha miaka ambayo GPA ya somo ilishuka."
            )
        else:
            st.info(tr(
                "At least two years of subject GPA data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya GPA ya somo ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))
    with sub_y2:
        fig_yoy, _ = yoy_bar_chart(
            trend_subject_pass_df,
            "year",
            "pass_rate",
            tr("Subject Pass Rate Year-over-Year Change", "Mabadiliko ya Ufaulu wa Somo Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars show years where subject pass rate improved; red bars show years where it declined.",
                "Mabao ya kijani yanaonyesha miaka ambayo kiwango cha ufaulu wa somo kiliongezeka; mabao mekundu yanaonyesha miaka ambayo kilishuka."
            )
        else:
            st.info(tr(
                "At least two years of subject pass rate data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya ufaulu wa somo ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))

    render_section_header(
        tr("Subject Prediction Analysis", "Uchambuzi wa Makadirio ya Somo"),
        tr(
            "Use recent direction to support teaching plans for the next two years. Forecasts are estimates, not official results.",
            "Tumia mwelekeo wa karibuni kusaidia mipango ya ufundishaji ya miaka miwili ijayo. Makadirio si matokeo rasmi.",
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
            trend_subject_gpa_df,
            "year",
            "subject_gpa",
            tr("Subject GPA"),
            lower_bound=0,
            upper_bound=5,
            height=400
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            render_chart_insight(
                forecast_interpretation_text(
                    trend_subject_gpa_df,
                    "year",
                        "subject_gpa",
                        tr("subject GPA", "GPA ya somo"),
                        selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa"),
                    )
                )
        else:
            st.info(tr(
                "At least two years of subject GPA data are needed for prediction.",
                "Inahitajika angalau miaka miwili ya data ya GPA ya somo kwa makadirio.",
            ))
    with p2:
        note_box(tr(
            "Solid lines show actual results; dashed lines show the two-year planning forecast.",
            "Mistari kamili inaonyesha matokeo halisi; mistari ya nukta inaonyesha makadirio ya mipango ya miaka miwili.",
        ))
        fig = forecast_line_chart(
            trend_subject_pass_df,
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
                    trend_subject_pass_df,
                    "year",
                        "pass_rate",
                        tr("pass rate", "kiwango cha ufaulu"),
                        selected_subject if selected_subject != "All Subjects" else tr("all selected subjects", "masomo yote yaliyochaguliwa"),
                    )
                )
        else:
            st.info(tr(
                "At least two years of subject pass rate data are needed for prediction.",
                "Inahitajika angalau miaka miwili ya data ya kiwango cha ufaulu wa somo kwa makadirio.",
            ))

    render_section_header(
        tr("Subject Summary", "Muhtasari wa Masomo"),
        tr(
            "Rank all subjects for the selected school and year using GPA and weighted pass rate.",
            "Panga masomo yote kwa shule na mwaka uliochaguliwa kwa kutumia GPA na kiwango cha ufaulu kilichopimwa kwa idadi.",
        ),
        tr("Ranking table", "Jedwali la upangaji"),
    )

    subject_summary_df = filter_subject_data(
        subject_df,
        years=selected_year,
        school=selected_school,
        subject=None
    )

    if not subject_summary_df.empty:
        subject_summary = (
            subject_summary_df.groupby("subject_name", as_index=False)
            .agg({
                "subject_gpa": "mean",
                "pass": "sum",
                "sat": "sum"
            })
        )

        subject_summary["pass_rate"] = (
            subject_summary["pass"] / subject_summary["sat"].where(subject_summary["sat"] != 0)
        ) * 100

        subject_summary = subject_summary.sort_values("subject_gpa", ascending=True).reset_index(drop=True)
        subject_summary["Rank"] = range(1, len(subject_summary) + 1)

        subject_summary["subject_gpa"] = subject_summary["subject_gpa"].round(2)
        subject_summary["pass_rate"] = subject_summary["pass_rate"].round(1).fillna(0)

        subject_summary = subject_summary.rename(columns={
            "Rank": tr("Rank"),
            "subject_name": tr("Subject"),
            "subject_gpa": "GPA",
            "pass_rate": tr("Pass Rate (%)")
        })

        st.dataframe(
            subject_summary[[tr("Rank"), tr("Subject"), "GPA", tr("Pass Rate (%)")]],
            width="stretch",
            hide_index=True
        )
    else:
        st.info(tr("No subject data available.", "Hakuna data ya masomo."))
