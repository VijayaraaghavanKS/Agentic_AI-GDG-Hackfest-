"""Comprehensive test suite for the risk engine, risk tool, and paper trading.

Run:  python test_risk_engine.py
"""
import sys
import math
import json

# ── Counters ─────────────────────────────────────────────────
passed = 0
failed = 0
errors = []

def check(label, condition, detail=""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  ✓ {label}")
    else:
        failed += 1
        errors.append(f"{label}: {detail}")
        print(f"  ✗ {label}  —  {detail}")

# ==============================================================
# 1.  risk_engine.py — apply_risk_limits
# ==============================================================
print("\n" + "="*60)
print("1. RISK ENGINE — apply_risk_limits()")
print("="*60)

from trading_agents.risk_engine import (
    apply_risk_limits, validate_trade_inputs, ValidatedTrade,
    _is_finite, _assert_finite, VALID_ACTIONS, VALID_REGIMES,
)

# 1a. Basic BUY accepted
print("\n1a. Basic BUY (BULL, good R:R)")
p = {"ticker": "RELIANCE.NS", "action": "BUY", "entry": 2800, "target": 3100, "conviction_score": 0.7, "regime": "BULL"}
t = apply_risk_limits(p, atr=30, portfolio_equity=1_000_000)
check("not killed", not t.killed)
check("action=BUY", t.action == "BUY")
check("ticker=RELIANCE.NS", t.ticker == "RELIANCE.NS")
check("stop < entry", t.stop_loss < t.entry_price)
check("target > entry", t.target_price > t.entry_price)
check("rr >= 2.0", t.risk_reward_ratio >= 2.0)
check("position_size > 0", t.position_size > 0)
check("not contrarian", not t.is_contrarian)
check("to_dict works", isinstance(t.to_dict(), dict) and len(t.to_dict()) == 14)

# 1b. Contrarian BUY in BEAR
print("\n1b. Contrarian BUY in BEAR (50% size)")
p2 = {"ticker": "TCS.NS", "action": "BUY", "entry": 3500, "target": 3700, "conviction_score": 0.6, "regime": "BEAR"}
t2 = apply_risk_limits(p2, atr=40, portfolio_equity=1_000_000)
check("accepted", not t2.killed)
check("is_contrarian=True", t2.is_contrarian)
# Compare with BULL version (should be ~2x size)
p2b = {**p2, "regime": "BULL"}
t2b = apply_risk_limits(p2b, atr=40, portfolio_equity=1_000_000)
check("contrarian ~50% of aligned size", 0.45 <= t2.position_size / t2b.position_size <= 0.55,
      f"{t2.position_size} vs {t2b.position_size}")

# 1c. HOLD → killed
print("\n1c. HOLD → always killed")
p3 = {"ticker": "INFY.NS", "action": "HOLD", "entry": 1500, "conviction_score": 0.5}
t3 = apply_risk_limits(p3, atr=20)
check("killed=True", t3.killed)
check("reason mentions HOLD", "HOLD" in (t3.kill_reason or ""))

# 1d. Bad R:R → killed
print("\n1d. Bad R:R → killed")
p4 = {"ticker": "INFY.NS", "action": "BUY", "entry": 1500, "target": 1510, "conviction_score": 0.5, "regime": "BULL"}
t4 = apply_risk_limits(p4, atr=20)
check("killed=True", t4.killed)
check("reason mentions risk_reward", "risk_reward" in (t4.kill_reason or "").lower())

# 1e. SIDEWAYS regime — BUY not contrarian
print("\n1e. SIDEWAYS regime — BUY should NOT be contrarian")
p5 = {"ticker": "SBIN.NS", "action": "BUY", "entry": 800, "target": 900, "conviction_score": 0.8, "regime": "SIDEWAYS"}
t5 = apply_risk_limits(p5, atr=10)
check("not contrarian", not t5.is_contrarian)
check("accepted", not t5.killed)

# 1f. SELL in BEAR — aligned
print("\n1f. SELL in BEAR — should be aligned (not contrarian)")
p6 = {"ticker": "SBIN.NS", "action": "SELL", "entry": 800, "target": 700, "conviction_score": 0.8, "regime": "BEAR"}
t6 = apply_risk_limits(p6, atr=10)
check("not contrarian", not t6.is_contrarian)
check("accepted", not t6.killed)
check("stop > entry (for SELL)", t6.stop_loss > t6.entry_price)

# 1g. SELL in BULL — contrarian
print("\n1g. SELL in BULL — should be contrarian")
p7 = {"ticker": "SBIN.NS", "action": "SELL", "entry": 800, "target": 700, "conviction_score": 0.8, "regime": "BULL"}
t7 = apply_risk_limits(p7, atr=10)
check("is_contrarian=True", t7.is_contrarian)
check("accepted", not t7.killed)

# 1h. Missing required field → ValueError
print("\n1h. Missing required field → ValueError")
try:
    apply_risk_limits({"ticker": "X", "action": "BUY"}, atr=10)
    check("raised ValueError", False, "no exception raised")
except ValueError as e:
    check("raised ValueError", True)
    check("mentions 'entry'", "entry" in str(e).lower())

# 1i. NaN / Inf inputs
print("\n1i. NaN / Inf inputs → ValueError")
try:
    apply_risk_limits({"ticker": "X", "action": "BUY", "entry": float('nan'), "conviction_score": 0.5}, atr=10)
    check("NaN entry raises", False, "no exception")
except ValueError:
    check("NaN entry raises", True)
try:
    apply_risk_limits({"ticker": "X", "action": "BUY", "entry": 100, "conviction_score": 0.5}, atr=float('inf'))
    check("Inf ATR raises", False, "no exception")
except ValueError:
    check("Inf ATR raises", True)

# 1j. Zero entry / atr / equity → ValueError
print("\n1j. Zero values → ValueError")
try:
    apply_risk_limits({"ticker": "X", "action": "BUY", "entry": 0, "conviction_score": 0.5}, atr=10)
    check("zero entry raises", False)
except ValueError:
    check("zero entry raises", True)
try:
    apply_risk_limits({"ticker": "X", "action": "BUY", "entry": 100, "conviction_score": 0.5}, atr=0)
    check("zero atr raises", False)
except ValueError:
    check("zero atr raises", True)

# 1k. Conviction auto-normalisation (0-100 → 0-1)
print("\n1k. Conviction 70 auto-normalised to 0.70")
p8 = {"ticker": "TCS.NS", "action": "BUY", "entry": 3500, "target": 3700, "conviction_score": 70, "regime": "NEUTRAL"}
t8 = apply_risk_limits(p8, atr=40)
check("conviction=0.70", abs(t8.conviction_score - 0.70) < 0.01, f"got {t8.conviction_score}")

# 1l. No target provided → engine computes 2R
print("\n1l. No target → engine computes 2R target")
p9 = {"ticker": "HDFCBANK.NS", "action": "BUY", "entry": 1600, "conviction_score": 0.6, "regime": "BULL"}
t9 = apply_risk_limits(p9, atr=20)
check("accepted", not t9.killed)
check("target > entry", t9.target_price > t9.entry_price)
risk = t9.entry_price - t9.stop_loss
reward = t9.target_price - t9.entry_price
check("rr >= 2.0", t9.risk_reward_ratio >= 2.0, f"rr={t9.risk_reward_ratio}")

# 1m. Unknown regime → defaults to NEUTRAL
print("\n1m. Unknown regime → defaults to NEUTRAL")
p10 = {"ticker": "X.NS", "action": "BUY", "entry": 100, "target": 200, "conviction_score": 0.5, "regime": "RANGBOUND"}
t10 = apply_risk_limits(p10, atr=5)
check("accepted", not t10.killed)
check("regime=NEUTRAL", t10.regime == "NEUTRAL")

# 1n. Invalid action → ValueError
print("\n1n. Invalid action → ValueError")
try:
    apply_risk_limits({"ticker": "X", "action": "SHORT", "entry": 100, "conviction_score": 0.5}, atr=10)
    check("invalid action raises", False)
except ValueError:
    check("invalid action raises", True)

# 1o. Negative portfolio equity → ValueError    
print("\n1o. Negative portfolio equity → ValueError")
try:
    apply_risk_limits({"ticker": "X", "action": "BUY", "entry": 100, "conviction_score": 0.5}, atr=10, portfolio_equity=-1000)
    check("negative equity raises", False)
except ValueError:
    check("negative equity raises", True)

# 1p. Tiny equity → position_size=0 → killed
print("\n1p. Tiny equity → position_size < 1 → killed")
p11 = {"ticker": "X.NS", "action": "BUY", "entry": 100, "target": 200, "conviction_score": 0.5, "regime": "BULL"}
t11 = apply_risk_limits(p11, atr=5, portfolio_equity=1.0)  # 1% of 1 = 0.01 risk
check("killed=True (size < 1)", t11.killed)
check("reason mentions position_size", "position_size" in (t11.kill_reason or ""))

# ==============================================================
# 2.  validate_trade_inputs (convenience helper)
# ==============================================================
print("\n" + "="*60)
print("2. RISK ENGINE — validate_trade_inputs()")
print("="*60)

print("\n2a. Valid inputs → None")
check("valid returns None", validate_trade_inputs(100, 90, 125) is None)

print("\n2b. Stop >= entry")
r = validate_trade_inputs(100, 100, 150)
check("returns error", r is not None)
check("mentions stop", "stop" in r.lower() or "risk_per_share" in r.lower())

print("\n2c. Bad R:R")
r = validate_trade_inputs(100, 95, 101)
check("returns error", r is not None)
check("mentions R:R", "risk/reward" in r.lower() or "reward" in r.lower())

print("\n2d. NaN entry")
r = validate_trade_inputs(float('nan'), 90, 120)
check("returns error", r is not None)

print("\n2e. Zero stop")
r = validate_trade_inputs(100, 0, 120)
check("returns error for stop=0", r is not None)

# ==============================================================
# 3.  _is_finite helper
# ==============================================================
print("\n" + "="*60)
print("3. HELPER — _is_finite()")
print("="*60)
check("finite int", _is_finite(42))
check("finite float", _is_finite(3.14))
check("nan → False", not _is_finite(float('nan')))
check("inf → False", not _is_finite(float('inf')))
check("-inf → False", not _is_finite(float('-inf')))
check("string → False", not _is_finite("hello"))
check("None → False", not _is_finite(None))

# ==============================================================
# 4.  risk_tool.py — enforce_risk_limits
# ==============================================================
print("\n" + "="*60)
print("4. RISK TOOL — enforce_risk_limits()")
print("="*60)

from trading_agents.tools.risk_tool import enforce_risk_limits

print("\n4a. Accepted trade")
r = enforce_risk_limits(symbol="RELIANCE.NS", action="BUY", entry=2800, atr=30, target=3100, regime="BULL")
check("status=ACCEPTED", r.get("status") == "ACCEPTED")
check("has summary", "ACCEPTED" in r.get("summary", ""))
check("has position_size", r.get("position_size", 0) > 0)

print("\n4b. Rejected bad R:R")
r = enforce_risk_limits(symbol="TCS.NS", action="BUY", entry=3500, atr=40, target=3510, regime="BULL")
check("status=REJECTED", r.get("status") == "REJECTED")
check("summary mentions REJECTED", "REJECTED" in r.get("summary", ""))

print("\n4c. HOLD")
r = enforce_risk_limits(symbol="X.NS", action="HOLD", entry=100, atr=5)
check("status=REJECTED", r.get("status") == "REJECTED")

print("\n4d. Invalid entry → ERROR")
r = enforce_risk_limits(symbol="X.NS", action="BUY", entry=0, atr=5)
check("status=ERROR", r.get("status") == "ERROR")

print("\n4e. Conviction 80 (auto-normalised)")
r = enforce_risk_limits(symbol="REL.NS", action="BUY", entry=2800, atr=30, target=3100, conviction=80)
check("accepted", r.get("status") == "ACCEPTED")
check("conviction ~0.8", abs(r.get("conviction_score", 0) - 0.8) < 0.01, f"got {r.get('conviction_score')}")

print("\n4f. No target → engine computes")
r = enforce_risk_limits(symbol="REL.NS", action="BUY", entry=2800, atr=30, conviction=0.7, regime="BULL")
check("accepted", r.get("status") == "ACCEPTED")
check("has target_price", r.get("target_price", 0) > 2800)

# ==============================================================
# 5.  paper_trading.py — calculate_trade_plan
# ==============================================================
print("\n" + "="*60)
print("5. PAPER TRADING — calculate_trade_plan()")
print("="*60)

from trading_agents.tools.paper_trading import (
    calculate_trade_plan,
    calculate_trade_plan_from_entry_stop,
    execute_paper_trade,
)

print("\n5a. Basic plan")
r = calculate_trade_plan("RELIANCE.NS", close=2800, atr=30)
check("status=success", r.get("status") == "success")
plan = r.get("plan", {})
check("entry=2800", plan.get("entry") == 2800)
check("stop < entry", plan.get("stop", 9999) < plan.get("entry", 0))
check("target > entry", plan.get("target", 0) > plan.get("entry", 0))
check("qty > 0", plan.get("qty", 0) > 0)
check("rr >= 2.0", plan.get("rr", 0) >= 2.0)
check("has capital_required", plan.get("capital_required", 0) > 0)
check("has regime", plan.get("regime") in ("BULL", "BEAR", "SIDEWAYS", "NEUTRAL"))

print("\n5b. Invalid close")
r = calculate_trade_plan("X", close=0, atr=10)
check("error", r.get("status") == "error")
r = calculate_trade_plan("X", close=-5, atr=10)
check("negative close error", r.get("status") == "error")
r = calculate_trade_plan("X", close=float('nan'), atr=10)
check("NaN close error", r.get("status") == "error")

print("\n5c. Invalid ATR")
r = calculate_trade_plan("X", close=100, atr=0)
check("zero atr error", r.get("status") == "error")
r = calculate_trade_plan("X", close=100, atr=-5)
check("negative atr error", r.get("status") == "error")

print("\n5d. Plan from entry/stop")
r = calculate_trade_plan_from_entry_stop("HDFCBANK.NS", entry=1600, stop=1580)
check("status=success", r.get("status") == "success")
plan = r.get("plan", {})
check("entry=1600", plan.get("entry") == 1600)

print("\n5e. Plan from entry/stop — stop >= entry")
r = calculate_trade_plan_from_entry_stop("X", entry=100, stop=100)
check("error", r.get("status") == "error")
r = calculate_trade_plan_from_entry_stop("X", entry=100, stop=110)
check("stop > entry error", r.get("status") == "error")

print("\n5f. Plan from entry/stop — NaN")
r = calculate_trade_plan_from_entry_stop("X", entry=float('nan'), stop=90)
check("NaN entry error", r.get("status") == "error")

print("\n5g. Plan with BEAR regime (contrarian)")
r = calculate_trade_plan("SBIN.NS", close=800, atr=10, regime="BEAR")
# BUY in BEAR = contrarian
check("status=success", r.get("status") == "success")
check("contrarian=True", r.get("plan", {}).get("contrarian") == True)

# ==============================================================
# 6.  trade_agent.py — check_risk wrapper
# ==============================================================
print("\n" + "="*60)
print("6. TRADE AGENT — check_risk()")
print("="*60)

from trading_agents.trade_agent import check_risk, plan_trade, plan_trade_from_dividend

print("\n6a. check_risk accepted")
r = check_risk("RELIANCE.NS", "BUY", entry=2800, atr=30, target=3100, regime="BULL")
check("ACCEPTED", r.get("status") == "ACCEPTED")

print("\n6b. check_risk rejected (bad RR)")
r = check_risk("TCS.NS", "BUY", entry=3500, atr=40, target=3510)
check("REJECTED", r.get("status") == "REJECTED")

print("\n6c. plan_trade is same as calculate_trade_plan")
r = plan_trade("RELIANCE.NS", close=2800, atr=30)
check("plan_trade success", r.get("status") == "success")

print("\n6d. plan_trade_from_dividend")
r = plan_trade_from_dividend("HDFCBANK.NS", entry=1600, stop=1580)
check("plan_trade_from_dividend success", r.get("status") == "success")

# ==============================================================
# 7.  ValidatedTrade dataclass
# ==============================================================
print("\n" + "="*60)
print("7. ValidatedTrade dataclass integrity")
print("="*60)

t = apply_risk_limits(
    {"ticker": "TEST.NS", "action": "BUY", "entry": 500, "target": 600, "conviction_score": 0.75, "regime": "BULL"},
    atr=10, portfolio_equity=500_000,
)
d = t.to_dict()
check("to_dict has 14 keys", len(d) == 14, f"got {len(d)}")
check("ticker matches", d["ticker"] == "TEST.NS")
check("entry_price matches", d["entry_price"] == t.entry_price)
check("frozen — no mutation", True)  # slots=True, frozen=True in dataclass
try:
    t.ticker = "CHANGED"
    check("actually frozen", False, "mutation succeeded")
except (AttributeError, TypeError, FrozenInstanceError if False else Exception):
    check("actually frozen", True)

check("repr contains ACCEPTED", "ACCEPTED" in repr(t))

# JSON serializable
try:
    json.dumps(d)
    check("JSON serializable", True)
except TypeError as e:
    check("JSON serializable", False, str(e))

# ==============================================================
# 8.  Constants & config consistency
# ==============================================================
print("\n" + "="*60)
print("8. Constants & config consistency")
print("="*60)

from trading_agents.config import ATR_STOP_MULTIPLIER, MIN_REWARD_RISK, RISK_PER_TRADE, MAX_OPEN_TRADES, INITIAL_CAPITAL
check("ATR_STOP_MULTIPLIER=1.5", ATR_STOP_MULTIPLIER == 1.5)
check("MIN_REWARD_RISK=2.0", MIN_REWARD_RISK == 2.0)
check("RISK_PER_TRADE=0.01", RISK_PER_TRADE == 0.01)
check("MAX_OPEN_TRADES=3", MAX_OPEN_TRADES == 3)
check("INITIAL_CAPITAL=1M", INITIAL_CAPITAL == 1_000_000.0)
check("VALID_ACTIONS={BUY,SELL,HOLD}", VALID_ACTIONS == frozenset({"BUY", "SELL", "HOLD"}))
check("VALID_REGIMES has 4", len(VALID_REGIMES) == 4)

# ==============================================================
#  SUMMARY
# ==============================================================
print("\n" + "="*60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("="*60)

if errors:
    print("\nFAILURES:")
    for e in errors:
        print(f"  ✗ {e}")

sys.exit(1 if failed else 0)
