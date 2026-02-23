"""
tools/risk_tool.py – ADK Tool Adapter for the Deterministic Risk Engine (Step 6)
==================================================================================
Production-grade ADK-compatible wrapper around ``quant/risk_engine.py``.

This is the **final deterministic gate** before trade execution.

Pipeline position::

    CIO Agent
       ↓
    KEY_CIO_PROPOSAL   (session state)
       ↓
    risk_tool.py       ← YOU ARE HERE
       ↓
    risk_engine.apply_risk_limits()
       ↓
    KEY_FINAL_TRADE    (session state)

Design rules:
    • Deterministic only — NO LLM calls, NO Gemini, NO ADK reasoning.
    • All risk mathematics live in ``quant/risk_engine.py``.
    • This file is ONLY the adapter (read state → call engine → write state).
    • The LLM CANNOT override risk rules.
"""

from __future__ import annotations

import json
import logging
from typing import Dict

from quant.risk_engine import apply_risk_limits, ValidatedTrade

from pipeline.session_keys import (
    KEY_CIO_PROPOSAL,
    KEY_QUANT_SNAPSHOT,
    KEY_FINAL_TRADE,
)

from config import DEFAULT_PORTFOLIO_EQUITY

# ──────────────────────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Required Keys
# ──────────────────────────────────────────────────────────────

_REQUIRED_PROPOSAL_FIELDS: tuple[str, ...] = (
    "ticker",
    "action",
    "entry",
    "target",
    "conviction_score",
    "regime",
)

_REQUIRED_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "atr",
    "ticker",
)


# ──────────────────────────────────────────────────────────────
# Validation Helpers
# ──────────────────────────────────────────────────────────────

def _validate_proposal(cio_proposal: Dict) -> None:
    """Raise ``ValueError`` if required CIO proposal fields are missing."""
    for field in _REQUIRED_PROPOSAL_FIELDS:
        if field not in cio_proposal:
            raise ValueError(
                f"Missing required field in CIO proposal: '{field}'"
            )


def _validate_snapshot(quant_snapshot: Dict) -> None:
    """Raise ``ValueError`` if required quant snapshot fields are missing or invalid."""
    for field in _REQUIRED_SNAPSHOT_FIELDS:
        if field not in quant_snapshot:
            raise ValueError(
                f"Missing required field in quant snapshot: '{field}'"
            )
    atr = quant_snapshot["atr"]
    if not isinstance(atr, (int, float)) or atr <= 0:
        raise ValueError(f"ATR must be > 0, got {atr!r}")


# ──────────────────────────────────────────────────────────────
# Dataclass → Dict Converter
# ──────────────────────────────────────────────────────────────

def _trade_to_dict(trade: ValidatedTrade) -> Dict:
    """Convert a frozen ``ValidatedTrade`` dataclass to a JSON-safe dict.

    No computation — pure field copy.
    """
    return {
        "ticker": trade.ticker,
        "action": trade.action,
        "entry_price": trade.entry_price,
        "stop_loss": trade.stop_loss,
        "target_price": trade.target_price,
        "position_size": trade.position_size,
        "risk_per_share": trade.risk_per_share,
        "total_risk": trade.total_risk,
        "risk_reward_ratio": trade.risk_reward_ratio,
        "conviction_score": trade.conviction_score,
        "regime": trade.regime,
        "killed": trade.killed,
        "kill_reason": trade.kill_reason,
    }


# ──────────────────────────────────────────────────────────────
# ADK Tool Function
# ──────────────────────────────────────────────────────────────

def risk_enforcement_tool(
    cio_proposal: Dict,
    quant_snapshot: Dict,
    portfolio_equity: float = DEFAULT_PORTFOLIO_EQUITY,
) -> Dict:
    """Enforce deterministic risk limits on the CIO agent's trade proposal.

    This is an ADK-compatible function tool.  The orchestrator calls it at
    Step 6 after the CIO agent has written ``KEY_CIO_PROPOSAL``.

    Parameters
    ----------
    cio_proposal : Dict
        Raw JSON dict from the CIO agent.  Must contain:
        ``ticker``, ``action``, ``entry``, ``target``,
        ``conviction_score``, ``regime``.
    quant_snapshot : Dict
        Quant engine output from ``KEY_QUANT_SNAPSHOT``.  Must contain:
        ``atr``, ``ticker``.
    portfolio_equity : float, optional
        Portfolio equity in currency units (default: ``DEFAULT_PORTFOLIO_EQUITY``).

    Returns
    -------
    Dict
        JSON-safe dictionary with all ``ValidatedTrade`` fields.
        Check the ``killed`` flag before execution.

    Raises
    ------
    ValueError
        If required keys are missing, ATR is invalid, or proposal is malformed.
    """

    ticker = cio_proposal.get("ticker", "UNKNOWN")

    # ── Step 1: Validate Inputs ──────────────────────────────
    _validate_proposal(cio_proposal)
    _validate_snapshot(quant_snapshot)

    # ── Ticker Consistency Guard ─────────────────────────────
    if cio_proposal["ticker"] != quant_snapshot["ticker"]:
        raise ValueError(
            f"Ticker mismatch: CIO={cio_proposal['ticker']} "
            f"Quant={quant_snapshot['ticker']}"
        )

    logger.info("[%s] RiskTool → validating CIO proposal", ticker)

    # ── Step 2: Extract ATR ──────────────────────────────────
    atr: float = float(quant_snapshot["atr"])

    # ── Step 3: Run Deterministic Risk Engine ────────────────
    trade: ValidatedTrade = apply_risk_limits(
        cio_proposal,
        atr,
        portfolio_equity,
    )

    # ── Step 4: Convert Dataclass → Dict ─────────────────────
    result: Dict = _trade_to_dict(trade)

    # ── Step 5: Log Outcome ──────────────────────────────────
    if trade.killed:
        logger.warning(
            "[%s] RiskTool → KILLED %s",
            trade.ticker,
            trade.kill_reason or "unknown reason",
        )
    else:
        logger.info(
            "[%s] RiskTool → ACCEPTED size=%d rr=%.1f",
            trade.ticker,
            trade.position_size,
            trade.risk_reward_ratio,
        )

    return result


# ──────────────────────────────────────────────────────────────
# Standalone Test
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    cio_proposal = {
        "ticker": "RELIANCE.NS",
        "action": "BUY",
        "entry": 2800,
        "target": 3100,
        "conviction_score": 0.7,
        "regime": "BULL",
    }

    quant_snapshot = {
        "ticker": "RELIANCE.NS",
        "atr": 30,
    }

    trade = risk_enforcement_tool(
        cio_proposal,
        quant_snapshot,
        portfolio_equity=1_000_000,
    )

    print("\n=== Risk Enforcement Tool Output ===")
    print(json.dumps(trade, indent=2))
