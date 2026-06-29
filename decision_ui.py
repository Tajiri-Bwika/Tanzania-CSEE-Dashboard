"""Render native dashboard cards and tables from offline decision artifacts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from styles import (
    note_box,
    render_insight_card,
    render_narrative,
    render_section_header,
    tr,
)


def _scoped(df, selected_regions):
    if df.empty or not selected_regions or "region" not in df.columns:
        return df.copy()
    return df[df["region"].isin(selected_regions)].copy()


def _risk_status(level):
    return {
        "High": "danger",
        "Moderate": "warning",
        "Safe": "good",
    }.get(str(level), "neutral")


def _display_text(value):
    """Translate common artifact values without mutating saved artifact files."""
    text = str(value)
    exact = {
        "Teacher Development Program": tr("Teacher Development Program", "Programu ya Maendeleo ya Walimu"),
        "Mathematics Tutoring Program": tr("Mathematics Tutoring Program", "Programu ya Usaidizi wa Hisabati"),
        "Monitor and Maintain Support": tr("Monitor and Maintain Support", "Fuatilia na Dumisha Msaada"),
        "Laboratory Support Program": tr("Laboratory Support Program", "Programu ya Msaada wa Maabara"),
        "Teacher Development": tr("Teacher Development", "Maendeleo ya Walimu"),
        "Mathematics Tutoring": tr("Mathematics Tutoring", "Usaidizi wa Hisabati"),
        "Monitor and Maintain Support": tr("Monitor and Maintain Support", "Fuatilia na Dumisha Msaada"),
        "Laboratory Support": tr("Laboratory Support", "Msaada wa Maabara"),
        "Safe": tr("Safe", "Salama"),
        "Moderate": tr("Moderate", "Wastani"),
        "High": tr("High", "Juu"),
        "Low": tr("Low", "Chini"),
        "Medium": tr("Medium", "Wastani"),
        "Critical": tr("Critical", "Muhimu"),
        "Latest mathematics performance meets the weak-subject threshold.": tr(
            "Latest mathematics performance meets the weak-subject threshold.",
            "Ufaulu wa karibuni wa Hisabati umefikia kizingiti cha somo dhaifu.",
        ),
        "Latest science performance meets the weak-subject threshold.": tr(
            "Latest science performance meets the weak-subject threshold.",
            "Ufaulu wa karibuni wa masomo ya sayansi umefikia kizingiti cha somo dhaifu.",
        ),
        "Current evidence does not cross a targeted intervention threshold.": tr(
            "Current evidence does not cross a targeted intervention threshold.",
            "Ushahidi wa sasa haujavuka kizingiti cha uingiliaji uliolengwa.",
        ),
        "Planning scenario only; the range is not a measured, causal, or guaranteed outcome.": tr(
            "Planning scenario only; the range is not a measured, causal, or guaranteed outcome.",
            "Hii ni hali ya mipango tu; kiwango hiki si matokeo yaliyopimwa, ya kisababishi, au yaliyohakikishwa.",
        ),
    }
    if text in exact:
        return exact[text]
    if " weak subjects indicate a broad instructional challenge." in text:
        count = text.split(" ", 1)[0]
        return tr(
            text,
            f"Masomo dhaifu {count} yanaonyesha changamoto pana ya ufundishaji.",
        )
    if text.startswith("Assumption-based scenario estimate:"):
        return tr(
            text,
            text.replace("Assumption-based scenario estimate:", "Makadirio ya hali ya kidhahania:")
            .replace("pass rate", "kiwango cha ufaulu"),
        )
    return text


def render_dashboard_decision_support(artifacts, selected_regions):
    """Render selected-region intervention priorities on the Dashboard page."""
    render_section_header(
        tr("Intervention Priorities", "Vipaumbele vya Uingiliaji"),
        tr(
            "Offline school and regional scores identify where follow-up should begin.",
            "Alama za shule na mikoa zilizotengenezwa nje ya dashibodi zinaonyesha ufuatiliaji uanze wapi.",
        ),
        tr("Decision support", "Msaada wa maamuzi"),
    )
    if not artifacts:
        st.info(
            tr(
                "Decision-support artifacts are unavailable. Run build_decision_artifacts.py offline.",
                "Faili za msaada wa maamuzi hazipatikani. Endesha build_decision_artifacts.py nje ya dashibodi.",
            )
        )
        return

    priority_df = _scoped(artifacts["school_priority"], selected_regions)
    regional_risk_df = _scoped(artifacts["regional_risk"], selected_regions)
    intervention_df = _scoped(artifacts["interventions"], selected_regions)
    if priority_df.empty or intervention_df.empty:
        st.info(
            tr(
                "No intervention priorities match the selected regions.",
                "Hakuna vipaumbele vya uingiliaji vinavyolingana na mikoa iliyochaguliwa.",
            )
        )
        return

    top_priority = priority_df.sort_values("priority_rank").iloc[0]
    highest_region = (
        regional_risk_df.sort_values("risk_score", ascending=False).iloc[0]
        if not regional_risk_df.empty
        else None
    )
    elevated_count = int(
        priority_df["priority_category"].isin(["Critical", "High"]).sum()
    )
    dominant_intervention = (
        intervention_df["recommended_intervention"].value_counts().index[0]
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_insight_card(
            tr("Top Priority School", "Shule ya Kipaumbele"),
            str(top_priority["school_name"]),
            f"{top_priority['region']} | {tr('Score', 'Alama')} {top_priority['priority_score']:.1f}",
            "danger",
        )
    with c2:
        if highest_region is not None:
            render_insight_card(
                tr("Highest Regional Risk", "Hatari Kubwa ya Mkoa"),
                str(highest_region["region"]),
                f"{_display_text(highest_region['risk_level'])} | {tr('Score', 'Alama')} {highest_region['risk_score']:.1f}",
                _risk_status(highest_region["risk_level"]),
            )
        else:
            render_insight_card(
                tr("Highest Regional Risk", "Hatari Kubwa ya Mkoa"),
                "N/A",
                tr("No regional score available", "Hakuna alama ya mkoa"),
                "neutral",
            )
    with c3:
        render_insight_card(
            tr("Elevated Priorities", "Vipaumbele vya Juu"),
            f"{elevated_count:,}",
            tr(
                "Critical or High priority schools",
                "Shule za kipaumbele cha Juu au Muhimu",
            ),
            "warning" if elevated_count else "good",
        )
    with c4:
        render_insight_card(
            tr("Most Common Action", "Hatua Inayojirudia"),
            _display_text(dominant_intervention.replace(" Program", "")),
            tr(
                "Recommended most often in this selection",
                "Imependekezwa mara nyingi katika uchaguzi huu",
            ),
            "neutral",
        )

    note_box(
        tr(
            "Expected improvement ranges below are assumption-based scenario estimates. "
            "They are not measured, causal, guaranteed, or official outcomes.",
            "Makadirio ya maboresho hapa chini yanatokana na dhana za hali inayowezekana. "
            "Si matokeo yaliyopimwa, ya kisababishi, yaliyohakikishwa, au rasmi.",
        )
    )
    display = (
        intervention_df.sort_values(["priority_rank", "risk_score"])
        .head(15)
        .copy()
    )
    display["priority_score"] = display["priority_score"].round(1)
    display["risk_score"] = display["risk_score"].round(1)
    for column in [
        "priority_category",
        "risk_level",
        "recommended_intervention",
        "expected_improvement_range",
    ]:
        if column in display.columns:
            display[column] = display[column].map(_display_text)
    st.dataframe(
        display[
            [
                "priority_rank",
                "school_name",
                "region",
                "priority_score",
                "priority_category",
                "risk_score",
                "risk_level",
                "recommended_intervention",
                "expected_improvement_range",
            ]
        ].rename(
            columns={
                "priority_rank": tr("Rank"),
                "school_name": tr("School"),
                "region": tr("Region"),
                "priority_score": tr("Priority Score", "Alama ya Kipaumbele"),
                "priority_category": tr("Priority Level", "Kiwango cha Kipaumbele"),
                "risk_score": tr("Risk Score", "Alama ya Hatari"),
                "risk_level": tr("Risk Level", "Kiwango cha Hatari"),
                "recommended_intervention": tr(
                    "Recommended Intervention",
                    "Uingiliaji Unaopendekezwa",
                ),
                "expected_improvement_range": tr(
                    "Assumption-Based Scenario Range",
                    "Makadirio ya Hali ya Kidhahania",
                ),
            }
        ),
        width="stretch",
        hide_index=True,
    )


def render_school_decision_support(artifacts, school_name):
    """Render one selected school's priority, risk, and recommended action."""
    if not school_name:
        return
    render_section_header(
        tr("Intervention Action", "Hatua ya Uingiliaji"),
        tr(
            "The latest offline evidence combines priority, risk, and subject signals.",
            "Ushahidi wa hivi karibuni unachanganya kipaumbele, hatari, na viashiria vya masomo.",
        ),
        tr("School decision support", "Msaada wa maamuzi ya shule"),
    )
    note_box(
        tr(
            "This section combines recent results, performance trends, and subject "
            "evidence to show where support may be most useful. It is a planning "
            "guide, not a final decision.",
            "Sehemu hii inaunganisha matokeo ya hivi karibuni, mwenendo wa ufaulu, "
            "na ushahidi wa masomo ili kuonyesha msaada unaweza kuhitajika zaidi "
            "wapi. Ni mwongozo wa mipango, si uamuzi wa mwisho.",
        )
    )
    if not artifacts:
        st.info(
            tr(
                "Decision-support artifacts are unavailable.",
                "Faili za msaada wa maamuzi hazipatikani.",
            )
        )
        return

    matches = artifacts["interventions"][
        artifacts["interventions"]["school_name"]
        .astype("string")
        .str.casefold()
        .eq(str(school_name).casefold())
    ].sort_values("priority_rank")
    if matches.empty:
        st.info(
            tr(
                "No decision-support record matched this school.",
                "Hakuna rekodi ya msaada wa maamuzi iliyolingana na shule hii.",
            )
        )
        return

    row = matches.iloc[0]
    c1, c2, c3 = st.columns(3)
    with c1:
        render_insight_card(
            tr("Risk Level", "Kiwango cha Hatari"),
            f"{_display_text(row['risk_level'])} ({row['risk_score']:.1f})",
            tr(
                "Composite pass decline, subject failure, and instability",
                "Mchanganyiko wa kushuka kwa ufaulu, kushindwa kwa masomo, na kutotulia",
            ),
            _risk_status(row["risk_level"]),
        )
    with c2:
        render_insight_card(
            tr("National Priority", "Kipaumbele cha Kitaifa"),
            f"#{int(row['priority_rank']):,} | {_display_text(row['priority_category'])}",
            f"{tr('Priority Score', 'Alama ya Kipaumbele')} {row['priority_score']:.1f}",
            "danger"
            if row["priority_category"] in {"Critical", "High"}
            else "warning"
            if row["priority_category"] == "Medium"
            else "good",
        )
    with c3:
        render_insight_card(
            tr("Recommended Intervention", "Uingiliaji Unaopendekezwa"),
            _display_text(str(row["recommended_intervention"]).replace(" Program", "")),
            _display_text(row["problem_detected"]),
            "warning",
        )
    render_narrative(
        f"{_display_text(row['expected_improvement_range'])}. {_display_text(row['assumption_basis'])}"
    )


