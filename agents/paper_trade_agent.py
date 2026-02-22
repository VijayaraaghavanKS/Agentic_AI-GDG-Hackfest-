"""
agents/paper_trade_agent.py – Paper Trade Executor
=====================================================
Input: StrategyResult, candles, portfolio_value, risk_pct
Logic:
  - Get signal from strategy.get_signal(candles)
  - Position size = (portfolio_value * risk_pct) / (entry - stop)
  - Stop  = entry - 1R  (HARD FIX: not entry - 2 flat)
  - Target = entry + 2R  (HARD FIX: R:R = 2.0 always)
  - Log to paper_trades.json
Output: TradeRecord
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from core.models import Scenario, StrategyResult, TradeRecord
from strategy.strategies import ALL_STRATEGIES


_TRADES_PATH = Path(__file__).resolve().parent.parent / "memory" / "paper_trades.json"


def _log_trade(record: TradeRecord) -> None:
    """Append trade to paper_trades.json."""
    trades = []
    if _TRADES_PATH.exists():
        try:
            with open(_TRADES_PATH, "r", encoding="utf-8") as f:
                trades = json.load(f)
        except (json.JSONDecodeError, Exception):
            trades = []
    trades.append(record.to_dict())
    os.makedirs(_TRADES_PATH.parent, exist_ok=True)
    with open(_TRADES_PATH, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, default=str)


def execute(
    selected: StrategyResult,
    candles: pd.DataFrame,
    portfolio_value: float,
    scenario: Scenario,
    risk_pct: float = 0.01,
    ticker: str = "UNKNOWN",
) -> dict:
    """Execute a paper trade based on the selected strategy.

    Parameters
    ----------
    selected : StrategyResult
        The chosen strategy from the selector.
    candles : pd.DataFrame
        Full candle data for signal generation.
    portfolio_value : float
        Total portfolio equity in currency units.
    scenario : Scenario
        Current scenario (for record context).
    risk_pct : float
        Fraction of portfolio to risk per trade (default 1%).
    ticker : str
        Stock ticker symbol.

    Returns
    -------
    dict
        status, trade (TradeRecord or None), reason.
    """
    # No-trade short-circuit
    if selected.name == "no_trade":
        return {
            "status": "NO_TRADE",
            "trade": None,
            "reason": "Strategy is no_trade — preserving capital.",
        }

    # Get strategy instance
    strategy = ALL_STRATEGIES.get(selected.name)
    if strategy is None:
        return {
            "status": "ERROR",
            "trade": None,
            "reason": f"Unknown strategy: {selected.name}",
        }

    # Get signal
    signal = strategy.get_signal(candles)
    if signal is None:
        return {
            "status": "NO_SIGNAL",
            "trade": None,
            "reason": f"Strategy '{selected.name}' produced no signal on current candle.",
        }

    entry = signal["entry"]
    stop = signal["stop"]
    target = signal["target"]
    direction = signal.get("direction", "BUY")

    # ── Position sizing ───────────────────────────────────────────────────
    risk_per_share = abs(entry - stop)
    if risk_per_share <= 0:
        return {
            "status": "ERROR",
            "trade": None,
            "reason": "Risk per share is zero.",
        }

    # R:R check — MUST be 2.0
    reward = abs(target - entry)
    rr = round(reward / risk_per_share, 2)
    if rr < 1.9:  # allow tiny float imprecision
        return {
            "status": "SKIPPED",
            "trade": None,
            "reason": f"R:R = {rr} is below minimum 2.0.",
        }

    risk_amount = portfolio_value * risk_pct
    size = int(risk_amount / risk_per_share)
    if size <= 0:
        return {
            "status": "SKIPPED",
            "trade": None,
            "reason": "Position size is zero (insufficient capital for this stop distance).",
        }

    # ── Build trade record ────────────────────────────────────────────────
    record = TradeRecord(
        scenario_label=scenario.label,
        strategy_name=selected.name,
        regime_trend=scenario.regime.trend,
        regime_volatility=scenario.regime.volatility,
        news_bucket=scenario.sentiment.bucket,
        ticker=ticker,
        entry=round(entry, 2),
        stop=round(stop, 2),
        target=round(target, 2),
        size=size,
        risk_per_share=round(risk_per_share, 2),
        rr_ratio=rr,
    )

    # Log to file
    _log_trade(record)

    return {
        "status": "OPENED",
        "trade": record,
        "reason": f"{direction} {ticker} qty={size} entry={entry:.2f} stop={stop:.2f} target={target:.2f} R:R={rr}",
    }
