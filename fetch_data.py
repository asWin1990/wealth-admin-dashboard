import os
import re
import json
import yaml
import feedparser
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
AMFI_NAV_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

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

AMFI_DEBT_BUCKETS = [
    {"bucket": "Liquid", "keywords": ["liquid fund"], "duration": "Ultra-Short (<91d)", "credit": "Sovereign / AAA"},
    {"bucket": "Money Market", "keywords": ["money market"], "duration": "Short (<1y)", "credit": "AAA / Commercial"},
    {"bucket": "Short Duration", "keywords": ["short duration", "short term"], "duration": "Short (1–3y)", "credit": "AAA / Sovereign"},
    {"bucket": "Corporate Bond", "keywords": ["corporate bond"], "duration": "Medium (2–5y)", "credit": "High-Grade AAA"},
    {"bucket": "Gilt / Long Duration", "keywords": ["gilt fund", "long duration"], "duration": "Long (7–10y+)", "credit": "Sovereign"},
]


def clean_label(text):
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calc_cagr(start_price, end_price, years):
    if start_price is None or end_price is None or pd.isna(start_price) or pd.isna(end_price) or start_price <= 0 or years <= 0:
        return None
    return round(((end_price / start_price) ** (1 / years) - 1) * 100, 2)


def calc_ny_cagr(series, years):
    """Computes annualized CAGR using the price ~N calendar years ago."""
    if series is None or len(series) < 20 or years <= 0:
        return None
    s = series.copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s = s.sort_index()

    end_dt = s.index[-1]
    end_price = float(s.iloc[-1])
    target_dt = end_dt - pd.Timedelta(days=int(round(years * 365.25)))

    # Require series history to reach back near target_dt (within a 45-day buffer)
    if s.index[0] > (target_dt + pd.Timedelta(days=45)):
        return None

    past_slice = s[s.index <= target_dt]
    if past_slice.empty:
        return None

    start_price = float(past_slice.iloc[-1])
    actual_years = (end_dt - past_slice.index[-1]).days / 365.25
    if actual_years < (years * 0.85):
        return None

    return calc_cagr(start_price, end_price, actual_years)


def calc_pct_return(series, trading_days):
    if len(series) <= trading_days:
        return None
    start = series.iloc[-1 - trading_days]
    end = series.iloc[-1]
    if pd.isna(start) or start <= 0:
        return None
    return round(((end / start) - 1) * 100, 2)


def calc_rsi_14(series):
    if series is None or len(series) < 15:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    latest = rs.iloc[-1]
    if pd.isna(latest):
        return None
    return round(float(100 - (100 / (1 + latest))), 1)


def calc_yoy_history(close, start_year=1995):
    if close is None or close.empty:
        return {}
    s = close.copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s = s.sort_index()

    years = [y for y in sorted(s.index.year.unique()) if y >= start_year]
    yoy = {}

    for idx, yr in enumerate(years):
        yr_slice = s[s.index.year == yr]
        if yr_slice.empty:
            continue
        end_val = float(yr_slice.iloc[-1])

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
    if "Yield" in name or "TNX" in ticker:
        return "%"
    if "INR" in name or ticker.endswith(".NS") or ticker.endswith(".BO"):
        return "₹"
    if "USD" in name or "Crude" in name or ticker in ["GC=F", "SI=F", "BZ=F", "EEM"]:
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
        return "Sell | 1D volatility spike"
    if dist_200dma is not None and dist_200dma > 30:
        return "Sell | Elevated stress"
    if price < 14 and (r_1w is None or r_1w <= 2):
        return "Buy | Calm volatility"
    return "Hold | Normal volatility"


