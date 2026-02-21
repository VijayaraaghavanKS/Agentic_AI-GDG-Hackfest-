"""
agents/agent.py – ADK Entry Point
===================================
The `adk web` and `adk run` commands look for a variable named `root_agent`
in this exact file: <agents_dir>/agent.py

This file wires the three specialist agents into a single SequentialAgent
pipeline and exposes it as `root_agent` for the ADK dev UI.

Run with:
    adk web .           (from the repo root)  ← serves the ADK dev console
    adk run agents      (headless CLI test)
"""

from google.adk.agents import SequentialAgent, ParallelAgent

from .researcher import researcher_agent
from .analyst import analyst_agent
from .decision_maker import decision_agent

import sys
import os

# Allow config.py to be found when ADK imports this module directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PIPELINE_MODE

# ── Pipeline Factory ──────────────────────────────────────────────────────────

def _build_root_agent():
    if PIPELINE_MODE == "parallel":
        # Researcher and Analyst run in parallel; DecisionMaker waits for both.
        pre_stage = ParallelAgent(
            name="ResearchAndAnalysis",
            sub_agents=[researcher_agent, analyst_agent],
        )
        return SequentialAgent(
            name="TradingPipeline",
            description=(
                "Autonomous stock trading agent: parallel research + analysis, "
                "then final BUY/SELL/HOLD decision."
            ),
            sub_agents=[pre_stage, decision_agent],
        )

    # Default: sequential  Researcher → Analyst → DecisionMaker
    return SequentialAgent(
        name="TradingPipeline",
        description=(
            "Autonomous stock trading agent: research → technical analysis → "
            "BUY/SELL/HOLD decision for NSE/BSE equities."
        ),
        sub_agents=[researcher_agent, analyst_agent, decision_agent],
    )


# ── This is the variable the ADK CLI looks for ───────────────────────────────
root_agent = _build_root_agent()
