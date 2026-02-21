"""
tools/risk_tool.py – ADK Tool Wrapper for the Risk Engine (Step 6)
===================================================================
Thin ADK-compatible wrapper around quant/risk_engine.py.

Intercepts the CIO agent's raw JSON proposal from session state at Step 6,
applies the ATR-based stop-loss override and 1% position-sizing rule, and
writes the final validated (or killed) trade back to session state.

The raw math lives in quant/risk_engine.py and is independently testable
without ADK.  This file is ONLY the adapter.

TODO: Implement risk_enforcement_tool()
"""

from quant.risk_engine import apply_risk_limits
from pipeline.session_keys import KEY_CIO_PROPOSAL, KEY_FINAL_TRADE, KEY_QUANT_SNAPSHOT


def risk_enforcement_tool(
    cio_proposal: dict,
    atr: float,
    portfolio_equity: float,
) -> dict | None:
    """
    Enforce deterministic risk limits on the CIO's trade proposal.

    This is an ADK-compatible function tool. The orchestrator calls it at
    Step 6 after the CIO agent has written its proposal.

    Args:
        cio_proposal:     The raw JSON dict from the CIO agent.
        atr:              ATR from the quant snapshot.
        portfolio_equity: Total portfolio equity in INR.

    Returns:
        A ValidatedTrade dict if the trade passes risk checks,
        or None if the trade was killed.
    """
    raise NotImplementedError("TODO: Wire up risk enforcement")
