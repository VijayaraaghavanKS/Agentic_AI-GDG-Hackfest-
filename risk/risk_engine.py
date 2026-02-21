"""
risk/risk_engine.py – Deterministic Risk Enforcement Gate
==========================================================
The final enforcement gate in the pipeline (Step 6).

Accepts the CIO agent's raw JSON trade proposal and:
    1. Overrides the stop-loss to: Entry − (1.5 × ATR)
    2. Applies the 1% portfolio-equity position-sizing rule to calculate
       exact share count.
    3. Returns None (silently kills the trade) if the resulting risk/reward
       is below the minimum threshold or if no valid setup exists.

This is DETERMINISTIC Python. The LLM has zero say in risk math.

TODO: Implement apply_risk_limits()
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from config import MAX_RISK_PCT, ATR_STOP_MULTIPLIER


@dataclass
class ValidatedTrade:
    """A trade proposal that has passed through risk enforcement."""
    ticker: str
    action: str                 # BUY | SELL | HOLD
    entry_price: float
    stop_loss: float            # Overridden to Entry − (1.5 × ATR)
    target_price: float
    position_size: int          # Number of shares (from 1% rule)
    risk_per_share: float       # Entry − Stop Loss
    total_risk: float           # risk_per_share × position_size
    risk_reward_ratio: float
    conviction_score: float
    regime: str
    killed: bool = False        # True if risk engine vetoed this trade
    kill_reason: str = ""

    def to_dict(self) -> dict:
        """Serialise for session state / UI."""
        return asdict(self)


def apply_risk_limits(
    cio_proposal: dict,
    atr: float,
    portfolio_equity: float,
) -> Optional[ValidatedTrade]:
    """
    Intercept the CIO agent's JSON trade proposal and enforce hard risk limits.

    Steps:
        1. Override stop-loss → Entry − (ATR_STOP_MULTIPLIER × ATR)
        2. Calculate risk per share → Entry − Stop Loss
        3. Calculate max dollar risk → portfolio_equity × MAX_RISK_PCT
        4. Calculate position size → max_dollar_risk / risk_per_share
        5. Validate risk/reward ratio ≥ 1.5; kill trade if not.
        6. Return ValidatedTrade or None if the trade is killed.

    Args:
        cio_proposal:     The raw JSON dict from the CIO agent containing
                          'action', 'entry', 'raw_stop_loss', 'target',
                          'conviction_score'.
        atr:              The current ATR value from the quant engine.
        portfolio_equity: Total portfolio equity in INR for position sizing.

    Returns:
        A ValidatedTrade dataclass, or None if the trade is killed.
    """
    raise NotImplementedError("TODO: Implement risk enforcement logic")
