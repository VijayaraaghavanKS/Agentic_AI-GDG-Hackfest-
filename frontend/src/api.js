const API_BASE = "";

export async function runAnalysis(ticker) {
  // Normalise ticker: add .NS suffix for NSE stocks if missing
  let t = ticker.trim().toUpperCase();
  if (!t.startsWith("^") && !t.includes(".")) t = `${t}.NS`;

  const controller = new AbortController();
  // Allow up to 5 minutes for the full agent pipeline
  const timeoutId = setTimeout(() => controller.abort(), 300_000);

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: `Analyze ${t}` }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Analysis timed out (>5 min). Try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchRegime() {
  const res = await fetch(`${API_BASE}/api/regime`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchPortfolio() {
  const res = await fetch(`${API_BASE}/api/portfolio`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchMarket({ ticker, period = "6mo", interval = "1d", limit = 180 }) {
  const url = new URL(`${API_BASE}/api/market`, window.location.origin);
  url.searchParams.set("ticker", ticker);
  url.searchParams.set("period", period);
  url.searchParams.set("interval", interval);
  url.searchParams.set("limit", String(limit));

  const res = await fetch(url.toString(), { method: "GET" });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || JSON.stringify(body);
    } catch {
      try { detail = await res.text(); } catch { /* ignore */ }
    }
    throw new Error(detail);
  }
  return res.json();
}
