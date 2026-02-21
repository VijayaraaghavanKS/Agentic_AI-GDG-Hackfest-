"""
config.py – Central configuration for the Regime-Aware Trading Command Center.

All modules import from here.

Design Principles:
• Single source of truth
• Deterministic risk parameters
• Environment-driven configuration
• Hackathon-safe defaults
• Vertex AI only (no API keys)

LLM NEVER touches risk parameters.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────
# Load Environment Variables
# ──────────────────────────────────────────────────────────────

load_dotenv()

# ──────────────────────────────────────────────────────────────
# Vertex AI Configuration
# ──────────────────────────────────────────────────────────────

# Force Vertex AI routing
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

GEMINI_MODEL: str = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION: str = os.getenv(
    "GOOGLE_CLOUD_LOCATION",
    "us-central1"
)

if not GOOGLE_CLOUD_PROJECT:
    raise EnvironmentError(
        "GOOGLE_CLOUD_PROJECT not set in .env"
    )

# Optional fallback models
GEMINI_FALLBACK_MODELS: list[str] = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]

# ──────────────────────────────────────────────────────────────
# System Identity
# ──────────────────────────────────────────────────────────────

CONFIG_NAME: str = "GDG Hackfest Trading System"

HACKATHON_MODE: bool = True

# ──────────────────────────────────────────────────────────────
# Feature Flags
# ──────────────────────────────────────────────────────────────

ENABLE_BATCH_FETCH: bool = True
ENABLE_QUANT_AGENT: bool = True
ENABLE_SENTIMENT_AGENT: bool = True
ENABLE_RISK_ENGINE: bool = True

# ──────────────────────────────────────────────────────────────
# Market Configuration
# ──────────────────────────────────────────────────────────────

WATCH_LIST: list[str] = [

    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",

    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS",

    "LT.NS",
    "AXISBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "TITAN.NS",

    "SUNPHARMA.NS",
    "BAJFINANCE.NS",
    "WIPRO.NS",
    "HCLTECH.NS",
    "TATAMOTORS.NS",

]

TARGET_EXCHANGE: str = "NSE"

# ──────────────────────────────────────────────────────────────
# Data Defaults
# ──────────────────────────────────────────────────────────────

DEFAULT_PERIOD: str = "1y"
DEFAULT_INTERVAL: str = "1d"

INTRADAY_PERIOD: str = "30d"
INTRADAY_INTERVAL: str = "15m"

DATA_LOOKBACK_DAYS: int = 140

# ──────────────────────────────────────────────────────────────
# Index Defaults
# ──────────────────────────────────────────────────────────────

DEFAULT_INDEX: str = "^NSEI"
BANK_INDEX: str = "^NSEBANK"

# ──────────────────────────────────────────────────────────────
# Regime Thresholds
# ──────────────────────────────────────────────────────────────

BULL_RETURN_20D_MIN: float = 0.0
BEAR_RETURN_20D_MAX: float = -0.03

# ──────────────────────────────────────────────────────────────
# Risk Engine Parameters
# ──────────────────────────────────────────────────────────────

MAX_RISK_PCT: float = 0.01

ATR_STOP_MULTIPLIER: float = 1.5

MIN_RISK_REWARD: float = 2.0

DEFAULT_PORTFOLIO_EQUITY: float = 1_000_000.0

MAX_OPEN_TRADES: int = 3

DAILY_LOSS_LIMIT_PCT: float = 0.03

# ──────────────────────────────────────────────────────────────
# Runtime Settings
# ──────────────────────────────────────────────────────────────

SESSION_TIMEOUT_SECONDS: int = 600

AGENT_TEMPERATURE: float = 0.2

MAX_OUTPUT_TOKENS: int = 2048

# ──────────────────────────────────────────────────────────────
# Session State Keys
# ──────────────────────────────────────────────────────────────

from pipeline.session_keys import (  # noqa: E402

    KEY_MARKET_CONTEXT,
    KEY_QUANT_SNAPSHOT,
    KEY_QUANT_ANALYSIS,
    KEY_SENTIMENT,
    KEY_BULL_THESIS,
    KEY_BEAR_THESIS,
    KEY_CIO_PROPOSAL,
    KEY_FINAL_TRADE,
    KEY_USER_EQUITY,

)