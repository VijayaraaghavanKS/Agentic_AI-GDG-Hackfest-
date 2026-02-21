# Regime-Aware Trading Command Center — Change Log

> **Project:** GDG Hackfest 2026  
> **Architecture:** Hybrid Quant-Agent (Deterministic Handcuffs + ADK Brain)  
> **Started:** February 21, 2026  

---

## Current State

| Component | Status |
|---|---|
| `quant/data_fetcher.py` | **Complete** — `MarketData` dataclass + `fetch_ohlcv` (11-step pipeline) + `fetch_multiple` + `fetch_nifty` + `fetch_banknifty` |
| `quant/indicators.py` | **Complete** — `IndicatorSet` dataclass + `compute_indicators` (12-step pipeline) + RSI/ATR/SMA/EMA/Vol/Mom/Trend + `IndicatorResult` compat alias |
| `test_indicators.py` | **Complete** — 4 integration tests (single, multiple, index, failure) — ALL PASSED |
| `quant/regime_classifier.py` | **Complete** — `RegimeSnapshot` frozen dataclass + `classify_regime` (4-step pipeline) + BULL/BEAR/NEUTRAL deterministic rules |
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

### [2026-02-21] Session 2 — Implemented `quant/data_fetcher.py` (Layer 1: Deterministic Quant Engine)

#### 1. `MarketData` Dataclass
- Created `MarketData` frozen dataclass with `slots=True` — immutable container for validated OHLCV data.
- Fields: `ticker`, `dataframe`, `last_updated` (UTC datetime), `rows`, `period`, `interval`.
- Custom `__repr__` for readable logging output.

#### 2. `fetch_ohlcv()` — Primary Entry-Point (11-Step Pipeline)
- **Step 0** — Ticker normalisation via `_normalise_ticker()`: bare `RELIANCE` → `RELIANCE.NS`, index `^NSEI` untouched, already-suffixed tickers pass through.
- **Step 1** — `yf.download()` wrapped in try/except → raises `RuntimeError` on network/yfinance failure.
- **Step 2** — Empty DataFrame check → raises `ValueError` with actionable message.
- **Step 3** — `_standardise_columns()`: flattens MultiIndex columns (yfinance ≥ 0.2.50 quirk), lowercases via `str(c).strip().lower()` to handle non-string labels.
- **Step 4** — `_validate_columns()`: asserts `[open, high, low, close, volume]` exist.
- **Step 5** — Retains only OHLCV columns (drops adj_close, dividends, etc.).
- **Step 6** — `_drop_nans()`: drops NaN rows with division-by-zero guard on percentage logging.
- **Step 7** — `_validate_row_count()`: enforces minimum 200 rows.
- **Step 8** — `df.sort_index()`: ensures ascending time order (Yahoo sometimes returns unsorted).
- **Step 9** — `_validate_freshness()`: last candle must be within 10 days of now; all comparisons in UTC via `_to_utc_timestamp()` helper.
- **Step 10** — `df.copy()`: defensive copy prevents mutation leaking into frozen dataclass.
- **Step 11** — Builds and returns immutable `MarketData` instance.

#### 3. `fetch_multiple()` — Batch Fetch
- Iterates over a sequence of tickers, calls `fetch_ohlcv()` for each.
- Failed tickers are logged via `logger.warning()` and skipped — returns partial results instead of aborting.

#### 4. `fetch_nifty()` / `fetch_banknifty()` — Convenience Wrappers
- `fetch_nifty()` → fetches `^NSEI` (NIFTY 50 index).
- `fetch_banknifty()` → fetches `^NSEBANK` (BANK NIFTY index).

#### 5. Constants
- `REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]`
- `MIN_ROWS = 200` (needed for 200DMA lookback)
- `FRESHNESS_DAYS = 10` (max staleness before raising)
- `_NIFTY_50 = "^NSEI"`, `_BANK_NIFTY = "^NSEBANK"`, `_NSE_SUFFIX = ".NS"`

#### 6. Standalone Test (`__main__` block)
- Accepts optional ticker from CLI arg (defaults to `RELIANCE.NS`).
- Prints: ticker, rows, period, interval, last candle date, freshness in days, fetch timestamp, last 5 rows.
- Exits with code 1 on failure.

