"""
tools/quant_tool.py – ADK Tool Wrapper for the Quant Engine (Step 1)
=====================================================================
Thin ADK-compatible wrapper around the pure-Python quant/ package.

When called by the orchestrator at Step 1, this tool:
    1. Fetches OHLCV data via quant.fetch_ohlcv()
    2. Computes indicators via quant.compute_indicators()
    3. Classifies regime via quant.classify_regime()
    4. Writes the RegimeSnapshot to session state at KEY_QUANT_SNAPSHOT

The raw math lives in quant/ and is independently testable without ADK.
This file is ONLY the adapter.

TODO: Implement quant_engine_tool()
"""

from quant import fetch_ohlcv, compute_indicators, classify_regime
from pipeline.session_keys import KEY_QUANT_SNAPSHOT


def quant_engine_tool(ticker: str) -> dict:
    """
    Run the full quant pipeline for a ticker: fetch data, compute indicators,
    and classify the market regime.

    This is an ADK-compatible function tool. The orchestrator calls it at
    Step 1 and writes the result to session state.

    Args:
        ticker: The stock ticker symbol (e.g., 'RELIANCE.NS').

    Returns:
        A dict containing the RegimeSnapshot (regime, indicators, close, ATR,
        etc.) ready to be stored in session.state[KEY_QUANT_SNAPSHOT].
    """
    raise NotImplementedError("TODO: Wire up quant pipeline")
