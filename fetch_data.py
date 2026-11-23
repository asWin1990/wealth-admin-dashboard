import os
import re
import json
import yaml
import feedparser
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

VALUATION_PROXIES = {
    "^NSEI": ["NIFTYBEES.NS"],
    "^BSESN": ["SENSEXADD.NS", "NIFTYBEES.NS"],
    "^NSMIDCP": ["JUNIORBEES.NS"],
    "^NSEMDCP150": ["MID150BEES.NS"],
    "^CRSLDX": ["MONIFTY500.NS"],
    "^NSEBANK": ["BANKBEES.NS"],
    "^CNXPSUBANK": ["PSUBNKBEES.NS"],
    "^CNXIT": ["ITBEES.NS"],
    "^CNXPHARMA": ["PHARMABEES.NS", "HEALTHY.NS", "AXISHCETF.NS"],
    "^CNXINFRA": ["INFRABEES.NS"],
    "^CNXAUTO": ["AUTOBEES.NS"],
    "^CNXFMCG": ["FMCGIETF.NS", "CONSUMBEES.NS", "AXISCONSUM.NS"],
    "^CNXMETAL": ["METALIETF.NS"],
    "^CNXENERGY": ["OILIETF.NS"],
    "^GSPC": ["SPY"],
    "^DJI": ["DIA"],
    "^NDX": ["QQQ"],
    "^FTSE": ["EWU"],
    "^FCHI": ["EWQ"],
    "^N225": ["EWJ"],
    "^GDAXI": ["EWG"],
    "^HSI": ["EWH"],
}

DEBT_AND_LIQUID_PROXIES = {
    "Liquid MF Proxy (LiquidBeES)": {"ticker": "LIQUIDBEES.NS", "bucket": "Liquid", "duration_profile": "Ultra-Short (<91d)", "credit_profile": "Sovereign / AAA"},
    "Money Market / T-Bill Proxy (US 3M)": {"ticker": "^IRX", "bucket": "Money Market", "duration_profile": "Short (~3M)", "credit_profile": "Sovereign"},
    "Short / Medium Gilt & Bond Proxy (LtGiltBeES)": {"ticker": "LTGILTBEES.NS", "bucket": "Gilt / Sovereign", "duration_profile": "Medium-Long Duration", "credit_profile": "Sovereign"},
    "US Treasury 7-10Y Bond Proxy (IEF)": {"ticker": "IEF", "bucket": "Global Sovereign Debt", "duration_profile": "Intermediate (~7.5y)", "credit_profile": "US Sovereign"},
    "US Investment Grade Corp Proxy (LQD)": {"ticker": "LQD", "bucket": "Global Corporate Debt", "duration_profile": "Medium-Long (~8y)", "credit_profile": "Investment Grade"},
}


def clean_label(text):
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calc_cagr(start_price, end_price, years):
    if pd.isna(start_price) or pd.isna(end_price) or start_price <= 0:
        return None
    return round(((end_price / start_price) ** (1 / years) - 1) * 100, 2)


def calc_pct_return(series, trading_days):
    if len(series) <= trading_days:
        return None
    start = series.iloc[-1 - trading_days]
    end = series.iloc[-1]
    if pd.isna(start) or start <= 0:
        return None
    return round(((end / start) - 1) * 100, 2)


def calc_yoy_history(close, start_year=1995):
    """Computes calendar year-on-year returns from start_year (or earliest available year) through current year."""
    if close is None or close.empty:
        return {}
    s = close.copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s = s.sort_index()

    years = sorted(s.index.year.unique())
    years = [y for y in years if y >= start_year]
    yoy = {}

    for idx, yr in enumerate(years):
        yr_slice = s[s.index.year == yr]
        if yr_slice.empty:
            continue
        end_val = float(yr_slice.iloc[-1])

        # Base is prior year's last close if available; otherwise first close of that year
        prev_slice = s[s.index.year == (yr - 1)]
        if not prev_slice.empty:
            start_val = float(prev_slice.iloc[-1])
        elif idx == 0 and len(yr_slice) > 1:
            start_val = float(yr_slice.iloc[0])
        else:
            continue

        if start_val > 0:
            yoy[str(yr)] = round(((end_val / start_val) - 1) * 100, 2)

    return yoy


def get_currency_symbol(name, ticker):
    if "VIX" in name.upper():
        return ""
    if "Yield" in name or "TNX" in ticker or "IRX" in ticker:
        return "%"
    if "INR" in name or ticker.endswith(".NS") or ticker.endswith(".BO"):
        return "₹"
    if "USD" in name or "Crude" in name or ticker in ["GC=F", "SI=F", "BZ=F", "EEM", "IEF", "LQD"]:
        return "$"
    return ""


