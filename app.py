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
    .block-container { padding-top: 2.2rem; max-width: 1520px; }

    /* Ensure expander text wraps cleanly without horizontal clipping */
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
        color: #E2C06D; margin-right: 6px;
    }
    h3, h4 { color: #E2C06D !important; font-weight: 600 !important; letter-spacing: 0.3px; }
    button[data-baseweb="tab"] {
        color: #94A3B8 !important; font-weight: 600 !important; font-size: 14px !important; padding: 10px 14px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #F3D58D !important; border-bottom-color: #D4AF37 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SNAPSHOT_PATH = "data/market_snapshot.json"
snapshot = None
if os.path.exists(SNAPSHOT_PATH):
    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

with st.sidebar:
    st.markdown("### ⚡ AURA BI AGENT")
    st.caption("Autonomous Market & Valuation Intelligence")
    st.divider()

    if st.button("🔄 Refresh Live Data & AI", use_container_width=True, type="primary"):
        with st.spinner("Pulling live prices, YoY history, Debt proxies & News Headlines..."):
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
            label="📄 Export Printable Brief",
            data=printable_html,
            file_name="AURA_BI_Daily_Brief.html",
            mime="text/html",
            use_container_width=True,
        )
        st.caption("Open downloaded file in browser and press Ctrl+P to save as PDF.")

    st.divider()
    st.caption("Auto-Schedule: 8:30 AM and 4:30 PM IST, Mon–Fri")

if not snapshot:
    st.warning("No snapshot found yet. Click **🔄 Refresh Live Data & AI** in the sidebar.")
    st.stop()

ai = snapshot.get("ai_strategist", {})
macro = snapshot.get("macro_manual", {})
markets = snapshot.get("markets", {})
debt_liquid = snapshot.get("debt_liquid", [])


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

st.markdown("<br>", unsafe_allow_html=True)

# --- TOP KPI PULSE STRIP ---
def find_item(cat, keyword):
    for x in markets.get(cat, []):
        if keyword.lower() in x["name"].lower():
            return x
    return None

kpis = [
    ("Nifty 50", find_item("indian_equity", "Nifty 50")),
    ("BSE SENSEX", find_item("indian_equity", "SENSEX")),
    ("S&P 500", find_item("global_indices", "S&P 500")),
    ("Gold INR / 10g", find_item("macro_commodities_fx", "Gold INR")),
    ("USD / INR", find_item("macro_commodities_fx", "USD / INR")),
    ("India VIX", find_item("volatility_indices", "India VIX")),
]

kpi_cols = st.columns(7)
for idx, (label, item) in enumerate(kpis):
    with kpi_cols[idx]:
        if item:
            d1 = item.get("1D") or 0
            cls = "kpi-pos" if d1 >= 0 else "kpi-neg"
            arrow = "▲" if d1 >= 0 else "▼"
            sign = "+" if d1 > 0 else ""
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-val">{format_price(item)}</div>
                  <div class="{cls}">{arrow} {sign}{d1:.2f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with kpi_cols[6]:
    repo = macro.get("rbi_repo_rate", 6.50)
    gsec = macro.get("india_10y_gsec_approx", 6.85)
    spread = round(gsec - repo, 2)
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">RBI Repo / 10Y</div>
          <div class="kpi-val">{repo:.2f}%/{gsec:.2f}%</div>
          <div class="kpi-pos">▲ +{spread:.2f}% Sprd</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# --- AURA AI GUIDE ---
with st.expander("📘 AURA AI guide — Jargon Glossary, CAGR Methodology and BI Stance"):
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(
            """
            * **CAGR (3Y and 5Y):** Compound Annual Growth Rate = `((Ending Price / Beginning Price) ^ (1 / Years)) - 1`. Converts multi-year cumulative price change into an annualized return rate.
            * **1D, 1W, 1M, 3M and 1Y:** Point-to-point percentage return across 1, 5, 21, 63, and 252 trading sessions.
            * **Vol %:** Annualized return volatility = `daily_std * √252`. Measures price fluctuation intensity.
            * **Sharpe:** `(1Y Return - 6.8% Risk-Free Rate) / 1Y Volatility`. Gauges return per unit of volatility on return assets (omitted on VIX indices).
            """
        )
    with g2:
        st.markdown(
            """
            * **vs 52W High:** Percentage gap below the 52-week peak (`-15%` means 15% below the 1-year high).
            * **vs 200-DMA:** Percentage distance above or below the 200-day moving average trend line.
            * **P/E:** Trailing Price-to-Earnings multiple (sourced directly or via liquid ETF proxies for equity benchmarks).
            * **BI Stance:** Multi-factor judgement combining valuation multiples, 200-DMA and 52W High positioning, 1M/3M/1Y momentum alignment, and Sharpe/volatility; volatility indices use regime and spike logic instead.
            """
        )

# --- AI AGENT BRIEF ---
if ai:
    c1, c2 = st.columns(2)
    with c1:
        opp_md = "<br>".join(f"• {x}" for x in ai.get("opportunities", []))
        st.markdown(f'<div class="ai-box"><strong>🎯 BI Opportunities</strong><br><br>{opp_md}</div>', unsafe_allow_html=True)
    with c2:
        risk_md = "<br>".join(f"• {x}" for x in ai.get("risk_flags", []))
        st.markdown(f'<div class="ai-box"><strong>⚠️ Risk and Overextension Alerts</strong><br><br>{risk_md}</div>', unsafe_allow_html=True)
    st.info(f"**🏦 Debt Duration and Macro Call:** {ai.get('debt_and_macro', 'N/A')}")


# --- HEATMAP RENDERER ---
def render_heatmap(items, show_valuation=True, show_risk_metrics=True):
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
        }
        if show_risk_metrics:
            row["Sharpe"] = x.get("sharpe_1y")
        row["vs 52W High"] = x.get("from_52w_high")
        row["vs 200-DMA"] = x.get("dist_200dma")
        if show_valuation:
            row["P/E"] = x.get("pe")
        row["BI Stance"] = x.get("bi_stance", "Neutral")
        rows.append(row)

    df = pd.DataFrame(rows)
    ret_cols = ["1D", "1W", "1M", "3M", "1Y", "3Y CAGR", "5Y CAGR", "vs 52W High", "vs 200-DMA"]

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

    fmt_map = {c: "{:+.2f}%" for c in ret_cols} | {"Vol %": "{:.1f}%"}
    if show_risk_metrics:
        fmt_map["Sharpe"] = "{:.2f}"
    if show_valuation:
        fmt_map["P/E"] = "{:.1f}"

    styled = df.style.map(color_cells, subset=ret_cols).format(fmt_map, na_rep="—")
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "BI Stance": st.column_config.TextColumn("BI Stance", width="large"),
        },
    )


