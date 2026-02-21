"""
config.py – Central configuration for the Regime-Aware Trading Command Center.

All team members import from here. Edit WATCH_LIST and TARGET_EXCHANGE
to suit the current hackathon stock picks. Risk parameters are defined
here — the LLM never touches these numbers.
"""

import os
from dotenv import load_dotenv

# ── Load variables from .env ───────────────────────────────────────────────────
load_dotenv()

# ── Model Settings ─────────────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

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
DEFAULT_PERIOD: str  = "1y"    # yfinance period – 1y needed for 200DMA
DEFAULT_INTERVAL: str = "1d"   # yfinance interval (1m, 5m, 15m, 1h, 1d)

# ── Risk Parameters (Deterministic – LLM NEVER touches these) ─────────────────
MAX_RISK_PCT: float        = 0.01    # 1% of portfolio equity per trade
ATR_STOP_MULTIPLIER: float = 1.5     # Stop-loss = Entry − (1.5 × ATR)
MIN_RISK_REWARD: float     = 1.5     # Minimum R:R ratio to allow a trade
DEFAULT_PORTFOLIO_EQUITY: float = 1_000_000.0  # ₹10L default for sizing

# ── Session State Keys (re-exported from pipeline.session_keys) ────────────────
# Import from pipeline.session_keys for the canonical key constants.
from pipeline.session_keys import (  # noqa: E402
    KEY_QUANT_SNAPSHOT,
    KEY_SENTIMENT,
    KEY_BULL_THESIS,
    KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
    KEY_FINAL_TRADE,
)

# ── Agent Generation Settings ──────────────────────────────────────────────────
AGENT_TEMPERATURE: float = 0.2      # Lower = more deterministic trading logic
MAX_OUTPUT_TOKENS: int   = 2048
