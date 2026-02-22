"""FastAPI application serving the trading dashboard and ADK agent API."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException, Query
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

from google.adk.runners import InMemoryRunner
from google.genai import types

from root_agent.agent import root_agent
from trading_agents.tools.portfolio import get_portfolio_summary, reset_portfolio
from trading_agents.regime_agent import analyze_regime

import math

import numpy as np
import pandas as pd
import yfinance as yf

from quant.data_fetcher import fetch_ohlcv
from quant.indicators import compute_indicators
from quant.regime_classifier import classify_regime

app = FastAPI(title="Agentic Trading Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Serve React production build from frontend/dist/ if it exists
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIR / "assets")), name="frontend-assets")

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
    steps: list[dict] | None = None


class Candle(BaseModel):
    t: str  # ISO8601 timestamp (UTC)
    o: float
    h: float
    l: float
    c: float
    v: float


class MarketResponse(BaseModel):
    ticker: str
    period: str
    interval: str
    timestamp: str
    candles: list[Candle]
    indicators: dict
    regime: str


@app.get("/", response_class=HTMLResponse)
async def index():
    # Serve React frontend if built, otherwise fall back to legacy static page
    frontend_index = _FRONTEND_DIR / "index.html"
    if frontend_index.is_file():
        return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
    html_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = await _get_session_id()
    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=req.message)]
    )

    # Map agent names to pipeline step indices
    _AGENT_STEP_MAP = {
        "QuantToolAgent": 0,
        "QuantAgent": 1,
        "SentimentAgent": 2,
        "BullAgent": 3,
        "BearAgent": 4,
        "CIOAgent": 5,
        "RiskToolAgent": 6,
    }
    _STEP_NAMES = [
        "Quant Engine", "Quant Agent", "Sentiment Agent",
        "Bull Agent", "Bear Agent", "CIO Agent", "Risk Engine",
    ]

    reply_parts: list[str] = []
    step_outputs: dict[int, str] = {}  # step_index -> collected text

    async for event in _runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=user_content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and part.text.strip():
                    text = part.text.strip()
                    reply_parts.append(text)

                    # Track which agent produced this text
                    author = getattr(event, "author", None) or ""
                    if author in _AGENT_STEP_MAP:
                        idx = _AGENT_STEP_MAP[author]
                        step_outputs[idx] = step_outputs.get(idx, "") + "\n" + text

    reply = "\n\n".join(reply_parts) if reply_parts else "No response from agent."

    # Build structured step data for the frontend
    steps = []
    for i, name in enumerate(_STEP_NAMES):
        output_text = step_outputs.get(i, "")
        has_output = bool(output_text.strip())

        # Determine summary from the output
        summary = None
        if has_output:
            lines = [l.strip() for l in output_text.strip().split("\n") if l.strip()]
            # Pick the first meaningful summary line
            for line in lines[:5]:
                if len(line) > 10 and not line.startswith("="):
                    summary = line[:120]
                    break
            if not summary and lines:
                summary = lines[0][:120]

        # Check for flagged state (Risk Engine rejection)
        is_flagged = (
            i == 6 and has_output and
            any(kw in output_text.upper() for kw in ["REJECTED", "KILLED"])
        )

        steps.append({
            "name": name,
            "status": "flagged" if is_flagged else ("complete" if has_output else "pending"),
            "summary": summary,
            "output": output_text.strip() if has_output else None,
        })

    return ChatResponse(reply=reply, steps=steps)


@app.get("/api/regime")
async def regime():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, analyze_regime)
    return result


@app.get("/api/portfolio")
async def portfolio():
    return get_portfolio_summary()


@app.post("/api/portfolio/reset")
async def portfolio_reset():
    return reset_portfolio()


@app.get("/api/market", response_model=MarketResponse)
async def market(
    ticker: str = Query(..., min_length=1),
    period: str = Query("6mo"),
    interval: Literal["1d", "1h", "30m", "15m"] = Query("1d"),
    limit: int = Query(180, ge=50, le=400),
):
    """Return lightweight OHLCV + indicators for charting.

    This is intentionally small and UI-friendly (no DataFrames).
    """
    loop = asyncio.get_running_loop()

    def _work() -> dict:  # noqa: PLR0912
        # ── 1. Normalise ticker (replicate _normalise_ticker logic) ────────────
        t = ticker.strip().upper()
        if not t.startswith("^") and "." not in t:
            t = f"{t}.NS"

        # ── 2. Download via yfinance directly (no MIN_ROWS restriction) ────────
        try:
            raw: pd.DataFrame = yf.download(
                tickers=t,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
            )
        except Exception as exc:
            raise RuntimeError(f"[{t}] yfinance download failed: {exc}") from exc

        if raw is None or raw.empty:
            raise ValueError(
                f"[{t}] No data returned by Yahoo Finance. "
                "Verify the ticker symbol and try a longer period."
            )

        # Flatten MultiIndex columns produced by yfinance ≥ 0.2.50
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw.columns = [str(c).strip().lower() for c in raw.columns]

        required = ["open", "high", "low", "close", "volume"]
        missing = set(required) - set(raw.columns)
        if missing:
            raise ValueError(f"[{t}] Missing columns: {sorted(missing)}")

        df = raw[required].dropna().sort_index()
        n = len(df)
        if n < 2:
            raise ValueError(f"[{t}] Too few rows ({n}) to build a chart.")

        # ── 3. Inline indicator helpers ────────────────────────────────────────
        closes = df["close"].to_numpy(dtype=float)
        highs  = df["high"].to_numpy(dtype=float)
        lows   = df["low"].to_numpy(dtype=float)

        def _sma(arr: np.ndarray, p: int) -> float:
            return float(arr[-p:].mean()) if len(arr) >= p else float(arr.mean())

        def _ema(arr: np.ndarray, p: int) -> float:
            s = pd.Series(arr)
            return float(s.ewm(span=p, adjust=False).mean().iloc[-1])

        def _rsi(arr: np.ndarray, p: int = 14) -> float:
            if len(arr) < p + 1:
                return 50.0
            delta = np.diff(arr)
            gain = np.where(delta > 0, delta, 0.0)
            loss = np.where(delta < 0, -delta, 0.0)
            avg_gain = gain[-p:].mean()
            avg_loss = loss[-p:].mean()
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return float(100.0 - (100.0 / (1.0 + rs)))

        def _atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, p: int = 14) -> float:
            if len(c) < p + 1:
                return float((h - l).mean())
            tr = np.maximum(
                h[1:] - l[1:],
                np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1]))
            )
            return float(tr[-p:].mean())

        price     = float(closes[-1])
        sma20     = _sma(closes, 20)
        sma50     = _sma(closes, 50)
        sma200    = _sma(closes, 200)
        ema20     = _ema(closes, 20)
        ema50     = _ema(closes, 50)
        rsi_val   = _rsi(closes)
        atr_val   = _atr(highs, lows, closes)

        returns   = np.diff(closes) / np.where(closes[:-1] != 0, closes[:-1], 1.0)
        vol_win   = min(20, len(returns))
        volatility = float(returns[-vol_win:].std() * math.sqrt(252)) if vol_win >= 2 else 0.0

        mom_win   = min(20, n - 1)
        momentum_20d = float((closes[-1] - closes[-(mom_win + 1)]) / closes[-(mom_win + 1)]) if mom_win > 0 else 0.0

        trend_strength = float(
            (1 if closes[-1] > sma50 else -1) +
            (0.5 if sma50 > sma200 else -0.5)
        )

        # ── 4. Regime ──────────────────────────────────────────────────────────
        if closes[-1] > sma50 > sma200 and trend_strength > 0:
            regime_str = "BULL"
        elif closes[-1] < sma50 < sma200 and trend_strength < 0:
            regime_str = "BEAR"
        else:
            regime_str = "NEUTRAL"

        # ── 5. Build candles list ──────────────────────────────────────────────
        chart_df = df.tail(limit)
        candles: list[dict] = []
        for idx, row in chart_df.iterrows():
            ts = idx
            try:
                ts = ts.tz_convert("UTC")
            except Exception:
                pass
            candles.append(
                {
                    "t": ts.isoformat().replace("+00:00", "Z"),
                    "o": float(row["open"]),
                    "h": float(row["high"]),
                    "l": float(row["low"]),
                    "c": float(row["close"]),
                    "v": float(row["volume"]),
                }
            )

        last_ts = df.index[-1]
        try:
            last_ts = last_ts.tz_convert("UTC")
        except Exception:
            pass
        ts_iso = pd.Timestamp(last_ts).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "ticker": t,
            "period": period,
            "interval": interval,
            "timestamp": ts_iso,
            "candles": candles,
            "indicators": {
                "price": price,
                "rsi": rsi_val,
                "atr": atr_val,
                "sma20": sma20,
                "sma50": sma50,
                "sma200": sma200,
                "ema20": ema20,
                "ema50": ema50,
                "volatility": volatility,
                "momentum_20d": momentum_20d,
                "trend_strength": trend_strength,
            },
            "regime": regime_str,
        }

    try:
        result = await loop.run_in_executor(None, _work)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


# ── SPA catch-all: serve React index.html for non-API routes ──────────────
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Catch-all route to support React SPA client-side routing.
    Also serves static assets from the frontend dist folder (e.g. vite.svg).
    """
    # First check if the path maps to a real file in frontend/dist
    if full_path:
        candidate = (_FRONTEND_DIR / full_path).resolve()
        # Prevent path traversal
        if str(candidate).startswith(str(_FRONTEND_DIR.resolve())) and candidate.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(str(candidate))

    # Otherwise serve the SPA index.html
    frontend_index = _FRONTEND_DIR / "index.html"
    if frontend_index.is_file():
        return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Not found")
