"""
main.py – Agentic Pipeline Entry Point
========================================
Runs the multi-agent trading pipeline from the command line.

Usage:
    python main.py                    # Run with default watch list
    python main.py --tickers TCS.NS   # Run for a single ticker

Pipeline Modes (set PIPELINE_MODE in config.py):
    sequential  →  Researcher → Analyst → DecisionMaker (one after another)
    parallel    →  Researcher + Analyst run in parallel → DecisionMaker

ADK Key Concepts used here:
    - Runner          : Executes an agent or pipeline given a user message.
    - InMemorySession : Lightweight session store; swap for DB-backed store in prod.
    - session.state   : The 'shared whiteboard' – agents read/write here.
"""

import asyncio
import argparse

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from config import (
    PIPELINE_MODE,
    WATCH_LIST,
    KEY_TRADE_DECISION,
)
from agents import researcher_agent, analyst_agent, decision_agent
from utils.helpers import pretty_print_state, extract_decisions_from_state


# ── Pipeline Factory ──────────────────────────────────────────────────────────

def build_pipeline(mode: str = PIPELINE_MODE):
    """
    Build and return the top-level orchestrator agent.

    Args:
        mode: 'sequential' or 'parallel'.

    Returns:
        A SequentialAgent or ParallelAgent wrapping all three sub-agents.
    """
    if mode == "parallel":
        # Researcher and Analyst run simultaneously; DecisionMaker waits.
        pre_pipeline = ParallelAgent(
            name="ResearchAndAnalysis",
            sub_agents=[researcher_agent, analyst_agent],
        )
        return SequentialAgent(
            name="TradingPipeline",
            sub_agents=[pre_pipeline, decision_agent],
        )

    # Default: strictly sequential
    return SequentialAgent(
        name="TradingPipeline",
        sub_agents=[researcher_agent, analyst_agent, decision_agent],
    )


# ── Main Runner ───────────────────────────────────────────────────────────────

async def run_pipeline(tickers: list[str] | None = None) -> dict:
    """
    Execute the full trading pipeline for the given tickers.

    Args:
        tickers: List of ticker symbols. Defaults to WATCH_LIST in config.

    Returns:
        The final session.state dict after all agents have run.
    """
    watch_list = tickers or WATCH_LIST

    # Build the orchestrator
    pipeline = build_pipeline(PIPELINE_MODE)

    # Session service holds state between agents in the same run
    session_service = InMemorySessionService()

    runner = Runner(
        agent=pipeline,
        app_name="stock_trading_agent",
        session_service=session_service,
    )

    # The user turn message that kicks off the pipeline
    user_message = genai_types.Content(
        role="user",
        parts=[
            genai_types.Part(text=(
                f"Analyse the following stocks and provide trading decisions: "
                f"{', '.join(watch_list)}"
            ))
        ],
    )

    # Create a new session for this run
    session = await session_service.create_session(
        app_name="stock_trading_agent",
        user_id="hackathon_user",
    )

    print(f"\n{'='*60}")
    print(f" PIPELINE MODE : {PIPELINE_MODE.upper()}")
    print(f" WATCH LIST    : {', '.join(watch_list)}")
    print(f"{'='*60}\n")

    # Stream events from the pipeline
    async for event in runner.run_async(
        user_id="hackathon_user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Log each agent completing
        if event.is_final_response() and event.author:
            print(f"[{event.author}] ✓ Complete")

    # Retrieve the final session state
    final_session = await session_service.get_session(
        app_name="stock_trading_agent",
        user_id="hackathon_user",
        session_id=session.id,
    )

    return dict(final_session.state)


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Stock Market AI Trading Agent – GDG Hackfest"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Space-separated ticker symbols to analyse (e.g. TCS.NS INFY.NS)",
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel"],
        default=PIPELINE_MODE,
        help="Pipeline execution mode (default: from config.py)",
    )
    args = parser.parse_args()

    # Run the async pipeline
    final_state = asyncio.run(run_pipeline(tickers=args.tickers))

    # Debug: print entire shared whiteboard
    pretty_print_state(final_state)

    # Parse and display the structured decisions
    decisions = extract_decisions_from_state(final_state)
    print("\n FINAL TRADE DECISIONS")
    print("-" * 40)
    for d in decisions:
        ticker = d.get("ticker", "N/A")
        action = d.get("action", "N/A")
        conf   = d.get("confidence", "N/A")
        rat    = d.get("rationale", "")
        print(f"  {ticker:<15} {action:<6} (conf: {conf})")
        if rat:
            print(f"    → {rat}")
    print()


if __name__ == "__main__":
    main()
