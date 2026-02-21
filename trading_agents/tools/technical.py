"""Technical indicator calculations."""

from __future__ import annotations

import math
from statistics import pstdev
from typing import Dict, List


def _simple_returns(closes: List[float]) -> List[float]:
    returns: List[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev == 0:
            returns.append(0.0)
        else:
            returns.append((closes[i] / prev) - 1.0)
    return returns


def compute_index_metrics(closes: List[float]) -> Dict:
    """Compute index-level technical metrics from daily closes.

    Returns dict with close, dma_50, dma_50_slope, return_20d, volatility.
    """
    if len(closes) < 60:
        return {"status": "error", "error_message": f"Need >=60 closes, got {len(closes)}."}

    close = closes[-1]
    dma_50 = sum(closes[-50:]) / 50
    prior_dma_50 = sum(closes[-55:-5]) / 50
    dma_50_slope = dma_50 - prior_dma_50
    return_20d = (closes[-1] / closes[-21]) - 1.0
    vol_20d = pstdev(_simple_returns(closes[-21:])) * math.sqrt(252)

    return {
        "status": "success",
        "close": round(close, 2),
        "dma_50": round(dma_50, 2),
        "dma_50_slope": round(dma_50_slope, 4),
        "return_20d": round(return_20d, 4),
        "volatility": round(vol_20d, 4),
    }


def compute_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Compute Average True Range over the given period."""
    if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
        return 0.0

    true_ranges: List[float] = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / max(len(true_ranges), 1)

    return sum(true_ranges[-period:]) / period


def detect_breakout(
    symbol: str,
    closes: List[float],
    volumes: List[float],
    highs: List[float],
    lows: List[float],
) -> Dict:
    """Detect whether a stock is breaking out of its 20-day high with volume confirmation.

    Returns dict with breakout analysis results.
    """
    if len(closes) < 60 or len(volumes) < 21:
        return {
            "status": "error",
            "error_message": f"Insufficient data for {symbol}: {len(closes)} closes, {len(volumes)} volumes.",
        }

    close = closes[-1]
    prev_20d_high = max(closes[-21:-1])
    avg_20d_volume = sum(volumes[-21:-1]) / 20
    volume_ratio = round(volumes[-1] / max(avg_20d_volume, 1), 2)
    dma_50 = sum(closes[-50:]) / 50
    above_50dma = close > dma_50

    is_breakout = close > prev_20d_high and volume_ratio > 1.2 and above_50dma

    atr = compute_atr(highs, lows, closes)

    return {
        "status": "success",
        "symbol": symbol,
        "close": round(close, 2),
        "prev_20d_high": round(prev_20d_high, 2),
        "volume_ratio": volume_ratio,
        "above_50dma": above_50dma,
        "dma_50": round(dma_50, 2),
        "atr": round(atr, 2),
        "is_breakout": is_breakout,
    }
