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
    .block-container { padding-top: 1.4rem; padding-bottom: 1.5rem; max-width: 1600px; }

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
    .kpi-val { font-size: 17px; font-weight: 700; color: #F8FAFC; font-family: 'JetBrains Mono', monospace; margin-top: 3px; }
    .kpi-pos { font-size: 11px; color: #34D399; font-weight: 700; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }
    .kpi-neg { font-size: 11px; color: #F87171; font-weight: 700; margin-top: 2px; font-family: 'JetBrains Mono', monospace; }

    .ai-box {
        background: rgba(17, 25, 40, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 3px solid #D4AF37;
        padding: 12px 16px; border-radius: 8px; margin-bottom: 8px;
        color: #E2E8F0; font-size: 13px; line-height: 1.5;
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
    .tri-up { color: #34D399; font-weight: 700; }
    .tri-dn { color: #F87171; font-weight: 700; }
    h3, h4 { color: #E2C06D !important; font-weight: 600 !important; letter-spacing: 0.25px; margin-top: 0.6rem !important; margin-bottom: 0.4rem !important; }
    button[data-baseweb="tab"] {
        color: #94A3B8 !important; font-weight: 600 !important; font-size: 13.5px !important; padding: 8px 12px !important;
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
        with st.spinner("Pulling live prices, RSI, YoY history, AMFI Debt NAVs & News..."):
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
amfi_debt_schemes = snapshot.get("amfi_debt_schemes", [])


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


def fmt_tri_pct(val):
    if val is None or pd.isna(val):
        return "—"
    tri = "▲" if val >= 0 else "▼"
    sign = "+" if val > 0 else ""
    return f"{tri} {sign}{val:.2f}%"


def format_stance_cell(stance_raw):
    text = stance_raw or "Hold | Balanced signals"
    if " | " in text:
        head, reason = text.split(" | ", 1)
    else:
        head, reason = text, ""

    head_lower = head.lower()
    if "strong buy" in head_lower or "accumulate" in head_lower or "low-vol" in head_lower:
        tag_bg, tag_fg = "rgba(16, 185, 129, 0.18)", "#34D399"
    elif "trim" in head_lower or "avoid" in head_lower or "fear spike" in head_lower or "elevated stress" in head_lower:
        tag_bg, tag_fg = "rgba(239, 68, 68, 0.18)", "#F87171"
    else:
        tag_bg, tag_fg = "rgba(212, 175, 55, 0.18)", "#F3D58D"

    reason_html = (
        f"<div style='font-size:11px;color:#CBD5E1;line-height:1.3;margin-top:3px;white-space:normal;'>{reason}</div>"
        if reason else ""
    )
    return (
        f"<div style='min-width:240px;max-width:300px;white-space:normal;'>"
        f"<span style='display:inline-block;padding:2px 7px;border-radius:4px;background:{tag_bg};color:{tag_fg};font-size:11px;font-weight:700;'>{head}</span>"
        f"{reason_html}</div>"
    )


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
    sprd_cls = "kpi-pos" if spread >= 0 else "kpi-neg"
    sprd_tri = "▲" if spread >= 0 else "▼"
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">RBI Repo / 10Y</div>
          <div class="kpi-val">{repo:.2f}%/{gsec:.2f}%</div>
          <div class="{sprd_cls}">{sprd_tri} {spread:+.2f}% Sprd</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- COMPACT AURA AI GUIDE ---
with st.expander("📘 AURA AI guide — Glossary, CAGR Formula & BI stance | reasoning"):
    g1, g2 = st.columns(2)
    with g1:
        st.markdown(
            """
            * **CAGR (3Y & 5Y):** `((Ending / Beginning) ^ (1 / Years)) - 1` annualized return rate.
            * **1D, 1W, 1M, 3M, 1Y:** Return over 1, 5, 21, 63, and 252 trading sessions (`▲` gain / `▼` loss).
            * **Vol % & Sharpe:** Annualized volatility (`std * √252`) and `(1Y Return - 6.8%) / Vol %` (omitted on VIX).
            """
        )
    with g2:
        st.markdown(
            """
            * **RSI (14):** 14-day momentum oscillator (`>70–75` stretched, `<30–35` oversold; omitted on VIX).
            * **vs 52W High & vs 200-DMA:** Distance from 52-week peak and 200-day moving average.
            * **BI stance | reasoning:** Stance tag paired with its primary valuation, trend, RSI/momentum, or volatility reason.
            """
        )

# --- COMPACT AI BRIEF ---
if ai:
    c1, c2 = st.columns(2)
    with c1:
        opp_md = "<br>".join(f"• {x}" for x in ai.get("opportunities", []))
        st.markdown(f'<div class="ai-box"><strong>🎯 BI Opportunities</strong><br>{opp_md}</div>', unsafe_allow_html=True)
    with c2:
        risk_md = "<br>".join(f"• {x}" for x in ai.get("risk_flags", []))
        st.markdown(f'<div class="ai-box"><strong>⚠️ Risk & Overextension Alerts</strong><br>{risk_md}</div>', unsafe_allow_html=True)
    st.info(f"**🏦 Debt & Macro Call:** {ai.get('debt_and_macro', 'N/A')}")


# --- COMPACT HTML + TRIANGLE TABLE RENDERER ---
def render_heatmap(items, show_valuation=True, show_risk_metrics=True):
    if not items:
        st.info("No data available. Click **🔄 Refresh Live Data & AI** in the sidebar.")
        return

    headers = ["Benchmark", "Price", "1D", "1W", "1M", "3M", "1Y", "3Y CAGR", "5Y CAGR", "Vol %"]
    if show_risk_metrics:
        headers.extend(["Sharpe", "RSI"])
    headers.extend(["vs 52W High", "vs 200-DMA"])
    if show_valuation:
        headers.append("P/E")
    headers.append("BI stance | reasoning")

    def cell_pct_html(v):
        if v is None or pd.isna(v):
            return "<span style='color:#64748B;'>—</span>"
        sign = "+" if v > 0 else ""
        if v >= 0:
            bg = "rgba(16, 185, 129, 0.22)" if v >= 10 else "rgba(16, 185, 129, 0.10)"
            return f"<span style='display:inline-block;padding:1px 5px;border-radius:4px;background:{bg};color:#34D399;font-weight:700;font-size:12px;'>▲ {sign}{v:.2f}%</span>"
        bg = "rgba(239, 68, 68, 0.22)" if v <= -10 else "rgba(239, 68, 68, 0.10)"
        return f"<span style='display:inline-block;padding:1px 5px;border-radius:4px;background:{bg};color:#F87171;font-weight:700;font-size:12px;'>▼ {v:.2f}%</span>"

    def plain_num(v, fmt):
        if v is None or pd.isna(v):
            return "<span style='color:#64748B;'>—</span>"
        return fmt.format(v)

    body_rows = []
    for x in items:
        stance_val = x.get("bi_stance", "Hold | Balanced signals")
        if " | " not in stance_val and x.get("bi_driver"):
            stance_val = f"{stance_val} | {x.get('bi_driver')}"

        tds = [
            f"<td style='font-weight:600;color:#F8FAFC;white-space:nowrap;'>{x['name']}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;font-weight:600;color:#F8FAFC;white-space:nowrap;'>{format_price(x)}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('1D'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('1W'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('1M'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('3M'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('1Y'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('3Y_CAGR'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('5Y_CAGR'))}</td>",
            f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{plain_num(x.get('volatility_1y'), '{:.1f}%')}</td>",
        ]
        if show_risk_metrics:
            tds.append(f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{plain_num(x.get('sharpe_1y'), '{:.2f}')}</td>")
            tds.append(f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{plain_num(x.get('rsi_14'), '{:.1f}')}</td>")
        tds.append(f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('from_52w_high'))}</td>")
        tds.append(f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{cell_pct_html(x.get('dist_200dma'))}</td>")
        if show_valuation:
            tds.append(f"<td style='font-family:\"JetBrains Mono\",monospace;white-space:nowrap;'>{plain_num(x.get('pe'), '{:.1f}')}</td>")
        tds.append(f"<td style='padding:7px 10px;'>{format_stance_cell(stance_val)}</td>")
        body_rows.append("<tr style='border-bottom:1px solid rgba(255,255,255,0.05);'>" + "".join(tds) + "</tr>")

    th_html = "".join(
        f"<th style='text-align:left;padding:8px 10px;color:#94A3B8;font-size:10.5px;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid rgba(255,255,255,0.12);white-space:nowrap;'>{h}</th>"
        for h in headers
    )
    table_html = (
        "<div style='overflow-x:auto;border:1px solid rgba(255,255,255,0.08);border-radius:10px;background:rgba(15,23,42,0.72);margin-bottom:10px;'>"
        "<table style='width:100%;border-collapse:collapse;font-size:12.5px;'>"
        f"<thead><tr>{th_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


# --- MAIN TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Equity, MF & Volatility",
    "🧭 Sector & Return Charts",
    "📰 News Headlines",
    "🌍 Global, FX & Commodities",
    "🏦 Indian Debt & AMFI MF",
])

with tab1:
    view_slice = st.radio(
        "Quick Focus",
        ["All", "Broad Equity & MF", "Volatility", "Sectors"],
        horizontal=True,
    )
    if view_slice in ["All", "Broad Equity & MF"]:
        st.markdown("#### Indian Broad Equity, BSE SENSEX & MF Benchmarks")
        render_heatmap(markets.get("indian_equity", []), show_valuation=True, show_risk_metrics=True)

    if view_slice in ["All", "Volatility"]:
        st.markdown("#### Volatility & Fear Indices")
        render_heatmap(markets.get("volatility_indices", []), show_valuation=False, show_risk_metrics=False)

    if view_slice in ["All", "Sectors"]:
        st.markdown("#### Indian Sectoral Benchmarks")
        render_heatmap(markets.get("indian_sectors", []), show_valuation=True, show_risk_metrics=True)

with tab2:
    chart_mode = st.radio(
        "Chart View",
        ["YoY Returns (Since 1995)", "Sector Leader vs. Laggard & Quadrant"],
        horizontal=True,
    )

    if chart_mode == "YoY Returns (Since 1995)":
        st.markdown("#### Year-on-Year Calendar Returns Since 1995")
        yoy_candidates = [x for x in (markets.get("indian_equity", []) + markets.get("global_indices", [])) if x.get("yoy_returns")]
        if yoy_candidates:
            selected_yoy_name = st.selectbox(
                "Select Broad Market Index",
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
                    height=340,
                )
                yoy_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,25,40,0.5)")
                st.plotly_chart(yoy_fig, use_container_width=True)
                st.dataframe(yoy_df.T, use_container_width=True)
        else:
            st.info("Click **🔄 Refresh Live Data & AI** once to pull historical YoY series since 1995.")

    else:
        st.markdown("#### Sectoral Performance Breakup — Leader vs. Laggard Matrix")
        sectors = markets.get("indian_sectors", [])
        if sectors:
            sdf = pd.DataFrame(sectors)
            nifty_item = find_item("indian_equity", "Nifty 50")
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
                    bucket = "▲ Leader"
                elif rel_3m is not None and rel_3m <= -3.0:
                    bucket = "▼ Laggard"
                else:
                    bucket = "In-Line"

                stance_val = x.get("bi_stance", "Hold | Balanced signals")
                if " | " not in stance_val and x.get("bi_driver"):
                    stance_val = f"{stance_val} | {x.get('bi_driver')}"

                matrix_rows.append({
                    "Sector": x["name"],
                    "1M": fmt_tri_pct(r1m),
                    "3M": fmt_tri_pct(r3m),
                    "1Y": fmt_tri_pct(r1y),
                    "vs Nifty 3M": fmt_tri_pct(rel_3m),
                    "vs Nifty 1Y": fmt_tri_pct(rel_1y),
                    "RSI": f"{x['rsi_14']:.1f}" if x.get("rsi_14") is not None else "—",
                    "Vol %": f"{x['volatility_1y']:.1f}%" if x.get("volatility_1y") is not None else "—",
                    "P/E": f"{x['pe']:.1f}" if x.get("pe") is not None else "—",
                    "Group": bucket,
                    "BI stance | reasoning": stance_val,
                    "_sort_3m": rel_3m if rel_3m is not None else -9999.0,
                })

            mdf = pd.DataFrame(matrix_rows).sort_values("_sort_3m", ascending=False).drop(columns=["_sort_3m"])
            st.dataframe(mdf, use_container_width=True, hide_index=True)

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
                    height=380,
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
              <a href="{n.get('link', '#')}" target="_blank" style="color:#F8FAFC;font-weight:600;text-decoration:none;font-size:14.5px;">
                {n.get('title', '')}
              </a>
              <div style="font-size:12.5px;color:#94A3B8;margin-top:4px;">
                {n.get('impact', '')} <em>— {n.get('source', '')}</em>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab4:
    st.markdown("#### Global Markets")
    render_heatmap(markets.get("global_indices", []), show_valuation=True, show_risk_metrics=True)

    st.markdown("#### Gold, Currencies, Commodities & Yields")
    render_heatmap(markets.get("macro_commodities_fx", []), show_valuation=False, show_risk_metrics=True)

with tab5:
    st.markdown("#### Indian Debt Yields & Sovereign Curve")
    repo = float(macro.get("rbi_repo_rate", 6.50))
    tbill_3m = float(macro.get("india_3m_tbill_approx", 6.55))
    gsec_1y = float(macro.get("india_1y_gsec_approx", 6.65))
    gsec_5y = float(macro.get("india_5y_gsec_approx", 6.75))
    gsec_10y = float(macro.get("india_10y_gsec_approx", 6.85))
    spread = round(gsec_10y - repo, 2)
    sprd_tri = "▲" if spread >= 0 else "▼"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("RBI Repo Rate", f"{repo:.2f}%")
    m2.metric("India 1Y G-Sec", f"{gsec_1y:.2f}%")
    m3.metric("India 10Y G-Sec", f"{gsec_10y:.2f}%")
    m4.metric("10Y vs. Repo Spread", f"{sprd_tri} {spread:+.2f}%")

    c_left, c_right = st.columns([1, 1.3])
    with c_left:
        curve_df = pd.DataFrame([
            {"Tenor": "RBI Repo", "Yield %": repo},
            {"Tenor": "3M T-Bill", "Yield %": tbill_3m},
            {"Tenor": "1Y G-Sec", "Yield %": gsec_1y},
            {"Tenor": "5Y G-Sec", "Yield %": gsec_5y},
            {"Tenor": "10Y G-Sec", "Yield %": gsec_10y},
        ])
        curve_fig = px.line(
            curve_df,
            x="Tenor",
            y="Yield %",
            markers=True,
            labels={"Yield %": "Yield (%)"},
            template="plotly_dark",
            height=280,
        )
        curve_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(17,25,40,0.5)")
        st.plotly_chart(curve_fig, use_container_width=True)

    with c_right:
        st.markdown("##### Debt Category Duration & Role")
        domestic_matrix = pd.DataFrame([
            {"Category": "Liquid / Overnight", "Duration": "<91d", "Rate Risk": "Minimal", "Role": "Liquidity & cash"},
            {"Category": "Money Market / Low Dur.", "Duration": "6m–1.5y", "Rate Risk": "Low", "Role": "Short accrual"},
            {"Category": "Short Duration", "Duration": "1–3y", "Rate Risk": "Low–Mod", "Role": "Balanced accrual"},
            {"Category": "Corporate / Banking & PSU", "Duration": "2–5y", "Rate Risk": "Moderate", "Role": "AAA spread pickup"},
            {"Category": "Gilt / Long Duration", "Duration": "7–10y+", "Rate Risk": "High", "Role": "Yield-move / MTM"},
        ])
        st.dataframe(domestic_matrix, use_container_width=True, hide_index=True)

    st.markdown("#### Live AMFI Indian Debt & Liquid Mutual Fund NAVs")
    if amfi_debt_schemes:
        adf = pd.DataFrame(amfi_debt_schemes).rename(columns={
            "scheme_name": "AMFI Scheme (Growth)",
            "bucket": "Category",
            "duration": "Duration",
            "credit": "Credit",
            "nav": "NAV (₹)",
            "nav_date": "NAV Date",
        })
        st.dataframe(
            adf.style.format({"NAV (₹)": "₹{:.4f}"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Click **🔄 Refresh Live Data & AI** once to fetch live AMFI Indian debt/liquid NAVs.")
