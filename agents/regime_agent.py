"""
agents/regime_agent.py – Market Regime Detector
=================================================
Input: OHLCV candle data (last N candles)
Logic: EMA crossover + ATR percentile → trend + volatility
Output: MarketRegime
"""

from __future__ import annotations

import pandas as pd

from core.models import MarketRegime
from strategy.strategies import _ema, _safe_atr


def analyze(candles: pd.DataFrame) -> dict:
    """Detect market regime from candle data.

    Parameters
    ----------
    candles : pd.DataFrame
        Must have columns: open, high, low, close, volume.
        Need at least 60 rows.

    Returns
    -------
    dict
        status, regime (MarketRegime), evidence dict.
    """
    if len(candles) < 60:
        regime = MarketRegime(trend="sideways", volatility="low")
        return {
            "status": "success",
            "regime": regime,
            "evidence": {"error": "insufficient_data"},
        }

    close = candles["close"].astype(float)
    high = candles["high"].astype(float)
    low = candles["low"].astype(float)

    # Trend: price vs 200-period EMA (or 50 if not enough data)
    if len(close) >= 200:
        ema_long = _ema(close, 200)
    else:
        ema_long = _ema(close, 50)

    ema_short = _ema(close, 20)

    current_close = float(close.iloc[-1])
    ema_l = float(ema_long.iloc[-1])
    ema_s = float(ema_short.iloc[-1])

    # Trend classification
    if current_close > ema_l and ema_s > ema_l:
        trend = "bull"
    elif current_close < ema_l and ema_s < ema_l:
        trend = "bear"
    else:
        trend = "sideways"

    # Volatility: ATR percentile vs 20-period median
    atr = _safe_atr(high, low, close, period=14)
    current_atr = float(atr.iloc[-1])
    atr_20 = atr.tail(20)
    median_atr = float(atr_20.median())

    # High if current ATR > 75th percentile of last 20
    pct_75 = float(atr_20.quantile(0.75))
    volatility = "high" if current_atr > pct_75 else "low"

    regime = MarketRegime(trend=trend, volatility=volatility)

    return {
        "status": "success",
        "regime": regime,
        "evidence": {
            "close": round(current_close, 2),
            "ema_short": round(ema_s, 2),
            "ema_long": round(ema_l, 2),
            "trend": trend,
            "atr": round(current_atr, 2),
            "atr_median": round(median_atr, 2),
            "atr_pct75": round(pct_75, 2),
            "volatility": volatility,
        },
    }
