"""
utils/helpers.py – Shared Utility Functions
=============================================
Utility functions used across agents, tools, and the UI.
Add shared logic here to keep agents clean and focused.
"""

import json
from typing import Any


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


def extract_decisions_from_state(state: dict[str, Any]) -> list[dict]:
    """
    Parse the trade_decision text block from session.state into a list
    of structured decision dicts for the Streamlit UI.

    Args:
        state: The session.state dictionary.

    Returns:
        A list of dicts, each representing one ticker's trade decision.
        Falls back to a single dict with raw text if parsing fails.

    TODO: Replace this simple parser with a proper Pydantic output schema
          once the DecisionMaker prompt is stabilised.
    """
    raw: str = state.get("trade_decision", "")
    if not raw:
        return [{"error": "No trade decision found in session state."}]

    decisions: list[dict] = []
    current: dict = {}

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("- ticker:"):
            if current:
                decisions.append(current)
            current = {"ticker": line.split(":", 1)[-1].strip()}
        elif ":" in line and current:
            k, _, v = line.partition(":")
            current[k.strip().lstrip("- ")] = v.strip()

    if current:
        decisions.append(current)

    return decisions if decisions else [{"raw": raw}]


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
