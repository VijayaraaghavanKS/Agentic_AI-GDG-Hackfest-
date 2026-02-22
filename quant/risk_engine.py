"""
quant/risk_engine.py – Deterministic Risk Engine
=================================================
Production-grade, hard risk gate for all trade proposals.

This module enforces strict trading risk rules using pure Python.
It does NOT use Gemini, ADK, or any LLM.

Design Philosophy:
    • This is the final deterministic safety layer before execution.
    • LLM proposals MUST pass through here.
    • The risk engine can: modify stop-loss, modify position size, reject trades.
    • The LLM CANNOT override risk rules.

Data Flow:
    CIO Proposal → apply_risk_limits() → ValidatedTrade OR KILLED
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional
import logging

from config import (
    MAX_RISK_PCT,
    ATR_STOP_MULTIPLIER,
    MIN_RISK_REWARD,
)

# ──────────────────────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

VALID_ACTIONS: frozenset[str] = frozenset({"BUY", "SELL", "HOLD"})
VALID_REGIMES: frozenset[str] = frozenset({"BULL", "BEAR", "NEUTRAL"})

_REQUIRED_FIELDS: tuple[str, ...] = (
    "ticker",
    "action",
    "entry",
    "target",
    "conviction_score",
    "regime",
)

# ──────────────────────────────────────────────────────────────
# Regime → Allowed Directions
# ──────────────────────────────────────────────────────────────

_REGIME_ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "BULL":    frozenset({"BUY", "SELL"}),
    "BEAR":    frozenset({"BUY", "SELL"}),
    "NEUTRAL": frozenset({"BUY", "SELL"}),
}

# Position size penalty for trades that go against the regime direction
_REGIME_ALIGNED_ACTIONS: dict[str, frozenset[str]] = {
    "BULL":    frozenset({"BUY"}),
    "BEAR":    frozenset({"SELL"}),
    "NEUTRAL": frozenset({"BUY", "SELL"}),
}
# Contrarian trades get 50% position size
_CONTRARIAN_SIZE_FACTOR: float = 0.5

# ──────────────────────────────────────────────────────────────
# Validated Trade Dataclass
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ValidatedTrade:
    """Immutable, fully-validated trade record produced by the risk engine."""

    ticker: str
    action: str
    entry_price: float
    stop_loss: float
    target_price: float
    position_size: int
    risk_per_share: float
    total_risk: float
    risk_reward_ratio: float
    conviction_score: float
    regime: str
    killed: bool
    kill_reason: Optional[str]

    def __repr__(self) -> str:
        return (
            f"ValidatedTrade(\n"
            f"  ticker={self.ticker}\n"
            f"  action={self.action}\n"
            f"  size={self.position_size}\n"
            f"  entry={self.entry_price:.2f}\n"
            f"  stop={self.stop_loss:.2f}\n"
            f"  target={self.target_price:.2f}\n"
            f"  rr={self.risk_reward_ratio:.1f}\n"
            f"  killed={self.killed}\n"
            f")"
        )


# ──────────────────────────────────────────────────────────────
# Numeric Safety
# ──────────────────────────────────────────────────────────────

def _assert_finite(value: float, name: str) -> None:
    """Raise ValueError if *value* is NaN or Inf."""
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


# ──────────────────────────────────────────────────────────────
# Helper — build a killed trade
# ──────────────────────────────────────────────────────────────

def _killed_trade(
    proposal: dict,
    reason: str,
    *,
    stop_loss: float = 0.0,
    risk_per_share: float = 0.0,
) -> ValidatedTrade:
    """Return a ValidatedTrade with killed=True."""
    ticker: str = proposal.get("ticker", "UNKNOWN")
    logger.warning("[%s] KILLED — %s", ticker, reason)
    return ValidatedTrade(
        ticker=ticker,
        action=str(proposal.get("action", "UNKNOWN")).upper(),
        entry_price=float(proposal.get("entry", 0)),
        stop_loss=stop_loss,
        target_price=float(proposal.get("target", 0)),
        position_size=0,
        risk_per_share=risk_per_share,
        total_risk=0.0,
        risk_reward_ratio=0.0,
        conviction_score=float(proposal.get("conviction_score", 0)),
        regime=str(proposal.get("regime", "UNKNOWN")).upper(),
        killed=True,
        kill_reason=reason,
    )


# ──────────────────────────────────────────────────────────────
# Core Function
# ──────────────────────────────────────────────────────────────

def apply_risk_limits(
    cio_proposal: dict,
    atr: float,
    portfolio_equity: float,
) -> ValidatedTrade:
    """Apply deterministic risk limits to a CIO proposal.

    Parameters
    ----------
    cio_proposal : dict
        Must contain: ticker, action, entry, target, conviction_score, regime.
        ``raw_stop_loss`` is accepted but **ignored** — the risk engine
        always computes its own ATR-based stop-loss.
    atr : float
        Average True Range for the instrument (must be > 0).
    portfolio_equity : float
        Current portfolio equity in currency units (must be > 0).

    Returns
    -------
    ValidatedTrade
        Frozen dataclass.  Check ``killed`` flag before execution.

    Raises
    ------
    ValueError
        If required proposal fields are missing, numeric values are
        non-finite, conviction_score is out of [0, 1], or positional
        guards fail.
    """

    # ── Step 1: Validate Required Fields ─────────────────────
    for field in _REQUIRED_FIELDS:
        if field not in cio_proposal:
            raise ValueError(f"Missing required field in CIO proposal: '{field}'")

    ticker: str = str(cio_proposal["ticker"])
    action: str = str(cio_proposal["action"]).upper()
    entry: float = float(cio_proposal["entry"])
    target: float = float(cio_proposal["target"])
    conviction_score: float = float(cio_proposal["conviction_score"])
    regime: str = str(cio_proposal["regime"]).upper()

    # ── Numeric Safety (NaN / Inf) ───────────────────────────
    _assert_finite(entry, "entry")
    _assert_finite(target, "target")
    _assert_finite(atr, "atr")
    _assert_finite(portfolio_equity, "portfolio_equity")
    _assert_finite(conviction_score, "conviction_score")

    # ── Positional Guards ────────────────────────────────────
    if entry <= 0:
        raise ValueError(f"entry must be > 0, got {entry}")
    if target <= 0:
        raise ValueError(f"target must be > 0, got {target}")
    if atr <= 0:
        raise ValueError(f"atr must be > 0, got {atr}")
    if portfolio_equity <= 0:
        raise ValueError(f"portfolio_equity must be > 0, got {portfolio_equity}")

    # ── Conviction Validation ────────────────────────────────
    if not (0.0 <= conviction_score <= 1.0):
        raise ValueError(
            f"conviction_score must be in [0.0, 1.0], got {conviction_score}"
        )

    # ── Action Validation ────────────────────────────────────
    if action not in VALID_ACTIONS:
        raise ValueError(
            f"Unsupported action: '{action}'. Must be one of {sorted(VALID_ACTIONS)}"
        )

    # ── Regime Validation ────────────────────────────────────
    if regime not in VALID_REGIMES:
        raise ValueError(
            f"Unsupported regime: '{regime}'. Must be one of {sorted(VALID_REGIMES)}"
        )

    logger.info("[%s] RiskEngine start — action=%s entry=%.2f target=%.2f atr=%.2f regime=%s",
                ticker, action, entry, target, atr, regime)

    # ── HOLD → always killed ─────────────────────────────────
    if action == "HOLD":
        return _killed_trade(
            cio_proposal,
            "HOLD action requires no trade",
        )

    # ── Regime Guard ─────────────────────────────────────────
    if action not in _REGIME_ALLOWED_ACTIONS[regime]:
        return _killed_trade(
            cio_proposal,
            "Trade direction conflicts with regime",
        )

    # ── Step 2: ATR Stop-Loss Override ───────────────────────
    # Risk engine ALWAYS controls stop-loss; raw_stop_loss is ignored.
    if action == "BUY":
        stop_loss: float = entry - (ATR_STOP_MULTIPLIER * atr)
    else:  # SELL
        stop_loss = entry + (ATR_STOP_MULTIPLIER * atr)

    logger.info("[%s] StopLoss=%.2f ATR=%.2f Mult=%.2f",
                ticker, stop_loss, atr, ATR_STOP_MULTIPLIER)

    # ── Step 3: Risk Per Share ───────────────────────────────
    if action == "BUY":
        risk_per_share: float = entry - stop_loss
    else:  # SELL
        risk_per_share = stop_loss - entry

    if risk_per_share <= 0:
        return _killed_trade(
            cio_proposal,
            f"risk_per_share={risk_per_share:.4f} is not positive",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 4: Maximum Risk ─────────────────────────────────
    max_risk: float = portfolio_equity * MAX_RISK_PCT

    logger.info("[%s] MaxRiskAllowed=%.2f", ticker, max_risk)

    # ── Step 5: Position Size ────────────────────────────────
    position_size: int = int(max_risk / risk_per_share)

    # Apply contrarian penalty — halve position if trading against regime
    is_contrarian = action not in _REGIME_ALIGNED_ACTIONS.get(regime, set())
    if is_contrarian:
        position_size = int(position_size * _CONTRARIAN_SIZE_FACTOR)
        logger.info("[%s] Contrarian trade (action=%s regime=%s) — size halved to %d",
                    ticker, action, regime, position_size)

    logger.info("[%s] Position=%d MaxRisk=%.2f",
                ticker, position_size, max_risk)

    if position_size < 1:
        return _killed_trade(
            cio_proposal,
            f"position_size={position_size} < 1 — risk per share too large for equity",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 6: Total Risk ───────────────────────────────────
    total_risk: float = position_size * risk_per_share

    # ── Step 7: Risk-Reward Ratio ────────────────────────────
    if action == "BUY":
        reward: float = target - entry
    else:  # SELL
        reward = entry - target

    risk_reward_ratio: float = max(0.0, reward / risk_per_share)

    logger.info("[%s] RiskReward=%.2f", ticker, risk_reward_ratio)

    # ── Step 8: Reject Bad Trades ────────────────────────────
    if risk_reward_ratio < MIN_RISK_REWARD:
        return _killed_trade(
            cio_proposal,
            f"risk_reward_ratio={risk_reward_ratio:.2f} < MIN_RISK_REWARD={MIN_RISK_REWARD}",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 9 & 10: Accepted trade ─────────────────────────
    logger.info("[%s] ACCEPTED — size=%d stop=%.2f target=%.2f rr=%.2f total_risk=%.2f",
                ticker, position_size, stop_loss, target, risk_reward_ratio, total_risk)

    return ValidatedTrade(
        ticker=ticker,
        action=action,
        entry_price=round(entry, 2),
        stop_loss=round(stop_loss, 2),
        target_price=round(target, 2),
        position_size=position_size,
        risk_per_share=round(risk_per_share, 2),
        total_risk=round(total_risk, 2),
        risk_reward_ratio=round(risk_reward_ratio, 2),
        conviction_score=conviction_score,
        regime=regime,
        killed=False,
        kill_reason=None,
    )


# ──────────────────────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    proposal: dict = {
        "ticker": "RELIANCE.NS",
        "action": "BUY",
        "entry": 2800,
        "raw_stop_loss": 2700,
        "target": 3100,
        "conviction_score": 0.7,
        "regime": "BULL",
    }

    trade: ValidatedTrade = apply_risk_limits(
        proposal,
        atr=30,
        portfolio_equity=1_000_000,
    )

    print(trade)
