"""
utils/helpers.py – Shared Utility Functions
=============================================
Utility functions used across agents, tools, and the UI.
Includes JSON parsing for the CIO output schema, logging helpers,
and formatting utilities for the Streamlit dashboard.
"""

import json
import logging
from typing import Any


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logger(name: str = "regime_trading", level: int = logging.INFO) -> logging.Logger:
    """
    Create a standardised logger for pipeline components.

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


# ── Session State Printing ────────────────────────────────────────────────────

def pretty_print_state(state: dict[str, Any]) -> None:
    """
    Pretty-print the full ADK session state to stdout.
    Useful for debugging the shared whiteboard during development.

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


# ── CIO JSON Parsing ─────────────────────────────────────────────────────────

def parse_cio_json(raw: str) -> dict | None:
    """
    Parse the CIO agent's raw text output into a structured dict.

    The CIO is instructed to output pure JSON, but may wrap it in markdown
    fences or include preamble text. This function extracts and validates
    the JSON block.

    Args:
        raw: The raw string from session.state[KEY_CIO_PROPOSAL].

    Returns:
        A parsed dict with keys: ticker, action, entry, raw_stop_loss,
        target, conviction_score, rationale.
        Returns None if parsing fails.
    """
    if not raw:
        return None

    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None


# ── Formatting ────────────────────────────────────────────────────────────────

def format_currency_inr(value: float) -> str:
    """
    Format a float as an Indian Rupee string.

    Args:
        value: Numeric price value.

    Returns:
        Formatted string, e.g. '₹1,234.56'.
    """
    return f"₹{value:,.2f}"


def get_action_colour(action: str) -> str:
    """
    Return a CSS/Streamlit colour for a BUY/SELL/HOLD action label.

    Args:
        action: 'BUY', 'SELL', or 'HOLD'.

    Returns:
        Hex colour string.
    """
    colours = {
        "BUY":  "#00C853",  # Green
        "SELL": "#D50000",  # Red
        "HOLD": "#FF6D00",  # Amber
    }
    return colours.get(action.upper(), "#FFFFFF")


def format_risk_reward(rr_ratio: float) -> str:
    """
    Format a risk/reward ratio for display.

    Args:
        rr_ratio: The risk-to-reward ratio (e.g. 2.5).

    Returns:
        Formatted string, e.g. '1:2.50'.
    """
    return f"1:{rr_ratio:.2f}"
