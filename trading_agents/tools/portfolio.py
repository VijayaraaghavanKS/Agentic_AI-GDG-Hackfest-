"""Portfolio state persistence and queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from trading_agents.config import INITIAL_CAPITAL
from trading_agents.models import PortfolioState, Position


MEMORY_DIR = Path("memory")
PORTFOLIO_FILE = MEMORY_DIR / "portfolio.json"


def load_portfolio() -> PortfolioState:
    """Load portfolio state from disk, or return a fresh one."""
    if not PORTFOLIO_FILE.exists():
        return PortfolioState(cash=INITIAL_CAPITAL)

    raw = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
    return PortfolioState(
        cash=raw.get("cash", INITIAL_CAPITAL),
        open_positions=[Position(**p) for p in raw.get("open_positions", [])],
        closed_trades=raw.get("closed_trades", []),
        realized_pnl=raw.get("realized_pnl", 0.0),
        actions_log=raw.get("actions_log", []),
    )


def save_portfolio(state: PortfolioState) -> None:
    """Persist portfolio state to disk."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    payload = state.model_dump()
    payload["actions_log"] = payload["actions_log"][-50:]
    PORTFOLIO_FILE.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def get_portfolio_summary() -> Dict:
    """Return a human-readable portfolio summary."""
    p = load_portfolio()
    total_invested = sum(pos.qty * pos.entry for pos in p.open_positions)
    return {
        "status": "success",
        "cash": round(p.cash, 2),
        "total_invested": round(total_invested, 2),
        "portfolio_value": round(p.cash + total_invested, 2),
        "open_positions_count": len(p.open_positions),
        "open_positions": [
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "entry": pos.entry,
                "stop": pos.stop,
                "target": pos.target,
                "invested": round(pos.qty * pos.entry, 2),
                "opened_at": pos.opened_at,
            }
            for pos in p.open_positions
        ],
        "realized_pnl": round(p.realized_pnl, 2),
        "recent_actions": p.actions_log[-10:],
    }


def reset_portfolio() -> Dict:
    """Reset portfolio to initial clean state."""
    fresh = PortfolioState(cash=INITIAL_CAPITAL)
    save_portfolio(fresh)
    return {"status": "success", "message": f"Portfolio reset to INR {INITIAL_CAPITAL:,.0f}"}
