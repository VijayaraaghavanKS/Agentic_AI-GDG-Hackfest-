"""
main.py – Regime-Aware Trading Pipeline (CLI Entry Point)
===========================================================
Runs the full 6-step pipeline from the command line for a single ticker.

Usage:
    python main.py                          # Run for first ticker in WATCH_LIST
    python main.py --ticker RELIANCE.NS     # Run for a specific ticker
    python main.py --equity 500000          # Custom portfolio equity

Pipeline Steps:
    1. Quant Engine (Python Tool)  → Fetch OHLCV, indicators, regime
    2. Sentiment Agent (ADK)       → Search news/macro
    3. Bull Agent (ADK)            → Bullish thesis
    4. Bear Agent (ADK)            → Bearish teardown
    5. CIO Agent (ADK)             → Synthesise into trade proposal JSON
    6. Risk Handcuffs (Python Tool)→ Enforce ATR stop-loss & 1% sizing
"""

import asyncio
import argparse

from config import WATCH_LIST, DEFAULT_PORTFOLIO_EQUITY
from pipeline import Orchestrator
from pipeline.session_keys import KEY_FINAL_TRADE, ALL_KEYS
from utils.helpers import pretty_print_state, format_currency_inr


# ── Main Runner ───────────────────────────────────────────────────────────────

async def run_pipeline(
    ticker: str,
    portfolio_equity: float = DEFAULT_PORTFOLIO_EQUITY,
) -> dict:
    """
    Execute the full 6-step Regime-Aware pipeline for one ticker.

    Args:
        ticker:           The stock ticker symbol (e.g. 'RELIANCE.NS').
        portfolio_equity: Total portfolio equity in INR for position sizing.

    Returns:
        The final session.state dict containing all intermediate outputs
        and the risk-validated trade in KEY_FINAL_TRADE.
    """
    orchestrator = Orchestrator(ticker=ticker, portfolio_equity=portfolio_equity)
    return await orchestrator.run()


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Regime-Aware Trading Command Center – GDG Hackfest 2026"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Ticker symbol to analyse (e.g. RELIANCE.NS). Defaults to first in WATCH_LIST.",
    )
    parser.add_argument(
        "--equity",
        type=float,
        default=DEFAULT_PORTFOLIO_EQUITY,
        help=f"Portfolio equity in INR (default: {DEFAULT_PORTFOLIO_EQUITY:,.0f})",
    )
    args = parser.parse_args()

    ticker = args.ticker or WATCH_LIST[0]

    print(f"\n{'='*60}")
    print(f"  REGIME-AWARE TRADING COMMAND CENTER")
    print(f"  Ticker:    {ticker}")
    print(f"  Equity:    {format_currency_inr(args.equity)}")
    print(f"{'='*60}\n")

    # Run the async pipeline
    final_state = asyncio.run(run_pipeline(ticker=ticker, portfolio_equity=args.equity))

    # Debug: print entire shared whiteboard
    pretty_print_state(final_state)

    # Display final trade result
    final_trade = final_state.get(KEY_FINAL_TRADE)
    print("\n FINAL VALIDATED TRADE")
    print("-" * 40)
    if final_trade and not final_trade.get("killed"):
        print(f"  Ticker:        {final_trade.get('ticker', 'N/A')}")
        print(f"  Action:        {final_trade.get('action', 'N/A')}")
        print(f"  Entry:         {format_currency_inr(final_trade.get('entry_price', 0))}")
        print(f"  Stop Loss:     {format_currency_inr(final_trade.get('stop_loss', 0))}")
        print(f"  Target:        {format_currency_inr(final_trade.get('target_price', 0))}")
        print(f"  Position Size: {final_trade.get('position_size', 0)} shares")
        print(f"  Total Risk:    {format_currency_inr(final_trade.get('total_risk', 0))}")
        print(f"  Risk/Reward:   1:{final_trade.get('risk_reward_ratio', 0):.2f}")
        print(f"  Regime:        {final_trade.get('regime', 'N/A')}")
    elif final_trade and final_trade.get("killed"):
        print(f"  ⛔ TRADE KILLED by Risk Engine")
        print(f"  Reason: {final_trade.get('kill_reason', 'Unknown')}")
    else:
        print("  No trade proposal generated.")
    print()


if __name__ == "__main__":
    main()
