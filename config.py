"""
config.py – Central configuration for the Stock Market AI Trading Agent.

All team members import from here. Edit WATCH_LIST and TARGET_EXCHANGE
to suit the current hackathon stock picks.
"""

import os
from dotenv import load_dotenv

# ── Load variables from .env ───────────────────────────────────────────────────
load_dotenv()

# ── Model Settings ─────────────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.0-flash")

# ── API Keys ───────────────────────────────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY is not set. "
        "Copy .env.example → .env and add your key."
    )

# ── Market Configuration ───────────────────────────────────────────────────────
# Add/remove tickers here without touching agent code.
WATCH_LIST: list[str] = [
    "RELIANCE.NS",   # NSE – Reliance Industries
    "TCS.NS",        # NSE – Tata Consultancy Services
    "INFY.NS",       # NSE – Infosys
    "HDFCBANK.NS",   # NSE – HDFC Bank
    "WIPRO.NS",      # NSE – Wipro
]

TARGET_EXCHANGE: str = "NSE"   # Options: "NSE", "BSE", "NASDAQ"
DEFAULT_PERIOD: str  = "6mo"   # yfinance period (1d, 5d, 1mo, 3mo, 6mo, 1y)
DEFAULT_INTERVAL: str = "1d"   # yfinance interval (1m, 5m, 15m, 1h, 1d)

# ── Session State Keys (Shared Whiteboard) ─────────────────────────────────────
# Using constants avoids typos when agents read/write session.state.
KEY_RESEARCH_OUTPUT:     str = "research_output"       # Researcher → Analyst
KEY_TECHNICAL_SIGNALS:   str = "technical_signals"     # Analyst → DecisionMaker
KEY_TRADE_DECISION:      str = "trade_decision"        # DecisionMaker → UI / main

# ── Pipeline Mode ──────────────────────────────────────────────────────────────
# Toggle between "sequential" and "parallel" from a single flag.
PIPELINE_MODE: str = "sequential"   # or "parallel"

# ── Agent Generation Settings ──────────────────────────────────────────────────
AGENT_TEMPERATURE: float = 0.2      # Lower = more deterministic trading logic
MAX_OUTPUT_TOKENS: int   = 2048
