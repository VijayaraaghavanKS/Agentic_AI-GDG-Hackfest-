"""
agents/quant_tool_agent.py – QuantToolAgent (ADK Agent – Step 1)
=================================================================
PIPELINE STEP: 1 (first agent in the pipeline)

PIPELINE ORDER:
    **QuantToolAgent** → QuantAgent → SentimentAgent → BullAgent → BearAgent → CIOAgent → RiskToolAgent

RESPONSIBILITY:
    - Accept a stock ticker symbol from the user or upstream context.
    - Execute ``quant_engine_tool`` to produce a deterministic quant snapshot.
    - Write the snapshot to session state at ``KEY_QUANT_SNAPSHOT``.
    - Return a short confirmation string (no analysis, no interpretation).

DESIGN:
    This is a **deterministic tool-wrapper agent**.  It exists solely so
    that the ADK Web UI can visualise the ``quant_engine_tool`` execution
    as a distinct pipeline step.  The LLM is configured at temperature 0
    and instructed to do NOTHING beyond calling the tool and echoing
    the confirmation format.

WRITES:
    ``KEY_QUANT_SNAPSHOT`` — flat dict from ``quant_engine_tool``

READS:
    Nothing — ticker comes from user input.
"""

from __future__ import annotations

import logging
from typing import Final

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL
from tools.quant_tool import quant_engine_tool
from pipeline.session_keys import KEY_QUANT_SNAPSHOT

# ── Logging ───────────────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Agent Constants ───────────────────────────────────────────────────────────
AGENT_TEMPERATURE: Final[float] = 0.0
MAX_OUTPUT_TOKENS: Final[int] = 1024

# ── Instruction ───────────────────────────────────────────────────────────────
_INSTRUCTION: Final[str] = """\
You are QuantToolAgent — a deterministic tool-execution wrapper.

YOUR ONLY JOB:
1. Extract the stock ticker symbol from the user message.
2. Call quant_engine_tool with that ticker.
3. Return EXACTLY this format and NOTHING else:

QUANT_SNAPSHOT_GENERATED

Ticker: <ticker>
Regime: <regime>
Price:  <price>
ATR:    <atr>
RSI:    <rsi>
SMA50:  <sma50>
SMA200: <sma200>

RULES — STRICT:
• You MUST call quant_engine_tool. Do NOT skip the tool call.
• Do NOT add analysis, interpretation, commentary, or opinions.
• Do NOT rephrase or summarise the tool output beyond the format above.
• Do NOT hallucinate data — use ONLY values returned by the tool.
• If the tool call fails, return the error message verbatim.
"""

# ── Agent Definition ──────────────────────────────────────────────────────────
quant_tool_agent: LlmAgent = LlmAgent(
    name="QuantToolAgent",
    model=GEMINI_MODEL,
    description=(
        "Deterministic tool-wrapper that executes quant_engine_tool "
        "and writes the quant snapshot to session state."
    ),
    instruction=_INSTRUCTION,
    tools=[quant_engine_tool],
    output_key=KEY_QUANT_SNAPSHOT,
    generate_content_config=GenerateContentConfig(
        temperature=AGENT_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

logger.info(
    "QuantToolAgent initialized | model=%s | writes=%s",
    GEMINI_MODEL,
    KEY_QUANT_SNAPSHOT,
)

# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("QuantToolAgent initialized")
    print(f"Model: {GEMINI_MODEL}")
    print(f"Writes: {KEY_QUANT_SNAPSHOT}")
