"""
tools/market_tools.py – Technical Indicator Tools
===================================================
Each function in this file is an ADK-compatible tool that can be passed
directly to LlmAgent(..., tools=[get_price_data, get_rsi, ...]).

The ADK automatically generates a schema from the docstring and type hints.
The Analyst agent will call these functions autonomously during reasoning.

ADD NEW TOOLS HERE by defining a plain Python function with:
    - Full type hints
    - A clear one-line docstring (the model reads this to decide when to call it)
"""

import pandas as pd
import numpy as np
import yfinance as yf

from config import DEFAULT_PERIOD, DEFAULT_INTERVAL


# ── Price Data ────────────────────────────────────────────────────────────────

def get_price_data(ticker: str) -> dict:
    """
    Fetch recent OHLCV price history for a given stock ticker.

    Args:
        ticker: The ticker symbol (e.g., 'RELIANCE.NS', 'TCS.NS').

    Returns:
        A dictionary with 'ticker', 'period', 'latest_close', 'rows',
        and 'error' key if the fetch fails.
    """
    try:
        data: pd.DataFrame = yf.download(
            ticker,
            period=DEFAULT_PERIOD,
            interval=DEFAULT_INTERVAL,
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return {"ticker": ticker, "error": "No data returned from yfinance."}

        latest_close = round(float(data["Close"].iloc[-1]), 2)
        return {
            "ticker": ticker,
            "period": DEFAULT_PERIOD,
            "interval": DEFAULT_INTERVAL,
            "latest_close": latest_close,
            "rows": len(data),
            "columns": list(data.columns),
            # Pass the serialisable summary; full DataFrame stays in-process.
            "recent_closes": data["Close"].tail(10).round(2).tolist(),
        }
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}


# ── RSI ───────────────────────────────────────────────────────────────────────

def get_rsi(ticker: str, period: int = 14) -> dict:
    """
    Calculate the Relative Strength Index (RSI) for a stock.

    Args:
        ticker: The stock ticker symbol (e.g., 'INFY.NS').
        period: The RSI lookback period (default 14).

    Returns:
        A dict with 'ticker', 'rsi', and an 'interpretation' string.
    """
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if data.empty or len(data) < period + 1:
            return {"ticker": ticker, "error": "Insufficient data for RSI."}

        close = data["Close"].squeeze()
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss
        rsi   = round(float(100 - (100 / (1 + rs.iloc[-1]))), 2)

        interpretation = (
            "Overbought" if rsi > 70 else
            "Oversold"   if rsi < 30 else
            "Neutral"
        )
        return {"ticker": ticker, "rsi": rsi, "interpretation": interpretation}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}


# ── MACD ──────────────────────────────────────────────────────────────────────

def get_macd(ticker: str, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    Calculate the MACD indicator for a stock.

    Args:
        ticker: The stock ticker symbol.
        fast:   Fast EMA period (default 12).
        slow:   Slow EMA period (default 26).
        signal: Signal line EMA period (default 9).

    Returns:
        A dict with 'macd_line', 'signal_line', 'histogram', and 'crossover'.
    """
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if data.empty or len(data) < slow + signal:
            return {"ticker": ticker, "error": "Insufficient data for MACD."}

        close       = data["Close"].squeeze()
        ema_fast    = close.ewm(span=fast, adjust=False).mean()
        ema_slow    = close.ewm(span=slow, adjust=False).mean()
        macd_line   = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram   = macd_line - signal_line

        crossover = "BULLISH" if macd_line.iloc[-1] > signal_line.iloc[-1] else "BEARISH"

        return {
            "ticker":      ticker,
            "macd_line":   round(float(macd_line.iloc[-1]),   4),
            "signal_line": round(float(signal_line.iloc[-1]), 4),
            "histogram":   round(float(histogram.iloc[-1]),   4),
            "crossover":   crossover,
        }
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}


# ── Moving Averages ───────────────────────────────────────────────────────────

def get_moving_averages(ticker: str) -> dict:
    """
    Calculate 20-day and 50-day Simple Moving Averages for a stock.

    Args:
        ticker: The stock ticker symbol.

    Returns:
        A dict with 'sma_20', 'sma_50', 'current_price', and 'trend'.
    """
    try:
        data = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if data.empty or len(data) < 50:
            return {"ticker": ticker, "error": "Insufficient data for moving averages."}

        close         = data["Close"].squeeze()
        current_price = round(float(close.iloc[-1]), 2)
        sma_20        = round(float(close.rolling(20).mean().iloc[-1]), 2)
        sma_50        = round(float(close.rolling(50).mean().iloc[-1]), 2)

        if current_price > sma_20 > sma_50:
            trend = "UPTREND"
        elif current_price < sma_20 < sma_50:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        return {
            "ticker":        ticker,
            "current_price": current_price,
            "sma_20":        sma_20,
            "sma_50":        sma_50,
            "trend":         trend,
        }
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}


# ── TODO: Portfolio Exposure ───────────────────────────────────────────────────
# def check_portfolio_exposure(ticker: str) -> dict:
#     """Check current portfolio allocation for a ticker to enforce position limits."""
#     raise NotImplementedError("Wire up your portfolio store here.")
