"""
agents/pipeline.py – Trading Pipeline Orchestrator
=====================================================
Runs the full 8-step pipeline:
  1. RegimeAgent.analyze(candles)       → MarketRegime
  2. SentimentAgent.analyze(headlines)  → NewsSentiment
  3. ScenarioAgent.analyze(regime, sentiment) → Scenario
  4. StrategyAgent.analyze(scenario)    → list[BaseStrategy]
  5. BacktestAgent.analyze(strategies, candles) → list[StrategyResult]
  6. SelectorAgent.analyze(results, scenario, memory) → StrategyResult
  7. PaperTradeAgent.execute(selected, candles, portfolio, scenario) → TradeRecord
  8. MemoryAgent.store(record)          → confirmation

All outputs are JSON-serializable dicts.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd

from agents import regime_agent
from agents import sentiment_agent
from agents import scenario_agent
from agents import strategy_agent
from agents import backtest_agent
from agents import selector_agent
from agents import paper_trade_agent
from agents import memory_agent

from memory.trade_memory import TradeMemory

logger = logging.getLogger(__name__)


class TradingPipeline:
    """Orchestrates the 8-agent trading pipeline."""

    def __init__(self):
        self._memory = TradeMemory()

    def run(
        self,
        candles: pd.DataFrame,
        news: List[str],
        portfolio_value: float = 1_000_000.0,
        risk_pct: float = 0.01,
        ticker: str = "UNKNOWN",
    ) -> Dict:
        """Execute the full pipeline.

        Parameters
        ----------
        candles : pd.DataFrame
            OHLCV candle data (columns: open, high, low, close, volume).
        news : list[str]
            Recent news headlines.
        portfolio_value : float
            Total portfolio equity for position sizing.
        risk_pct : float
            Fraction of portfolio to risk per trade (default 1%).
        ticker : str
            Stock ticker symbol.

        Returns
        -------
        dict
            Full pipeline result with all step outputs, JSON-serializable.
        """
        logger.info("═══ Pipeline START: %s ═══", ticker)

        # ── Step 1: Regime Detection ──────────────────────────────────────
        logger.info("Step 1/8: Regime Detection")
        step1 = regime_agent.analyze(candles)
        regime = step1["regime"]
        logger.info("  → %s", regime)

        # ── Step 2: Sentiment Analysis ────────────────────────────────────
        logger.info("Step 2/8: Sentiment Analysis")
        step2 = sentiment_agent.analyze(news)
        sentiment = step2["sentiment"]
        logger.info("  → %s", sentiment)

        # ── Step 3: Scenario Detection ────────────────────────────────────
        logger.info("Step 3/8: Scenario Detection")
        step3 = scenario_agent.analyze(regime, sentiment)
        scenario = step3["scenario"]
        logger.info("  → %s", scenario.label)

        # ── Step 4: Strategy Selection ────────────────────────────────────
        logger.info("Step 4/8: Strategy Candidates")
        step4 = strategy_agent.analyze(scenario)
        candidates = step4["candidates"]
        logger.info("  → %s", [c.name for c in candidates])

        # ── Step 5: Quick Backtest ────────────────────────────────────────
        logger.info("Step 5/8: Backtesting")
        step5 = backtest_agent.analyze(candidates, candles)
        results = step5["results"]
        logger.info("  → %s", [(r.name, r.win_rate, r.sharpe) for r in results])

        # ── Step 6: Strategy Selector ─────────────────────────────────────
        logger.info("Step 6/8: Selecting Best Strategy")
        step6 = selector_agent.analyze(results, scenario, self._memory)
        selected = step6["selected"]
        logger.info("  → %s (score=%.4f)", selected.name, selected.composite_score)

        # ── Step 7: Paper Trade Execution ─────────────────────────────────
        logger.info("Step 7/8: Paper Trade")
        step7 = paper_trade_agent.execute(
            selected=selected,
            candles=candles,
            portfolio_value=portfolio_value,
            scenario=scenario,
            risk_pct=risk_pct,
            ticker=ticker,
        )
        trade = step7.get("trade")
        logger.info("  → %s", step7["status"])

        # ── Step 8: Memory Storage ────────────────────────────────────────
        logger.info("Step 8/8: Memory Storage")
        if trade is not None:
            step8 = memory_agent.store_trade(trade)
        else:
            step8 = {"status": "skipped", "reason": "no trade to store"}
        logger.info("  → %s", step8["status"])

        logger.info("═══ Pipeline END: %s ═══", ticker)

        # ── Build JSON-serializable result ────────────────────────────────
        return {
            "status": "success",
            "ticker": ticker,
            "scenario": scenario.to_dict(),
            "strategy_selected": selected.name,
            "backtest_scores": [r.to_dict() for r in results],
            "trade": trade.to_dict() if trade else None,
            "trade_status": step7["status"],
            "trade_reason": step7.get("reason", ""),
            "memory_stats": step8.get("memory_stats", memory_agent.get_stats()),
        }


# ── Module-level convenience function ─────────────────────────────────────────

# Shared pipeline instance (reuses TradeMemory across calls)
_pipeline_instance: TradingPipeline = None


def run_pipeline(
    ticker: str = "RELIANCE.NS",
    portfolio_value: float = 1_000_000.0,
    risk_pct: float = 0.01,
) -> Dict:
    """Convenience function to run the full trading pipeline.

    Uses a shared pipeline instance to preserve memory across calls.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g., 'RELIANCE.NS').
    portfolio_value : float
        Total portfolio equity for position sizing.
    risk_pct : float
        Fraction of portfolio to risk per trade.

    Returns
    -------
    dict
        Full pipeline result.
    """
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = TradingPipeline()

    # Fetch live data
    from tools.market_data import fetch_stock_data
    from tools.news_data import fetch_stock_news

    # Fetch candles
    data = fetch_stock_data(symbol=ticker)
    if data.get("status") != "success":
        return {"status": "error", "reason": f"Cannot fetch data for {ticker}"}

    closes = data.get("closes", [])
    highs = data.get("highs", [])
    lows = data.get("lows", [])
    volumes = data.get("volumes", [])
    opens = data.get("opens", closes)
    n = min(len(closes), len(highs), len(lows), len(volumes))
    if n < 30:
        return {"status": "error", "reason": f"Insufficient data for {ticker}"}

    candles = pd.DataFrame({
        "open": opens[-n:],
        "high": highs[-n:],
        "low": lows[-n:],
        "close": closes[-n:],
        "volume": volumes[-n:],
    })

    # Fetch news
    try:
        news_result = fetch_stock_news(symbol=ticker)
        news = news_result.get("headlines", []) if news_result.get("status") == "success" else []
    except Exception:
        news = []

    return _pipeline_instance.run(
        candles=candles,
        news=news,
        portfolio_value=portfolio_value,
        risk_pct=risk_pct,
        ticker=ticker,
    )


# ── Standalone Test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import numpy as np

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    np.random.seed(42)
    n = 80
    df = pd.DataFrame({
        "open": np.random.uniform(100, 110, n),
        "high": np.random.uniform(108, 115, n),
        "low": np.random.uniform(95, 102, n),
        "close": np.random.uniform(100, 110, n),
        "volume": np.random.uniform(1e6, 5e6, n),
    })

    headlines = [
        "Stock market rallies on strong earnings",
        "Positive GDP growth expected",
    ]

    pipeline = TradingPipeline()
    result = pipeline.run(
        candles=df,
        news=headlines,
        portfolio_value=1_000_000,
        ticker="TEST.NS",
    )

    print("\n" + "=" * 60)
    print("PIPELINE RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
