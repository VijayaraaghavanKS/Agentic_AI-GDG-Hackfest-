"""
risk/ – Deterministic Risk Engine ("The Handcuffs" – Risk Layer)
=================================================================
The final enforcement gate. Accepts the CIO's raw trade proposal and
mathematically overrides stop-loss, applies position sizing, and can
silently kill trades that breach risk limits.

Usage:
    from risk import apply_risk_limits
"""

from .risk_engine import apply_risk_limits, ValidatedTrade

__all__ = ["apply_risk_limits", "ValidatedTrade"]
