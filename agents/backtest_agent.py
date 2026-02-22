"""
agents/backtest_agent.py – Quick Backtest Scorer
==================================================
Input: list[BaseStrategy], candles
Logic: calls backtester.score_strategies()
Output: list[StrategyResult]
"""

from __future__ import annotations

from typing import List

import pandas as pd

from core.models import StrategyResult
from strategy.strategies import BaseStrategy
from strategy.backtester import score_strategies


def analyze(strategies: List[BaseStrategy], candles: pd.DataFrame) -> dict:
    """Backtest all candidate strategies.

    Returns
    -------
    dict
        status, results (list[StrategyResult]).
    """
    results = score_strategies(strategies, candles, lookback=30)
    return {
        "status": "success",
        "results": results,
    }
