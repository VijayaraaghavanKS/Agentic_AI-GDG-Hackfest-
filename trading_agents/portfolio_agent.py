"""Portfolio manager sub-agent -- queries and manages paper portfolio state."""

from __future__ import annotations

from typing import Dict

from google.adk.agents import Agent

from trading_agents.config import GEMINI_MODEL
from trading_agents.tools.portfolio import get_portfolio_summary, reset_portfolio


def view_portfolio() -> Dict:
    """Get the current paper portfolio summary including cash, positions, and PnL.

    Returns:
        dict with full portfolio overview.
    """
    return get_portfolio_summary()


def reset_paper_portfolio() -> Dict:
    """Reset the paper portfolio to its initial state (INR 10,00,000 cash, no positions).

    Returns:
        dict confirming the reset.
    """
    return reset_portfolio()


portfolio_agent = Agent(
    name="portfolio_manager",
    model=GEMINI_MODEL,
    description=(
        "Manages and reports on the paper trading portfolio. "
        "Shows current holdings, cash balance, invested amount, and trade history."
    ),
    instruction=(
        "You are the Portfolio Manager. When asked about the portfolio, "
        "use view_portfolio to show current state. "
        "Format amounts in INR with proper formatting (e.g., INR 10,00,000). "
        "Show each open position with symbol, qty, entry, stop, target. "
        "Only reset the portfolio when explicitly asked."
    ),
    tools=[view_portfolio, reset_paper_portfolio],
)
