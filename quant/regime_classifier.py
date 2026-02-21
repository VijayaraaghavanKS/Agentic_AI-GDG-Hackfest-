"""
quant/regime_classifier.py – Market Regime Classifier
=======================================================
Consumes the IndicatorResult and classifies the current market regime
as BULL, BEAR, or NEUTRAL using explicit deterministic rules.

Rules:
    BULL:    Price > 50DMA > 200DMA
    BEAR:    Price < 50DMA < 200DMA
    NEUTRAL: Everything else (mixed signals)

Returns a typed RegimeSnapshot dataclass that gets written into the ADK
session state by quant_tool.py.

TODO: Implement classify_regime()
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Literal

from .indicators import IndicatorResult


class Regime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"


@dataclass
class RegimeSnapshot:
    """
    Complete quant snapshot written to the ADK session state whiteboard.
    All downstream agents read this to ground their debate.
    """
    ticker: str
    regime: Regime
    latest_close: float
    dma_50: float
    dma_200: float
    atr: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float

    def to_dict(self) -> dict:
        """Serialise for session state storage."""
        return asdict(self)


def classify_regime(indicator: IndicatorResult) -> RegimeSnapshot:
    """
    Classify the market regime from computed indicators.

    Args:
        indicator: An IndicatorResult from indicators.compute_indicators().

    Returns:
        A RegimeSnapshot with the regime classification and all indicator
        values bundled together.
    """
    raise NotImplementedError("TODO: Implement regime classification logic")
