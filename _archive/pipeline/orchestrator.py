"""
pipeline/orchestrator.py – Sequential ADK Pipeline Orchestrator
================================================================
Wires the full 6-step Regime-Aware Trading pipeline:

    Step 1: quant_tool      → Fetch OHLCV, compute indicators, classify regime
    Step 2: sentiment_agent  → Search news/macro, write sentiment summary
    Step 3: bull_agent       → Read quant + sentiment, write bullish thesis
    Step 4: bear_agent       → Read all above + bull thesis, write bearish teardown
    Step 5: cio_agent        → Synthesise debate into JSON trade proposal
    Step 6: risk_tool        → Enforce ATR stop-loss & 1% position sizing

Uses ADK's InMemorySessionService as the shared whiteboard between steps.

TODO: Implement Orchestrator.run()
"""

from __future__ import annotations


class Orchestrator:
    """
    Initialises the ADK session, runs each pipeline step sequentially,
    and returns the final validated trade proposal (or None) to the caller.
    """

    def __init__(self, ticker: str, portfolio_equity: float = 1_000_000.0):
        """
        Args:
            ticker:           The stock ticker to analyse (e.g., 'RELIANCE.NS').
            portfolio_equity: Total portfolio equity in INR for position sizing.
        """
        self.ticker = ticker
        self.portfolio_equity = portfolio_equity

    async def run(self) -> dict:
        """
        Execute the full 6-step pipeline.

        Returns:
            The final session.state dict containing all intermediate outputs
            and the risk-validated trade in KEY_FINAL_TRADE.
        """
        raise NotImplementedError("TODO: Wire up the 6-step ADK pipeline")