def fetch_pe_ratio(ticker):
    for sym in [ticker] + VALUATION_PROXIES.get(ticker, []):
        try:
            pe = (yf.Ticker(sym).info or {}).get("trailingPE")
            if pe and float(pe) > 0:
                return round(float(pe), 2)
        except Exception:
            continue
    return None


def compute_vol_stance(price, dist_200dma, r_1d, r_1w):
    if r_1d is not None and r_1d >= 15:
        return "Fear Spike • Volatility Surge"
    if dist_200dma is not None and dist_200dma > 30:
        return "Elevated Stress • Above 200-DMA"
    if price < 14 and (r_1w is None or r_1w <= 2):
        return "Low-Vol • Calm Regime"
    return "Normal Regime • Balanced Vol"


def compute_bi_stance(pe, dist_200dma, from_52w_high, r_1m, r_3m, r_1y, sharpe, vol_1y, is_equity=True):
    score = 0.0
    drivers = []

    if is_equity and pe is not None:
        if pe < 18:
            score += 1.5
            drivers.append("Cheap P/E")
        elif pe <= 24:
            score += 0.75
            drivers.append("Fair P/E")
        elif pe <= 30:
            score -= 0.5
            drivers.append("Rich P/E")
        else:
            score -= 1.5
            drivers.append("Expensive P/E")

    if dist_200dma is not None:
        if -12 <= dist_200dma < 0 and r_1m is not None and r_1m > 0:
            score += 1.5
            drivers.append("Reversing Near 200-DMA")
        elif 0 <= dist_200dma <= 12:
            score += 1.0
            drivers.append("Above 200-DMA")
        elif dist_200dma > 18:
            score -= 1.25
            drivers.append("Extended vs 200-DMA")
        elif dist_200dma < -15:
            score -= 1.0
            drivers.append("Below 200-DMA")

    if from_52w_high is not None and from_52w_high < -20 and (r_1m is None or r_1m <= 0):
        score -= 0.75
        drivers.append("Deep Off High")

    pos_horizons = sum(1 for x in [r_1m, r_3m, r_1y] if x is not None and x > 0)
    neg_horizons = sum(1 for x in [r_1m, r_3m, r_1y] if x is not None and x < 0)
    if pos_horizons == 3:
        score += 1.0
        drivers.append("Broad Uptrend")
    elif neg_horizons == 3:
        score -= 1.0
        drivers.append("Broad Downtrend")

    if sharpe is not None:
        if sharpe >= 1.0:
            score += 0.75
            drivers.append("Strong Sharpe")
        elif sharpe < -0.25:
            score -= 0.75
            drivers.append("Weak Sharpe")

    if vol_1y is not None and vol_1y > 28 and is_equity:
        score -= 0.5
        drivers.append("High Vol")

    if score >= 2.5:
        label = "Strong Buy"
    elif score >= 1.25:
        label = "Accumulate"
    elif score >= -0.75:
        label = "Hold / Neutral"
    elif score >= -2.0:
        label = "Cautious / Trim"
    else:
        label = "Avoid / Weak"

    top_reason = drivers[0] if drivers else "Balanced Signals"
    return f"{label} • {top_reason}"


def analyze_series(name, ticker, close, rf_rate=0.068, pe=None, currency="", mode="equity", include_yoy=False):
    current_price = round(float(close.iloc[-1]), 2)

    r_1d = calc_pct_return(close, 1)
    r_1w = calc_pct_return(close, 5)
    r_1m = calc_pct_return(close, 21)
    r_3m = calc_pct_return(close, 63)
    r_1y = calc_pct_return(close, 252)
    r_3y_cagr = calc_cagr(close.iloc[-756], current_price, 3) if len(close) > 756 else None
    r_5y_cagr = calc_cagr(close.iloc[0], current_price, 5) if len(close) > 1100 else None

    recent_1y = close.tail(252)
    daily_ret = recent_1y.pct_change().dropna()
    ann_vol = round(float(daily_ret.std() * np.sqrt(252) * 100), 2) if len(daily_ret) > 10 else None

    sharpe = None
    if r_1y is not None and ann_vol and ann_vol > 0:
        sharpe = round(((r_1y / 100) - rf_rate) / (ann_vol / 100), 2)

    dma_200 = float(close.tail(200).mean()) if len(close) >= 200 else None
    dist_200dma = round(((current_price / dma_200) - 1) * 100, 2) if dma_200 else None

    high_52w = float(recent_1y.max())
    from_52w_high = round(((current_price / high_52w) - 1) * 100, 2) if high_52w > 0 else None

    if mode == "vol":
        bi_stance = compute_vol_stance(current_price, dist_200dma, r_1d, r_1w)
    else:
        bi_stance = compute_bi_stance(
            pe, dist_200dma, from_52w_high, r_1m, r_3m, r_1y, sharpe, ann_vol, is_equity=(mode == "equity")
        )

    out = {
        "name": name,
        "ticker": ticker,
        "currency": currency,
        "price": current_price,
        "1D": r_1d,
        "1W": r_1w,
        "1M": r_1m,
        "3M": r_3m,
        "1Y": r_1y,
        "3Y_CAGR": r_3y_cagr,
        "5Y_CAGR": r_5y_cagr,
        "volatility_1y": ann_vol,
        "sharpe_1y": sharpe,
        "from_52w_high": from_52w_high,
        "dist_200dma": dist_200dma,
        "pe": pe if mode == "equity" else None,
        "bi_stance": bi_stance,
    }
    if include_yoy:
        out["yoy_returns"] = calc_yoy_history(close, start_year=1995)
    return out


