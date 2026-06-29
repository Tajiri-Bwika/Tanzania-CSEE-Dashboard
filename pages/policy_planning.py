"""Render the configurable hypothetical 2032 policy-planning simulator."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from charts import polish_chart_legend
from policy_artifacts import load_policy_artifacts
from policy_config import SCENARIOS
from styles import (
    note_box,
    render_insight_card,
    render_key_findings,
    render_page_hero,
    render_section_header,
    render_stat_strip,
    tr,
)


SCENARIO_OPTIONS = {
    "Scenario A": "A",
    "Scenario B": "B",
    "Scenario C": "C",
}


def _scenario_option_label(option):
    return {
        "Scenario A": tr("Scenario A", "Hali A"),
        "Scenario B": tr("Scenario B", "Hali B"),
        "Scenario C": tr("Scenario C", "Hali C"),
    }.get(option, option)


def _scenario_name(name):
    return {
        "Conservative Growth": tr("Conservative Growth", "Ukuaji wa Tahadhari"),
        "Moderate Growth": tr("Moderate Growth", "Ukuaji wa Wastani"),
        "High Growth": tr("High Growth", "Ukuaji wa Juu"),
    }.get(str(name), str(name))


def _scenario_label(option):
    scenario_id = SCENARIO_OPTIONS[option]
    scenario = SCENARIOS[scenario_id]
    return (
        f"{_scenario_option_label(option)} | {_scenario_name(scenario['scenario_name'])} | "
        f"+{scenario['growth_rate'] * 100:.0f}%"
    )


def _policy_insights(summary, regions, schools):
    top_region = regions.sort_values("demand_pressure_index", ascending=False).iloc[0]
    top_school = schools.sort_values("demand_pressure_index", ascending=False).iloc[0]
    region_mover = regions.sort_values("rank_change", ascending=False).iloc[0]
    school_mover = schools.sort_values("rank_change", ascending=False).iloc[0]
    national = [
        tr(
            f"Under {summary['scenario_name']}, projected examination candidates "
            f"increase from {summary['current_candidates']:,.0f} to "
            f"{summary['projected_candidates']:,.0f} by 2032.",
            f"Katika {_scenario_name(summary['scenario_name'])}, watahiniwa wanaokadiriwa kufanya "
            f"mtihani wanaongezeka kutoka {summary['current_candidates']:,.0f} hadi "
            f"{summary['projected_candidates']:,.0f} kufikia 2032.",
        ),
        tr(
            f"{int(summary['high_risk_regions'])} regions reach High or Critical "
            "examination-demand pressure in this scenario.",
            f"Mikoa {int(summary['high_risk_regions'])} inafikia shinikizo la mahitaji "
            "ya mitihani la Juu au Muhimu katika hali hii.",
        ),
    ]
    regional = [
        tr(
            f"{top_region['region']} has the highest demand pressure score "
            f"({top_region['demand_pressure_index']:.1f}) and reaches "
            f"{top_region['projected_candidates']:,.0f} projected candidates.",
            f"{top_region['region']} ina alama ya juu zaidi ya shinikizo la mahitaji "
            f"({top_region['demand_pressure_index']:.1f}) na inafikia watahiniwa "
            f"{top_region['projected_candidates']:,.0f} wanaokadiriwa.",
        ),
        tr(
            f"{region_mover['region']} has the largest regional priority rise, "
            f"moving from #{int(region_mover['priority_rank'])} to "
            f"#{int(region_mover['future_priority_rank'])}.",
            f"{region_mover['region']} ina ongezeko kubwa zaidi la kipaumbele cha "
            f"mkoa, kutoka nafasi #{int(region_mover['priority_rank'])} hadi "
            f"#{int(region_mover['future_priority_rank'])}.",
        ),
    ]
    school = [
        tr(
            f"{top_school['school_name']} records the highest school demand pressure "
            f"score ({top_school['demand_pressure_index']:.1f}).",
            f"{top_school['school_name']} ina alama ya juu zaidi ya shinikizo la "
            f"mahitaji ya shule ({top_school['demand_pressure_index']:.1f}).",
        ),
        tr(
            f"{school_mover['school_name']} has the largest school priority rise, "
            f"moving from #{int(school_mover['priority_rank'])} to "
            f"#{int(school_mover['future_priority_rank'])}.",
            f"{school_mover['school_name']} ina ongezeko kubwa zaidi la kipaumbele "
            f"cha shule, kutoka nafasi #{int(school_mover['priority_rank'])} hadi "
            f"#{int(school_mover['future_priority_rank'])}.",
        ),
    ]
    return national, regional, school


def render_policy_planning():
    """Render the complete policy scenario page from saved synthetic artifacts."""
    render_page_hero(
        tr("2032 Policy Planning Simulator", "Kiigaji cha Mipango ya Sera 2032"),
        tr(
            "Explore future examination demand under alternative enrollment growth scenarios.",
            "Chunguza mahitaji ya mitihani ya baadaye chini ya hali tofauti za ongezeko la uandikishaji.",
        ),
        kicker=tr("Hypothetical Scenario Planning", "Mipango ya Hali ya Kidhahania"),
        panel_title=tr("Target Year", "Mwaka Lengwa"),
        panel_value="2032",
        panel_subtext=tr(
            "Three configurable growth scenarios",
            "Hali tatu za ukuaji zinazoweza kuchaguliwa",
        ),
    )
    note_box(
        tr(
            "Scenario planning for possible CSEE candidate growth after the 2028 education transition.",
            "Mipango ya hali kwa ongezeko linalowezekana la watahiniwa wa CSEE baada ya mpito wa elimu wa 2028.",
        )
    )

    artifacts = load_policy_artifacts()
    if not artifacts:
        st.error(
            tr(
                "Policy-planning artifacts are unavailable.",
                "Faili za mipango ya sera hazipatikani.",
            )
        )
        st.info(
            tr(
                "Run build_policy_artifacts.py offline, then reload this page.",
                "Endesha build_policy_artifacts.py nje ya dashibodi, kisha pakia ukurasa huu upya.",
            )
        )
        return

    render_section_header(
        tr("Scenario Selector", "Kichaguzi cha Hali"),
        tr(
            "Choose one enrollment-growth assumption. Every result below updates to that scenario.",
            "Chagua dhana moja ya ongezeko la uandikishaji. Matokeo yote hapa chini yatabadilika kulingana na hali hiyo.",
        ),
        tr("One active scenario", "Hali moja inayotumika"),
    )
    selected_option = st.segmented_control(
        tr("2032 Growth Scenario", "Hali ya Ukuaji 2032"),
        options=list(SCENARIO_OPTIONS),
        default="Scenario B",
        format_func=_scenario_label,
        key="policy_2032_scenario",
    ) or "Scenario B"
    scenario_id = SCENARIO_OPTIONS[selected_option]
    scenario = SCENARIOS[scenario_id]

    note_box(
        tr(
            f"The selected scenario applies a +{scenario['growth_rate'] * 100:.0f}% candidate-growth "
            "assumption to the latest observed school demand, then refreshes the regional, school, "
            "priority-shift, and action views below.",
            f"Hali iliyochaguliwa inatumia dhana ya ongezeko la watahiniwa la +{scenario['growth_rate'] * 100:.0f}% "
            "kwenye mahitaji ya hivi karibuni ya shule, kisha inasasisha mikoa, shule, "
            "mabadiliko ya kipaumbele, na hatua zilizo hapa chini.",
        )
    )

    note_box(
        tr(
            "This is a configurable hypothetical planning scenario, not a prediction "
            "or a confirmed government policy outcome. All displayed future values "
            "are synthetic scenario estimates.",
            "Hii ni hali ya kidhahania inayoweza kubadilishwa kwa ajili ya mipango, "
            "si utabiri wala matokeo ya sera ya serikali yaliyothibitishwa. Thamani "
            "zote za baadaye ni makadirio ya hali bandia.",
        )
    )

    summary = artifacts["summary"][
        artifacts["summary"]["scenario_id"] == scenario_id
    ].iloc[0]
    regions = artifacts["regions"][
        artifacts["regions"]["scenario_id"] == scenario_id
    ].copy()
    schools = artifacts["schools"][
        artifacts["schools"]["scenario_id"] == scenario_id
    ].copy()
    shifts = artifacts["priority_shift"][
        artifacts["priority_shift"]["scenario_id"] == scenario_id
    ].copy()

    render_stat_strip(
        [
            (
                tr("Projected Candidates", "Watahiniwa Wanaokadiriwa"),
                f"{summary['projected_candidates']:,.0f}",
                tr("Hypothetical 2032 examination demand", "Mahitaji ya mitihani ya kidhahania 2032"),
            ),
            (
                tr("Candidate Growth", "Ongezeko la Watahiniwa"),
                f"+{summary['growth_pct']:.0f}%",
                f"+{summary['candidate_increase']:,.0f} {tr('candidates', 'watahiniwa')}",
            ),
            (
                tr("High-Risk Regions", "Mikoa Yenye Hatari Kubwa"),
                f"{int(summary['high_risk_regions'])}",
                tr("High or Critical demand pressure", "Shinikizo la mahitaji la Juu au Muhimu"),
            ),
            (
                tr("Priority Rank Changes", "Mabadiliko ya Nafasi za Kipaumbele"),
                f"{int(summary['school_rank_increases']):,}",
                tr("Schools moving to a higher priority", "Shule zinazopanda kwenye kipaumbele"),
            ),
        ]
    )

    render_section_header(
        tr("Top Affected Regions", "Mikoa Inayoathirika Zaidi"),
        tr(
            "Regional examination demand ranked by normalized pressure.",
            "Mahitaji ya mitihani ya mikoa yamepangwa kwa shinikizo lililosawazishwa.",
        ),
        tr("Highest pressure first", "Shinikizo kubwa kwanza"),
    )
    note_box(
        tr(
            "Use this table to see where candidate growth could create the strongest regional "
            "examination-readiness pressure. The pressure index compares 2032 demand with each "
            "region's historical candidate level, so it highlights relative strain rather than size alone.",
            "Tumia jedwali hili kuona mahali ongezeko la watahiniwa linaweza kuongeza zaidi "
            "shinikizo la utayari wa mitihani ya mkoa. Alama ya shinikizo inalinganisha mahitaji ya "
            "2032 na kiwango cha kihistoria cha watahiniwa wa kila mkoa, hivyo inaonyesha mzigo wa "
            "ulinganisho badala ya ukubwa pekee.",
        )
    )
    region_display = regions.sort_values(
        "demand_pressure_index",
        ascending=False,
    ).copy()
    region_display["current_candidates"] = region_display[
        "current_candidates"
    ].round().astype(int)
    region_display["projected_candidates"] = region_display[
        "projected_candidates"
    ].round().astype(int)
    region_display["demand_pressure_index"] = region_display[
        "demand_pressure_index"
    ].round(1)
    st.dataframe(
        region_display[
            [
                "region",
                "current_candidates",
                "projected_candidates",
                "growth_pct",
                "demand_pressure_index",
                "future_priority_rank",
            ]
        ].rename(
            columns={
                "region": tr("Region"),
                "current_candidates": tr("Current Candidates", "Watahiniwa wa Sasa"),
                "projected_candidates": tr("Projected Candidates", "Watahiniwa Wanaokadiriwa"),
                "growth_pct": tr("Growth (%)", "Ukuaji (%)"),
                "demand_pressure_index": tr("Demand Pressure", "Shinikizo la Mahitaji"),
                "future_priority_rank": tr("Future Rank", "Nafasi ya Baadaye"),
            }
        ),
        width="stretch",
        hide_index=True,
    )
    top_regions = region_display.head(10).sort_values(
        "demand_pressure_index",
        ascending=True,
    )
    fig_regions = px.bar(
        top_regions,
        x="demand_pressure_index",
        y="region",
        orientation="h",
        color="demand_category",
        text="demand_pressure_index",
        color_discrete_map={
            "Low": "#16a34a",
            "Moderate": "#f59e0b",
            "High": "#f97316",
            "Critical": "#dc2626",
        },
        labels={
            "demand_pressure_index": tr("Demand Pressure Index", "Alama ya Shinikizo la Mahitaji"),
            "region": tr("Region"),
            "demand_category": tr("Demand Category", "Kiwango cha Mahitaji"),
        },
        title=tr(
            "Top 10 Regions by 2032 Demand Pressure",
            "Mikoa 10 ya Juu kwa Shinikizo la Mahitaji 2032",
        ),
    )
    fig_regions.update_layout(
        height=460,
        xaxis_title=tr("Demand Pressure Index", "Alama ya Shinikizo la Mahitaji"),
        yaxis_title=tr("Region"),
    )
    polish_chart_legend(
        fig_regions,
        title=tr("Demand Category", "Kiwango cha Mahitaji"),
    )
    st.plotly_chart(fig_regions, width="stretch")

    render_section_header(
        tr("Top Affected Schools", "Shule Zinazoathirika Zaidi"),
        tr(
            "School examination demand ranked by normalized pressure.",
            "Mahitaji ya mitihani ya shule yamepangwa kwa shinikizo lililosawazishwa.",
        ),
        tr("Top 100 shown", "Shule 100 za juu"),
    )
    note_box(
        tr(
            "This view narrows the same scenario to individual schools. Schools near the top may need "
            "earlier checks on examination rooms, invigilation capacity, materials, and academic support.",
            "Mwonekano huu unashusha hali hiyo hiyo hadi ngazi ya shule moja moja. Shule zilizo juu "
            "zinaweza kuhitaji ukaguzi wa mapema kuhusu vyumba vya mitihani, uwezo wa wasimamizi, "
            "vifaa, na msaada wa kitaaluma.",
        )
    )
    school_display = schools.sort_values(
        "demand_pressure_index",
        ascending=False,
    ).head(100).copy()
    school_display["current_candidates"] = school_display[
        "current_candidates"
    ].round().astype(int)
    school_display["projected_candidates"] = school_display[
        "projected_candidates"
    ].round().astype(int)
    school_display["demand_pressure_index"] = school_display[
        "demand_pressure_index"
    ].round(1)
    st.dataframe(
        school_display[
            [
                "school_name",
                "region",
                "current_candidates",
                "projected_candidates",
                "growth_pct",
                "demand_pressure_index",
                "future_priority_rank",
            ]
        ].rename(
            columns={
                "school_name": tr("School"),
                "region": tr("Region"),
                "current_candidates": tr("Current Candidates", "Watahiniwa wa Sasa"),
                "projected_candidates": tr("Projected Candidates", "Watahiniwa Wanaokadiriwa"),
                "growth_pct": tr("Growth (%)", "Ukuaji (%)"),
                "demand_pressure_index": tr("Demand Pressure", "Shinikizo la Mahitaji"),
                "future_priority_rank": tr("Future Rank", "Nafasi ya Baadaye"),
            }
        ),
        width="stretch",
        hide_index=True,
    )

    render_section_header(
        tr("Priority Shift Analysis", "Uchambuzi wa Mabadiliko ya Kipaumbele"),
        tr(
            "Compare current intervention priority with the scenario-based 2032 rank.",
            "Linganisha kipaumbele cha sasa na nafasi ya 2032 inayotokana na hali iliyochaguliwa.",
        ),
        tr("Positive change means higher priority", "Mabadiliko chanya ni kipaumbele cha juu"),
    )
    note_box(
        tr(
            "Priority shift shows how the scenario could reorder existing intervention priorities. "
            "A positive rank change means an entity moves closer to rank #1 because future demand, "
            "current risk, and current priority now combine into a higher planning signal.",
            "Mabadiliko ya kipaumbele yanaonyesha jinsi hali hii inaweza kupanga upya vipaumbele "
            "vya sasa vya uingiliaji. Mabadiliko chanya ya nafasi yanamaanisha eneo au shule "
            "inasogea karibu na nafasi #1 kwa sababu mahitaji ya baadaye, hatari ya sasa, na "
            "kipaumbele cha sasa vinatoa ishara kubwa zaidi ya mipango.",
        )
    )
    school_shifts = shifts[shifts["entity_type"] == "school"].copy()
    region_shifts = shifts[shifts["entity_type"] == "region"].copy()
    largest_school_movers = school_shifts.sort_values(
        "rank_change",
        ascending=False,
    ).head(10)
    highest_priority_schools = school_shifts.sort_values(
        "future_priority_rank"
    ).head(10)
    highest_priority_regions = region_shifts.sort_values(
        "future_priority_rank"
    ).head(10)

    tab_movers, tab_schools, tab_regions = st.tabs(
        [
            tr("Largest Movers", "Mabadiliko Makubwa"),
            tr("Highest-Risk Schools", "Shule zenye Hatari Kubwa"),
            tr("Highest-Risk Regions", "Mikoa yenye Hatari Kubwa"),
        ]
    )
    with tab_movers:
        st.dataframe(
            largest_school_movers[
                [
                    "school_name",
                    "region",
                    "priority_rank",
                    "future_priority_rank",
                    "rank_change",
                    "future_priority_score",
                ]
            ].rename(
                columns={
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "priority_rank": tr("Current Rank", "Nafasi ya Sasa"),
                    "future_priority_rank": tr("Future Rank", "Nafasi ya Baadaye"),
                    "rank_change": tr("Rank Change", "Mabadiliko ya Nafasi"),
                    "future_priority_score": tr("Future Priority Score", "Alama ya Kipaumbele cha Baadaye"),
                }
            ),
            width="stretch",
            hide_index=True,
        )
    with tab_schools:
        st.dataframe(
            highest_priority_schools[
                [
                    "school_name",
                    "region",
                    "priority_rank",
                    "future_priority_rank",
                    "rank_change",
                    "future_priority_score",
                ]
            ].rename(
                columns={
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "priority_rank": tr("Current Rank", "Nafasi ya Sasa"),
                    "future_priority_rank": tr("Future Rank", "Nafasi ya Baadaye"),
                    "rank_change": tr("Rank Change", "Mabadiliko ya Nafasi"),
                    "future_priority_score": tr("Future Priority Score", "Alama ya Kipaumbele cha Baadaye"),
                }
            ),
            width="stretch",
            hide_index=True,
        )
    with tab_regions:
        st.dataframe(
            highest_priority_regions[
                [
                    "region",
                    "priority_rank",
                    "future_priority_rank",
                    "rank_change",
                    "future_priority_score",
                ]
            ].rename(
                columns={
                    "region": tr("Region"),
                    "priority_rank": tr("Current Rank", "Nafasi ya Sasa"),
                    "future_priority_rank": tr("Future Rank", "Nafasi ya Baadaye"),
                    "rank_change": tr("Rank Change", "Mabadiliko ya Nafasi"),
                    "future_priority_score": tr("Future Priority Score", "Alama ya Kipaumbele cha Baadaye"),
                }
            ),
            width="stretch",
            hide_index=True,
        )

    mover_chart = largest_school_movers.sort_values("rank_change")
    fig_movers = px.bar(
        mover_chart,
        x="rank_change",
        y="school_name",
        orientation="h",
        text="rank_change",
        color_discrete_sequence=["#2563eb"],
        labels={
            "rank_change": tr("Rank Increase", "Ongezeko la Nafasi"),
            "school_name": tr("School"),
        },
        title=tr(
            "Top 10 School Priority Rank Increases",
            "Ongezeko 10 Kubwa la Nafasi za Kipaumbele za Shule",
        ),
    )
    fig_movers.update_layout(
        height=480,
        xaxis_title=tr("Rank Increase", "Ongezeko la Nafasi"),
        yaxis_title=tr("School"),
    )
    polish_chart_legend(fig_movers, show=False)
    st.plotly_chart(fig_movers, width="stretch")

    render_section_header(
        tr("Policy Insights", "Maarifa ya Sera"),
        tr(
            "Automatic interpretations of national, regional, and school scenario evidence.",
            "Tafsiri za moja kwa moja za ushahidi wa hali ya kitaifa, mikoa, na shule.",
        ),
        tr("Scenario evidence", "Ushahidi wa hali"),
    )
    national_insights, regional_insights, school_insights = _policy_insights(
        summary,
        regions,
        schools,
    )
    render_key_findings(
        national_insights,
        title=tr("National Insights", "Maarifa ya Kitaifa"),
        subtitle=tr("What changes nationally under this assumption.", "Kinachobadilika kitaifa chini ya dhana hii."),
    )
    render_key_findings(
        regional_insights,
        title=tr("Regional Insights", "Maarifa ya Mikoa"),
        subtitle=tr("Where regional demand and priority move most.", "Mahali ambapo mahitaji na kipaumbele cha mkoa vinabadilika zaidi."),
    )
    render_key_findings(
        school_insights,
        title=tr("School Insights", "Maarifa ya Shule"),
        subtitle=tr("Which schools rise most under the selected scenario.", "Shule zinazopanda zaidi chini ya hali iliyochaguliwa."),
    )

    render_section_header(
        tr("Recommended Planning Actions", "Hatua za Mipango Zinazopendekezwa"),
        tr(
            "Planning suggestions based on the selected scenario, not guaranteed outcomes.",
            "Mapendekezo ya mipango kulingana na hali iliyochaguliwa, si matokeo yaliyohakikishwa.",
        ),
        tr("Decision support", "Msaada wa maamuzi"),
    )
    note_box(
        tr(
            "Treat these actions as a planning shortlist. They point to where staff can validate "
            "capacity, monitor demand, and stage support before committing resources.",
            "Chukulia hatua hizi kama orodha fupi ya mipango. Zinaonyesha maeneo ya kuthibitisha "
            "uwezo, kufuatilia mahitaji, na kupanga msaada kabla ya kugawa rasilimali.",
        )
    )
    action_columns = st.columns(4)
    actions = [
        (
            tr("Prioritize High-Demand Regions", "Tanguliza Mikoa yenye Mahitaji Makubwa"),
            str(regions.sort_values("demand_pressure_index", ascending=False).iloc[0]["region"]),
            tr("Begin detailed examination-readiness review here.", "Anza tathmini ya kina ya utayari wa mitihani hapa."),
        ),
        (
            tr("Increase Readiness Monitoring", "Ongeza Ufuatiliaji wa Utayari"),
            f"{int(summary['high_risk_regions'])} {tr('regions', 'mikoa')}",
            tr("Track candidate demand before each planning cycle.", "Fuatilia mahitaji ya watahiniwa kabla ya kila mzunguko wa mipango."),
        ),
        (
            tr("Support Priority Schools", "Saidia Shule za Kipaumbele"),
            str(highest_priority_schools.iloc[0]["school_name"]),
            tr("Review academic support and examination preparation.", "Pitia msaada wa kitaaluma na maandalizi ya mitihani."),
        ),
        (
            tr("Review Priority Shifts", "Pitia Mabadiliko ya Kipaumbele"),
            f"{int(summary['school_rank_increases']):,} {tr('schools', 'shule')}",
            tr("Use rank movement to stage follow-up, not as a final verdict.", "Tumia mabadiliko ya nafasi kupanga ufuatiliaji, si kama uamuzi wa mwisho."),
        ),
    ]
    for column, (title, value, subtext) in zip(action_columns, actions):
        with column:
            render_insight_card(title, value, subtext, "warning")

    st.caption(
        tr(
            "Method: projected candidates = latest observed candidates x scenario "
            "growth factor. Demand pressure compares projected candidates with the "
            "historical annual average. Future priority combines risk (40%), current "
            "priority (40%), and demand pressure (20%).",
            "Mbinu: watahiniwa wanaokadiriwa = watahiniwa wa mwisho walioonekana x "
            "kigezo cha ukuaji wa hali. Shinikizo la mahitaji linalinganisha watahiniwa "
            "wanaokadiriwa na wastani wa kihistoria wa mwaka. Kipaumbele cha baadaye "
            "kinaunganisha hatari (40%), kipaumbele cha sasa (40%), na shinikizo la "
            "mahitaji (20%).",
        )
    )
