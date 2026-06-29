"""Render the national CSEE overview, risks, trends, and saved forecasts."""

import pandas as pd
import plotly.express as px
import streamlit as st

from charts import (
    forecast_line_chart,
    polish_chart_legend,
    professional_series_label,
    weighted_pass_rate_by_group,
    yoy_bar_chart,
)
from decision_artifacts import load_decision_artifacts
from decision_ui import render_dashboard_decision_support
from filters import (
    filter_school_data,
    filter_subject_data,
    region_filter_options,
    selected_region_values,
    sync_region_multiselect_state,
)
from insights import (
    attendance_efficiency,
    distribution_insight_text,
    national_key_findings,
    performance_change,
    policy_summary_items,
    regional_gap,
    last_n_year_slope,
    momentum_status,
    render_momentum_indicator,
    render_policy_summary,
    risk_scatter_data,
    risk_schools,
    subject_strength_table,
    trend_insight_text,
)
from metrics import metric_display_name, school_kpi_values, school_ranking_summary
from model_artifacts import load_model_artifacts
from styles import (
    localize_phrase,
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


def build_model_artifacts(_school_df):
    """Load saved forecast artifacts without exposing maintenance controls."""
    artifacts = load_model_artifacts()
    if artifacts is None:
        st.warning(tr("Forecast results are currently unavailable.", "Matokeo ya makadirio hayapatikani kwa sasa."))
    return artifacts


def render_model_comparison(artifacts):
    """Render advanced holdout metrics and selected model explanations."""
    render_section_header(
        "Advanced Model Comparison",
        "Technical validation details for researchers and evaluators.",
        "Advanced",
    )
    st.caption(
        "Models are evaluated on the latest holdout year using MAE, RMSE, R², and MAPE. "
        "Only the selected winner is used for future forecasts."
    )

    metrics_df = artifacts["metrics"].copy() if artifacts else pd.DataFrame()
    if metrics_df.empty:
        st.info("Model comparison is unavailable because there are not enough valid training rows.")
        return

    selected_rows = metrics_df[metrics_df["Selected"]].copy()
    c1, c2 = st.columns(2)

    for container, target_name, target_key in [
        (c1, "GPA", "gpa"),
        (c2, "Pass Rate", "pass_rate"),
    ]:
        with container:
            target_rows = selected_rows[selected_rows["Target"] == target_name]
            metadata = artifacts.get("metadata", {}).get(target_key, {})
            if target_rows.empty:
                render_insight_card(
                    f"Selected {target_name} Model",
                    "N/A",
                    "No model passed evaluation.",
                    "warning",
                )
                continue

            row = target_rows.iloc[0]
            render_insight_card(
                f"Selected {target_name} Model",
                row["Model"],
                f"RMSE {row['RMSE']:.3f} | MAE {row['MAE']:.3f} | MAPE {row['MAPE']:.2f}%",
                "good",
            )
            if metadata.get("selection_reason"):
                render_narrative(metadata["selection_reason"])

    display_cols = ["Target", "Model", "MAE", "RMSE", "R2", "MAPE", "Status", "Selected"]
    display_df = metrics_df[display_cols].copy()
    for col in ["MAE", "RMSE", "R2", "MAPE"]:
        display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(4)
    display_df["Selected"] = display_df["Selected"].map({True: "Winner", False: ""})

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "MAE": st.column_config.NumberColumn("MAE", format="%.4f"),
            "RMSE": st.column_config.NumberColumn("RMSE", format="%.4f"),
            "R2": st.column_config.NumberColumn("R²", format="%.4f"),
            "MAPE": st.column_config.NumberColumn("MAPE (%)", format="%.4f"),
        },
    )


def ml_forecast_line_chart(
    history_df,
    forecast_df,
    target,
    title,
    y_title,
    lower_bound=None,
    upper_bound=None,
):
    """Combine historical regional values with saved model forecast values."""
    if history_df.empty:
        return None

    fig = px.line(
        history_df,
        x="year",
        y=target,
        color="region",
        markers=True,
        title=title,
        labels={"year": tr("Year"), target: tr(y_title), "region": tr("Region")},
    )
    for trace in fig.data:
        trace.name = professional_series_label(trace.name, "Actual", "region")

    if not forecast_df.empty:
        for region in forecast_df["region"].dropna().unique():
            regional_history = history_df[history_df["region"] == region].sort_values("year")
            regional_forecast = forecast_df[forecast_df["region"] == region].sort_values("year")
            if regional_forecast.empty:
                continue

            forecast_points = regional_forecast[["year", target]].copy()
            if not regional_history.empty:
                forecast_points = pd.concat(
                    [regional_history[["year", target]].tail(1), forecast_points],
                    ignore_index=True,
                )

            history_trace = next(
                (
                    trace
                    for trace in fig.data
                    if trace.name == professional_series_label(region, "Actual", "region")
                ),
                None,
            )
            history_color = (
                history_trace.line.color
                if history_trace is not None
                else None
            )
            fig.add_scatter(
                x=forecast_points["year"],
                y=forecast_points[target],
                mode="lines+markers",
                line={
                    "dash": "dot",
                    "width": 3,
                    **({"color": history_color} if history_color else {}),
                },
                marker={
                    "size": 8,
                    **({"color": history_color} if history_color else {}),
                },
                name=professional_series_label(region, "Forecast", "region"),
            )

    fig.update_layout(
        height=440,
        hovermode="x unified",
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    if lower_bound is not None or upper_bound is not None:
        fig.update_yaxes(range=[lower_bound, upper_bound])
    return polish_chart_legend(fig, title=tr("Region and Series"))


def division_distribution_by_year_chart(division_year_df):
    """Build a readable stacked annual NECTA division distribution."""
    fig = px.bar(
        division_year_df,
        x="year",
        y="Count",
        color="Division",
        barmode="stack",
        text="Count",
        color_discrete_map={
            "Div I": "#16a34a",
            "Div II": "#2563eb",
            "Div III": "#f59e0b",
            "Div IV": "#f97316",
            "Div 0": "#dc2626",
        },
    )
    fig.update_layout(
        title=tr("NECTA Division Distribution by Year", "Mgawanyo wa Madaraja ya NECTA kwa Mwaka"),
        xaxis_title=tr("Year"),
        yaxis_title=tr("Number of Candidates"),
        height=500,
        hovermode="x unified",
        margin={"l": 70, "r": 24, "t": 92, "b": 60},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "title": None,
            "bgcolor": "rgba(255,255,255,0.88)",
        },
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=sorted(division_year_df["year"].dropna().unique().tolist()),
        fixedrange=False,
    )
    fig.update_traces(
        texttemplate="%{y:,.0f}",
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            f"{tr('Year')}: %{{x}}<br>"
            f"{tr('Candidates', 'Watahiniwa')}: %{{y:,.0f}}<extra></extra>"
        ),
    )
    return polish_chart_legend(fig, title=tr("NECTA Division"))


