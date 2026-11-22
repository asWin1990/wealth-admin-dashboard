import os
import json
import yaml
import feedparser
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ETF proxies used to fetch real P/E & P/B multiples where raw indices return None
VALUATION_PROXIES = {
    "^NSEI": "NIFTYBEES.NS",
    "^NSMIDCP": "JUNIORBEES.NS",
    "^CRSLDX": "MONIFTY500.NS",
    "^NSEBANK": "BANKBEES.NS",
    "^CNXPSUBANK": "PSUBNKBEES.NS",
    "^CNXIT": "ITBEES.NS",
    "^CNXPHARMA": "PHARMABEES.NS",
    "^CNXINFRA": "INFRABEES.NS",
    "^CNXAUTO": "AUTOBEES.NS",
    "^CNXFMCG": "FMCGIETF.NS",
    "^CNXMETAL": "METALIETF.NS",
    "^CNXENERGY": "OILIETF.NS",
    "^GSPC": "SPY",
    "^NDX": "QQQ",
    "^HSI": "EWH",
    "^N225": "EWJ",
    "^GDAXI": "EWG",
}


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


def get_currency_symbol(name, ticker):
    if "VIX" in name:
        return ""
    if "Yield" in name or "TNX" in ticker:
        return "%"
    if "INR" in name or ticker.endswith(".NS") or ticker.endswith(".BO"):
        return "₹"
    if "USD" in name or "Crude" in name or ticker in ["GC=F", "SI=F", "BZ=F", "EEM"]:
        return "$"
    return ""


def fetch_valuation_multiples(ticker):
    """Fetch P/E and P/B from ticker, falling back to its liquid ETF proxy."""
    for sym in [ticker, VALUATION_PROXIES.get(ticker)]:
        if not sym:
            continue
        try:
            info = yf.Ticker(sym).info or {}
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            if pe or pb:
                return (
                    round(float(pe), 2) if pe else None,
                    round(float(pb), 2) if pb else None,
                )
        except Exception:
            continue
    return None, None


def compute_bi_stance(pe, pb, dist_200dma, r_1m, r_3m, sharpe):
    score = 0
    if pe is not None:
        if pe < 18:
            score += 2
        elif pe <= 25:
            score += 1
        elif pe > 32:
            score -= 2
        else:
            score -= 1

    if pb is not None:
        if pb < 2.5:
            score += 1
        elif pb > 5.0:
            score -= 1

    if dist_200dma is not None:
        if -12 <= dist_200dma <= 0 and (r_1m is not None and r_1m > 0):
            score += 2
        elif 0 < dist_200dma <= 12:
            score += 1
        elif dist_200dma > 16:
            score -= 2
        elif dist_200dma < -12:
            score -= 1

    if r_3m is not None:
        if r_3m > 4:
            score += 1
        elif r_3m < -5:
            score -= 1

    if sharpe is not None:
        if sharpe >= 0.8:
            score += 1
        elif sharpe < -0.3:
            score -= 1

    if score >= 3:
        return "Strong Buy"
    elif score == 2:
        return "Accumulate"
    elif score in [0, 1]:
        return "Hold / Neutral"
    elif score == -1:
        return "Cautious / Trim"
    return "Avoid / Weak"


def analyze_series(name, ticker, close, rf_rate=0.068, pe=None, pb=None, currency=""):
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

    bi_stance = compute_bi_stance(pe, pb, dist_200dma, r_1m, r_3m, sharpe)

    return {
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
        "dist_200dma": dist_200dma,
        "pe": pe,
        "pb": pb,
        "bi_stance": bi_stance,
    }


def analyze_ticker(name, ticker, category, rf_rate=0.068):
    try:
        hist = yf.Ticker(ticker).history(period="5y", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None, None

        close = hist["Close"].dropna()
        is_equity = category in ["indian_equity", "indian_sectors", "global_indices"] and "VIX" not in name
        pe_ratio, pb_ratio = fetch_valuation_multiples(ticker) if is_equity else (None, None)
        currency = get_currency_symbol(name, ticker)

        return analyze_series(name, ticker, close, rf_rate, pe_ratio, pb_ratio, currency), close
    except Exception as e:
        print(f"Error fetching {name} ({ticker}): {e}")
        return None, None


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
        "raw_news": {},
        "verified_news": [],
        "ai_strategist": {},
    }

    series_cache = {}
    for category, tickers in cfg["benchmarks"].items():
        snapshot["markets"][category] = []
        for name, ticker in tickers.items():
            if ticker == "GOLDBEES.NS":
                continue
            print(f"Fetching {name} ({ticker})...")
            data, close = analyze_ticker(name, ticker, category, rf_rate)
            if data:
                snapshot["markets"][category].append(data)
                series_cache[ticker] = close

    # Live Gold (INR / 10g)
    if "GC=F" in series_cache and "INR=X" in series_cache:
        gold_usd = series_cache["GC=F"].tz_localize(None)
        usdinr = series_cache["INR=X"].tz_localize(None)
        aligned = pd.concat([gold_usd.rename("gold"), usdinr.rename("fx")], axis=1).ffill().dropna()
        if len(aligned) > 20:
            gold_inr_10g = (aligned["gold"] / 31.1034768) * aligned["fx"] * 10
            gold_inr_data = analyze_series(
                "Gold (INR / 10g)", "GOLD_INR_10G", gold_inr_10g, rf_rate, currency="₹"
            )
            snapshot["markets"].setdefault("macro_commodities_fx", []).insert(0, gold_inr_data)

    snapshot["raw_news"] = fetch_rss_news(cfg["rss_feeds"])

    os.makedirs("data", exist_ok=True)
    with open("data/market_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print("Saved data/market_snapshot.json successfully.")
    return snapshot


if __name__ == "__main__":
    run_fetch()
