"""FastAPI application serving the trading dashboard and ADK agent API."""

from __future__ import annotations

import asyncio
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

# Load environment from root .env (has Vertex AI creds)
_project_root = str(Path(__file__).resolve().parent.parent)
_root_env = Path(_project_root) / ".env"
load_dotenv(_root_env)

# Ensure Vertex AI env var is set for ADK
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")

# Ensure project root is on sys.path
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from google.adk.runners import InMemoryRunner
from google.genai import types

# Import unified pipeline agent
from agents.agent import root_agent, get_market_regime, get_portfolio_status
from agents.pipeline import run_pipeline
from config import WATCH_LIST
from memory.trade_memory import TradeMemory
from scheduler import (
    run_single_scan,
    start_auto_scan,
    stop_auto_scan,
    get_scan_status,
    get_scan_log,
)

app = FastAPI(title="Agentic Trading Assistant", version="2.0.0")

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
    try:
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
    except Exception as exc:
        import traceback
        traceback.print_exc()
        reply = f"Agent error: {type(exc).__name__}: {exc}"
    return ChatResponse(reply=reply)


@app.get("/api/regime")
async def regime():
    """Get current market regime from unified pipeline."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_market_regime)
    return result


# ── Portfolio Endpoints ──────────────────────────────────────────────────────

@app.get("/api/portfolio")
async def portfolio():
    """Get current paper portfolio status."""
    return get_portfolio_status()


@app.get("/api/portfolio/performance")
async def portfolio_performance():
    """Get portfolio memory and win/loss stats."""
    return get_portfolio_status()


@app.post("/api/portfolio/reset")
async def portfolio_reset():
    """Reset paper portfolio (clear all memory)."""
    try:
        memory_path = Path(__file__).parent.parent / "memory"
        (memory_path / "trade_memory.json").write_text("[]")
        (memory_path / "portfolio.json").write_text("{}")
        return {"status": "success", "message": "Portfolio and trade memory reset"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Pipeline Analysis Endpoints ───────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    ticker: str = "RELIANCE.NS"
    portfolio_value: float = 10000.0


@app.post("/api/analyze")
async def analyze_ticker(req: AnalysisRequest):
    """Run full 8-step pipeline analysis on a ticker."""
    loop = asyncio.get_event_loop()
    fn = partial(run_pipeline, ticker=req.ticker, portfolio_value=req.portfolio_value)
    result = await loop.run_in_executor(None, fn)
    return result


@app.get("/api/signals/nifty50")
async def nifty50_signals(limit: int = 10):
    """Scan top Nifty50 stocks with unified pipeline."""
    loop = asyncio.get_event_loop()

    def scan_all():
        results = []
        for ticker in WATCH_LIST[:limit]:
            try:
                r = run_pipeline(ticker=ticker, portfolio_value=100000)
                if r.get("status") == "success":
                    results.append({
                        "ticker": ticker,
                        "regime": r.get("scenario", {}).get("regime", {}).get("trend", "?"),
                        "sentiment": r.get("scenario", {}).get("sentiment", {}).get("bucket", "?"),
                        "scenario": r.get("scenario", {}).get("label", "?"),
                        "strategy": r.get("strategy_selected", "?"),
                        "score": max(
                            (s.get("composite_score", 0) for s in r.get("backtest_scores", [])),
                            default=0
                        ),
                        "trade_status": r.get("trade_status", "?"),
                    })
            except Exception as e:
                results.append({"ticker": ticker, "error": str(e)})
        return {"status": "success", "signals": results}

    return await loop.run_in_executor(None, scan_all)


# ── Scanner / Auto-Scan Endpoints ────────────────────────────────────────────

@app.post("/api/scan")
async def manual_scan(ticker: str = "RELIANCE.NS"):
    """Run a single scan-and-trade cycle (manual trigger)."""
    loop = asyncio.get_event_loop()
    fn = partial(run_single_scan, ticker)
    result = await loop.run_in_executor(None, fn)
    return result


class AutoScanRequest(BaseModel):
    interval_seconds: int = 300


@app.post("/api/scan/start")
async def start_scan(req: AutoScanRequest):
    """Start the background auto-scan loop."""
    return start_auto_scan(interval_seconds=req.interval_seconds)


@app.post("/api/scan/stop")
async def stop_scan():
    """Stop the background auto-scan loop."""
    return stop_auto_scan()


@app.get("/api/scan/status")
async def scan_status():
    """Get current auto-scan status and recent logs."""
    return get_scan_status()


@app.get("/api/scan/log")
async def scan_log(limit: int = 50):
    """Get scan log entries."""
    return get_scan_log(limit=limit)
