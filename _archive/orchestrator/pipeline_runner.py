"""
orchestrator/pipeline_runner.py – Production-Grade Trading Pipeline Orchestrator
==================================================================================
Main execution entrypoint for the Regime-Aware Trading Command Center.

Orchestrates the full 7-step pipeline sequentially:

    Step 1: QuantTool        → Fetch OHLCV, compute indicators, classify regime
    Step 2: QuantAgent       → Interpret quant snapshot into professional analysis
    Step 3: SentimentAgent   → Search news/macro, write sentiment summary
    Step 4: BullAgent        → Build strongest bullish thesis
    Step 5: BearAgent        → Build strongest bearish counter-thesis
    Step 6: CIOAgent         → Synthesise debate into disciplined trade proposal
    Step 7: RiskTool         → Enforce ATR stop-loss, position sizing, R:R gate

Uses ADK's InMemorySessionService as the shared whiteboard between steps.
Each step reads from and writes to well-defined session state keys.

Design principles:
    • Sequential execution — each step depends on prior outputs.
    • Fail-fast — state validation after every step.
    • Deterministic risk — LLM never touches risk parameters.
    • Production-safe logging — structured, timestamped, level-aware.
    • Ticker normalisation — prevents UI bugs from inconsistent formats.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from typing import Dict

# Ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

from config import DEFAULT_PORTFOLIO_EQUITY

from tools.quant_tool import quant_engine_tool
from tools.risk_tool import risk_enforcement_tool

from agents.quant_agent import quant_agent
from agents.sentiment_agent import sentiment_agent
from agents.bull_agent import bull_agent
from agents.bear_agent import bear_agent
from agents.cio_agent import cio_agent

from pipeline.session_keys import (
    KEY_QUANT_SNAPSHOT,
    KEY_QUANT_ANALYSIS,
    KEY_SENTIMENT,
    KEY_BULL_THESIS,
    KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
    KEY_FINAL_TRADE,
)

# ── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger: logging.Logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME: str = "trading_pipeline"
USER_ID: str = "system"
SESSION_ID: str = "pipeline_session"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _validate_state(state: dict, key: str, step_label: str) -> None:
    """Raise ``RuntimeError`` if *key* is missing or empty in *state*.

    Args:
        state:      The session state dict.
        key:        The session key to check.
        step_label: Human-readable step name for the error message.
    """
    if key not in state or not state[key]:
        raise RuntimeError(
            f"{step_label} failed — key '{key}' not found in session state."
        )


async def _run_agent(
    runner: Runner,
    user_id: str,
    session_id: str,
    message_text: str,
    step_label: str,
) -> None:
    """Execute an ADK agent via its runner and log progress.

    Args:
        runner:       The ADK ``Runner`` wrapping the agent.
        user_id:      User ID for the session.
        session_id:   Session ID for the session.
        message_text: The user message to send to the agent.
        step_label:   Human-readable label for logging.
    """
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.content and event.content.parts:
            text = "".join(p.text for p in event.content.parts if p.text)
            if text:
                logger.debug(
                    "[%s] %s responded (%d chars)",
                    step_label,
                    event.author,
                    len(text),
                )


def _parse_cio_proposal(raw_text: str, quant_snapshot: dict) -> Dict:
    """Parse the CIO agent's structured text output into a risk-tool-compatible dict.

    The CIO agent outputs a fixed text format::

        Action: BUY
        Ticker: RELIANCE.NS
        Entry: 1420
        Raw Stop Loss: 1380
        Target: 1500
        Conviction: 0.7
        Reasoning: ...

    This function extracts those fields with regex and merges ``regime``
    from the quant snapshot (the CIO never writes regime as a separate field).

    Args:
        raw_text:       Raw CIO agent text output from session state.
        quant_snapshot: The quant engine dict (provides ``regime``).

    Returns:
        Dict with keys: ticker, action, entry, target, conviction_score, regime.

    Raises:
        RuntimeError: If a required field cannot be parsed from the text.
    """

    def _extract(pattern: str, label: str) -> str:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if not match:
            raise RuntimeError(
                f"CIO proposal parsing failed — could not find '{label}' "
                f"in CIO output.\n\nRaw output:\n{raw_text[:500]}"
            )
        return match.group(1).strip()

    action = _extract(r"Action:\s*(.+)", "Action")
    ticker = _extract(r"Ticker:\s*(.+)", "Ticker")
    entry = float(_extract(r"Entry:\s*([\d.]+)", "Entry"))
    raw_stop = float(_extract(r"Raw Stop Loss:\s*([\d.]+)", "Raw Stop Loss"))
    target = float(_extract(r"Target:\s*([\d.]+)", "Target"))
    conviction = float(_extract(r"Conviction:\s*([\d.]+)", "Conviction"))

    regime = quant_snapshot.get("regime", "NEUTRAL")

    proposal = {
        "ticker": ticker,
        "action": action.upper(),
        "entry": entry,
        "raw_stop_loss": raw_stop,
        "target": target,
        "conviction_score": conviction,
        "regime": regime,
    }

    logger.info(
        "CIO proposal parsed | action=%s ticker=%s entry=%.2f target=%.2f conviction=%.2f",
        proposal["action"],
        proposal["ticker"],
        proposal["entry"],
        proposal["target"],
        proposal["conviction_score"],
    )

    return proposal


# ── Main Pipeline ──────────────────────────────────────────────────────────────

async def run_pipeline(ticker: str) -> Dict:
    """Execute the full 7-step regime-aware trading pipeline.

    Args:
        ticker: Stock ticker symbol (e.g. ``"RELIANCE"`` or ``"RELIANCE.NS"``).
                Automatically normalised to uppercase with ``.NS`` suffix.

    Returns:
        A dictionary containing all pipeline outputs::

            {
                "quant_snapshot": ...,
                "quant_analysis": ...,
                "sentiment": ...,
                "bull_thesis": ...,
                "bear_thesis": ...,
                "cio_proposal": ...,
                "final_trade": ...,
            }

    Raises:
        RuntimeError: If any pipeline step fails to write its expected state key.
        ValueError:   If quant or risk tool inputs are invalid.
    """
    try:
        # ── Normalize Ticker ───────────────────────────────────────────────────
        ticker = ticker.upper()
        if not ticker.endswith(".NS"):
            ticker = ticker + ".NS"
        logger.info("Pipeline starting | ticker=%s", ticker)

        # ── STEP 1 — Quant Tool (before session, so state is pre-populated) ──
        logger.info("STEP 1 — Generating Quant Snapshot for %s ...", ticker)
        snapshot: dict = quant_engine_tool(ticker)

        if not snapshot:
            raise RuntimeError("quant_engine_tool returned empty snapshot")

        logger.info(
            "STEP 1 — Quant Snapshot Generated | regime=%s | price=%s",
            snapshot.get("regime"),
            snapshot.get("price"),
        )

        # ── Session Setup (snapshot must be in initial state for ADK
        #    instruction templating, e.g. {quant_snapshot}) ─────────────────────
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state={KEY_QUANT_SNAPSHOT: snapshot},
        )
        state = session.state
        _validate_state(state, KEY_QUANT_SNAPSHOT, "STEP 1 — Quant Tool")

        # ── Create Runners ────────────────────────────────────────────────────
        quant_runner = Runner(
            app_name=APP_NAME,
            agent=quant_agent,
            session_service=session_service,
        )
        sentiment_runner = Runner(
            app_name=APP_NAME,
            agent=sentiment_agent,
            session_service=session_service,
        )
        bull_runner = Runner(
            app_name=APP_NAME,
            agent=bull_agent,
            session_service=session_service,
        )
        bear_runner = Runner(
            app_name=APP_NAME,
            agent=bear_agent,
            session_service=session_service,
        )
        cio_runner = Runner(
            app_name=APP_NAME,
            agent=cio_agent,
            session_service=session_service,
        )

        # ── STEP 2 — Quant Agent ──────────────────────────────────────────────
        logger.info("STEP 2 — Running QuantAgent ...")
        await _run_agent(
            runner=quant_runner,
            user_id=USER_ID,
            session_id=SESSION_ID,
            message_text=(
                f"Interpret the quant snapshot for {ticker}. "
                f"The snapshot is already in session state at key '{KEY_QUANT_SNAPSHOT}'."
            ),
            step_label="STEP 2",
        )

        # Re-fetch session to pick up state mutations
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        state = session.state
        _validate_state(state, KEY_QUANT_ANALYSIS, "STEP 2 — QuantAgent")
        logger.info("STEP 2 — Quant Analysis Complete")

        # ── STEP 3 — Sentiment Agent ──────────────────────────────────────────
        logger.info("STEP 3 — Running SentimentAgent ...")
        await _run_agent(
            runner=sentiment_runner,
            user_id=USER_ID,
            session_id=SESSION_ID,
            message_text=(
                f"Analyze recent news and macro sentiment for {ticker}. "
                f"The quant snapshot is in session state at key '{KEY_QUANT_SNAPSHOT}'."
            ),
            step_label="STEP 3",
        )

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        state = session.state
        _validate_state(state, KEY_SENTIMENT, "STEP 3 — SentimentAgent")
        logger.info("STEP 3 — Sentiment Analysis Complete")

        # ── STEP 4 — Bull Agent ───────────────────────────────────────────────
        logger.info("STEP 4 — Running BullAgent ...")
        await _run_agent(
            runner=bull_runner,
            user_id=USER_ID,
            session_id=SESSION_ID,
            message_text=(
                f"Build the strongest possible bullish case for {ticker}. "
                f"Use the quant snapshot, quant analysis, and sentiment "
                f"already in session state."
            ),
            step_label="STEP 4",
        )

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        state = session.state
        _validate_state(state, KEY_BULL_THESIS, "STEP 4 — BullAgent")
        logger.info("STEP 4 — Bull Thesis Generated")

        # ── STEP 5 — Bear Agent ───────────────────────────────────────────────
        logger.info("STEP 5 — Running BearAgent ...")
        await _run_agent(
            runner=bear_runner,
            user_id=USER_ID,
            session_id=SESSION_ID,
            message_text=(
                f"Build the strongest possible bearish case for {ticker}. "
                f"Challenge the Bull thesis. Use the quant snapshot, quant analysis, "
                f"sentiment, and bull thesis already in session state."
            ),
            step_label="STEP 5",
        )

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        state = session.state
        _validate_state(state, KEY_BEAR_THESIS, "STEP 5 — BearAgent")
        logger.info("STEP 5 — Bear Thesis Generated")

        # ── STEP 6 — CIO Agent ────────────────────────────────────────────────
        logger.info("STEP 6 — Running CIOAgent ...")
        await _run_agent(
            runner=cio_runner,
            user_id=USER_ID,
            session_id=SESSION_ID,
            message_text=(
                f"Make the final trading decision for {ticker}. "
                f"Evaluate the quant data, sentiment, bull thesis, and bear thesis "
                f"already in session state. Produce a disciplined trade proposal."
            ),
            step_label="STEP 6",
        )

        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        state = session.state
        _validate_state(state, KEY_CIO_PROPOSAL, "STEP 6 — CIOAgent")
        logger.info("STEP 6 — CIO Decision Complete")

        # ── STEP 7 — Risk Tool ────────────────────────────────────────────────
        logger.info("STEP 7 — Running Risk Enforcement ...")
        cio_raw = state[KEY_CIO_PROPOSAL]
        quant_snapshot = state[KEY_QUANT_SNAPSHOT]

        # CIO output is structured text — parse into dict for risk engine
        cio_proposal: dict = _parse_cio_proposal(cio_raw, quant_snapshot)

        final_trade: dict = risk_enforcement_tool(
            cio_proposal,
            quant_snapshot,
            DEFAULT_PORTFOLIO_EQUITY,
        )

        state[KEY_FINAL_TRADE] = final_trade
        _validate_state(state, KEY_FINAL_TRADE, "STEP 7 — RiskTool")
        logger.info("STEP 7 — Risk Enforcement Complete")

        # ── Return All Outputs ─────────────────────────────────────────────────
        logger.info("Pipeline complete | ticker=%s", ticker)

        return {
            "quant_snapshot": state[KEY_QUANT_SNAPSHOT],
            "quant_analysis": state[KEY_QUANT_ANALYSIS],
            "sentiment": state[KEY_SENTIMENT],
            "bull_thesis": state[KEY_BULL_THESIS],
            "bear_thesis": state[KEY_BEAR_THESIS],
            "cio_proposal": state[KEY_CIO_PROPOSAL],
            "final_trade": state[KEY_FINAL_TRADE],
        }

    except Exception:
        logger.exception("Pipeline failed")
        raise


# ── Standalone Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":

    result = asyncio.run(run_pipeline("RELIANCE"))

    print("\nFINAL TRADE:\n")
    print(result["final_trade"])
