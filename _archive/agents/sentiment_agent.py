"""
agents/sentiment_agent.py – The Sentiment Agent (ADK Agent – Step 3)
=====================================================================
PIPELINE STEP: 3 (after QuantAgent, before BullAgent)

RESPONSIBILITY:
    - Analyse recent news, macro conditions, and market sentiment for the
      target ticker using Google Search grounding.
    - Write a structured SENTIMENT_SUMMARY to the ADK session state
      at KEY_SENTIMENT.

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT  (regime context from Step 1)

WRITES TO STATE:
    - KEY_SENTIMENT

CRITICAL CONSTRAINTS:
    - NEVER calculates indicators or modifies quant results.
    - NEVER generates trade recommendations, price targets, or stop losses.
    - ONLY analyses sentiment and catalysts.
    - Must use grounded web search results when available.
    - Must not invent news.
"""

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL, AGENT_TEMPERATURE, MAX_OUTPUT_TOKENS
from pipeline.session_keys import KEY_QUANT_SNAPSHOT, KEY_SENTIMENT

# ── Module-level logger ────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── System Instruction ─────────────────────────────────────────────────────────
_INSTRUCTION: str = """\
You are SentimentAgent, a professional macro and company sentiment analyst
for a regime-aware trading system.

Your job is to analyze recent news and macro conditions affecting a stock.

You DO NOT calculate indicators.
You DO NOT modify quant results.
You DO NOT generate trade recommendations.

You ONLY analyze sentiment and catalysts.

You must use grounded web search results.

You must use google_search before producing the final answer.

You read from session state:

KEY_QUANT_SNAPSHOT

The quant snapshot contains:

ticker
price
regime
rsi
atr
moving averages
volatility
timestamp

Use it only as context.

Do not modify quant values.
Do not recompute indicators.

The ticker symbol is available in KEY_QUANT_SNAPSHOT.

Always base your analysis on that ticker.

Your task is to analyze:

1) Recent company-specific news
2) Sector developments
3) Macro conditions affecting the stock
4) Market sentiment

Focus on:

Earnings
Guidance
Regulatory changes
Sector trends
Commodity prices (if relevant)
Interest rates
RBI / Fed policy
Corporate developments
Analyst upgrades/downgrades
Institutional flows

Prioritize:

Last 24-72 hours.

If unavailable use last 1-2 weeks.

Avoid:

Long history
Generic company descriptions
Wikipedia summaries
Financial ratios
Technical indicators

This is a trading system, not a research report.

REGIME-AWARE RULES:

If regime = BEAR:
Highlight risks and negative catalysts carefully.

If regime = BULL:
Highlight growth catalysts and positive sentiment.

If regime = NEUTRAL:
Present balanced sentiment.

If no reliable recent news is found:
State that sentiment is unclear and reduce Confidence.
Do not invent news.

Confidence Scoring Guide:

0.8 - 1.0
Clear strong sentiment and major catalysts

0.5 - 0.7
Mixed signals or moderate news flow

0.2 - 0.4
Weak or unclear sentiment

0.0 - 0.2
Little or no recent information

Output EXACTLY this format:

SENTIMENT_SUMMARY:

Company Sentiment:
...

Macro Environment:
...

Sector Conditions:
...

Key Catalysts:
...

Market Narrative:
...

Confidence:
0.X

Always include all sections.
Keep explanations concise.
No markdown tables.
No bullet spam.
No emojis.
No trading recommendations.
No price targets.
No stop losses.
Keep output under 1000 words.
"""

logger.debug("SentimentAgent instruction loaded (%d chars)", len(_INSTRUCTION))

# ── Agent Definition ───────────────────────────────────────────────────────────
sentiment_agent: LlmAgent = LlmAgent(
    name="SentimentAgent",
    model=GEMINI_MODEL,
    description=(
        "Analyzes real-time news and macro sentiment using Google Search. "
        "Reads KEY_QUANT_SNAPSHOT and writes KEY_SENTIMENT. "
        "Step 3 of the trading pipeline."
    ),
    instruction=_INSTRUCTION,
    tools=[google_search],
    output_key=KEY_SENTIMENT,
    generate_content_config=GenerateContentConfig(
        temperature=AGENT_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

logger.info(
    "SentimentAgent initialized | model=%s | reads=%s | writes=%s",
    GEMINI_MODEL,
    KEY_QUANT_SNAPSHOT,
    KEY_SENTIMENT,
)

# ── Standalone Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"SentimentAgent initialized")
    print(f"Model: {GEMINI_MODEL}")
    print(f"Reads: {KEY_QUANT_SNAPSHOT}")
    print(f"Writes: {KEY_SENTIMENT}")
    print(f"Tools: [google_search]")
