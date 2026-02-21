# Architecture -- Agentic Indian Stock Market Trading Assistant

## System Design

This application is a **multi-agent system** built on **Google ADK** (Agent Development Kit).
A root coordinator agent delegates tasks to four specialist sub-agents, each with their own
tools and responsibilities. All data comes from live NSE market feeds via Yahoo Finance.

## Agent Hierarchy

```
trading_assistant (root coordinator)
  |
  +-- regime_analyst        -> analyzes Nifty 50 to classify BULL / SIDEWAYS / BEAR
  +-- stock_scanner         -> scans 20 NSE stocks for breakout candidates
  +-- trade_executor        -> calculates trade plans and executes paper trades
  +-- portfolio_manager     -> reports portfolio state, holdings, PnL
```

## Data Flow

```
User (browser) ---> FastAPI server ---> ADK root_agent
                                           |
                    +----------+-----------+-----------+
                    |          |           |           |
             regime_analyst  scanner  trade_executor  portfolio
                    |          |           |           |
              fetch_index  fetch_stock  paper_trade  load/save
              (yfinance)   (yfinance)   (memory/)    (memory/)
```

## Tool Functions

### market_data.py
- `fetch_index_data(symbol, days)` -- fetches index OHLCV from Yahoo Finance
- `fetch_stock_data(symbol, days)` -- fetches individual stock OHLCV

### technical.py
- `compute_index_metrics(closes)` -- 50-DMA, slope, 20d return, volatility
- `compute_atr(highs, lows, closes, period)` -- Average True Range
- `detect_breakout(symbol, closes, volumes, highs, lows)` -- 20-day breakout detection

### paper_trading.py
- `calculate_trade_plan(symbol, close, atr)` -- entry, stop, target, position size
- `execute_paper_trade(symbol, entry, stop, target, qty)` -- execute with risk rules

### portfolio.py
- `load_portfolio()` / `save_portfolio()` -- JSON persistence
- `get_portfolio_summary()` -- formatted portfolio overview
- `reset_portfolio()` -- reset to initial capital

## Risk Rules (hardcoded, not LLM-decided)

| Rule               | Value         |
|--------------------|---------------|
| Risk per trade     | 1% of cash    |
| Max open trades    | 3             |
| Min reward:risk    | 2:1           |
| Stop-loss          | 1.5 x ATR     |
| BEAR regime        | No new trades |

## Tech Stack

- **Agent framework:** Google ADK (Python)
- **LLM:** Gemini 2.5 Flash
- **Data:** Yahoo Finance via yfinance
- **Backend:** FastAPI + uvicorn
- **Frontend:** HTML/CSS/JS (single-page dashboard)
- **Memory:** JSON file (memory/portfolio.json)
- **Market:** NSE (Nifty 50 + top 20 liquid stocks)
