# Regime-Aware AI Trading Command Center

### GDG HackFest 2026 · Hybrid Quant + Gemini Multi-Agent System

A **production-style agentic AI trading system** built with **Google ADK** and **Gemini** on **Vertex AI**.

The system demonstrates how **AI agents can safely automate financial workflows** by combining deterministic quantitative models, multi-agent adversarial reasoning, a risk engine that can override AI decisions, paper trading, and a real-time React dashboard.

> **This is a workflow automation system, not a chatbot.**

---

## Live Dashboard

| Page | What It Shows |
|------|---------------|
| **Dashboard** (`/`) | Chat interface, market regime card, portfolio summary, backtest results, dividend scanner, Nifty 50 signal board |
| **Market** (`/market`) | Interactive candlestick / line chart with SMA overlays, volume bars, RSI, period & interval selectors |
| **Analyze** (`/analyze`) | Full 7-step AI pipeline: Regime → Scan → Dividend Health → Debate → Trade/Risk → Portfolio → Autonomous Flow |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React + Tailwind Frontend                     │
│    Dashboard  ·  Market Chart  ·  Analyze Pipeline  ·  Chat     │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API
┌──────────────────────────┴──────────────────────────────────────┐
│                   FastAPI Server (server/app.py)                 │
│                                                                  │
│  /api/chat ──► ADK root_agent (LLM-driven delegation)           │
│  /api/analyze ──► Server-orchestrated 7-step pipeline            │
│  /api/market, /api/regime, /api/portfolio, /api/signals, ...     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                  Google ADK Agent Layer                           │
│                                                                  │
│  root_agent (trading_assistant)                                  │
│    ├── regime_analyst         → analyze_regime()                 │
│    ├── stock_scanner          → scan_watchlist / get_analysis    │
│    ├── dividend_scanner       → assess_dividend_health()         │
│    ├── trade_debate_judge     → Bull vs Bear adversarial debate  │
│    │     ├── bull_advocate                                       │
│    │     └── bear_advocate                                       │
│    ├── trade_executor         → check_risk() + paper trading     │
│    └── portfolio_manager      → portfolio CRUD                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                  Deterministic Python Layer                       │
│                                                                  │
│  Risk Engine · Technical Indicators · Regime Classifier          │
│  Position Sizing · ATR Stop-Loss · Portfolio Persistence         │
│  yfinance (live NSE data) · News Fetcher                        │
└─────────────────────────────────────────────────────────────────┘
```

**Key design principle:** The LLM reasons and orchestrates; Python computes and enforces. The AI cannot override mathematical risk rules.

---

## Seven-Step Analysis Pipeline

When you click **Run Analysis** on the Analyze page, the server orchestrates these steps programmatically (no LLM delegation failures):

| Step | Agent | What It Does |
|------|-------|-------------|
| 1 | Regime Analyst | Classifies market as BULL / SIDEWAYS / BEAR using 50-DMA, 200-DMA, slope, momentum |
| 2 | Stock Scanner | Fetches live OHLCV, computes RSI, ATR, 50-DMA, breakout detection, volume ratio |
| 3 | Dividend Scanner | Assesses dividend health (HEALTHY / CAUTION / DESPERATE) via earnings growth, payout ratio, PE, ROE |
| 4 | Debate (Bull vs Bear) | LLM produces BULL_THESIS + BEAR_THESIS + CIO_DECISION in one pass with embedded market data |
| 5 | Trade Executor | Deterministic risk engine: entry/stop/target calc, position sizing, kill rules. Or HOLD with no trade. |
| 6 | Portfolio Manager | Reports cash, open positions, portfolio value |
| 7 | Autonomous Flow | Synthesis summary of all completed steps |

---

## Bull vs Bear Debate

The debate is the core innovation. Instead of a single LLM opinion, the system generates **adversarial arguments**:

- **Bull Advocate** — strongest possible case FOR the trade (quant strengths, sentiment strengths, catalysts, risk rebuttal)
- **Bear Advocate** — strongest possible case AGAINST (quant weaknesses, sentiment risks, downside catalysts, bull case flaws)
- **CIO Decision** — final verdict (BUY / SELL / HOLD) with entry, stop-loss, target, risk-reward ratio, conviction score

Both sides cite real data (RSI, 50-DMA, volume, news headlines). The CIO weighs both and delivers a data-backed verdict.

---

## Risk Engine

All risk calculations are **deterministic Python** — the LLM cannot override them.

| Rule | Implementation |
|------|---------------|
| Stop-Loss | `Entry − (1.5 × ATR)` for BUY; `Entry + (1.5 × ATR)` for SELL |
| Position Size | `floor((Portfolio × 0.01) / RiskPerShare)` — 1% risk per trade |
| Minimum R:R | ≥ 1.5:1 reward-to-risk ratio |
| Conviction Gate | Trades below 0.4 conviction are killed |
| Regime Filter | BEAR regime trades face stricter scrutiny |
| Volatility Cap | Excessive ATR-to-price ratio triggers rejection |
| Max Exposure | Portfolio-level position limits |

The risk engine can **REJECT** trades that pass the debate — risk rules act as a hard safety layer.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI** | Google ADK, Gemini (via Vertex AI or API key) |
| **Backend** | Python 3.11, FastAPI, uvicorn |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, Recharts, shadcn/ui |
| **Data** | yfinance (live NSE OHLCV + news), Yahoo Finance |
| **Storage** | JSON file-based portfolio (`server/memory/portfolio.json`) |

### Model Fallback

At startup, `_pick_available_model()` probes models in order and uses the first that responds:

1. `gemini-3-flash-preview`
2. `gemini-2.5-flash`
3. `gemini-2.0-flash`
4. `gemini-2.5-pro`

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/chat` | POST | Send message to ADK root agent |
| `/api/analyze` | POST | Server-orchestrated 7-step analysis pipeline |
| `/api/regime` | GET | Current market regime |
| `/api/market` | GET | OHLCV + indicators for chart (ticker, period, interval) |
| `/api/portfolio` | GET | Portfolio summary |
| `/api/portfolio/performance` | GET | Portfolio performance metrics |
| `/api/portfolio/refresh` | POST | Refresh position prices |
| `/api/portfolio/reset` | POST | Reset to initial INR 10,00,000 |
| `/api/backtest/oversold-summary` | GET | Oversold bounce backtest results |
| `/api/backtest/oversold-best` | GET | Best oversold trades |
| `/api/dividend/top` | GET | Top dividend stocks |
| `/api/signals/nifty50` | GET | Nifty 50 signal board |

