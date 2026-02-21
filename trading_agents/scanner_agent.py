"""Stock scanner sub-agent -- scans NSE watchlist for breakout candidates."""

from __future__ import annotations

from typing import Dict, List

from google.adk.agents import Agent

from trading_agents.config import GEMINI_MODEL, NSE_WATCHLIST
from trading_agents.tools.market_data import fetch_stock_data
from trading_agents.tools.technical import detect_breakout


def scan_watchlist_breakouts(watchlist: str = "") -> Dict:
    """Scan NSE watchlist stocks for 20-day breakout candidates with live data.

    Args:
        watchlist: Comma-separated stock symbols to scan. Leave empty to use default NSE watchlist.

    Returns:
        dict with breakout candidates and scan metadata.
    """
    if watchlist.strip():
        symbols = [s.strip() for s in watchlist.split(",")]
    else:
        symbols = NSE_WATCHLIST

    candidates: List[Dict] = []
    scanned: List[str] = []
    errors: List[str] = []

    for sym in symbols:
        data = fetch_stock_data(symbol=sym)
        if data.get("status") != "success":
            errors.append(f"{sym}: {data.get('error_message', 'fetch failed')}")
            continue

        scanned.append(sym)
        result = detect_breakout(
            symbol=data["symbol"],
            closes=data["closes"],
            volumes=data["volumes"],
            highs=data["highs"],
            lows=data["lows"],
        )
        if result.get("status") == "success" and result.get("is_breakout"):
            candidates.append(result)

    candidates.sort(key=lambda x: x.get("volume_ratio", 0), reverse=True)

    return {
        "status": "success",
        "stocks_scanned": len(scanned),
        "breakout_count": len(candidates),
        "candidates": candidates,
        "scan_errors": errors if errors else None,
    }


def get_stock_analysis(symbol: str) -> Dict:
    """Get detailed breakout analysis for a single stock.

    Args:
        symbol: NSE stock ticker (e.g. 'RELIANCE' or 'RELIANCE.NS').

    Returns:
        dict with breakout analysis, ATR, and technical metrics.
    """
    data = fetch_stock_data(symbol=symbol)
    if data.get("status") != "success":
        return data

    result = detect_breakout(
        symbol=data["symbol"],
        closes=data["closes"],
        volumes=data["volumes"],
        highs=data["highs"],
        lows=data["lows"],
    )
    result["last_trade_date"] = data["last_trade_date"]
    result["source"] = data["source"]
    return result


scanner_agent = Agent(
    name="stock_scanner",
    model=GEMINI_MODEL,
    description=(
        "Scans NSE stocks for breakout candidates using live market data. "
        "Checks 20-day high breakout with volume confirmation and 50-DMA filter."
    ),
    instruction=(
        "You are the Stock Scanner. When asked to scan for trade opportunities, "
        "use scan_watchlist_breakouts to scan the NSE watchlist. "
        "Report how many stocks were scanned, how many are breaking out, "
        "and list candidates ranked by volume ratio. "
        "For individual stock analysis, use get_stock_analysis. "
        "Only present stocks that are genuine breakouts."
    ),
    tools=[scan_watchlist_breakouts, get_stock_analysis],
)
