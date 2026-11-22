import os
import json
import yaml
import feedparser
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


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


def analyze_ticker(name, ticker, rf_rate=0.068):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5y", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None

        close = hist["Close"].dropna()
        current_price = round(float(close.iloc[-1]), 2)

        # Multi-horizon returns
        r_1d = calc_pct_return(close, 1)
        r_1w = calc_pct_return(close, 5)
        r_1m = calc_pct_return(close, 21)
        r_3m = calc_pct_return(close, 63)
        r_1y = calc_pct_return(close, 252)
        r_3y_cagr = calc_cagr(close.iloc[-756], current_price, 3) if len(close) > 756 else None
        r_5y_cagr = calc_cagr(close.iloc[0], current_price, 5) if len(close) > 1100 else None

        # Risk & Technicals (1Y Window)
        recent_1y = close.tail(252)
        daily_ret = recent_1y.pct_change().dropna()
        ann_vol = round(float(daily_ret.std() * np.sqrt(252) * 100), 2) if len(daily_ret) > 10 else None

        sharpe = None
        if r_1y is not None and ann_vol and ann_vol > 0:
            sharpe = round(((r_1y / 100) - rf_rate) / (ann_vol / 100), 2)

        # Max Drawdown (1Y)
        rolling_max = recent_1y.cummax()
        drawdown = (recent_1y / rolling_max - 1) * 100
        max_dd = round(float(drawdown.min()), 2)

        # Distance from 200-DMA
        dma_200 = float(close.tail(200).mean()) if len(close) >= 200 else None
        dist_200dma = round(((current_price / dma_200) - 1) * 100, 2) if dma_200 else None

        # Valuation metrics (where available on Yahoo Finance)
        info = t.info or {}
        pe_ratio = info.get("trailingPE")
        pb_ratio = info.get("priceToBook")
        pe_ratio = round(float(pe_ratio), 2) if pe_ratio else None
        pb_ratio = round(float(pb_ratio), 2) if pb_ratio else None

        # Rule-based Signal (Valuation/Mean-Reversion + Momentum)
        signal = "Neutral"
        if dist_200dma is not None and r_3m is not None:
            if dist_200dma < 0 and r_1m is not None and r_1m > 0:
                signal = "Accumulate (Reversing)"
            elif dist_200dma > 15:
                signal = "Extended / Caution"
            elif dist_200dma > 0 and r_3m > 3:
                signal = "Bullish Trend"
            elif dist_200dma < -5 and r_3m < -3:
                signal = "Weak / Watchlist"

        return {
            "name": name,
            "ticker": ticker,
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
            "pe": pe_ratio,
            "pb": pb_ratio,
            "signal": signal,
        }
    except Exception as e:
        print(f"Error fetching {name} ({ticker}): {e}")
        return None


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
                        "region": region.upper()
                    })
            except Exception as e:
                print(f"RSS error ({source['name']}): {e}")
    return news_pool


def run_fetch():
    cfg = load_config()
    rf_rate = cfg.get("macro_manual", {}).get("risk_free_rate_india", 0.068)
    stances = cfg.get("advisory_stances", {})

    snapshot = {
        "updated_at_ist": datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
        "macro_manual": cfg.get("macro_manual", {}),
        "markets": {},
        "raw_news": {},
        "verified_news": [],
        "ai_strategist": {}
    }

    for category, tickers in cfg["benchmarks"].items():
        snapshot["markets"][category] = []
        for name, ticker in tickers.items():
            print(f"Fetching {name} ({ticker})...")
            data = analyze_ticker(name, ticker, rf_rate)
            if data:
                data["stance"] = stances.get(name, "Neutral")
                snapshot["markets"][category].append(data)

    print("Fetching Tier-1 RSS news feeds...")
    snapshot["raw_news"] = fetch_rss_news(cfg["rss_feeds"])

    os.makedirs("data", exist_ok=True)
    with open("data/market_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print("Saved data/market_snapshot.json successfully.")
    return snapshot


if __name__ == "__main__":
    run_fetch()
