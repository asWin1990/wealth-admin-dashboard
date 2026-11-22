import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from fetch_data import run_fetch
from ai_analyst import run_ai_analysis

st.set_page_config(
    page_title="Wealth Admin | Daily Market Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🏛️ Wealth Desk Controls")
    print_mode = st.toggle("🖨️ Printable Brief Mode (Light)", value=False)
    st.caption("Toggle on and press Ctrl+P to export a clean PDF brief.")
    st.divider()

    if st.button("🔄 Refresh Market & AI Now", use_container_width=True, type="primary"):
        with st.spinner("Fetching live market data, macro rates & Tier-1 news..."):
            run_fetch()
            if os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None):
                if "GEMINI_API_KEY" not in os.environ and "GEMINI_API_KEY" in st.secrets:
                    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
                run_ai_analysis()
        st.success("Dashboard refreshed!")
        st.rerun()

    st.divider()
    st.markdown("**Schedule:** Auto-updates at `8:30 AM` & `4:30 PM IST` (Mon–Fri).")
    st.markdown("**Config:** Edit `config.yaml` on GitHub to update your Overweight / Underweight stances.")


# --- PRIVATE-BANK DARK / PRINT CSS ---
if not print_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0B0F17; color: #E2E8F0; }
        section[data-testid="stSidebar"] { background-color: #0F1520; border-right: 1px solid #1E293B; }
        h1, h2, h3 { color: #D4AF37 !important; font-family: 'Segoe UI', sans-serif; letter-spacing: 0.4px; }
        .kpi-card {
            background: #131A26; border: 1px solid #1F2937; border-top: 2px solid #D4AF37;
            border-radius: 8px; padding: 14px 16px; margin-bottom: 8px;
        }
        .kpi-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; }
        .kpi-val { font-size: 22px; font-weight: 700; color: #F8FAFC; font-family: monospace; margin-top: 4px; }
        .kpi-delta-pos { font-size: 12px; color: #10B981; font-weight: 600; }
        .kpi-delta-neg { font-size: 12px; color: #EF4444; font-weight: 600; }
        .ai-box {
            background: #131A26; border-left: 4px solid #D4AF37; padding: 16px 20px;
            border-radius: 6px; margin-bottom: 16px;
        }
        .news-card {
            background: #131A26; border: 1px solid #1E293B; border-radius: 6px;
            padding: 12px 16px; margin-bottom: 10px;
        }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 700; background: #1E293B; color: #D4AF37; margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp { background-color: #FFFFFF; color: #0F172A; }
        h1, h2, h3 { color: #0F172A !important; }
        .kpi-card { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; }
        .kpi-label { font-size: 11px; color: #475569; text-transform: uppercase; }
        .kpi-val { font-size: 20px; font-weight: 700; color: #0F172A; font-family: monospace; }
        .kpi-delta-pos { font-size: 12px; color: #15803D; font-weight: 600; }
        .kpi-delta-neg { font-size: 12px; color: #B91C1C; font-weight: 600; }
        .ai-box { background: #F8FAFC; border-left: 4px solid #0F172A; padding: 14px; margin-bottom: 12px; }
        .news-card { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
        .badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; background: #E2E8F0; color: #0F172A; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- LOAD DATA ---
SNAPSHOT_PATH = "data/market_snapshot.json"
if not os.path.exists(SNAPSHOT_PATH):
    st.warning("No daily snapshot found yet. Click **🔄 Refresh Market & AI Now** in the sidebar to generate your first brief.")
    st.stop()

with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
    snapshot = json.load(f)

ai = snapshot.get("ai_strategist", {})
macro = snapshot.get("macro_manual", {})
markets = snapshot.get("markets", {})


# --- HEADER ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("## 🏛️ WEALTH MANAGEMENT DAILY INTELLIGENCE")
    st.caption(f"Last Updated: **{snapshot.get('updated_at_ist', 'N/A')}** &nbsp;|&nbsp; Market Regime: **{ai.get('market_regime', 'Awaiting AI Run')}**")
with col_h2:
    with st.popover("ℹ️ Metric Guide"):
        st.markdown("""
        * **Dist 200-DMA:** `%` above/below 200-day average. `< 0%` with positive `1M` often flags early mean-reversion; `> +15%` signals extended/overbought.
        * **Sharpe (1Y):** Risk-adjusted return over India's risk-free rate (`6.8%`). `> 1.0` is strong; `< 0` means underperforming safe debt.
        * **Volatility (1Y):** Annualized standard deviation. Higher = wider drawdowns.
        * **Stance vs. Signal:** Highlights when market data diverges from your `config.yaml` view.
        """)


# --- TOP KPI PULSE STRIP ---
def find_item(cat, keyword):
    for x in markets.get(cat, []):
        if keyword.lower() in x["name"].lower():
            return x
    return None

kpis = [
    ("Nifty 50", find_item("indian_equity", "Nifty 50")),
    ("India VIX", find_item("indian_equity", "VIX")),
    ("S&P 500", find_item("global_indices", "S&P 500")),
    ("Gold (India ETF)", find_item("macro_commodities_fx", "Gold Bees")),
    ("USD / INR", find_item("macro_commodities_fx", "USD / INR")),
]

kpi_cols = st.columns(6)
for idx, (label, item) in enumerate(kpis):
    with kpi_cols[idx]:
        if item:
            d1 = item.get("1D") or 0
            cls = "kpi-delta-pos" if d1 >= 0 else "kpi-delta-neg"
            sign = "+" if d1 > 0 else ""
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-val">{item['price']:,.2f}</div>
                  <div class="{cls}">{sign}{d1:.2f}% (1D)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with kpi_cols[5]:
    repo = macro.get("rbi_repo_rate", 6.50)
    gsec = macro.get("india_10y_gsec_approx", 6.85)
    spread = round(gsec - repo, 2)
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">RBI Repo / 10Y G-Sec</div>
          <div class="kpi-val">{repo:.2f}% / {gsec:.2f}%</div>
          <div class="kpi-delta-pos">Spread: +{spread:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- AI STRATEGIST DESK ---
if ai:
    st.markdown("### 🧠 AI Strategist Desk")
    c1, c2 = st.columns(2)
    with c1:
        opp_md = "\n".join(f"- {x}" for x in ai.get("opportunities", []))
        st.markdown(f'<div class="ai-box"><strong>🎯 Valuation & Momentum Opportunities</strong><br>{opp_md}</div>', unsafe_allow_html=True)
    with c2:
        risk_md = "\n".join(f"- {x}" for x in ai.get("risk_flags", []))
        st.markdown(f'<div class="ai-box"><strong>⚠️ Risk & Stance Divergence Flags</strong><br>{risk_md}</div>', unsafe_allow_html=True)
    st.info(f"**🏦 Debt Duration & Macro Call:** {ai.get('debt_and_macro', 'N/A')}")


# --- HELPER: MULTI-HORIZON HEATMAP TABLE ---
def render_heatmap(items):
    if not items:
        st.info("No data available.")
        return
    df = pd.DataFrame(items)
    cols = [
        "name", "price", "1D", "1W", "1M", "3M", "1Y", "3Y_CAGR", "5Y_CAGR",
        "volatility_1y", "sharpe_1y", "dist_200dma", "pe", "stance", "signal"
    ]
    df = df[[c for c in cols if c in df.columns]].rename(columns={
        "name": "Benchmark", "price": "Price", "3Y_CAGR": "3Y CAGR", "5Y_CAGR": "5Y CAGR",
        "volatility_1y": "Vol %", "sharpe_1y": "Sharpe", "dist_200dma": "vs 200-DMA",
        "pe": "P/E", "stance": "My Stance", "signal": "Signal"
    })

    ret_cols = [c for c in ["1D", "1W", "1M", "3M", "1Y", "3Y CAGR", "5Y CAGR", "vs 200-DMA"] if c in df.columns]

    def color_cells(val):
        if pd.isna(val):
            return ""
        if val >= 10:
            return "background-color: rgba(16, 185, 129, 0.35); color: #ECFDF5; font-weight: 600;"
        if val > 0:
            return "background-color: rgba(16, 185, 129, 0.15);"
        if val <= -10:
            return "background-color: rgba(239, 68, 68, 0.35); color: #FEF2F2; font-weight: 600;"
        if val < 0:
            return "background-color: rgba(239, 68, 68, 0.15);"
        return ""

    styled = (
        df.style.map(color_cells, subset=ret_cols)
        .format(
            {c: "{:+.2f}%" for c in ret_cols} | {"Price": "{:,.2f}", "Vol %": "{:.1f}%", "Sharpe": "{:.2f}", "P/E": "{:.1f}"},
            na_rep="—",
        )
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Multi-Horizon Heatmaps",
    "🧭 Sector Rotation Radar",
    "📰 Top 10 Verified News",
    "🌍 Macro, FX & Commodities"
])

with tab1:
    st.markdown("#### Indian Broad Equity & MF Category Benchmarks")
    render_heatmap(markets.get("indian_equity", []))
    st.markdown("#### Indian Sectoral Benchmarks")
    render_heatmap(markets
