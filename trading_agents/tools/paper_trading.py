"""Paper trade execution and position sizing.

Delegates all risk math to ``trading_agents.risk_engine`` — the single
deterministic safety layer.  This module handles only portfolio I/O
(load / save / refresh) and the ADK-facing function signatures.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
from typing import Dict

from trading_agents.config import (
    ATR_STOP_MULTIPLIER,
    MAX_OPEN_TRADES,
)
from trading_agents.models import Position
from trading_agents.risk_engine import (
    apply_risk_limits,
    validate_trade_inputs,
    ValidatedTrade,
    _is_finite,
)
from trading_agents.tools.portfolio import load_portfolio, refresh_portfolio_positions, save_portfolio


def calculate_trade_plan_from_entry_stop(symbol: str, entry: float, stop: float) -> Dict:
    """Build a trade plan from explicit entry and stop (e.g. from dividend scan).

    Derives ATR from stop distance so that target = entry + 2R (2:1 R:R).
    Use this when you already have entry/stop from another source (e.g. dividend scanner).

    Args:
        symbol: Stock ticker.
        entry: Entry price.
        stop: Stop-loss price (must be < entry).

    Returns:
        dict with the trade plan details.
    """
    if not _is_finite(entry) or not _is_finite(stop):
        return {"status": "error", "error_message": f"Non-finite inputs: entry={entry}, stop={stop}"}
    if stop >= entry:
        return {"status": "error", "error_message": "Stop must be below entry."}
    atr = (entry - stop) / ATR_STOP_MULTIPLIER
    return calculate_trade_plan(symbol=symbol, close=entry, atr=atr)


def calculate_trade_plan(symbol: str, close: float, atr: float, regime: str = "") -> Dict:
    """Build a trade plan with entry, stop (1.5×ATR), target (2R), and position size.

    Delegates all risk math to ``risk_engine.apply_risk_limits``.

    Args:
        symbol: Stock ticker.
        close: Current closing price (entry price).
        atr: Average True Range for stop calculation.
        regime: Market regime (BULL/BEAR/SIDEWAYS). Optional — full size if empty.

    Returns:
        dict with the trade plan details.
    """
    if not _is_finite(close) or close <= 0:
        return {"status": "error", "error_message": f"Invalid close price: {close}"}
    if not _is_finite(atr) or atr <= 0:
        return {"status": "error", "error_message": f"Invalid ATR: {atr}"}

    portfolio = load_portfolio()

    proposal = {
        "ticker": symbol.upper(),
        "action": "BUY",
        "entry": close,
        "conviction_score": 0.7,  # default for plan-stage
        "regime": regime.upper().strip() if regime else "NEUTRAL",
    }

    try:
        trade: ValidatedTrade = apply_risk_limits(
            proposal, atr=atr, portfolio_equity=portfolio.cash,
        )
    except ValueError as exc:
        return {"status": "error", "error_message": str(exc)}

    if trade.killed:
        return {"status": "error", "error_message": trade.kill_reason or "Trade killed by risk engine."}

    return {
        "status": "success",
        "plan": {
            "symbol": trade.ticker,
            "entry": trade.entry_price,
            "stop": trade.stop_loss,
            "target": trade.target_price,
            "rr": trade.risk_reward_ratio,
            "qty": trade.position_size,
            "risk_amount": trade.total_risk,
            "capital_required": round(trade.position_size * trade.entry_price, 2),
            "regime": trade.regime,
            "contrarian": trade.is_contrarian,
        },
    }


def execute_paper_trade(symbol: str, entry: float, stop: float, target: float, qty: int, regime: str = "") -> Dict:
    """Execute a paper trade: validate via risk engine, update portfolio, persist state.

    Delegates validation to ``risk_engine.validate_trade_inputs`` and applies
    regime-aware contrarian sizing via ``risk_engine.apply_risk_limits``.

    Args:
        symbol: Stock ticker.
        entry: Entry price.
        stop: Stop-loss price.
        target: Target price.
        qty: Number of shares.
        regime: Market regime (BULL/BEAR/SIDEWAYS). Optional.

    Returns:
        dict with execution result and updated portfolio summary.
    """
    # --- Deterministic risk gate (from risk_engine) --------
    err = validate_trade_inputs(entry, stop, target)
    if err:
        return {"status": "REJECTED", "reason": err}

    # Refresh lifecycle first so stale trades can close and free capacity.
    refresh_portfolio_positions()
    portfolio = load_portfolio()

    if len(portfolio.open_positions) >= MAX_OPEN_TRADES:
        return {"status": "REJECTED", "reason": f"Already at max {MAX_OPEN_TRADES} open trades."}

    # Use risk engine for sizing & contrarian penalty
    atr = (entry - stop) / ATR_STOP_MULTIPLIER  # back-derive ATR
    proposal = {
        "ticker": symbol.upper(),
        "action": "BUY",
        "entry": entry,
        "target": target,
        "conviction_score": 0.7,
        "regime": regime.upper().strip() if regime else "NEUTRAL",
    }
    try:
        validated: ValidatedTrade = apply_risk_limits(
            proposal, atr=atr, portfolio_equity=portfolio.cash,
        )
    except ValueError as exc:
        return {"status": "REJECTED", "reason": str(exc)}

    if validated.killed:
        return {"status": "REJECTED", "reason": validated.kill_reason or "Killed by risk engine."}

    # Engine may adjust qty via contrarian penalty; honour its sizing but
    # allow caller to override to a SMALLER qty.
    qty = min(qty, validated.position_size) if qty > 0 else validated.position_size
    is_contrarian = validated.is_contrarian
    rr = validated.risk_reward_ratio

    capital_needed = qty * entry
    if capital_needed > portfolio.cash:
        qty = int(portfolio.cash / entry)
        if qty <= 0:
            return {"status": "REJECTED", "reason": "Insufficient cash."}
        capital_needed = qty * entry

    portfolio.cash -= capital_needed
    now_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    portfolio.open_positions.append(
        Position(
            symbol=symbol.upper(),
            qty=qty,
            entry=entry,
            stop=stop,
            target=target,
            opened_at=now_str,
        )
    )
    action = f"OPEN {symbol.upper()} qty={qty} entry={entry:.2f} stop={stop:.2f} target={target:.2f}"
    if is_contrarian:
        action += " (CONTRARIAN — 50% size)"
    portfolio.actions_log.append(f"[{now_str}] {action}")

    save_portfolio(portfolio)

    return {
        "status": "OPENED",
        "symbol": symbol.upper(),
        "qty": qty,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_reward": round(rr, 2),
        "cash_remaining": round(portfolio.cash, 2),
        "open_positions_count": len(portfolio.open_positions),
        "contrarian": is_contrarian,
    }
