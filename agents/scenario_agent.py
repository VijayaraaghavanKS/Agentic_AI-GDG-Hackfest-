"""
agents/scenario_agent.py – Scenario Detector
==============================================
Thin wrapper: calls scenario_builder.build_scenario(regime, sentiment).
Output: Scenario
"""

from __future__ import annotations

from core.models import MarketRegime, NewsSentiment, Scenario
from strategy.scenario_builder import build_scenario


def analyze(regime: MarketRegime, sentiment: NewsSentiment) -> dict:
    """Build scenario from regime + sentiment.

    Returns
    -------
    dict
        status, scenario (Scenario).
    """
    scenario = build_scenario(regime, sentiment)
    return {
        "status": "success",
        "scenario": scenario,
    }
