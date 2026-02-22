"""
strategy/backtester.py – Quick Walk-Forward Backtest
======================================================
Runs each strategy's ``get_signal()`` on a rolling window of the last
30 candles and computes per-strategy metrics.
"""

from __future__ import annotations

import math
from typing import List

import pandas as pd

from core.models import StrategyResult
from strategy.strategies import BaseStrategy


def backtest_strategy(
    strategy: BaseStrategy,
    candles: pd.DataFrame,
    lookback: int = 30,
) -> StrategyResult:
    """Walk-forward backtest of a single strategy.

    For each of the last *lookback* candles, run get_signal() on all
    preceding data and check if the next candle would have hit stop
    or target.

    Parameters
    ----------
    strategy : BaseStrategy
    candles : pd.DataFrame
        Full candle history (columns: open, high, low, close, volume).
    lookback : int
        Number of recent bars to test.

    Returns
    -------
    StrategyResult
    """
    n = len(candles)
    if n < lookback + 20:
        return StrategyResult(
            name=strategy.name,
            win_rate=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
        )

    # No-trade always returns zeros
    if strategy.name == "no_trade":
        return StrategyResult(
            name="no_trade",
            win_rate=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
        )

    returns: list[float] = []
    equity = 1.0
    peak = 1.0
    max_dd = 0.0

    start_idx = n - lookback

    for i in range(start_idx, n - 1):
        # Use all data up to candle i (inclusive) for signal generation
        window = candles.iloc[: i + 1].copy()
        signal = strategy.get_signal(window)

        if signal is None:
            returns.append(0.0)
            continue

        entry = signal["entry"]
        stop = signal["stop"]
        target = signal["target"]
        direction = signal.get("direction", "BUY")

        # Check outcome on the NEXT candle
        next_candle = candles.iloc[i + 1]
        next_high = float(next_candle["high"])
        next_low = float(next_candle["low"])
        next_close = float(next_candle["close"])

        if direction == "BUY":
            risk = entry - stop
            if risk <= 0:
                returns.append(0.0)
                continue
            # Check stop hit first (conservative)
            if next_low <= stop:
                ret = -risk / entry
            elif next_high >= target:
                ret = (target - entry) / entry
            else:
                ret = (next_close - entry) / entry
        else:  # SELL (short)
            risk = stop - entry
            if risk <= 0:
                returns.append(0.0)
                continue
            if next_high >= stop:
                ret = -risk / entry
            elif next_low <= target:
                ret = (entry - target) / entry
            else:
                ret = (entry - next_close) / entry

        returns.append(ret)

        # Track equity and drawdown
        equity *= (1 + ret)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    # ── Compute metrics ───────────────────────────────────────────────────
    if not returns:
        return StrategyResult(
            name=strategy.name,
            win_rate=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
        )

    active = [r for r in returns if r != 0.0]
    if not active:
        return StrategyResult(
            name=strategy.name,
            win_rate=0.0,
            avg_return=0.0,
            max_drawdown=0.0,
            sharpe=0.0,
        )

    wins = sum(1 for r in active if r > 0)
    win_rate = wins / len(active)
    avg_return = sum(active) / len(active)

    # Sharpe ratio (annualised, assuming daily candles)
    mean_r = sum(returns) / len(returns)
    var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
    std_r = math.sqrt(var_r) if var_r > 0 else 1e-9
    sharpe = (mean_r / std_r) * math.sqrt(252)

    return StrategyResult(
        name=strategy.name,
        win_rate=round(win_rate, 4),
        avg_return=round(avg_return, 6),
        max_drawdown=round(max_dd, 4),
        sharpe=round(sharpe, 4),
    )


def score_strategies(
    strategies: List[BaseStrategy],
    candles: pd.DataFrame,
    lookback: int = 30,
) -> List[StrategyResult]:
    """Backtest all strategies and return sorted results.

    Parameters
    ----------
    strategies : list[BaseStrategy]
    candles : pd.DataFrame
    lookback : int

    Returns
    -------
    list[StrategyResult]
        Sorted by composite_score descending (filled by selector later).
    """
    results = [backtest_strategy(s, candles, lookback) for s in strategies]
    return results
