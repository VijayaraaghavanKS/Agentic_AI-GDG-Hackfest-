"""
tools/quant_tool.py – ADK Tool Wrapper for the Deterministic Quant Engine
==========================================================================
Single bridge between the deterministic Python quant pipeline and Gemini
ADK agents.  This file is **only** an adapter — all maths live in
``quant/`` and are independently testable without ADK.

Pipeline executed per call::

    Ticker
      ↓  fetch_ohlcv()        → MarketData
      ↓  compute_indicators()  → IndicatorSet
      ↓  classify_regime()     → RegimeSnapshot
      ↓
    Return flat JSON-safe dict

Design principles:
    • Deterministic only — no LLM / Gemini / ADK reasoning.
    • No calculations — delegates entirely to ``quant/``.
    • No mutation — frozen dataclass inputs, dict output.
    • No global state — pure function calls.
    • Fail-fast — raises ``ValueError`` / ``RuntimeError`` on bad input.
    • ADK compatible — function-based tools with automatic schema generation.

Coexists safely with:
    • ``trading_agents/tools/market_data.py``
    • ``trading_agents/tools/technical.py``
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Final

from quant.data_fetcher import fetch_ohlcv, fetch_multiple, MarketData
from quant.indicators import compute_indicators, IndicatorSet
from quant.regime_classifier import classify_regime, RegimeSnapshot
from config import DEFAULT_PERIOD, DEFAULT_INTERVAL

# ── Module-level logger ────────────────────────────────────────────────────────
logger: logging.Logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
_ROUND_DIGITS: Final[int] = 4


# ── Internal helpers (pure functions) ──────────────────────────────────────────

def _snapshot_to_dict(
    indicators: IndicatorSet,
    regime: RegimeSnapshot,
) -> dict:
    """Convert frozen dataclass outputs into a flat, JSON-safe dictionary.

    No computation happens here — values are copied verbatim from the
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

    return {
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


# ── Public API — ADK-compatible function tools ────────────────────────────────

def quant_engine_tool(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> dict:
    """Run the full deterministic quant pipeline for a single ticker.

    Executes three sequential steps — fetch, compute, classify — then
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
    # ── Step 1: Fetch OHLCV ────────────────────────────────────────────────────
    logger.info("[%s] Fetching quant snapshot (period=%s, interval=%s)", ticker, period, interval)
    market_data: MarketData = fetch_ohlcv(ticker, period=period, interval=interval)

    # ── Step 2: Compute indicators ─────────────────────────────────────────────
    indicators: IndicatorSet = compute_indicators(market_data)
    logger.info("[%s] Indicators computed", market_data.ticker)

    # ── Step 3: Classify regime ────────────────────────────────────────────────
    regime: RegimeSnapshot = classify_regime(indicators)
    logger.info("[%s] Regime classified → %s", market_data.ticker, regime.regime)

    # ── Step 4: Build flat dict ────────────────────────────────────────────────
    return _snapshot_to_dict(indicators, regime)


def quant_engine_batch_tool(
    tickers: list[str],
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> list[dict]:
    """Run the deterministic quant pipeline for multiple tickers.

    Uses :func:`~quant.data_fetcher.fetch_multiple` for batch fetching,
    then computes indicators and classifies regime for each successful
    fetch.  Tickers that fail at **any** stage (fetch, compute, classify)
    are skipped with a logged warning — partial results are returned
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

    # ── Step 1: Batch fetch (skips failures internally) ────────────────────────
    market_data_list: list[MarketData] = fetch_multiple(
        tickers, period=period, interval=interval,
    )

    # ── Step 2–3: Compute + classify each ──────────────────────────────────────
    results: list[dict] = []
    for md in market_data_list:
        try:
            indicators: IndicatorSet = compute_indicators(md)
            logger.info("[%s] Indicators computed", md.ticker)

            regime: RegimeSnapshot = classify_regime(indicators)
            logger.info("[%s] Regime classified → %s", md.ticker, regime.regime)

            results.append(_snapshot_to_dict(indicators, regime))
        except (ValueError, TypeError) as exc:
            logger.warning("[%s] Skipped during indicator/regime stage — %s", md.ticker, exc)

    logger.info(
        "Batch complete: %d/%d tickers succeeded",
        len(results), len(tickers),
    )

    return results


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Single-ticker tests ────────────────────────────────────────────────────
    test_tickers: list[str] = ["RELIANCE", "TCS", "^NSEI"]

    print("\n" + "=" * 70)
    print("  tools/quant_tool.py — Single-Ticker Tests")
    print("=" * 70)

    for t in test_tickers:
        try:
            snapshot: dict = quant_engine_tool(t)
            print(f"\n  ✓ {snapshot['ticker']} — {snapshot['regime']}")
            print(json.dumps(snapshot, indent=4))
        except (ValueError, RuntimeError) as err:
            print(f"\n  ✗ {t} — FAILED: {err}")

    # ── Batch test ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  tools/quant_tool.py — Batch Test")
    print("=" * 70)

    try:
        batch: list[dict] = quant_engine_batch_tool(test_tickers)
        print(f"\n  Batch returned {len(batch)}/{len(test_tickers)} snapshots:\n")
        for snap in batch:
            print(f"    {snap['ticker']:15s}  regime={snap['regime']:8s}  "
                  f"price={snap['price']:.2f}  rsi={snap['rsi']:.1f}  "
                  f"vol={snap['volatility']:.2%}")
    except (ValueError, RuntimeError) as err:
        print(f"\n  ✗ Batch FAILED: {err}")

    print("\n" + "=" * 70)
    print("  Done.")
    print("=" * 70 + "\n")
