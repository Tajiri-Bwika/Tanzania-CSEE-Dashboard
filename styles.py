"""Provide the shared responsive visual system and HTML UI components."""

import html
import textwrap
from urllib.parse import quote

import streamlit as st


CSS = r"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;600&family=Fira+Sans:wght@400;500;600;700;800;900&display=swap');

    :root {
        --ui-bg: #f8fafc;
        --ui-surface: #ffffff;
        --ui-surface-soft: #f1f5f9;
        --ui-border: rgba(30, 64, 175, 0.12);
        --ui-text: #0f172a;
        --ui-muted: #64748b;
        --ui-primary: #1e40af;
        --ui-secondary: #0f766e;
        --ui-accent: #f59e0b;
        --ui-danger: #dc2626;
        --ui-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
        --ui-shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.06);
        --ui-radius: 12px;
        --ui-radius-sm: 8px;
    }

    html, body, [class*="css"], .stApp {
        font-family: "Fira Sans", "Inter", "Segoe UI", sans-serif;
        color: var(--ui-text);
    }

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f8fafc 0%, #eef4f8 100%);
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        display: none;
    }

    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none;
    }

    .site-navbar {
        position: sticky;
        top: 0;
        z-index: 100000;
        width: 100%;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 13px 18px;
        margin: 0 0 20px;
        background: linear-gradient(135deg, #07111f 0%, #12324a 58%, #0f5e58 100%);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 14px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.22);
        backdrop-filter: blur(18px);
    }

    .site-brand-link {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none !important;
        min-width: 250px;
        flex: 0 1 250px;
    }

    .site-brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: block;
        position: relative;
        overflow: hidden;
        background: #1eb53a;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.22);
    }

    .tz-flag {
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, #1eb53a 0 34%, #fcd116 34% 39%, #000000 39% 61%, #fcd116 61% 66%, #00a3dd 66% 100%);
    }

    .site-brand-title {
        color: #ffffff;
        font-size: 16px;
        font-weight: 900;
        line-height: 1.05;
    }

    .site-brand-subtitle {
        color: #cbd5e1;
        font-size: 12px;
        font-weight: 700;
        margin-top: 3px;
    }

    .site-nav-links {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        flex: 1;
        min-width: 0;
    }

    .site-nav-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 40px;
        padding: 0 15px;
        border-radius: 11px;
        color: #dbeafe !important;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 850;
        border: 1px solid transparent;
        transition: background 180ms ease, color 180ms ease, box-shadow 180ms ease;
    }

    .site-nav-link:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #ffffff !important;
        border-color: rgba(255, 255, 255, 0.2);
    }

    .site-nav-link.active {
        background: #ffffff;
        color: #0f172a !important;
        box-shadow: 0 10px 22px rgba(0, 0, 0, 0.18);
    }

    .site-nav-actions {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
        min-width: 230px;
        flex: 0 1 230px;
    }

    .site-lang-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 34px;
        padding: 0 10px;
        border-radius: 999px;
        color: #dbeafe !important;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
        text-decoration: none !important;
        font-size: 12px;
        font-weight: 850;
    }

    .site-lang-link.active {
        color: #0f172a !important;
        background: #fef3c7;
        border-color: #fbbf24;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #08111f 0%, #12324a 56%, #0f5e58 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 14px 0 40px rgba(15, 23, 42, 0.2);
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    [data-testid="stSidebar"] [data-baseweb="radio"] div {
        color: #f8fafc !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] button {
        border-radius: var(--ui-radius-sm) !important;
    }

    h1 {
        color: var(--ui-text);
        font-size: 2.15rem !important;
        font-weight: 900 !important;
        letter-spacing: 0;
        margin-bottom: 0.1rem !important;
    }

    h2, h3 {
        color: var(--ui-text);
        font-weight: 850 !important;
        letter-spacing: 0;
    }

    h3 {
        margin-top: 1.4rem !important;
        padding-top: 0.2rem;
    }

    p, label, span {
        letter-spacing: 0;
    }

    code, pre {
        font-family: "Fira Code", "Cascadia Code", monospace;
    }

    .premium-kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fbff 100%);
        border: 1px solid var(--ui-border);
        border-radius: var(--ui-radius);
        padding: 18px 18px 16px;
        box-shadow: var(--ui-shadow-soft);
        min-height: 122px;
        position: relative;
        overflow: hidden;
    }

    .premium-kpi-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 5px;
        background: linear-gradient(180deg, var(--ui-primary), var(--ui-secondary));
    }

    .premium-kpi-label {
        color: var(--ui-muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .premium-kpi-value {
        color: var(--ui-text);
        font-size: 32px;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 8px;
    }

    .premium-kpi-subtext {
        color: var(--ui-muted);
        font-size: 13px;
        line-height: 1.35;
    }

    .policy-panel {
        background: linear-gradient(135deg, #07111f 0%, #15354d 55%, #0f5e58 100%);
        color: #f8fafc;
        border-radius: var(--ui-radius);
        padding: 22px 24px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.22);
        margin-top: 8px;
        margin-bottom: 18px;
    }

    .policy-panel h4 {
        margin: 0 0 12px;
        font-size: 18px;
        color: #ffffff;
    }

    .policy-panel ul {
        margin: 0;
        padding-left: 20px;
    }

    .policy-panel li {
        margin-bottom: 8px;
        color: #dbeafe;
    }

    .findings-panel {
        background: #ffffff;
        border: 1px solid rgba(30, 64, 175, 0.14);
        border-left: 5px solid var(--ui-primary);
        border-radius: var(--ui-radius);
        padding: 18px 20px;
        margin-bottom: 18px;
        box-shadow: var(--ui-shadow-soft);
    }

    .findings-panel h4 {
        margin: 0 0 5px;
        color: var(--ui-text);
        font-size: 18px;
    }

    .findings-panel p {
        margin: 0 0 12px;
        color: var(--ui-muted);
        font-size: 14px;
    }

    .findings-panel ul {
        margin: 0;
        padding-left: 20px;
    }

    .findings-panel li {
        margin-bottom: 8px;
        color: #1e293b;
        line-height: 1.45;
    }

    .note-box {
        background: var(--ui-surface);
        border-left: 6px solid var(--ui-primary);
        border-radius: var(--ui-radius);
        padding: 18px 18px;
        color: #334155;
        min-height: 94px;
        display: flex;
        align-items: center;
        font-size: 15px;
        margin-bottom: 12px;
        box-shadow: var(--ui-shadow-soft);
    }

    .chart-box {
        background: #eef4ff;
        border: 3px solid #b8cdf3;
        border-radius: 20px;
        min-height: 320px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #2d5aa7;
        font-size: 24px;
        font-weight: 800;
        text-align: center;
        padding: 12px;
    }

    .chart-box-tall {
        background: #eef4ff;
        border: 3px solid #b8cdf3;
        border-radius: 20px;
        min-height: 360px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #2d5aa7;
        font-size: 24px;
        font-weight: 800;
        text-align: center;
        padding: 12px;
    }

    div[data-testid="stMetric"] {
        background: #fafafa;
        border: 1px solid #d9d9d9;
        border-radius: var(--ui-radius);
        padding: 16px 14px;
        text-align: center;
    }

    div[data-testid="stMetricLabel"] {
        justify-content: center;
    }

    div[data-testid="stMetricValue"] {
        justify-content: center;
    }

    .insight-card {
        border-radius: var(--ui-radius);
        padding: 18px 20px;
        margin-bottom: 14px;
        border: 1px solid var(--ui-border);
        background: var(--ui-surface);
        box-shadow: var(--ui-shadow-soft);
    }

    .insight-title {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 8px;
        color: #111827;
    }

    .insight-value {
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 6px;
        color: #111827;
        overflow-wrap: anywhere;
    }

    .insight-subtext {
        font-size: 14px;
        color: #6b7280;
    }

    .badge {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .badge-good {
        background: #dcfce7;
        color: #166534;
    }

    .badge-warning {
        background: #fef3c7;
        color: #92400e;
    }

    .badge-danger {
        background: #fee2e2;
        color: #991b1b;
    }

    .badge-neutral {
        background: #e5e7eb;
        color: #374151;
    }

    .narrative-box {
        background: #ffffff;
        border-left: 5px solid #94a3b8;
        border-radius: var(--ui-radius);
        padding: 14px 16px;
        margin-top: 8px;
        margin-bottom: 14px;
        color: #334155;
        font-size: 14px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }

    .chart-insight {
        background: #ffffff;
        border-left: 5px solid var(--ui-secondary);
        border-radius: var(--ui-radius);
        padding: 12px 15px;
        margin-top: 8px;
        margin-bottom: 14px;
        color: #334155;
        font-size: 14px;
        font-style: italic;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    }

    .pro-sidebar-brand {
        margin: 8px 0 20px;
        padding: 18px 16px;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.14), rgba(255, 255, 255, 0.05));
        border: 1px solid rgba(255, 255, 255, 0.18);
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
    }

    .pro-sidebar-mark {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: grid;
        place-items: center;
        background: #f59e0b;
        color: #0f172a !important;
        font-weight: 900;
        letter-spacing: 0;
        margin-bottom: 12px;
    }

    .pro-sidebar-title {
        color: #ffffff !important;
        font-size: 18px;
        font-weight: 900;
        line-height: 1.1;
        margin-bottom: 6px;
    }

    .pro-sidebar-subtitle {
        color: #cbd5e1 !important;
        font-size: 12px;
        font-weight: 600;
        line-height: 1.35;
    }

    .pro-sidebar-label {
        color: #bfdbfe !important;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 900;
        margin: 16px 0 8px;
    }

    .pro-hero {
        position: relative;
        overflow: hidden;
        border-radius: 16px;
        padding: 22px 24px;
        margin: 8px 0 18px;
        background: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 14px 36px rgba(15, 23, 42, 0.07);
    }

    .pro-hero::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #f59e0b, #3b82f6, #14b8a6);
    }

    .pro-hero-grid {
        position: relative;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.8fr);
        gap: 22px;
        align-items: end;
    }

    .pro-kicker {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        font-size: 12px;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 14px;
    }

    .pro-hero h1 {
        color: #0f172a;
        font-size: 30px;
        line-height: 1.08;
        font-weight: 900;
        margin: 0 0 10px;
        letter-spacing: 0;
    }

    .pro-hero p {
        color: #475569;
        max-width: 780px;
        font-size: 15px;
        line-height: 1.55;
        margin: 0;
    }

    .pro-hero-panel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px;
    }

    .pro-hero-panel-label {
        color: #1e40af;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .pro-hero-panel-value {
        color: #0f172a;
        font-size: 26px;
        font-weight: 900;
        margin-bottom: 6px;
    }

    .pro-hero-panel-sub {
        color: #64748b;
        font-size: 13px;
        line-height: 1.4;
    }

    .pro-stat-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 10px 0 18px;
    }

    .pro-stat-tile {
        background: #ffffff;
        border: 1px solid rgba(30, 64, 175, 0.12);
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: var(--ui-shadow-soft);
    }

    .pro-stat-label {
        color: #64748b;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .pro-stat-value {
        color: #0f172a;
        font-size: 24px;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 6px;
    }

    .pro-stat-sub {
        color: #64748b;
        font-size: 12px;
        line-height: 1.35;
    }

    .pro-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 16px 0 8px;
        margin-top: 8px;
    }

    .pro-section-title {
        color: #0f172a;
        font-size: 22px;
        font-weight: 900;
        line-height: 1.1;
        margin: 0;
    }

    .pro-section-subtitle {
        color: #64748b;
        font-size: 13px;
        line-height: 1.45;
        margin-top: 5px;
    }

    .pro-section-meta {
        white-space: nowrap;
        padding: 7px 11px;
        border-radius: 999px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        font-size: 12px;
        font-weight: 900;
    }

    div[data-testid="stPlotlyChart"] {
        background: var(--ui-surface);
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: var(--ui-radius);
        padding: 12px;
        box-shadow: var(--ui-shadow-soft);
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        background: var(--ui-surface);
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: var(--ui-radius);
        padding: 8px;
        box-shadow: var(--ui-shadow-soft);
        overflow: hidden;
    }

    [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
        padding: 4px 0 8px;
    }

    [data-baseweb="tab"] {
        height: 42px;
        border-radius: var(--ui-radius-sm);
        padding: 0 16px;
        background: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.22);
        color: #334155;
        font-weight: 700;
    }

    [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, var(--ui-primary), #2563eb);
        color: #ffffff;
        border-color: transparent;
        box-shadow: 0 10px 24px rgba(30, 64, 175, 0.2);
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="tag"] {
        border-radius: var(--ui-radius-sm) !important;
        border-color: rgba(148, 163, 184, 0.32) !important;
    }

    [data-testid="stMultiSelect"] div[data-baseweb="tag"] {
        background: #e0f2fe !important;
        color: #075985 !important;
        font-weight: 700;
    }

    button[kind],
    .stButton > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-primary"] {
        border-radius: var(--ui-radius-sm) !important;
        font-weight: 800 !important;
        border: 1px solid rgba(30, 64, 175, 0.16) !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
    }

    [data-testid="stBaseButton-primary"],
    button[kind="primary"] {
        background: linear-gradient(135deg, var(--ui-primary), #2563eb) !important;
        color: #ffffff !important;
    }

    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid rgba(148, 163, 184, 0.24);
        border-radius: var(--ui-radius);
        box-shadow: var(--ui-shadow-soft);
        overflow: hidden;
    }

    div[data-testid="stCaptionContainer"] {
        color: var(--ui-muted);
        font-weight: 600;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    div[data-testid="stSegmentedControl"] label {
        border-radius: var(--ui-radius-sm) !important;
        font-weight: 800;
    }

    div[data-testid="stSlider"] [role="slider"] {
        background: var(--ui-primary);
        border-color: #ffffff;
    }

    @media (max-width: 1100px) {
        .block-container {
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .site-navbar {
            flex-wrap: wrap;
            gap: 10px 14px;
        }

        .site-brand-link {
            min-width: 0;
            flex: 1 1 260px;
        }

        .site-nav-actions {
            min-width: 0;
            flex: 0 1 auto;
        }

        .site-nav-links {
            order: 3;
            flex: 1 0 100%;
            justify-content: flex-start;
            overflow-x: auto;
            scrollbar-width: thin;
            padding: 2px 0 4px;
        }

        .pro-stat-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 1rem !important;
        }

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 1 1 300px !important;
            width: auto !important;
            min-width: 0 !important;
        }

        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            width: 100%;
            min-width: 0;
            box-sizing: border-box;
        }

        [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
            scrollbar-width: thin;
        }
    }

    @media (max-width: 760px) {
        .block-container {
            padding-left: 0.65rem;
            padding-right: 0.65rem;
            padding-bottom: 1.25rem;
        }

        .site-navbar {
            position: relative;
            top: 0;
            align-items: stretch;
            padding: 12px;
            margin-bottom: 14px;
            border-radius: 10px;
        }

        .site-brand-link {
            flex-basis: 100%;
        }

        .site-nav-links {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            overflow: visible;
            gap: 6px;
        }

        .site-nav-link {
            width: 100%;
            min-width: 0;
            padding: 0 8px;
            box-sizing: border-box;
        }

        .site-nav-actions {
            order: 4;
            width: 100%;
            justify-content: flex-start;
            flex-wrap: wrap;
        }

        .pro-hero-grid,
        .pro-stat-grid {
            grid-template-columns: 1fr;
        }

        .pro-hero {
            padding: 18px 16px;
            border-radius: 12px;
        }

        .pro-hero h1 {
            font-size: 25px;
            overflow-wrap: anywhere;
        }

        .pro-hero-panel {
            padding: 14px;
        }

        .pro-hero-panel-value {
            font-size: 22px;
            overflow-wrap: anywhere;
        }

        .pro-section-header {
            align-items: flex-start;
            flex-direction: column;
            gap: 8px;
        }

        .pro-section-title {
            font-size: 19px;
        }

        .pro-section-meta {
            white-space: normal;
        }

        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 1 1 100% !important;
            width: 100% !important;
        }

        div[data-testid="stPlotlyChart"] {
            padding: 4px;
            border-radius: 8px;
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            padding: 4px;
            overflow-x: auto;
        }

        [data-baseweb="tab"] {
            padding: 0 11px;
            white-space: nowrap;
        }
    }

    @media (max-width: 430px) {
        .site-brand-mark {
            width: 38px;
            height: 38px;
            flex: 0 0 38px;
        }

        .site-brand-title {
            font-size: 14px;
        }

        .site-brand-subtitle {
            font-size: 11px;
        }

        .site-lang-link {
            flex: 1 1 auto;
        }

        .pro-kicker {
            max-width: 100%;
            box-sizing: border-box;
            white-space: normal;
        }

        .insight-card {
            padding: 15px;
        }

        .insight-value {
            font-size: 22px;
        }
    }
    </style>
