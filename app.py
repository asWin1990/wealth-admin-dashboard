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
        with st.spinner("Pulling live prices, ETF P/E-P/B, Gold INR & Gemini AI brief..."):
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
            label="📄 Export Printable Brief (HTML)",
            data=printable_html,
            file_name="AURA_BI_Daily_Brief.html",
            mime="text/html",
            use_container_width=True,
        )
        st.caption("Open downloaded file in browser & press Ctrl+P for a crisp white-paper PDF.")

    st.divider()
    st.caption("Auto-Schedule: 8:30 AM & 4:30 PM IST (Mon–Fri)")

if not snapshot:
    st.warning("No snapshot found yet. Click **🔄 Refresh Live Data & AI** in the sidebar.")
    st.stop()

ai = snapshot.get("ai_strategist", {})
macro = snapshot.get("macro_manual", {})
markets = snapshot.get("markets", {})


def format_price(item):
    if not item or item.get("price") is None:
        return "—"
    cur = item.get("currency", "")
    val = item["price"]
    if cur == "%":
        return f"{val:.2f}%"
    if cur in ["₹", "$"]:
        return f"{cur}{val:,.2f}"
    return f"{val:,.2f}"


# --- HEADER ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    regime = ai.get("market_regime", "Awaiting AI Sync")
    st.markdown(
        f"""
        <div class="brand-title">AURA BI AGENT</div>
        <div class="brand-sub">
            Updated: <strong>{snapshot.get('updated_at_ist', 'N/A')}</strong>
            <span class="regime-pill">REGIME: {regime.upper()}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_h2:
    with st.popover("ℹ️ BI Methodology"):
        st.markdown("""
        * **BI Stance:** Algorithmic score combining **P/E & P/B multiples** (via liquid ETF proxies), **200-DMA trend**, **1M/3M momentum**, and **1Y Sharpe**.
        * **vs 200-DMA:** `< 0%` with positive `1M` flags early reversal; `> +16%` flags overextended risk.
        * **Sharpe (1Y):** Risk-adjusted return over India's 6.8% risk-free rate.
        """)

st.markdown("<br>", unsafe_allow_html=True)

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
    ("Gold (INR / 10g)", find_item("macro_commodities_fx", "Gold (INR")),
    ("USD / INR", find_item("macro_commodities_fx", "USD / INR")),
]

kpi_cols = st.columns(6)
for idx, (label, item) in enumerate(kpis):
    with kpi_cols[idx]:
        if item:
            d1 = item.get("1D") or 0
            cls = "kpi-pos" if d1 >= 0 else "kpi-neg"
            sign = "+" if d1 > 0 else ""
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-val">{format_price(item)}</div>
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
          <div class="kpi-pos">Spread: +{spread:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- AI AGENT BRIEF ---
if ai:
    c1, c2 = st.columns(2)
    with c1:
        opp_md = "<br>".join(f"• {x}" for x in ai.get("opportunities", []))
        st.markdown(f'<div class="ai-box"><strong>🎯 BI Opportunities (Value + Momentum)</strong><br><br>{opp_md}</div>', unsafe_allow_html=True)
    with c2:
        risk_md = "<br>".join(f"• {x}" for x in ai.get("risk_flags", []))
        st.markdown(f'<div class="ai-box"><strong>⚠️ Risk & Overextension Alerts</strong><br><br>{risk_md}</div>', unsafe_allow_html=True)
    st.info(f"**🏦 Debt Duration & Macro Call:** {ai.get('debt_and_macro', 'N/A')}")


# --- HEATMAP RENDERER ---
def render_heatmap(items, show_valuation=True):
    if not items:
        st.info("No data available. Click **🔄 Refresh Live Data & AI** in the sidebar.")
        return

    rows = []
    for x in items:
        row = {
            "Benchmark": x["name"],
            "Price": format_price(x),
            "1D": x.get("1D"),
            "1W": x.get("1W"),
            "1M": x.get("1M"),
            "3M": x.get("3M"),
            "1Y": x.get("1Y"),
            "3Y CAGR": x.get("3Y_CAGR"),
            "5Y CAGR": x.get("5Y_CAGR"),
            "Vol %": x.get("volatility_1y"),
            "Sharpe": x.get("sharpe_1y"),
            "vs 200-DMA": x.get("dist_200dma"),
            "RSI": x.get("rsi_14"),
            "vs 52W High": x.get("from_52w_high"),
        }
       if show_valuation:
            row["P/E"] = x.get("pe")
        row["BI Stance"] = x.get("bi_stance", "Neutral")
        rows.append(row)

    df = pd.DataFrame(rows)
    ret_cols = ["1D", "1W", "1M", "3M", "1Y", "3Y CAGR", "5Y CAGR", "vs 200-DMA"]

    def color_cells(val):
        if pd.isna(val):
            return ""
        if val >= 10:
            return "background-color: rgba(16, 185, 129, 0.28); color: #A7F3D0; font-weight: 600;"
        if val > 0:
            return "background-color: rgba(16, 185, 129, 0.12); color: #D1FAE5;"
        if val <= -10:
            return "background-color: rgba(239, 68, 68, 0.28); color: #FECACA; font-weight: 600;"
        if val < 0:
            return "background-color: rgba(239, 68, 68, 0.12); color: #FEE2E2;"
        return ""

   fmt_map = {c: "{:+.2f}%" for c in ret_cols} | {
        "Vol %": "{:.1f}%",
        "Sharpe": "{:.2f}",
        "RSI": "{:.1f}",
        "vs 52W High": "{:+.1f}%",
    }
    if show_valuation:
        fmt_map["P/E"] = "{:.1f}"

    styled = df.style.map(color_cells, subset=ret_cols).format(fmt_map, na_rep="—")
    st.dataframe(styled, use_container_width=True, hide_index=True)


# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Equity & Valuation Heatmaps",
    "🧭 Sector Rotation Radar",
    "📰 Top 10 Verified News",
    "🌍 Macro, FX & Commodities",
])

with tab1:
    st.markdown("#### Indian Broad Equity & MF Category Benchmarks")
    render_heatmap(markets.get("indian_equity", []), show_valuation=True)
    st.markdown("#### Indian Sectoral Benchmarks")
    render_heatmap(markets.get("indian_sectors", []), show_valuation=True)
    st.markdown("#### Global Markets (Indian International FoF Exposure)")
    render_heatmap(markets.get("global_indices", []), show_valuation=True)

with tab2:
    st.markdown("#### Sector Trend vs. Momentum Quadrant")
    sectors = markets.get("indian_sectors", [])
    if sectors:
        sdf = pd.DataFrame(sectors).dropna(subset=["dist_200dma", "3M"])
        if not sdf.empty:
            fig = px.scatter(
                sdf,
                x="dist_200dma",
                y="3M",
                text="name",
                color="bi_stance",
                size=sdf["volatility_1y"].fillna(15),
                labels={"dist_200dma": "Distance from 200-DMA (%)", "3M": "3-Month Return (%)"},
                template="plotly_dark",
                height=500,
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,25,40,0.5)")
            fig.add_vline(x=0, line_dash="dash", line_color="#64748B")
            fig.add_hline(y=0, line_dash="dash", line_color="#64748B")
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### Top 10 Verified Financial News")
    filter_reg = st.radio("Filter Region", ["ALL", "INDIA", "GLOBAL"], horizontal=True)
    news_list = snapshot.get("verified_news", [])
    if not news_list:
        st.info("Click **🔄 Refresh Live Data & AI** in the sidebar to populate today's AI-verified news wire.")
    for n in news_list:
        if filter_reg != "ALL" and n.get("region", "").upper() != filter_reg:
            continue
        st.markdown(
            f"""
            <div class="news-card">
              <span class="badge">{n.get('region', '')}</span>
              <span class="badge">{n.get('tag', '')}</span>
              <a href="{n.get('link', '#')}" target="_blank" style="color:#F8FAFC;font-weight:600;text-decoration:none;font-size:15px;">
                {n.get('title', '')}
              </a>
              <div style="font-size:13px;color:#94A3B8;margin-top:6px;">
                {n.get('impact', '')} <em>— {n.get('source', '')}</em>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab4:
    st.markdown("#### Gold (INR & USD), Commodities, FX & Global Yields")
    render_heatmap(markets.get("macro_commodities_fx", []), show_valuation=False)
