"""
agents/memory_agent.py – Trade Memory Interface
==================================================
Input: TradeRecord (after outcome is known)
Logic: calls TradeMemory.store(record) and provides get_similar()
Output: confirmation + updated memory stats
"""

from __future__ import annotations

from typing import Optional

from core.models import TradeRecord
from memory.trade_memory import TradeMemory


# Shared instance
_memory: Optional[TradeMemory] = None


def _get_memory() -> TradeMemory:
    global _memory
    if _memory is None:
        _memory = TradeMemory()
    return _memory


def store_trade(record: TradeRecord) -> dict:
    """Store a trade record to memory.

    Returns
    -------
    dict
        status, memory_stats.
    """
    memory = _get_memory()
    memory.store(record)
    return {
        "status": "success",
        "action": "stored",
        "memory_stats": memory.stats(),
    }


def update_outcome(
    ticker: str,
    exit_price: float,
    outcome: str,
    pnl_pct: float,
    closed_at: str,
) -> dict:
    """Update an open trade's outcome in memory.

    Returns
    -------
    dict
        status, updated trade or not_found message.
    """
    memory = _get_memory()
    result = memory.update_outcome(ticker, exit_price, outcome, pnl_pct, closed_at)
    if result is None:
        return {"status": "not_found", "message": f"No open trade for {ticker}"}
    return {
        "status": "success",
        "updated_trade": result,
        "memory_stats": memory.stats(),
    }


def get_similar(scenario_label: str, strategy_name: str) -> dict:
    """Get historical trades for this scenario+strategy.

    Returns
    -------
    dict
        status, similar trades, memory_bias.
    """
    memory = _get_memory()
    similar = memory.get_similar(scenario_label, strategy_name)
    bias = memory.memory_bias(scenario_label, strategy_name)
    return {
        "status": "success",
        "count": len(similar),
        "memory_bias": bias,
        "trades": similar,
    }


def get_stats() -> dict:
    """Return overall memory stats."""
    return _get_memory().stats()
