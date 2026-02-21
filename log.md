# Regime-Aware Trading Command Center — Change Log

> **Project:** GDG Hackfest 2026  
> **Architecture:** Hybrid Quant-Agent (Deterministic Handcuffs + ADK Brain)  
> **Started:** February 21, 2026  

---

## Current State

| Component | Status |
|---|---|
| `quant/` (Data Layer) | Scaffolded — stubs with `NotImplementedError` |
| `risk/` (Risk Layer) | Scaffolded — stubs with `NotImplementedError` |
| `pipeline/` (Orchestrator) | Scaffolded — stubs with `NotImplementedError` |
| `agents/` (4 ADK Agents) | Scaffolded — system prompts written, `output_key` wired |
| `tools/` (ADK Adapters) | Scaffolded — stubs with `NotImplementedError` |
| `config.py` | Complete — risk params, session keys, model config |
| `app.py` | Scaffolded — Streamlit layout with regime UI, debate panels, trade card |
| `main.py` | Scaffolded — CLI entry point wired to Orchestrator |
| `utils/helpers.py` | Complete — JSON parser, logger, formatters |
| **Core logic implementation** | **Not started** |

---

## Change History

### [2026-02-21] Session 1 — Full Architecture Refactor

#### 1. Architectural Plan
- Defined the Regime-Aware Trading Command Center philosophy.
- Designed the 6-step ADK pipeline: Quant → Sentiment → Bull → Bear → CIO → Risk.
- Mapped out the new folder structure with file-level responsibilities.

#### 2. Created `quant/` package (Deterministic Data Layer)
- **`quant/__init__.py`** — Package init exporting `fetch_ohlcv`, `compute_indicators`, `classify_regime`, `RegimeSnapshot`.
- **`quant/data_fetcher.py`** — Stub for yfinance OHLCV fetch with validation. Raises on empty/stale data.
- **`quant/indicators.py`** — Stub for 50DMA, 200DMA, ATR(14), RSI(14), MACD(12,26,9). Defines `IndicatorResult` dataclass.
- **`quant/regime_classifier.py`** — Stub for BULL/BEAR/NEUTRAL classification. Defines `Regime` enum, `RegimeSnapshot` dataclass with `.to_dict()`.

#### 3. Created `risk/` package (Deterministic Risk Layer)
- **`risk/__init__.py`** — Package init exporting `apply_risk_limits`, `ValidatedTrade`.
- **`risk/risk_engine.py`** — Stub for risk enforcement: ATR stop-loss override (`Entry − 1.5×ATR`), 1% position sizing, R:R validation, trade kill logic. Defines `ValidatedTrade` dataclass.

#### 4. Created `pipeline/` package (ADK Orchestration)
- **`pipeline/__init__.py`** — Package init exporting `Orchestrator`.
- **`pipeline/session_keys.py`** — 6 string constants for the ADK `InMemorySessionService` whiteboard: `KEY_QUANT_SNAPSHOT`, `KEY_SENTIMENT`, `KEY_BULL_THESIS`, `KEY_BEAR_THESIS`, `KEY_CIO_PROPOSAL`, `KEY_FINAL_TRADE`. Plus `ALL_KEYS` list.
- **`pipeline/orchestrator.py`** — Stub for the `Orchestrator` class that wires Steps 1→6 sequentially.

#### 5. Replaced `agents/` (old → new)
- **Deleted (logically replaced):** `researcher.py`, `analyst.py`, `decision_maker.py`.
- **Created `agents/sentiment_agent.py`** — Step 2: `LlmAgent` with Google Search grounding. Reads `KEY_QUANT_SNAPSHOT`, writes `KEY_SENTIMENT`.
- **Created `agents/bull_agent.py`** — Step 3: `LlmAgent` that builds aggressive bullish thesis. Reads quant + sentiment, writes `KEY_BULL_THESIS`.
- **Created `agents/bear_agent.py`** — Step 4: `LlmAgent` that tears apart bull thesis. Reads quant + sentiment + bull, writes `KEY_BEAR_THESIS`.
- **Created `agents/cio_agent.py`** — Step 5: `LlmAgent` that synthesises debate into JSON trade proposal. Reads all prior state, writes `KEY_CIO_PROPOSAL`.
- **Updated `agents/__init__.py`** — Now exports `sentiment_agent`, `bull_agent`, `bear_agent`, `cio_agent`.

#### 6. Replaced `tools/` (old → new)
- **`market_tools.py`** — Kept on disk but no longer imported (superseded by `quant/`).
- **Created `tools/quant_tool.py`** — Step 1 ADK adapter: wraps `quant/` pipeline, writes `RegimeSnapshot` to state.
- **Created `tools/risk_tool.py`** — Step 6 ADK adapter: wraps `risk/risk_engine.py`, enforces limits on CIO proposal.
- **`tools/search_tools.py`** — Kept as-is (query builders for sentiment agent).
- **Updated `tools/__init__.py`** — Now exports `quant_engine_tool`, `risk_enforcement_tool`, `format_search_query`, `build_macro_query`.

