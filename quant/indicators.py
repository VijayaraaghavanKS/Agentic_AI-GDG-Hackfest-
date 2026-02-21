"""
quant/indicators.py – Technical Indicator Engine (Deterministic)
================================================================
Pure-Python module that computes technical indicators from a validated
``MarketData.dataframe`` produced by :mod:`quant.data_fetcher`.

Design principles:
    • Deterministic only — no LLM / Gemini / ADK logic.
    • No external indicator libraries (no pandas-ta) — all formulas
      implemented manually for auditability and zero hidden state.
    • Fail-fast — invalid input raises immediately.
    • Production-grade — type hints, docstrings, frozen dataclass output.

All indicators are computed from the standard OHLCV columns
``[open, high, low, close, volume]`` on a ``DatetimeIndex``.

Consumed by:
    • quant/regime_classifier.py  → classify_regime(indicator_set)
    • tools/quant_tool.py         → quant_engine_tool() Step 2
    • pipeline/orchestrator.py    → full pipeline entry-point
    • agents/*                    → agent reasoning over indicator values

Public API:
    • compute_indicators(market_data) → IndicatorSet
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Sequence

import numpy as np
import pandas as pd

from quant.data_fetcher import MarketData

# ── Module-level logger ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
REQUIRED_COLUMNS: Final[Sequence[str]] = ["open", "high", "low", "close", "volume"]
MIN_ROWS: Final[int] = 200

# ── Indicator Parameters ──────────────────────────────────────────────────────
RSI_PERIOD: Final[int] = 14
ATR_PERIOD: Final[int] = 14
SMA_20: Final[int] = 20
SMA_50: Final[int] = 50
SMA_200: Final[int] = 200
EMA_20: Final[int] = 20
EMA_50: Final[int] = 50
MOMENTUM_WINDOW: Final[int] = 20
ANNUALISATION_FACTOR: Final[float] = math.sqrt(252)


# ── Data Contract ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class IndicatorSet:
    """Immutable container for computed technical indicators.

    Every field is a scalar snapshot (the most-recent value) so that
    downstream consumers — agents, risk engine, regime classifier — can
    reason over a single, consistent point-in-time reading.

    Attributes:
        ticker:          Yahoo Finance ticker symbol.
        rsi:             Relative Strength Index (14-period, Wilder smoothing).
        atr:             Average True Range (14-period).
        sma20:           Simple Moving Average — 20-day.
        sma50:           Simple Moving Average — 50-day.
        sma200:          Simple Moving Average — 200-day.
        ema20:           Exponential Moving Average — 20-day.
        ema50:           Exponential Moving Average — 50-day.
        volatility:      Annualised volatility (daily returns σ × √252).
        momentum_20d:    20-day return (close[-1] / close[-21] − 1).
        trend_strength:  (price − sma50) / sma50.
        price:           Latest closing price.
        timestamp:       UTC datetime of the latest candle.
    """

    ticker: str
    rsi: float
    atr: float
    sma20: float
    sma50: float
    sma200: float
    ema20: float
    ema50: float
    volatility: float
    momentum_20d: float
    trend_strength: float
    price: float
    timestamp: datetime

    def __repr__(self) -> str:
        return (
            f"IndicatorSet(ticker={self.ticker!r}, price={self.price:.2f}, "
            f"rsi={self.rsi:.2f}, atr={self.atr:.2f}, "
            f"sma20={self.sma20:.2f}, sma50={self.sma50:.2f}, "
            f"sma200={self.sma200:.2f}, ema20={self.ema20:.2f}, "
            f"ema50={self.ema50:.2f}, volatility={self.volatility:.4f}, "
            f"momentum_20d={self.momentum_20d:.4f}, "
            f"trend_strength={self.trend_strength:.4f}, "
            f"timestamp={self.timestamp:%Y-%m-%d %H:%M} UTC)"
        )


# ── Input validation ──────────────────────────────────────────────────────────

def _validate_input(df: pd.DataFrame, ticker: str) -> None:
    """Validate the input DataFrame before any computation.

    Checks performed:
        1. Required OHLCV columns are present.
        2. Minimum row count (≥ 200).
        3. All OHLCV columns are numeric dtype.
        4. No NaN values in required columns.

    Args:
        df:     The ``MarketData.dataframe`` to validate.
        ticker: Ticker symbol for error messages.

    Raises:
        ValueError: If any validation rule is violated.
    """
    # 1. Column check
    missing: set[str] = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"[{ticker}] Missing required columns: {sorted(missing)}. "
            f"Available: {sorted(df.columns)}"
        )

    # 2. Minimum rows
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"[{ticker}] Insufficient data: {len(df)} rows, "
            f"minimum required is {MIN_ROWS}."
        )

    # 3. Numeric dtype check
    non_numeric: list[str] = [
        col for col in REQUIRED_COLUMNS
        if not pd.api.types.is_numeric_dtype(df[col])
    ]
    if non_numeric:
        raise ValueError(
            f"[{ticker}] Non-numeric OHLCV column detected: {sorted(non_numeric)}. "
            f"All OHLCV columns must have numeric dtype."
        )

    # 4. NaN check on required columns
    nan_counts: pd.Series = df[list(REQUIRED_COLUMNS)].isna().sum()
    has_nans: pd.Series = nan_counts[nan_counts > 0]
    if not has_nans.empty:
        detail: str = ", ".join(
            f"{col}={int(cnt)}" for col, cnt in has_nans.items()
        )
        raise ValueError(
            f"[{ticker}] NaN values detected in OHLCV columns: {detail}. "
            f"Clean data before computing indicators."
        )


# ── Indicator computation (pure functions) ─────────────────────────────────────

def _compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    """Compute the Relative Strength Index using Wilder smoothing.

    Wilder's smoothing is an exponential moving average with
    ``alpha = 1 / period``, which is equivalent to ``com = period - 1``
    in pandas EWM terminology.

    Args:
        close:  Series of closing prices (ascending time order).
        period: Look-back window (default 14).

    Returns:
        The most recent RSI value as a float in ``[0, 100]``.
    """
    delta: pd.Series = close.diff()

    gain: pd.Series = delta.where(delta > 0, 0.0)
    loss: pd.Series = (-delta).where(delta < 0, 0.0)

    # Wilder smoothing: alpha = 1/period  →  com = period - 1
    avg_gain: pd.Series = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss: pd.Series = loss.ewm(com=period - 1, min_periods=period).mean()

    rs: pd.Series = avg_gain / avg_loss
    rsi: pd.Series = 100.0 - (100.0 / (1.0 + rs))

    value: float = float(rsi.iloc[-1])
    if math.isnan(value):
        raise ValueError("RSI computation produced NaN.")
    return round(value, 4)


def _compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = ATR_PERIOD,
) -> float:
    """Compute Average True Range (ATR).

    True Range for each bar is::

        max(high − low,
            |high − prev_close|,
            |low  − prev_close|)

    ATR is the simple rolling mean of True Range over *period* bars.

    Args:
        high:   Series of high prices.
        low:    Series of low prices.
        close:  Series of closing prices.
        period: Look-back window (default 14).

    Returns:
        The most recent ATR value as a float.
    """
    prev_close: pd.Series = close.shift(1)

    tr1: pd.Series = high - low
    tr2: pd.Series = (high - prev_close).abs()
    tr3: pd.Series = (low - prev_close).abs()

    true_range: pd.DataFrame = pd.concat([tr1, tr2, tr3], axis=1)
    tr: pd.Series = true_range.max(axis=1)

    atr: pd.Series = tr.rolling(window=period, min_periods=period).mean()

    value: float = float(atr.iloc[-1])
    if math.isnan(value):
        raise ValueError("ATR computation produced NaN.")
    if value == 0.0:
        raise ValueError("ATR is zero — invalid OHLC series.")
    return round(value, 4)


def _compute_sma(close: pd.Series, window: int) -> float:
    """Compute the Simple Moving Average for a given window.

    Uses direct numpy slicing on the tail of the array for speed —
    avoids the overhead of a full rolling computation when only the
    last value is needed.

    Args:
        close:  Series of closing prices.
        window: Number of periods.

    Returns:
        The most recent SMA value as a float.
    """
    values: np.ndarray = close.values
    if len(values) < window:
        raise ValueError(f"SMA({window}) requires at least {window} rows.")
    value: float = float(np.mean(values[-window:]))
    if math.isnan(value):
        raise ValueError(f"SMA({window}) computation produced NaN.")
    return round(value, 4)


def _compute_ema(close: pd.Series, span: int) -> float:
    """Compute the Exponential Moving Average for a given span.

    Uses the standard EMA formula with ``span`` parameter (decay factor
    ``alpha = 2 / (span + 1)``).

    Args:
        close: Series of closing prices.
        span:  Number of periods.

    Returns:
        The most recent EMA value as a float.
    """
    ema: pd.Series = close.ewm(span=span, min_periods=span).mean()
    value: float = float(ema.iloc[-1])
    if math.isnan(value):
        raise ValueError(f"EMA({span}) computation produced NaN.")
    return round(value, 4)


def _compute_volatility(close: pd.Series) -> float:
    """Compute annualised volatility from daily returns.

    ``volatility = std(daily_returns) × √252``

    Uses simple percentage returns to match common quant conventions
    for equity markets.

    Args:
        close: Series of closing prices.

    Returns:
        Annualised volatility as a float (e.g. 0.25 = 25%).
    """
    daily_returns: np.ndarray = close.pct_change().dropna().values
    std_dev: float = float(np.std(daily_returns, ddof=1))
    value: float = std_dev * ANNUALISATION_FACTOR
    if math.isnan(value):
        raise ValueError("Volatility computation produced NaN.")
    if value == 0.0:
        raise ValueError("Volatility is zero — invalid price series.")
    return round(value, 4)


def _compute_momentum(close: pd.Series, window: int = MOMENTUM_WINDOW) -> float:
    """Compute momentum as the *window*-day return.

    ``momentum = close[-1] / close[-(window+1)] − 1``

    Args:
        close:  Series of closing prices.
        window: Look-back period in trading days (default 20).

    Returns:
        Fractional return (e.g. 0.05 = +5%).
    """
    close_values: np.ndarray = close.values
    if len(close_values) < window + 1:
        raise ValueError(
            f"Momentum requires at least {window + 1} rows, got {len(close_values)}."
        )
    current: float = float(close_values[-1])
    past: float = float(close_values[-(window + 1)])
    if past == 0:
        raise ValueError("Momentum denominator is zero — invalid price data.")
    value: float = (current / past) - 1.0
    if math.isnan(value):
        raise ValueError("Momentum computation produced NaN.")
    return round(value, 4)


def _compute_trend_strength(price: float, sma50: float) -> float:
    """Compute trend strength as deviation from 50-day SMA.

    ``trend_strength = (price − sma50) / sma50``

    Positive values indicate the price is above the 50-day moving
    average; negative values indicate it is below.

    Args:
        price: Latest closing price.
        sma50: Current 50-day SMA value.

    Returns:
        Fractional deviation (e.g. 0.05 = +5% above 50DMA).
    """
    if sma50 == 0:
        raise ValueError("Trend strength denominator (SMA50) is zero.")
    value: float = (price - sma50) / sma50
    if math.isnan(value):
        raise ValueError("Trend strength computation produced NaN.")
    return round(value, 4)


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_indicators(market_data: MarketData) -> IndicatorSet:
    """Compute all technical indicators from validated market data.

    This is the **single entry-point** for the indicator engine.  It
    accepts a :class:`~quant.data_fetcher.MarketData` instance (produced
    by :func:`~quant.data_fetcher.fetch_ohlcv`) and returns an immutable
    :class:`IndicatorSet` snapshot.

    Processing pipeline:
        1. Validate input (columns, row count, NaNs).
        2. Extract OHLCV series.
        3. Compute RSI (14, Wilder smoothing).
        4. Compute ATR (14).
        5. Compute SMA-20, SMA-50, SMA-200.
        6. Compute EMA-20, EMA-50.
        7. Compute annualised volatility.
        8. Compute 20-day momentum.
        9. Compute trend strength (price vs SMA-50).
        10. Assemble & return frozen ``IndicatorSet``.

    Args:
        market_data: A validated :class:`~quant.data_fetcher.MarketData`
                     instance with ≥ 200 rows and clean OHLCV columns.

    Returns:
        An immutable :class:`IndicatorSet` containing all computed
        indicator values as scalars (latest bar).

    Raises:
        TypeError:  If *market_data* is not a :class:`MarketData` instance.
        ValueError: If input validation fails or any indicator produces NaN.
    """
    # ── Type guard ─────────────────────────────────────────────────────────────
    if not isinstance(market_data, MarketData):
        raise TypeError(
            f"Expected MarketData instance, got {type(market_data).__name__}."
        )

    ticker: str = market_data.ticker
    df: pd.DataFrame = market_data.dataframe

    logger.info("[%s] Computing technical indicators (%d rows) …", ticker, len(df))

    # ── 0. Defensive sort (consistent with data_fetcher) ──────────────────────
    df = df.sort_index()

    # ── 1. Validate ────────────────────────────────────────────────────────────
    _validate_input(df, ticker)

    # ── 2. Extract series ──────────────────────────────────────────────────────
    high: pd.Series = df["high"]
    low: pd.Series = df["low"]
    close: pd.Series = df["close"]

    # ── 3. RSI ─────────────────────────────────────────────────────────────────
    rsi: float = _compute_rsi(close, RSI_PERIOD)
    logger.debug("[%s] RSI(14) = %.2f", ticker, rsi)

    # ── 4. ATR ─────────────────────────────────────────────────────────────────
    atr: float = _compute_atr(high, low, close, ATR_PERIOD)
    logger.debug("[%s] ATR(14) = %.2f", ticker, atr)

    # ── 5. Moving Averages (SMA) ──────────────────────────────────────────────
    sma20: float = _compute_sma(close, SMA_20)
    sma50: float = _compute_sma(close, SMA_50)
    sma200: float = _compute_sma(close, SMA_200)
    logger.debug("[%s] SMA20=%.2f  SMA50=%.2f  SMA200=%.2f", ticker, sma20, sma50, sma200)

    # ── 6. Moving Averages (EMA) ──────────────────────────────────────────────
    ema20: float = _compute_ema(close, EMA_20)
    ema50: float = _compute_ema(close, EMA_50)
    logger.debug("[%s] EMA20=%.2f  EMA50=%.2f", ticker, ema20, ema50)

    # ── 7. Volatility ─────────────────────────────────────────────────────────
    volatility: float = _compute_volatility(close)
    logger.debug("[%s] Volatility = %.4f", ticker, volatility)

    # ── 8. Momentum ────────────────────────────────────────────────────────────
    momentum_20d: float = _compute_momentum(close, MOMENTUM_WINDOW)
    logger.debug("[%s] Momentum(20d) = %.4f", ticker, momentum_20d)

    # ── 9. Trend Strength ─────────────────────────────────────────────────────
    price: float = round(float(close.iloc[-1]), 4)
    trend_strength: float = _compute_trend_strength(price, sma50)
    logger.debug("[%s] Trend strength = %.4f", ticker, trend_strength)

    # ── 10. Timestamp ──────────────────────────────────────────────────────────
    last_ts: pd.Timestamp = pd.Timestamp(df.index[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    else:
        last_ts = last_ts.tz_convert("UTC")
    timestamp: datetime = last_ts.to_pydatetime()

    # ── 11. Final sanity check — all values must be finite ─────────────────────
    _numeric_fields: dict[str, float] = {
        "rsi": rsi, "atr": atr, "sma20": sma20, "sma50": sma50,
        "sma200": sma200, "ema20": ema20, "ema50": ema50,
        "volatility": volatility, "momentum_20d": momentum_20d,
        "trend_strength": trend_strength, "price": price,
    }
    _invalid: list[str] = [
        name for name, val in _numeric_fields.items()
        if not math.isfinite(val)
    ]
    if _invalid:
        raise ValueError(
            f"[{ticker}] IndicatorSet contains invalid values: {sorted(_invalid)}. "
            f"All indicator fields must be finite."
        )

    # ── 12. Assemble ───────────────────────────────────────────────────────────
    indicator_set = IndicatorSet(
        ticker=ticker,
        rsi=rsi,
        atr=atr,
        sma20=sma20,
        sma50=sma50,
        sma200=sma200,
        ema20=ema20,
        ema50=ema50,
        volatility=volatility,
        momentum_20d=momentum_20d,
        trend_strength=trend_strength,
        price=price,
        timestamp=timestamp,
    )

    logger.info(
        "[%s] Indicators computed — RSI=%.1f  ATR=%.2f  Vol=%.2f%%  "
        "Mom=%.2f%%  Trend=%.4f",
        ticker, rsi, atr, volatility * 100, momentum_20d * 100, trend_strength,
    )

    return indicator_set


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    from quant.data_fetcher import fetch_ohlcv

    test_ticker: str = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"

    try:
        data: MarketData = fetch_ohlcv(test_ticker, period="1y", interval="1d")
        indicators: IndicatorSet = compute_indicators(data)
    except (ValueError, RuntimeError, TypeError) as err:
        logger.error("FAILED: %s", err)
        sys.exit(1)

    now_str: str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    print("\n" + "=" * 60)
    print("  Technical Indicators Computed Successfully")
    print("=" * 60)
    print(f"  Ticker          : {indicators.ticker}")
    print(f"  Price            : {indicators.price:.2f}")
    print(f"  Timestamp        : {indicators.timestamp:%Y-%m-%d}")
    print("-" * 60)
    print("  Trend")
    print(f"    SMA 20         : {indicators.sma20:.2f}")
    print(f"    SMA 50         : {indicators.sma50:.2f}")
    print(f"    SMA 200        : {indicators.sma200:.2f}")
    print(f"    EMA 20         : {indicators.ema20:.2f}")
    print(f"    EMA 50         : {indicators.ema50:.2f}")
    print(f"    Trend Strength : {indicators.trend_strength:+.4f}")
    print("-" * 60)
    print("  Momentum & Volatility")
    print(f"    RSI (14)       : {indicators.rsi:.2f}")
    print(f"    ATR (14)       : {indicators.atr:.2f}")
    print(f"    Volatility     : {indicators.volatility:.2%}")
    print(f"    Momentum (20d) : {indicators.momentum_20d:+.2%}")
    print("=" * 60)
    print(f"  Fetched At       : {now_str}")
    print(f"  ✓ {indicators.ticker} — indicators ready for regime classifier")
    print("=" * 60 + "\n")
