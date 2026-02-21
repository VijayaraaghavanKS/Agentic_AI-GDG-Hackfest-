"""
app.py – Streamlit Dashboard for the Trading Agent
====================================================
Run with:
    streamlit run app.py

This UI lets you:
    - Select tickers from the WATCH_LIST
    - Trigger the multi-agent pipeline with a single click
    - View the structured trade decisions in a colour-coded table
    - Inspect the raw shared whiteboard (session.state)
"""

import asyncio
import streamlit as st
import pandas as pd

from config import WATCH_LIST, KEY_RESEARCH_OUTPUT, KEY_TECHNICAL_SIGNALS, KEY_TRADE_DECISION
from main import run_pipeline
from utils.helpers import extract_decisions_from_state, get_action_colour


# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Market AI Agent",
    page_icon="📈",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    selected_tickers = st.multiselect(
        "Select Tickers to Analyse",
        options=WATCH_LIST,
        default=WATCH_LIST[:3],
    )

    custom_ticker = st.text_input(
        "Add Custom Ticker (e.g. BAJFINANCE.NS)",
        placeholder="TICKER.NS",
    )
    if custom_ticker:
        selected_tickers.append(custom_ticker.strip().upper())

    pipeline_mode = st.radio(
        "Pipeline Mode",
        options=["sequential", "parallel"],
        index=0,
        help="Sequential: R → A → D | Parallel: (R + A) → D",
    )

    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.caption("GDG Hackfest 2026 · Powered by Gemini 3.0 Flash + ADK")


# ── Main Panel ────────────────────────────────────────────────────────────────
st.title("📈 Stock Market AI Trading Agent")
st.caption("Multi-Agent System · NSE/BSE · Autonomous Research → Analysis → Decision")

if not run_button:
    st.info("Select tickers in the sidebar and click **🚀 Run Analysis** to begin.")
    st.stop()

if not selected_tickers:
    st.error("Please select at least one ticker.")
    st.stop()

# ── Run Pipeline ──────────────────────────────────────────────────────────────
with st.spinner(f"Running {pipeline_mode} pipeline for {len(selected_tickers)} tickers..."):
    try:
        # asyncio.run() works in Streamlit because each click is a fresh script run
        final_state = asyncio.run(run_pipeline(tickers=selected_tickers))
    except Exception as exc:
        st.error(f"Pipeline error: {exc}")
        st.stop()

st.success("Pipeline complete!")

# ── Trade Decisions Table ─────────────────────────────────────────────────────
st.subheader("📊 Trade Decisions")

decisions = extract_decisions_from_state(final_state)
if decisions and "error" not in decisions[0]:
    rows = []
    for d in decisions:
        action = d.get("action", "HOLD").upper()
        colour = get_action_colour(action)
        rows.append({
            "Ticker":      d.get("ticker", ""),
            "Action":      action,
            "Confidence":  d.get("confidence", ""),
            "Target":      d.get("target_price", "N/A"),
            "Stop Loss":   d.get("stop_loss", "N/A"),
            "Risk Flag":   d.get("risk_flag", ""),
            "Rationale":   d.get("rationale", ""),
        })
    df = pd.DataFrame(rows)

    def colour_action(val: str):
        c = get_action_colour(val)
        return f"color: {c}; font-weight: bold;"

    st.dataframe(
        df.style.applymap(colour_action, subset=["Action"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("Could not parse structured decisions. See raw output below.")
    st.text(final_state.get(KEY_TRADE_DECISION, "No decision output."))

# ── Shared Whiteboard Expanders ───────────────────────────────────────────────
st.subheader("🧠 Agent Outputs (Shared Whiteboard)")

col1, col2, col3 = st.columns(3)

with col1:
    with st.expander("🔍 Researcher Output"):
        st.text(final_state.get(KEY_RESEARCH_OUTPUT, "Not yet generated."))

with col2:
    with st.expander("📐 Analyst Signals"):
        st.text(final_state.get(KEY_TECHNICAL_SIGNALS, "Not yet generated."))

with col3:
    with st.expander("✅ DecisionMaker Output"):
        st.text(final_state.get(KEY_TRADE_DECISION, "Not yet generated."))
