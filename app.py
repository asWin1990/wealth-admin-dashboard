import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from fetch_data import run_fetch
from ai_analyst import run_ai_analysis
from notifier import build_html_email

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
    .block-container { padding-top: 2.2rem; max-width: 1560px; }

    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] li,
    div[data-testid="stExpander"] code {
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
    }

    .brand-title {
        font-size: 28px; font-weight: 700; letter-spacing: 1.2px;
        background: linear-gradient(90deg, #F8FAFC 0%, #E2C06D 60%, #D4AF37 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .brand-sub { font-size: 12px; color: #94A3B8; letter-spacing: 0.4px; margin-top: 4px; }
    .regime-pill {
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        background: rgba(212, 175, 55, 0.14); border: 1px solid rgba(212, 175, 55, 0.4);
        color: #F3D58D; font-size: 11px; font-weight: 600; margin-left: 8px;
        animation: pulseGold 2.8s infinite;
    }

    .kpi-card {
        background: rgba(17, 25, 40, 0.72);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 2px solid rgba(212, 175, 55, 0.7);
        border-radius: 10px; padding: 14px 15px;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: rgba(212, 175, 55, 0.6);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    .kpi-label { font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.9px; font-weight: 600; }
    .kpi-val { font-size: 19px; font-weight: 700; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; margin-top: 6px; }
    .kpi-pos { font-size: 12px; color: #34D399; font-weight: 700; margin-top: 3px; font-family: 'JetBrains Mono', monospace; }
    .kpi-neg { font-size: 12px; color: #F87171; font-weight: 700; margin-top: 3px; font-family: 'JetBrains Mono', monospace; }

    .ai-box {
        background: rgba(17, 25, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #D4AF37;
        padding: 16px 2
