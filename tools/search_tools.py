"""
tools/search_tools.py – Search Query Utilities
================================================
Helper functions for constructing optimised Google Search queries.
The Researcher agent uses these to build targeted prompts.

NOTE: Actual Search Grounding is handled automatically by the ADK when
you pass `tools=[google_search]` to LlmAgent. These are purely helper
utilities for query construction, NOT the grounding mechanism itself.
"""

from config import TARGET_EXCHANGE


def format_search_query(ticker: str, query_type: str = "news") -> str:
    """
    Build a focused Google Search query string for a stock ticker.

    Args:
        ticker:     The ticker symbol (e.g., 'RELIANCE.NS').
        query_type: Type of search – 'news', 'earnings', or 'sentiment'.

    Returns:
        A formatted search query string.
    """
    # Strip exchange suffix for cleaner queries (RELIANCE.NS → RELIANCE)
    clean_name = ticker.split(".")[0]

    templates: dict[str, str] = {
        "news":      f"{clean_name} {TARGET_EXCHANGE} stock latest news today",
        "earnings":  f"{clean_name} quarterly earnings results 2025 2026",
        "sentiment": f"{clean_name} stock analyst opinion buy sell rating",
    }
    return templates.get(query_type, templates["news"])


def build_macro_query(topic: str = "india") -> str:
    """
    Build a macro-level market conditions search query.

    Args:
        topic: 'india', 'global', 'rbi', or 'fed'.

    Returns:
        A formatted macro search query string.
    """
    templates: dict[str, str] = {
        "india":  "Indian stock market NSE BSE outlook today",
        "global": "Global equity market risk sentiment this week",
        "rbi":    "RBI monetary policy interest rate decision latest",
        "fed":    "US Federal Reserve interest rate decision stock market impact",
    }
    return templates.get(topic, templates["india"])
