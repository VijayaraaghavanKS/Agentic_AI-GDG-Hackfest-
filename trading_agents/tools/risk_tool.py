"""ADK tool wrapper for the deterministic risk engine.

This is the **final gate** before trade execution.  The LLM calls
``enforce_risk_limits`` and gets back a fully-validated trade dict
with position size, stop-loss, target, and risk-reward already
computed.  The LLM CANNOT override the engine's decisions.

Usage (by trade_executor or risk_agent):
    result = enforce_risk_limits(
        symbol="RELIANCE.NS",
        action="BUY",
        entry=2800.0,
        atr=30.0,
        conviction=0.7,
        regime="BULL",
        target=3100.0,      # optional — engine computes 2R default
        portfolio_equity=0,  # 0 = use current portfolio cash
    )
"""

from __future__ import annotations

import logging
from typing import Dict

from trading_agents.risk_engine import apply_risk_limits, ValidatedTrade
from trading_agents.tools.portfolio import load_portfolio

logger = logging.getLogger(__name__)


def enforce_risk_limits(
    symbol: str,
    action: str,
    entry: float,
    atr: float,
    conviction: float = 0.7,
    regime: str = "NEUTRAL",
    target: float = 0.0,
    portfolio_equity: float = 0.0,
) -> Dict:
    """Enforce deterministic risk limits on a trade proposal.

    This is an ADK-compatible function tool.  It wraps the pure-Python
    ``risk_engine.apply_risk_limits()`` so agents can call it.

    Args:
        symbol: Stock ticker (e.g. RELIANCE.NS).
        action: BUY, SELL, or HOLD.
        entry: Entry price (must be > 0).
        atr: Average True Range (must be > 0).
        conviction: Conviction score 0-1 (or 0-100, auto-normalised).
        regime: Market regime (BULL / BEAR / SIDEWAYS / NEUTRAL).
        target: Target price. 0 = let engine compute 2R target.
        portfolio_equity: Portfolio equity in INR. 0 = read from portfolio file.

    Returns:
        dict with all ValidatedTrade fields plus a human-readable ``summary``.
    """
    # Default equity from live portfolio if not supplied
    if portfolio_equity <= 0:
        try:
            portfolio_equity = load_portfolio().cash
        except Exception:
            from trading_agents.config import INITIAL_CAPITAL
            portfolio_equity = INITIAL_CAPITAL

    proposal: dict = {
        "ticker": symbol.upper(),
        "action": action.upper().strip(),
        "entry": entry,
        "conviction_score": conviction,
        "regime": regime.upper().strip() or "NEUTRAL",
    }
    if target > 0:
        proposal["target"] = target

    try:
        trade: ValidatedTrade = apply_risk_limits(
            proposal, atr=atr, portfolio_equity=portfolio_equity,
        )
    except ValueError as exc:
        logger.error("[%s] Risk enforcement ValueError: %s", symbol, exc)
        return {"status": "ERROR", "error": str(exc)}

    result = trade.to_dict()

    # Add a human-friendly summary line
    if trade.killed:
        result["status"] = "REJECTED"
        result["summary"] = (
            f"REJECTED {trade.ticker} {trade.action} — {trade.kill_reason}"
        )
    else:
        result["status"] = "ACCEPTED"
        result["summary"] = (
            f"ACCEPTED {trade.ticker} {trade.action} "
            f"qty={trade.position_size} entry={trade.entry_price:.2f} "
            f"stop={trade.stop_loss:.2f} target={trade.target_price:.2f} "
            f"R:R={trade.risk_reward_ratio:.1f}"
            f"{' (CONTRARIAN 50% size)' if trade.is_contrarian else ''}"
        )

    return result
