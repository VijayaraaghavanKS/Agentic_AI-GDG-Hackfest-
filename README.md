# 📈 Stock Market AI Trading Agent
### GDG Hackfest 2026 · Autonomous Multi-Agent System for NSE/BSE Equities

> Built with **Google Agent Development Kit (ADK)**, **Gemini 2.5 Flash**, **Vertex AI**, and **Streamlit**.  
> A fully modular, hackathon-ready boilerplate that lets two developers work on separate agents simultaneously without merge conflicts.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Pipeline Flow](#3-agent-pipeline-flow)
4. [Shared Whiteboard (session.state)](#4-shared-whiteboard-sessionstate)
5. [Folder Structure](#5-folder-structure)
6. [File-by-File Reference](#6-file-by-file-reference)
   - [config.py](#configpy)
   - [agents/agent.py](#agentsagentpy)
   - [agents/researcher.py](#agentsresearcherpy)
   - [agents/analyst.py](#agentsanalystpy)
   - [agents/decision_maker.py](#agentsdecision_makerpy)
   - [tools/market_tools.py](#toolsmarket_toolspy)
   - [tools/search_tools.py](#toolssearch_toolspy)
   - [utils/helpers.py](#utilshelperspy)
   - [main.py](#mainpy)
   - [app.py](#apppy)
7. [Pipeline Modes](#7-pipeline-modes)
8. [Authentication & Setup](#8-authentication--setup)
9. [Running the System](#9-running-the-system)
10. [Streamlit Dashboard](#10-streamlit-dashboard)
11. [ADK Developer Console](#11-adk-developer-console)
12. [Environment Variables Reference](#12-environment-variables-reference)
13. [Adding New Agents or Tools](#13-adding-new-agents-or-tools)
14. [Technical Indicators Reference](#14-technical-indicators-reference)
15. [Team Collaboration Guide](#15-team-collaboration-guide)
16. [Roadmap / TODO](#16-roadmap--todo)
17. [Tech Stack](#17-tech-stack)

---

## 1. What This System Does

This is an **autonomous multi-agent trading system** that analyses Indian equities (NSE/BSE) and produces structured **BUY / SELL / HOLD** recommendations. It does not execute trades — it produces recommendations with rationale, confidence scores, target prices, and stop-loss levels.

The pipeline runs three AI agents in sequence (or partially in parallel):

| Agent | Role |
|---|---|
| **Researcher** | Searches live news and rates market sentiment per ticker (BULLISH / BEARISH / NEUTRAL) using Google Search Grounding |
| **Analyst** | Fetches real-time OHLCV price data and computes RSI, MACD, and Moving Averages |
| **DecisionMaker** | Synthesises research + technical signals → final BUY/SELL/HOLD with risk management rules |

Results are viewable via a **Streamlit dashboard** or the **ADK developer console**.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User / Streamlit UI                         │
│              (app.py  OR  adk web .  OR  main.py)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │  user message: "Analyse RELIANCE.NS, TCS.NS ..."
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ADK Runner + InMemorySession                  │
│              (orchestrates agents, manages session.state)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TradingPipeline                              │
│              SequentialAgent (or ParallelAgent)                  │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│   │  Researcher  │───▶│   Analyst    │───▶│  DecisionMaker   │  │
│   │  LlmAgent    │    │  LlmAgent    │    │  LlmAgent        │  │
│   └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘  │
│          │                   │                     │             │
│          │ google_search     │ get_price_data      │ (synthesis) │
│          │ (grounding)       │ get_rsi             │             │
│          │                   │ get_macd            │             │
│          │                   │ get_moving_averages │             │
└──────────┼───────────────────┼─────────────────────┼────────────┘
           │                   │                     │
           ▼                   ▼                     ▼
    session.state["research_output"]
                        session.state["technical_signals"]
                                             session.state["trade_decision"]
```

All three agents communicate exclusively through **`session.state`** — the shared whiteboard. No direct function calls between agents.

---

## 3. Agent Pipeline Flow

### Sequential Mode (default)

```
User Input
    │
    ▼
┌───────────────────────────────────────────────────────────┐
│  STEP 1 – Researcher                                       │
│  • Triggers Google Search Grounding for each ticker       │
│  • Rates sentiment: BULLISH / BEARISH / NEUTRAL           │
│  • Writes → session.state["research_output"]              │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│  STEP 2 – Analyst                                          │
│  • Reads ← session.state["research_output"]               │
│  • Calls get_price_data() via yfinance                    │
│  • Calls get_rsi()   → 14-day RSI + interpretation        │
│  • Calls get_macd()  → MACD line, signal, histogram       │
│  • Calls get_moving_averages() → SMA-20, SMA-50, trend    │
│  • Writes → session.state["technical_signals"]            │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│  STEP 3 – DecisionMaker                                    │
│  • Reads ← session.state["technical_signals"]             │
│  • Applies risk rules (RSI > 65 + BEARISH = no BUY)       │
│  • Produces per-ticker: action, confidence, target,       │
│    stop-loss, rationale, risk_flag                        │
│  • Produces PORTFOLIO_SUMMARY (RISK-ON/OFF/NEUTRAL)       │
│  • Writes → session.state["trade_decision"]               │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
                     Final Output
              (Streamlit table / CLI print)
```

### Parallel Mode

```
User Input
    │
    ├──────────────────────────────┐
    ▼                              ▼
┌──────────────┐         ┌──────────────────┐
│  Researcher  │         │     Analyst      │
│  (runs       │         │  (runs           │
│   concurrently)        │   concurrently)  │
└──────┬───────┘         └────────┬─────────┘
       │                          │
       └──────────┬───────────────┘
                  ▼
         ┌────────────────┐
         │ DecisionMaker  │
         │ (waits for     │
         │  both above)   │
         └───────┬────────┘
                 ▼
           Final Output
```

> Switch between modes by setting `PIPELINE_MODE = "sequential"` or `"parallel"` in [config.py](config.py).

---

## 4. Shared Whiteboard (session.state)

The ADK `session.state` dictionary is the **only** communication channel between agents. It acts like a shared whiteboard that every agent can read from and write to.

```
session.state
├── "research_output"     (str)  ← written by Researcher, read by Analyst
├── "technical_signals"   (str)  ← written by Analyst, read by DecisionMaker
└── "trade_decision"      (str)  ← written by DecisionMaker, read by UI/main
```

These keys are defined as constants in [config.py](config.py) to prevent typos:

```python
KEY_RESEARCH_OUTPUT   = "research_output"
KEY_TECHNICAL_SIGNALS = "technical_signals"
KEY_TRADE_DECISION    = "trade_decision"
```

Each agent uses `output_key=KEY_<NAME>` in its `LlmAgent` definition to automatically write its final response into the correct state slot. Downstream agents receive the value injected into their prompt via `{key_name}` template substitution — handled automatically by the ADK runtime.

---

## 5. Folder Structure

```
Agentic_AI-GDG-Hackfest-/
│
├── agents/                         ← All AI agents
│   ├── agent.py                    ← ADK entry point (root_agent for adk web)
│   ├── researcher.py               ← Agent 1: News + sentiment (Team Member A)
│   ├── analyst.py                  ← Agent 2: Technical indicators (Team Member B)
│   ├── decision_maker.py           ← Agent 3: BUY/SELL/HOLD decisions
│   └── __init__.py                 ← Clean exports
│
├── tools/                          ← ADK-compatible Python tools
│   ├── market_tools.py             ← yfinance: price data, RSI, MACD, SMAs
│   ├── search_tools.py             ← Query builders for Google Search
│   └── __init__.py
│
├── utils/                          ← Shared utilities
│   ├── helpers.py                  ← State printer, decision parser, formatters
│   └── __init__.py
│
├── config.py                       ← Single source of truth (keys, tickers, modes)
├── main.py                         ← CLI runner + async pipeline executor
├── app.py                          ← Streamlit dashboard
│
├── requirements.txt                ← All Python dependencies
├── .env                            ← Your secrets (gitignored)
├── .env.example                    ← Template for .env
└── .gitignore
```

---

## 6. File-by-File Reference

### `config.py`

The single source of truth for all configuration. **All team members import from here. Nobody hardcodes values in agent files.**

| Constant | Type | Description |
|---|---|---|
| `GEMINI_MODEL` | `str` | Model string passed to all `LlmAgent` instances. Default: `gemini-2.5-flash` |
| `GOOGLE_CLOUD_PROJECT` | `str` | GCP project ID for Vertex AI billing |
| `GOOGLE_CLOUD_LOCATION` | `str` | Vertex AI region. Default: `us-central1` |
| `WATCH_LIST` | `list[str]` | Tickers to analyse. Edit here to add/remove stocks |
| `TARGET_EXCHANGE` | `str` | `"NSE"`, `"BSE"`, or `"NASDAQ"` |
| `DEFAULT_PERIOD` | `str` | yfinance lookback period, e.g. `"6mo"` |
| `DEFAULT_INTERVAL` | `str` | yfinance candle interval, e.g. `"1d"` |
| `KEY_RESEARCH_OUTPUT` | `str` | `"research_output"` — state key for Researcher output |
| `KEY_TECHNICAL_SIGNALS` | `str` | `"technical_signals"` — state key for Analyst output |
| `KEY_TRADE_DECISION` | `str` | `"trade_decision"` — state key for DecisionMaker output |
| `PIPELINE_MODE` | `str` | `"sequential"` or `"parallel"` |
| `AGENT_TEMPERATURE` | `float` | LLM temperature. `0.2` = deterministic |
| `MAX_OUTPUT_TOKENS` | `int` | Max tokens per agent response |

Also sets `GOOGLE_GENAI_USE_VERTEXAI=true` as an OS environment variable to route all SDK calls to Vertex AI.

---

### `agents/agent.py`

The **ADK entry point**. The `adk web` and `adk run` CLI commands look for a variable named `root_agent` inside `agents/agent.py`.

- Imports all three specialist agents and wires them into a `SequentialAgent` or `ParallelAgent` based on `PIPELINE_MODE` from `config.py`.
- Exposes `root_agent` at module level for the ADK runtime to discover.

```python
# Internally calls:
root_agent = _build_root_agent()   # returns SequentialAgent or ParallelAgent
```

---

### `agents/researcher.py`

**Owner: Team Member A**

| Property | Value |
|---|---|
| ADK type | `LlmAgent` |
| Model | `GEMINI_MODEL` from config |
| Tools | `[google_search]` — built-in ADK grounding tool |
| Output key | `"research_output"` |

**What it does:**
1. Iterates over `WATCH_LIST`
2. Uses **Google Search Grounding** to find news from the last 24 hours for each ticker
3. Identifies earnings, regulatory changes, macro events
4. Rates each ticker: `BULLISH | BEARISH | NEUTRAL` with a confidence score
5. Returns a structured `RESEARCH_REPORT:` text block

**How Search Grounding works:**  
Simply passing `tools=[google_search]` to `LlmAgent` enables it. The model autonomously decides when to call a live Google Search during its chain-of-thought reasoning. No manual tool call code is needed.

**Output format written to `session.state["research_output"]`:**
```
RESEARCH_REPORT:
  - ticker: RELIANCE.NS
    headline: Reliance Q3 earnings beat estimates by 12%
    sentiment: BULLISH
    confidence: HIGH
    notes: Record EBITDA driven by O2C segment; JIO added 8M subscribers.
```

---

### `agents/analyst.py`

**Owner: Team Member B**

| Property | Value |
|---|---|
| ADK type | `LlmAgent` |
| Model | `GEMINI_MODEL` from config |
| Tools | `[get_price_data, get_rsi, get_macd, get_moving_averages]` |
| Input | `session.state["research_output"]` (injected into prompt) |
| Output key | `"technical_signals"` |

**What it does:**
1. Receives the Researcher's report via `{research_output}` template injection
2. For each ticker, autonomously calls the four technical tools from `tools/market_tools.py`
3. Interprets signals using quantitative rules
4. Returns a structured `TECHNICAL_SIGNALS:` block

**Signal interpretation rules:**
| Signal | Condition | Interpretation |
|---|---|---|
| RSI | > 70 | Overbought — caution |
| RSI | < 30 | Oversold — potential opportunity |
| MACD | Line > Signal line | BULLISH crossover |
| MACD | Line < Signal line | BEARISH crossover |
| Price vs SMA | Price > SMA-20 > SMA-50 | UPTREND |
| Price vs SMA | Price < SMA-20 < SMA-50 | DOWNTREND |

**Output format written to `session.state["technical_signals"]`:**
```
TECHNICAL_SIGNALS:
  - ticker: RELIANCE.NS
    rsi: 58.3
    macd_signal: BULLISH
    ma_trend: UPTREND
    combined_sentiment: BULLISH
    suggested_action: BUY
```

---

### `agents/decision_maker.py`

**Owner: Team Member A or B**

| Property | Value |
|---|---|
| ADK type | `LlmAgent` |
| Model | `GEMINI_MODEL` from config |
| Tools | None (synthesis only; TODO: add portfolio exposure tool) |
| Input | `session.state["technical_signals"]` (injected into prompt) |
| Output key | `"trade_decision"` |

**What it does:**
1. Receives the Analyst's signals via `{technical_signals}` template injection
2. Applies hard-coded risk rules before issuing recommendations
3. Produces a final structured decision per ticker
4. Adds a `PORTFOLIO_SUMMARY` with market stance

**Risk rules applied:**
- `NEVER` recommend BUY if sentiment is BEARISH **and** RSI > 65
- Flag `risk_flag: YES` if confidence is LOW on both research and technicals
- Prefer HOLD over BUY/SELL when signals conflict

**Output format written to `session.state["trade_decision"]`:**
```
TRADE_DECISION:
  - ticker: RELIANCE.NS
    action: BUY
    confidence: HIGH
    target_price: ₹1,520
    stop_loss: ₹1,380
    rationale: Strong earnings beat + MACD bullish crossover confirm momentum.
    risk_flag: NO

PORTFOLIO_SUMMARY:
  stance: RISK-ON
```

---

### `tools/market_tools.py`

ADK-compatible Python tools — plain functions that the Analyst agent calls autonomously. The ADK auto-generates a JSON schema from type hints and docstrings; the model reads the docstring to decide when to invoke each tool.

| Function | Data Source | Returns |
|---|---|---|
| `get_price_data(ticker)` | yfinance | Latest close, OHLCV summary, last 10 closes |
| `get_rsi(ticker, period=14)` | yfinance (3mo daily) | RSI value + "Overbought / Oversold / Neutral" |
| `get_macd(ticker, fast=12, slow=26, signal=9)` | yfinance (6mo daily) | MACD line, signal line, histogram, crossover direction |
| `get_moving_averages(ticker)` | yfinance (6mo daily) | SMA-20, SMA-50, current price, trend (UPTREND/DOWNTREND/SIDEWAYS) |

All functions return a `dict` with an `"error"` key on failure — the model handles failures gracefully.

**Adding a new tool:**
```python
def my_new_tool(ticker: str) -> dict:
    """One-line description the model reads to decide when to call this."""
    # implementation
    return {"ticker": ticker, "result": value}
```
Then add it to `analyst_agent`'s `tools=[...]` list in `agents/analyst.py`.

---

### `tools/search_tools.py`

Utility helpers for constructing optimised Google Search query strings. These are **not** the grounding mechanism — they just build clean query strings.

| Function | Description |
|---|---|
| `format_search_query(ticker, query_type)` | Builds a ticker-specific news/earnings/sentiment query |
| `build_macro_query(topic)` | Builds India/global/RBI/Fed macro queries |

---

### `utils/helpers.py`

Shared utilities used by both the CLI (`main.py`) and the Streamlit UI (`app.py`).

| Function | Description |
|---|---|
| `pretty_print_state(state)` | Pretty-prints the full `session.state` to stdout for debugging |
| `extract_decisions_from_state(state)` | Parses the `trade_decision` text block into a list of dicts for the UI table |
| `format_currency_inr(value)` | Formats a float as `₹1,234.56` |
| `get_action_colour(action)` | Returns hex colour for BUY (green), SELL (red), HOLD (amber) |

---

### `main.py`

The async CLI entry point and reusable pipeline executor.

**Key components:**

- `build_pipeline(mode)` — factory function that returns a `SequentialAgent` or `ParallelAgent` based on `PIPELINE_MODE`
- `run_pipeline(tickers)` — async function that creates a session, runs the pipeline, streams events, and returns the final `session.state` dict
- CLI argument parser — supports `--tickers` and `--mode` overrides

**Usage:**
```bash
# Default watch list, sequential mode
python main.py

# Custom tickers
python main.py --tickers TCS.NS INFY.NS WIPRO.NS

# Parallel mode for this run only
python main.py --mode parallel

# Single ticker
python main.py --tickers HDFC.NS
```

**Output:**
```
============================================================
 PIPELINE MODE : SEQUENTIAL
 WATCH LIST    : RELIANCE.NS, TCS.NS, INFY.NS
============================================================

[Researcher] ✓ Complete
[Analyst] ✓ Complete
[DecisionMaker] ✓ Complete

 FINAL TRADE DECISIONS
----------------------------------------
  RELIANCE.NS     BUY    (conf: HIGH)
    → Strong earnings beat + MACD bullish crossover confirm momentum.
  TCS.NS          HOLD   (conf: MEDIUM)
    → Sideways trend, conflicting signals.
```

---

### `app.py`

The Streamlit web dashboard.

**Sidebar controls:**
- **Ticker multiselect** — pre-loaded from `WATCH_LIST`, supports custom ticker input
- **Pipeline mode radio** — Sequential or Parallel
- **Run Analysis button** — triggers the pipeline

**Main panel:**
- Colour-coded trade decisions table (green BUY / red SELL / amber HOLD)
- Three expandable panels showing raw agent outputs:
  - Researcher Output
  - Analyst Signals
  - DecisionMaker Output (full whiteboard inspection)

**Run:**
```bash
streamlit run app.py
```

---

## 7. Pipeline Modes

| Mode | Description | Use When |
|---|---|---|
| `sequential` | Researcher → Analyst → DecisionMaker, strictly one at a time | Default; most reliable; Analyst reads Researcher output |
| `parallel` | Researcher + Analyst run simultaneously, then DecisionMaker | When speed matters; note Analyst won't have Researcher's output |

Change in [config.py](config.py):
```python
PIPELINE_MODE: str = "sequential"   # or "parallel"
```

Or override for a single CLI run:
```bash
python main.py --mode parallel
```

---

## 8. Authentication & Setup

This project uses **Vertex AI** via **Application Default Credentials (ADC)** — no API keys.

### One-time setup (per machine)

**Step 1: Install Google Cloud SDK** (if not already installed)
```powershell
winget install Google.CloudSDK
# Open a new terminal after installation
```

**Step 2: Authenticate**
```bash
gcloud auth application-default login
```
A browser window opens → sign in with the Google account that owns your GCP project → click Allow.  
Credentials are saved to:
```
Windows: C:\Users\<you>\AppData\Roaming\gcloud\application_default_credentials.json
Linux/Mac: ~/.config/gcloud/application_default_credentials.json
```

**Step 3: Set quota project**
```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

**Step 4: Enable Vertex AI API**
```bash
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

**Step 5: Configure `.env`**
```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
```

### Verify authentication
```bash
gcloud auth application-default print-access-token
# Should print a long token string
```

---

## 9. Running the System

### Prerequisites
```bash
# 1. Activate virtual environment (Python 3.11.9)
.\.venv\Scripts\Activate.ps1          # Windows PowerShell
source .venv/bin/activate              # Linux/Mac

# 2. Install dependencies (first time only)
uv pip install -r requirements.txt

# 3. Configure .env (copy from template)
Copy-Item .env.example .env
# Edit .env with your GCP project ID
```

### CLI
```bash
python main.py
python main.py --tickers INFY.NS TCS.NS
python main.py --mode parallel
```

### Streamlit Dashboard
```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### ADK Developer Console
```bash
adk web .
# Opens at http://localhost:8000
# Full conversation UI with agent trace, session state inspector, tool call logs
```

### ADK Headless Run
```bash
adk run agents
```

---

## 10. Streamlit Dashboard

```
┌──────────────────────────────────────────────────────────┐
│  Sidebar                │  Main Panel                    │
│  ─────────────────────  │  ───────────────────────────── │
│  [x] RELIANCE.NS        │  📊 Trade Decisions            │
│  [x] TCS.NS             │  ┌────────┬──────┬──────────┐  │
│  [ ] INFY.NS            │  │Ticker  │Action│Confidence│  │
│  [ ] HDFCBANK.NS        │  ├────────┼──────┼──────────┤  │
│  [ ] WIPRO.NS           │  │REL.NS  │ BUY  │  HIGH    │  │
│                         │  │TCS.NS  │ HOLD │  MEDIUM  │  │
│  Custom: [________]     │  └────────┴──────┴──────────┘  │
│                         │                                 │
│  ○ Sequential           │  🧠 Agent Outputs               │
│  ● Parallel             │  [Researcher ▼] [Analyst ▼]    │
│                         │  [DecisionMaker ▼]              │
│  [🚀 Run Analysis]      │                                 │
└──────────────────────────────────────────────────────────┘
```

---

## 11. ADK Developer Console

Running `adk web .` opens a full-featured developer UI at `http://localhost:8000`:

- **Chat interface** — send messages to the pipeline interactively
- **Agent trace panel** — see each agent's reasoning steps
- **Tool call inspector** — see every `get_rsi()`, `get_macd()` call with arguments and return values
- **Session state viewer** — inspect the full shared whiteboard live
- **Event stream** — raw ADK events for debugging

---

## 12. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | ✅ Yes | — | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | No | `us-central1` | Vertex AI region |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | `true` (set in config.py) | Routes SDK to Vertex AI |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Override the model string |

**Available Vertex AI models** (verified against your project):
```
gemini-2.5-flash              ← default, recommended
gemini-2.5-flash-lite         ← cheaper, faster
gemini-3-flash-preview        ← latest preview
gemini-3-pro-preview          ← most capable
gemini-2.5-flash-lite         ← budget option
```

---

## 13. Adding New Agents or Tools

### Adding a new agent

1. Create `agents/my_new_agent.py`:
```python
from google.adk.agents import LlmAgent
from config import GEMINI_MODEL

my_agent = LlmAgent(
    name="MyAgent",
    model=GEMINI_MODEL,
    instruction="Your instruction here. Read {previous_output} from state.",
    output_key="my_output_key",
    tools=[],
)
```

2. Export it in `agents/__init__.py`:
```python
from .my_new_agent import my_agent
```

3. Add it to the pipeline in `agents/agent.py` and `main.py`:
```python
SequentialAgent(
    name="TradingPipeline",
    sub_agents=[researcher_agent, analyst_agent, my_agent, decision_agent],
)
```

4. Add its state key to `config.py`:
```python
KEY_MY_OUTPUT: str = "my_output_key"
```

### Adding a new tool

1. Add a function to `tools/market_tools.py`:
```python
def get_volatility(ticker: str) -> dict:
    """Calculate 30-day historical volatility for a stock ticker."""
    # implementation using yfinance
    return {"ticker": ticker, "volatility": value}
```

2. Register it in `tools/__init__.py` and add it to the relevant agent's `tools=[...]` list.

---

## 14. Technical Indicators Reference

### RSI (Relative Strength Index)
- **Period**: 14 days
- **Formula**: $RSI = 100 - \frac{100}{1 + RS}$ where $RS = \frac{\text{Avg Gain}}{\text{Avg Loss}}$
- **> 70**: Overbought — potential reversal down
- **< 30**: Oversold — potential reversal up
- **30–70**: Neutral zone

### MACD (Moving Average Convergence Divergence)
- **Fast EMA**: 12 days
- **Slow EMA**: 26 days
- **Signal Line**: 9-day EMA of the MACD line
- **Histogram**: MACD line − Signal line
- **Bullish**: MACD line crosses above signal line
- **Bearish**: MACD line crosses below signal line

### Simple Moving Averages
- **SMA-20**: Short-term trend
- **SMA-50**: Medium-term trend
- **Price > SMA-20 > SMA-50**: Strong uptrend
- **Price < SMA-20 < SMA-50**: Strong downtrend

---

## 15. Team Collaboration Guide

This project is structured so two developers can work on different files simultaneously with **zero merge conflicts**:

| Developer A owns | Developer B owns |
|---|---|
| `agents/researcher.py` | `agents/analyst.py` |
| `agents/decision_maker.py` | `tools/market_tools.py` |
| `app.py` (UI layer) | `utils/helpers.py` |

**Shared files** (coordinate before editing):
- `config.py` — add new constants, don't rename existing ones
- `agents/agent.py` — update pipeline wiring when adding agents
- `agents/__init__.py` — add new exports
- `requirements.txt` — add new packages

**Branch strategy recommendation:**
```
main          ← stable, demo-ready
feature/researcher-agent      ← Developer A
feature/analyst-tools         ← Developer B
```

---

## 16. Roadmap / TODO

### In Progress
- [ ] `check_portfolio_exposure()` tool in `tools/market_tools.py`
- [ ] `send_trade_alert()` notification tool (Telegram / email)
- [ ] Pydantic output schema for `extract_decisions_from_state()` (currently simple line parser)

### Planned
- [ ] F&O data tool (options chain, Put-Call Ratio)
- [ ] ATR (Average True Range) volatility tool
- [ ] Persistent session storage (replace `InMemorySessionService` with DB-backed)
- [ ] Cross-session memory tool for trend recall
- [ ] Streamlit charts (candlestick chart per ticker using `plotly`)
- [ ] Portfolio allocation table (% capital per BUY signal)
- [ ] Backtesting module

---

## 17. Tech Stack

| Layer | Technology |
|---|---|
| **AI Runtime** | [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) |
| **LLM** | Gemini 2.5 Flash via Vertex AI |
| **Authentication** | Google Application Default Credentials (ADC) |
| **Cloud** | Google Cloud Vertex AI |
| **Market Data** | [yfinance](https://github.com/ranaroussi/yfinance) |
| **Web UI** | [Streamlit](https://streamlit.io) |
| **Python** | 3.11.9 (managed via `uv` venv) |
| **Package Manager** | [uv](https://github.com/astral-sh/uv) |
| **Key Libraries** | `google-adk`, `google-genai`, `pandas`, `numpy`, `python-dotenv` |

---

> **GDG Hackfest 2026** — Built in 24 hours. Stock Market AI Trading Agent.
