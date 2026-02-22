"""
memory/trade_memory.py – Trade Outcome Persistence
=====================================================
JSON-backed store for recording trades with full context:
scenario, strategy, regime, news bucket, outcome.

Provides ``memory_bias()`` — a float multiplier based on historical
win rate for a specific (scenario_label, strategy_name) combination.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional

from core.models import TradeRecord


_DEFAULT_PATH = Path(__file__).parent / "trade_memory.json"
_lock = threading.Lock()


class TradeMemory:
    """Thread-safe JSON-backed trade memory."""

    def __init__(self, path: str | Path = _DEFAULT_PATH):
        self._path = Path(path)
        self._trades: List[dict] = []
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._trades = json.load(f)
            except (json.JSONDecodeError, Exception):
                self._trades = []
        else:
            self._trades = []

    def _save(self) -> None:
        os.makedirs(self._path.parent, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._trades, f, indent=2, default=str)

    # ── Store ─────────────────────────────────────────────────────────────

    def store(self, record: TradeRecord) -> None:
        """Append a trade record to memory and persist."""
        with _lock:
            self._trades.append(record.to_dict())
            self._save()

    # ── Update Outcome ────────────────────────────────────────────────────

    def update_outcome(
        self,
        ticker: str,
        exit_price: float,
        outcome: str,
        pnl_pct: float,
        closed_at: str,
    ) -> Optional[dict]:
        """Close the most recent open trade for *ticker*.

        Returns the updated trade dict, or None if not found.
        """
        with _lock:
            for trade in reversed(self._trades):
                if trade.get("ticker") == ticker and trade.get("outcome") == "open":
                    trade["exit_price"] = exit_price
                    trade["outcome"] = outcome
                    trade["pnl_pct"] = pnl_pct
                    trade["closed_at"] = closed_at
                    self._save()
                    return trade
        return None

    # ── Query ─────────────────────────────────────────────────────────────

    def get_similar(
        self,
        scenario_label: str,
        strategy_name: str,
    ) -> List[dict]:
        """Return all past trades with the same scenario + strategy combo."""
        return [
            t for t in self._trades
            if t.get("scenario_label") == scenario_label
            and t.get("strategy_name") == strategy_name
        ]

    def memory_bias(
        self,
        scenario_label: str,
        strategy_name: str,
    ) -> float:
        """Return a multiplier (0.5–1.5) based on historical win rate.

        - No data        → 1.0 (neutral)
        - Win rate >= 70% → 1.5 (strong boost)
        - Win rate >= 50% → 1.0 + (wr - 0.5) * 2  (1.0–1.4)
        - Win rate <  50% → max(0.5, wr)  (0.5–1.0)
        """
        similar = self.get_similar(scenario_label, strategy_name)
        closed = [t for t in similar if t.get("outcome") in ("win", "loss", "scratch")]
        if len(closed) < 3:
            return 1.0  # not enough data

        wins = sum(1 for t in closed if t.get("outcome") == "win")
        wr = wins / len(closed)

        if wr >= 0.7:
            return 1.5
        elif wr >= 0.5:
            return 1.0 + (wr - 0.5) * 2.0  # 1.0 → 1.4
        else:
            return max(0.5, wr)

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        """Return summary statistics."""
        total = len(self._trades)
        closed = [t for t in self._trades if t.get("outcome") in ("win", "loss", "scratch")]
        wins = sum(1 for t in closed if t.get("outcome") == "win")
        losses = sum(1 for t in closed if t.get("outcome") == "loss")
        if closed:
            avg_pnl = sum(t.get("pnl_pct", 0) for t in closed) / len(closed)
            win_rate = wins / len(closed)
        else:
            avg_pnl = 0.0
            win_rate = 0.0

        return {
            "total_trades": total,
            "closed": len(closed),
            "open": total - len(closed),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "avg_pnl_pct": round(avg_pnl, 4),
        }

    def __len__(self) -> int:
        return len(self._trades)

    def __repr__(self) -> str:
        return f"TradeMemory({len(self._trades)} trades, path={self._path})"
