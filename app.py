"""
app.py – Streamlit Dashboard: Regime-Aware Trading Command Center
===================================================================
Run with:
    streamlit run app.py

This UI:
    - Selects a single ticker from the WATCH_LIST (or custom input)
    - Triggers the 6-step Regime-Aware pipeline
    - Shows real-time observability trace (st.status) of agents debating
    - Renders interactive Plotly charts (price + regime overlay)
    - Displays the final CIO advisory + risk-validated trade card
    - The system ONLY advises; the human executes.
"""

import asyncio
import streamlit as st
import pandas as pd

from config import (
    WATCH_LIST,
    DEFAULT_PORTFOLIO_EQUITY,
    KEY_QUANT_SNAPSHOT,
    KEY_SENTIMENT,
    KEY_BULL_THESIS,
    KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
    KEY_FINAL_TRADE,
)
from main import run_pipeline
from utils.helpers import format_currency_inr, get_action_colour


# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Regime-Aware Trading Command Center",
    page_icon="🎯",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    selected_ticker = st.selectbox(
        "Select Ticker to Analyse",
        options=WATCH_LIST,
        index=0,
    )

    custom_ticker = st.text_input(
        "Or enter a Custom Ticker (e.g. BAJFINANCE.NS)",
        placeholder="TICKER.NS",
    )
    if custom_ticker:
        selected_ticker = custom_ticker.strip().upper()

    portfolio_equity = st.number_input(
        "Portfolio Equity (₹)",
        min_value=10_000.0,
        value=DEFAULT_PORTFOLIO_EQUITY,
        step=100_000.0,
        format="%.0f",
    )

    run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.caption("GDG Hackfest 2026 · Regime-Aware Trading Command Center")
    st.caption("Powered by Gemini 3 Flash Preview + Google ADK")


# ── Main Panel ────────────────────────────────────────────────────────────────
st.title("🎯 Regime-Aware Trading Command Center")
st.caption("Hybrid Quant-Agent Architecture · Bull vs Bear Debate · Risk-Enforced Advisory")

if not run_button:
    st.info("Select a ticker in the sidebar and click **🚀 Run Analysis** to begin.")
    st.stop()

if not selected_ticker:
    st.error("Please select or enter a ticker.")
    st.stop()

# ── Run Pipeline with Observability Trace ─────────────────────────────────────
with st.status(f"Running 6-step pipeline for {selected_ticker}...", expanded=True) as status:
    try:
        st.write("**Step 1:** Quant Engine — fetching OHLCV, computing indicators, classifying regime...")
        final_state = asyncio.run(
            run_pipeline(ticker=selected_ticker, portfolio_equity=portfolio_equity)
        )
        # TODO: Add per-step st.write() calls inside the Orchestrator
        # for real-time observability of each agent step.
        status.update(label="Pipeline complete!", state="complete", expanded=False)
    except Exception as exc:
        status.update(label="Pipeline failed!", state="error")
        st.error(f"Pipeline error: {exc}")
        st.stop()

# ── Regime & Quant Snapshot ───────────────────────────────────────────────────
st.subheader("📊 Quant Snapshot & Regime")
quant_data = final_state.get(KEY_QUANT_SNAPSHOT)
if quant_data and isinstance(quant_data, dict):
    regime = quant_data.get("regime", "UNKNOWN")
    regime_colour = {"BULL": "🟢", "BEAR": "🔴", "NEUTRAL": "🟡"}.get(regime, "⚪")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Regime", f"{regime_colour} {regime}")
    col2.metric("Close", format_currency_inr(quant_data.get("latest_close", 0)))
    col3.metric("50 DMA", format_currency_inr(quant_data.get("dma_50", 0)))
    col4.metric("ATR", f"{quant_data.get('atr', 0):.2f}")
else:
    st.warning("Quant snapshot not available.")

# ── TODO: Interactive Plotly Chart (Price + Regime Overlay) ────────────────────
# st.subheader("📈 Price Chart with Regime Overlay")
# TODO: Implement Plotly chart showing OHLCV candles + 50DMA/200DMA lines
# + coloured regime bands (green=BULL, red=BEAR, yellow=NEUTRAL)

# ── Agent Debate (Observability) ──────────────────────────────────────────────
st.subheader("🧠 Agent Debate (Shared Whiteboard)")

col1, col2 = st.columns(2)

with col1:
    with st.expander("📰 Sentiment Agent Output", expanded=False):
        st.text(final_state.get(KEY_SENTIMENT, "Not yet generated."))

    with st.expander("🐂 Bull Agent Thesis", expanded=True):
        st.text(final_state.get(KEY_BULL_THESIS, "Not yet generated."))

with col2:
    with st.expander("🐻 Bear Agent Thesis", expanded=True):
        st.text(final_state.get(KEY_BEAR_THESIS, "Not yet generated."))

    with st.expander("👔 CIO Raw Proposal", expanded=False):
        st.text(final_state.get(KEY_CIO_PROPOSAL, "Not yet generated."))

# ── Final Risk-Validated Trade Card ───────────────────────────────────────────
st.subheader("✅ Final Trade Advisory (Risk-Validated)")
final_trade = final_state.get(KEY_FINAL_TRADE)

if final_trade and isinstance(final_trade, dict) and not final_trade.get("killed"):
    action = final_trade.get("action", "HOLD")
    colour = get_action_colour(action)

    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.metric("Action", action)
    tc2.metric("Entry", format_currency_inr(final_trade.get("entry_price", 0)))
    tc3.metric("Stop Loss", format_currency_inr(final_trade.get("stop_loss", 0)))
    tc4.metric("Target", format_currency_inr(final_trade.get("target_price", 0)))

    tc5, tc6, tc7, tc8 = st.columns(4)
    tc5.metric("Position Size", f"{final_trade.get('position_size', 0)} shares")
    tc6.metric("Total Risk", format_currency_inr(final_trade.get("total_risk", 0)))
    tc7.metric("Risk/Reward", f"1:{final_trade.get('risk_reward_ratio', 0):.2f}")
    tc8.metric("Regime", final_trade.get("regime", "N/A"))

    st.info("⚠️ This is an ADVISORY ONLY. The human executes the trade.")

elif final_trade and final_trade.get("killed"):
    st.error(f"⛔ **Trade Killed by Risk Engine:** {final_trade.get('kill_reason', 'Risk limits breached.')}")
else:
    st.warning("No trade proposal generated for this ticker.")
