"""Comprehensive test of all API endpoints."""
import requests
import json
import sys

BASE = "http://localhost:8000"
errors = []
passed = []

# Test 1: Root page serves React frontend
try:
    r = requests.get(f"{BASE}/", timeout=10)
    assert r.status_code == 200
    assert "root" in r.text
    passed.append("GET / (frontend)")
except Exception as e:
    errors.append(f"GET /: {e}")

# Test 2: Regime API
try:
    r = requests.get(f"{BASE}/api/regime", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    assert d["regime"] in ("BULL", "SIDEWAYS", "BEAR")
    passed.append(f"GET /api/regime -> {d['regime']}")
except Exception as e:
    errors.append(f"GET /api/regime: {e}")

# Test 3: Portfolio API
try:
    r = requests.get(f"{BASE}/api/portfolio", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    assert "cash" in d
    passed.append("GET /api/portfolio")
except Exception as e:
    errors.append(f"GET /api/portfolio: {e}")

# Test 4: Market data API
try:
    r = requests.get(f"{BASE}/api/market?ticker=TCS&period=3mo&interval=1d&limit=30", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    assert len(d["candles"]) > 0
    c = d["candles"][-1]
    assert c.get("rsi") is not None, "RSI should be present"
    passed.append(f"GET /api/market -> {len(d['candles'])} candles, RSI={c['rsi']}")
except Exception as e:
    errors.append(f"GET /api/market: {e}")

# Test 5: Chat API
try:
    r = requests.post(f"{BASE}/api/chat", json={"message": "What is the market regime?"}, timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d.get("reply"), "Chat reply should not be empty"
    assert len(d["reply"]) > 20
    assert d.get("steps") is not None
    passed.append(f"POST /api/chat -> {len(d['reply'])} chars, {len(d['steps'])} steps")
except Exception as e:
    errors.append(f"POST /api/chat: {e}")

# Test 6: Portfolio reset
try:
    r = requests.post(f"{BASE}/api/portfolio/reset", timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    passed.append("POST /api/portfolio/reset")
except Exception as e:
    errors.append(f"POST /api/portfolio/reset: {e}")

# Test 7: Portfolio performance
try:
    r = requests.get(f"{BASE}/api/portfolio/performance", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    assert "portfolio_value" in d
    passed.append("GET /api/portfolio/performance")
except Exception as e:
    errors.append(f"GET /api/portfolio/performance: {e}")

# Test 8: Portfolio refresh
try:
    r = requests.post(f"{BASE}/api/portfolio/refresh", timeout=60)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    passed.append("POST /api/portfolio/refresh")
except Exception as e:
    errors.append(f"POST /api/portfolio/refresh: {e}")

# Test 9: Nifty 50 signals
try:
    r = requests.get(f"{BASE}/api/signals/nifty50?limit=3&include_news=false", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert len(d.get("signals", [])) > 0
    passed.append(f"GET /api/signals/nifty50 -> {len(d['signals'])} signals")
except Exception as e:
    errors.append(f"GET /api/signals/nifty50: {e}")

# Test 10: Dividend top
try:
    r = requests.get(f"{BASE}/api/dividend/top", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    count = len(d.get("top_opportunities", []))
    passed.append(f"GET /api/dividend/top -> {count} opportunities")
except Exception as e:
    errors.append(f"GET /api/dividend/top: {e}")

# Test 11: Backtest oversold best
try:
    r = requests.get(f"{BASE}/api/backtest/oversold-best?top_n=3", timeout=300)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "success"
    count = len(d.get("best_stocks", []))
    pnl = d.get("total_best_pnl_inr", 0)
    passed.append(f"GET /api/backtest/oversold-best -> {count} stocks, PnL={pnl}")
except Exception as e:
    errors.append(f"GET /api/backtest/oversold-best: {e}")

print(f"\n{'='*60}")
print(f"RESULTS: {len(passed)} PASSED / {len(errors)} FAILED")
print(f"{'='*60}")
for p in passed:
    print(f"  [OK] {p}")
if errors:
    print(f"\nFAILED:")
    for e in errors:
        print(f"  [FAIL] {e}")
    sys.exit(1)
else:
    print("\nAll tests passed!")
