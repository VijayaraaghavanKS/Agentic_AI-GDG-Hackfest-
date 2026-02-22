"""
agents/selector_agent.py – Strategy Selector
===============================================
Input: list[StrategyResult], Scenario, TradeMemory
Logic: calls selector.select_strategy()
Output: StrategyResult (the winner)
"""

from __future__ import annotations

from typing import List

from core.models import Scenario, StrategyResult
from memory.trade_memory import TradeMemory
from strategy.selector import select_strategy


def analyze(
    results: List[StrategyResult],
    scenario: Scenario,
    memory: TradeMemory,
) -> dict:
    """Select the best strategy.

    Returns
    -------
    dict
        status, selected (StrategyResult).
    """
    selected = select_strategy(results, memory, scenario)
    return {
        "status": "success",
        "selected": selected,
    }
