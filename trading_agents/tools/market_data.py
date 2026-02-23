"""Live NSE market data fetching via yfinance.

Includes production-grade validation:
- NaN scrubbing on all price/volume arrays
- Minimum 60 trading days required (prevents stale/thin data)
- Freshness metadata for audit trail
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
from typing import Dict, List

import yfinance as yf

from trading_agents.config import DATA_LOOKBACK_DAYS

_MIN_TRADING_DAYS = 60


def _scrub_nans(values: List[float], fallback: float = 0.0) -> List[float]:
    """Replace NaN/Inf values with fallback, ensuring all entries are finite."""
    return [round(float(v), 2) if math.isfinite(v) else fallback for v in values]


def fetch_index_data(symbol: str = "^NSEI", days: int = DATA_LOOKBACK_DAYS) -> Dict:
    """Fetch daily OHLCV data for a market index (default: Nifty 50).

    Args:
        symbol: Yahoo Finance ticker symbol for the index.
        days: Number of calendar days of history to fetch.

    Returns:
        dict with status, closes, highs, lows, volumes, metadata.
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{days}d", interval="1d")

    if hist is None or hist.empty:
        return {
            "status": "error",
            "error_message": f"No data returned for '{symbol}'. Market may be closed or symbol invalid.",
        }

    closes = _scrub_nans(hist["Close"].tolist())
    highs = _scrub_nans(hist["High"].tolist(), fallback=closes[-1] if closes else 0)
    lows = _scrub_nans(hist["Low"].tolist(), fallback=closes[-1] if closes else 0)
    volumes = [int(v) if math.isfinite(v) else 0 for v in hist["Volume"].tolist()]

    # Filter out days where close is 0 (bad data)
    valid_closes = [c for c in closes if c > 0]
    if len(valid_closes) < _MIN_TRADING_DAYS:
        return {
            "status": "error",
            "error_message": f"Only {len(valid_closes)} valid trading days for '{symbol}'. Need at least {_MIN_TRADING_DAYS}.",
        }

    last_ts = str(hist.index[-1])

    return {
        "status": "success",
        "symbol": symbol,
        "source": "Yahoo Finance (yfinance)",
        "fetched_at_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "last_trade_date": last_ts,
        "trading_days": len(closes),
        "latest_close": closes[-1],
        "last_5_closes": closes[-5:],
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
    }


def fetch_stock_data(symbol: str, days: int = DATA_LOOKBACK_DAYS) -> Dict:
    """Fetch daily OHLCV data for an individual NSE stock.

    Args:
        symbol: Yahoo Finance ticker (e.g. 'RELIANCE.NS').
        days: Number of calendar days of history to fetch.

    Returns:
        dict with status, closes, highs, lows, volumes, metadata.
    """
    if not symbol.upper().endswith(".NS") and not symbol.startswith("^"):
        symbol = symbol.upper() + ".NS"

    return fetch_index_data(symbol=symbol, days=days)