---

## Project Structure

```
GDG_HACKFEST/
├── server/
│   └── app.py                          # FastAPI backend (~970 lines)
│
├── trading_agents/                     # Google ADK agent package
│   ├── __init__.py
│   ├── agent.py                        # root_agent — coordinator
│   ├── config.py                       # model fallback, risk rules, watchlist
│   ├── models.py                       # Pydantic data models
│   ├── utils.py                        # shared helpers (IST, ticker normalization)
│   ├── risk_engine.py                  # deterministic risk engine (290 lines)
│   ├── regime_agent.py                 # market regime classifier
│   ├── scanner_agent.py                # breakout + stock scanner
│   ├── debate_agent.py                 # bull/bear/CIO debate system
│   ├── trade_agent.py                  # trade execution + risk check
│   ├── portfolio_agent.py              # portfolio queries
│   ├── dividend_agent.py               # dividend scanning
│   └── tools/
│       ├── market_data.py              # live NSE data (yfinance)
│       ├── news_data.py                # stock news fetcher
│       ├── technical.py                # indicators (DMA, ATR, RSI, breakout)
│       ├── fundamental_data.py         # fundamentals + dividend health
│       ├── dividend_data.py            # MoneyControl dividend scraper
│       ├── paper_trading.py            # paper trade execution
│       ├── portfolio.py                # portfolio persistence (JSON)
│       ├── risk_tool.py                # ADK-compatible check_risk wrapper
│       ├── backtest_oversold.py        # oversold bounce backtest
│       ├── backtest_dividend.py        # dividend momentum backtest
│       ├── autonomous_trading.py       # autonomous trading flow
│       ├── market_status.py            # market open/close check
│       └── demo_tools.py              # demo helpers
│
├── frontend/                           # React + Vite + Tailwind
│   ├── src/
│   │   ├── App.tsx                     # Router setup
│   │   ├── api.ts                      # API client
│   │   ├── pages/
│   │   │   ├── Home.tsx                # Dashboard (chat + widgets)
│   │   │   ├── Market.tsx              # Interactive chart page
│   │   │   └── Analyze.tsx             # 7-step AI pipeline page
│   │   └── components/
│   │       ├── Layout.tsx              # App shell + nav
│   │       ├── Chat.tsx                # Chat interface
│   │       ├── MarketChart.tsx         # Candlestick/line chart (SVG + Recharts)
│   │       ├── MarketRegime.tsx        # Regime status card
│   │       ├── Portfolio.tsx           # Portfolio summary
│   │       ├── DecisionCard.tsx        # Trade decision display
│   │       ├── DebatePanel.tsx         # Bull vs Bear debate UI
│   │       ├── PipelineSteps.tsx       # 7-step pipeline visualizer
│   │       ├── SignalBoard.tsx         # Nifty 50 signals
│   │       ├── BacktestSummary.tsx     # Backtest results
│   │       └── DividendTop.tsx         # Top dividend stocks
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                              # Test suite
├── _archive/                           # Archived legacy code
├── docs/                               # Architecture docs
├── memory/                             # Portfolio JSON persistence
├── requirements.txt                    # Python dependencies
└── README.md
```

