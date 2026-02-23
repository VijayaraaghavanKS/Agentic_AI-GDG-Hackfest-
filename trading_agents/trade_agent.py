"""Trade execution sub-agent -- calculates plans, enforces risk limits, and executes paper trades."""

from __future__ import annotations

from typing import Dict

from google.adk.agents import Agent

from trading_agents.config import GEMINI_MODEL
from trading_agents.tools.paper_trading import (
    calculate_trade_plan,
    calculate_trade_plan_from_entry_stop,
    execute_paper_trade,
)
from trading_agents.tools.risk_tool import enforce_risk_limits


def plan_trade(symbol: str, close: float, atr: float) -> Dict:
    """Calculate a trade plan with entry, stop, target, position size, and risk amount.

    Args:
        symbol: Stock ticker symbol.
        close: Current closing price to use as entry.
        atr: Average True Range for stop-loss calculation.

    Returns:
        dict with the complete trade plan or error.
    """
    return calculate_trade_plan(symbol=symbol, close=close, atr=atr)


def plan_trade_from_dividend(symbol: str, entry: float, stop: float) -> Dict:
    """Calculate a trade plan using entry and stop from a scan (dividend or oversold bounce).

    Use when implementing a dividend pick OR an oversold bounce pick: pass the scan's
    entry (close/suggested_entry) and stop (suggested_stop). Target = 2R (entry + 2 * risk).

    Args:
        symbol: Stock ticker (e.g. ENGINERSIN.NS or RELIANCE.NS).
        entry: Entry price (scan's close or suggested_entry).
        stop: Stop-loss (scan's suggested_stop).

    Returns:
        dict with the complete trade plan or error.
    """
    return calculate_trade_plan_from_entry_stop(symbol=symbol, entry=entry, stop=stop)


def check_risk(symbol: str, action: str, entry: float, atr: float,
               conviction: float = 0.7, regime: str = "NEUTRAL",
               target: float = 0.0) -> Dict:
    """Run the deterministic risk engine on a proposed trade BEFORE execution.

    Returns a validated trade with engine-computed stop, target, position size,
    risk-reward ratio, and ACCEPTED/REJECTED status.  The LLM cannot override
    this verdict.

    Args:
        symbol: Stock ticker.
        action: BUY, SELL, or HOLD.
        entry: Entry price.
        atr: Average True Range.
        conviction: Conviction score (0-1 or 0-100).
        regime: Market regime (BULL/BEAR/SIDEWAYS/NEUTRAL).
        target: Target price (0 = let engine compute 2R target).

    Returns:
        dict with all ValidatedTrade fields, status, and summary.
    """
    return enforce_risk_limits(
        symbol=symbol, action=action, entry=entry, atr=atr,
        conviction=conviction, regime=regime, target=target,
    )


def execute_trade(symbol: str, entry: float, stop: float, target: float, qty: int) -> Dict:
    """Execute a paper trade after validating risk rules.

    Args:
        symbol: Stock ticker symbol.
        entry: Entry price.
        stop: Stop-loss price.
        target: Target price.
        qty: Number of shares to buy.

    Returns:
        dict with execution result and portfolio impact.
    """
    return execute_paper_trade(symbol=symbol, entry=entry, stop=stop, target=target, qty=qty)


trade_agent = Agent(
    name="trade_executor",
    model=GEMINI_MODEL,
    description=(
        "Calculates trade plans, enforces deterministic risk limits, and executes paper trades. "
        "Risk engine: 1% risk per trade, ATR-based stops, contrarian regime penalty (50% size), "
        "min 2:1 R:R, max 3 open positions. "
        "Supports generic plans (plan_trade) and scan-based entry/stop (plan_trade_from_dividend)."
    ),
    instruction=(
        "You are the Trade Executor with a built-in Risk Engine.\n\n"
        "WORKFLOW (MANDATORY ORDER):\n"
        "1. PLAN: compute a plan (plan_trade or plan_trade_from_dividend).\n"
        "2. RISK CHECK: call check_risk(symbol, action, entry, atr, conviction, regime, target) "
        "   to get the deterministic risk engine verdict.  If status is REJECTED, STOP — "
        "   present the rejection reason and do NOT execute.\n"
        "3. PRESENT: show the plan + risk verdict to the user.\n"
        "4. EXECUTE: only after step 2 returns ACCEPTED, call execute_trade.\n\n"
        "WHICH PLANNING TOOL TO USE:\n"
        "- Dividend pick  → plan_trade_from_dividend(symbol, suggested_entry, suggested_stop)\n"
        "- Oversold bounce → plan_trade_from_dividend(symbol, close, suggested_stop)\n"
        "- Breakout/momentum → plan_trade(symbol, close, atr)\n\n"
        "RISK ENGINE FIELDS (from check_risk):\n"
        "- entry_price, stop_loss, target_price, position_size, risk_per_share\n"
        "- risk_reward_ratio, total_risk, is_contrarian, killed, kill_reason\n"
        "- The engine computes its own ATR-based stop; it may differ from the plan.\n"
        "- Contrarian trades (BUY in BEAR) get 50% position size automatically.\n\n"
        "RULES:\n"
        "- NEVER execute without calling check_risk first.\n"
        "- NEVER override the engine's REJECTED verdict.\n"
        "- Always show: symbol, entry, stop, target, qty, R:R, capital required, "
        "  and whether it's contrarian."
    ),
    tools=[plan_trade, plan_trade_from_dividend, check_risk, execute_trade],
)
