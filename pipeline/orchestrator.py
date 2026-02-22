"""
pipeline/orchestrator.py – Lightweight orchestrator facade
==========================================================
Provides the public `Orchestrator` class used by `main.py` and `app.py`.

Execution is delegated to the unified pipeline in `agents/pipeline.py`.
"""

from __future__ import annotations


class Orchestrator:
    """Thin facade over `agents.pipeline.run_pipeline`."""

    def __init__(self, ticker: str, portfolio_equity: float = 1_000_000.0):
        """
        Args:
            ticker:           The stock ticker to analyse (e.g., 'RELIANCE.NS').
            portfolio_equity: Total portfolio equity in INR for position sizing.
        """
        self.ticker = ticker
        self.portfolio_equity = portfolio_equity

    def run(self) -> dict:
        """
        Execute the full production trading pipeline.

        Returns:
            Pipeline output dict with regime, sentiment, scenario, strategy,
            trade execution result, and memory stats.
        """
        from agents.pipeline import run_pipeline

        return run_pipeline(
            ticker=self.ticker,
            portfolio_value=self.portfolio_equity,
        )
