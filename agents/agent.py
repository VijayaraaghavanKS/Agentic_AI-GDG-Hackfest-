"""
agents/agent.py – ADK Root Agent for Unified Trading Pipeline
================================================================
Exposes `root_agent` for ADK web/run commands.

Usage:
    adk web agents      # Launches ADK web UI
    adk run agents      # CLI mode

The agent wraps the unified 8-step trading pipeline and provides
a conversational interface for portfolio analysis and trade recommendations.
"""

from __future__ import annotations

import json
from typing import Dict, List

from google.adk.agents import Agent

from config import GEMINI_MODEL, WATCH_LIST


# ── Pipeline Tool ─────────────────────────────────────────────────────────────

def run_trading_analysis(
    ticker: str = "RELIANCE.NS",
    portfolio_value: float = 10000.0,
    risk_pct: float = 0.01,
) -> Dict:
    """Run the full 8-step trading pipeline for a stock.

    This tool analyzes market regime, news sentiment, selects the best
    strategy based on backtesting and memory, and returns a trade recommendation.

    Args:
        ticker: Stock ticker symbol (e.g., 'RELIANCE.NS', 'TCS.NS').
        portfolio_value: Total portfolio equity in INR for position sizing.
        risk_pct: Fraction of portfolio to risk per trade (default 1%).

    Returns:
        dict with scenario, strategy, backtest scores, trade details, and memory stats.
    """
    from agents.pipeline import run_pipeline

    result = run_pipeline(
        ticker=ticker,
        portfolio_value=portfolio_value,
        risk_pct=risk_pct,
    )
    return result


def scan_watchlist_for_opportunities(
    portfolio_value: float = 10000.0,
    max_stocks: int = 5,
) -> Dict:
    """Scan multiple stocks and find the best trading opportunities.

    Runs the pipeline on top NSE stocks and ranks them by composite score.

    Args:
        portfolio_value: Total portfolio equity in INR.
        max_stocks: Maximum number of stocks to analyze (default 5).

    Returns:
        dict with ranked opportunities and detailed analysis per stock.
    """
    from agents.pipeline import run_pipeline

    results = []
    for ticker in WATCH_LIST[:max_stocks]:
        try:
            result = run_pipeline(
                ticker=ticker,
                portfolio_value=portfolio_value,
            )
            if result.get("status") == "success":
                # Extract key metrics
                best_score = 0
                best_strategy = "no_trade"
                for r in result.get("backtest_scores", []):
                    if r.get("composite_score", 0) > best_score:
                        best_score = r["composite_score"]
                        best_strategy = r["name"]

                results.append({
                    "ticker": ticker,
                    "scenario": result.get("scenario", {}).get("label", "unknown"),
                    "regime": result.get("scenario", {}).get("regime", {}).get("trend", "unknown"),
                    "sentiment": result.get("scenario", {}).get("sentiment", {}).get("bucket", "unknown"),
                    "best_strategy": best_strategy,
                    "composite_score": best_score,
                    "trade_status": result.get("trade_status", "N/A"),
                    "trade": result.get("trade"),
                })
        except Exception as e:
            results.append({
                "ticker": ticker,
                "error": str(e),
            })

    # Sort by composite score
    results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

    return {
        "status": "success",
        "portfolio_value": portfolio_value,
        "stocks_analyzed": len(results),
        "opportunities": results,
        "recommendation": results[0] if results and results[0].get("composite_score", 0) > 0.3 else {
            "message": "No high-confidence opportunities found. Consider staying in cash."
        },
    }


