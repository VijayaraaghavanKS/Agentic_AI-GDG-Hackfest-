"""
strategy/scenario_builder.py – Scenario Builder
==================================================
Maps (MarketRegime × NewsSentiment) → Scenario label.

Covers all 9+ combinations (3 trends × 3 buckets), plus danger variants.
"""

from __future__ import annotations

from core.models import MarketRegime, NewsSentiment, Scenario


# ── Mapping Table ─────────────────────────────────────────────────────────────
# key: (trend, bucket) → scenario label

_SCENARIO_TABLE: dict[tuple[str, str], str] = {
    # Bull regime
    ("bull", "positive"):  "bull_positive",
    ("bull", "neutral"):   "bull_neutral",
    ("bull", "negative"):  "bull_negative",
    # Sideways regime
    ("sideways", "positive"): "sideways_positive",
    ("sideways", "neutral"):  "sideways_neutral",
    ("sideways", "negative"): "sideways_negative",
    # Bear regime
    ("bear", "positive"):  "bear_positive",
    ("bear", "neutral"):   "bear_neutral",
    ("bear", "negative"):  "bear_negative",
}


def build_scenario(regime: MarketRegime, sentiment: NewsSentiment) -> Scenario:
    """Build a Scenario from regime + sentiment.

    Parameters
    ----------
    regime : MarketRegime
        Output of the Regime Agent (trend + volatility).
    sentiment : NewsSentiment
        Output of the Sentiment Agent (score, bucket, danger).

    Returns
    -------
    Scenario
        With label, regime, sentiment. If danger=True, label ends with "_danger".
    """
    key = (regime.trend, sentiment.bucket)
    base_label = _SCENARIO_TABLE.get(key, f"{regime.trend}_{sentiment.bucket}")

    if sentiment.danger:
        label = f"{base_label}_danger"
    else:
        label = base_label

    return Scenario(label=label, regime=regime, sentiment=sentiment)
