"""
quant/data_fetcher.py – OHLCV Data Fetcher
============================================
Pure-Python module that fetches, validates, and standardises OHLCV market
data via Yahoo Finance (yfinance).  Returns a ``MarketData`` dataclass —
never a raw DataFrame — so every downstream consumer works with a
guaranteed-clean, typed contract.

Design principles:
    • Deterministic only — no LLM / Gemini / ADK logic.
    • Fail-fast — bad data raises immediately; no silent NaN propagation.
    • Production-grade — type hints, docstrings, dataclass output.

Consumed by:
    • quant/indicators.py       → compute_indicators(market_data.dataframe)
    • quant/regime_classifier.py → classify_regime(...)
    • tools/quant_tool.py        → quant_engine_tool() Step 1
    • pipeline/orchestrator.py   → full pipeline entry-point
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final

import pandas as pd
import yfinance as yf

from config import DEFAULT_PERIOD, DEFAULT_INTERVAL

# ── Module-level logger ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
REQUIRED_COLUMNS: Final[list[str]] = ["open", "high", "low", "close", "volume"]
MIN_ROWS: Final[int] = 200
FRESHNESS_DAYS: Final[int] = 10


# ── Data Contract ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class MarketData:
    """Immutable container for validated OHLCV market data.

    Attributes:
        ticker:       Yahoo Finance ticker symbol (e.g. ``RELIANCE.NS``).
        dataframe:    Cleaned pandas DataFrame with lowercase columns
                      [open, high, low, close, volume] and a DatetimeIndex.
        last_updated: UTC timestamp of the most recent candle in *dataframe*.
        rows:         Number of rows after cleaning.
        period:       The ``yfinance`` period string used to fetch the data.
        interval:     The ``yfinance`` interval string used to fetch the data.
    """

    ticker: str
    dataframe: pd.DataFrame
    last_updated: datetime
    rows: int
    period: str = field(default="1y")
    interval: str = field(default="1d")

    def __repr__(self) -> str:
        return (
            f"MarketData(ticker={self.ticker!r}, rows={self.rows}, "
            f"last_updated={self.last_updated:%Y-%m-%d %H:%M}, "
            f"period={self.period!r}, interval={self.interval!r})"
        )


# ── Validation helpers (pure functions) ────────────────────────────────────────

def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names and flatten any MultiIndex columns.

    yfinance ≥ 0.2.50 may return a MultiIndex when ``group_by='ticker'``
    is used or when a single ticker still produces a two-level header.
    This helper normalises both cases into flat, lowercase column names.
    """
    # Flatten MultiIndex columns (e.g. ('Close', 'RELIANCE.NS') → 'Close')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _validate_columns(df: pd.DataFrame, ticker: str) -> None:
    """Ensure all required OHLCV columns exist after standardisation."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"[{ticker}] Missing required columns: {sorted(missing)}. "
            f"Available: {list(df.columns)}"
        )


def _drop_nans(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Drop rows with *any* NaN in the OHLCV columns and log the count."""
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped = before - len(df)
    if dropped:
        logger.info("[%s] Dropped %d NaN rows (%.1f%%).", ticker, dropped, dropped / before * 100)
    return df


def _validate_row_count(df: pd.DataFrame, ticker: str) -> None:
    """Ensure the DataFrame has at least ``MIN_ROWS`` rows."""
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"[{ticker}] Insufficient data: {len(df)} rows returned, "
            f"minimum required is {MIN_ROWS}. "
            f"Try a longer period or check if the ticker is valid."
        )


def _validate_freshness(df: pd.DataFrame, ticker: str) -> None:
    """Ensure the most recent candle is within ``FRESHNESS_DAYS`` of now.

    Uses UTC throughout to avoid timezone ambiguity.
    """
    last_date = pd.Timestamp(df.index[-1])

    # Make timezone-aware (UTC) if naive
    if last_date.tzinfo is None:
        last_date = last_date.tz_localize("UTC")
    else:
        last_date = last_date.tz_convert("UTC")

    now_utc = pd.Timestamp.now(tz="UTC")
    staleness = (now_utc - last_date).days

    if staleness > FRESHNESS_DAYS:
        raise ValueError(
            f"[{ticker}] Stale data: last candle is {staleness} days old "
            f"({last_date:%Y-%m-%d}). Maximum allowed staleness is "
            f"{FRESHNESS_DAYS} days. Market may be closed or ticker delisted."
        )


