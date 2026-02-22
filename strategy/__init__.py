"""
strategy/ – Trading Strategy Layer
====================================
Deterministic strategy building blocks:
  - strategies: BaseStrategy + 4 concrete strategies
  - scenario_builder: maps regime+indicators to scenarios
  - backtester: quick 30-candle walk-forward backtest
  - selector: picks best strategy from memory
"""

from .strategies import (
    BaseStrategy,
    BreakoutStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    NoTradeStrategy,
    ALL_STRATEGIES,
)

from .scenario_builder import build_scenario
from .backtester import backtest_strategy

# Alias for compatibility
quick_backtest = backtest_strategy

__all__ = [
    "BaseStrategy",
    "BreakoutStrategy",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "NoTradeStrategy",
    "ALL_STRATEGIES",
    "build_scenario",
    "backtest_strategy",
    "quick_backtest",
]
