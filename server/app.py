"""FastAPI application serving the trading dashboard and ADK agent API."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from functools import partial
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

from trading_agents.agent import root_agent
from trading_agents.scanner_agent import get_nifty50_signal_board, get_stock_analysis
from trading_agents.tools.portfolio import (
    get_portfolio_performance,
    get_portfolio_summary,
    refresh_portfolio_positions,
    reset_portfolio,
)
from trading_agents.regime_agent import analyze_regime
from trading_agents.trade_agent import check_risk

app = FastAPI(title="Trade Copilot", version="1.0.0")

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
    # Serve other static files (vite.svg, etc.) from dist root
    _vite_svg = _FRONTEND_DIR / "vite.svg"
    if _vite_svg.is_file():
        @app.get("/vite.svg")
        async def vite_svg():
            from fastapi.responses import FileResponse
            return FileResponse(str(_vite_svg), media_type="image/svg+xml")

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
    fresh_session: bool = False


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


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


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
    global _session_id
    # Fresh session for Analyze page — avoids stale context from prior chats
    if req.fresh_session:
        _session_id = None
    try:
        session_id = await _get_session_id()
    except Exception:
        # Session may be stale — reset and retry
        _session_id = None
        session_id = await _get_session_id()

    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=req.message)]
    )

    # Map agent names to pipeline step indices
    # Active agents: root_agent (trading_assistant) delegates to these sub-agents
    _AGENT_STEP_MAP = {
        "regime_analyst": 0,
        "stock_scanner": 1,
        "dividend_scanner": 2,
        "trade_debate_judge": 3,
        "bull_advocate": 3,      # sub-agent of debate, maps to same step
        "bear_advocate": 3,      # sub-agent of debate, maps to same step
        "trade_executor": 4,
        "portfolio_manager": 5,
        "trading_assistant": 6,  # root agent's own tool calls (autonomous flow)
    }
    _STEP_NAMES = [
        "Regime Analyst", "Stock Scanner", "Dividend Scanner",
        "Debate (Bull vs Bear)", "Trade Executor", "Portfolio Manager", "Autonomous Flow",
    ]

    reply_parts: list[str] = []
    step_outputs: dict[int, str] = {}  # step_index -> collected text

    try:
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
    except Exception as exc:
        import logging
        logging.getLogger("server").exception("ADK runner error: %s", exc)
        if not reply_parts:
            reply_parts.append(f"Agent encountered an error: {exc}")

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

        # Check for flagged state (Risk Engine rejection) on Trade Executor step
        is_flagged = (
            i == 4 and has_output and
            any(kw in output_text.upper() for kw in ["REJECTED", "KILLED"])
        )

        steps.append({
            "name": name,
            "status": "flagged" if is_flagged else ("complete" if has_output else "pending"),
            "summary": summary,
            "output": output_text.strip() if has_output else None,
        })

    return ChatResponse(reply=reply, steps=steps)


# ── Server-side orchestrated full analysis ─────────────────────────────────
# Instead of relying on the LLM to delegate to 5 sub-agents in one turn
# (which it often short-circuits), we orchestrate each step programmatically.
# Steps 1 (regime), 2 (scan), 5 (portfolio) are direct function calls.
# Steps 3 (debate) and 4 (trade plan) use the ADK agent with focused prompts.

class AnalyzeRequest(BaseModel):
    ticker: str = "RELIANCE"


class AnalyzeResponse(BaseModel):
    reply: str
    trade: dict | None = None
    steps: list[dict]
    debate: dict | None = None


async def _run_agent_turn(session_id: str, message: str) -> tuple[str, dict[int, str]]:
    """Send a single message to the root agent and collect reply + step outputs."""
    _AGENT_STEP_MAP = {
        "regime_analyst": 0, "stock_scanner": 1, "dividend_scanner": 2,
        "trade_debate_judge": 3, "bull_advocate": 3, "bear_advocate": 3,
        "trade_executor": 4, "portfolio_manager": 5, "trading_assistant": 6,
    }
    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=message)]
    )
    reply_parts: list[str] = []
    step_outputs: dict[int, str] = {}

    async for event in _runner.run_async(
        user_id=_USER_ID, session_id=session_id, new_message=user_content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text and part.text.strip():
                    text = part.text.strip()
                    reply_parts.append(text)
                    author = getattr(event, "author", None) or ""
                    if author in _AGENT_STEP_MAP:
                        idx = _AGENT_STEP_MAP[author]
                        step_outputs[idx] = step_outputs.get(idx, "") + "\n" + text

    return "\n\n".join(reply_parts), step_outputs


def _strip_md(s: str) -> str:
    """Strip markdown bold markers and leading/trailing whitespace."""
    return re.sub(r"\*+", "", s).strip()


def _extract_number(text: str, key: str) -> float | None:
    """Extract a numeric value from 'Key: value' in text."""
    m = re.search(rf"\*?\*?{key}\*?\*?:\s*([^\n]+)", text, re.IGNORECASE)
    if not m:
        return None
    val = _strip_md(m.group(1))
    # Handle ratio format like 1:2.5
    rr = re.search(r"1\s*:\s*([\d.]+)", val)
    if rr:
        try:
            return float(rr.group(1))
        except ValueError:
            return None
    cleaned = re.sub(r"[^\d.\-]", "", val)
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _extract_string(text: str, key: str) -> str | None:
    """Extract a string value from 'Key: value' in text."""
    m = re.search(rf"\*?\*?{key}\*?\*?:\s*([^\n]+)", text, re.IGNORECASE)
    return _strip_md(m.group(1)) if m else None


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_stock(req: AnalyzeRequest):
    """Orchestrated full analysis pipeline — guarantees all 5 steps run."""
    import logging, re, time
    log = logging.getLogger("server.analyze")

    ticker = req.ticker.strip().upper()
    if not ticker.startswith("^") and not ticker.endswith(".NS"):
        ticker = ticker + ".NS"

    _STEP_NAMES = [
        "Regime Analyst", "Stock Scanner", "Dividend Scanner",
        "Debate (Bull vs Bear)", "Trade Executor", "Portfolio Manager", "Autonomous Flow",
    ]
    step_data: list[dict] = [
        {"name": n, "status": "pending", "summary": None, "output": None}
        for n in _STEP_NAMES
    ]
    full_reply_parts: list[str] = []
    loop = asyncio.get_running_loop()

    # ── STEP 1: Regime (direct call) ──────────────────────────────────────
    t0 = time.time()
    try:
        regime_result = await loop.run_in_executor(None, analyze_regime)
        regime = regime_result.get("regime", "SIDEWAYS")
        regime_summary = regime_result.get("reasoning", f"Market regime: {regime}")
        strategy = regime_result.get("strategy", "")
        step_data[0] = {
            "name": _STEP_NAMES[0], "status": "complete",
            "summary": f"Market regime: {regime} ({strategy})",
            "output": regime_summary,
        }
        full_reply_parts.append(f"**Regime Analysis:** {regime_summary}")
        log.info("Step 1 (Regime): %s in %.1fs", regime, time.time() - t0)
    except Exception as e:
        regime = "SIDEWAYS"
        step_data[0]["status"] = "error"
        step_data[0]["summary"] = f"Error: {e}"
        log.exception("Step 1 (Regime) failed")

    # ── STEP 2: Stock Scan (direct call) ──────────────────────────────────
    t0 = time.time()
    atr = 0.0
    close_price = 0.0
    rsi = 0.0
    scan_result: dict = {}
    try:
        scan_result = await loop.run_in_executor(
            None, lambda: get_stock_analysis(symbol=ticker)
        )
        close_price = scan_result.get("close", 0)
        atr = scan_result.get("atr", 0) or 0
        rsi = scan_result.get("rsi") or 0
        breakout = scan_result.get("breakout", False) or scan_result.get("is_breakout", False)
        above_50dma = scan_result.get("above_50dma", None)
        support_zone = scan_result.get("support_zone", False)

        scan_summary = (
            f"{ticker}: Close={close_price}, RSI={rsi}, ATR={atr:.1f}, "
            f"Breakout={'Yes' if breakout else 'No'}, "
            f"Above 50DMA={'Yes' if above_50dma else 'No'}, "
            f"Support Zone={'Yes' if support_zone else 'No'}"
        )
        # Build detailed output
        scan_output_lines = [scan_summary]
        for k, v in scan_result.items():
            if k not in ("status", "symbol") and v is not None:
                scan_output_lines.append(f"  {k}: {v}")

        step_data[1] = {
            "name": _STEP_NAMES[1], "status": "complete",
            "summary": scan_summary[:120],
            "output": "\n".join(scan_output_lines),
        }
        full_reply_parts.append(f"**Stock Scan:** {scan_summary}")
        log.info("Step 2 (Scan): close=%.2f atr=%.2f rsi=%.1f in %.1fs",
                 close_price, atr, rsi or 0, time.time() - t0)
    except Exception as e:
        step_data[1]["status"] = "error"
        step_data[1]["summary"] = f"Error: {e}"
        log.exception("Step 2 (Scan) failed")

    # ── STEP 3: Dividend Scanner (direct call) ───────────────────────────
    t0 = time.time()
    try:
        from trading_agents.tools.fundamental_data import assess_dividend_health
        div_result = await loop.run_in_executor(
            None, lambda: assess_dividend_health(symbol=ticker)
        )
        if div_result.get("status") == "success":
            div_health = div_result.get("dividend_health", "N/A")
            div_score = div_result.get("health_score", 0)
            div_yield = div_result.get("key_metrics", {}).get("dividend_yield_pct")
            div_yield_str = f", Yield: {div_yield:.2f}%" if div_yield else ""
            div_reasons = "; ".join(div_result.get("reasons", [])[:3]) or "No details"
            div_summary = f"{div_result.get('company', ticker)}: {div_health} (Score: {div_score}/100{div_yield_str})"
            step_data[2] = {
                "name": _STEP_NAMES[2], "status": "complete",
                "summary": div_summary[:120],
                "output": f"{div_summary}\nReasons: {div_reasons}",
            }
            full_reply_parts.append(f"**Dividend Health:** {div_summary}")
        else:
            step_data[2] = {
                "name": _STEP_NAMES[2], "status": "complete",
                "summary": "No dividend data available",
                "output": div_result.get("error", "Could not fetch dividend data"),
            }
        log.info("Step 3 (Dividend): %s in %.1fs", div_result.get("dividend_health", "?"), time.time() - t0)
    except Exception as e:
        step_data[2]["status"] = "error"
        step_data[2]["summary"] = f"Error: {e}"
        log.exception("Step 3 (Dividend) failed")

    # ── STEP 4: Debate (data-embedded prompt — no delegation needed) ──────
    # The core problem with ADK sub-agent delegation is the LLM often only
    # delegates to bull_advocate and skips bear_advocate + CIO verdict.
    # Fix: Fetch all data upfront, embed it in the prompt, and ask the LLM
    # to produce BULL_THESIS + BEAR_THESIS + CIO_DECISION in one response.
    t0 = time.time()
    debate_text = ""
    try:
        # Fetch news data for debate context
        from trading_agents.tools.news_data import fetch_stock_news
        news_result = await loop.run_in_executor(
            None, lambda: fetch_stock_news(symbol=ticker)
        )
        news_articles = news_result.get("articles", [])[:8]
        news_text = "\n".join(
            f"  - [{a.get('publisher', '?')}] {a.get('title', '')} ({a.get('days_ago', '?')}d ago)"
            for a in news_articles
        ) or "  No recent news available."

        # Format scan data as text
        scan_data_for_prompt = {
            k: v for k, v in scan_result.items()
            if k not in ("status",)
        }

        # Create a fresh session for the analysis pipeline
        analysis_session = await _runner.session_service.create_session(
            app_name="trading_assistant", user_id=_USER_ID
        )

        debate_prompt = f"""I need you to act as the Trade Debate Judge (CIO) and produce a COMPLETE analysis for {ticker}.

