"""
core/models.py – Shared Data Structures
=========================================
All dataclasses used across the pipeline. Every agent, strategy module,
and the pipeline orchestrator imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List

IST = timezone(timedelta(hours=5, minutes=30))


# ── Market Regime ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MarketRegime:
    """Output of the Regime Agent."""

    trend: str          # "bull", "bear", "sideways"
    volatility: str     # "high", "low"

    def __post_init__(self):
        assert self.trend in ("bull", "bear", "sideways"), f"Invalid trend: {self.trend}"
        assert self.volatility in ("high", "low"), f"Invalid volatility: {self.volatility}"

    def to_dict(self) -> dict:
        return asdict(self)


# ── News Sentiment ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class NewsSentiment:
    """Output of the Sentiment Agent."""

    score: float        # -1.0 … +1.0
    bucket: str         # "positive", "neutral", "negative"
    danger: bool        # True when crisis-level negative news detected

    def __post_init__(self):
        assert self.bucket in ("positive", "neutral", "negative"), f"Invalid bucket: {self.bucket}"

    def to_dict(self) -> dict:
        return asdict(self)


# ── Scenario ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Scenario:
    """Output of the Scenario Agent – regime × sentiment combination."""

    label: str                  # e.g. "bull_positive", "sideways_danger"
    regime: MarketRegime
    sentiment: NewsSentiment

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "regime": self.regime.to_dict(),
            "sentiment": self.sentiment.to_dict(),
        }


# ── Strategy Result ────────────────────────────────────────────────────────────

@dataclass
class StrategyResult:
    """Output of the Backtester for a single strategy."""

    name: str
    win_rate: float         # 0.0 – 1.0
    avg_return: float       # average per-trade return (decimal)
    max_drawdown: float     # worst peak-to-trough (decimal, positive number)
    sharpe: float           # risk-adjusted return
    composite_score: float = 0.0   # filled by selector

    def to_dict(self) -> dict:
        return asdict(self)


# ── Trade Record ───────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    """A single paper trade logged by the pipeline."""

    scenario_label: str
    strategy_name: str
    regime_trend: str
    regime_volatility: str
    news_bucket: str
    ticker: str
    entry: float
    stop: float
    target: float
    size: int               # number of shares
    risk_per_share: float   # entry - stop
    rr_ratio: float         # (target - entry) / risk_per_share
    outcome: str = "open"   # "open", "win", "loss", "scratch"
    pnl_pct: float = 0.0
    exit_price: Optional[float] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    )
    closed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> TradeRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