def render_executive_summary(filtered_school_df, filtered_subject_df):
    """Render countrywide comparison cards independent of region selection."""
    render_section_header(
        tr("Executive Summary", "Muhtasari wa Kitaifa"),
        tr(
            "Countrywide regional, school, subject, and momentum signals for the selected year window.",
            "Viashiria vya kitaifa vya mikoa, shule, masomo, na mwenendo kwa kipindi kilichochaguliwa.",
        ),
        tr("National comparison", "Ulinganisho wa kitaifa"),
    )

    region_gpa_df = pd.DataFrame()
    if not filtered_school_df.empty and {"region", "gpa"}.issubset(filtered_school_df.columns):
        valid_region_gpa_df = filtered_school_df[
            filtered_school_df["gpa"].notna() &
            (filtered_school_df["region"].astype(str).str.upper() != "UNKNOWN")
        ]
        region_gpa_df = (
            valid_region_gpa_df.groupby("region", as_index=False)["gpa"]
            .mean()
            .dropna(subset=["gpa"])
            .sort_values("gpa")
        )

    risk_df = risk_scatter_data(filtered_school_df)
    subject_df = subject_strength_table(filtered_subject_df)
    pass_trend_df = weighted_pass_rate_by_group(filtered_school_df, ["year"]).sort_values("year")
    pass_slope = last_n_year_slope(pass_trend_df, "year", "pass_rate")
    pass_status, pass_badge = momentum_status(pass_slope, "pass_rate")

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    with c1:
        if not region_gpa_df.empty:
            best_region = region_gpa_df.iloc[0]
            render_insight_card(
                tr("Best Region by GPA", "Mkoa Bora kwa GPA"),
                str(best_region["region"]),
                f"{tr('Average GPA')} {best_region['gpa']:.2f}",
                "good"
            )
        else:
            render_insight_card(
                tr("Best Region by GPA", "Mkoa Bora kwa GPA"),
                "N/A",
                tr("No regional GPA data available", "Hakuna data ya GPA ya mikoa."),
                "neutral",
            )

    with c2:
        if not region_gpa_df.empty:
            weakest_region = region_gpa_df.iloc[-1]
            status = "danger" if weakest_region["gpa"] >= 4 else "warning"
            render_insight_card(
                tr("Weakest Region by GPA", "Mkoa Dhaifu kwa GPA"),
                str(weakest_region["region"]),
                f"{tr('Average GPA')} {weakest_region['gpa']:.2f}",
                status
            )
        else:
            render_insight_card(
                tr("Weakest Region by GPA", "Mkoa Dhaifu kwa GPA"),
                "N/A",
                tr("No regional GPA data available", "Hakuna data ya GPA ya mikoa."),
                "neutral",
            )

    with c3:
        if not risk_df.empty:
            highest_risk = risk_df.sort_values("division_0_rate", ascending=False).iloc[0]
            status = "danger" if highest_risk["division_0_rate"] >= 15 else "warning"
            render_insight_card(
                tr("Highest-Risk School", "Shule Yenye Hatari Kubwa"),
                str(highest_risk["school_name"]),
                f"{tr('Division 0 rate', 'Kiwango cha Division 0')} {highest_risk['division_0_rate']:.1f}%",
                status
            )
        else:
            render_insight_card(
                tr("Highest-Risk School", "Shule Yenye Hatari Kubwa"),
                "N/A",
                tr("No Division 0 risk data available", "Hakuna data ya hatari ya Division 0."),
                "neutral",
            )

    with c4:
        if not subject_df.empty:
            strongest_subject = subject_df.iloc[0]
            render_insight_card(
                tr("Strongest Subject by GPA", "Somo Bora kwa GPA"),
                str(strongest_subject["subject_name"]),
                f"GPA {strongest_subject['subject_gpa']:.2f}, {tr('Pass Rate')} {strongest_subject['pass_rate']:.1f}%",
                "good"
            )
        else:
            render_insight_card(
                tr("Strongest Subject by GPA", "Somo Bora kwa GPA"),
                "N/A",
                tr("No subject data available", "Hakuna data ya masomo."),
                "neutral",
            )

    with c5:
        if not subject_df.empty:
            weakest_subject = subject_df.iloc[-1]
            status = "danger" if weakest_subject["subject_gpa"] >= 4 else "warning"
            render_insight_card(
                tr("Weakest Subject by GPA", "Somo Dhaifu kwa GPA"),
                str(weakest_subject["subject_name"]),
                f"GPA {weakest_subject['subject_gpa']:.2f}, {tr('Pass Rate')} {weakest_subject['pass_rate']:.1f}%",
                status
            )
        else:
            render_insight_card(
                tr("Weakest Subject by GPA", "Somo Dhaifu kwa GPA"),
                "N/A",
                tr("No subject data available", "Hakuna data ya masomo."),
                "neutral",
            )

    with c6:
        slope_text = (
            tr("Not enough history", "Historia haitoshi")
            if pass_slope is None
            else f"{tr('Last-3-year slope', 'Mteremko wa miaka 3 ya mwisho')} {pass_slope:+.2f} {tr('points/year', 'pointi kwa mwaka')}"
        )
        render_insight_card(
            tr("Pass-Rate Momentum", "Mwenendo wa Kiwango cha Ufaulu"),
            pass_status,
            slope_text,
            pass_badge
        )


