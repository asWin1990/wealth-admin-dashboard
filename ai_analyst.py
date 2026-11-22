import os
import json
from google import genai
from google.genai import types


def run_ai_analysis():
    snapshot_path = "data/market_snapshot.json"
    if not os.path.exists(snapshot_path):
        print("Snapshot not found. Run fetch_data.py first.")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Skipping AI analysis.")
        return

    client = genai.Client(api_key=api_key)

    # Compact market summary for the AI
    market_summary = {}
    for cat, items in snapshot.get("markets", {}).items():
        market_summary[cat] = [
            {
                "name": x["name"],
                "1D": x["1D"],
                "1M": x["1M"],
                "3M": x["3M"],
                "1Y": x["1Y"],
                "dist_200dma": x["dist_200dma"],
                "vol_1y": x["volatility_1y"],
                "sharpe": x["sharpe_1y"],
                "pe": x["pe"],
                "stance": x.get("stance", "Neutral"),
                "bi_stance": x.get("bi_stance", "Neutral"),
            }
            for x in items
        ]

    raw_news = snapshot.get("raw_news", {})

    prompt = f"""
You are a Senior Wealth Management Strategist advising an Indian Mutual Fund & Multi-Asset advisor.
Analyze today's market data and raw Tier-1 RSS news below.

MARKET DATA:
{json.dumps(market_summary)}

MACRO RATES:
{json.dumps(snapshot.get("macro_manual", {}))}

RAW NEWS POOL:
{json.dumps(raw_news)}

Return ONLY valid JSON with this exact structure:
{{
  "verified_news": [
    {{
      "region": "INDIA" or "GLOBAL",
      "source": "Source Name",
      "title": "Clean, factual headline (no clickbait)",
      "link": "exact URL from raw news",
      "tag": "e.g., India Equity | Global Macro | Debt/Duration | Commodities | Sectoral",
      "impact": "1-sentence takeaway for a wealth advisor"
    }}
  ],
  "ai_strategist": {{
    "market_regime": "1 short phrase (e.g., Risk-On Rotation / Cautious Consolidation / High-Vol Pullback)",
    "opportunities": [
      "2-3 specific bullets on sectors/indices looking attractive on valuation + momentum or reversing from oversold"
    ],
    "risk_flags": [
      "2 bullets on extended/expensive pockets, volatility spikes, or divergence from the advisor's current Overweight/Underweight stances"
    ],
    "debt_and_macro": "2 sentences on RBI Repo, US/India yields, USD/INR, Gold, and whether Short or Long Duration debt looks better right now."
  }}
}}

STRICT RULES:
1. Select EXACTLY 10 news items: 4 INDIA and 6 GLOBAL.
2. Only use links and facts strictly present in RAW NEWS POOL. Never invent URLs or stories.
3. Prioritize macro, central banks, earnings, flows, and sector-moving news over minor single-stock gossip.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        result = json.loads(response.text)
        snapshot["verified_news"] = result.get("verified_news", [])
        snapshot["ai_strategist"] = result.get("ai_strategist", {})

        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        print("AI analysis & verified news saved to market_snapshot.json.")
    except Exception as e:
        print(f"AI analysis error: {e}")


if __name__ == "__main__":
    run_ai_analysis()
