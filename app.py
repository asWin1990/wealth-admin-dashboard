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

# --- SLEEK INSTITUTIONAL TERMINAL CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

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
    .block-container { padding-top: 2.2rem; max-width: 1450px; }

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
    }

    .kpi-card {
        background: rgba(17, 25, 40, 0.72);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 2px solid rgba(212, 175, 55, 0.7);
        border-radius: 10px; padding: 15px 16px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(212, 175, 55, 0.55);
    }
    .kpi-label { font-size: 10.5px; color: #94A3B8; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .kpi-val { font-size: 21px; font-weight: 700; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; margin-top: 6px; }
    .kpi-pos { font-size: 12px; color: #34D399; font-weight: 600; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }
    .kpi-neg { font-size: 12px; color: #F87171; font-weight: 600; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }

    .ai-box {
        background: rgba(17, 25, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #D4AF37;
        padding: 16px 20px; border-radius: 8px; margin-bottom: 12px;
        color: #E2E8F0; font-size: 13.5px; line-height: 1.6;
    }
    .news-card {
        background: rgba(17, 25, 40, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
    }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 10.5px; font-weight: 700; background: rgba(212, 175, 55, 0.14);
        color: #E2C06D; margin-right: 6px; letter-spacing: 0.4px;
    }
    h3, h4 { color: #E2C06D !important; font-weight: 600 !important; letter-spacing: 0.3px; }
    button[data-baseweb="tab"] {
        color: #94A3B8 !important; font-weight: 600 !important; font-size: 14px !important; padding: 10px 16px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #F3D58D !important; border-bottom-color: #D4AF37 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- LOAD SNAPSHOT ---
SNAPSHOT_PATH = "data/market_snapshot.json"
snapshot = None
if os.path.exists(SNAPSHOT_PATH):
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### ⚡ AURA BI AGENT")
    st.caption("Autonomous Market & Valuation Intelligence")
    st.divider()

    if st.button("🔄 Refresh Live Data & AI", use_container_width=True, type="primary"):
        with st.spinner("Pulling live prices, P/E multiples, Gold INR & Gemini AI brief..."):
            run_fetch()
            if os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None):
                if "GEMINI_API_KEY" not in os.environ and "GEMINI_API_KEY" in st.secrets:
                    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
                run_ai_analysis()
        st.success("Terminal updated!")
        st.rerun()

    if snapshot:
        printable_html = build_html_email(snapshot, "https://share.streamlit.io")
        st.download_button(
            label="