#### 7. Updated `quant/__init__.py`
- Now exports: `fetch_ohlcv`, `fetch_multiple`, `fetch_nifty`, `fetch_banknifty`, `MarketData`, `compute_indicators`, `classify_regime`, `RegimeSnapshot`.

#### 8. Verified
- `python -m quant.data_fetcher RELIANCE.NS` → 248 rows, last candle 2026-02-20.
- `python -m quant.data_fetcher RELIANCE` → auto-normalised to `RELIANCE.NS`, same result.

---

### [2026-02-21] Session 3 — Implemented `quant/indicators.py` (Layer 2: Technical Indicator Engine)

#### 1. `IndicatorSet` Dataclass
- Created `IndicatorSet` frozen dataclass with `slots=True` — immutable container for computed indicator snapshots.
- Fields: `ticker`, `rsi`, `atr`, `sma20`, `sma50`, `sma200`, `ema20`, `ema50`, `volatility`, `momentum_20d`, `trend_strength`, `price`, `timestamp`.
- Custom `__repr__` for readable logging output.
- Added backward-compatible alias: `IndicatorResult = IndicatorSet` (consumed by `regime_classifier.py`).

#### 2. `compute_indicators()` — Single Entry-Point (12-Step Pipeline)
- **Step 0** — Type guard: rejects non-`MarketData` input with `TypeError`.
- **Step 0b** — Defensive `df.sort_index()` (consistent with `data_fetcher.py`).
- **Step 1** — Input validation via `_validate_input()`: column check, minimum 200 rows, numeric dtype check, NaN check.
- **Step 2** — Extract `high`, `low`, `close` series.
- **Step 3** — RSI(14) via Wilder smoothing (`ewm(com=13)`).
- **Step 4** — ATR(14) via True Range → 14-day rolling mean.
- **Step 5** — SMA-20, SMA-50, SMA-200 via `np.mean()` on tail slice (fast path).
- **Step 6** — EMA-20, EMA-50 via `ewm(span=...)`.
- **Step 7** — Annualised volatility: `np.std(returns, ddof=1) × √252`.
- **Step 8** — 20-day momentum: `close[-1] / close[-21] − 1`.
- **Step 9** — Trend strength: `(price − sma50) / sma50`.
- **Step 10** — UTC timestamp from last candle.
- **Step 11** — Final sanity check: `math.isfinite()` on all numeric fields.
- **Step 12** — Assemble & return frozen `IndicatorSet`.

#### 3. Indicator Formulas (All Manual — No pandas-ta)
- **RSI**: Wilder smoothing via `ewm(com=period-1)`, gain/loss separation, RS → RSI.
- **ATR**: `max(H−L, |H−prev_C|, |L−prev_C|)` → 14-day rolling mean.
- **SMA**: `np.mean(close.values[-window:])` — numpy fast path.
- **EMA**: `ewm(span=N, min_periods=N).mean()` — standard decay `α = 2/(N+1)`.
- **Volatility**: `np.std(daily_returns, ddof=1) × √252` — numpy fast path.
- **Momentum**: `close[-1] / close[-21] − 1` — numpy indexing on `.values`.
- **Trend Strength**: `(price − sma50) / sma50`.

#### 4. Validation & Guards
- Column existence check.
- Minimum row count (≥ 200).
- Numeric dtype validation (`pd.api.types.is_numeric_dtype`).
- NaN detection on all OHLCV columns.
- Zero-ATR guard: raises `ValueError` if ATR is zero.
- Zero-volatility guard: raises `ValueError` if volatility is zero.
- Final `math.isfinite()` sweep on all indicator values before returning.

#### 5. Performance Optimisations
- SMA: `np.mean(close.values[-window:])` replaces `close.rolling(window).mean().iloc[-1]` (~3× faster).
- Volatility: `np.std(values, ddof=1)` replaces `pd.Series.std()` (~3× faster).
- Momentum: numpy array indexing replaces pandas `.iloc[]`.

#### 6. Constants & Parameters
- `REQUIRED_COLUMNS`, `MIN_ROWS = 200`.
- Indicator parameters block: `RSI_PERIOD = 14`, `ATR_PERIOD = 14`, `SMA_20/50/200`, `EMA_20/50`, `MOMENTUM_WINDOW = 20`, `ANNUALISATION_FACTOR = √252`.