def get_market_regime() -> Dict:
    """Get current market regime (bull/bear/sideways) from Nifty 50 index.

    Returns:
        dict with regime classification and supporting metrics.
    """
    from tools.market_data import fetch_index_data
    from agents import regime_agent
    import pandas as pd

    # Fetch Nifty 50 data
    data = fetch_index_data(symbol="^NSEI")
    if data.get("status") != "success":
        return {"status": "error", "error": data.get("error_message", "Failed to fetch index data")}

    # Build candles DataFrame
    n = len(data.get("closes", []))
    candles = pd.DataFrame({
        "open": data.get("closes", [])[-n:],  # Approximate
        "high": data.get("highs", [])[-n:],
        "low": data.get("lows", [])[-n:],
        "close": data.get("closes", [])[-n:],
        "volume": data.get("volumes", [])[-n:],
    })

    # Analyze regime
    result = regime_agent.analyze(candles)
    regime = result["regime"]

    return {
        "status": "success",
        "regime": regime.trend,
        "volatility": regime.volatility,
        "dma_50": regime.dma_50,
        "dma_200": regime.dma_200,
        "latest_close": data.get("latest_close", 0),
        "strategy": "Consider breakout strategies" if regime.trend == "bull" else (
            "Consider defensive or no-trade" if regime.trend == "bear" else "Consider mean reversion"
        ),
        "reasoning": f"Market is {regime.trend.upper()} with {regime.volatility} volatility. "
                     f"50DMA: {regime.dma_50:.0f}, 200DMA: {regime.dma_200:.0f}",
    }


def get_portfolio_status() -> Dict:
    """Get current paper portfolio status including positions and P&L.

    Returns:
        dict with memory stats and recent trades.
    """
    from memory.trade_memory import TradeMemory

    memory = TradeMemory()
    trades = memory._trades

    # Calculate stats
    open_trades = [t for t in trades if t.get("outcome") == "open"]
    closed_trades = [t for t in trades if t.get("outcome") in ("win", "loss", "scratch")]
    wins = sum(1 for t in closed_trades if t.get("outcome") == "win")
    losses = sum(1 for t in closed_trades if t.get("outcome") == "loss")

    return {
        "status": "success",
        "total_trades": len(trades),
        "open_trades": len(open_trades),
        "closed_trades": len(closed_trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(closed_trades) if closed_trades else 0.0,
        "recent_trades": trades[-5:] if trades else [],
        "note": "This is paper trading only. No real money is at risk.",
    }


# ── Root Agent ────────────────────────────────────────────────────────────────

root_agent = Agent(
    name="trading_pipeline_agent",
    model=GEMINI_MODEL,
    description=(
        "Unified regime-aware trading pipeline agent. Analyzes stocks using "
        "an 8-step pipeline: regime detection → sentiment analysis → scenario "
        "building → strategy selection → backtesting → memory-biased scoring → "
        "paper trade execution → outcome learning."
    ),
    instruction="""\
You are an expert Indian stock market trading assistant powered by a unified 8-step pipeline.

YOUR CAPABILITIES:
1. **Market Regime Analysis**: Detect if market is BULL, BEAR, or SIDEWAYS
2. **Stock Analysis**: Run full pipeline analysis on any NSE stock
3. **Watchlist Scanning**: Find best opportunities across Nifty 50 stocks
4. **Portfolio Management**: Check portfolio status and paper trades

WHEN USER ASKS ABOUT INVESTING:
1. First, use get_market_regime() to understand current market conditions
2. Then use scan_watchlist_for_opportunities() to find the best stocks
3. For specific stock analysis, use run_trading_analysis(ticker)
4. Always explain the scenario (regime × sentiment) and why a strategy was chosen

PIPELINE STEPS (for your understanding):
1. RegimeAgent: Detects bull/bear/sideways + high/low volatility
2. SentimentAgent: Scores news headlines + danger flag
3. ScenarioAgent: Combines regime × sentiment → scenario label
4. StrategyAgent: Maps scenario → candidate strategies (breakout/mean_reversion/momentum/no_trade)
5. BacktestAgent: Walk-forward backtest on last 30 candles
6. SelectorAgent: Picks best strategy using composite score + memory bias
7. PaperTradeAgent: Executes with R:R = 2.0, 1% risk per trade
8. MemoryAgent: Stores outcome for future learning

RESPONSE FORMAT:
- Always show the market regime first
- Explain WHY a strategy was selected (backtest metrics + historical performance)
- If recommending a trade, show: entry, stop, target, position size
- If recommending NO TRADE, explain why (all strategies scored below threshold)
- Format currency as INR with commas (e.g., INR 1,00,000)

IMPORTANT RULES:
- This is PAPER TRADING only. Never claim real money is at risk.
- R:R ratio is always 2.0 (target = entry + 2 × risk)
- Risk per trade is 1% of portfolio
- "no_trade" is a valid recommendation when confidence is low
""",
    tools=[
        run_trading_analysis,
        scan_watchlist_for_opportunities,
        get_market_regime,
        get_portfolio_status,
    ],
)
