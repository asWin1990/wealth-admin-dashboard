import os
import json
import time
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from fetch_data import run_fetch
from ai_analyst import run_ai_analysis
from notifier import build_html_email

IST = timezone(timedelta(hours=5, minutes=30))
SNAPSHOT_PATH = "data/market_snapshot.json"
DEFAULT_STALE_HOURS = 6

st.set_page_config(
    page_title="AURA BI AGENT | Market Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

    @keyframes pulseGold {
        0% { box-shadow: 0 0 0 0 rgba(212, 175, 55, 0.25); }
        70% { box-shadow: 0 0 0 8px rgba(212, 175, 55, 0); }
        100% { box-shadow: 0 0 0 0 rgba(212, 175, 55, 0); }
    }

    .stApp {
        background: radial-gradient(circle at 15% 0%, #111C33 0%, #070B14 55%, #05080F 100%);
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
    }
    header[data-testid="stHeader"] {
        background: rgba(7, 11, 20, 0.85) !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    section[data-testid="stSidebar"] {
        background: #090E1A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    .block-container { padding-top: 1.3rem; padding-bottom: 1.5rem; max-width: 1640px; }

    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] li,
    div[data-testid="stExpander"] code {
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
    }

    .brand-title {
        font-size: 25px; font-weight: 700; letter-spacing: 1.1px;
        background: linear-gradient(90deg, #F8FAFC 0%, #E2C06D 60%, #D4AF37 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0; line-height: 1.2;
    }
    .brand-sub { font-size: 12px; color: #94A3B8; letter-spacing: 0.3px; margin-top: 3px; }
    .regime-pill {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        background: rgba(212, 175, 55, 0.14); border: 1px solid rgba(212, 175, 55, 0.4);
        color: #F3D58D; font-size: 10.5px; font-weight: 600; margin-left: 8px;
        animation: pulseGold 2.8s infinite;
    }
    .status-fresh {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(52, 211, 153, 0.45);
        color: #34D399; font-size: 10.5px; font-weight: 700; margin-left: 6px;
    }
    .status-aging {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(251, 191, 36, 0.45);
        color: #FBBF24; font-size: 10.5px; font-weight: 700; margin-left: 6px;
    }
    .status-stale {
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        background: rgba(239, 68, 68, 0.18); border: 1px solid rgba(248, 113, 113, 0.5);
        color: #F87171; font-size: 10.5px; font-weight: 700; margin-left: 6px;
    }
    .tbl-header-row {
        display: flex; align-items: baseline; justify-content: space-between;
        margin-top: 0.65rem; margin-bottom: 0.35rem; gap: 10px; flex-wrap: wrap;
    }
    .tbl-title {
        color: #E2C06D; font-weight: 600; font-size: 15.5px; letter-spacing: 0.25px;
    }
    .tbl-asof {
        font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #94A3B8;
        background: rgba(30, 41, 59, 0.65); border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 2px 8px; border-radius: 5px;
    }

    .kpi-card {
        background: rgba(17, 25, 40, 0.72);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 2px solid rgba(212, 175, 55, 0.7);
        border-radius: 9px; padding: 10px 12px;
        transition: transform 0.16s ease, border-color 0.16s ease;
    }
    .kpi-card:hover { transform: translateY(-2px); border-color: rgba(212, 175, 55, 0.6); }
    .kpi-label { font-size: 9.5px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }
    .kpi-val { font-size: 16.5px; font-weight: 700; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; margin-top: 3px; }
    .kpi-pos { font-size: 11px; color: #34D399; font-weight: 700; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }
    .kpi-neg { font-size: 11px; color: #F87171; font-weight: 700; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }

    .ai-box {
        background: rgba(17, 25, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #D4AF37;
        padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;
        color: #E2E8F0; font-size: 13px; line-height: 1.5;
    }
    .alert-card {
        background: rgba(17, 25, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
    }
    .news-card {
        background: rgba(17, 25, 40, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px; padding: 11px 15px; margin-bottom: 8px;
    }
    .badge {
        display: inline-block; padding: 2px 7px; border-radius: 4px;
        font-size: 10px; font-weight: 700; background: rgba(212, 175, 55, 0.14);
        color: #E2C06D; margin-right: 6px;
    }
    h3, h4 { color: #E2C06D !important; font-weight: 600 !important; letter-spacing: 0.25px; margin-top: 0.5rem !important; margin-bottom: 0.35rem !important; }
    button[data-baseweb="tab"] {
        color: #94A3B8 !important; font-weight: 600 !important; font-size: 13px !important; padding: 8px 11px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #F3D58D !important; border-bottom-color: #D4AF37 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def parse_snapshot_dt(snap):
    if not snap:
        return None
    raw_str = snap.get("updated_at_ist", "")
    for fmt in ("%d %b %Y, %I:%M %p IST", "%d %b %Y, %H:%M IST"):
        try:
            dt = datetime.strptime(raw_str, fmt)
            return dt.replace(tzinfo=IST)
        except ValueError:
            continue
    if os.path.exists(SNAPSHOT_PATH):
        mtime = os.path.getmtime(SNAPSHOT_PATH)
        return datetime.fromtimestamp(mtime, tz=IST)
    return None


def format_as_of_stamp(snap):
    dt = parse_snapshot_dt(snap)
    if dt:
        return f"as of {dt.strftime('%d %b')} (at {dt.strftime('%H:%M')})"
    return "as of —"


def render_section_heading(title, as_of_text):
    st.markdown(
        f"""
        <div class="tbl-header-row">
            <span class="tbl-title">{title}</span>
            <span class="tbl-asof">{as_of_text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_freshness_info(snap, stale_hours=DEFAULT_STALE_HOURS):
    now_ist = datetime.now(IST)
    dt = parse_snapshot_dt(snap)
    if not dt:
        return "UNKNOWN", "No timestamp available", "status-stale"

    age_delta = now_ist - dt
    age_hours = max(0.0, age_delta.total_seconds() / 3600.0)

    if age_hours < 1:
        age_label = f"{max(1, int(age_delta.total_seconds() // 60))}m ago"
    elif age_hours < 24:
        age_label = f"{age_hours:.1f}h ago"
    else:
        age_label = f"{age_delta.days}d {(age_delta.seconds // 3600)}h
