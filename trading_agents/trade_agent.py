"""Trade execution sub-agent -- calculates plans and executes paper trades."""

from __future__ import annotations

from typing import Dict

from google.adk.agents import Agent

from trading_agents.config import GEMINI_MODEL
from trading_agents.tools.paper_trading import calculate_trade_plan, execute_paper_trade


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
        "Calculates trade plans with proper position sizing and executes paper trades. "
        "Enforces risk rules: 1% risk per trade, max 3 open positions, min 1:2 R:R."
    ),
    instruction=(
        "You are the Trade Executor. When asked to trade a stock, "
        "first use plan_trade to calculate entry/stop/target/qty, "
        "then present the plan for confirmation before using execute_trade. "
        "Never execute without showing the plan first. "
        "Always mention: symbol, entry, stop, target, qty, R:R ratio, and capital required. "
        "If risk rules block the trade, explain why clearly."
    ),
    tools=[plan_trade, execute_trade],
)
