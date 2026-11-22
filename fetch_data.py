import os
import json
import yaml
import feedparser
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# Currency prefix mapping
CURRENCY_MAP = {
    "indian_equity": "pts",
    "indian_sectors": "pts",
    "global_indices": "pts",
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


def get_currency_symbol(name, ticker, category):
    if "VIX" in name:
        return ""
    if "Yield" in name or "TNX" in ticker:
        return "%"
    if "INR" in name or ticker.endswith(".NS") or ticker.endswith(".BO"):
        if "USD / INR" in name:
            return "₹"
        return "₹" if ticker.endswith(".NS") else ""
    if "USD" in name or "Crude" in name or ticker in ["GC=F", "SI=F", "BZ=F", "EEM"]:
        return "$"
    return ""


def compute_bi_stance(pe, pb, dist_200dma, r_1m, r_3m, sharpe):
    """
    Business Intelligence Stance combining Valuation (P/E, P/B),
    Trend (200-DMA, 1M/3M momentum), and Risk-Adjusted Quality (Sharpe).
    """
    score = 0
    reasons = []

    # 1. Valuation Pillar
    if pe is not None:
        if pe < 18:
            score += 2
            reasons.append("Attractive P/E")
        elif pe <= 25:
            score += 1
            reasons.append("Fair P/E")
        elif pe > 32:
            score -= 2
            reasons.append("Rich P/E")
        else:
            score -= 1

    if pb is not None:
        if pb < 2.5:
            score += 1
        elif pb > 5.0:
            score -= 1

    # 2. Trend & Mean-Reversion Pillar
    if dist_200dma is not None:
        if -12 <= dist_200dma <= 0 and (r_1m is not None and r_1m > 0):
            score += 2
            reasons.append("Reversing from 200-DMA")
        elif 0 < dist_200dma <= 12:
            score += 1
            reasons.append("Healthy Uptrend")
        elif dist_200dma > 16:
            score -= 2
            reasons.append("Overextended")
        elif dist_200dma < -12:
            score -= 1
            reasons.append("Deep Drawdown")

    # 3. Momentum & Risk-Adjusted Quality
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

    # Final BI Judgement
    if score >= 3:
        return "Strong Buy (Value + Trend)"
    elif score == 2:
        return "Accumulate"
    elif score in [0, 1]:
        return "Hold / Neutral"
    elif score == -1:
        return "Cautious / Trim"
    else:
        return "Avoid / Overheated"


def analyze_series(name, ticker, close, category, rf_rate=0.068, pe=None, pb=None, currency=""):
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

    rolling_max = recent_1y.cummax()
    max_dd = round(float(((recent_1y / rolling_max - 1) * 100).min()), 2)

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
        "max_drawdown_1y": max_dd,
        "dist_200dma": dist_200dma,
        "pe": pe,
        "pb": pb,
        "bi_stance": bi_stance,
    }


def analyze_ticker(name, ticker, category, rf_rate=0.068):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5y", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None, None

        close = hist["Close"].dropna()
        info = t.info or {}
        pe_ratio = info.get("trailingPE")
        pb_ratio = info.get("priceToBook")
        pe_ratio = round(float(pe_ratio), 2) if pe_ratio else None
        pb_ratio = round(float(pb_ratio), 2) if pb_ratio else None
        currency = get_currency_symbol(name, ticker, category)

        data = analyze_series(name, ticker, close, category, rf_rate, pe_ratio, pb_ratio, currency)
        return data, close
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
            # Skip old Gold Bees ETF in favor of synthetic Gold INR / 10g
            if ticker == "GOLDBEES.NS":
                continue
            print(f"Fetching {name} ({ticker})...")
            data, close = analyze_ticker(name, ticker, category, rf_rate)
            if data:
                snapshot["markets"][category].append(data)
                series_cache[ticker] = close

    # Compute live Gold (INR / 10g) = (Gold USD/oz / 31.1034768) * USD/INR * 10
    if "GC=F" in series_cache and "INR=X" in series_cache:
        gold_usd = series_cache["GC=F"].tz_localize(None)
        usdinr = series_cache["INR=X"].tz_localize(None)
        aligned = pd.concat([gold_usd.rename("gold"), usdinr.rename("fx")], axis=1).ffill().dropna()
        if len(aligned) > 20:
            gold_inr_10g = (aligned["gold"] / 31.1034768) * aligned["fx"] * 10
            gold_inr_data = analyze_series(
                "Gold (INR / 10g)", "GOLD_INR_10G", gold_inr_10g, "macro_commodities_fx", rf_rate, currency="₹"
            )
            snapshot["markets"].setdefault("macro_commodities_fx", []).insert(0, gold_inr_data)

    print("Fetching Tier-1 RSS news feeds...")
    snapshot["raw_news"] = fetch_rss_news(cfg["rss_feeds"])

    os.makedirs("data", exist_ok=True)
    with open("data/market_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print("Saved data/market_snapshot.json successfully.")
    return snapshot


if __name__ == "__main__":
    run_fetch()
