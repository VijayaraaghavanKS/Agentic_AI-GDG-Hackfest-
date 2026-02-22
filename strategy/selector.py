"""
strategy/selector.py – Strategy Selector with Memory Bias
============================================================
Scores each backtested strategy by combining metrics with historical
memory of what worked in similar scenarios.

Composite score formula:
    composite = (0.4 * sharpe) + (0.3 * win_rate) + (0.2 * avg_return_scaled)
                - (0.1 * max_drawdown)

Then multiplied by the memory_bias (0.5–1.5) for this scenario+strategy.

If all composite_scores < 0.3 threshold → return no_trade.
"""

from __future__ import annotations

from typing import List

from core.models import Scenario, StrategyResult
from memory.trade_memory import TradeMemory


COMPOSITE_THRESHOLD = 0.3


def select_strategy(
    results: List[StrategyResult],
    memory: TradeMemory,
    scenario: Scenario,
) -> StrategyResult:
    """Select the best strategy based on backtest results + memory bias.

    Parameters
    ----------
    results : list[StrategyResult]
        From ``backtester.score_strategies()``.
    memory : TradeMemory
        For historical bias lookup.
    scenario : Scenario
        Current scenario (provides label for memory lookup).

    Returns
    -------
    StrategyResult
        The winner, with ``composite_score`` filled in.
        If no strategy exceeds threshold, returns a no_trade result.
    """
    for r in results:
        if r.name == "no_trade":
            r.composite_score = 0.0
            continue

        # Base composite score
        # Scale avg_return to 0-1 range (assuming daily returns are small)
        avg_return_scaled = min(1.0, max(0.0, r.avg_return * 100))

        composite = (
            0.4 * r.sharpe
            + 0.3 * r.win_rate
            + 0.2 * avg_return_scaled
            - 0.1 * r.max_drawdown
        )

        # Apply memory bias
        bias = memory.memory_bias(scenario.label, r.name)
        composite *= bias

        r.composite_score = round(composite, 4)

    # Sort by composite score descending
    scored = sorted(results, key=lambda r: r.composite_score, reverse=True)

    # Check if the best exceeds threshold
    best = scored[0]
    if best.composite_score < COMPOSITE_THRESHOLD or best.name == "no_trade":
        return StrategyResult(
            name="no_trade",
            win_rate=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
            composite_score=0.0,
        )

    return best
