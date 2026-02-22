"""
pipeline/session_keys.py – ADK Session State Key Registry
===========================================================
A single file of string constants used as keys on the ADK
InMemorySessionService shared whiteboard. All agents and tools
import from HERE — eliminates typo-driven bugs.

This file IS the contract between every component in the system.
"""

# ── Step 0: Market Context (Bloomberg-style overview) ─────────────────────
KEY_MARKET_CONTEXT = "market_context"
"""
Written by: market_context_agent (Step 0)
Read by:    bull_agent, bear_agent
Contains:   JSON with nifty_regime, banknifty_regime, trade_bias, vix_level,
            fii_dii_flow, macro_cues, market_health
"""

# ── Step 1: Quant Engine Output ────────────────────────────────────────────────
KEY_QUANT_SNAPSHOT = "quant_snapshot"
"""
Written by: quant_tool (Step 1)
Read by:    sentiment_agent, bull_agent, bear_agent, cio_agent
Contains:   RegimeSnapshot dict — regime, close, DMA50, DMA200, ATR, RSI, MACD
"""

# ── Step 1b: Quant Agent Analysis (interpreted quant snapshot) ─────────────────
KEY_QUANT_ANALYSIS = "quant_analysis"
"""
Written by: quant_agent (Step 2 in pipeline_runner)
Read by:    sentiment_agent, bull_agent, bear_agent, cio_agent
Contains:   Professional narrative interpreting the quant snapshot
"""

# ── Step 2: Sentiment Agent Output ─────────────────────────────────────────────
KEY_SENTIMENT = "sentiment_summary"
"""
Written by: sentiment_agent (Step 2)
Read by:    bull_agent, bear_agent, cio_agent
Contains:   Structured macro/news sentiment summary text
"""

# ── Step 3: Bull Agent Thesis ──────────────────────────────────────────────────
KEY_BULL_THESIS = "bull_thesis"
"""
Written by: bull_agent (Step 3)
Read by:    bear_agent, cio_agent
Contains:   Aggressive bullish thesis text
"""

# ── Step 4: Bear Agent Thesis ──────────────────────────────────────────────────
KEY_BEAR_THESIS = "bear_thesis"
"""
Written by: bear_agent (Step 4)
Read by:    cio_agent
Contains:   Skeptical counter-thesis text
"""

# ── Step 5: CIO Raw Proposal ──────────────────────────────────────────────────
KEY_CIO_PROPOSAL = "cio_proposal"
"""
Written by: cio_agent (Step 5)
Read by:    risk_tool (Step 6)
Contains:   Raw JSON trade proposal — action, entry, raw_stop_loss, target,
            conviction_score. NOT yet risk-validated.
"""

# ── Step 6: Final Validated Trade ──────────────────────────────────────────────
KEY_FINAL_TRADE = "final_trade"
"""
Written by: risk_tool (Step 6)
Read by:    app.py (Streamlit UI), main.py (CLI)
Contains:   ValidatedTrade dict with enforced stop-loss, position size,
            and risk/reward check. May be None if trade was killed.
"""

# ── Step 7b: Paper Trade Execution Result ─────────────────────────────────────
KEY_PAPER_TRADE = "paper_trade"
"""
Written by: orchestrator/pipeline_runner.py (after risk validation)
Read by:    app.py / main.py / observability tooling
Contains:   Execution result dict from paper trading layer (OPENED/SKIPPED/error)
"""

# ── User Equity (set by app.py / main.py before pipeline runs) ─────────────────
KEY_USER_EQUITY = "user_equity"
"""
Written by: app.py / main.py (before pipeline runs)
Read by:    risk_tool_agent (Step 7)
Contains:   float — user's portfolio equity in INR
"""

# ── Convenience: All Keys ──────────────────────────────────────────────────────
ALL_KEYS = [
    KEY_MARKET_CONTEXT,
    KEY_QUANT_SNAPSHOT,
    KEY_QUANT_ANALYSIS,
    KEY_SENTIMENT,
    KEY_BULL_THESIS,
    KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
    KEY_FINAL_TRADE,
    KEY_PAPER_TRADE,
    KEY_USER_EQUITY,
]

# ── Learning Loop Keys ────────────────────────────────────────────────────────
KEY_STRATEGY_RECOMMENDATION = "strategy_recommendation"
"""
Written by: learning loop (before pipeline runs)
Read by:    cio_agent (as part of quant_snapshot scenario context)
Contains:   StrategyRecommendation dict — action_bias, conviction range,
            win rate, confidence source, rationale
"""
