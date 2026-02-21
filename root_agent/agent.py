"""
root_agent/agent.py – ADK Sequential Root Agent
=================================================
Exposes the full regime-aware trading pipeline as a ``SequentialAgent``
so the ADK Web UI renders every step in the graph.

Run with::

    adk web .

Pipeline order (7 steps)::

    QuantToolAgent  →  QuantAgent  →  SentimentAgent  →  BullAgent
    →  BearAgent  →  CIOAgent  →  RiskToolAgent

ADK UI will display::

    root_agent
    ├── QuantToolAgent        └── quant_engine_tool
    ├── QuantAgent
    ├── SentimentAgent        └── google_search
    ├── BullAgent
    ├── BearAgent
    ├── CIOAgent
    └── RiskToolAgent         └── risk_enforcement_tool
"""

from __future__ import annotations

import logging

from google.adk.agents import SequentialAgent

from agents.quant_tool_agent import quant_tool_agent
from agents.quant_agent import quant_agent
from agents.sentiment_agent import sentiment_agent
from agents.bull_agent import bull_agent
from agents.bear_agent import bear_agent
from agents.cio_agent import cio_agent
from agents.risk_tool_agent import risk_tool_agent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

# ── Root Agent ────────────────────────────────────────────────────────────────

root_agent = SequentialAgent(
    name="root_agent",
    description=(
        "Regime-Aware Trading Pipeline — sequentially executes "
        "QuantToolAgent, QuantAgent, SentimentAgent, BullAgent, "
        "BearAgent, CIOAgent, and RiskToolAgent."
    ),
    sub_agents=[
        quant_tool_agent,
        quant_agent,
        sentiment_agent,
        bull_agent,
        bear_agent,
        cio_agent,
        risk_tool_agent,
    ],
)

logger.info("Sequential root_agent initialized with %d sub-agents", len(root_agent.sub_agents))

# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Sequential root agent ready")
