"""
agents/strategy_agent.py – Candidate Strategy Selector
========================================================
Input: Scenario
Logic: maps scenario label → list of candidate BaseStrategy instances
Output: list[BaseStrategy]
"""

from __future__ import annotations

from typing import List

from core.models import Scenario
from strategy.strategies import (
    BaseStrategy,
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NoTradeStrategy,
)


# Scenario label prefix → ordered candidate strategies
_SCENARIO_CANDIDATES: dict[str, list[type]] = {
    "bull_positive":       [BreakoutStrategy, MeanReversionStrategy],
    "bull_neutral":        [BreakoutStrategy, MeanReversionStrategy],
    "bull_negative":       [MeanReversionStrategy, BreakoutStrategy],
    "sideways_positive":   [MeanReversionStrategy, BreakoutStrategy],
    "sideways_neutral":    [MeanReversionStrategy],
    "sideways_negative":   [MomentumStrategy, MeanReversionStrategy],
    "bear_positive":       [MeanReversionStrategy, MomentumStrategy],
    "bear_neutral":        [MomentumStrategy],
    "bear_negative":       [MomentumStrategy],
}


def analyze(scenario: Scenario) -> dict:
    """Map scenario label to candidate strategy instances.

    If scenario has ``_danger`` suffix, only NoTradeStrategy is returned.

    Returns
    -------
    dict
        status, candidates (list[BaseStrategy]).
    """
    label = scenario.label

    # Danger override → no_trade only
    if label.endswith("_danger"):
        return {
            "status": "success",
            "candidates": [NoTradeStrategy()],
            "reason": "danger_override",
        }

    # Look up base label (strip _danger if present, though handled above)
    base_label = label.replace("_danger", "")
    strategy_classes = _SCENARIO_CANDIDATES.get(base_label, [MeanReversionStrategy])

    # Instantiate + always include NoTradeStrategy as fallback
    candidates: List[BaseStrategy] = [cls() for cls in strategy_classes]
    candidates.append(NoTradeStrategy())

    return {
        "status": "success",
        "candidates": candidates,
    }
