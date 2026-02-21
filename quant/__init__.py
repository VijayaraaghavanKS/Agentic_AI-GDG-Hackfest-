"""
quant/ – Deterministic Quant Engine ("The Handcuffs" – Data Layer)
===================================================================
Pure Python data fetching, indicator calculations, and regime classification.
No LLM involvement. Numbers in, numbers out.

Usage:
    from quant import fetch_ohlcv, compute_indicators, classify_regime
"""

from .data_fetcher import fetch_ohlcv
from .indicators import compute_indicators
from .regime_classifier import classify_regime, RegimeSnapshot

__all__ = [
    "fetch_ohlcv",
    "compute_indicators",
    "classify_regime",
    "RegimeSnapshot",
]
