import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from fetch_data import run_fetch
from ai_analyst import run_ai_analysis

st.set_page_config(
    page_title="Wealth Desk | Daily Market Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🏛️ Wealth Desk")
    print_mode = st.toggle("🖨️ Printable Brief (Light)", value=False)
    st.caption("Toggle on and press Ctrl+P to export a clean PDF.")
    st.divider()

    if st.button("🔄 Refresh Market & AI Now", use_container_width=True, type="primary"):
        with st.spinner("Pulling live market data, Gold INR, BI Stances & Tier-1 news..."):
            run_fetch()
            if os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None):
                if "GEMINI_API_KEY" not in os.environ and "GEMINI_API_KEY" in st.secrets:
                    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
                run_ai_analysis()
        st.success("Dashboard updated!")
        st.rerun()

    st.divider()
    st.caption("Auto-Schedule: 8:30 AM & 4:30 PM IST (Mon–Fri)")


# --- INSTITUTIONAL PRIVATE-BANK STYLING ---
if not print_mode:
    st.markdown(
        """
        <style>
        header[data-testid="stHeader"] { background-color: #0A0E17 !important; border-bottom: 1px solid #1E293B; }
        .block-container { padding-top: 2rem; }
        h1, h2, h3, h4 { color: #E2C06D !important; font-weight: 600; letter-spacing: 0.3px; }
        .kpi-card {
            background: #111827; border: 1px solid #1F2937; border-top: 2px solid #D4AF37;
            border-radius: 6px; padding: 14px 16px;
        }
        .kpi-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px; }
        .kpi-val { font-size: 21px; font-weight: 700; color: #F8FAFC; font-family: 'Consolas', monospace; margin-top: 4px; }
        .kpi-pos { font-size: 12px; color: #10B981; font-weight: 600; }
        .kpi-neg { font-size: 12px; color: #F87171; font-weight: 600; }
        .ai-box {
            background: #111827; border: 1px solid #1F2937; border-left: 3px solid #D4AF37;
            padding: 14px 18px; border-radius: 6px; margin-bottom: 12px; color: #E2E8F0;
        }
        .news-card {
            background: #111827; border: 1px solid #1F2937; border-radius: 6px;
            padding: 14px 16px; margin-bottom: 10px;
        }
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 11px; font-weight: 700; background: #1E293B; color: #E2C06D; margin-right: 6px;
        }
        button[data-baseweb="tab"] {
            color: #94A3B8 !important; font-weight: 600 !important; font-size: 14px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #E2C06D !important; border-bottom-color: #D4AF37 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        .stApp, header[data-testid="stHeader"] { background-color: #FFFFFF !important; color: #0F172A !important; }
        h1, h2, h3, h4 { color: #0F172A !important; }
        .kpi-card { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; }
        .kpi-label { font-size: 11px; color: #475569; text-transform: uppercase; }
        .kpi-val { font-size: 20px; font-weight: 700; color: #0F172A; font-family: monospace; }
        .kpi-pos { font-size: 12px; color: #15803D; font-weight: 600; }
        .kpi-neg { font-size: 12px; color: #B91C1C; font-weight: 600; }
        .ai-box { background: #F8FAFC; border-left: 3px solid #0F172A; padding: 14px; color: #0F172A; }
        .news-card { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; margin-bottom: 8px; }
        .badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; background: #E2E8F0; color: #0F172A; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- LOAD SNAPSHOT ---
SNAPSHOT_PATH = "data/market_snapshot.json"
if not os.path.exists(SNAPSHOT_PATH):
    st.warning("No snapshot found. Click **🔄 Refresh Market & AI Now** in the sidebar.")
    st.stop()

with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
    snapshot = json.load(f)

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
    st.markdown("## WEALTH MANAGEMENT DAILY INTELLIGENCE")
    st.caption(f"Last Updated: **{snapshot.get('updated_at_ist', 'N/A')}**  |  Market Regime: **{ai.get('market_regime', 'Click Refresh for AI Brief')}**")
with col_h2:
    with st.popover("ℹ️ Metric & BI Guide"):
        st.markdown("""
        * **BI Stance:** Automated judgement combining **P/E & P/B multiples**, **200-DMA trend**, **1M/3M momentum**, and **1Y Sharpe ratio**.
        * **vs 200-DMA:** `%` above/below 200-day average. `< 0%` with positive `1M` flags early reversal; `> +16%` flags overextended risk.
        * **Sharpe (1Y):** Risk-adjusted return above India's 6.8% risk-free rate.
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

# --- AI STRATEGIST DESK ---
if ai:
    st.markdown("### AI Strategist Desk")
    c1, c2 = st.columns(2)
    with c1:
        opp_md = "<br>".join(f"• {x}" for x in ai.get("opportunities", []))
        st.markdown(f'<div class="ai-box"><strong>🎯 Valuation & Momentum Opportunities</strong><br><br>{opp_md}</div>', unsafe_allow_html=True)
    with c2:
        risk_md = "<br>".join(f"• {x}" for x in ai.get("risk_flags", []))
        st.markdown(f'<div class="ai-box"><strong>⚠️ Risk & Overextension Flags</strong><br><br>{risk_md}</div>', unsafe_allow_html=True)
    st.info(f"**🏦 Debt Duration & Macro Call:** {ai.get('debt_and_macro', 'N/A')}")


# --- HEATMAP RENDERER ---
def render_heatmap(items):
    if not items:
        st.info("No data available yet. Click **🔄 Refresh Market & AI Now** in the sidebar.")
        return

    rows = []
    for x in items:
        rows.append({
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
            "P/E": x.get("pe"),
            "P/B": x.get("pb"),
            "BI Stance": x.get("bi_stance", x.get("signal", "Neutral")),
        })
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

    styled = (
        df.style.map(color_cells, subset=ret_cols)
        .format(
            {c: "{:+.2f}%" for c in ret_cols} | {"Vol %": "{:.1f}%", "Sharpe": "{:.2f}", "P/E": "{:.1f}", "P/B": "{:.1f}"},
            na_rep="—",
        )
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


# --- MAIN TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Multi-Horizon Heatmaps",
    "🧭 Sector Rotation Radar",
    "📰 Top 10 Verified News",
    "🌍 Macro, FX & Commodities",
])

