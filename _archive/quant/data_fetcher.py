"""
quant/data_fetcher.py – OHLCV Data Fetcher (Single Source of Truth)
====================================================================
Pure-Python module that fetches, validates, and standardises OHLCV market
data via Yahoo Finance (yfinance).  Returns a ``MarketData`` dataclass —
never a raw DataFrame — so every downstream consumer works with a
guaranteed-clean, typed contract.

Design principles:
    • Deterministic only — no LLM / Gemini / ADK logic.
    • Fail-fast — bad data raises immediately; no silent NaN propagation.
    • Production-grade — type hints, docstrings, dataclass output.
    • Single Source of Truth — all market data flows through this module.

Consumed by:
    • quant/indicators.py        → compute_indicators(market_data.dataframe)
    • quant/regime_classifier.py  → classify_regime(...)
    • tools/quant_tool.py         → quant_engine_tool() Step 1
    • pipeline/orchestrator.py    → full pipeline entry-point

Public API:
    • fetch_ohlcv(ticker, period, interval)  → MarketData
    • fetch_multiple(tickers, period, interval) → list[MarketData]
    • fetch_nifty(period, interval)  → MarketData   (^NSEI)
    • fetch_banknifty(period, interval) → MarketData (^NSEBANK)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final, Sequence

import pandas as pd
import yfinance as yf

from config import DEFAULT_PERIOD, DEFAULT_INTERVAL

# ── Module-level logger ────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
REQUIRED_COLUMNS: Final[list[str]] = ["open", "high", "low", "close", "volume"]
MIN_ROWS: Final[int] = 200
FRESHNESS_DAYS: Final[int] = 10

# Index tickers (never append exchange suffix)
_NIFTY_50: Final[str] = "^NSEI"
_BANK_NIFTY: Final[str] = "^NSEBANK"

# Exchange suffix applied when a bare ticker is provided
_NSE_SUFFIX: Final[str] = ".NS"


# ── Data Contract ──────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class MarketData:
    """Immutable container for validated OHLCV market data.

    This is the **only** object downstream modules should pass around for
    price data.  The frozen dataclass prevents accidental mutation of the
    validated payload after construction.

    Attributes:
        ticker:       Yahoo Finance ticker symbol (e.g. ``'RELIANCE.NS'``).
        dataframe:    Cleaned :class:`~pandas.DataFrame` with lowercase
                      columns ``[open, high, low, close, volume]`` and a
                      sorted :class:`~pandas.DatetimeIndex`.
        last_updated: UTC :class:`~datetime.datetime` of the most recent
                      candle in *dataframe*.
        rows:         Number of rows after all cleaning steps.
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
            f"last_updated={self.last_updated:%Y-%m-%d %H:%M} UTC, "
            f"period={self.period!r}, interval={self.interval!r})"
        )


# ── Internal helpers (pure functions) ──────────────────────────────────────────

def _normalise_ticker(ticker: str) -> str:
    """Normalise a raw ticker string for Yahoo Finance.

    Rules:
        1. Strip whitespace, convert to uppercase.
        2. Index tickers (starting with ``^``) are returned as-is.
        3. Tickers already carrying an exchange suffix (e.g. ``.NS``,
           ``.BO``) are returned unchanged.
        4. Bare tickers (e.g. ``RELIANCE``) get ``.NS`` appended.

    Args:
        ticker: Raw ticker string from the caller.

    Returns:
        Cleaned Yahoo Finance symbol string.

    Raises:
        ValueError: If *ticker* is empty or contains spaces.
    """
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker must be a non-empty string.")
    ticker = ticker.strip().upper()
    if " " in ticker:
        raise ValueError(f"Ticker must not contain spaces: {ticker!r}")

    # Index symbols — never modify
    if ticker.startswith("^"):
        return ticker

    # Already has an exchange suffix (.NS, .BO, etc.)
    if "." in ticker:
        return ticker

    # Bare ticker → assume NSE
    logger.debug("[%s] No exchange suffix detected — appending %s", ticker, _NSE_SUFFIX)
    return f"{ticker}{_NSE_SUFFIX}"


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten any MultiIndex columns and lowercase all column names.

    yfinance ≥ 0.2.50 may return a :class:`~pandas.MultiIndex` when
    ``group_by='ticker'`` is active or even for a single ticker.  This
    helper normalises both cases into flat, lowercase string column names.

    Args:
        df: Raw DataFrame from ``yfinance.download()``.

    Returns:
        The same DataFrame with flat, lowercase, stripped column names.
    """
    # Flatten MultiIndex columns (e.g. ('Close', 'RELIANCE.NS') → 'Close')
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Safe cast: yfinance occasionally returns non-string column labels
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _validate_columns(df: pd.DataFrame, ticker: str) -> None:
    """Ensure all required OHLCV columns exist after standardisation.

    Args:
        df:     Standardised DataFrame.
        ticker: Ticker symbol for error messages.

    Raises:
        ValueError: If any of ``[open, high, low, close, volume]`` is missing.
    """
    missing: set[str] = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"[{ticker}] Missing required OHLCV columns: {sorted(missing)}. "
            f"Available columns: {sorted(df.columns)}"
        )


def _drop_nans(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Drop rows with *any* NaN in the required OHLCV columns.

    Args:
        df:     DataFrame to clean.
        ticker: Ticker symbol for logging.

    Returns:
        Cleaned DataFrame with NaN rows removed.
    """
    before: int = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS)
    dropped: int = before - len(df)
    if dropped:
        pct: float = (dropped / before * 100) if before else 0.0
        logger.info(
            "[%s] Dropped %d NaN rows (%.1f%% of %d total).",
            ticker, dropped, pct, before,
        )
    return df


