"""
agents/cio_agent.py – The Chief Investment Officer (ADK Agent – Step 5)
========================================================================
PIPELINE STEP: 5

RESPONSIBILITY:
    - Read the ENTIRE debate: quant snapshot, sentiment, bull thesis, and
      bear thesis from session state.
    - Synthesise everything into a single structured JSON trade proposal.
    - Write the raw proposal to KEY_CIO_PROPOSAL (Step 6's risk_tool will
      then intercept and enforce hard limits).

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT
    - KEY_SENTIMENT
    - KEY_BULL_THESIS
    - KEY_BEAR_THESIS

WRITES TO STATE:
    - KEY_CIO_PROPOSAL (raw JSON — NOT yet risk-validated)

TODO: Define the LlmAgent with system prompt
"""

from google.adk.agents import LlmAgent

from config import GEMINI_MODEL, AGENT_TEMPERATURE
from pipeline.session_keys import (
    KEY_QUANT_SNAPSHOT, KEY_SENTIMENT,
    KEY_BULL_THESIS, KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
)


_INSTRUCTION = """
You are the CHIEF INVESTMENT OFFICER (CIO) — the final decision authority.
You have just listened to a structured debate between the Bull and Bear
analysts, grounded in deterministic quant data.

QUANT SNAPSHOT (deterministic — treat as ground truth):
{quant_snapshot}

SENTIMENT SUMMARY:
{sentiment_summary}

BULL THESIS:
{bull_thesis}

BEAR THESIS:
{bear_thesis}

Your task:
1. Weigh both sides of the debate objectively.
2. Factor in the REGIME classification (BULL/BEAR/NEUTRAL) heavily — trend
   is your friend.
3. Produce a single trade proposal as structured JSON.

CRITICAL RULES:
- If the regime is BEAR and both sentiment and bear thesis are strong,
  default to HOLD or SELL. Do NOT fight the trend.
- Your stop-loss is a SUGGESTION — the Risk Engine will override it
  mathematically. Set it to your best estimate.
- conviction_score is 0.0 to 1.0 (1.0 = highest conviction).

Output ONLY valid JSON (no markdown fences):
{
  "ticker": "<TICKER>",
  "action": "BUY | SELL | HOLD",
  "entry": <entry price as float>,
  "raw_stop_loss": <your suggested stop-loss as float>,
  "target": <target price as float>,
  "conviction_score": <0.0 to 1.0>,
  "rationale": "<2-3 sentence synthesis of the debate>"
}
"""

cio_agent = LlmAgent(
    name="CIOAgent",
    model=GEMINI_MODEL,
    description=(
        "Chief Investment Officer. Synthesises the bull/bear debate into a "
        "final structured JSON trade proposal. Step 5 of the pipeline."
    ),
    instruction=_INSTRUCTION,
    tools=[],
    output_key=KEY_CIO_PROPOSAL,
)
