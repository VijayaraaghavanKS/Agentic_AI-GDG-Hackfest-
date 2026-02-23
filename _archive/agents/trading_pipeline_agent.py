"""
agents/trading_pipeline_agent.py – ADK SequentialAgent for the Regime-Aware Pipeline
======================================================================================
Exposes the full regime-aware trading workflow **visually** in the ADK Web UI
as a single ``SequentialAgent`` whose children run in strict pipeline order::

    quant_engine_tool
    → QuantAgent
    → SentimentAgent
    → BullAgent
    → BearAgent
    → CIOAgent
    → risk_enforcement_tool

Each sub-agent and tool is imported from its canonical module so that any
updates to individual agents are reflected here automatically.
"""

from __future__ import annotations

from google.adk.agents import SequentialAgent

from agents.quant_agent import quant_agent
from agents.sentiment_agent import sentiment_agent
from agents.bull_agent import bull_agent
from agents.bear_agent import bear_agent
from agents.cio_agent import cio_agent

from tools.quant_tool import quant_engine_tool
from tools.risk_tool import risk_enforcement_tool

# ── Sequential Pipeline Agent ────────────────────────────────────────────────

trading_pipeline_agent = SequentialAgent(
    name="RegimeAwareTradingPipeline",
    description=(
        "Full regime-aware trading workflow including "
        "QuantTool, QuantAgent, SentimentAgent, BullAgent, "
        "BearAgent, CIOAgent, and RiskTool."
    ),
    sub_agents=[
        quant_agent,
        sentiment_agent,
        bull_agent,
        bear_agent,
        cio_agent,
    ],
)

# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("TradingPipelineAgent ready")