def _validate_row_count(df: pd.DataFrame, ticker: str) -> None:
    """Ensure the DataFrame contains at least ``MIN_ROWS`` rows.

    Args:
        df:     Cleaned DataFrame.
        ticker: Ticker symbol for error messages.

    Raises:
        ValueError: If row count is below ``MIN_ROWS`` (200).
    """
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"[{ticker}] Insufficient OHLCV data: only {len(df)} rows "
            f"returned, minimum required is {MIN_ROWS}. "
            f"Try a longer period or verify the ticker is actively traded."
        )


def _to_utc_timestamp(ts: pd.Timestamp) -> pd.Timestamp:
    """Convert a pandas Timestamp to UTC, handling both naive and aware inputs.

    Args:
        ts: Any :class:`~pandas.Timestamp`.

    Returns:
        Timezone-aware UTC Timestamp.
    """
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _validate_freshness(df: pd.DataFrame, ticker: str) -> None:
    """Ensure the most recent candle is within ``FRESHNESS_DAYS`` of now.

    All comparisons are made in UTC to avoid timezone ambiguity.

    Args:
        df:     Sorted, cleaned DataFrame with a DatetimeIndex.
        ticker: Ticker symbol for error messages.

    Raises:
        ValueError: If the last candle is older than ``FRESHNESS_DAYS`` days.
    """
    last_date: pd.Timestamp = _to_utc_timestamp(pd.Timestamp(df.index[-1]))
    now_utc: pd.Timestamp = pd.Timestamp.now(tz="UTC")
    staleness: int = (now_utc - last_date).days

    if staleness > FRESHNESS_DAYS:
        raise ValueError(
            f"[{ticker}] Stale OHLCV data: last candle is {staleness} days old "
            f"({last_date:%Y-%m-%d}). Maximum allowed staleness is "
            f"{FRESHNESS_DAYS} days. The market may be closed, or the ticker "
            f"may be delisted or suspended."
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_ohlcv(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> MarketData:
    """Fetch, validate, and return OHLCV data for a single ticker.

    This is the **primary entry-point** for all market data in the system.
    Every downstream module (indicators, regime classifier, quant tool,
    orchestrator) calls this function and receives a guaranteed-clean
    :class:`MarketData` object.

    Processing pipeline:
        1. Normalise & validate ticker format.
        2. Download data via ``yfinance.download()``.
        3. Flatten & lowercase column names.
        4. Verify required OHLCV columns exist.
        5. Retain only ``[open, high, low, close, volume]``.
        6. Drop NaN rows.
        7. Enforce minimum row count (≥ 200).
        8. Sort by time index (ascending).
        9. Enforce freshness (last candle ≤ 10 days old).
        10. Defensive copy to prevent mutation leaks.
        11. Return an immutable ``MarketData`` dataclass.

    Args:
        ticker:   Yahoo Finance symbol (e.g. ``'RELIANCE.NS'``,
                  ``'TCS'``, ``'^NSEI'``).  Bare tickers without an
                  exchange suffix are assumed to be NSE and get ``.NS``
                  appended automatically.
        period:   Look-back window — ``'1y'``, ``'6mo'``, ``'2y'``, etc.
                  Defaults to config ``DEFAULT_PERIOD`` (``'1y'``).
        interval: Candle granularity — ``'1d'`` (daily) is the only
                  supported value for this system.  Defaults to config
                  ``DEFAULT_INTERVAL`` (``'1d'``).

    Returns:
        A validated, immutable :class:`MarketData` instance containing
        the cleaned DataFrame, row count, and UTC timestamp of the latest
        candle.

    Raises:
        ValueError:    Empty data, missing columns, too few rows, stale
                       data, or invalid ticker format.
        RuntimeError:  Network failure or yfinance internal error.
    """
    # ── 0. Normalise ticker ────────────────────────────────────────────────────
    ticker = _normalise_ticker(ticker)

    logger.info(
        "[%s] Fetching OHLCV data (period=%s, interval=%s) …",
        ticker, period, interval,
    )

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
            f"[{ticker}] Failed to fetch OHLCV data from Yahoo Finance. "
            f"Check network connectivity and ticker validity. Detail: {exc}"
        ) from exc

    # ── 2. Empty check ─────────────────────────────────────────────────────────
    if df is None or df.empty:
        raise ValueError(
            f"[{ticker}] No OHLCV data returned from Yahoo Finance. "
            f"Check ticker symbol or market availability."
        )

    # ── 3. Standardise columns ─────────────────────────────────────────────────
    df = _standardise_columns(df)

    # ── 4. Column validation ───────────────────────────────────────────────────
    _validate_columns(df, ticker)

    # ── 5. Retain only required columns ────────────────────────────────────────
    df = df[REQUIRED_COLUMNS].copy()

    # ── 6. NaN removal ─────────────────────────────────────────────────────────
    df = _drop_nans(df, ticker)

    # ── 7. Minimum row count ───────────────────────────────────────────────────
    _validate_row_count(df, ticker)

    # ── 8. Sort by time index (Yahoo sometimes returns unsorted rows) ──────────
    df = df.sort_index()

    # ── 9. Freshness check ─────────────────────────────────────────────────────
    _validate_freshness(df, ticker)

    # ── 10. Defensive copy (prevent mutation leaking into MarketData) ──────────
    df = df.copy()

    # ── 11. Build & return MarketData ──────────────────────────────────────────
    last_ts: pd.Timestamp = _to_utc_timestamp(pd.Timestamp(df.index[-1]))

    market_data = MarketData(
        ticker=ticker,
        dataframe=df,
        last_updated=last_ts.to_pydatetime(),
        rows=len(df),
        period=period,
        interval=interval,
    )

    logger.info(
        "[%s] Loaded %d validated OHLCV rows (last candle %s)",
        ticker, market_data.rows, f"{market_data.last_updated:%Y-%m-%d}",
    )

    return market_data


def fetch_multiple(
    tickers: Sequence[str],
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> list[MarketData]:
    """Fetch OHLCV data for multiple tickers sequentially.

    Iterates over *tickers* and calls :func:`fetch_ohlcv` for each.
    Tickers that fail are logged and skipped — a partial result is
    returned rather than aborting the entire batch.

    Args:
        tickers:  Iterable of Yahoo Finance symbols.
        period:   Look-back window (default ``DEFAULT_PERIOD``).
        interval: Candle granularity (default ``DEFAULT_INTERVAL``).

    Returns:
        A list of :class:`MarketData` objects for every ticker that
        succeeded.  May be shorter than *tickers* if some failed.

    Raises:
        ValueError: If *tickers* is empty.
    """
    if not tickers:
        raise ValueError("Ticker list must not be empty.")

    results: list[MarketData] = []
    for t in tickers:
        try:
            results.append(fetch_ohlcv(t, period=period, interval=interval))
        except (ValueError, RuntimeError) as exc:
            logger.warning("[%s] Skipped — %s", t, exc)
    return results


def fetch_nifty(
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> MarketData:
    """Convenience wrapper: fetch NIFTY 50 index (``^NSEI``).

    Args:
        period:   Look-back window (default ``DEFAULT_PERIOD``).
        interval: Candle granularity (default ``DEFAULT_INTERVAL``).

    Returns:
        Validated :class:`MarketData` for NIFTY 50.

    Raises:
        ValueError:   If data validation fails.
        RuntimeError: If the download fails.
    """
    return fetch_ohlcv(_NIFTY_50, period=period, interval=interval)


def fetch_banknifty(
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> MarketData:
    """Convenience wrapper: fetch BANK NIFTY index (``^NSEBANK``).

    Args:
        period:   Look-back window (default ``DEFAULT_PERIOD``).
        interval: Candle granularity (default ``DEFAULT_INTERVAL``).

    Returns:
        Validated :class:`MarketData` for BANK NIFTY.

    Raises:
        ValueError:   If data validation fails.
        RuntimeError: If the download fails.
    """
    return fetch_ohlcv(_BANK_NIFTY, period=period, interval=interval)


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    test_ticker: str = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"

    try:
        data: MarketData = fetch_ohlcv(test_ticker, period="1y", interval="1d")
    except (ValueError, RuntimeError) as err:
        logger.error("FAILED: %s", err)
        sys.exit(1)

    now_str: str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    freshness_days: int = (
        datetime.now(tz=timezone.utc) - data.last_updated
    ).days

    print("\n" + "=" * 60)
    print("  Market Data Loaded Successfully")
    print("=" * 60)
    print(f"  Ticker        : {data.ticker}")
    print(f"  Rows          : {data.rows}")
    print(f"  Period        : {data.period}")
    print(f"  Interval      : {data.interval}")
    print(f"  Last Candle   : {data.last_updated:%Y-%m-%d}")
    print(f"  Freshness     : {freshness_days} day(s) ago")
    print(f"  Fetched At    : {now_str}")
    print("-" * 60)
    print("  Last 5 Rows:")
    print("-" * 60)
    print(data.dataframe.tail(5).to_string())
    print("=" * 60)
    print(f"  ✓ {data.ticker} — {data.rows} rows ready for indicator pipeline")
    print("=" * 60 + "\n")
