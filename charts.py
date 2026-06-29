"""Shared Plotly transformations and presentation rules for the dashboard."""

import numpy as np
import pandas as pd
import plotly.express as px

from metrics import lower_is_better, metric_display_name, weighted_rate
from styles import tr


LEGEND_TITLE_LABELS = {
    "region": "Region",
    "school_name": "School",
    "subject_name": "Subject",
    "Division": "NECTA Division",
    "NECTA Division": "NECTA Division",
    "Source": "Comparison Series",
    "Comparison Series": "Comparison Series",
    "Region and Series": "Region and Series",
    "Performance Direction": "Performance Direction",
    "Series": "Performance Series",
    "status": "Performance Direction",
}

LEGEND_ITEM_LABELS = {
    "Improved": "Improved Performance",
    "Declined": "Declined Performance",
    "Stable": "No Material Change",
    "Div I": "Division I",
    "Div II": "Division II",
    "Div III": "Division III",
    "Div IV": "Division IV",
    "Div 0": "Division 0",
    "Historical": "Actual",
    "Actual": "Actual",
    "Forecast": "Forecast",
}


def professional_label(value):
    """Convert internal trace labels into concise user-facing legend text."""
    text = str(value or "").strip()
    if not text:
        return ""
    if text in LEGEND_ITEM_LABELS:
        return tr(LEGEND_ITEM_LABELS[text])
    if text.lower().endswith(" forecast"):
        base = text[:-9].strip()
        return f"{professional_label(base)} ({tr('Forecast')})"
    if text.lower().endswith(" historical"):
        base = text[:-10].strip()
        return f"{professional_label(base)} ({tr('Actual')})"

    display = text.replace("_", " ").strip().title()
    display = (
        display
        .replace("Gpa", "GPA")
        .replace("Necta", "NECTA")
        .replace("Dar Es Salaam", "Dar es Salaam")
        .replace("Division Iii", "Division III")
        .replace("Division Ii", "Division II")
        .replace("Division Iv", "Division IV")
    )
    return tr(display)


def professional_legend_title(value):
    """Convert an internal grouping field into a professional legend title."""
    text = str(value or "").strip()
    return tr(LEGEND_TITLE_LABELS.get(text, professional_label(text)))


def professional_series_label(value, series, group_col=None):
    """Build an explicit Actual/Forecast label for one chart series."""
    base = professional_label(value)
    if group_col == "region" and not base.lower().endswith(" region"):
        base = f"{base} {tr('Region')}"
    return f"{base} ({tr(series)})"


