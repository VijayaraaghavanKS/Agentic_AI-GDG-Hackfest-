"""
scheduler.py – Intraday Auto-Scan Loop Controller
====================================================
Runs the TradingPipeline on a timer, fetching live market data and news.

Provides:
    - start_auto_scan(interval_seconds)  → start background loop
    - stop_auto_scan()                   → stop background loop
    - run_single_scan(ticker)            → manual one-shot pipeline run
    - get_scan_status()                  → current state
    - get_scan_log()                     → structured log entries
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from agents.pipeline import TradingPipeline
from trading_agents.tools.market_data import fetch_stock_data
from trading_agents.tools.news_data import fetch_stock_news
from trading_agents.config import NSE_WATCHLIST

logger = logging.getLogger(__name__)


# ── Scan Log (in-memory ring buffer for UI) ──────────────────────────────────
_scan_log: list[dict] = []
_MAX_LOG_ENTRIES = 100

# ── Background scan state ────────────────────────────────────────────────────
_scan_thread: Optional[threading.Thread] = None
_scan_stop_event = threading.Event()
_scan_running = False
_scan_interval = 300
_scan_count = 0


def _log_event(event_type: str, message: str, data: dict | None = None) -> None:
    """Append a structured log entry to the scan log ring buffer."""
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "event": event_type,
        "message": message,
    }
    if data:
        entry["data"] = data
    _scan_log.append(entry)
    if len(_scan_log) > _MAX_LOG_ENTRIES:
        _scan_log.pop(0)
    logger.info("[%s] %s", event_type, message)


def _fetch_candles(symbol: str) -> Optional[pd.DataFrame]:
    """Fetch stock data and convert to DataFrame."""
    data = fetch_stock_data(symbol=symbol)
    if data.get("status") != "success":
        return None
    closes = data.get("closes", [])
    highs = data.get("highs", [])
    lows = data.get("lows", [])
    volumes = data.get("volumes", [])
    opens = data.get("opens", closes)  # fallback if no opens
    n = min(len(closes), len(highs), len(lows), len(volumes))
    if n < 30:
        return None
    return pd.DataFrame({
        "open": opens[-n:],
        "high": highs[-n:],
        "low": lows[-n:],
        "close": closes[-n:],
        "volume": volumes[-n:],
    })


def _fetch_news(symbol: str) -> list[str]:
    """Fetch news headlines for a symbol."""
    try:
        result = fetch_stock_news(symbol=symbol)
        return result.get("headlines", []) if result.get("status") == "success" else []
    except Exception:
        return []


def run_single_scan(ticker: str = "RELIANCE.NS") -> dict:
    """Execute a single pipeline run for one ticker.

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g. "RELIANCE.NS").

    Returns
    -------
    dict
        Full pipeline result.
    """
    global _scan_count
    _scan_count += 1
    scan_id = _scan_count

    _log_event("SCAN_START", f"Scan #{scan_id}: {ticker}")

    # Fetch candles
    candles = _fetch_candles(ticker)
    if candles is None:
        _log_event("DATA_ERROR", f"Failed to fetch candles for {ticker}")
        return {"status": "error", "reason": f"Cannot fetch data for {ticker}"}

    # Fetch news
    news = _fetch_news(ticker)
    _log_event("DATA_OK", f"Fetched {len(candles)} candles, {len(news)} headlines for {ticker}")

    # Run pipeline
    try:
        pipeline = TradingPipeline()
        result = pipeline.run(
            candles=candles,
            news=news,
            ticker=ticker,
        )
        _log_event(
            "PIPELINE_DONE",
            f"Scan #{scan_id}: scenario={result['scenario']['label']}, "
            f"strategy={result['strategy_selected']}, "
            f"trade={result['trade_status']}",
            data={k: v for k, v in result.items() if k not in ("backtest_scores",)},
        )
        return result

    except Exception as e:
        _log_event("PIPELINE_ERROR", f"Pipeline failed for {ticker}: {e}")
        return {"status": "error", "reason": str(e)}


def run_watchlist_scan() -> dict:
    """Scan all tickers in the watchlist and run pipeline for the best candidate.

    Returns
    -------
    dict
        Scan summary with per-ticker results.
    """
    _log_event("WATCHLIST_SCAN", f"Scanning {len(NSE_WATCHLIST)} stocks")
    results = {}
    for sym in NSE_WATCHLIST[:10]:  # limit to 10 for speed
        try:
            r = run_single_scan(sym)
            results[sym] = {
                "scenario": r.get("scenario", {}).get("label", "?"),
                "strategy": r.get("strategy_selected", "?"),
                "trade": r.get("trade_status", "?"),
            }
        except Exception as e:
            results[sym] = {"error": str(e)}
    return {"status": "success", "results": results}


# ── Background Loop ──────────────────────────────────────────────────────────

def _scan_loop() -> None:
    """Background loop that runs pipeline on a timer."""
    global _scan_running
    _scan_running = True
    _log_event("AUTO_START", f"Auto-scan started, interval={_scan_interval}s")

    while not _scan_stop_event.is_set():
        try:
            run_watchlist_scan()
        except Exception as e:
            _log_event("LOOP_ERROR", f"Error in scan loop: {e}")

        _scan_stop_event.wait(timeout=_scan_interval)

    _scan_running = False
    _log_event("AUTO_STOP", "Auto-scan stopped")


def start_auto_scan(interval_seconds: int = 300) -> dict:
    """Start the background auto-scan loop."""
    global _scan_thread, _scan_interval

    if _scan_running:
        return {"status": "already_running", "interval": _scan_interval}

    _scan_interval = interval_seconds
    _scan_stop_event.clear()
    _scan_thread = threading.Thread(target=_scan_loop, daemon=True)
    _scan_thread.start()

    return {"status": "started", "interval": interval_seconds}


def stop_auto_scan() -> dict:
    """Stop the background auto-scan loop."""
    if not _scan_running:
        return {"status": "not_running"}

    _scan_stop_event.set()
    return {"status": "stopping"}


def get_scan_status() -> dict:
    """Get current auto-scan state."""
    return {
        "running": _scan_running,
        "interval": _scan_interval,
        "total_scans": _scan_count,
    }


def get_scan_log(limit: int = 50) -> list[dict]:
    """Get recent scan log entries."""
    return _scan_log[-limit:]