MARKET DATA (already fetched — DO NOT call any tools):
- Market Regime: {regime}
- Current Price: {close_price}
- ATR: {atr:.2f}
- RSI: {rsi}
- Above 50-DMA: {scan_result.get('above_50dma', 'N/A')}
- Volume Ratio: {scan_result.get('volume_ratio', 'N/A')}
- Breakout: {scan_result.get('breakout', False)}
- 50-DMA: {scan_result.get('dma_50', 'N/A')}
- 20d High: {scan_result.get('prev_20d_high', 'N/A')}

Recent News:
{news_text}

YOU MUST produce ALL THREE sections below in your response. Do NOT skip any section.

SECTION 1 — BULL_THESIS:
Present the strongest possible bullish case using the data above.
Include: Quant Strengths, Sentiment Strengths, Catalysts, Risk Rebuttal, Why Bulls Could Be Right, Conviction (0-1).

SECTION 2 — BEAR_THESIS:
Present the strongest possible bearish case, challenging the bull thesis.
Include: Quant Weaknesses, Sentiment Risks, Downside Catalysts, Bull Case Flaws, Why Bears Could Be Right, Conviction (0-1).

SECTION 3 — CIO_DECISION:
After weighing both sides, deliver your FINAL verdict:
Verdict: [BUY or SELL or HOLD]
Ticker: {ticker}
Regime: {regime}
Entry: [price within ±2% of {close_price}]
Stop Loss: [1-2 ATR below entry for BUY, above for SELL]
Target: [at least 2:1 risk-reward ratio]
Risk Reward: [ratio like 1:2.5]
Conviction: [0-1]
Bull Summary: [2-3 key points]
Bear Summary: [2-3 key points]
Reasoning: [3-5 sentences]

