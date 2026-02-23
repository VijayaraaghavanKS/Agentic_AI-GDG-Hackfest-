"""
quant/regime_classifier.py – Market Regime Classifier (Deterministic)
======================================================================
Pure-Python module that classifies the current market regime from a
computed :class:`~quant.indicators.IndicatorSet` snapshot.

Design principles:
    • Deterministic only — no LLM / Gemini / ADK logic.
    • No external ML libraries (no sklearn, no numpy, no randomness).
    • Fail-fast — invalid input raises immediately.
    • Production-grade — type hints, docstrings, frozen dataclass output.

Regime rules (strict, deterministic):
    BULL:    price > sma50 > sma200  AND  trend_strength > 0
    BEAR:    price < sma50 < sma200  AND  trend_strength < 0
    NEUTRAL: Everything else (mixed / transitional signals).

Data flow::

    MarketData  →  IndicatorSet  →  RegimeSnapshot
    (Layer 1)      (Layer 2)        (Layer 3 — this module)

Consumed by:
    • tools/quant_tool.py         → quant_engine_tool() Step 3
    • pipeline/orchestrator.py    → full pipeline entry-point
    • agents/*                    → agent reasoning over regime context

Public API:
    • classify_regime(indicators) → RegimeSnapshot
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

from quant.indicators import IndicatorSet

# ── Module-level logger ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
REGIME_BULL: Final[str] = "BULL"
REGIME_BEAR: Final[str] = "BEAR"
REGIME_NEUTRAL: Final[str] = "NEUTRAL"

VALID_REGIMES: Final[frozenset[str]] = frozenset(
    {REGIME_BULL, REGIME_BEAR, REGIME_NEUTRAL}
)


# ── Data Contract ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class RegimeSnapshot:
    """Immutable container for a classified market regime.

    This is the **final output** of the deterministic quant pipeline.
    All downstream consumers — Gemini agents, risk engine, orchestrator —
    read this to ground their reasoning in hard numbers.

    Attributes:
        ticker:          Yahoo Finance ticker symbol.
        regime:          Market regime string (``'BULL'``, ``'BEAR'``,
                         or ``'NEUTRAL'``).
        price:           Latest closing price.
        sma50:           50-day Simple Moving Average.
        sma200:          200-day Simple Moving Average.
        rsi:             Relative Strength Index (14-period).
        volatility:      Annualised volatility (decimal, e.g. 0.20 = 20%).
        trend_strength:  ``(price − sma50) / sma50`` — fractional deviation.
        timestamp:       UTC datetime of the latest candle.
    """

    ticker: str
    regime: str
    price: float
    sma50: float
    sma200: float
    rsi: float
    volatility: float
    trend_strength: float
    timestamp: datetime

    def __repr__(self) -> str:
        return (
            f"RegimeSnapshot({self.ticker}, regime={self.regime}, "
            f"price={self.price:.2f}, sma50={self.sma50:.2f}, "
            f"sma200={self.sma200:.2f}, rsi={self.rsi:.2f}, "
            f"volatility={self.volatility:.4f}, "
            f"trend_strength={self.trend_strength:+.4f}, "
            f"timestamp={self.timestamp:%Y-%m-%d %H:%M} UTC)"
        )


# ── Internal helpers (pure functions) ──────────────────────────────────────────

def _validate_indicator_set(indicators: IndicatorSet) -> None:
    """Validate the incoming IndicatorSet before classification.

    Checks performed:
        1. Type is :class:`IndicatorSet`.
        2. ``price > 0``.
        3. ``sma50 > 0``.
        4. ``sma200 > 0``.

    Args:
        indicators: The :class:`IndicatorSet` to validate.

    Raises:
        TypeError:  If *indicators* is not an :class:`IndicatorSet`.
        ValueError: If any numeric constraint is violated.
    """
    # 1. Type check
    if not isinstance(indicators, IndicatorSet):
        raise TypeError(
            f"Expected IndicatorSet instance, got {type(indicators).__name__}."
        )

    # 2. Price > 0
    if indicators.price <= 0:
        raise ValueError(
            f"[{indicators.ticker}] Invalid price: {indicators.price:.4f}. "
            f"Price must be > 0."
        )

    # 3. SMA50 > 0
    if indicators.sma50 <= 0:
        raise ValueError(
            f"[{indicators.ticker}] Invalid SMA50: {indicators.sma50:.4f}. "
            f"SMA50 must be > 0."
        )

    # 4. SMA200 > 0
    if indicators.sma200 <= 0:
        raise ValueError(
            f"[{indicators.ticker}] Invalid SMA200: {indicators.sma200:.4f}. "
            f"SMA200 must be > 0."
        )

    # 5. Finite number check — prevent NaN / Inf propagation
    _numeric_fields: dict[str, float] = {
        "price": indicators.price,
        "sma50": indicators.sma50,
        "sma200": indicators.sma200,
        "rsi": indicators.rsi,
        "volatility": indicators.volatility,
        "trend_strength": indicators.trend_strength,
    }
    _invalid: list[str] = [
        k for k, v in _numeric_fields.items() if not math.isfinite(v)
    ]
    if _invalid:
        raise ValueError(
            f"[{indicators.ticker}] Invalid indicator values: {sorted(_invalid)}. "
            f"All numeric fields must be finite."
        )


def _determine_regime(indicators: IndicatorSet) -> str:
    """Determine the market regime from indicator values.

    Rules (strict, deterministic):
        **BULL**:    ``price > sma50 > sma200``  AND  ``trend_strength > 0``
        **BEAR**:    ``price < sma50 < sma200``  AND  ``trend_strength < 0``
        **NEUTRAL**: Everything else.

    No probabilities.  No AI.  Pure rule-based classification.

    Args:
        indicators: A validated :class:`IndicatorSet`.

    Returns:
        One of ``'BULL'``, ``'BEAR'``, or ``'NEUTRAL'``.
    """
    price: float = indicators.price
    sma50: float = indicators.sma50
    sma200: float = indicators.sma200
    trend: float = indicators.trend_strength

    # BULL: price > sma50 > sma200 AND trend_strength > 0
    if price > sma50 > sma200 and trend > 0:
        return REGIME_BULL

    # BEAR: price < sma50 < sma200 AND trend_strength < 0
    if price < sma50 < sma200 and trend < 0:
        return REGIME_BEAR

    # NEUTRAL: everything else
    return REGIME_NEUTRAL


# ── Public API ─────────────────────────────────────────────────────────────────

def classify_regime(indicators: IndicatorSet) -> RegimeSnapshot:
    """Classify the market regime from computed indicators.

    This is the **single entry-point** for the regime classifier.  It
    accepts an :class:`~quant.indicators.IndicatorSet` instance (produced
    by :func:`~quant.indicators.compute_indicators`) and returns an
    immutable :class:`RegimeSnapshot`.

    Processing pipeline:
        1. Validate input (type, price > 0, SMAs > 0).
        2. Determine regime via deterministic rules.
        3. Build frozen :class:`RegimeSnapshot`.
        4. Log results.

    Args:
        indicators: A validated :class:`~quant.indicators.IndicatorSet`
                    instance with all indicator values populated.

    Returns:
        An immutable :class:`RegimeSnapshot` containing the regime
        classification and key indicator values.

    Raises:
        TypeError:  If *indicators* is not an :class:`IndicatorSet`.
        ValueError: If input validation fails.
    """
    # ── 1. Validate ────────────────────────────────────────────────────────────
    _validate_indicator_set(indicators)

    ticker: str = indicators.ticker
    logger.info("[%s] Classifying market regime", ticker)

    # ── 2. Determine regime ────────────────────────────────────────────────────
    regime: str = _determine_regime(indicators)

    # ── 3. Build snapshot ──────────────────────────────────────────────────────
    snapshot = RegimeSnapshot(
        ticker=indicators.ticker,
        regime=regime,
        price=indicators.price,
        sma50=indicators.sma50,
        sma200=indicators.sma200,
        rsi=indicators.rsi,
        volatility=indicators.volatility,
        trend_strength=indicators.trend_strength,
        timestamp=indicators.timestamp,
    )

    # ── 4. Log ─────────────────────────────────────────────────────────────────
    logger.info(
        "[%s] Regime = %s | Price=%.2f SMA50=%.2f SMA200=%.2f Trend=%.3f",
        ticker,
        regime,
        indicators.price,
        indicators.sma50,
        indicators.sma200,
        indicators.trend_strength,
    )

    return snapshot


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    from quant.data_fetcher import fetch_ohlcv
    from quant.indicators import compute_indicators

    test_ticker: str = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"

    try:
        data = fetch_ohlcv(test_ticker, period="1y", interval="1d")
        indicators = compute_indicators(data)
        regime = classify_regime(indicators)
    except (ValueError, RuntimeError, TypeError) as err:
        logger.error("FAILED: %s", err)
        sys.exit(1)

    now_str: str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("\n" + "=" * 60)
    print("  Market Regime Classified Successfully")
    print("=" * 60)
    print(f"  Ticker           : {regime.ticker}")
    print(f"  Regime           : {regime.regime}")
    print(f"  Price            : {regime.price:.2f}")
    print("-" * 60)
    print("  Moving Averages")
    print(f"    SMA 50         : {regime.sma50:.2f}")
    print(f"    SMA 200        : {regime.sma200:.2f}")
    print("-" * 60)
    print("  Indicators")
    print(f"    RSI (14)       : {regime.rsi:.2f}")
    print(f"    Volatility     : {regime.volatility:.2%}")
    print(f"    Trend Strength : {regime.trend_strength:+.4f}")
    print("-" * 60)
    print(f"  Timestamp        : {regime.timestamp:%Y-%m-%d}")
    print(f"  Fetched At       : {now_str}")
    print(f"  ✓ {regime.ticker} — regime = {regime.regime}")
    print("=" * 60)
    print(f"\n  {regime!r}\n")