def _validate_ticker_format(ticker: str) -> None:
    """Basic sanity check on ticker string."""
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string.")
    if " " in ticker.strip():
        raise ValueError(f"Ticker must not contain spaces: {ticker!r}")


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_ohlcv(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> MarketData:
    """Fetch, validate, and return OHLCV data for a single ticker.

    Pipeline:
        1. Validate ticker format.
        2. Download data via ``yfinance.download()``.
        3. Flatten & lowercase column names.
        4. Verify required OHLCV columns exist.
        5. Drop NaN rows.
        6. Enforce minimum row count (≥ 200).
        7. Enforce freshness (last candle ≤ 10 days old).
        8. Return an immutable ``MarketData`` dataclass.

    Args:
        ticker:   Yahoo Finance symbol (e.g. ``'RELIANCE.NS'``).
        period:   Look-back window — ``'1y'``, ``'6mo'``, ``'2y'``, etc.
        interval: Candle granularity — ``'1d'`` (daily) is the only
                  supported value for this system.

    Returns:
        A validated :class:`MarketData` instance.

    Raises:
        ValueError:    Empty data, missing columns, too few rows, or stale.
        RuntimeError:  Network / yfinance failure.
    """
    _validate_ticker_format(ticker)
    ticker = ticker.strip().upper()

    logger.info("[%s] Fetching OHLCV data  (period=%s, interval=%s) …", ticker, period, interval)

    # ── 1. Download ────────────────────────────────────────────────────────────
    try:
        df: pd.DataFrame = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        raise RuntimeError(
            f"[{ticker}] Failed to fetch data from Yahoo Finance: {exc}"
        ) from exc

    # ── 2. Empty check ─────────────────────────────────────────────────────────
    if df is None or df.empty:
        raise ValueError(
            f"[{ticker}] No data returned for ticker. "
            f"Verify the symbol exists on Yahoo Finance."
        )

    # ── 3. Standardise columns ─────────────────────────────────────────────────
    df = _standardise_columns(df)

    # ── 4. Column validation ───────────────────────────────────────────────────
    _validate_columns(df, ticker)

    # Keep only the required columns (drop adj_close, dividends, etc.)
    df = df[REQUIRED_COLUMNS].copy()

    # ── 5. NaN removal ─────────────────────────────────────────────────────────
    df = _drop_nans(df, ticker)

    # ── 6. Minimum row count ───────────────────────────────────────────────────
    _validate_row_count(df, ticker)

    # ── 7. Freshness check ─────────────────────────────────────────────────────
    _validate_freshness(df, ticker)

    # ── 8. Build & return MarketData ───────────────────────────────────────────
    last_ts = pd.Timestamp(df.index[-1])
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize("UTC")
    else:
        last_ts = last_ts.tz_convert("UTC")

    market_data = MarketData(
        ticker=ticker,
        dataframe=df,
        last_updated=last_ts.to_pydatetime(),
        rows=len(df),
        period=period,
        interval=interval,
    )

    logger.info("[%s] ✓ Loaded %d rows — last candle: %s", ticker, market_data.rows, f"{market_data.last_updated:%Y-%m-%d}")

    return market_data


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    test_ticker = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"

    try:
        data = fetch_ohlcv(test_ticker, period="1y", interval="1d")
    except (ValueError, RuntimeError) as err:
        logger.error("FAILED: %s", err)
        sys.exit(1)

    print("\n" + "=" * 55)
    print("  Market Data Loaded")
    print("=" * 55)
    print(f"  Ticker      : {data.ticker}")
    print(f"  Rows        : {data.rows}")
    print(f"  Last Update : {data.last_updated:%Y-%m-%d}")
    print(f"  Period      : {data.period}")
    print(f"  Interval    : {data.interval}")
    print("-" * 55)
    print(data.dataframe.tail(5).to_string())
    print("=" * 55 + "\n")
