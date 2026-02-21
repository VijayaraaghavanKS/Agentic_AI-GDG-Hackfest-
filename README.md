# 🏛️ Regime-Aware AI Trading Command Center
### GDG HackFest 2026 · Hybrid Quant + Gemini Multi-Agent System

A **production-style agentic AI trading system** built using **Google ADK and Gemini 3**.

This project demonstrates how **AI agents can safely automate financial workflows** by combining:

- Deterministic Quantitative Models
- Multi-Agent AI Reasoning
- Risk Enforcement
- Paper Trading
- Observability Dashboard

This is a **real workflow automation system**, not a chatbot.

---

# Core Philosophy — Hybrid Quant + AI Agents

Most AI trading bots fail because:

- LLMs hallucinate numbers
- Risk management is ignored
- Bots revenge-trade after losses

This system solves that by **separating mathematics from reasoning.**

```
PYTHON (Quant Engine)
      ↓
GEMINI AGENTS (Reasoning)
      ↓
PYTHON (Risk Engine)
```

## Deterministic Python — "The Handcuffs"

Python handles:

- Market data fetching
- Indicator calculations
- Market regime detection
- Position sizing
- Stop-loss calculation
- Risk enforcement

The AI **cannot override mathematics.**

---

## Gemini Agents — "The Brain"

Gemini is used only for:

- Market reasoning
- News interpretation
- Bull vs Bear debate
- Trade thesis generation

The AI **advises but does not execute trades.**

---

# System Capabilities

The system performs **real financial workflow automation.**

---

## 1 — Market Regime Detection

Classifies the market into:

- BULL
- SIDEWAYS
- BEAR

Using:

- 50 DMA
- 200 DMA
- Trend slope
- 20-day returns

---

## 2 — Breakout Scanning

Scans Nifty50 stocks for:

- 20-day breakouts
- Volume expansion
- Trend confirmation

---

## 3 — AI Debate Engine

Four Gemini agents collaborate.

### Sentiment Agent

- Reads live news
- Summarizes sentiment

### Bull Agent

- Builds strongest bullish thesis

### Bear Agent

- Attacks bull thesis
- Identifies risks

### CIO Agent

- Synthesizes debate
- Approves or rejects trade

---

## 4 — Quant Risk Engine

Strict mathematical rules enforce safety.

### Stop Loss

```
StopLoss = Entry − (1.5 × ATR)
```

### Position Size

```
Shares = (Portfolio × 0.01) / RiskPerShare
```

### Risk Rules

- Maximum 1% portfolio risk
- Minimum 1.5 reward/risk
- Volatility limits enforced
- No invalid stop-loss values

Python can **override AI decisions.**

---

## 5 — Paper Trading Engine

Simulates trades with full risk validation.

Calculates:

- Entry price
- Stop-loss
- Target price
- Position size
- Capital required

Portfolio stored in:

```
memory/portfolio.json
```

Tracks:

- Cash
- Positions
- PnL
- Trade history

---

## 6 — Observability Dashboard

Shows system reasoning in real time.

Displays:

- Market regime
- AI debate
- Risk calculations
- Trade setups
- Portfolio state

Built using:

- Streamlit
- Plotly

---

# Agent Architecture

```
User Input
    ↓
Root Agent (ADK)
    ↓
--------------------------------
| Regime Agent
| Scanner Agent
| Trade Agent
| Portfolio Agent
--------------------------------
    ↓
Python Tools
    ↓
Yahoo Finance
```

The Gemini model decides **what to do.**

Python tools perform **all calculations.**

---

# Multi-Agent Workflow

Example request:

```
Run a full market scan and trade
```

System executes:

1. Market Regime Detection
2. Breakout Scanning
3. AI Debate
4. Risk Calculation
5. Trade Planning
6. Portfolio Update

---

# Quant Engine

Pure deterministic Python.

Indicators:

- 50 DMA
- 200 DMA
- ATR
- RSI
- MACD

---

## Regime Classification Rules

```
BULL:
Price > 50DMA > 200DMA

BEAR:
Price < 50DMA < 200DMA

Otherwise:
NEUTRAL
```

---

# Risk Engine

Hard safety layer.

Prevents:

- Oversized trades
- Unrealistic stops
- Bad reward/risk
- High volatility trades

AI cannot bypass risk rules.

---

# Paper Trading Rules

| Rule | Value |
|------|------|
Risk per trade | 1%
Stop Loss | 1.5×ATR
Reward/Risk | ≥1.5
Max Trades | Limited
Execution | Paper only

---

# Example Commands

```
What is the market regime?
```

```
Scan for breakout stocks
```

```
Analyze RELIANCE.NS
```

```
Plan a trade for TCS
```

```
Show portfolio
```

```
Run full scan and trade
```

---

# Tech Stack

## AI

- Google ADK
- Gemini 3

## Backend

- Python 3.11
- FastAPI
- Streamlit

## Quant

- Pandas
- Numpy
- Pandas-ta
- yfinance

## Visualization

- Plotly

## Storage

- JSON portfolio memory

---

# Project Structure

```
GDG_HACKFEST/

quant/
    data_fetcher.py
    indicators.py
    regime_classifier.py

agents/
    sentiment_agent.py
    bull_agent.py
    bear_agent.py
    cio_agent.py

risk/
    risk_engine.py

pipeline/
    orchestrator.py
    session_keys.py

tools/
    quant_tool.py
    risk_tool.py

utils/
    helpers.py

memory/
    portfolio.json

app.py
main.py
config.py
requirements.txt
```

---

# Setup

## 1 — Install

```
pip install -r requirements.txt
```

---

## 2 — Create .env

```
GOOGLE_API_KEY=YOUR_API_KEY
```

---

## 3 — Run ADK

```
adk web
```

---

## 4 — Run Dashboard

```
streamlit run app.py
```

---

# Why This Project Stands Out

Most hackathon projects build:

- Chatbots
- Simple wrappers
- Single-step tools

This project demonstrates:

- Multi-agent orchestration
- Deterministic AI guardrails
- Quantitative models
- Risk-managed AI
- Production architecture
- Observability
- Real workflow automation

This is **an actual AI command center.**

---

# HackFest 2026

Built for:

**GDG Chennai HackFest 2026**

Focus:

**Autonomous AI Agents solving real workflows**