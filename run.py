#!/usr/bin/env python3
"""
run.py – Single-Command Trading Pipeline Entry Point
=====================================================
Runs the full 8-step unified pipeline with real-time output.

Usage:
    python run.py --portfolio 10000                    # Scan watchlist, find best opportunity
    python run.py --portfolio 10000 --ticker TCS.NS    # Analyze specific stock
    python run.py --portfolio 50000 --top 3            # Show top 3 opportunities

Pipeline Flow:
    1. Portfolio + Goal
    2. Market Regime Analysis
    3. News/Sentiment Analysis
    4. Scenario Detection
    5. Strategy Selection
    6. Quick Backtest
    7. Strategy Scoring
    8. Select Best
    9. Paper Trade
    10. Store Outcome + Context
    11. Memory → Bias Future Decisions
    12. Repeat (or exit)
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from config import WATCH_LIST

# ── Setup Logging ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def print_header(portfolio_value: float, ticker: str | None):
    """Print startup banner."""
    print()
    print("=" * 70)
    print("  REGIME-AWARE TRADING COMMAND CENTER")
    print("  GDG HackFest 2026 – AI Trading Pipeline")
    print("=" * 70)
    print(f"  Portfolio:     INR {portfolio_value:,.2f}")
    print(f"  Risk per trade: 1%")
    print(f"  Target:        {ticker or 'SCAN WATCHLIST'}")
    print(f"  Timestamp:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()


def run_single_ticker(ticker: str, portfolio_value: float, verbose: bool = True) -> dict:
    """Run full pipeline for a single ticker with step-by-step output."""
    from agents.pipeline import run_pipeline, TradingPipeline
    from tools.market_data import fetch_stock_data
    from tools.news_data import fetch_stock_news
    import pandas as pd

    if verbose:
        print(f"\n{'─' * 70}")
        print(f"  ANALYZING: {ticker}")
        print(f"{'─' * 70}")

    # Step 1-2: Fetch data
    if verbose:
        print("\n[1/8] Fetching market data...")

    data = fetch_stock_data(symbol=ticker)
    if data.get("status") != "success":
        if verbose:
            print(f"      ❌ Failed: {data.get('error_message', 'Unknown error')}")
        return {"status": "error", "ticker": ticker, "reason": data.get("error_message")}

    # Build candles DataFrame
    closes = data.get("closes", [])
    highs = data.get("highs", [])
    lows = data.get("lows", [])
    volumes = data.get("volumes", [])
    opens = data.get("opens", closes)
    n = min(len(closes), len(highs), len(lows), len(volumes))

    if n < 30:
        if verbose:
            print(f"      ❌ Insufficient data: {n} days")
        return {"status": "error", "ticker": ticker, "reason": f"Only {n} days of data"}

    candles = pd.DataFrame({
        "open": opens[-n:],
        "high": highs[-n:],
        "low": lows[-n:],
        "close": closes[-n:],
        "volume": volumes[-n:],
    })

    if verbose:
        print(f"      ✓ {n} days of data fetched (latest close: INR {closes[-1]:,.2f})")

    # Fetch news
    if verbose:
        print("\n[2/8] Fetching news sentiment...")

    try:
        news_result = fetch_stock_news(symbol=ticker)
        news = [a.get("title", "") for a in news_result.get("articles", [])[:10]]
        if verbose:
            print(f"      ✓ {len(news)} headlines fetched")
    except Exception as e:
        news = []
        if verbose:
            print(f"      ⚠ No news: {e}")

    # Run pipeline
    from agents import regime_agent, sentiment_agent, scenario_agent
    from agents import strategy_agent, backtest_agent, selector_agent
    from agents import paper_trade_agent, memory_agent
    from memory.trade_memory import TradeMemory

    memory = TradeMemory()

    # Step 3: Regime Detection
    if verbose:
        print("\n[3/8] Market Regime Analysis...")
    step1 = regime_agent.analyze(candles)
    regime = step1["regime"]
    if verbose:
        print(f"      TREND: {regime.trend.upper()}")
        print(f"        Volatility: {regime.volatility}")

    # Step 4: Sentiment Analysis
    if verbose:
        print("\n[4/8] News Sentiment Analysis...")
    step2 = sentiment_agent.analyze(news)
    sentiment = step2["sentiment"]
    if verbose:
        print(f"      ✓ Sentiment: {sentiment.bucket.upper()} (score: {sentiment.score:.2f})")
        if sentiment.danger:
            print(f"        ⚠ DANGER FLAG ACTIVE")

    # Step 5: Scenario Detection
    if verbose:
        print("\n[5/8] Scenario Detection...")
    step3 = scenario_agent.analyze(regime, sentiment)
    scenario = step3["scenario"]
    if verbose:
        print(f"      ✓ Scenario: {scenario.label}")

    # Step 6: Strategy Selection
    if verbose:
        print("\n[6/8] Strategy Candidates...")
    step4 = strategy_agent.analyze(scenario)
    candidates = step4["candidates"]
    if verbose:
        print(f"      ✓ Candidates: {[c.name for c in candidates]}")

    # Step 7: Backtest
    if verbose:
        print("\n[7/8] Quick Backtest (30 candles)...")
    step5 = backtest_agent.analyze(candidates, candles)
    results = step5["results"]
    if verbose:
        for r in results:
            print(f"      - {r.name:18} | WR: {r.win_rate*100:5.1f}% | Sharpe: {r.sharpe:5.2f} | Score: {r.composite_score:.3f}")

    # Step 8: Select Best (with memory bias)
    if verbose:
        print("\n[8/8] Selecting Best Strategy (with memory bias)...")
    step6 = selector_agent.analyze(results, scenario, memory)
    selected = step6["selected"]

    # Check memory bias
    bias = memory.memory_bias(scenario.label, selected.name)
    if verbose:
        print(f"      ✓ Selected: {selected.name}")
        print(f"        Composite Score: {selected.composite_score:.4f}")
        print(f"        Memory Bias: {bias:.2f}x")

    # Step 9: Paper Trade
    if verbose:
        print("\n[9] Paper Trade Execution...")
    step7 = paper_trade_agent.execute(
        selected=selected,
        candles=candles,
        portfolio_value=portfolio_value,
        scenario=scenario,
        risk_pct=0.01,
        ticker=ticker,
    )
    trade = step7.get("trade")

    if trade:
        if verbose:
            print(f"      ✓ Trade Placed: {trade.strategy_name}")
            direction = "SHORT" if trade.stop > trade.entry else "LONG"
            print(f"        Direction: {direction}")
            print(f"        Entry:    INR {trade.entry:,.2f}")
            print(f"        Stop:     INR {trade.stop:,.2f}")
            print(f"        Target:   INR {trade.target:,.2f}")
            print(f"        Position: {trade.size} shares")
            print(f"        R:R Ratio: {trade.rr_ratio:.1f}")
            risk_amount = abs(trade.entry - trade.stop) * trade.size
            print(f"        Risk:     INR {risk_amount:,.2f} (1% of portfolio)")
    else:
        if verbose:
            print(f"      ✗ No Trade: {step7.get('reason', 'N/A')}")

    # Step 10: Store Outcome
    if verbose:
        print("\n[10] Storing to Memory...")
    if trade:
        step8 = memory_agent.store_trade(trade)
        if verbose:
            stats = step8.get("memory_stats", {})
            print(f"      ✓ Trade #{stats.get('total_trades', 1)} stored")
            print(f"        Total trades in memory: {stats.get('total_trades', 1)}")
    else:
        if verbose:
            print("      ✓ No trade to store (paper skip)")

    # Build result
    result = {
        "status": "success",
        "ticker": ticker,
        "regime": regime.trend,
        "volatility": regime.volatility,
        "sentiment": sentiment.bucket,
        "scenario": scenario.label,
        "strategy": selected.name,
        "composite_score": selected.composite_score,
        "memory_bias": bias,
        "trade": trade.to_dict() if trade else None,
        "trade_status": step7["status"],
    }

    return result


def scan_watchlist(portfolio_value: float, top_n: int = 5) -> list:
    """Scan watchlist and return top opportunities."""
    print("\n" + "=" * 70)
    print("  SCANNING WATCHLIST FOR OPPORTUNITIES")
    print("=" * 70)

    results = []
    for i, ticker in enumerate(WATCH_LIST[:top_n * 2]):  # Scan more to get top N
        result = run_single_ticker(ticker, portfolio_value, verbose=False)
        if result.get("status") == "success":
            results.append(result)
            print(f"  [{i+1:2}] {ticker:15} | {result['regime']:8} | {result['sentiment']:8} | {result['strategy']:18} | score: {result['composite_score']:.3f}")
        else:
            print(f"  [{i+1:2}] {ticker:15} | ❌ {result.get('reason', 'Error')[:40]}")

    # Sort by composite score
    results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    return results[:top_n]


def display_recommendations(results: list, portfolio_value: float):
    """Display final recommendations."""
    print("\n" + "=" * 70)
    print("  TOP RECOMMENDATIONS")
    print("=" * 70)

    if not results:
        print("\n  No valid opportunities found.")
        return

    for i, r in enumerate(results, 1):
        print(f"\n  #{i} {r['ticker']}")
        print(f"     Scenario: {r['scenario']}")
        print(f"     Strategy: {r['strategy']}")
        print(f"     Score:    {r['composite_score']:.4f}")
        print(f"     Bias:     {r['memory_bias']:.2f}x")

        trade = r.get("trade")
        if trade:
            direction = "SHORT" if trade['stop'] > trade['entry'] else "LONG"
            print(f"     Trade:    {direction}")
            print(f"     Entry:    INR {trade['entry']:,.2f}")
            print(f"     Stop:     INR {trade['stop']:,.2f}")
            print(f"     Target:   INR {trade['target']:,.2f}")
            print(f"     Qty:      {trade['size']} shares")
        else:
            print(f"     Trade:    NO TRADE ({r.get('trade_status', 'N/A')})")

    print("\n" + "=" * 70)
    print("  MEMORY + LEARNING")
    print("=" * 70)
    print("  Outcomes from these trades will be stored and used to bias")
    print("  future strategy selection for similar market conditions.")
    print("  Run again after market close to update trade outcomes.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Regime-Aware AI Trading Pipeline – Single Command Entry Point"
    )
    parser.add_argument(
        "--portfolio", "-p",
        type=float,
        default=10000.0,
        help="Portfolio value in INR (default: 10,000)",
    )
    parser.add_argument(
        "--ticker", "-t",
        type=str,
        default=None,
        help="Specific ticker to analyze (e.g., TCS.NS). If omitted, scans watchlist.",
    )
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=5,
        help="Number of top opportunities to show when scanning (default: 5)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity",
    )
    args = parser.parse_args()

    print_header(args.portfolio, args.ticker)

    if args.ticker:
        # Single ticker analysis
        result = run_single_ticker(args.ticker, args.portfolio, verbose=not args.quiet)
        if result.get("status") == "success":
            display_recommendations([result], args.portfolio)
        else:
            print(f"\n❌ Analysis failed: {result.get('reason', 'Unknown error')}")
            sys.exit(1)
    else:
        # Scan watchlist
        results = scan_watchlist(args.portfolio, args.top)
        display_recommendations(results, args.portfolio)


if __name__ == "__main__":
    main()
