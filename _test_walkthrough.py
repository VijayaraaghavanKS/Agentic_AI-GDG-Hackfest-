"""Quick walkthrough test of all API endpoints."""
import requests
import json
import time

BASE = "http://localhost:8000"

def test(name, method, path, **kwargs):
    url = BASE + path
    t0 = time.time()
    try:
        r = getattr(requests, method)(url, timeout=kwargs.pop("timeout", 30), **kwargs)
        elapsed = time.time() - t0
        try:
            d = r.json()
        except Exception:
            d = r.text[:200]
        print(f"  [{r.status_code}] {name} ({elapsed:.1f}s)")
        return d
    except Exception as e:
        print(f"  [ERR] {name}: {e}")
        return None

print("=== 1. HEALTH ===")
d = test("health", "get", "/api/health")
print(f"     -> {d}")

print("\n=== 2. REGIME (Dashboard) ===")
d = test("regime", "get", "/api/regime", timeout=30)
if d:
    print(f"     -> regime={d.get('regime')}, nifty={d.get('nifty_close')}, strategy={d.get('strategy')}")

print("\n=== 3. MARKET CHART ===")
d = test("market", "get", "/api/market?ticker=RELIANCE&period=6mo&interval=1d&limit=100", timeout=30)
if d:
    print(f"     -> status={d.get('status')}, ticker={d.get('ticker')}, candles={len(d.get('candles', []))}")
    if d.get("candles"):
        c = d["candles"][-1]
        print(f"     -> last candle: {c.get('date')} O={c.get('open')} H={c.get('high')} L={c.get('low')} C={c.get('close')}")

print("\n=== 4. PORTFOLIO (Dashboard) ===")
d = test("portfolio", "get", "/api/portfolio", timeout=10)
if d:
    print(f"     -> cash={d.get('cash')}, positions={d.get('open_positions_count')}, value={d.get('portfolio_value')}")

print("\n=== 5. SIGNAL BOARD (Dashboard) ===")
d = test("signals", "get", "/api/signals/nifty50?include_news=true&max_news=2&news_days=1", timeout=120)
if d:
    sigs = d.get("signals", [])
    print(f"     -> {len(sigs)} signals, scanned={d.get('stocks_scanned')}")
    if sigs:
        s = sigs[0]
        print(f"     -> first: {s.get('symbol')} close={s.get('close')} breakout={s.get('is_breakout')} rsi={s.get('rsi')}")

print("\n=== 6. DIVIDENDS (Dashboard) ===")
d = test("dividends", "get", "/api/dividends/top?count=5", timeout=30)
if d:
    divs = d.get("dividends", [])
    print(f"     -> {len(divs)} dividends")
    if divs:
        print(f"     -> first: {divs[0].get('company')} yield={divs[0].get('yield')}")

print("\n=== 7. ANALYZE (Analyze page) ===")
d = test("analyze", "post", "/api/analyze", json={"ticker": "SBIN"}, timeout=300)
if d:
    steps = d.get("steps", [])
    complete = sum(1 for s in steps if s.get("status") == "complete")
    print(f"     -> steps: {complete}/{len(steps)} complete")
    for s in steps:
        print(f"        [{s.get('status', '?'):8s}] {s.get('name', '?')}")
    t = d.get("trade", {})
    if t:
        print(f"     -> trade: {t.get('action')} entry={t.get('entry')} stop={t.get('stop')} target={t.get('target')} rr={t.get('riskReward')}")
    db = d.get("debate", {})
    if db:
        bp = db.get("bull", {}).get("points", [])
        brp = db.get("bear", {}).get("points", [])
        bc = db.get("bull", {}).get("conviction", 0)
        brc = db.get("bear", {}).get("conviction", 0)
        print(f"     -> debate: bull={len(bp)} pts ({bc}), bear={len(brp)} pts ({brc})")
        for p in bp[:2]:
            print(f"        Bull: {p[:100]}")
        for p in brp[:2]:
            print(f"        Bear: {p[:100]}")

print("\n=== 8. CHAT (Chat page) ===")
d = test("chat", "post", "/api/chat", json={"message": "What is the current market regime?", "fresh_session": True}, timeout=60)
if d:
    reply = d.get("reply", "")
    print(f"     -> reply length: {len(reply)}")
    print(f"     -> first 200 chars: {reply[:200]}")

print("\n=== 9. SPA ROUTES ===")
for path in ["/", "/market", "/analyze"]:
    r = requests.get(BASE + path, timeout=10)
    is_html = "<!doctype html>" in r.text.lower() or "<html" in r.text.lower()
    print(f"  [{r.status_code}] {path} -> HTML={is_html}")

print("\nDone!")
