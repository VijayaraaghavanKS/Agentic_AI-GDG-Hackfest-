"""
trading_agents/risk_engine.py – Deterministic Risk Engine
==========================================================
Production-grade, hard risk gate for all trade proposals.

This module enforces strict trading risk rules using pure Python.
It does NOT use Gemini, ADK, or any LLM.

Design Philosophy:
    - This is the final deterministic safety layer before execution.
    - LLM proposals MUST pass through here.
    - The risk engine can: modify stop-loss, modify position size, reject trades.
    - The LLM CANNOT override risk rules.

Data Flow:
    CIO / Debate Verdict  →  apply_risk_limits()  →  ValidatedTrade OR KILLED
    Trade Executor         →  validate_and_size()   →  sized plan dict
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from trading_agents.config import (
    ATR_STOP_MULTIPLIER,
    MIN_REWARD_RISK,
    RISK_PER_TRADE,
    MAX_OPEN_TRADES,
    INITIAL_CAPITAL,
)

# ──────────────────────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

VALID_ACTIONS: frozenset[str] = frozenset({"BUY", "SELL", "HOLD"})
VALID_REGIMES: frozenset[str] = frozenset({"BULL", "BEAR", "SIDEWAYS", "NEUTRAL"})

_REQUIRED_FIELDS: tuple[str, ...] = (
    "ticker",
    "action",
    "entry",
    "conviction_score",
)

# ──────────────────────────────────────────────────────────────
# Regime → Allowed Directions & Contrarian Penalty
# ──────────────────────────────────────────────────────────────

_REGIME_ALIGNED_ACTIONS: dict[str, frozenset[str]] = {
    "BULL":     frozenset({"BUY"}),
    "BEAR":     frozenset({"SELL"}),
    "SIDEWAYS": frozenset({"BUY", "SELL"}),
    "NEUTRAL":  frozenset({"BUY", "SELL"}),
}

# Contrarian trades (e.g. BUY in BEAR) get 50 % position size
_CONTRARIAN_SIZE_FACTOR: float = 0.5

# ──────────────────────────────────────────────────────────────
# ValidatedTrade Dataclass
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ValidatedTrade:
    """Immutable, fully-validated trade record produced by the risk engine.

    Check ``killed`` before proceeding to execution.
    """

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
    is_contrarian: bool
    killed: bool
    kill_reason: Optional[str]

    def to_dict(self) -> dict:
        """Convert to a JSON-safe dictionary."""
        return asdict(self)  # frozen dataclass → plain dict

    def __repr__(self) -> str:
        tag = "KILLED" if self.killed else "ACCEPTED"
        return (
            f"ValidatedTrade({tag}\n"
            f"  ticker={self.ticker}\n"
            f"  action={self.action}\n"
            f"  size={self.position_size}\n"
            f"  entry={self.entry_price:.2f}\n"
            f"  stop={self.stop_loss:.2f}\n"
            f"  target={self.target_price:.2f}\n"
            f"  rr={self.risk_reward_ratio:.1f}\n"
            f"  contrarian={self.is_contrarian}\n"
            f"  reason={self.kill_reason}\n"
            f")"
        )


# ──────────────────────────────────────────────────────────────
# Numeric Safety
# ──────────────────────────────────────────────────────────────

def _is_finite(value: float) -> bool:
    """Return True if *value* is a real finite number."""
    return isinstance(value, (int, float)) and math.isfinite(value)


def _assert_finite(value: float, name: str) -> None:
    """Raise ValueError if *value* is NaN or Inf."""
    if not _is_finite(value):
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
        is_contrarian=False,
        killed=True,
        kill_reason=reason,
    )


# ──────────────────────────────────────────────────────────────
# Core Function — full risk enforcement
# ──────────────────────────────────────────────────────────────

def apply_risk_limits(
    proposal: dict,
    atr: float,
    portfolio_equity: float | None = None,
) -> ValidatedTrade:
    """Apply deterministic risk limits to a trade proposal.

    Parameters
    ----------
    proposal : dict
        Must contain: ticker, action, entry, conviction_score.
        Optional: target, regime, raw_stop_loss (ignored, engine computes its own).
    atr : float
        Average True Range for the instrument (must be > 0).
    portfolio_equity : float, optional
        Portfolio equity in INR. Defaults to ``INITIAL_CAPITAL``.

    Returns
    -------
    ValidatedTrade
        Frozen dataclass.  Check ``killed`` flag before execution.
    """
    if portfolio_equity is None:
        portfolio_equity = INITIAL_CAPITAL

    # ── Step 1: Validate Required Fields ─────────────────────
    for field in _REQUIRED_FIELDS:
        if field not in proposal:
            raise ValueError(f"Missing required field in proposal: '{field}'")

    ticker: str = str(proposal["ticker"]).upper()
    action: str = str(proposal["action"]).upper()
    entry: float = float(proposal["entry"])
    conviction_score: float = float(proposal["conviction_score"])
    regime: str = str(proposal.get("regime", "NEUTRAL")).upper()

    # ── Numeric Safety (NaN / Inf) ───────────────────────────
    _assert_finite(entry, "entry")
    _assert_finite(atr, "atr")
    _assert_finite(portfolio_equity, "portfolio_equity")
    _assert_finite(conviction_score, "conviction_score")

    # ── Positional Guards ────────────────────────────────────
    if entry <= 0:
        raise ValueError(f"entry must be > 0, got {entry}")
    if atr <= 0:
        raise ValueError(f"atr must be > 0, got {atr}")
    if portfolio_equity <= 0:
        raise ValueError(f"portfolio_equity must be > 0, got {portfolio_equity}")

    # ── Conviction Validation (allow 0-1 or 0-100 scale) ────
    if conviction_score > 1.0:
        conviction_score = conviction_score / 100.0  # normalise 0-100 → 0-1
    if not (0.0 <= conviction_score <= 1.0):
        raise ValueError(f"conviction_score must be in [0, 1], got {conviction_score}")

    # ── Action Validation ────────────────────────────────────
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported action: '{action}'. Must be one of {sorted(VALID_ACTIONS)}")

    # ── Regime Validation ────────────────────────────────────
    if regime not in VALID_REGIMES:
        logger.warning("[%s] Unknown regime '%s', defaulting to NEUTRAL", ticker, regime)
        regime = "NEUTRAL"

    logger.info(
        "[%s] RiskEngine start — action=%s entry=%.2f atr=%.2f regime=%s conviction=%.2f",
        ticker, action, entry, atr, regime, conviction_score,
    )

    # ── HOLD → always killed ─────────────────────────────────
    if action == "HOLD":
        return _killed_trade(proposal, "HOLD action requires no trade")

    # ── Step 2: ATR Stop-Loss (engine always computes its own) ──
    if action == "BUY":
        stop_loss: float = round(max(0.01, entry - (ATR_STOP_MULTIPLIER * atr)), 2)
    else:  # SELL
        stop_loss = round(entry + (ATR_STOP_MULTIPLIER * atr), 2)

    logger.info("[%s] StopLoss=%.2f (ATR=%.2f × %.1f)", ticker, stop_loss, atr, ATR_STOP_MULTIPLIER)

    # ── Step 3: Risk Per Share ───────────────────────────────
    if action == "BUY":
        risk_per_share: float = entry - stop_loss
    else:
        risk_per_share = stop_loss - entry

    if risk_per_share <= 0:
        return _killed_trade(
            proposal,
            f"risk_per_share={risk_per_share:.4f} is not positive",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 4: Target ───────────────────────────────────────
    # If proposal has target, use it; otherwise compute 2R target
    if "target" in proposal and _is_finite(float(proposal["target"])) and float(proposal["target"]) > 0:
        target: float = float(proposal["target"])
    else:
        if action == "BUY":
            target = round(entry + (MIN_REWARD_RISK * risk_per_share), 2)
        else:
            target = round(entry - (MIN_REWARD_RISK * risk_per_share), 2)

    _assert_finite(target, "target")

    # ── Step 5: Risk-Reward Ratio ────────────────────────────
    if action == "BUY":
        reward: float = target - entry
    else:
        reward = entry - target

    risk_reward_ratio: float = max(0.0, reward / risk_per_share) if risk_per_share > 0 else 0.0

    logger.info("[%s] RiskReward=%.2f", ticker, risk_reward_ratio)

    if risk_reward_ratio < MIN_REWARD_RISK:
        return _killed_trade(
            proposal,
            f"risk_reward_ratio={risk_reward_ratio:.2f} < min required {MIN_REWARD_RISK}",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 6: Position Sizing ──────────────────────────────
    max_risk: float = portfolio_equity * RISK_PER_TRADE
    position_size: int = int(max_risk / risk_per_share)

    # Contrarian penalty — halve if trading against regime
    is_contrarian = False
    if regime in _REGIME_ALIGNED_ACTIONS:
        if action not in _REGIME_ALIGNED_ACTIONS[regime]:
            position_size = int(position_size * _CONTRARIAN_SIZE_FACTOR)
            is_contrarian = True
            logger.info(
                "[%s] Contrarian trade (action=%s regime=%s) — size halved to %d",
                ticker, action, regime, position_size,
            )

    if position_size < 1:
        return _killed_trade(
            proposal,
            f"position_size={position_size} < 1 — risk per share too large for equity",
            stop_loss=stop_loss,
            risk_per_share=risk_per_share,
        )

    # ── Step 7: Total Risk ───────────────────────────────────
    total_risk: float = position_size * risk_per_share

    logger.info(
        "[%s] ACCEPTED — size=%d stop=%.2f target=%.2f rr=%.2f total_risk=%.2f contrarian=%s",
        ticker, position_size, stop_loss, target, risk_reward_ratio, total_risk, is_contrarian,
    )

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
        conviction_score=round(conviction_score, 4),
        regime=regime,
        is_contrarian=is_contrarian,
        killed=False,
        kill_reason=None,
    )


# ──────────────────────────────────────────────────────────────
# Convenience — quick validation (used by paper_trading.py)
# ──────────────────────────────────────────────────────────────

def validate_trade_inputs(
    entry: float,
    stop: float,
    target: float,
) -> Optional[str]:
    """Return an error message if inputs are invalid, else None."""
    for name, val in [("entry", entry), ("stop", stop), ("target", target)]:
        if not _is_finite(val) or val <= 0:
            return f"Invalid {name}: {val}"
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return f"Invalid stop (>= entry) — risk_per_share not positive"
    rr = (target - entry) / risk_per_share
    if rr < MIN_REWARD_RISK:
        return f"Risk/Reward {rr:.2f} below minimum {MIN_REWARD_RISK}. Trade not viable."
    return None


# ──────────────────────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    proposal = {
        "ticker": "RELIANCE.NS",
        "action": "BUY",
        "entry": 2800,
        "target": 3100,
        "conviction_score": 0.7,
        "regime": "BULL",
    }

    trade = apply_risk_limits(proposal, atr=30, portfolio_equity=1_000_000)
    print(trade)
    print()
    print("Dict:", trade.to_dict())