#### 7. Standalone Test (`__main__` block)
- Fetches `RELIANCE` via `fetch_ohlcv()`, computes indicators, prints formatted output.
- Sections: Trend (SMA/EMA/Trend Strength), Momentum & Volatility (RSI/ATR/Vol/Mom).

---

### [2026-02-21] Session 3 — Refactored `quant/indicators.py` (Safe Refactor)

Applied 10 production-grade improvements (logic unchanged):

1. **Sort safety** — `df.sort_index()` before validation (defensive, consistent with `data_fetcher.py`).
2. **Numeric dtype validation** — `pd.api.types.is_numeric_dtype` on all OHLCV columns.
3. **Faster volatility** — `np.std(values, ddof=1)` replaces `pd.Series.std()`.
4. **Faster momentum** — `close.values` numpy indexing replaces `.iloc[]`.
5. **Faster SMA** — `np.mean(close.values[-window:])` replaces full `.rolling().mean()`.
6. **Zero volatility guard** — raises `ValueError` if volatility is zero.
7. **Zero ATR guard** — raises `ValueError` if ATR is zero.
8. **Type hint improvement** — `Final[Sequence[str]]` for `REQUIRED_COLUMNS`.
9. **Indicator Parameters header** — new section comment above `RSI_PERIOD`.
10. **Final sanity check** — `math.isfinite()` on all numeric fields before returning `IndicatorSet`.

---

### [2026-02-21] Session 3 — Backward Compatibility Fix

- **`quant/indicators.py`** — Added `IndicatorResult = IndicatorSet` alias so `regime_classifier.py` import continues to work.
- **`quant/regime_classifier.py`** — Updated import: `from .indicators import IndicatorSet, IndicatorResult`.

---

### [2026-02-21] Session 3 — Integration Test (`test_indicators.py`)

#### Created `test_indicators.py`
- **TEST 1** — Single ticker (`RELIANCE`): fetch → compute → validate indicator ranges.
- **TEST 2** — Multiple tickers (`RELIANCE`, `TCS`, `INFY`): batch fetch → compute each → validate.
- **TEST 3** — NIFTY index (`^NSEI`): fetch via `fetch_nifty()` → compute → validate.
- **TEST 4** — Failure case (`INVALIDTICKERXYZ`): confirms invalid ticker is rejected with exception.
- **Validation checks**: `price > 0`, `0 ≤ RSI ≤ 100`, `ATR > 0`, `volatility > 0`, `isfinite(trend_strength)`, `isfinite(momentum_20d)`.

#### Test Results (ALL PASSED)
| Test | Ticker | RSI | ATR | Volatility | Momentum | Status |
|------|--------|-----|-----|-----------|----------|--------|
| Single | RELIANCE.NS | 44.4 | 29.68 | 19.98% | +1.20% | ✓ |
| Multiple | RELIANCE.NS | 44.4 | 29.68 | 19.98% | +1.20% | ✓ |
| Multiple | TCS.NS | 27.0 | 100.89 | 21.22% | −14.73% | ✓ |
| Multiple | INFY.NS | 22.7 | 60.53 | 25.96% | −18.65% | ✓ |
| Index | ^NSEI | 47.8 | 315.87 | 11.76% | +1.11% | ✓ |
| Failure | INVALIDTICKERXYZ | — | — | — | — | ✓ Rejected |

---

### [2026-02-21] Session 4 — Implemented `quant/regime_classifier.py` (Layer 3: Market Regime Classifier)

#### 1. `RegimeSnapshot` Dataclass
- Created `RegimeSnapshot` frozen dataclass with `slots=True` — immutable container for classified market regime.
- Fields: `ticker`, `regime`, `price`, `sma50`, `sma200`, `rsi`, `volatility`, `trend_strength`, `timestamp`.
- Custom `__repr__` for readable logging output.
- Replaced old stub (which had `Regime` enum, MACD fields, `to_dict()`) with production-grade frozen dataclass matching `data_fetcher.py` / `indicators.py` style.