---

## NSE Watchlist (Nifty 50 Stocks)

| # | Symbol | Company |
|---|--------|---------|
| 1 | RELIANCE.NS | Reliance Industries |
| 2 | TCS.NS | Tata Consultancy Services |
| 3 | HDFCBANK.NS | HDFC Bank |
| 4 | INFY.NS | Infosys |
| 5 | ICICIBANK.NS | ICICI Bank |
| 6 | HINDUNILVR.NS | Hindustan Unilever |
| 7 | ITC.NS | ITC Limited |
| 8 | SBIN.NS | State Bank of India |
| 9 | BHARTIARTL.NS | Bharti Airtel |
| 10 | KOTAKBANK.NS | Kotak Mahindra Bank |
| 11 | LT.NS | Larsen & Toubro |
| 12 | AXISBANK.NS | Axis Bank |
| 13 | ASIANPAINT.NS | Asian Paints |
| 14 | MARUTI.NS | Maruti Suzuki |
| 15 | TITAN.NS | Titan Company |
| 16 | SUNPHARMA.NS | Sun Pharma |
| 17 | BAJFINANCE.NS | Bajaj Finance |
| 18 | WIPRO.NS | Wipro |
| 19 | HCLTECH.NS | HCL Technologies |
| 20 | TATAMOTORS.NS | Tata Motors |

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd GDG_HACKFEST

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure credentials

Create `trading_agents/.env`:

```env
# Option A: Vertex AI (recommended)
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Option B: API Key
# GOOGLE_API_KEY=your-api-key
```

### 3. Build the frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run the server

```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### 5. Alternative: ADK Web UI

```bash
cd trading_agents
adk web
```

---

## Chat Commands

| Prompt | What Happens |
|--------|-------------|
| "What is the current market regime?" | Fetches live Nifty 50 data, classifies BULL/SIDEWAYS/BEAR |
| "Scan for breakout stocks" | Scans watchlist for 20-day breakout candidates |
| "Analyze RELIANCE" | Full 7-step pipeline: regime → scan → dividend → debate → risk → portfolio |
| "Should I buy TCS?" | Bull vs Bear debate with BUY/SELL/HOLD verdict |
| "Show my portfolio" | Cash, positions, P&L, trade history |
| "Reset portfolio" | Resets to INR 10,00,000 |

---

## What Makes This Agentic

| Property | Implementation |
|----------|---------------|
| **Autonomous reasoning** | LLM decides which sub-agent to delegate to and how to interpret results |
| **Tool use** | 15+ deterministic tool functions registered with ADK |
| **Multi-agent orchestration** | Root agent coordinates 6 sub-agents (8 total including debate advocates) |
| **Adversarial reasoning** | Bull and Bear agents debate from opposing perspectives; CIO delivers verdict |
| **Deterministic safety** | Risk engine is pure Python — LLM cannot override math |
| **Memory** | Portfolio state persists to disk across sessions |
| **Explainability** | Every decision includes data, reasoning, source, and timestamp |
| **Observability** | React dashboard shows pipeline steps, debate points, chart, and trade details in real time |

---

## License

See [LICENSE](LICENSE).

---

**Built for GDG Chennai HackFest 2026** — Autonomous AI Agents solving real workflows.