"""


def apply_styles():
    """Inject the shared dashboard CSS once per Streamlit run."""
    st.markdown(CSS, unsafe_allow_html=True)


def render_html(markup):
    """Render dedented trusted application markup."""
    st.html(textwrap.dedent(markup).strip())


def note_box(text):
    """Render a short contextual note above a chart or control group."""
    render_html(f'<div class="note-box">{html.escape(str(tr(text)))}</div>')

def render_kpi_card(label, value, subtext=""):
    """Render a standard KPI card."""
    render_html(
        f"""
        <div class="premium-kpi-card">
            <div class="premium-kpi-label">{html.escape(str(tr(label)))}</div>
            <div class="premium-kpi-value">{html.escape(str(tr(value)))}</div>
            <div class="premium-kpi-subtext">{html.escape(str(tr(subtext)))}</div>
        </div>
        """
    )

def render_insight_card(title, value, subtext="", status="neutral"):
    """Render a status-coded decision-support insight card."""
    badge_class = {
        "good": "badge-good",
        "warning": "badge-warning",
        "danger": "badge-danger",
        "neutral": "badge-neutral"
    }.get(status, "badge-neutral")

    badge_text = {
        "good": tr("Strong"),
        "warning": tr("Watch"),
        "danger": tr("High Risk"),
        "neutral": tr("Insight")
    }.get(status, tr("Insight"))

    render_html(
        f"""
        <div class="insight-card">
            <div class="badge {badge_class}">{html.escape(str(badge_text))}</div>
            <div class="insight-title">{html.escape(str(tr(title)))}</div>
            <div class="insight-value">{html.escape(str(tr(value)))}</div>
            <div class="insight-subtext">{html.escape(str(tr(subtext)))}</div>
        </div>
        """
    )

def render_narrative(text):
    """Render concise explanatory narrative text."""
    render_html(f'<div class="narrative-box">{html.escape(str(tr(text)))}</div>')


def render_measure_guide(include_forecast=True):
    """Explain recurring education measures without technical jargon."""
    if use_swahili():
        text = (
            "GPA: kipimo cha wastani wa ufaulu kinachotumiwa na NECTA; thamani ya chini ni bora. "
            "Kiwango cha Ufaulu: asilimia ya watahiniwa waliopata daraja la ufaulu."
        )
        if include_forecast:
            text += " Makadirio: mwelekeo wa baadaye unaokadiriwa kutokana na historia, si matokeo rasmi."
    else:
        text = (
            "GPA: NECTA's average academic performance indicator; lower is stronger. "
            "Pass Rate: the percentage of candidates who achieved passing grades."
        )
        if include_forecast:
            text += " Forecast: a projection from historical patterns, not an official result."
    render_narrative(text)


def render_key_findings(items, title="Key Findings", subtitle="What happened, why it matters, and the next priority."):
    """Render three to five escaped data-derived findings in a shared panel."""
    findings = [str(tr(item)).strip() for item in items if str(item).strip()][:5]
    if not findings:
        findings = [
            (
                "Hakuna data ya kutosha kutengeneza matokeo muhimu kwa uchaguzi wa sasa."
                if use_swahili()
                else "There is not enough data to generate key findings for the current selection."
            )
        ]
    list_items = "".join(f"<li>{html.escape(item)}</li>" for item in findings)
    render_html(
        f"""
        <div class="findings-panel">
            <h4>{html.escape(str(tr(title)))}</h4>
            <p>{html.escape(str(tr(subtitle)))}</p>
            <ul>{list_items}</ul>
        </div>
        """
    )


def interpretation_language():
    """Return the active chart interpretation language."""
    return st.session_state.get("chart_interpretation_language", "English")

def use_swahili():
    """Return whether Swahili interpretation is active."""
    return interpretation_language() == "Kiswahili"

TRANSLATIONS = {
    "Dashboard": "Dashibodi",
    "School": "Shule",
    "Subject": "Masomo",
    "Rankings": "Upangaji",
    "2032 Policy Planning": "Mipango ya Sera 2032",
    "CSEE Analytics Dashboard": "Dashibodi ya Uchambuzi wa CSEE",
    "Strong": "Imara",
    "Watch": "Angalia",
    "High Risk": "Hatari Kubwa",
    "Insight": "Taarifa",
    "Winner": "Mshindi",
    "Trained": "Imefundishwa",
    "Selected": "Imechaguliwa",
    "Model": "Modeli",
    "Target": "Kipimo",
    "Status": "Hali",
    "GPA": "GPA",
    "Pass Rate": "Kiwango cha Ufaulu",
    "Pass Rate (%)": "Kiwango cha Ufaulu (%)",
    "Average GPA": "Wastani wa GPA",
    "Subject GPA": "GPA ya Somo",
    "Average Subject GPA": "Wastani wa GPA ya Somo",
    "Average Subject GPA Change": "Mabadiliko ya Wastani wa GPA ya Somo",
    "Number of Candidates": "Idadi ya Watahiniwa",
    "Candidate Count": "Idadi ya Watahiniwa",
    "Candidates Sat": "Watahiniwa Waliofanya",
    "Candidates Passed": "Watahiniwa Waliofaulu",
    "Registered": "Waliosajiliwa",
    "Subject entries": "Majaribio ya somo",
    "Exam sitters": "Waliofanya mtihani",
    "Year": "Mwaka",
    "Region": "Mkoa",
    "School": "Shule",
    "Subject": "Somo",
    "Rank": "Nafasi",
    "Sat": "Waliofanya",
    "Passed": "Waliofaulu",
    "Division": "Daraja",
    "Count": "Idadi",
    "Actual": "Halisi",
    "Forecast": "Makadirio",
    "Series": "Mfululizo",
    "Performance Series": "Mfululizo wa Ufaulu",
    "Performance Direction": "Mwelekeo wa Ufaulu",
    "Region and Series": "Mkoa na Mfululizo",
    "Comparison Series": "Mfululizo wa Ulinganisho",
    "NECTA Division": "Daraja la NECTA",
    "Improved": "Imeimarika",
    "Improved Performance": "Ufaulu Umeimarika",
    "Declined": "Imeshuka",
    "Declined Performance": "Ufaulu Umeshuka",
    "Stable": "Imetulia",
    "No Material Change": "Hakuna Mabadiliko Makubwa",
    "Improving": "Inaimarika",
    "Declining": "Inashuka",
    "High": "Juu",
    "Moderate": "Wastani",
    "Safe": "Salama",
    "Critical": "Muhimu",
    "Medium": "Wastani",
    "Low": "Chini",
    "Total Schools": "Jumla ya Shule",
    "Unique schools in selection": "Shule za kipekee katika uchaguzi",
    "Lower NECTA GPA is better": "GPA ya chini ya NECTA ni bora",
    "Passed candidates over sat": "Waliofaulu kati ya waliofanya",
    "Division I": "Daraja I",
    "Share of sat candidates": "Sehemu ya watahiniwa waliofanya",
    "School GPA": "GPA ya Shule",
    "Lower is better": "Thamani ya chini ni bora",
    "Selected year": "Mwaka uliochaguliwa",
    "Subject GPA": "GPA ya Somo",
    "Selected filter": "Kichujio kilichochaguliwa",
    "Ranking Year": "Mwaka wa Upangaji",
    "Snapshot for top and bottom tables": "Muhtasari kwa majedwali ya juu na chini",
    "Improvement Window": "Kipindi cha Mabadiliko",
    "History used for momentum": "Historia inayotumika kupima mwenendo",
    "Top View": "Mwonekano wa Juu",
    "Best performance or improvement": "Ufaulu bora au uimarishaji",
    "Bottom View": "Mwonekano wa Chini",
    "Weakest performance or decline": "Ufaulu dhaifu au kushuka",
    "Key Findings": "Matokeo Muhimu",
    "The national result, the main gap, and the immediate planning priority.": "Matokeo ya kitaifa, pengo kuu, na kipaumbele cha haraka cha mipango.",
    "The selected school's latest movement, risk, strength, and next priority.": "Mabadiliko ya karibuni ya shule, hatari, nguvu, na kipaumbele kinachofuata.",
    "The strongest signal, the weakest area, and the teaching priority.": "Ishara yenye nguvu zaidi, eneo dhaifu zaidi, na kipaumbele cha ufundishaji.",
    "Who leads, who needs support, and where momentum is changing.": "Nani anaongoza, nani anahitaji msaada, na wapi mwenendo unabadilika.",
}

def tr(en, sw=None):
    """Translate a supported UI phrase when Swahili is active."""
    if use_swahili():
        return sw if sw is not None else TRANSLATIONS.get(str(en), str(en))
    return str(en)

def localize_phrase(text):
    """Translate recurring narrative phrases used by insight helpers."""
    translations = {
        "selected data": "data iliyochaguliwa",
        "selected regions": "mikoa iliyochaguliwa",
        "the selected dashboard filters": "vichujio vilivyochaguliwa",
        "the selected school": "shule iliyochaguliwa",
        "the two selected schools": "shule mbili zilizochaguliwa",
        "all selected subjects": "masomo yote yaliyochaguliwa",
        "Improving": "Inaimarika",
        "Declining": "Inashuka",
        "Stable": "Imetulia",
        "GPA": "GPA",
        "pass rate": "kiwango cha ufaulu",
        "Pass Rate (%)": "Kiwango cha Ufaulu (%)",
        "subject GPA": "GPA ya somo",
        "candidate count": "idadi ya watahiniwa",
        "Average GPA": "wastani wa GPA",
        "Average Subject GPA": "wastani wa GPA ya somo",
        "Pass Rate": "kiwango cha ufaulu",
        "Pass Rate (%)": "kiwango cha ufaulu (%)",
        "School GPA": "GPA ya shule",
        "School Pass Rate": "kiwango cha ufaulu cha shule",
        "Regional GPA": "GPA ya mkoa",
        "Subject Pass Rate": "kiwango cha ufaulu wa somo",
    }
    if not use_swahili():
        return str(text)
    return translations.get(str(text), TRANSLATIONS.get(str(text), str(text)))

def render_chart_insight(text, sw_text=None):
    """Render a plain-language interpretation below a chart."""
    display_text = sw_text if use_swahili() and sw_text is not None else tr(text)
    render_html(f'<div class="chart-insight">{html.escape(str(display_text))}</div>')


def render_sidebar_brand():
    """Render the legacy sidebar brand component when a sidebar is enabled."""
    render_html(
        """
        <div class="pro-sidebar-brand">
            <div class="pro-sidebar-mark">ND</div>
            <div class="pro-sidebar-title">NECTA Data Intelligence</div>
            <div class="pro-sidebar-subtitle">Executive analytics for CSEE school, subject, regional and predictive performance.</div>
        </div>
        """
    )


def render_top_nav(active_page="Dashboard", active_language="English"):
    """Render the responsive top navigation and language controls."""
    pages = ["Dashboard", "School", "Subject", "Rankings", "2032 Policy Planning"]
    languages = ["English", "Kiswahili"]

    nav_links = []
    for page in pages:
        active_class = " active" if page == active_page else ""
        nav_links.append(
            f'<a class="site-nav-link{active_class}" href="?page={quote(page)}&lang={quote(active_language)}">{html.escape(tr(page))}</a>'
        )

    language_links = []
    for language in languages:
        active_class = " active" if language == active_language else ""
        language_links.append(
            f'<a class="site-lang-link{active_class}" href="?page={quote(active_page)}&lang={quote(language)}">{html.escape(language)}</a>'
        )

    render_html(
        f"""
        <nav class="site-navbar">
            <a class="site-brand-link" href="?page=Dashboard&lang={quote(active_language)}">
                <div class="site-brand-mark" aria-label="Tanzania flag"><div class="tz-flag"></div></div>
                <div>
                    <div class="site-brand-title">NECTA Data</div>
                    <div class="site-brand-subtitle">{html.escape(tr("CSEE Analytics Dashboard"))}</div>
                </div>
            </a>
            <div class="site-nav-links">
                {"".join(nav_links)}
            </div>
            <div class="site-nav-actions">
                {"".join(language_links)}
            </div>
        </nav>
        """
    )


def render_page_hero(title, subtitle, kicker="Executive Analytics", panel_title="", panel_value="", panel_subtext=""):
    """Render a consistent page introduction and optional coverage panel."""
    panel_html = ""
    if panel_title or panel_value or panel_subtext:
        panel_html = (
            '<div class="pro-hero-panel">'
            f'<div class="pro-hero-panel-label">{html.escape(str(tr(panel_title)))}</div>'
            f'<div class="pro-hero-panel-value">{html.escape(str(tr(panel_value)))}</div>'
            f'<div class="pro-hero-panel-sub">{html.escape(str(tr(panel_subtext)))}</div>'
            '</div>'
        )

    render_html(
        f"""
        <div class="pro-hero">
            <div class="pro-hero-grid">
                <div>
                    <div class="pro-kicker">{html.escape(str(tr(kicker)))}</div>
                    <h1>{html.escape(str(tr(title)))}</h1>
                    <p>{html.escape(str(tr(subtitle)))}</p>
                </div>
                {panel_html}
            </div>
        </div>
        """
    )


def render_stat_strip(items):
    """Render a responsive row of KPI summary tiles."""
    tiles = []
    for label, value, subtext in items:
        tiles.append(
            '<div class="pro-stat-tile">'
            f'<div class="pro-stat-label">{html.escape(str(tr(label)))}</div>'
            f'<div class="pro-stat-value">{html.escape(str(tr(value)))}</div>'
            f'<div class="pro-stat-sub">{html.escape(str(tr(subtext)))}</div>'
            '</div>'
        )
    render_html(f'<div class="pro-stat-grid">{"".join(tiles)}</div>')


def render_section_header(title, subtitle="", meta=""):
    """Render a consistent section title, guidance line, and metadata label."""
    meta_html = f'<div class="pro-section-meta">{html.escape(str(tr(meta)))}</div>' if meta else ""
    render_html(
        f"""
        <div class="pro-section-header">
            <div>
                <div class="pro-section-title">{html.escape(str(tr(title)))}</div>
                <div class="pro-section-subtitle">{html.escape(str(tr(subtitle)))}</div>
            </div>
            {meta_html}
        </div>
        """
    )