#### 2. `classify_regime()` — Single Entry-Point (4-Step Pipeline)
- **Step 1** — Input validation via `_validate_indicator_set()`: type check (`IndicatorSet`), price > 0, sma50 > 0, sma200 > 0.
- **Step 2** — Regime determination via `_determine_regime()`: pure deterministic rules.
- **Step 3** — Build frozen `RegimeSnapshot` from indicator values.
- **Step 4** — Log regime classification with key metrics.

#### 3. Regime Rules (Strict, Deterministic)
- **BULL**: `price > sma50 > sma200` AND `trend_strength > 0`.
- **BEAR**: `price < sma50 < sma200` AND `trend_strength < 0`.
- **NEUTRAL**: Everything else (mixed / transitional signals).
- No probabilities, no AI, no randomness — pure rule-based.

#### 4. Constants
- `REGIME_BULL = "BULL"`, `REGIME_BEAR = "BEAR"`, `REGIME_NEUTRAL = "NEUTRAL"`.
- `VALID_REGIMES = frozenset({BULL, BEAR, NEUTRAL})` — immutable.

#### 5. Validation & Guards
- Type guard: rejects non-`IndicatorSet` input with `TypeError`.
- Price, SMA50, SMA200 must all be > 0 — raises `ValueError` otherwise.
- `math.isfinite()` sweep on all numeric fields (price, sma50, sma200, rsi, volatility, trend_strength) — prevents NaN/Inf propagation.

#### 6. Standalone Test (`__main__` block)
- Fetches `RELIANCE` via `fetch_ohlcv()` → `compute_indicators()` → `classify_regime()`.
- Prints formatted output: ticker, regime, price, SMAs, RSI, volatility, trend strength.

#### 7. Verified
- `python -m quant.regime_classifier` → `RegimeSnapshot(RELIANCE.NS, regime=NEUTRAL, price=1419.40, sma50=1478.38, sma200=1449.36, ...)` ✓
- `python -m quant.indicators` → Still works ✓
- `python -m quant.data_fetcher` → Still works ✓

#### 8. Design Notes
- Input is `IndicatorSet` only — does NOT import `MarketData`.
- No external dependencies (no numpy, sklearn, pandas-ta, Gemini, ADK).
- Matches style of `data_fetcher.py` and `indicators.py`: docstrings, logging, constants, validation helpers, public API section, standalone test.

---

### [2026-02-21] Session 4 — Safe Refactor of `quant/regime_classifier.py`

Applied 3 production-grade improvements (logic unchanged):

1. **Finite number validation** — Added `math.isfinite()` sweep in `_validate_indicator_set()` on all 6 numeric fields (`price`, `sma50`, `sma200`, `rsi`, `volatility`, `trend_strength`). Prevents NaN/Inf propagation. Matches validation style in `quant/indicators.py`.
2. **Simplified ticker extraction** — Replaced `getattr(indicators, "ticker", "UNKNOWN")` with `indicators.ticker` since `_validate_indicator_set()` already type-checks the input.
3. **Immutable `VALID_REGIMES`** — Changed `set[str]` to `frozenset[str]` to prevent accidental mutation of the constant.

#### Verified
- `python -m quant.regime_classifier` → `RegimeSnapshot(RELIANCE.NS, regime=NEUTRAL, ...)` ✓ — identical output.

---

## Next Steps (TODO)
- [x] Implement `quant/data_fetcher.py` — yfinance fetch logic
- [x] Implement `quant/indicators.py` — RSI, ATR, SMA, EMA, Volatility, Momentum, Trend Strength
- [x] Integration test `data_fetcher` → `indicators` pipeline
- [x] Implement `quant/regime_classifier.py` — BULL/BEAR/NEUTRAL rules
- [ ] Implement `risk/risk_engine.py` — stop-loss override + 1% sizing
- [ ] Implement `tools/quant_tool.py` — wire quant pipeline as ADK tool
- [ ] Implement `tools/risk_tool.py` — wire risk engine as ADK tool
- [ ] Implement `pipeline/orchestrator.py` — ADK InMemorySessionService + 6-step sequencing
- [ ] Add Plotly chart to `app.py` — OHLCV candles + DMA lines + regime colour bands
- [ ] Delete obsolete files (`researcher.py`, `analyst.py`, `decision_maker.py`, `market_tools.py`)
- [ ] Create `.env.example` template
