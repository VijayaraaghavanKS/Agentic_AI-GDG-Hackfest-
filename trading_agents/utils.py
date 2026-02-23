"""
trading_agents/utils.py – Shared Utility Functions
====================================================
Ported from _archive/utils/helpers.py.
Includes JSON parsing for CIO output, currency formatting, and display helpers.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional


# ── Logging ───────────────────────────────────────────────────────────────────


def setup_logger(name: str = "regime_trading", level: int = logging.INFO) -> logging.Logger:
    """Create a standardised logger for pipeline components.

    Args:
        name:  Logger name.
        level: Logging level (default INFO).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "[%(asctime)s] %(name)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ── CIO JSON Parsing ─────────────────────────────────────────────────────────


def parse_cio_json(raw: str) -> Optional[dict]:
    """Parse the CIO agent's raw text output into a structured dict.

    The CIO / debate judge may output pure JSON or wrap it in markdown
    fences.  This function extracts and validates the JSON block.

    Args:
        raw: The raw string from the CIO verdict.

    Returns:
        A parsed dict (keys vary by agent output), or None if parsing fails.
    """
    if not raw:
        return None

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find embedded JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None


# ── Currency Formatting ──────────────────────────────────────────────────────


def format_currency_inr(value: float) -> str:
    """Format a float as an Indian Rupee string.

    Args:
        value: Numeric price value.

    Returns:
        Formatted string, e.g. '₹1,234.56'.
    """
    return f"₹{value:,.2f}"


# ── Display Helpers ──────────────────────────────────────────────────────────


def get_action_colour(action: str) -> str:
    """Return a CSS colour hex for a BUY/SELL/HOLD action label.

    Args:
        action: 'BUY', 'SELL', or 'HOLD'.

    Returns:
        Hex colour string.
    """
    colours = {
        "BUY": "#00C853",   # Green
        "SELL": "#D50000",  # Red
        "HOLD": "#FF6D00",  # Amber
    }
    return colours.get(action.upper(), "#FFFFFF")


def format_risk_reward(rr_ratio: float) -> str:
    """Format a risk/reward ratio for display.

    Args:
        rr_ratio: The risk-to-reward ratio (e.g. 2.5).

    Returns:
        Formatted string, e.g. '1:2.50'.
    """
    return f"1:{rr_ratio:.2f}"


# ── Session State Printing ────────────────────────────────────────────────────


def pretty_print_state(state: dict[str, Any]) -> None:
    """Pretty-print ADK session state to stdout (debug helper).

    Args:
        state: The session.state dictionary from the ADK runner.
    """
    print("\n" + "=" * 60)
    print("  SHARED WHITEBOARD (session.state)")
    print("=" * 60)
    for key, value in state.items():
        print(f"\n[{key.upper()}]")
        print(value if isinstance(value, str) else json.dumps(value, indent=2))
    print("=" * 60 + "\n")


# ── Search Query Builders (from tools/search_tools.py) ───────────────────────

TARGET_EXCHANGE = "NSE"


def format_search_query(ticker: str, query_type: str = "news") -> str:
    """Build a focused Google Search query string for a stock ticker.

    Args:
        ticker:     The ticker symbol (e.g., 'RELIANCE.NS').
        query_type: Type of search – 'news', 'earnings', or 'sentiment'.

    Returns:
        A formatted search query string.
    """
    clean_name = ticker.split(".")[0]
    templates: dict[str, str] = {
        "news": f"{clean_name} {TARGET_EXCHANGE} stock latest news today",
        "earnings": f"{clean_name} quarterly earnings results 2025 2026",
        "sentiment": f"{clean_name} stock analyst opinion buy sell rating",
    }
    return templates.get(query_type, templates["news"])


def build_macro_query(topic: str = "india") -> str:
    """Build a macro-level market conditions search query.

    Args:
        topic: 'india', 'global', 'rbi', or 'fed'.

    Returns:
        A formatted macro search query string.
    """
    templates: dict[str, str] = {
        "india": "Indian stock market NSE BSE outlook today",
        "global": "Global equity market risk sentiment this week",
        "rbi": "RBI monetary policy interest rate decision latest",
        "fed": "US Federal Reserve interest rate decision stock market impact",
    }
    return templates.get(topic, templates["india"])
