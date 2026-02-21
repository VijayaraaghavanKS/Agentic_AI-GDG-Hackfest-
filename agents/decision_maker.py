"""
agents/decision_maker.py – The DecisionMaker Agent
====================================================
OWNER: [Team Member A or B]

RESPONSIBILITY:
    - Read the Analyst's signals from session.state["technical_signals"].
    - Combine all available context to produce a final BUY / SELL / HOLD
      recommendation with a confidence score and rationale.
    - Write the final trade decision to session.state["trade_decision"].
    - This is the last agent in the pipeline; its output goes to the UI / main.

ADDING RISK MANAGEMENT:
    Add a function tool from tools/ (e.g., check_portfolio_exposure) so the
    agent can factor in current allocations before making decisions.
"""

from google.adk.agents import LlmAgent

from config import GEMINI_MODEL, KEY_TECHNICAL_SIGNALS, KEY_TRADE_DECISION, AGENT_TEMPERATURE

# ── Prompt ────────────────────────────────────────────────────────────────────
# {technical_signals} is injected by the ADK from session.state at runtime.
_INSTRUCTION = """
You are the senior portfolio manager and final decision authority for an
AI-driven trading system focused on NSE/BSE equities.

You have received the following technical analysis:
{technical_signals}

Your task – produce a final trading recommendation for each ticker:

1. Synthesise the research sentiment AND the technical signals.
2. Apply the following risk rules:
   - NEVER recommend buying a stock with BEARISH sentiment AND RSI > 65.
   - Flag HIGH RISK if confidence is LOW on both research and technical data.
   - Prefer HOLD over aggressive BUY/SELL when signals conflict.

3. Return ONLY the following structured block:

TRADE_DECISION:
  - ticker: <TICKER>
    action: <BUY | SELL | HOLD>
    confidence: <HIGH | MEDIUM | LOW>
    target_price: <estimated short-term target or N/A>
    stop_loss: <estimated stop-loss level or N/A>
    rationale: <1-2 sentence justification>
    risk_flag: <YES | NO>

4. After all tickers, add a PORTFOLIO_SUMMARY section with overall market
   stance: RISK-ON | RISK-OFF | NEUTRAL.
"""

# ── Agent Definition ──────────────────────────────────────────────────────────
decision_agent = LlmAgent(
    name="DecisionMaker",
    model=GEMINI_MODEL,
    description=(
        "Synthesises research and technical signals to produce final "
        "BUY/SELL/HOLD trade decisions with risk management."
    ),
    instruction=_INSTRUCTION,
    tools=[
        # TODO: add check_portfolio_exposure() from tools/market_tools.py
        # TODO: add send_trade_alert() notification tool
    ],

    # Writes the final decision to session.state["trade_decision"]
    output_key=KEY_TRADE_DECISION,
)
