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

# Load environment from root .env (has Vertex AI creds)
_project_root = str(Path(__file__).resolve().parent.parent)
_root_env = Path(_project_root) / ".env"
load_dotenv(_root_env)

# Also try trading_agents/.env as fallback
_ta_env = Path(_project_root) / "trading_agents" / ".env"
if _ta_env.exists():
    load_dotenv(_ta_env, override=False)

# Ensure Vertex AI env var is set for ADK
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")

# Ensure project root is on sys.path so trading_agents is importable
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
from scheduler import (
    run_single_scan,
    start_auto_scan,
    stop_auto_scan,
    get_scan_status,
    get_scan_log,
)

app = FastAPI(title="Agentic Trading Assistant", version="1.0.0")

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
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, analyze_regime)
    return result


# ── Portfolio Endpoints ──────────────────────────────────────────────────────

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


# ── Nifty 50 Signal Board ───────────────────────────────────────────────────

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


# ── Scanner / Auto-Scan Endpoints ────────────────────────────────────────────

@app.post("/api/scan")
async def manual_scan():
    """Run a single scan-and-trade cycle (manual trigger)."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_single_scan)
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
