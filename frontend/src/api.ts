const API_BASE = "";

export async function runAnalysis(ticker: string) {
  let t = ticker.trim().toUpperCase();
  // No need to add .NS — server handles that

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300_000);

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: t }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
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

export async function fetchMarket({
  ticker,
  period = "6mo",
  interval = "1d",
  limit = 180,
}: {
  ticker: string;
  period?: string;
  interval?: string;
  limit?: number;
}) {
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
      try {
        detail = await res.text();
      } catch {
        /* ignore */
      }
    }
    throw new Error(detail);
  }
  return res.json();
}