def polish_chart_legend(fig, title=None, show=None, large_series_threshold=16):
    """Apply responsive titles, margins, legends, and axis auto-margins."""
    for trace in fig.data:
        if getattr(trace, "name", None):
            trace.name = professional_label(trace.name)

    initial_names = list(
        dict.fromkeys(
            trace.name
            for trace in fig.data
            if getattr(trace, "showlegend", None) is not False
            and getattr(trace, "name", None)
        )
    )
    large_series = len(initial_names) >= large_series_threshold

    if large_series:
        for trace in fig.data:
            trace_name = str(getattr(trace, "name", "") or "")
            if trace_name.endswith(" (Actual)"):
                trace.name = trace_name.removesuffix(" (Actual)")
                trace.showlegend = True
            elif trace_name.endswith(" (Forecast)"):
                trace.showlegend = False

    legend_traces = []
    for trace in fig.data:
        if getattr(trace, "showlegend", None) is not False and getattr(trace, "name", None):
            legend_traces.append(trace)

    distinct_names = list(dict.fromkeys(trace.name for trace in legend_traces))
    if show is None:
        show = len(distinct_names) > 1

    current_margin = fig.layout.margin
    margin = {
        "l": current_margin.l if current_margin and current_margin.l is not None else 60,
        "r": current_margin.r if current_margin and current_margin.r is not None else 24,
        "t": current_margin.t if current_margin and current_margin.t is not None else 60,
        "b": current_margin.b if current_margin and current_margin.b is not None else 55,
    }

    if show:
        item_count = len(distinct_names)
        legend_rows = max(1, int(np.ceil(item_count / 4)))
        extra_rows = max(0, legend_rows - 1)
        chart_title = str(getattr(fig.layout.title, "text", "") or "").strip()
        if chart_title.lower() in {"undefined", "none", "null"}:
            chart_title = ""
        has_chart_title = bool(chart_title)
        if large_series:
            # All-region charts need a right-side legend so 31 labels do not
            # consume the vertical plot area or collide with the title.
            margin["t"] = max(margin["t"], 80 if has_chart_title else 48)
            margin["r"] = max(margin["r"], 265)
            margin["b"] = max(margin["b"], 65)
            legend_orientation = "v"
            legend_x = 1.01
            legend_xanchor = "left"
            legend_y = 1
            legend_yanchor = "top"
            legend_font_size = 10
        elif has_chart_title:
            margin["t"] = max(margin["t"], 72)
            margin["b"] = max(margin["b"], 105 + min(extra_rows, 6) * 24)
            legend_orientation = "h"
            legend_x = 0
            legend_xanchor = "left"
            legend_y = -0.20
            legend_yanchor = "top"
            legend_font_size = 11
        else:
            margin["t"] = max(margin["t"], 95 + min(extra_rows, 6) * 24)
            legend_orientation = "h"
            legend_x = 0
            legend_xanchor = "left"
            legend_y = 1.02
            legend_yanchor = "bottom"
            legend_font_size = 11

        current_height = fig.layout.height or 380
        large_series_height = max(
            current_height,
            180 + item_count * 19,
        )
        legend_title = professional_legend_title(
            title or getattr(fig.layout.legend.title, "text", "")
        )
        if large_series:
            legend_title = (
                f"<b>{legend_title}</b><br>"
                f"<span style='font-size:10px'>{tr('Solid = Actual', 'Mstari kamili = Halisi')}<br>"
                f"{tr('Dashed = Forecast', 'Mstari wa nukta = Makadirio')}</span>"
            )

        fig.update_layout(
            autosize=True,
            height=(
                large_series_height
                if large_series
                else current_height + min(extra_rows, 6) * 24
            ),
            showlegend=True,
            title={
                "text": chart_title,
                "x": 0.01,
                "xanchor": "left",
                "y": 0.98,
                "yanchor": "top",
                "font": {
                    "size": 17 if large_series else 18,
                    "color": "#0f172a",
                },
            } if has_chart_title else {"text": ""},
            legend={
                "title": {
                    "text": legend_title,
                    "font": {"size": 12, "color": "#334155"},
                },
                "orientation": legend_orientation,
                "yanchor": legend_yanchor,
                "y": legend_y,
                "xanchor": legend_xanchor,
                "x": legend_x,
                "font": {"size": legend_font_size, "color": "#334155"},
                "bgcolor": "rgba(255,255,255,0.94)",
                "bordercolor": "rgba(148,163,184,0.40)",
                "borderwidth": 1,
                "tracegroupgap": 8,
                "itemsizing": "constant",
            },
            margin=margin,
        )
    else:
        chart_title = str(getattr(fig.layout.title, "text", "") or "").strip()
        fig.update_layout(
            showlegend=False,
            margin=margin,
            title={"text": ""} if chart_title.lower() in {"undefined", "none", "null"} else fig.layout.title,
        )

    color_axis = getattr(fig.layout, "coloraxis", None)
    if color_axis is not None and color_axis.colorbar is not None:
        color_title = getattr(color_axis.colorbar.title, "text", "")
        color_axis.colorbar.update(
            title={
                "text": professional_legend_title(color_title),
                "side": "right",
                "font": {"size": 12, "color": "#334155"},
            },
            tickfont={"size": 10, "color": "#475569"},
            thickness=14,
            len=0.78,
            xpad=8,
        )

    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def year_over_year_change_df(df, year_col, value_col, group_col=None):
    """Calculate year-over-year changes and improvement direction."""
    if df.empty or not {year_col, value_col}.issubset(df.columns):
        return pd.DataFrame(columns=[year_col, "change", "status"])

    group_cols = [year_col]
    if group_col and group_col in df.columns:
        group_cols.append(group_col)

    temp = (
        df[group_cols + [value_col]]
        .dropna()
        .groupby(group_cols, as_index=False)[value_col]
        .mean()
        .sort_values(group_cols)
    )

    if temp.empty:
        return pd.DataFrame(columns=group_cols + ["change", "status"])

    sort_cols = [group_col, year_col] if group_col and group_col in temp.columns else [year_col]
    temp = temp.sort_values(sort_cols)
    if group_col and group_col in temp.columns:
        temp["change"] = temp.groupby(group_col)[value_col].diff()
    else:
        temp["change"] = temp[value_col].diff()

    out = temp.dropna(subset=["change"]).copy()
    if out.empty:
        return pd.DataFrame(columns=group_cols + ["change", "status"])

    if lower_is_better(value_col):
        out["status"] = np.where(out["change"] < 0, "Improved", np.where(out["change"] > 0, "Declined", "Stable"))
    else:
        out["status"] = np.where(out["change"] > 0, "Improved", np.where(out["change"] < 0, "Declined", "Stable"))

    return out

