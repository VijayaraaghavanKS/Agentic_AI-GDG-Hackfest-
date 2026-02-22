"""
agents/agent.py – ADK Entry Point
===================================
The `adk web` and `adk run` commands look for a variable named `root_agent`
in this exact file: <agents_dir>/agent.py

This file wires the four Regime-Aware Trading agents into a SequentialAgent
pipeline and exposes it as `root_agent` for the ADK dev UI.

Pipeline (6 steps):
    Step 1: quant_tool       → Regime snapshot (via tools/quant_tool.py)
    Step 2: sentiment_agent  → News + macro sentiment
    Step 3: bull_agent       → Bullish thesis
    Step 4: bear_agent       → Counter-thesis
    Step 5: cio_agent        → Synthesises debate → raw trade proposal
    Step 6: risk_tool        → ATR stop-loss + 1% position sizing

Run with:
    adk web .           (from the repo root)  ← serves the ADK dev console
    adk run agents      (headless CLI test)
"""

import sys
import os

# Allow config.py and pipeline/ to be found when ADK imports this module directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import SequentialAgent

from .sentiment_agent import sentiment_agent
from .bull_agent import bull_agent
from .bear_agent import bear_agent
from .cio_agent import cio_agent

# ── Root Agent ────────────────────────────────────────────────────────────────
# Steps 1 (quant_tool) and 6 (risk_tool) are function tools called by the LLM
# agents, not standalone agents, so the sequential pipeline covers Steps 2-5.
# quant_tool is invoked first by sentiment_agent; risk_tool is invoked last
# by cio_agent before it writes KEY_FINAL_TRADE.

root_agent = SequentialAgent(
    name="RegimeAwareTradingPipeline",
    description=(
        "Regime-Aware Trading Command Center: "
        "Sentiment → Bull thesis → Bear thesis → CIO decision "
        "with ATR-based risk management for NSE/BSE equities."
    ),
    sub_agents=[
        sentiment_agent,   # Step 2: news + macro sentiment
        bull_agent,        # Step 3: bullish thesis using quant + sentiment
        bear_agent,        # Step 4: skeptical counter-thesis
        cio_agent,         # Step 5+6: synthesis + risk-validated trade
    ],
)