with tab1:
    st.markdown("#### Indian Broad Equity & MF Category Benchmarks")
    render_heatmap(markets.get("indian_equity", []))
    st.markdown("#### Indian Sectoral Benchmarks")
    render_heatmap(markets.get("indian_sectors", []))
    st.markdown("#### Global Markets (Indian International FoF Exposure)")
    render_heatmap(markets.get("global_indices", []))

with tab2:
    st.markdown("#### Sector Valuation-Proxy vs. Momentum Quadrant")
    sectors = markets.get("indian_sectors", [])
    if sectors:
        sdf = pd.DataFrame(sectors).dropna(subset=["dist_200dma", "3M"])
        if not sdf.empty:
            stance_col = "bi_stance" if "bi_stance" in sdf.columns else "signal"
            fig = px.scatter(
                sdf,
                x="dist_200dma",
                y="3M",
                text="name",
                color=stance_col,
                size=sdf["volatility_1y"].fillna(15),
                labels={"dist_200dma": "Distance from 200-DMA (%)", "3M": "3-Month Return (%)"},
                template="plotly_dark" if not print_mode else "plotly_white",
                height=500,
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#64748B")
            fig.add_hline(y=0, line_dash="dash", line_color="#64748B")
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough sector data to plot yet. Click Refresh.")
    else:
        st.info("No sector data found. Click **🔄 Refresh Market & AI Now**.")

with tab3:
    st.markdown("#### Top 10 Verified Financial News (40% India / 60% Global)")
    filter_reg = st.radio("Filter Region", ["ALL", "INDIA", "GLOBAL"], horizontal=True)
    news_list = snapshot.get("verified_news", [])
    if not news_list:
        st.info("No AI-verified news yet. Ensure `GEMINI_API_KEY` is in Streamlit Secrets and click **🔄 Refresh Market & AI Now**.")
    for n in news_list:
        if filter_reg != "ALL" and n.get("region", "").upper() != filter_reg:
            continue
        link_color = "#F8FAFC" if not print_mode else "#0F172A"
        st.markdown(
            f"""
            <div class="news-card">
              <span class="badge">{n.get('region', '')}</span>
              <span class="badge">{n.get('tag', '')}</span>
              <a href="{n.get('link', '#')}" target="_blank" style="color:{link_color};font-weight:700;text-decoration:none;">
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
    render_heatmap(markets.get("macro_commodities_fx", []))