# --- MAIN TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Equity, MF and Volatility",
    "🧭 Sector and Return Charts",
    "📰 News Headlines",
    "🌍 Global, FX and Commodities",
    "🏦 Debt & Liquid MF",
])

with tab1:
    st.markdown("#### Indian Broad Equity, BSE SENSEX and MF Benchmarks")
    render_heatmap(markets.get("indian_equity", []), show_valuation=True, show_risk_metrics=True)

    st.markdown("#### Volatility and Fear Indices")
    render_heatmap(markets.get("volatility_indices", []), show_valuation=False, show_risk_metrics=False)

    st.markdown("#### Indian Sectoral Benchmarks")
    render_heatmap(markets.get("indian_sectors", []), show_valuation=True, show_risk_metrics=True)

with tab2:
    # 1. Year-on-Year Returns since 1995
    st.markdown("#### Year-on-Year Calendar Returns Since 1995")
    yoy_candidates = [x for x in (markets.get("indian_equity", []) + markets.get("global_indices", [])) if x.get("yoy_returns")]
    if yoy_candidates:
        selected_yoy_name = st.selectbox(
            "Select Broad Market Index for YoY Return History",
            options=[x["name"] for x in yoy_candidates],
            index=0,
        )
        chosen = next(x for x in yoy_candidates if x["name"] == selected_yoy_name)
        yoy_dict = chosen.get("yoy_returns", {})
        if yoy_dict:
            yoy_df = pd.DataFrame([{"Year": k, "YoY Return %": v} for k, v in yoy_dict.items()])
            yoy_fig = px.bar(
                yoy_df,
                x="Year",
                y="YoY Return %",
                color="YoY Return %",
                color_continuous_scale=["#EF4444", "#475569", "#10B981"],
                labels={"YoY Return %": f"{selected_yoy_name} YoY Return (%)"},
                template="plotly_dark",
                height=380,
            )
            yoy_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,25,40,0.5)")
            st.plotly_chart(yoy_fig, use_container_width=True)
            st.dataframe(yoy_df.T, use_container_width=True)
    else:
        st.info("Click **🔄 Refresh Live Data & AI** once to pull historical YoY series since 1995.")

    st.divider()

    # 2. Sectoral Performance Breakup: Leader vs. Laggard Matrix
    st.markdown("#### Sectoral Performance Breakup — Leader vs. Laggard Matrix")
    sectors = markets.get("indian_sectors", [])
    if sectors:
        sdf = pd.DataFrame(sectors)
        nifty_item = find_item("indian_equity", "Nifty 50")
        nifty_1m = nifty_item.get("1M") if nifty_item and nifty_item.get("1M") is not None else 0.0
        nifty_3m = nifty_item.get("3M") if nifty_item and nifty_item.get("3M") is not None else 0.0
        nifty_1y = nifty_item.get("1Y") if nifty_item and nifty_item.get("1Y") is not None else 0.0

        matrix_rows = []
        for x in sectors:
            r1m = x.get("1M")
            r3m = x.get("3M")
            r1y = x.get("1Y")
            rel_3m = round(r3m - nifty_3m, 2) if r3m is not None else None
            rel_1y = round(r1y - nifty_1y, 2) if r1y is not None else None

            if rel_3m is not None and rel_3m >= 3.0 and (r1m is not None and r1m >= 0):
                bucket = "Leader"
            elif rel_3m is not None and rel_3m <= -3.0:
                bucket = "Laggard"
            else:
                bucket = "In-Line / Transition"

            matrix_rows.append({
                "Sector": x["name"],
                "1M": r1m,
                "3M": r3m,
                "1Y": r1y,
                "vs Nifty 3M": rel_3m,
                "vs Nifty 1Y": rel_1y,
                "Vol %": x.get("volatility_1y"),
                "P/E": x.get("pe"),
                "Leader / Laggard": bucket,
                "BI Stance": x.get("bi_stance", "Neutral"),
            })

        mdf = pd.DataFrame(matrix_rows).sort_values("vs Nifty 3M", ascending=False, na_position="last")
        st.dataframe(
            mdf.style.format({
                "1M": "{:+.2f}%",
                "3M": "{:+.2f}%",
                "1Y": "{:+.2f}%",
                "vs Nifty 3M": "{:+.2f}%",
                "vs Nifty 1Y": "{:+.2f}%",
                "Vol %": "{:.1f}%",
                "P/E": "{:.1f}",
            }, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )

        # Sector Quadrant Chart
        qdf = sdf.dropna(subset=["dist_200dma", "3M"])
        if not qdf.empty:
            fig = px.scatter(
                qdf,
                x="dist_200dma",
                y="3M",
                text="name",
                color="bi_stance",
                size=qdf["volatility_1y"].fillna(15),
                labels={"dist_200dma": "Distance from 200-DMA (%)", "3M": "3-Month Return (%)"},
                template="plotly_dark",
                height=420,
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,25,40,0.5)")
            fig.add_vline(x=0, line_dash="dash", line_color="#64748B")
            fig.add_hline(y=0, line_dash="dash", line_color="#64748B")
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### News Headlines")
    filter_reg = st.radio("Filter Region", ["ALL", "INDIA", "GLOBAL"], horizontal=True)
    news_list = snapshot.get("verified_news", [])
    if not news_list:
        st.info("Click **🔄 Refresh Live Data & AI** in the sidebar to load today's News Headlines.")
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
    st.markdown("#### Global Markets")
    render_heatmap(markets.get("global_indices", []), show_valuation=True, show_risk_metrics=True)

    st.markdown("#### Gold, Currencies, Commodities and Yields")
    render_heatmap(markets.get("macro_commodities_fx", []), show_valuation=False, show_risk_metrics=True)

with tab5:
    st.markdown("#### Debt & Liquid Mutual Fund Comparison (Duration, Credit & Return Profile)")
    repo = macro.get("rbi_repo_rate", 6.50)
    gsec = macro.get("india_10y_gsec_approx", 6.85)
    spread = round(gsec - repo, 2)

    m1, m2, m3 = st.columns(3)
    m1.metric("RBI Repo Rate (Policy Anchor)", f"{repo:.2f}%")
    m2.metric("India 10Y G-Sec (Approx)", f"{gsec:.2f}%")
    m3.metric("10Y vs. Repo Spread", f"{spread:+.2f}%")

    if debt_liquid:
        ddf = pd.DataFrame(debt_liquid)
        display_cols = [
            "name", "bucket", "duration_profile", "credit_profile",
            "1W", "1M", "3M", "1Y", "3Y_CAGR", "volatility_1y", "sharpe_1y", "bi_stance"
        ]
        avail = [c for c in display_cols if c in ddf.columns]
        view_df = ddf[avail].rename(columns={
            "name": "Debt / Liquid Proxy",
            "bucket": "Category",
            "duration_profile": "Duration Profile",
            "credit_profile": "Credit / Sovereign",
            "3Y_CAGR": "3Y CAGR",
            "volatility_1y": "Vol %",
            "sharpe_1y": "Sharpe",
            "bi_stance": "BI Stance",
        })
        st.dataframe(
            view_df.style.format({
                "1W": "{:+.2f}%",
                "1M": "{:+.2f}%",
                "3M": "{:+.2f}%",
                "1Y": "{:+.2f}%",
                "3Y CAGR": "{:+.2f}%",
                "Vol %": "{:.2f}%",
                "Sharpe": "{:.2f}",
            }, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "Apple-to-Apple Debt Note: Liquid and money-market funds prioritize capital preservation and accrual with minimal duration risk; "
            "gilt/longer-duration funds carry higher rate/mark-to-market sensitivity when bond yields move."
        )
    else:
        st.info("Click **🔄 Refresh Live Data & AI** once to load Debt & Liquid proxy metrics.")
