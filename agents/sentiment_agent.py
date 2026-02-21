"""
agents/sentiment_agent.py – The Sentiment Agent (ADK Agent – Step 2)
=====================================================================
PIPELINE STEP: 2

RESPONSIBILITY:
    - Call the search_tool to retrieve recent macro news and analyst
      commentary for the target ticker.
    - Write a structured sentiment summary to the ADK session state
      at KEY_SENTIMENT.

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT (regime context from Step 1)

WRITES TO STATE:
    - KEY_SENTIMENT

TODO: Define the LlmAgent with system prompt and tools=[search_tool]
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from config import GEMINI_MODEL, AGENT_TEMPERATURE
from pipeline.session_keys import KEY_QUANT_SNAPSHOT, KEY_SENTIMENT


_INSTRUCTION = """
You are a macro-economic and sentiment research analyst specialising in
Indian equities (NSE/BSE).

The Quant Engine has already produced the following deterministic snapshot
for the target ticker:
{quant_snapshot}

Your task:
1. Use Google Search to find the latest news (last 24–48 hours) about the
   company and any macro events affecting the Indian market.
2. Identify earnings announcements, regulatory changes, sector rotation,
   FII/DII flows, or RBI policy impacts.
3. Return a structured sentiment summary. Do NOT hallucinate — if no news
   is found, state that clearly.

Output format:
SENTIMENT_SUMMARY:
  ticker: <TICKER>
  macro_outlook: <BULLISH | BEARISH | NEUTRAL>
  company_sentiment: <BULLISH | BEARISH | NEUTRAL>
  key_headlines:
    - <headline 1>
    - <headline 2>
  catalyst_risk: <brief description of imminent catalyst or risk>
  confidence: <HIGH | MEDIUM | LOW>
"""

sentiment_agent = LlmAgent(
    name="SentimentAgent",
    model=GEMINI_MODEL,
    description=(
        "Researches real-time news and macro sentiment for the target ticker "
        "using Google Search Grounding. Step 2 of the pipeline."
    ),
    instruction=_INSTRUCTION,
    tools=[google_search],
    output_key=KEY_SENTIMENT,
)
