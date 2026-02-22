"""FastAPI application serving the trading dashboard and ADK agent API."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from functools import partial
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load environment from trading_agents/.env
_env_path = Path(__file__).resolve().parent.parent / "trading_agents" / ".env"
load_dotenv(_env_path)

# Ensure project root is on sys.path so trading_agents is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from trading_agents.agent import root_agent
from trading_agents.scanner_agent import get_nifty50_signal_board
from trading_agents.tools.portfolio import (
    get_portfolio_performance,
    get_portfolio_summary,
    refresh_portfolio_positions,
    reset_portfolio,
)
from trading_agents.regime_agent import analyze_regime

app = FastAPI(title="Trade Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ADK runner and session
_runner = InMemoryRunner(agent=root_agent, app_name="trading_assistant")
_USER_ID = "dashboard_user"
_session_id: str | None = None


async def _get_session_id() -> str:
    global _session_id
    if _session_id is None:
        session = await _runner.session_service.create_session(
            app_name="trading_assistant", user_id=_USER_ID
        )
        _session_id = session.id
    return _session_id


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = await _get_session_id()
    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=req.message)]
    )

    reply_parts: list[str] = []
    async for event in _runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=user_content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and part.text.strip():
                    reply_parts.append(part.text.strip())

    reply = "\n\n".join(reply_parts) if reply_parts else "No response from agent."
    return ChatResponse(reply=reply)


@app.get("/api/regime")
async def regime():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyze_regime)
    return result


@app.get("/api/portfolio")
async def portfolio():
    return get_portfolio_summary()


@app.get("/api/portfolio/performance")
async def portfolio_performance():
    return get_portfolio_performance()


@app.post("/api/portfolio/refresh")
async def portfolio_refresh():
    return refresh_portfolio_positions()


@app.post("/api/portfolio/reset")
async def portfolio_reset():
    return reset_portfolio()


@app.get("/api/backtest/oversold-summary")
async def backtest_oversold_summary(max_stocks: int = 10):
    """Run oversold bounce backtest on first Nifty 50 stocks; return summary with P&L for dashboard."""
    from trading_agents.tools.backtest_oversold import backtest_oversold_nifty50
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: backtest_oversold_nifty50(years=2, max_stocks=max_stocks, use_portfolio_sizing=True),
    )


@app.get("/api/backtest/oversold-best")
async def backtest_oversold_best(top_n: int | None = None):
    """Run oversold backtest on full Nifty 50, return only stocks that pass (win>=50%, >=3 trades). top_n: limit to top N (e.g. 5)."""
    from trading_agents.tools.backtest_oversold import get_best_oversold_nifty50
    loop = asyncio.get_event_loop()
    def _run():
        out = get_best_oversold_nifty50(years=2, min_win_rate_pct=50, min_trades=3)
        if out.get("status") != "success":
            return out
        best = out.get("best_stocks", [])
        if top_n is not None and top_n > 0:
            best = best[:top_n]
            out["best_stocks"] = best
        out["total_best_pnl_inr"] = round(sum(s.get("pnl_inr", 0) or 0 for s in best), 2)
        return out
    return await loop.run_in_executor(None, _run)


@app.get("/api/dividend/top")
async def dividend_top():
    """Fetch top dividend opportunities (Moneycontrol + scan) for dashboard."""
    from trading_agents.dividend_agent import scan_dividend_opportunities
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: scan_dividend_opportunities(min_days_to_ex=1))


@app.get("/api/market")
async def market(
    ticker: str = "^NSEI",
    period: str = "6mo",
    interval: str = "1d",
    limit: int = 500,
):
    """OHLCV + indicators for market chart. Ticker: symbol (e.g. RELIANCE, ^NSEI). Period: 1d,5d,1mo,3mo,6mo,1y,2y. Interval: 1d,1wk."""
    import yfinance as yf
    loop = asyncio.get_event_loop()

    def _run():
        sym = ticker.strip().upper()
        if not sym.startswith("^") and not sym.endswith(".NS"):
            sym = sym + ".NS"
        t = yf.Ticker(sym)
        hist = t.history(period=period, interval=interval)
        if hist is None or len(hist) == 0:
            return {"status": "error", "error_message": f"No data for {ticker}"}
        hist = hist.tail(limit)
        if len(hist) < 2:
            return {"status": "error", "error_message": "Insufficient bars"}
        closes = hist["Close"].ffill().tolist()
        highs = hist["High"].fillna(hist["Close"]).tolist()
        lows = hist["Low"].fillna(hist["Close"]).tolist()
        opens = hist["Open"].fillna(hist["Close"]).tolist()
        volumes = hist["Volume"].fillna(0).astype(int).tolist()
        dates = [d.isoformat()[:10] for d in hist.index]

        def sma(series, n):
            out = [None] * len(series)
            for i in range(n - 1, len(series)):
                out[i] = round(sum(series[i - n + 1 : i + 1]) / n, 2)
            return out

        def rsi_series(series, period=14):
            out = [None] * len(series)
            for i in range(period, len(series)):
                gains, losses = 0.0, 0.0
                for j in range(i - period + 1, i + 1):
                    ch = series[j] - series[j - 1]
                    if ch > 0:
                        gains += ch
                    else:
                        losses -= ch
                avg_gain = gains / period
                avg_loss = losses / period
                if avg_loss == 0:
                    out[i] = 100.0
                else:
                    rs = avg_gain / avg_loss
                    out[i] = round(100 - (100 / (1 + rs)), 2)
            return out

        sma20 = sma(closes, 20)
        sma50 = sma(closes, 50)
        sma200 = sma(closes, 200) if len(closes) >= 200 else [None] * len(closes)
        rsi = rsi_series(closes, 14)

        candles = []
        for i in range(len(dates)):
            candles.append({
                "date": dates[i],
                "open": round(float(opens[i]), 2),
                "high": round(float(highs[i]), 2),
                "low": round(float(lows[i]), 2),
                "close": round(float(closes[i]), 2),
                "volume": int(volumes[i]) if volumes[i] == volumes[i] else 0,
                "sma20": sma20[i],
                "sma50": sma50[i],
                "sma200": sma200[i],
                "rsi": rsi[i],
            })
        return {
            "status": "success",
            "ticker": sym,
            "candles": candles,
            "period": period,
            "interval": interval,
        }

    return await loop.run_in_executor(None, _run)


@app.get("/api/signals/nifty50")
async def nifty50_signals(
    limit: int = 50,
    include_news: bool = True,
    max_news: int = 2,
    news_days: int = 1,
):
    loop = asyncio.get_event_loop()
    fn = partial(
        get_nifty50_signal_board,
        limit,
        include_news,
        max_news,
        news_days,
    )
    return await loop.run_in_executor(None, fn)
