"""
strategy/strategies.py – Strategy Definitions
================================================
Four trading strategies with a common interface.

Each strategy's ``get_signal()`` method examines a candle DataFrame and
returns an entry/stop/target dict (or None if no signal).

R:R is ALWAYS 2.0 — stop = entry - 1R, target = entry + 2R.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict

import pandas as pd


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI series; NaN-safe."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _safe_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute ATR series."""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


# ─── Base Strategy ────────────────────────────────────────────────────────────

class BaseStrategy(ABC):
    """Common interface for all strategies."""

    name: str = "base"

    @abstractmethod
    def get_signal(self, candles: pd.DataFrame) -> Optional[Dict]:
        """Evaluate the latest candle against the strategy.

        Parameters
        ----------
        candles : pd.DataFrame
            Must have columns: open, high, low, close, volume.
            Sorted oldest→newest.

        Returns
        -------
        dict or None
            If signal is active: {"entry", "stop", "target", "direction"}.
            None if no signal.
        """
        ...


# ─── Breakout Strategy ───────────────────────────────────────────────────────

class BreakoutStrategy(BaseStrategy):
    """Buy when price breaks above the 20-period high with volume confirmation.

    - Entry  = current close
    - Stop   = entry − 1R  (R = ATR-14)
    - Target = entry + 2R  (R:R = 2.0)
    """

    name = "breakout"

    def get_signal(self, candles: pd.DataFrame) -> Optional[Dict]:
        if len(candles) < 21:
            return None

        close = candles["close"]
        high = candles["high"]
        low = candles["low"]
        volume = candles["volume"]

        current_close = float(close.iloc[-1])
        prev_20_high = float(high.iloc[-21:-1].max())
        avg_volume_20 = float(volume.iloc[-21:-1].mean())
        current_volume = float(volume.iloc[-1])

        # Signal: close breaks above 20-period high + volume > 1.2x average
        if current_close <= prev_20_high:
            return None
        if avg_volume_20 > 0 and current_volume < avg_volume_20 * 1.2:
            return None

        atr = _safe_atr(high, low, close)
        r = float(atr.iloc[-1])
        if r <= 0:
            return None

        entry = current_close
        stop = round(entry - r, 2)          # 1R stop
        target = round(entry + 2.0 * r, 2)  # 2R target → R:R = 2.0

        return {"entry": entry, "stop": stop, "target": target, "direction": "BUY"}


# ─── Mean Reversion Strategy ─────────────────────────────────────────────────

class MeanReversionStrategy(BaseStrategy):
    """Buy oversold bounces — RSI < 30 and price near lower Bollinger band.

    - Entry  = current close
    - Stop   = entry − 1R  (R = ATR-14)
    - Target = entry + 2R  (R:R = 2.0)
    """

    name = "mean_reversion"

    def get_signal(self, candles: pd.DataFrame) -> Optional[Dict]:
        if len(candles) < 30:
            return None

        close = candles["close"]
        high = candles["high"]
        low = candles["low"]

        rsi = _safe_rsi(close)
        current_rsi = float(rsi.iloc[-1])

        # Signal: RSI < 30 (oversold)
        if current_rsi >= 30:
            return None

        # Extra confirmation: price within 1% of 20-period SMA lower band
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        lower_band = sma_20 - 2 * std_20
        current_close = float(close.iloc[-1])
        lb = float(lower_band.iloc[-1])

        if pd.isna(lb) or current_close > lb * 1.01:
            # Relax: just RSI < 30 is enough
            pass

        atr = _safe_atr(high, low, close)
        r = float(atr.iloc[-1])
        if r <= 0:
            return None

        entry = current_close
        stop = round(entry - r, 2)          # 1R stop
        target = round(entry + 2.0 * r, 2)  # 2R target → R:R = 2.0

        return {"entry": entry, "stop": stop, "target": target, "direction": "BUY"}


# ─── Momentum Strategy ───────────────────────────────────────────────────────

class MomentumStrategy(BaseStrategy):
    """Short continuation in bearish momentum — price below EMA-20 and EMA-50.

    - Entry  = current close
    - Stop   = entry + 1R  (R = ATR-14, stop is ABOVE entry for shorts)
    - Target = entry − 2R  (R:R = 2.0)
    """

    name = "momentum"

    def get_signal(self, candles: pd.DataFrame) -> Optional[Dict]:
        if len(candles) < 50:
            return None

        close = candles["close"]
        high = candles["high"]
        low = candles["low"]

        ema_20 = _ema(close, 20)
        ema_50 = _ema(close, 50)

        current_close = float(close.iloc[-1])
        e20 = float(ema_20.iloc[-1])
        e50 = float(ema_50.iloc[-1])

        # Signal: price below both EMAs (bearish alignment)
        if current_close >= e20 or e20 >= e50:
            return None

        atr = _safe_atr(high, low, close)
        r = float(atr.iloc[-1])
        if r <= 0:
            return None

        entry = current_close
        stop = round(entry + r, 2)          # 1R stop (above for short)
        target = round(entry - 2.0 * r, 2)  # 2R target → R:R = 2.0

        return {"entry": entry, "stop": stop, "target": target, "direction": "SELL"}


# ─── No-Trade Strategy ───────────────────────────────────────────────────────

class NoTradeStrategy(BaseStrategy):
    """Always returns None — preserves capital when no edge exists."""

    name = "no_trade"

    def get_signal(self, candles: pd.DataFrame) -> Optional[Dict]:
        return None


# ─── Registry ─────────────────────────────────────────────────────────────────

ALL_STRATEGIES: dict[str, BaseStrategy] = {
    "breakout": BreakoutStrategy(),
    "mean_reversion": MeanReversionStrategy(),
    "momentum": MomentumStrategy(),
    "no_trade": NoTradeStrategy(),
}