def render_rankings_decision_support(artifacts, selected_regions, row_count):
    """Render an intervention-priority league table on the Rankings page."""
    render_section_header(
        tr("Intervention Priority Ranking", "Upangaji wa Kipaumbele cha Uingiliaji"),
        tr(
            "Rank schools by the approved severity, decline, and recoverability index.",
            "Panga shule kwa alama iliyoidhinishwa ya uzito wa tatizo, kushuka, na uwezekano wa kuimarika.",
        ),
        tr("Offline evidence", "Ushahidi wa nje ya dashibodi"),
    )
    if not artifacts:
        st.info(
            tr(
                "Decision-support artifacts are unavailable.",
                "Faili za msaada wa maamuzi hazipatikani.",
            )
        )
        return

    interventions = _scoped(artifacts["interventions"], selected_regions)
    if interventions.empty:
        st.info(
            tr(
                "No priority records match the selected regions.",
                "Hakuna rekodi za kipaumbele zinazolingana na mikoa iliyochaguliwa.",
            )
        )
        return

    display = interventions.sort_values("priority_rank").head(row_count).copy()
    display["priority_score"] = pd.to_numeric(
        display["priority_score"], errors="coerce"
    ).round(1)
    display["risk_score"] = pd.to_numeric(
        display["risk_score"], errors="coerce"
    ).round(1)
    for column in ["priority_category", "risk_level", "recommended_intervention"]:
        if column in display.columns:
            display[column] = display[column].map(_display_text)
    st.dataframe(
        display[
            [
                "priority_rank",
                "school_name",
                "region",
                "priority_score",
                "priority_category",
                "risk_score",
                "risk_level",
                "recommended_intervention",
            ]
        ].rename(
            columns={
                "priority_rank": tr("Rank"),
                "school_name": tr("School"),
                "region": tr("Region"),
                "priority_score": tr("Priority Score", "Alama ya Kipaumbele"),
                "priority_category": tr("Priority Level", "Kiwango cha Kipaumbele"),
                "risk_score": tr("Risk Score", "Alama ya Hatari"),
                "risk_level": tr("Risk Level", "Kiwango cha Hatari"),
                "recommended_intervention": tr(
                    "Recommended Intervention",
                    "Uingiliaji Unaopendekezwa",
                ),
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        tr(
            "This ranking is generated offline from observed-derived school and regional records.",
            "Upangaji huu umetengenezwa nje ya dashibodi kutoka rekodi halisi za shule na mikoa zilizochakatwa.",
        )
    )
