"""
tools/quant_tool.py ΓÇô ADK Tool Wrapper for the Deterministic Quant Engine
==========================================================================
Single bridge between the deterministic Python quant pipeline and Gemini
ADK agents.  This file is **only** an adapter ΓÇö all maths live in
``quant/`` and are independently testable without ADK.

Pipeline executed per call::

    Ticker
      Γåô  fetch_ohlcv()        ΓåÆ MarketData
      Γåô  compute_indicators()  ΓåÆ IndicatorSet
      Γåô  classify_regime()     ΓåÆ RegimeSnapshot
      Γåô
    Return flat JSON-safe dict

Design principles:
    ΓÇó Deterministic only ΓÇö no LLM / Gemini / ADK reasoning.
    ΓÇó No calculations ΓÇö delegates entirely to ``quant/``.
    ΓÇó No mutation ΓÇö frozen dataclass inputs, dict output.
    ΓÇó No global state ΓÇö pure function calls.
    ΓÇó Fail-fast ΓÇö raises ``ValueError`` / ``RuntimeError`` on bad input.
    ΓÇó ADK compatible ΓÇö function-based tools with automatic schema generation.

Coexists safely with:
    ΓÇó ``trading_agents/tools/market_data.py``
    ΓÇó ``trading_agents/tools/technical.py``
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Final

from quant.data_fetcher import fetch_ohlcv, fetch_multiple, MarketData
from quant.indicators import compute_indicators, IndicatorSet
from quant.regime_classifier import classify_regime, RegimeSnapshot
from config import DEFAULT_PERIOD, DEFAULT_INTERVAL
from strategy import build_scenario, quick_backtest

# Learning loop integration (lazy import to avoid circular deps)
_learning_loop = None

def _get_learning_loop():
    """Lazy-init the learning loop singleton."""
    global _learning_loop
    if _learning_loop is None:
        try:
            from pipeline.learning_loop import LearningLoop
            _learning_loop = LearningLoop()
        except Exception as exc:
            logger.warning("LearningLoop unavailable: %s", exc)
    return _learning_loop

# ΓöÇΓöÇ Module-level logger ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
logger: logging.Logger = logging.getLogger(__name__)

# ΓöÇΓöÇ Constants ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
_ROUND_DIGITS: Final[int] = 4


# ΓöÇΓöÇ Internal helpers (pure functions) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def _snapshot_to_dict(
    indicators: IndicatorSet,
    regime: RegimeSnapshot,
) -> dict:
    """Convert frozen dataclass outputs into a flat, JSON-safe dictionary.

    No computation happens here ΓÇö values are copied verbatim from the
    already-validated ``IndicatorSet`` and ``RegimeSnapshot``.

    Args:
        indicators: Computed technical indicators (immutable).
        regime:     Classified market regime (immutable).

    Returns:
        A flat ``dict`` with string keys and JSON-serialisable values.
    """
    ts: str = (
        indicators.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        if indicators.timestamp.tzinfo is not None
        else indicators.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    snapshot = {
        "ticker": indicators.ticker,
        "price": round(indicators.price, _ROUND_DIGITS),
        "regime": regime.regime,
        "rsi": round(indicators.rsi, _ROUND_DIGITS),
        "atr": round(indicators.atr, _ROUND_DIGITS),
        "sma20": round(indicators.sma20, _ROUND_DIGITS),
        "sma50": round(indicators.sma50, _ROUND_DIGITS),
        "sma200": round(indicators.sma200, _ROUND_DIGITS),
        "ema20": round(indicators.ema20, _ROUND_DIGITS),
        "ema50": round(indicators.ema50, _ROUND_DIGITS),
        "momentum_20d": round(indicators.momentum_20d, _ROUND_DIGITS),
        "trend_strength": round(indicators.trend_strength, _ROUND_DIGITS),
        "volatility": round(indicators.volatility, _ROUND_DIGITS),
        "timestamp": ts,
    }

    # ── Step 5: Build deterministic scenario ──────────────────────
    try:
        scenario = build_scenario(
            regime=regime.regime,
            rsi=indicators.rsi,
            trend_strength=indicators.trend_strength,
            volatility=indicators.volatility,
            atr=indicators.atr,
            price=indicators.price,
        )
        snapshot["scenario"] = scenario.to_dict()
    except Exception as exc:
        logger.warning("[%s] Scenario build failed — %s", indicators.ticker, exc)
        snapshot["scenario"] = None

    return snapshot


def _attach_quick_backtest(snapshot: dict, market_data: MarketData) -> dict:
    """Attach quick backtest scores and best strategy to snapshot."""
    try:
        bt = quick_backtest(
            dataframe=market_data.dataframe,
            regime=snapshot.get("regime", "NEUTRAL"),
            lookback=30,
        )
        snapshot["strategy_scores"] = bt.get("scores", {})
        snapshot["quick_backtest"] = {
            "lookback": bt.get("lookback", 30),
            "best_strategy": bt.get("best_strategy", "no_trade"),
            "reason": bt.get("reason", "ok"),
        }
    except Exception as exc:
        logger.warning("[%s] Quick backtest failed: %s", snapshot.get("ticker", "?"), exc)
        snapshot["strategy_scores"] = {}
        snapshot["quick_backtest"] = {
            "lookback": 30,
            "best_strategy": "no_trade",
            "reason": "error",
        }
    return snapshot


# ΓöÇΓöÇ Public API ΓÇö ADK-compatible function tools ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def quant_engine_tool(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> dict:
    """Run the full deterministic quant pipeline for a single ticker.

    Executes three sequential steps ΓÇö fetch, compute, classify ΓÇö then
    returns a flat JSON-safe dictionary suitable for Gemini agent
    consumption.  This function performs **no** calculations itself;
    all maths are delegated to the ``quant/`` package.

    Compatible with Google ADK automatic schema generation.

    Args:
        ticker:   Yahoo Finance symbol (e.g. ``'RELIANCE.NS'``,
                  ``'TCS'``, ``'^NSEI'``).  Bare tickers get ``.NS``
                  appended automatically by the data fetcher.
        period:   yfinance look-back period (default ``'1y'``).
        interval: yfinance candle interval (default ``'1d'``).

    Returns:
        Flat ``dict`` containing: ``ticker``, ``price``, ``regime``,
        ``rsi``, ``atr``, ``sma20``, ``sma50``, ``sma200``, ``ema20``,
        ``ema50``, ``momentum_20d``, ``trend_strength``, ``volatility``,
        ``timestamp``.

    Raises:
        ValueError:    Invalid ticker, insufficient data, stale data,
                       or indicator computation failure.
        RuntimeError:  Network failure or yfinance download error.
    """
    # ΓöÇΓöÇ Step 1: Fetch OHLCV ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    logger.info("[%s] Fetching quant snapshot (period=%s, interval=%s)", ticker, period, interval)
    market_data: MarketData = fetch_ohlcv(ticker, period=period, interval=interval)

    # ΓöÇΓöÇ Step 2: Compute indicators ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    indicators: IndicatorSet = compute_indicators(market_data)
    logger.info("[%s] Indicators computed", market_data.ticker)

    # ΓöÇΓöÇ Step 3: Classify regime ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    regime: RegimeSnapshot = classify_regime(indicators)
    logger.info("[%s] Regime classified → %s", market_data.ticker, regime.regime)

    # ── Step 4: Build flat dict ──────────────────────────────────────────
    snapshot = _snapshot_to_dict(indicators, regime)

    # ── Step 5: Quick backtest + strategy scores (30 candles) ─────────
    snapshot = _attach_quick_backtest(snapshot, market_data)

    # ── Step 6: Enrich with learning loop (selector recommendation) ───
    loop = _get_learning_loop()
    if loop is not None:
        try:
            snapshot = loop.enrich(snapshot)
        except Exception as exc:
            logger.warning("[%s] Learning loop enrichment failed: %s", ticker, exc)

    return snapshot


def quant_engine_batch_tool(
    tickers: list[str],
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> list[dict]:
    """Run the deterministic quant pipeline for multiple tickers.

    Uses :func:`~quant.data_fetcher.fetch_multiple` for batch fetching,
    then computes indicators and classifies regime for each successful
    fetch.  Tickers that fail at **any** stage (fetch, compute, classify)
    are skipped with a logged warning ΓÇö partial results are returned
    rather than aborting the entire batch.

    Compatible with Google ADK automatic schema generation.

    Args:
        tickers:  List of Yahoo Finance symbols (e.g.
                  ``['RELIANCE.NS', 'TCS.NS', '^NSEI']``).
        period:   yfinance look-back period (default ``'1y'``).
        interval: yfinance candle interval (default ``'1d'``).

    Returns:
        A ``list[dict]``, where each element is the same flat snapshot
        dictionary produced by :func:`quant_engine_tool`.  Failing
        tickers are omitted silently (logged at WARNING level).

    Raises:
        ValueError: If *tickers* is empty.
    """
    if not tickers:
        raise ValueError("Ticker list must not be empty.")

    logger.info("Batch quant snapshot for %d tickers: %s", len(tickers), tickers)

    # ΓöÇΓöÇ Step 1: Batch fetch (skips failures internally) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    market_data_list: list[MarketData] = fetch_multiple(
        tickers, period=period, interval=interval,
    )

    # ΓöÇΓöÇ Step 2ΓÇô3: Compute + classify each ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    results: list[dict] = []
    for md in market_data_list:
        try:
            indicators: IndicatorSet = compute_indicators(md)
            logger.info("[%s] Indicators computed", md.ticker)

            regime: RegimeSnapshot = classify_regime(indicators)
            logger.info("[%s] Regime classified ΓåÆ %s", md.ticker, regime.regime)

            results.append(_snapshot_to_dict(indicators, regime))
        except (ValueError, TypeError) as exc:
            logger.warning("[%s] Skipped during indicator/regime stage ΓÇö %s", md.ticker, exc)

    logger.info(
        "Batch complete: %d/%d tickers succeeded",
        len(results), len(tickers),
    )

    return results


# ΓöÇΓöÇ Standalone test ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s Γöé %(levelname)-7s Γöé %(name)s Γöé %(message)s",
        datefmt="%H:%M:%S",
    )

    # ΓöÇΓöÇ Single-ticker tests ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    test_tickers: list[str] = ["RELIANCE", "TCS", "^NSEI"]

    print("\n" + "=" * 70)
    print("  tools/quant_tool.py ΓÇö Single-Ticker Tests")
    print("=" * 70)

    for t in test_tickers:
        try:
            snapshot: dict = quant_engine_tool(t)
            print(f"\n  Γ£ô {snapshot['ticker']} ΓÇö {snapshot['regime']}")
            print(json.dumps(snapshot, indent=4))
        except (ValueError, RuntimeError) as err:
            print(f"\n  Γ£ù {t} ΓÇö FAILED: {err}")

    # ΓöÇΓöÇ Batch test ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    print("\n" + "=" * 70)
    print("  tools/quant_tool.py ΓÇö Batch Test")
    print("=" * 70)

    try:
        batch: list[dict] = quant_engine_batch_tool(test_tickers)
        print(f"\n  Batch returned {len(batch)}/{len(test_tickers)} snapshots:\n")
        for snap in batch:
            print(f"    {snap['ticker']:15s}  regime={snap['regime']:8s}  "
                  f"price={snap['price']:.2f}  rsi={snap['rsi']:.1f}  "
                  f"vol={snap['volatility']:.2%}")
    except (ValueError, RuntimeError) as err:
        print(f"\n  Γ£ù Batch FAILED: {err}")

    print("\n" + "=" * 70)
    print("  Done.")
    print("=" * 70 + "\n")