RESPOND WITH ALL THREE SECTIONS. Do NOT use any tools."""

        debate_text, debate_steps = await _run_agent_turn(
            analysis_session.id, debate_prompt
        )

        # Collect debate output (from step index 3 or root agent text)
        debate_output = debate_steps.get(3, "") or debate_steps.get(6, "") or debate_text
        if not debate_output.strip():
            debate_output = debate_text

        step_data[3] = {
            "name": _STEP_NAMES[3], "status": "complete",
            "summary": (
                _extract_string(debate_text, "Verdict") or
                "Debate complete"
            )[:120],
            "output": debate_output.strip(),
        }
        full_reply_parts.append(debate_text)
        log.info("Step 3 (Debate): verdict=%s in %.1fs",
                 _extract_string(debate_text, "Verdict"), time.time() - t0)
    except Exception as e:
        step_data[3]["status"] = "error"
        step_data[3]["summary"] = f"Error: {e}"
        log.exception("Step 3 (Debate) failed")

    # ── STEP 4: Risk Check / Trade Plan (direct call) ─────────────────────
    t0 = time.time()
    trade_data: dict | None = None
    try:
        # Extract trade params from debate output
        verdict = (_extract_string(debate_text, "Verdict") or "HOLD").upper()
        # Clean verdict — remove any stray chars
        for v in ("BUY", "SELL", "HOLD"):
            if v in verdict:
                verdict = v
                break

        entry = _extract_number(debate_text, "Entry") or close_price
        stop_from_debate = _extract_number(debate_text, "Stop Loss")
        target_from_debate = _extract_number(debate_text, "Target")
        rr_from_debate = _extract_number(debate_text, "Risk Reward")
        conviction = _extract_number(debate_text, "Conviction") or 0.5
        if conviction > 1:
            conviction = conviction / 100.0

        if verdict in ("BUY", "SELL"):
            # Run the deterministic risk engine for BUY/SELL
            risk_result = await loop.run_in_executor(
                None,
                lambda: check_risk(
                    symbol=ticker, action=verdict, entry=entry,
                    atr=atr if atr > 0 else entry * 0.02,
                    conviction=conviction, regime=regime,
                    target=target_from_debate or 0.0,
                ),
            )

            killed = risk_result.get("killed", False) or risk_result.get("status") == "REJECTED"
            kill_reason = risk_result.get("kill_reason") or risk_result.get("reason")

            final_entry = risk_result.get("entry_price", entry)
            final_stop = risk_result.get("stop_loss") or stop_from_debate or 0
            final_target = risk_result.get("target_price") or target_from_debate or 0
            rr_ratio = risk_result.get("risk_reward_ratio") or rr_from_debate
            position_size = risk_result.get("position_size", 0)

            trade_data = {
                "ticker": ticker,
                "action": verdict,
                "entry": round(final_entry, 2) if final_entry else None,
                "stop": round(final_stop, 2) if final_stop else None,
                "target": round(final_target, 2) if final_target else None,
                "riskReward": round(rr_ratio, 2) if rr_ratio else None,
                "regime": regime,
                "conviction": round(conviction, 2),
                "killed": killed,
                "killReason": kill_reason,
                "positionSize": position_size,
                "riskDetails": {
                    k: v for k, v in risk_result.items()
                    if k not in ("status", "summary")
                } if killed else None,
            }

            if killed:
                step_data[4] = {
                    "name": _STEP_NAMES[4], "status": "flagged",
                    "summary": f"REJECTED: {kill_reason}"[:120] if kill_reason else "Trade rejected",
                    "output": json.dumps(risk_result, indent=2, default=str),
                }
            else:
                trade_summary = (
                    f"{verdict} {ticker} | Entry: {final_entry:.2f} | "
                    f"Stop: {final_stop:.2f} | Target: {final_target:.2f} | "
                    f"R:R 1:{rr_ratio:.1f} | Qty: {position_size}"
                )
                step_data[4] = {
                    "name": _STEP_NAMES[4], "status": "complete",
                    "summary": trade_summary[:120],
                    "output": json.dumps(risk_result, indent=2, default=str),
                }
                full_reply_parts.append(f"**Trade Plan:** {trade_summary}")
        else:
            # HOLD verdict — no trade needed, clear stop/target/rr
            trade_data = {
                "ticker": ticker,
                "action": "HOLD",
                "entry": round(entry, 2),
                "stop": None,
                "target": None,
                "riskReward": None,
                "regime": regime,
                "conviction": round(conviction, 2),
                "killed": False,
                "killReason": None,
                "positionSize": 0,
                "riskDetails": None,
            }
            step_data[4] = {
                "name": _STEP_NAMES[4], "status": "complete",
                "summary": f"HOLD — No trade. Conviction: {conviction:.1f}",
                "output": f"Verdict: HOLD\nNo trade execution needed.\nConviction: {conviction}",
            }
            full_reply_parts.append(
                f"**Trade Decision:** HOLD {ticker} — No trade. Conviction: {conviction:.1f}"
            )

        log.info("Step 4 (Trade): %s killed=%s in %.1fs",
                 verdict, trade_data.get('killed', False), time.time() - t0)
    except Exception as e:
        step_data[4]["status"] = "error"
        step_data[4]["summary"] = f"Error: {e}"
        log.exception("Step 4 (Trade) failed")

    # ── STEP 5: Portfolio Impact (direct call) ────────────────────────────
    t0 = time.time()
    try:
        portfolio_result = await loop.run_in_executor(None, get_portfolio_summary)
        cash = portfolio_result.get("cash", 0)
        positions = portfolio_result.get("open_positions_count", 0)
        portfolio_value = portfolio_result.get("portfolio_value", 0)
        portfolio_summary = (
            f"Cash: INR {cash:,.0f} | Positions: {positions} | "
            f"Portfolio Value: INR {portfolio_value:,.0f}"
        )
        step_data[5] = {
            "name": _STEP_NAMES[5], "status": "complete",
            "summary": portfolio_summary[:120],
            "output": json.dumps(portfolio_result, indent=2, default=str),
        }
        full_reply_parts.append(f"**Portfolio:** {portfolio_summary}")
        log.info("Step 6 (Portfolio): cash=%.0f positions=%d in %.1fs",
                 cash, positions, time.time() - t0)
    except Exception as e:
        step_data[5]["status"] = "error"
        step_data[5]["summary"] = f"Error: {e}"
        log.exception("Step 6 (Portfolio) failed")

    # ── STEP 7: Autonomous Flow (synthesis) ───────────────────────────────
    try:
        # Build a concise summary of all completed steps
        completed_count = sum(1 for s in step_data if s["status"] in ("complete", "flagged"))
        total_count = len(step_data) - 1  # exclude this step itself
        auto_verdict = trade_data.get("action", "HOLD") if trade_data else "HOLD"
        auto_conviction = trade_data.get("conviction", 0) if trade_data else 0
        auto_summary_parts = []
        if auto_verdict == "BUY":
            auto_summary_parts.append(f"BUY {ticker} @ {trade_data.get('entry', '?')}")
        elif auto_verdict == "SELL":
            auto_summary_parts.append(f"SELL {ticker} @ {trade_data.get('entry', '?')}")
        else:
            auto_summary_parts.append(f"HOLD {ticker} — No trade action")
        auto_summary_parts.append(f"Pipeline: {completed_count}/{total_count} steps complete")
        auto_summary_parts.append(f"Regime: {regime} | Conviction: {auto_conviction}")
        auto_summary = " | ".join(auto_summary_parts)

        step_data[6] = {
            "name": _STEP_NAMES[6], "status": "complete",
            "summary": auto_summary[:120],
            "output": auto_summary,
        }
    except Exception as e:
        step_data[6]["status"] = "error"
        step_data[6]["summary"] = f"Error: {e}"

    # ── Build debate struct for frontend ──────────────────────────────────
    debate_struct = None
    if debate_text:
        def _extract_section(text: str, start_pat: str, end_pats: list[str]) -> str:
            pat = start_pat + r"[:\s]*([\s\S]*?)(?=" + "|".join(end_pats) + r"|$)"
            m = re.search(pat, text, re.IGNORECASE)
            return _strip_md(m.group(1)) if m else ""

        def _extract_points(section: str) -> list[str]:
            if not section:
                return []
            # Split by section headers like "Quant Strengths:", "Sentiment Risks:" etc.
            # Each header becomes a point (header + content)
            # Headers must appear at start of line (or start of text) to avoid
            # matching mid-sentence occurrences like "...a catalyst for..."
            header_pat = re.compile(
                r"(?:^|\n)\s*(Quant\s*(?:Strengths?|Weaknesses?)|Sentiment\s*(?:Strengths?|Risks?)|"
                r"Catalysts?|Downside\s*Catalysts?|Risk\s*Rebuttal|Bull\s*Case\s*Flaws?|"
                r"Why\s*(?:Bulls?|Bears?)\s*Could\s*Be\s*Right)[:\s]*",
                re.IGNORECASE,
            )
            # Use finditer to get header positions, then extract content between them
            matches = list(header_pat.finditer(section))
            points: list[str] = []
            for idx, m in enumerate(matches):
                header = _strip_md(m.group(1)).rstrip(": ")
                content_start = m.end()
                content_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
                content = _strip_md(section[content_start:content_end]).strip()
                # Strip leading punctuation artifacts (commas, periods)
                content = re.sub(r"^[,;.\s]+", "", content)
                if content and len(content) > 10:
                    # Split on sentence boundaries, but NOT after single
                    # digits/numbers (e.g. "1. item" or "No. 2")
                    sentences = re.split(r"(?<=[.!?])(?<!\d\.)(?<!No\.)\s+", content)
                    # Take enough sentences to give meaningful context (~300 chars)
                    collected = ""
                    for sent in sentences:
                        if collected and len(collected) + len(sent) > 300:
                            break
                        collected = (collected + " " + sent).strip() if collected else sent
                    points.append(f"{header}: {collected[:300]}")

            # Fallback: line-based extraction if header splitting didn't work
            if not points:
                points = [
                    _strip_md(l).lstrip("•-0123456789. ")
                    for l in section.split("\n")
                    if _strip_md(l).strip() and len(_strip_md(l).strip()) > 15
                    and not re.match(
                        r"^(Conviction|BULL_THESIS|BEAR_THESIS|CIO_DECISION|SECTION)",
                        _strip_md(l).strip(), re.I,
                    )
                ][:6]
            return points[:6]

        def _extract_conviction(section: str) -> float:
            m = re.search(r"Conviction[:\s]*(\d+\.?\d*)", section, re.I)
            if m:
                try:
                    v = float(m.group(1))
                    return v / 100 if v > 1 else v
                except ValueError:
                    pass
            return 0.5

        # Try BULL_THESIS / BEAR_THESIS sections (handle "SECTION N —" prefix)
        bull_sect = _extract_section(
            debate_text, r"(?:SECTION\s*\d+\s*[—\-]+\s*)?BULL_THESIS",
            [r"(?:SECTION\s*\d+\s*[—\-]+\s*)?BEAR_THESIS", r"(?:SECTION\s*\d+\s*[—\-]+\s*)?CIO_DECISION"],
        )
        bear_sect = _extract_section(
            debate_text, r"(?:SECTION\s*\d+\s*[—\-]+\s*)?BEAR_THESIS",
            [r"(?:SECTION\s*\d+\s*[—\-]+\s*)?CIO_DECISION", r"(?:SECTION\s*\d+\s*[—\-]+\s*)?BULL_THESIS"],
        )

        # Fallback: Bull Summary / Bear Summary from CIO_DECISION
        if not bull_sect:
            bull_sect = _extract_section(debate_text, r"Bull\s*Summary", [r"Bear\s*Summary", "Reasoning"])
        if not bear_sect:
            bear_sect = _extract_section(debate_text, r"Bear\s*Summary", ["Reasoning", r"Bull\s*Summary"])

        debate_struct = {
            "bull": {
                "points": _extract_points(bull_sect),
                "conviction": _extract_conviction(bull_sect or debate_text),
            },
            "bear": {
                "points": _extract_points(bear_sect),
                "conviction": _extract_conviction(bear_sect or debate_text),
            },
        }

    # ── Final reply ───────────────────────────────────────────────────────
    final_reply = "\n\n".join(full_reply_parts) if full_reply_parts else "Analysis incomplete."

    return AnalyzeResponse(
        reply=final_reply,
        trade=trade_data,
        steps=step_data,
        debate=debate_struct,
    )


@app.get("/api/regime")
async def regime():
    loop = asyncio.get_running_loop()
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
            """Wilder's smoothed RSI — matches trading_agents/tools/technical.py."""
            out = [None] * len(series)
            if len(series) < period + 1:
                return out
            # Seed with simple average of first `period` changes
            gains, losses = 0.0, 0.0
            for j in range(1, period + 1):
                ch = series[j] - series[j - 1]
                if ch > 0:
                    gains += ch
                else:
                    losses -= ch
            avg_gain = gains / period
            avg_loss = losses / period
            if avg_loss == 0:
                out[period] = 100.0
            else:
                rs = avg_gain / avg_loss
                out[period] = round(100 - (100 / (1 + rs)), 2)
            # Exponential smoothing for subsequent bars
            for i in range(period + 1, len(series)):
                ch = series[i] - series[i - 1]
                g = ch if ch > 0 else 0.0
                l = -ch if ch < 0 else 0.0
                avg_gain = (avg_gain * (period - 1) + g) / period
                avg_loss = (avg_loss * (period - 1) + l) / period
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


# ── SPA fallback: serve index.html for all non-API, non-asset routes ──
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    """Catch-all for client-side routes (React Router)."""
    frontend_index = _FRONTEND_DIR / "index.html"
    if frontend_index.is_file():
        return HTMLResponse(content=frontend_index.read_text(encoding="utf-8"))
    # If no React build, 404
    return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)