#### 7. Updated `config.py`
- Renamed docstring to "Regime-Aware Trading Command Center".
- Changed `GEMINI_MODEL` default: `"gemini-3.0-flash"` → `"gemini-1.5-pro"`.
- Changed `DEFAULT_PERIOD`: `"6mo"` → `"1y"` (needed for 200DMA lookback).
- **Added risk constants:** `MAX_RISK_PCT = 0.01`, `ATR_STOP_MULTIPLIER = 1.5`, `MIN_RISK_REWARD = 1.5`, `DEFAULT_PORTFOLIO_EQUITY = 1_000_000.0`.
- Replaced old session keys (`KEY_RESEARCH_OUTPUT`, `KEY_TECHNICAL_SIGNALS`, `KEY_TRADE_DECISION`) with re-exports from `pipeline.session_keys`.
- Removed `PIPELINE_MODE` flag (pipeline is now always sequential via Orchestrator).

#### 8. Updated `utils/helpers.py`
- Removed `extract_decisions_from_state()` (obsolete — old pipeline parser).
- Added `setup_logger()` — standardised logger factory.
- Added `parse_cio_json()` — robust JSON extraction from CIO agent output (handles markdown fences, preamble text).
- Added `format_risk_reward()` — formats R:R ratios for display.
- Kept `pretty_print_state()`, `format_currency_inr()`, `get_action_colour()`.
- Updated `utils/__init__.py` exports.

#### 9. Updated `main.py`
- Rewrote to use `Orchestrator` for a single ticker (not multi-ticker batch).
- CLI now accepts `--ticker` (single) and `--equity` (portfolio size).
- Output prints the `ValidatedTrade` card or "TRADE KILLED" message.

#### 10. Updated `app.py`
- Rewrote Streamlit dashboard for Regime-Aware architecture.
- Sidebar: single ticker selector + portfolio equity input.
- Added `st.status()` for pipeline observability trace.
- Added regime metrics row (Regime, Close, 50DMA, ATR).
- Added 2-column debate panels: Sentiment, Bull, Bear, CIO.
- Added final trade advisory card with 8 metrics.
- Added TODO placeholder for Plotly price + regime overlay chart.

#### 11. Updated `requirements.txt`
- Added `plotly>=5.24.0` (for future price charts).
- Added `pandas-ta>=0.3.14b1` (technical indicator library).

### [2026-02-21] Session 1 — Model Update
- **`config.py`** — Changed `GEMINI_MODEL` default: `"gemini-1.5-pro"` → `"gemini-3-flash-preview"`.
- **`app.py`** — Changed sidebar caption: `"Powered by Gemini 1.5 Pro + Google ADK"` → `"Powered by Gemini 3 Flash Preview + Google ADK"`.

### [2026-02-21] Session 1 — Virtual Environment Setup (Python 3.11.9)
- **`.venv/`** — Recreated with Python 3.11.9 using `py -3.11 -m venv .venv --clear`.
- **`venv/`** — Was created empty/broken earlier; `.venv/` is the canonical venv folder.
- Upgraded pip: 24.0 → 26.0.1.
- Installed all 13 dependencies into `.venv/`.
- **`pandas-ta`** → replaced with **`ta>=0.11.0`** (pandas-ta requires Python 3.12+ on PyPI, repo is gone from GitHub). The `ta` library provides identical indicators (RSI, MACD, ATR, SMA/EMA, Bollinger Bands).
- **`requirements.txt`** — Changed `pandas-ta>=0.3.14b1` → `ta>=0.11.0`.
- **`test_environment.py`** — Changed `pandas_ta` import → `ta` import.
- All 13 packages verified: `python test_environment.py` → "Environment setup successful! 🎯"

---

## Obsolete Files (still on disk, safe to delete)
- `agents/researcher.py` — replaced by `sentiment_agent.py`
- `agents/analyst.py` — replaced by `quant/` + `bull_agent.py` + `bear_agent.py`
- `agents/decision_maker.py` — replaced by `cio_agent.py` + `risk/risk_engine.py`
- `tools/market_tools.py` — replaced by `quant/indicators.py` + `quant/data_fetcher.py`

---

## Next Steps (TODO)
- [ ] Implement `quant/data_fetcher.py` — yfinance fetch logic
- [ ] Implement `quant/indicators.py` — DMA, ATR, RSI, MACD math
- [ ] Implement `quant/regime_classifier.py` — BULL/BEAR/NEUTRAL rules
- [ ] Implement `risk/risk_engine.py` — stop-loss override + 1% sizing
- [ ] Implement `tools/quant_tool.py` — wire quant pipeline as ADK tool
- [ ] Implement `tools/risk_tool.py` — wire risk engine as ADK tool
- [ ] Implement `pipeline/orchestrator.py` — ADK InMemorySessionService + 6-step sequencing
- [ ] Add Plotly chart to `app.py` — OHLCV candles + DMA lines + regime colour bands
- [ ] Delete obsolete files (`researcher.py`, `analyst.py`, `decision_maker.py`, `market_tools.py`)
- [ ] Create `.env.example` template
