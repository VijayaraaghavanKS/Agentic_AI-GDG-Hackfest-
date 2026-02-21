# Agentic Indian Stock Market Trading Assistant

A **multi-agent AI trading assistant** for the Indian stock market (NSE), built with **Google ADK**.
Uses live market data, classifies market regimes, scans for breakout stocks, executes paper trades,
and manages a virtual portfolio -- all through natural language.

## Features

- **Live NSE data** via Yahoo Finance (Nifty 50, Bank Nifty, 20 liquid stocks)
- **Regime detection** -- classifies market as BULL / SIDEWAYS / BEAR
- **Breakout scanner** -- finds 20-day breakout candidates with volume confirmation
- **Paper trading** -- position sizing, risk rules, trade execution
- **Portfolio tracking** -- cash, holdings, PnL, trade history
- **Multi-agent architecture** -- 4 specialist agents coordinated by a root agent
- **Web dashboard** -- dark-themed UI with chat + regime + portfolio panels

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Set up API key

Copy and edit the env file:

```bash
copy trading_agents\.env.example trading_agents\.env
```

Add your Gemini API key in `trading_agents/.env`:

```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_here
```

### 3. Run with ADK (terminal mode)

```bash
adk run trading_agents
```

### 4. Run with ADK (web UI)

```bash
adk web
```

Open http://localhost:8000 and select **trading_agents** in the dropdown.
(Other folders like `data`, `docs` may appear in the list -- ignore them.)

### 5. Run the dashboard

```bash
python -m uvicorn server.app:app --reload --port 8080
```

Open http://localhost:8080

## Example Prompts

- "What is the current market regime?"
- "Scan for breakout stocks"
- "Analyze RELIANCE"
- "Plan a trade for TCS at 4200 with ATR 85"
- "Execute the trade"
- "Show my portfolio"
- "Reset portfolio"

## Project Structure

```
trading_agents/          # ADK agent package
  agent.py                # root_agent (coordinator)
  regime_agent.py         # market regime classifier
  scanner_agent.py        # breakout stock scanner
  trade_agent.py          # paper trade executor
  portfolio_agent.py      # portfolio manager
  tools/
    market_data.py        # live NSE data (yfinance)
    technical.py          # indicators (DMA, ATR, breakout)
    paper_trading.py      # trade plans + execution
    portfolio.py          # portfolio persistence
  config.py               # risk rules + NSE defaults
  models.py               # Pydantic data models
server/
  app.py                  # FastAPI backend
  static/
    index.html            # dashboard UI
    style.css
    app.js
memory/
  portfolio.json          # paper portfolio state
docs/
  ARCHITECTURE.md         # system design docs
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

## Disclaimer

This is a **paper trading assistant** for educational purposes only.
No real money is involved. Not financial advice.