def analyze_ticker(name, ticker, category, rf_rate=0.068, include_yoy=False):
    try:
        period = "max" if include_yoy else "5y"
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None, None

        close = hist["Close"].dropna()
        clean_name = clean_label(name)
        currency = get_currency_symbol(clean_name, ticker)

        if category == "volatility_indices":
            mode = "vol"
            pe_ratio = None
        elif category in ["indian_equity", "indian_sectors", "global_indices"]:
            mode = "equity"
            pe_ratio = fetch_pe_ratio(ticker)
        else:
            mode = "macro"
            pe_ratio = None

        return analyze_series(
            clean_name, ticker, close, rf_rate, pe_ratio, currency, mode=mode, include_yoy=include_yoy
        ), close
    except Exception as e:
        print(f"Error fetching {name} ({ticker}): {e}")
        return None, None


def fetch_debt_and_liquid(rf_rate=0.068):
    results = []
    for label, meta in DEBT_AND_LIQUID_PROXIES.items():
        try:
            hist = yf.Ticker(meta["ticker"]).history(period="5y", auto_adjust=True)
            if hist.empty or len(hist) < 15:
                continue
            close = hist["Close"].dropna()
            base = analyze_series(
                label, meta["ticker"], close, rf_rate=rf_rate, pe=None,
                currency=get_currency_symbol(label, meta["ticker"]), mode="macro", include_yoy=False
            )
            base["bucket"] = meta["bucket"]
            base["duration_profile"] = meta["duration_profile"]
            base["credit_profile"] = meta["credit_profile"]
            results.append(base)
        except Exception as e:
            print(f"Debt proxy error ({label}): {e}")
    return results


def fetch_rss_news(rss_config, max_per_feed=6):
    news_pool = {"india": [], "global": []}
    for region in ["india", "global"]:
        for source in rss_config.get(region, []):
            try:
                feed = feedparser.parse(source["url"])
                for entry in feed.entries[:max_per_feed]:
                    news_pool[region].append({
                        "source": source["name"],
                        "title": entry.get("title", "").strip(),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "region": region.upper(),
                    })
            except Exception as e:
                print(f"RSS error ({source['name']}): {e}")
    return news_pool


def run_fetch():
    cfg = load_config()
    rf_rate = cfg.get("macro_manual", {}).get("risk_free_rate_india", 0.068)

    snapshot = {
        "updated_at_ist": datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
        "macro_manual": cfg.get("macro_manual", {}),
        "markets": {},
        "debt_liquid": [],
        "raw_news": {},
        "verified_news": [],
        "ai_strategist": {},
    }

    series_cache = {}
    for category, tickers in cfg["benchmarks"].items():
        snapshot["markets"][category] = []
        track_yoy = category in ["indian_equity", "global_indices"]
        for name, ticker in tickers.items():
            print(f"Fetching {name} ({ticker})...")
            data, close = analyze_ticker(name, ticker, category, rf_rate, include_yoy=track_yoy)
            if data:
                snapshot["markets"][category].append(data)
                series_cache[ticker] = close

    if "GC=F" in series_cache and "INR=X" in series_cache:
        gold_usd = series_cache["GC=F"].tz_localize(None)
        usdinr = series_cache["INR=X"].tz_localize(None)
        aligned = pd.concat([gold_usd.rename("gold"), usdinr.rename("fx")], axis=1).ffill().dropna()
        if len(aligned) > 20:
            gold_inr_10g = (aligned["gold"] / 31.1034768) * aligned["fx"] * 10
            gold_inr_data = analyze_series(
                "Gold INR / 10g", "GOLD_INR_10G", gold_inr_10g, rf_rate, currency="₹", mode="macro"
            )
            snapshot["markets"].setdefault("macro_commodities_fx", []).insert(0, gold_inr_data)

    snapshot["debt_liquid"] = fetch_debt_and_liquid(rf_rate=rf_rate)
    snapshot["raw_news"] = fetch_rss_news(cfg["rss_feeds"])

    os.makedirs("data", exist_ok=True)
    with open("data/market_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print("Saved data/market_snapshot.json successfully.")
    return snapshot


if __name__ == "__main__":
    run_fetch()