def yoy_bar_chart(df, year_col, value_col, title, group_col=None, height=350):
    """Build a status-colored year-over-year change chart."""
    yoy_df = year_over_year_change_df(df, year_col, value_col, group_col=group_col)
    if yoy_df.empty:
        return None, yoy_df

    fig = px.bar(
        yoy_df,
        x=year_col,
        y="change",
        color="status",
        barmode="group",
        text=yoy_df["change"].round(2),
        hover_data=[group_col] if group_col and group_col in yoy_df.columns else None,
        color_discrete_map={
            "Improved": "#16a34a",
            "Declined": "#dc2626",
            "Stable": "#94a3b8"
        },
        title=title
    )
    fig.update_layout(
        xaxis_title=tr("Year"),
        yaxis_title=f"{tr(metric_display_name(value_col))} {tr('Change', 'Mabadiliko')}",
        height=height
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    polish_chart_legend(fig, title="Performance Direction", show=True)
    return fig, yoy_df

def forecast_from_history(df, year_col, value_col, periods=2, lower_bound=None, upper_bound=None):
    """Project a short bounded linear continuation from historical values."""
    columns = [year_col, value_col]
    if df.empty or not set(columns).issubset(df.columns):
        return pd.DataFrame(columns=columns)

    temp = df[columns].copy()
    temp[year_col] = pd.to_numeric(temp[year_col], errors="coerce")
    temp[value_col] = pd.to_numeric(temp[value_col], errors="coerce")
    temp = (
        temp.dropna()
        .groupby(year_col, as_index=False)[value_col]
        .mean()
        .sort_values(year_col)
    )

    if temp[year_col].nunique() < 2:
        return pd.DataFrame(columns=columns)

    x = temp[year_col].astype(float).to_numpy()
    y = temp[value_col].astype(float).to_numpy()
    slope, intercept = np.polyfit(x, y, 1)

    start_year = int(temp[year_col].max()) + 1
    future_years = np.arange(start_year, start_year + periods)
    future_values = slope * future_years + intercept

    if lower_bound is not None or upper_bound is not None:
        future_values = np.clip(
            future_values,
            lower_bound if lower_bound is not None else -np.inf,
            upper_bound if upper_bound is not None else np.inf
        )

    return pd.DataFrame({
        year_col: future_years.astype(int),
        value_col: future_values
    })

def forecast_line_chart(
    df,
    year_col,
    value_col,
    y_title,
    group_col=None,
    periods=2,
    lower_bound=None,
    upper_bound=None,
    height=380,
    color_discrete_map=None,
    forecast_color_map=None,
    chart_title=None,
):
    """Build a responsive Actual/Forecast chart from historical records."""
    if df.empty or not {year_col, value_col}.issubset(df.columns):
        return None

    if group_col and group_col in df.columns:
        history = (
            df[[year_col, group_col, value_col]]
            .dropna()
            .groupby([year_col, group_col], as_index=False)[value_col]
            .mean()
            .sort_values([group_col, year_col])
        )
        if history.empty:
            return None

        fig = px.line(
            history,
            x=year_col,
            y=value_col,
            color=group_col,
            markers=True,
            color_discrete_map=color_discrete_map,
        )
        for trace in fig.data:
            trace.name = professional_series_label(trace.name, "Actual", group_col)

        for group_value in history[group_col].dropna().unique():
            group_history = history[history[group_col] == group_value].sort_values(year_col)
            forecast_df = forecast_from_history(
                group_history,
                year_col,
                value_col,
                periods=periods,
                lower_bound=lower_bound,
                upper_bound=upper_bound
            )
            if forecast_df.empty:
                continue

            bridge = pd.concat(
                [group_history[[year_col, value_col]].tail(1), forecast_df],
                ignore_index=True
            )
            history_trace = next(
                (
                    trace
                    for trace in fig.data
                    if trace.name
                    == professional_series_label(group_value, "Actual", group_col)
                ),
                None,
            )
            history_color = (
                history_trace.line.color
                if history_trace is not None
                else None
            )
            forecast_color = (
                forecast_color_map.get(group_value, history_color)
                if forecast_color_map
                else history_color
            )
            fig.add_scatter(
                x=bridge[year_col],
                y=bridge[value_col],
                mode="lines+markers",
                line={
                    "dash": "dash",
                    "width": 3,
                    **({"color": forecast_color} if forecast_color else {}),
                },
                marker={
                    **({"color": forecast_color} if forecast_color else {}),
                },
                opacity=0.72,
                name=professional_series_label(group_value, "Forecast", group_col),
            )
    else:
        history = (
            df[[year_col, value_col]]
            .dropna()
            .groupby(year_col, as_index=False)[value_col]
            .mean()
            .sort_values(year_col)
        )
        if history.empty:
            return None

        fig = px.line(
            history,
            x=year_col,
            y=value_col,
            markers=True,
        )
        if fig.data:
            fig.data[0].name = "Actual"
            fig.data[0].showlegend = True

        forecast_df = forecast_from_history(
            history,
            year_col,
            value_col,
            periods=periods,
            lower_bound=lower_bound,
            upper_bound=upper_bound
        )
        if not forecast_df.empty:
            bridge = pd.concat(
                [history[[year_col, value_col]].tail(1), forecast_df],
                ignore_index=True
            )
            history_color = fig.data[0].line.color if fig.data else None
            fig.add_scatter(
                x=bridge[year_col],
                y=bridge[value_col],
                mode="lines+markers",
                line={
                    "dash": "dash",
                    "width": 3,
                    **({"color": history_color} if history_color else {}),
                },
                marker={
                    **({"color": history_color} if history_color else {}),
                },
                opacity=0.58,
                name="Forecast",
            )

    fig.update_layout(
        xaxis_title=tr("Year"),
        yaxis_title=tr(y_title),
        height=height,
        title={
            "text": (
                chart_title
                or (
                    f"{tr(y_title)} {tr('Trend by', 'Mwenendo kwa')} {professional_legend_title(group_col)}"
                    if group_col
                    else f"{tr(y_title)} {tr('Trend and Forecast', 'Mwenendo na Makadirio')}"
                )
            )
        },
    )
    polish_chart_legend(
        fig,
        title=professional_legend_title(group_col) if group_col else "Series",
    )
    return fig

def weighted_pass_rate_by_group(df, group_cols):
    """Aggregate candidate-weighted school pass rates by grouping columns."""
    if df.empty or not {"total_passed_candidates", "sat"}.issubset(df.columns):
        return pd.DataFrame(columns=group_cols + ["pass_rate"])

    out = (
        df.groupby(group_cols, as_index=False)
        .agg({
            "total_passed_candidates": "sum",
            "sat": "sum"
        })
    )
    out["pass_rate"] = out.apply(
        lambda row: weighted_rate(row["total_passed_candidates"], row["sat"]),
        axis=1
    )
    out["pass_rate"] = out["pass_rate"].fillna(0)
    return out[group_cols + ["pass_rate"]]

def weighted_subject_pass_rate_by_group(df, group_cols):
    """Aggregate candidate-weighted subject pass rates by grouping columns."""
    if df.empty or not {"pass", "sat"}.issubset(df.columns):
        return pd.DataFrame(columns=group_cols + ["pass_rate"])

    out = (
        df.groupby(group_cols, as_index=False)
        .agg({
            "pass": "sum",
            "sat": "sum"
        })
    )
    out["pass_rate"] = out.apply(
        lambda row: weighted_rate(row["pass"], row["sat"]),
        axis=1
    )
    out["pass_rate"] = out["pass_rate"].fillna(0)
    return out[group_cols + ["pass_rate"]]

