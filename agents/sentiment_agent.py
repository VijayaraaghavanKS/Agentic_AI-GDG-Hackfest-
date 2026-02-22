"""
agents/sentiment_agent.py – News Sentiment Scorer
====================================================
Input: list of news headlines
Logic: keyword scoring → score/bucket/danger
Output: NewsSentiment
"""

from __future__ import annotations

import re
from typing import List

from core.models import NewsSentiment


_POSITIVE = {
    "upgrade", "buy", "outperform", "beat", "profit", "growth", "surge",
    "rally", "bullish", "record", "strong", "gain", "jumps", "soars",
    "rises", "dividend", "expansion", "acquisition", "optimistic", "boost",
    "recovery", "earnings", "revenue", "ipo", "approval",
}

_NEGATIVE = {
    "downgrade", "sell", "underperform", "miss", "loss", "decline", "crash",
    "bearish", "weak", "fall", "drops", "sinks", "cut", "warning", "risk",
    "investigation", "fraud", "default", "layoff", "shutdown", "bankruptcy",
    "debt", "lawsuit", "penalty", "probe", "scandal", "recession",
}

_DANGER_KEYWORDS = {
    "crisis", "crash", "halt", "ban", "emergency", "collapse", "default",
    "bankrupt", "fraud", "scam", "seized", "suspended", "delisted",
}


def _score_headline(headline: str) -> float:
    words = set(re.findall(r"[a-z]+", headline.lower()))
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    total = pos + neg
    return round((pos - neg) / total, 4) if total > 0 else 0.0


def _has_danger(headline: str) -> bool:
    words = set(re.findall(r"[a-z]+", headline.lower()))
    return bool(words & _DANGER_KEYWORDS)


def analyze(headlines: List[str]) -> dict:
    """Score news headlines and produce sentiment output.

    Parameters
    ----------
    headlines : list[str]
        Raw news headlines.

    Returns
    -------
    dict
        status, sentiment (NewsSentiment), details.
    """
    if not headlines:
        sentiment = NewsSentiment(score=0.0, bucket="neutral", danger=False)
        return {
            "status": "success",
            "sentiment": sentiment,
            "details": {"headline_count": 0, "note": "No headlines provided"},
        }

    scores = [_score_headline(h) for h in headlines]
    avg_score = round(sum(scores) / len(scores), 4)

    if avg_score >= 0.2:
        bucket = "positive"
    elif avg_score <= -0.2:
        bucket = "negative"
    else:
        bucket = "neutral"

    # Danger: any headline has crisis keywords OR score extremely negative
    danger = any(_has_danger(h) for h in headlines) or avg_score <= -0.6

    sentiment = NewsSentiment(score=avg_score, bucket=bucket, danger=danger)

    return {
        "status": "success",
        "sentiment": sentiment,
        "details": {
            "headline_count": len(headlines),
            "avg_score": avg_score,
            "bucket": bucket,
            "danger": danger,
            "headlines_scored": list(zip(headlines[:5], scores[:5])),
        },
    }
