"""
agents/analyst.py – The Analyst Agent
=======================================
OWNER: [Team Member B]

RESPONSIBILITY:
    - Read the Researcher's output from session.state["research_output"].
    - Fetch live OHLCV price data using tools from tools/market_tools.py.
    - Compute technical indicators (RSI, MACD, moving averages etc.).
    - Write a structured signals report to session.state["technical_signals"].

HOW TO READ FROM SHARED STATE:
    The ADK automatically injects session.state values into the instruction
    via template strings. Use {research_output} in the prompt and the ADK
    will substitute the live value at runtime.

OUTPUT (written to session.state["technical_signals"]):
    Structured signal data consumed by the DecisionMaker agent.
"""

from google.adk.agents import LlmAgent

from config import GEMINI_MODEL, KEY_RESEARCH_OUTPUT, KEY_TECHNICAL_SIGNALS, AGENT_TEMPERATURE
from tools.market_tools import (
    get_price_data,
    get_rsi,
    get_macd,
    get_moving_averages,
)

# ── Prompt ────────────────────────────────────────────────────────────────────
# {research_output} is substituted by the ADK from session.state at runtime.
_INSTRUCTION = f"""
You are a quantitative analyst for an Indian equity trading desk.

You have received the following research report from the Researcher:
{{{{research_output}}}}

Your task:
1. For each ticker in the research report, call the available technical tools:
   - get_price_data(ticker) – fetch recent OHLCV data
   - get_rsi(ticker)        – get the current 14-day RSI
   - get_macd(ticker)       – get MACD line, signal, and histogram
   - get_moving_averages(ticker) – get 20-day and 50-day SMAs

2. Interpret the signals:
   - RSI > 70 → Overbought warning
   - RSI < 30 → Oversold / potential opportunity
   - MACD crossover → Momentum shift
   - Price above 50-SMA = bullish structure, below = bearish

3. Return ONLY the following structured block:

TECHNICAL_SIGNALS:
  - ticker: <TICKER>
    rsi: <value>
    macd_signal: <BULLISH | BEARISH | NEUTRAL>
    ma_trend: <UPTREND | DOWNTREND | SIDEWAYS>
    combined_sentiment: <BULLISH | BEARISH | NEUTRAL>
    suggested_action: <BUY | SELL | HOLD>
"""

# ── Agent Definition ──────────────────────────────────────────────────────────
analyst_agent = LlmAgent(
    name="Analyst",
    model=GEMINI_MODEL,
    description=(
        "Performs quantitative technical analysis on stocks using "
        "live price data and indicators. Reads from research_output."
    ),
    instruction=_INSTRUCTION,
    tools=[
        get_price_data,
        get_rsi,
        get_macd,
        get_moving_averages,
    ],

    # Writes its final output to session.state["technical_signals"]
    output_key=KEY_TECHNICAL_SIGNALS,

    # TODO: Add sentiment scoring tool.
    # TODO: Add volatility / ATR tool.
    # TODO: Add F&O data tool (options chain, PCR).
)
