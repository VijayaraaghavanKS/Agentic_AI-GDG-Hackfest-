"""
agents/researcher.py – The Researcher Agent
============================================
OWNER: [Team Member A]

RESPONSIBILITY:
    - Gather live news, market sentiment, and macro headlines for each
      ticker in WATCH_LIST using Google Search Grounding.
    - Write a structured summary to session.state[KEY_RESEARCH_OUTPUT].

HOW SEARCH GROUNDING WORKS IN ADK:
    Pass `tools=[google_search]` to LlmAgent. The model will automatically
    decide when to trigger a live Google Search during its reasoning.
    No extra code is needed – grounding is handled by the Gemini API.

OUTPUT (written to session.state["research_output"]):
    A structured text block that the Analyst agent reads from session.state.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search          # Built-in grounding tool

from config import GEMINI_MODEL, KEY_RESEARCH_OUTPUT, WATCH_LIST, AGENT_TEMPERATURE

# ── Prompt ────────────────────────────────────────────────────────────────────
_INSTRUCTION = f"""
You are a financial research analyst specialising in Indian equities.

Your task:
1. For each ticker in this watch list: {WATCH_LIST}
   - Search for the latest news (last 24 hours) about the company.
   - Identify any earnings announcements, regulatory changes, or macro events.
   - Rate the overall sentiment as: BULLISH | BEARISH | NEUTRAL.

2. Return your findings ONLY as a structured JSON-like text block:

RESEARCH_REPORT:
  - ticker: <TICKER>
    headline: <key headline>
    sentiment: <BULLISH | BEARISH | NEUTRAL>
    confidence: <HIGH | MEDIUM | LOW>
    notes: <1-2 sentence context>

Use Google Search to ground your responses with real-time information.
Do NOT hallucinate. If no news is found, mark sentiment as NEUTRAL.
"""

# ── Agent Definition ──────────────────────────────────────────────────────────
researcher_agent = LlmAgent(
    name="Researcher",
    model=GEMINI_MODEL,
    description=(
        "Researches real-time news and market sentiment for stock tickers "
        "using Google Search Grounding."
    ),
    instruction=_INSTRUCTION,
    tools=[google_search],          # ← Enables Search Grounding

    # output_key writes the agent's final text response to session.state.
    # The Analyst agent can then read it via context.state["research_output"].
    output_key=KEY_RESEARCH_OUTPUT,

    # TODO: Add yfinance-based tools from tools/market_tools.py as needed.
    # TODO: Add a memory tool if you want cross-session recall.
)
