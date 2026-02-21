"""Risk rules, thresholds, and NSE-specific defaults."""

GEMINI_MODEL = "gemini-2.5-flash"

# --------------- Risk management ---------------
RISK_PER_TRADE = 0.01          # 1 % of portfolio per trade
MAX_OPEN_TRADES = 3
MIN_REWARD_RISK = 2.0          # minimum R:R ratio
ATR_STOP_MULTIPLIER = 1.5      # stop = entry - 1.5 * ATR
INITIAL_CAPITAL = 1_000_000.0  # INR paper portfolio

# --------------- Regime thresholds ---------------
BULL_RETURN_20D_MIN = 0.0
BEAR_RETURN_20D_MAX = -0.03

# --------------- Default index ---------------
DEFAULT_INDEX = "^NSEI"        # Nifty 50
BANK_INDEX = "^NSEBANK"        # Bank Nifty

# --------------- NSE watchlist (top liquid Nifty 50 stocks) ---------------
NSE_WATCHLIST = [
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

DATA_LOOKBACK_DAYS = 140       # enough for 50-DMA + buffer