def compute_bi_stance(pe, dist_200dma, from_52w_high, rsi_14, r_1m, r_3m, r_1y, sharpe, vol_1y, is_equity=True):
    score = 0.0
    reasons = []

    if is_equity and pe is not None:
        if pe < 18:
            score += 1.5
            reasons.append("reasonable valuation")
        elif pe <= 24:
            score += 0.75
            reasons.append("fair valuation")
        elif pe <= 30:
            score -= 0.5
            reasons.append("rich valuation")
        else:
            score -= 1.5
            reasons.append("stretched valuation")

    if dist_200dma is not None:
        if -12 <= dist_200dma < 0 and r_1m is not None and r_1m > 0:
            score += 1.5
            reasons.append("bouncing near long-term average")
        elif 0 <= dist_200dma <= 12:
            score += 1.0
            reasons.append("healthy long-term trend")
        elif dist_200dma > 18:
            score -= 1.25
            reasons.append("far above long-term average")
        elif dist_200dma < -15:
            score -= 1.0
            reasons.append("below long-term average")

    if rsi_14 is not None:
        if rsi_14 > 75:
            score -= 0.5
            reasons.append("short-term overbought")
        elif rsi_14 < 30:
            score += 0.5
            reasons.append("short-term oversold")

    if from_52w_high is not None and from_52w_high < -20 and (r_1m is None or r_1m <= 0):
        score -= 0.75
        reasons.append("well off 1-year high")

    pos_horizons = sum(1 for x in [r_1m, r_3m, r_1y] if x is not None and x > 0)
    neg_horizons = sum(1 for x in [r_1m, r_3m, r_1y] if x is not None and x < 0)
    if pos_horizons == 3:
        score += 1.0
        reasons.append("steady multi-month gains")
    elif neg_horizons == 3:
        score -= 1.0
        reasons.append("broad multi-month weakness")

    if sharpe is not None:
        if sharpe >= 1.0:
            score += 0.75
            reasons.append("strong risk-adjusted return")
        elif sharpe < -0.25:
            score -= 0.75
            reasons.append("weak risk-adjusted return")

    if vol_1y is not None and vol_1y > 28 and is_equity:
        score -= 0.5
        reasons.append("high price swings")

    if score >= 1.25:
        label = "Buy"
    elif score >= -0.75:
        label = "Hold"
    else:
        label = "Sell"

    reasoning = ", ".join(reasons[:2]) if reasons else "mixed signals"
    return f"{label} | {reasoning}"


def analyze_series(name, ticker, close, rf_rate=0.068, pe=None, currency="", mode="equity", include_yoy=False):
    current_price = round(float(close.iloc[-1]), 2)

    r_1d = calc_pct_return(close, 1)
    r_1w = calc_pct_return(close, 5)
    r_1m = calc_pct_return(close, 21)
    r_3m = calc_pct_return(close, 63)
    r_1y = calc_pct_return(close, 252)
    r_3y_cagr = calc_ny_cagr(close, 3)
    r_5y_cagr = calc_ny_cagr(close, 5)

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

    rsi_14 = None if mode == "vol" else calc_rsi_14(close)

    if mode == "vol":
        bi_stance = compute_vol_stance(current_price, dist_200dma, r_1d, r_1w)
    else:
        bi_stance = compute_bi_stance(
            pe, dist_200dma, from_52w_high, rsi_14, r_1m, r_3m, r_1y, sharpe, ann_vol, is_equity=(mode == "equity")
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
        "rsi_14": rsi_14,
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
        period = "max" if include_yoy else "6y"
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if hist.empty or len(hist) < 10:
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


def fetch_amfi_debt_schemes(per_bucket=3):
    schemes = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(AMFI_NAV_URL, headers=headers, timeout=25)
        resp.raise_for_status()
        lines = resp.text.splitlines()

        found_counts = {b["bucket"]: 0 for b in AMFI_DEBT_BUCKETS}
        for line in lines:
            parts = line.split(";")
            if len(parts) < 5:
                continue
            scheme_name = parts[3].strip()
            nav_str = parts[4].strip()
            nav_date = parts[5].strip() if len(parts) > 5 else ""

            try:
                nav_val = round(float(nav_str), 4)
            except ValueError:
                continue

            lower_name = scheme_name.lower()
            if "growth" not in lower_name:
                continue

            for b in AMFI_DEBT_BUCKETS:
                b_name = b["bucket"]
                if found_counts[b_name] >= per_bucket:
                    continue
                if any(kw in lower_name for kw in b["keywords"]):
                    schemes.append({
                        "scheme_name": scheme_name[:68],
                        "bucket": b_name,
                        "duration": b["duration"],
                        "credit": b["credit"],
                        "nav": nav_val,
                        "nav_date": nav_date,
                    })
                    found_counts[b_name] += 1
                    break

            if all(cnt >= per_bucket for cnt in found_counts.values()):
                break
    except Exception as e:
        print(f"AMFI NAV fetch error: {e}")
    return schemes


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
        "amfi_debt_schemes": [],
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

    print("Fetching live Indian Debt & Liquid MF NAVs from AMFI...")
    snapshot["amfi_debt_schemes"] = fetch_amfi_debt_schemes(per_bucket=3)

    snapshot["raw_news"] = fetch_rss_news(cfg["rss_feeds"])

    os.makedirs("data", exist_ok=True)
    with open("data/market_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print("Saved data/market_snapshot.json successfully.")
    return snapshot


if __name__ == "__main__":
    run_fetch()
