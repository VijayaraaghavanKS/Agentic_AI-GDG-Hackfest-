"""
main.py – Regime-Aware Trading Pipeline (CLI Entry Point)
===========================================================
Runs the full 8-step unified pipeline from the command line.

Usage:
    python main.py                          # Run for first ticker in WATCH_LIST
    python main.py --ticker RELIANCE.NS     # Run for a specific ticker
    python main.py --equity 500000          # Custom portfolio equity

Pipeline Steps (Unified):
    1. RegimeAgent      → Detect bull/bear/sideways + volatility
    2. SentimentAgent   → Score news + danger flag
    3. ScenarioAgent    → Regime × Sentiment → scenario label
    4. StrategyAgent    → Scenario → candidate strategies
    5. BacktestAgent    → Quick backtest on 30 candles
    6. SelectorAgent    → Score + memory bias → select best
    7. PaperTradeAgent  → Execute with R:R=2.0
    8. MemoryAgent      → Store outcome for learning
"""

import argparse

from config import WATCH_LIST, DEFAULT_PORTFOLIO_EQUITY
from pipeline import Orchestrator
from utils.helpers import format_currency_inr


# ── Main Runner ───────────────────────────────────────────────────────────────

def run_pipeline(
    ticker: str,
    portfolio_equity: float = DEFAULT_PORTFOLIO_EQUITY,
) -> dict:
    """
    Execute the full trading pipeline for one ticker.

    Args:
        ticker:           The stock ticker symbol (e.g. 'RELIANCE.NS').
        portfolio_equity: Total portfolio equity in INR for position sizing.

    Returns:
        Pipeline result dict with scenario, strategy, trade, and memory stats.
    """
    orchestrator = Orchestrator(ticker=ticker, portfolio_equity=portfolio_equity)
    return orchestrator.run()


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

    # Run the pipeline
    result = run_pipeline(ticker=ticker, portfolio_equity=args.equity)

    # Print result summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULT:")
    print("=" * 60)
    if result.get("status") == "success":
        print(f"  Scenario:  {result.get('scenario', {}).get('label', 'N/A')}")
        print(f"  Strategy:  {result.get('strategy_selected', 'N/A')}")
        print(f"  Trade:     {result.get('trade_status', 'N/A')}")
        print(f"  Reason:    {result.get('trade_reason', 'N/A')}")
    else:
        print(f"  Error: {result.get('reason', 'Unknown')}")

    # Display trade details if present
    trade = result.get('trade')
    print("\n TRADE DETAILS")
    print("-" * 40)
    if trade:
        print(f"  Ticker:        {trade.get('ticker', 'N/A')}")
        print(f"  Strategy:      {trade.get('strategy_name', 'N/A')}")
        print(f"  Entry:         {format_currency_inr(trade.get('entry', 0))}")
        print(f"  Stop Loss:     {format_currency_inr(trade.get('stop', 0))}")
        print(f"  Target:        {format_currency_inr(trade.get('target', 0))}")
        print(f"  Position Size: {trade.get('size', 0)} shares")
        print(f"  Risk/Share:    {format_currency_inr(trade.get('risk_per_share', 0))}")
        print(f"  R:R Ratio:     1:{trade.get('rr_ratio', 0):.2f}")
        print(f"  Scenario:      {trade.get('scenario_label', 'N/A')}")
    else:
        print(f"  {result.get('trade_reason', 'No trade generated')}")

    # Display memory stats
    memory_stats = result.get('memory_stats', {})
    if memory_stats:
        print("\n MEMORY STATS")
        print("-" * 40)
        print(f"  Total Trades:  {memory_stats.get('total_trades', 0)}")
        print(f"  Win Rate:      {memory_stats.get('win_rate', 0):.2%}")
        print(f"  Avg PnL:       {memory_stats.get('avg_pnl_pct', 0):.2%}")
    print()


if __name__ == "__main__":
    main()
