"""
agents/quant_agent.py – The Quant Analyst Agent (ADK Agent – Step 2)
=====================================================================
PIPELINE STEP: 2 (between quant_tool and SentimentAgent)

RESPONSIBILITY:
    - Interpret the deterministic quant snapshot produced by
      ``tools/quant_tool.py`` into professional, human-readable analysis.
    - Reason about trend, momentum, volatility, RSI, regime, and risk
      conditions using ONLY the provided numbers.

READS FROM STATE:
    - KEY_QUANT_SNAPSHOT  (RegimeSnapshot dict from Step 1)

WRITES TO STATE:
    - KEY_QUANT_ANALYSIS  (structured textual analysis)

CRITICAL CONSTRAINTS:
    - NEVER computes indicators or risk metrics.
    - NEVER calls tools (tools=[]).
    - NEVER invents or overrides deterministic values.
    - Performs reasoning / interpretation ONLY.
"""

from __future__ import annotations

import logging

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig

from config import GEMINI_MODEL, AGENT_TEMPERATURE, MAX_OUTPUT_TOKENS
from pipeline.session_keys import KEY_QUANT_SNAPSHOT, KEY_QUANT_ANALYSIS

# ── Module-level logger ────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── System Instruction ─────────────────────────────────────────────────────────
_INSTRUCTION: str = """\
You are a professional quantitative analyst.

You interpret deterministic trading metrics.

You NEVER invent numbers.

You ONLY interpret the provided quant snapshot.

You NEVER calculate indicators.

You NEVER estimate risk mathematically.

You NEVER override deterministic values.

Use ONLY the provided numbers.


The quant snapshot for interpretation:
{quant_snapshot}


Interpret:
• Trend condition (price vs SMA50 vs SMA200)
• Momentum strength (momentum_20d)
• Volatility environment (volatility)
• RSI condition
• Regime explanation
• Trading risk environment


Output EXACTLY this format:

QUANT_ANALYSIS:

Trend:
<analysis>

Momentum:
<analysis>

Volatility:
<analysis>

RSI:
<analysis>

Regime:
<analysis>

Risk Conditions:
<analysis>

Overall Quant View:
<analysis>
"""

# ── Agent Definition ───────────────────────────────────────────────────────────
quant_agent: LlmAgent = LlmAgent(
    name="QuantAgent",
    model=GEMINI_MODEL,
    description="Interprets deterministic quant snapshot into professional analysis",
    instruction=_INSTRUCTION,
    tools=[],
    output_key=KEY_QUANT_ANALYSIS,
    generate_content_config=GenerateContentConfig(
        temperature=AGENT_TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
)

logger.info(
    "QuantAgent initialized | model=%s | reads=%s | writes=%s",
    GEMINI_MODEL,
    KEY_QUANT_SNAPSHOT,
    KEY_QUANT_ANALYSIS,
)

# ── Standalone Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"QuantAgent initialized")
    print(f"Model: {GEMINI_MODEL}")
    print(f"Reads: {KEY_QUANT_SNAPSHOT}")
    print(f"Writes: {KEY_QUANT_ANALYSIS}")