def render_dashboard(school_df, subject_df, all_regions, all_years, all_subjects):
    """Render the complete national and regional dashboard page."""
    if school_df.empty or not all_years:
        render_page_hero(
            tr("NECTA CSEE Performance Dashboard", "Dashibodi ya Ufaulu wa NECTA CSEE"),
            tr(
                "National performance intelligence for Tanzania secondary schools, combining regional, school, subject, risk, and predictive analysis.",
                "Taarifa za kitaifa za ufaulu wa shule za sekondari Tanzania, zikijumuisha uchambuzi wa mikoa, shule, masomo, hatari, na makadirio.",
            ),
            kicker=tr("National Education Intelligence", "Taarifa za Kitaifa za Elimu"),
            panel_title=tr("Coverage", "Upeo wa Data"),
            panel_value=tr("No data", "Hakuna data"),
            panel_subtext=tr(
                "No school records or valid years are available for analysis.",
                "Hakuna rekodi za shule au miaka halali kwa uchambuzi.",
            ),
        )
        st.warning(
            tr(
                "The dashboard has no school data to display. Check that the combined school CSV contains records and a valid year column.",
                "Dashibodi haina data ya shule ya kuonyesha. Hakikisha faili ya CSV ya shule iliyounganishwa ina rekodi na safu halali ya mwaka.",
            )
        )
        return

    render_page_hero(
        tr("NECTA CSEE Performance Dashboard", "Dashibodi ya Ufaulu wa NECTA CSEE"),
        tr(
            "National performance intelligence for Tanzania secondary schools, combining regional, school, subject, risk, and predictive analysis.",
            "Taarifa za kitaifa za ufaulu wa shule za sekondari Tanzania, zikijumuisha uchambuzi wa mikoa, shule, masomo, hatari, na makadirio.",
        ),
        kicker=tr("National Education Intelligence", "Taarifa za Kitaifa za Elimu"),
        panel_title=tr("Coverage", "Upeo wa Data"),
        panel_value=f"{min(all_years)}-{max(all_years)}",
        panel_subtext=tr(
            f"{len(all_regions)} regions available with compact All-region filtering.",
            f"Mikoa {len(all_regions)} inapatikana kwa kichujio kifupi cha mikoa yote.",
        ),
    )
    render_measure_guide(include_forecast=True)

    render_section_header(
        tr("Dashboard Controls", "Vidhibiti vya Dashibodi"),
        tr(
            "Choose one or more regions and the historical window used throughout this page.",
            "Chagua mkoa mmoja au zaidi na kipindi cha historia kinachotumika kwenye ukurasa huu.",
        ),
        tr("National dataset", "Data ya kitaifa"),
    )

    d1, d2 = st.columns([1.2, 1.2])

    with d1:
        region_key = "dashboard_region_options"
        if region_key in st.session_state:
            sync_region_multiselect_state(st.session_state, region_key, all_regions)

        def sync_dashboard_region_options():
            sync_region_multiselect_state(st.session_state, region_key, all_regions)

        selected_region_options = st.multiselect(
            tr("Region"),
            options=region_filter_options(all_regions),
            default=["All"],
            format_func=lambda option: tr("All", "Yote") if option == "All" else option,
            key=region_key,
            on_change=sync_dashboard_region_options
        )
        selected_regions = selected_region_values(selected_region_options, all_regions)

    with d2:
        selected_years = st.select_slider(
            tr("Year"),
            options=all_years,
            value=(min(all_years), max(all_years)),
            key="dashboard_years"
        )

    filtered_school_df = filter_school_data(
        school_df,
        regions=selected_regions,
        years=selected_years
    )

    filtered_subject_df = filter_subject_data(
        subject_df,
        regions=selected_regions,
        years=selected_years
    )

    national_school_df = filter_school_data(
        school_df,
        years=selected_years
    )
    national_subject_df = filter_subject_data(
        subject_df,
        years=selected_years
    )

    kpis = school_kpi_values(filtered_school_df)

    render_stat_strip([
        ("Total Schools", f"{kpis['total_schools']:,}", "Unique schools in selection"),
        ("Average GPA", kpis["avg_gpa_display"], "Lower NECTA GPA is better"),
        ("Pass Rate", kpis["avg_pass_rate_display"], "Passed candidates over sat"),
        ("Division I", kpis["div1_percent_display"], "Share of sat candidates"),
    ])

    render_executive_summary(national_school_df, national_subject_df)
    render_key_findings(
        national_key_findings(
            national_school_df,
            national_subject_df,
            load_model_artifacts(),
        ),
        title="Key Findings",
        subtitle="The national result, the main gap, and the immediate planning priority.",
    )
    render_dashboard_decision_support(
        load_decision_artifacts(),
        selected_regions,
    )

    render_section_header(
        tr("Regional GPA Trend", "Mwenendo wa GPA ya Mikoa"),
        tr(
            "Compare average regional GPA over time; lower GPA represents stronger performance.",
            "Linganisha wastani wa GPA ya mikoa kwa muda; GPA ya chini inaonyesha ufaulu bora.",
        ),
        tr("Regional trend", "Mwenendo wa mikoa"),
    )
    regional_gpa_df = (
        filtered_school_df.groupby(["year", "region"], as_index=False)["gpa"]
        .mean()
        .sort_values(["year", "region"])
    )

    if not regional_gpa_df.empty:
        fig_trend = forecast_line_chart(
            regional_gpa_df,
            "year",
            "gpa",
            tr("Average GPA"),
            group_col="region",
            lower_bound=0,
            upper_bound=5,
            height=420
        )
        if fig_trend is not None:
            st.plotly_chart(fig_trend, width="stretch")
            render_chart_insight(
                trend_insight_text(
                    regional_gpa_df,
                    "year",
                    "gpa",
                    "GPA",
                    group_col="region",
                    context="selected regions"
                )
            )
    else:
        st.info(tr("No regional GPA trend data available.", "Hakuna data ya mwenendo wa GPA ya mikoa."))

    m1, m2 = st.columns(2)
    with m1:
        render_momentum_indicator(
            regional_gpa_df,
            "year",
            "gpa",
            tr("Regional GPA"),
            tr("selected regions", "mikoa iliyochaguliwa")
        )
    with m2:
        dashboard_pass_momentum_df = weighted_pass_rate_by_group(filtered_school_df, ["year"])
        render_momentum_indicator(
            dashboard_pass_momentum_df,
            "year",
            "pass_rate",
            tr("Pass Rate"),
            tr("selected regions", "mikoa iliyochaguliwa")
        )

    render_section_header(
        tr("Year-over-Year Change", "Mabadiliko ya Mwaka hadi Mwaka"),
        tr(
            "Separate annual movement from the longer-term GPA and pass-rate trend.",
            "Tenganisha mabadiliko ya kila mwaka na mwenendo wa muda mrefu wa GPA na kiwango cha ufaulu.",
        ),
        tr("Momentum", "Mwenendo"),
    )
    y1, y2 = st.columns(2)
    dashboard_gpa_yoy_df = (
        filtered_school_df.groupby("year", as_index=False)["gpa"]
        .mean()
        .sort_values("year")
    )
    dashboard_pass_yoy_df = weighted_pass_rate_by_group(filtered_school_df, ["year"]).sort_values("year")
    with y1:
        fig_yoy, yoy_df = yoy_bar_chart(
            dashboard_gpa_yoy_df,
            "year",
            "gpa",
            tr("GPA Year-over-Year Change", "Mabadiliko ya GPA Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars mean the GPA moved in the right direction because lower NECTA GPA is better; "
                "red bars mean the average GPA worsened from the previous year.",
                "Mabao ya kijani yanaonyesha GPA imeenda upande mzuri kwa sababu GPA ya NECTA ikiwa chini ni bora; "
                "mabao mekundu yanaonyesha wastani wa GPA umeharibika ukilinganishwa na mwaka uliopita."
            )
        else:
            st.info(tr(
                "At least two years of GPA data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya GPA ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))
    with y2:
        fig_yoy, yoy_df = yoy_bar_chart(
            dashboard_pass_yoy_df,
            "year",
            "pass_rate",
            tr("Pass Rate Year-over-Year Change", "Mabadiliko ya Kiwango cha Ufaulu Mwaka hadi Mwaka")
        )
        if fig_yoy is not None:
            st.plotly_chart(fig_yoy, width="stretch")
            render_chart_insight(
                "Green bars show years where pass rate improved; red bars show years where pass rate fell.",
                "Mabao ya kijani yanaonyesha miaka ambayo kiwango cha ufaulu kiliongezeka; mabao mekundu yanaonyesha miaka ambayo kiwango hicho kilishuka."
            )
        else:
            st.info(tr(
                "At least two years of pass rate data are needed for year-over-year change.",
                "Inahitajika angalau miaka miwili ya data ya ufaulu ili kuona mabadiliko ya mwaka hadi mwaka.",
            ))

    render_section_header(
        tr("Regional Pass Rate Heatmap", "Ramani ya Joto ya Ufaulu wa Mikoa"),
        tr(
            "Scan regional pass-rate differences across the selected years.",
            "Angalia tofauti za kiwango cha ufaulu wa mikoa katika miaka iliyochaguliwa.",
        ),
        tr("Regional comparison", "Ulinganisho wa mikoa"),
    )
    regional_pass_heatmap_df = weighted_pass_rate_by_group(
        filtered_school_df,
        ["region", "year"]
    )
    if not regional_pass_heatmap_df.empty:
        heatmap_pivot = regional_pass_heatmap_df.pivot(
            index="region",
            columns="year",
            values="pass_rate"
        ).sort_index()
        fig_heatmap = px.imshow(
            heatmap_pivot,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="YlGnBu",
            labels={"color": tr("Pass Rate (%)")}
        )
        fig_heatmap.update_layout(
            title=tr("Regional Pass Rate by Year", "Kiwango cha Ufaulu wa Mikoa kwa Mwaka"),
            xaxis_title=tr("Year"),
            yaxis_title=tr("Region"),
            height=360
        )
        polish_chart_legend(fig_heatmap, show=False)
        st.plotly_chart(fig_heatmap, width="stretch")
        render_chart_insight(
            trend_insight_text(
                regional_pass_heatmap_df,
                "year",
                "pass_rate",
                "pass rate",
                group_col="region",
                context="selected regions"
            )
        )
    else:
        st.info(tr(
            "No regional pass rate data available for the heatmap.",
            "Hakuna data ya kiwango cha ufaulu wa mikoa kwa ramani ya joto.",
        ))

    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown(f"### {tr('Division Distribution', 'Mgawanyo wa Madaraja')}")
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
            title=tr("Candidate Distribution by NECTA Division", "Mgawanyo wa Watahiniwa kwa Daraja la NECTA"),
            xaxis_title=tr("Division"),
            yaxis_title=tr("Number of Candidates"),
            height=360
        )
        polish_chart_legend(fig_div, show=False)
        st.plotly_chart(fig_div, width="stretch")
        render_chart_insight(
            distribution_insight_text(
                division_summary,
                "Division",
                "Count",
                "the selected dashboard filters"
            )
        )

    with right_col:
        st.markdown(f"### {tr('Top Schools', 'Shule Bora')}")
        top_schools_df = (
            school_ranking_summary(filtered_school_df)
            .sort_values("gpa", ascending=True)
            .head(10)
        )

        if not top_schools_df.empty:
            top_schools_df["Rank"] = range(1, len(top_schools_df) + 1)
            top_schools_df["gpa"] = top_schools_df["gpa"].round(2)
            top_schools_df = top_schools_df[["Rank", "school_name", "region", "gpa"]]
            top_schools_df.columns = [tr("Rank"), tr("School"), tr("Region"), "GPA"]
            st.dataframe(top_schools_df, width="stretch", hide_index=True)
        else:
            st.info(tr("No top schools data available.", "Hakuna data ya shule bora."))

    render_section_header(
        tr("Division Distribution by Year", "Mgawanyo wa Madaraja kwa Mwaka"),
        tr(
            "Track how candidate outcomes shift between Divisions I-IV and Division 0.",
            "Fuatilia jinsi matokeo ya watahiniwa yanavyobadilika kati ya Daraja I-IV na Division 0.",
        ),
        tr("Outcome structure", "Muundo wa matokeo"),
    )
    division_cols = {
        "division_1": "Div I",
        "division_2": "Div II",
        "division_3": "Div III",
        "division_4": "Div IV",
        "division_0": "Div 0"
    }
    available_division_cols = [col for col in division_cols if col in filtered_school_df.columns]
    if available_division_cols:
        division_year_df = (
            filtered_school_df.groupby("year", as_index=False)[available_division_cols]
            .sum()
            .sort_values("year")
        )
        division_year_df = division_year_df.melt(
            id_vars="year",
            value_vars=available_division_cols,
            var_name="Division",
            value_name="Count"
        )
        division_year_df["Division"] = division_year_df["Division"].map(division_cols)
        fig_stack = division_distribution_by_year_chart(division_year_df)
        st.plotly_chart(fig_stack, width="stretch")
        render_chart_insight(
            "This stacked view shows how candidate quality distribution changes over time. "
            "Growth in Div I-IV suggests healthier outcomes, while growth in Div 0 signals intervention pressure.",
            "Mwonekano huu wa tabaka unaonyesha jinsi mgawanyo wa madaraja ya watahiniwa unavyobadilika kwa muda. "
            "Ongezeko la Div I-IV linaashiria matokeo bora zaidi, wakati ongezeko la Div 0 linaonyesha hitaji la uingiliaji."
        )
    else:
        st.info(tr(
            "Division columns are missing for stacked yearly analysis.",
            "Safu za madaraja hazipo kwa uchambuzi wa kila mwaka.",
        ))

    render_section_header(
        tr("Subject Performance by Region", "Ufaulu wa Somo kwa Mkoa"),
        tr(
            "Use the local subject control to compare one subject across regions and years.",
            "Tumia kichujio cha somo kulinganisha somo moja kati ya mikoa na miaka.",
        ),
        tr("Subject lens", "Mtazamo wa somo"),
    )

    s1, s2 = st.columns([1, 2])
    with s1:
        local_subject = st.selectbox(
            tr("Local Subject Filter", "Kichujio cha Somo"),
            options=all_subjects,
            key="dashboard_local_subject"
        )
    with s2:
        note_box(tr(
            "This local subject filter only controls the subject performance trend chart below.",
            "Kichujio hiki cha somo kinadhibiti tu chati ya mwenendo wa ufaulu wa somo iliyo hapa chini.",
        ))

    subject_trend_df = filter_subject_data(
        subject_df,
        regions=selected_regions,
        years=selected_years,
        subject=local_subject
    )

    subject_region_trend_df = (
        subject_trend_df.groupby(["year", "region"], as_index=False)["subject_gpa"]
        .mean()
        .sort_values(["year", "region"])
    )

    if not subject_region_trend_df.empty:
        fig_subject_region = forecast_line_chart(
            subject_region_trend_df,
            "year",
            "subject_gpa",
            tr(f"{local_subject} Average GPA", f"Wastani wa GPA ya {local_subject}"),
            group_col="region",
            lower_bound=0,
            upper_bound=5,
            height=420
        )
        if fig_subject_region is not None:
            st.plotly_chart(fig_subject_region, width="stretch")
            render_chart_insight(
                trend_insight_text(
                    subject_region_trend_df,
                    "year",
                    "subject_gpa",
                    f"{local_subject} GPA",
                    group_col="region",
                    context="selected regions"
                )
            )
    else:
        st.info(tr(
            "No subject performance trend data available for this subject.",
            "Hakuna data ya mwenendo wa ufaulu kwa somo hili.",
        ))

    render_section_header(
        tr("Subject Performance Preview", "Muhtasari wa Ufaulu wa Masomo"),
        tr(
            "A compact table of subject GPA, candidates, and weighted pass rate.",
            "Jedwali fupi la GPA ya somo, watahiniwa, na kiwango cha ufaulu kilichopimwa kwa idadi.",
        ),
        tr("Current filters", "Vichujio vya sasa"),
    )

    if not filtered_subject_df.empty:
        preview_cols = ["subject_name", "subject_gpa", "pass", "sat"]
        available_cols = [c for c in preview_cols if c in filtered_subject_df.columns]

        if len(available_cols) == 4:

            temp_df = filtered_subject_df.copy()

            # Force numeric before grouping
            temp_df["subject_gpa"] = pd.to_numeric(temp_df["subject_gpa"], errors="coerce")
            temp_df["pass"] = pd.to_numeric(temp_df["pass"], errors="coerce")
            temp_df["sat"] = pd.to_numeric(temp_df["sat"], errors="coerce")

            subject_summary = (
                temp_df.groupby("subject_name", as_index=False)
                .agg({
                    "subject_gpa": "mean",
                    "pass": "sum",
                    "sat": "sum"
                })
            )

            subject_summary["pass_rate"] = (
                subject_summary["pass"] /
                subject_summary["sat"].where(subject_summary["sat"] != 0)
            ) * 100

            # Force numeric again after calculation
            subject_summary["pass_rate"] = pd.to_numeric(subject_summary["pass_rate"], errors="coerce")
            subject_summary["subject_gpa"] = pd.to_numeric(subject_summary["subject_gpa"], errors="coerce")

            subject_summary["subject_gpa"] = subject_summary["subject_gpa"].round(2)
            subject_summary["pass_rate"] = subject_summary["pass_rate"].round(1).fillna(0)

            subject_summary["pass"] = subject_summary["pass"].fillna(0).astype(int)
            subject_summary["sat"] = subject_summary["sat"].fillna(0).astype(int)

            st.dataframe(
                subject_summary.rename(columns={
                    "subject_name": tr("Subject"),
                    "subject_gpa": tr("Avg Subject GPA", "Wastani wa GPA ya Somo"),
                    "pass": tr("Passed"),
                    "sat": tr("Sat"),
                    "pass_rate": tr("Pass Rate (%)")
                }),
                width="stretch",
                hide_index=True
            )
        else:
            st.info(tr(
                "Required subject columns are missing for preview.",
                "Safu muhimu za masomo hazipo kwa muhtasari.",
            ))
    else:
        st.info(tr(
            "No subject data available for the selected filters.",
            "Hakuna data ya masomo kwa vichujio vilivyochaguliwa.",
        ))

    render_section_header(
        tr("Subject Performance Ranking", "Upangaji wa Ufaulu wa Masomo"),
        tr(
            "Compare leading subjects using GPA length and pass-rate colour intensity.",
            "Linganisha masomo yanayoongoza kwa urefu wa GPA na nguvu ya rangi ya kiwango cha ufaulu.",
        ),
        tr("Top 15", "Juu 15"),
    )
    if not filtered_subject_df.empty:
        subject_bar_df = (
            filtered_subject_df.groupby("subject_name", as_index=False)
            .agg({
                "subject_gpa": "mean",
                "pass": "sum",
                "sat": "sum"
            })
        )
        subject_bar_df["pass_rate"] = (
            subject_bar_df["pass"] /
            subject_bar_df["sat"].where(subject_bar_df["sat"] != 0)
        ) * 100
        subject_bar_df["pass_rate"] = subject_bar_df["pass_rate"].fillna(0)
        subject_bar_df = (
            subject_bar_df.sort_values(["subject_gpa", "pass_rate"], ascending=[True, False])
            .head(15)
            .sort_values("subject_gpa", ascending=False)
        )

        if not subject_bar_df.empty:
            fig_subject_bar = px.bar(
                subject_bar_df,
                x="subject_gpa",
                y="subject_name",
                orientation="h",
                color="pass_rate",
                color_continuous_scale="Viridis",
                text=subject_bar_df["subject_gpa"].round(2),
                labels={
                    "subject_gpa": tr("Average Subject GPA"),
                    "subject_name": tr("Subject"),
                    "pass_rate": tr("Pass Rate (%)")
                }
            )
            fig_subject_bar.update_layout(
                title=tr("Top 15 Subjects by Average GPA", "Masomo 15 ya Juu kwa Wastani wa GPA"),
                xaxis_title=tr("Average Subject GPA"),
                yaxis_title=tr("Subject"),
                height=520
            )
            polish_chart_legend(fig_subject_bar, show=False)
            st.plotly_chart(fig_subject_bar, width="stretch")
            best_subject = subject_bar_df.sort_values("subject_gpa", ascending=True).iloc[0]
            render_chart_insight(
                f"{best_subject['subject_name']} is the strongest subject in this view with GPA "
                f"{best_subject['subject_gpa']:.2f} and pass rate {best_subject['pass_rate']:.1f}%. "
                "Color intensity shows pass-rate strength while bar length shows GPA.",
                f"{best_subject['subject_name']} ndilo somo lenye nguvu zaidi kwenye mwonekano huu likiwa na GPA "
                f"{best_subject['subject_gpa']:.2f} na kiwango cha ufaulu {best_subject['pass_rate']:.1f}%. "
                "Uzito wa rangi unaonyesha nguvu ya kiwango cha ufaulu, wakati urefu wa bao unaonyesha GPA."
            )
        else:
            st.info(tr(
                "No subject summary is available for the horizontal bar.",
                "Hakuna muhtasari wa masomo kwa chati ya mlalo.",
            ))
    else:
        st.info(tr(
            "No subject data available for the horizontal bar.",
            "Hakuna data ya masomo kwa chati ya mlalo.",
        ))

    render_section_header(
        tr("Strategic Insights", "Maarifa ya Kimkakati"),
        tr(
            "Identify inequality, improvement, decline, attendance pressure, and intervention priorities.",
            "Tambua usawa, uimarishaji, kushuka, shinikizo la mahudhurio, na vipaumbele vya uingiliaji.",
        ),
        tr("Action view", "Mtazamo wa hatua"),
    )

    risk_threshold = st.slider(
        tr("Risk Threshold: Division 0 Rate (%)", "Kizingiti cha Hatari: Kiwango cha Division 0 (%)"),
        min_value=5,
        max_value=30,
        value=15,
        step=1,
        key="risk_threshold_slider"
    )

    change_metric = st.selectbox(
        tr("Improvement Metric", "Kipimo cha Uimarishaji"),
        options=["gpa", "pass_rate"],
        format_func=lambda x: "GPA" if x == "gpa" else tr("Pass Rate"),
        key="dashboard_change_metric"
    )

    change_df = performance_change(filtered_school_df, "school_name", change_metric)
    change_label = tr("GPA Change", "Mabadiliko ya GPA") if change_metric == "gpa" else tr("Pass Rate Change (%)", "Mabadiliko ya Kiwango cha Ufaulu (%)")
    gap_info = regional_gap(filtered_school_df)
    risk_df = risk_schools(filtered_school_df, threshold=risk_threshold)
    attendance = attendance_efficiency(filtered_school_df)

    i1, i2, i3 = st.columns(3)

    with i1:
        if gap_info:
            gap_status = "danger" if gap_info["gap"] > 1.0 else "warning"
            render_insight_card(
                tr("Regional GPA Gap", "Pengo la GPA ya Mikoa"),
                f"{gap_info['gap']:.2f}",
                f"{gap_info['best_region']} vs {gap_info['worst_region']}",
                gap_status
            )
        else:
            render_insight_card(
                tr("Regional GPA Gap", "Pengo la GPA ya Mikoa"),
                "N/A",
                tr("Not enough data for inequality analysis", "Data haitoshi kwa uchambuzi wa usawa"),
                "neutral"
            )

    with i2:
        high_risk_count = len(risk_df) if not risk_df.empty else 0
        risk_status = "danger" if high_risk_count > 0 else "good"
        render_insight_card(
            tr("High-Risk Schools", "Shule zenye Hatari Kubwa"),
            f"{high_risk_count}",
            tr(
                f"Schools with Division 0 rate above {risk_threshold}%",
                f"Shule zenye kiwango cha Division 0 zaidi ya {risk_threshold}%",
            ),
            risk_status
        )

    with i3:
        if attendance is not None:
            status = "good" if attendance >= 90 else "warning" if attendance >= 80 else "danger"
            render_insight_card(
                tr("Attendance Efficiency", "Ufanisi wa Mahudhurio"),
                f"{attendance:.1f}%",
                tr("Average sat-to-registered rate", "Wastani wa waliofanya dhidi ya waliosajiliwa"),
                status
            )
        else:
            render_insight_card(
                tr("Attendance Efficiency", "Ufanisi wa Mahudhurio"),
                "N/A",
                tr("Attendance data unavailable", "Data ya mahudhurio haipatikani"),
                "neutral"
            )

    render_narrative(
        tr(
            "This summary shows where intervention pressure is highest. "
            "A large regional gap signals inequality, high Division 0 concentration flags urgent support needs, "
            "and weak attendance efficiency points to access or retention issues. "
            "For GPA, a negative change is an improvement because lower NECTA GPA is better.",
            "Muhtasari huu unaonyesha maeneo yenye shinikizo kubwa la uingiliaji. "
            "Pengo kubwa la mikoa linaashiria kutokuwepo kwa usawa, mkusanyiko mkubwa wa Division 0 unaonyesha hitaji la haraka la msaada, "
            "na ufanisi dhaifu wa mahudhurio unaonyesha changamoto za upatikanaji au ubaki shuleni. "
            "Kwa GPA, mabadiliko hasi ni uimarishaji kwa sababu GPA ya chini ya NECTA ni bora.",
        )
    )

    x1, x2 = st.columns(2)

    with x1:
        st.markdown(f"#### {tr('Top Improving Schools', 'Shule Zinazoimarika Zaidi')}")
        if not change_df.empty:
            top_improvers = change_df.head(5).copy()
            st.dataframe(
                top_improvers[["school_name", "change"]].rename(columns={
                    "school_name": tr("School"),
                    "change": change_label
                }),
                width="stretch",
                hide_index=True
            )
            fig_improve = px.bar(
                top_improvers,
                x="school_name",
                y="change",
                color_discrete_sequence=["#16a34a"],
                text_auto=".2f"
            )
            fig_improve.update_layout(
                title=tr(
                    f"Top Improving Schools by {metric_display_name(change_metric)} Change",
                    f"Shule Zinazoimarika Zaidi kwa Mabadiliko ya {metric_display_name(change_metric)}",
                ),
                xaxis_title=tr("School"),
                yaxis_title=change_label,
                height=350
            )
            polish_chart_legend(fig_improve, show=False)
            st.plotly_chart(fig_improve, width="stretch")
            render_chart_insight(
                f"These schools have the strongest positive movement for {metric_display_name(change_metric)}. "
                "For GPA, negative change is improvement because lower GPA is better.",
                f"Shule hizi zina mabadiliko chanya zaidi kwa {localize_phrase(metric_display_name(change_metric))}. "
                "Kwa GPA, mabadiliko hasi ni uimarishaji kwa sababu GPA ya chini ni bora."
            )
        else:
            st.info(tr(
                "No year-over-year improvement data available.",
                "Hakuna data ya uimarishaji wa mwaka hadi mwaka.",
            ))

    with x2:
        st.markdown(f"#### {tr('Declining Schools', 'Shule Zinazoshuka')}")
        if not change_df.empty:
            top_decliners = change_df.tail(5).sort_values("improvement_score", ascending=True).copy()
            st.dataframe(
                top_decliners[["school_name", "change"]].rename(columns={
                    "school_name": tr("School"),
                    "change": change_label
                }),
                width="stretch",
                hide_index=True
            )
            fig_decline = px.bar(
                top_decliners,
                x="school_name",
                y="change",
                color_discrete_sequence=["#dc2626"],
                text_auto=".2f"
            )
            fig_decline.update_layout(
                title=tr(
                    f"Declining Schools by {metric_display_name(change_metric)} Change",
                    f"Shule Zinazoshuka kwa Mabadiliko ya {metric_display_name(change_metric)}",
                ),
                xaxis_title=tr("School"),
                yaxis_title=change_label,
                height=350
            )
            polish_chart_legend(fig_decline, show=False)
            st.plotly_chart(fig_decline, width="stretch")
            render_chart_insight(
                f"These schools show the steepest decline for {metric_display_name(change_metric)}. "
                "They should be reviewed before the next planning cycle.",
                f"Shule hizi zinaonyesha kushuka zaidi kwa {localize_phrase(metric_display_name(change_metric))}. "
                "Zinapaswa kufanyiwa tathmini kabla ya mzunguko unaofuata wa mipango."
            )
        else:
            st.info(tr(
                "No year-over-year decline data available.",
                "Hakuna data ya kushuka kwa mwaka hadi mwaka.",
            ))

    render_section_header(
        tr("School Risk Map", "Ramani ya Hatari za Shule"),
        tr(
            "Locate schools with weak pass rates, high GPA, and concentrated Division 0 outcomes.",
            "Tambua shule zenye viwango dhaifu vya ufaulu, GPA ya juu, na matokeo mengi ya Division 0.",
        ),
        tr("Risk detection", "Utambuzi wa hatari"),
    )
    scatter_df = risk_scatter_data(filtered_school_df)
    if not scatter_df.empty:
        fig_risk = px.scatter(
            scatter_df,
            x="pass_rate",
            y="gpa",
            size="sat",
            color="division_0_rate",
            hover_name="school_name",
            hover_data={
                "region": True,
                "attendance_rate": ":.1f",
                "sat": ":,",
                "division_0_rate": ":.1f",
                "pass_rate": ":.1f",
                "gpa": ":.2f"
            },
            color_continuous_scale="Reds",
            labels={
                "pass_rate": tr("Pass Rate (%)"),
                "gpa": tr("Average GPA"),
                "division_0_rate": tr("Division 0 Rate (%)", "Kiwango cha Division 0 (%)"),
                "sat": tr("Candidates Sat")
            }
        )
        fig_risk.update_layout(
            title=tr("School Performance Risk Map", "Ramani ya Hatari ya Ufaulu wa Shule"),
            xaxis_title=tr("Pass Rate (%)"),
            yaxis_title=tr("Average GPA"),
            height=520
        )
        fig_risk.update_yaxes(autorange="reversed")
        polish_chart_legend(fig_risk, show=False)
        st.plotly_chart(fig_risk, width="stretch")
        riskiest = scatter_df.sort_values(["division_0_rate", "gpa"], ascending=[False, False]).iloc[0]
        render_chart_insight(
            f"{riskiest['school_name']} is the highest-risk point in this view with Division 0 rate "
            f"{riskiest['division_0_rate']:.1f}% and GPA {riskiest['gpa']:.2f}. Larger bubbles represent more candidates sat.",
            f"{riskiest['school_name']} ndiyo sehemu yenye hatari kubwa zaidi kwenye mwonekano huu ikiwa na kiwango cha Division 0 "
            f"{riskiest['division_0_rate']:.1f}% na GPA {riskiest['gpa']:.2f}. Miduara mikubwa inaonyesha watahiniwa wengi zaidi waliofanya mtihani."
        )
    else:
        st.info(tr(
            "No risk scatter data available for the selected filters.",
            "Hakuna data ya ramani ya hatari kwa vichujio vilivyochaguliwa.",
        ))

    with st.expander(tr("Open risk list and intervention targets", "Fungua orodha ya hatari na malengo ya uingiliaji")):
        if not risk_df.empty:
            st.dataframe(
                risk_df[["school_name", "region", "division_0", "sat", "div0_rate"]]
                .rename(columns={
                    "school_name": tr("School"),
                    "region": tr("Region"),
                    "division_0": "Division 0",
                    "sat": tr("Sat"),
                    "div0_rate": tr("Division 0 Rate (%)", "Kiwango cha Division 0 (%)")
                }),
                width="stretch",
                hide_index=True
            )
            render_narrative(
                tr(
                    "Schools in this list should be prioritized for academic recovery, remedial support, and follow-up on exam readiness.",
                    "Shule zilizo kwenye orodha hii zipewe kipaumbele kwa urejeshaji wa kitaaluma, msaada wa marekebisho, na ufuatiliaji wa utayari wa mitihani.",
                )
            )
        else:
            st.success(tr(
                "No schools crossed the high-risk Division 0 threshold.",
                "Hakuna shule iliyovuka kizingiti cha hatari kubwa cha Division 0.",
            ))

    national_gap_info = regional_gap(national_school_df)
    national_risk_df = risk_schools(national_school_df, threshold=risk_threshold)
    national_attendance = attendance_efficiency(national_school_df)
    render_section_header(
        tr("Key Findings for Decision Makers", "Matokeo Muhimu kwa Watoa Maamuzi"),
        tr(
            "National priorities for supervisors, examiners, and education planners.",
            "Vipaumbele vya kitaifa kwa wasimamizi, watahini, na wapangaji wa elimu.",
        ),
        tr("National brief", "Muhtasari wa kitaifa"),
    )
    render_policy_summary(
        policy_summary_items(
            national_school_df,
            national_subject_df,
            national_risk_df,
            national_gap_info,
            national_attendance,
        ),
        title=tr("Key Findings for Decision Makers", "Matokeo Muhimu kwa Watoa Maamuzi"),
    )

    render_section_header(
        tr("Predictive Analytics", "Uchambuzi wa Makadirio"),
        tr(
            "Use the forecast direction for planning; dotted values are estimates rather than official NECTA results.",
            "Tumia mwelekeo wa makadirio kwa mipango; thamani za nukta ni makadirio, si matokeo rasmi ya NECTA.",
        ),
        tr("Forecasting", "Makadirio"),
    )
    st.caption(
        tr(
            "Solid lines show actual results. Dotted lines show the next two years if recent patterns continue. Forecasts should support, not replace, academic judgment.",
            "Mistari kamili inaonyesha matokeo halisi. Mistari ya nukta inaonyesha miaka miwili ijayo ikiwa mwenendo wa karibuni utaendelea. Makadirio yasaidie maamuzi ya kitaaluma, si kuyachukua nafasi.",
        )
    )
    artifacts = build_model_artifacts(school_df)

    p1, p2 = st.columns(2)
    with p1:
        gpa_history_df = (
            filtered_school_df.groupby(["year", "region"], as_index=False)["gpa"]
            .mean()
            .sort_values(["region", "year"])
        )
        gpa_forecast_df = (
            artifacts.get("forecasts", {}).get("gpa", pd.DataFrame()).copy()
            if artifacts else pd.DataFrame()
        )
        if selected_regions and not gpa_forecast_df.empty:
            gpa_forecast_df = gpa_forecast_df[
                gpa_forecast_df["region"].isin(selected_regions)
            ]
        note_box(tr(
            "Regional GPA outlook: solid lines are actual and dotted lines are forecast.",
            "Mtazamo wa GPA ya mikoa: mistari kamili ni matokeo halisi na mistari ya nukta ni makadirio.",
        ))
        fig = ml_forecast_line_chart(
            gpa_history_df,
            gpa_forecast_df,
            "gpa",
            tr("Regional GPA Forecast", "Makadirio ya GPA ya Mikoa"),
            tr("Average GPA"),
            lower_bound=0,
            upper_bound=5,
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            if not gpa_forecast_df.empty:
                best_future = gpa_forecast_df.sort_values("gpa").iloc[0]
                render_chart_insight(
                    tr(
                        "The dotted lines are two-year planning estimates. "
                        f"{best_future['region']} has the strongest projected GPA point at "
                        f"{best_future['gpa']:.2f} in {int(best_future['year'])}. "
                        "Lower GPA indicates stronger projected performance.",
                        "Mistari ya nukta ni makadirio ya mipango ya miaka miwili. "
                        f"{best_future['region']} ina GPA inayokadiriwa kuwa bora zaidi kwa "
                        f"{best_future['gpa']:.2f} mwaka {int(best_future['year'])}. "
                        "GPA ya chini inaonyesha ufaulu unaokadiriwa kuwa bora.",
                    )
                )
            else:
                render_chart_insight(
                    tr(
                        "No saved GPA forecast points are available for the selected regions.",
                        "Hakuna pointi za makadirio ya GPA zilizohifadhiwa kwa mikoa iliyochaguliwa.",
                    )
                )
        else:
            st.info(tr(
                "At least two years of regional GPA data are needed for ML forecasting.",
                "Inahitajika angalau miaka miwili ya data ya GPA ya mikoa kwa makadirio.",
            ))

    with p2:
        pass_history_df = weighted_pass_rate_by_group(
            filtered_school_df,
            ["year", "region"]
        ).sort_values(["region", "year"])
        pass_forecast_df = (
            artifacts.get("forecasts", {}).get("pass_rate", pd.DataFrame()).copy()
            if artifacts else pd.DataFrame()
        )
        if selected_regions and not pass_forecast_df.empty:
            pass_forecast_df = pass_forecast_df[
                pass_forecast_df["region"].isin(selected_regions)
            ]
        note_box(
            tr(
                "Regional pass-rate outlook: solid lines are actual and dotted lines are forecast.",
                "Mtazamo wa kiwango cha ufaulu wa mikoa: mistari kamili ni matokeo halisi na mistari ya nukta ni makadirio.",
            )
        )
        fig = ml_forecast_line_chart(
            pass_history_df,
            pass_forecast_df,
            "pass_rate",
            tr("Regional Pass Rate Forecast", "Makadirio ya Kiwango cha Ufaulu wa Mikoa"),
            tr("Pass Rate (%)"),
            lower_bound=0,
            upper_bound=100,
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
            if not pass_forecast_df.empty:
                strongest_future = pass_forecast_df.sort_values(
                    "pass_rate",
                    ascending=False,
                ).iloc[0]
                render_chart_insight(
                    tr(
                        "The dotted lines are two-year planning estimates. "
                        f"{strongest_future['region']} has the strongest projected pass rate at "
                        f"{strongest_future['pass_rate']:.1f}% in {int(strongest_future['year'])}.",
                        "Mistari ya nukta ni makadirio ya mipango ya miaka miwili. "
                        f"{strongest_future['region']} ina kiwango cha ufaulu kinachokadiriwa kuwa bora zaidi kwa "
                        f"{strongest_future['pass_rate']:.1f}% mwaka {int(strongest_future['year'])}.",
                    )
                )
            else:
                render_chart_insight(
                    tr(
                        "No saved pass-rate forecast points are available for the selected regions.",
                        "Hakuna pointi za makadirio ya kiwango cha ufaulu zilizohifadhiwa kwa mikoa iliyochaguliwa.",
                    )
                )
        else:
            st.info(tr(
                "At least two years of regional pass-rate data are needed for ML forecasting.",
                "Inahitajika angalau miaka miwili ya data ya kiwango cha ufaulu wa mikoa kwa makadirio.",
            ))
