"""
agents/risk_tool_agent.py – RiskToolAgent (ADK Agent – Step 7)
================================================================
PIPELINE STEP: 7 (final agent in the pipeline)

PIPELINE ORDER:
    QuantToolAgent → QuantAgent → SentimentAgent → BullAgent → BearAgent → CIOAgent → **RiskToolAgent**

RESPONSIBILITY:
    - Read the CIO proposal from ``KEY_CIO_PROPOSAL``.
    - Read the quant snapshot from ``KEY_QUANT_SNAPSHOT``.
    - Execute ``risk_enforcement_tool`` to produce a validated trade.
    - Write the validated trade to ``KEY_FINAL_TRADE``.
    - Return a short confirmation string (no analysis, no interpretation).

DESIGN:
    This is a **deterministic tool-wrapper agent**.  It exists solely so
    that the ADK Web UI can visualise the ``risk_enforcement_tool``
    execution as a distinct pipeline step.  The LLM is configured at
    temperature 0 and instructed to do NOTHING beyond calling the tool
    and echoing the confirmation format.

READS:
    ``KEY_CIO_PROPOSAL``  — raw JSON trade proposal from CIO agent
    ``KEY_QUANT_SNAPSHOT`` — deterministic quant engine output

WRITES:
    ``KEY_FINAL_TRADE`` — validated trade dict with enforced risk limits
"""

from __future__ import annotations

import logging
from typing import Final

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL
from tools.risk_tool import risk_enforcement_tool
from pipeline.session_keys import (
    KEY_CIO_PROPOSAL,
    KEY_QUANT_SNAPSHOT,
    KEY_FINAL_TRADE,
)

# ── Logging ───────────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Agent Constants ───────────────────────────────────────────────────────────
AGENT_TEMPERATURE: Final[float] = 0.0
MAX_OUTPUT_TOKENS: Final[int] = 1024

# ── Instruction ───────────────────────────────────────────────────────────────
_INSTRUCTION: Final[str] = """\
You are RiskToolAgent — the deterministic final gate of the trading pipeline.

=== CIO PROPOSAL ===
{cio_proposal}

=== QUANT SNAPSHOT ===
{quant_snapshot}

YOUR ONLY JOB:
1. Parse the CIO PROPOSAL above and extract these values:
   - ticker         (from the "Ticker:" line)
   - action         (from the "Action:" line — BUY, SELL, or HOLD)
   - entry          (from the "Entry:" line — numeric)
   - target         (from the "Target:" line — numeric)
   - conviction_score (from the "Conviction:" line — numeric 0 to 1)
   - raw_stop_loss  (from the "Raw Stop Loss:" line — numeric)

2. Parse the QUANT SNAPSHOT above and extract:
   - regime  (from the "Regime:" line)
   - atr     (from the "ATR:" line — numeric, must be > 0)
   - ticker  (from the "Ticker:" line — must match CIO ticker exactly)

3. Call risk_enforcement_tool with:
   cio_proposal = {
     "ticker": <CIO ticker>,
     "action": <CIO action>,
     "entry": <CIO entry as float>,
     "target": <CIO target as float>,
     "conviction_score": <CIO conviction_score as float>,
     "regime": <quant regime>
   }
   quant_snapshot = {
     "ticker": <quant ticker>,
     "atr": <quant atr as float>
   }

4. Return EXACTLY this pretty decision card format and NOTHING else:

REGIME-AWARE TRADING DECISION
================================

Ticker: <ticker>
Regime: <regime>

Decision: <action>

Entry: <entry_price>
Stop: <stop_loss>
Target: <target_price>

Risk Reward: <risk_reward_ratio>

Status: <ACCEPTED or REJECTED>

Reason:
<kill_reason or 'Trade accepted'>

RULES — STRICT:
• You MUST call risk_enforcement_tool. Do NOT write Python code.
• Use ONLY parsed values from the sessions above — do NOT hallucinate.
• All numeric values passed to the tool must be floats, not strings.
• Include ALL output fields — use ONLY values returned by the tool.
• If the tool call fails, return the error message verbatim.
"""

# ── Agent Definition ──────────────────────────────────────────────────────────
risk_tool_agent: LlmAgent = LlmAgent(
    name="RiskToolAgent",
    model=GEMINI_MODEL,
    description=(
        "Deterministic tool-wrapper that executes risk_enforcement_tool "
        "and writes the validated final trade to session state."
    ),
    instruction=_INSTRUCTION,
    tools=[risk_enforcement_tool],
    output_key=KEY_FINAL_TRADE,
    generate_content_config=GenerateContentConfig(
        temperature=AGENT_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

logger.info(
    "RiskToolAgent initialized | model=%s | reads=%s, %s | writes=%s",
    GEMINI_MODEL,
    KEY_CIO_PROPOSAL,
    KEY_QUANT_SNAPSHOT,
    KEY_FINAL_TRADE,
)

# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("RiskToolAgent initialized")
    print(f"Model: {GEMINI_MODEL}")
    print(f"Reads: {KEY_CIO_PROPOSAL}, {KEY_QUANT_SNAPSHOT}")
    print(f"Writes: {KEY_FINAL_TRADE}")
