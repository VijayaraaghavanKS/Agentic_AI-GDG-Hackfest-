import { useEffect, useMemo, useState, useCallback } from "react";
import Header from "./components/Header";
import DecisionCard from "./components/DecisionCard";
import MarketChart from "./components/MarketChart";
import PipelineSteps from "./components/PipelineSteps";
import DebatePanel from "./components/DebatePanel";
import { fetchMarket, runAnalysis } from "./api";

/* ── Parsers: extract structured data from agent text ── */

function parseTrade(text) {
  const g = (key) => {
    const re = new RegExp(`${key}:\\s*(.+)`, "i");
    const m = text.match(re);
    return m ? m[1].trim() : null;
  };
  const num = (key) => {
    const v = g(key);
    if (!v || v === "—" || v === "N/A") return null;
    const rr = v.match(/1\s*:\s*([\d.]+)/);
    if (rr) {
      const ratio = parseFloat(rr[1]);
      return Number.isFinite(ratio) ? ratio : null;
    }
    const n = parseFloat(String(v).replace(/[^\d.-]/g, ""));
    return isNaN(n) ? null : n;
  };

  // Extract kill reason – handle multi-line reasons
  let killReason = g("Reason") || g("Kill Reason");
  if (!killReason) {
    const reasonBlock = text.match(/Reason:\s*([\s\S]*?)(?=\n\n|\n[A-Z]|\s*$)/i);
    if (reasonBlock) killReason = reasonBlock[1].trim().split("\n").filter(Boolean).join(" ");
  }

  // Detect killed/rejected status
  const statusVal = g("Status") || g("Killed") || "";
  const killed = /REJECTED|True/i.test(statusVal);

  return {
    ticker: g("Ticker"),
    action: (g("Decision") || g("Action"))?.toUpperCase(),
    entry: num("Entry") ?? num("Entry Price"),
    stop: num("Stop") ?? num("Stop Loss"),
    target: num("Target"),
    riskReward: num("Risk Reward"),
    regime: g("Regime"),
    conviction: num("Conviction"),
    killed,
    killReason,
    // Extract raw sections for detailed rejection info
    riskDetails: killed ? extractRiskDetails(text) : null,
  };
}

function extractRiskDetails(text) {
  const details = {};
  // Try to extract all risk-related fields
  const fields = [
    "Position Size", "Risk Per Share", "Total Risk",
    "Risk Reward", "Risk Reward Ratio", "Conviction",
  ];
  for (const f of fields) {
    const m = text.match(new RegExp(`${f}[:\\s]+([^\\n]+)`, "i"));
    if (m) details[f.toLowerCase().replace(/ /g, "_")] = m[1].trim();
  }

  // Extract the reason block more thoroughly
  const reasonBlock = text.match(/(?:Reason|Kill Reason)[:\s]+([\s\S]*?)(?=\n\n[A-Z]|\s*$)/i);
  if (reasonBlock) details.full_reason = reasonBlock[1].trim();

  // Get the regime mismatch info
  const regime = text.match(/Regime[:\s]+(\w+)/i);
  if (regime) details.regime = regime[1];
  const action = text.match(/(?:Decision|Action)[:\s]+(\w+)/i);
  if (action) details.action = action[1];

  return Object.keys(details).length > 0 ? details : null;
}

function parsePipelineSteps(text, backendSteps) {
  const names = [
    "Quant Engine", "Quant Agent", "Sentiment Agent",
    "Bull Agent", "Bear Agent", "CIO Agent", "Risk Engine",
  ];

  // If backend provided structured steps, use them directly
  if (Array.isArray(backendSteps) && backendSteps.length === 7) {
    return backendSteps.map((step, i) => ({
      status: step.status || "pending",
      summary: step.summary || null,
      output: step.output || null,
      duration: null,
    }));
  }

  // Fallback: regex-based parsing from the combined reply text
  return names.map((name) => {
    const patterns = {
      "Quant Engine": /QUANT_SNAPSHOT_GENERATED|Ticker:.*\nRegime:/i,
      "Quant Agent": /QUANT_ANALYSIS|Overall Quant View/i,
      "Sentiment Agent": /SENTIMENT_SUMMARY|Company Sentiment|Macro Environment/i,
      "Bull Agent": /BULL_THESIS|Quant Strengths|Why Bulls Could Be Right/i,
      "Bear Agent": /BEAR_THESIS|Quant Weaknesses|Why Bears Could Be Right/i,
      "CIO Agent": /CIO_DECISION|Action:\s*(?:BUY|SELL|HOLD)/i,
      "Risk Engine": /REGIME-AWARE TRADING DECISION|FINAL_TRADE|Status:\s*(?:ACCEPTED|REJECTED)/i,
    };
    const matched = patterns[name]?.test(text);
    const isFlagged = name === "Risk Engine" && /REJECTED|killed.*true/i.test(text);

    // Extract a one-line summary
    let summary = null;
    if (matched) {
      if (name === "Quant Engine") {
        const regime = text.match(/Regime:\s*(\w+)/i);
        const price = text.match(/Price:\s*([\d,.]+)/i);
        summary = regime && price ? `${regime[1]} regime, Price ${price[1]}` : "Snapshot generated";
      } else if (name === "Quant Agent") {
        const view = text.match(/Overall Quant View:\s*([^\n]+)/i);
        summary = view ? view[1].slice(0, 80) : "Analysis complete";
      } else if (name === "Sentiment Agent") {
        const conf = text.match(/Confidence:\s*([\d.]+)/i);
        summary = conf ? `Confidence: ${conf[1]}` : "Sentiment analyzed";
      } else if (name === "Bull Agent") {
        const conv = text.match(/BULL_THESIS[\s\S]*?Conviction:\s*([\d.]+)/i);
        summary = conv ? `Conviction: ${conv[1]}` : "Bull case built";
      } else if (name === "Bear Agent") {
        const conv = text.match(/BEAR_THESIS[\s\S]*?Conviction:\s*([\d.]+)/i);
        summary = conv ? `Conviction: ${conv[1]}` : "Bear case built";
      } else if (name === "CIO Agent") {
        const action = text.match(/Action:\s*(\w+)/i);
        summary = action ? `Decision: ${action[1]}` : "Decision made";
      } else if (name === "Risk Engine") {
        if (isFlagged) {
          const reason = text.match(/(?:Reason|Kill Reason):\s*([^\n]+)/i);
          summary = reason ? `REJECTED: ${reason[1].slice(0, 60)}` : "Trade rejected by risk engine";
        } else {
          summary = "Trade accepted";
        }
      }
    }

    return {
      status: isFlagged ? "flagged" : matched ? "complete" : "pending",
      summary,
      output: null,
      duration: null,
    };
  });
}

function parseBullBear(text, backendSteps) {
  // Extract bullet-like points from bull/bear thesis sections
  const extractPoints = (section) => {
    if (!section) return [];
    return section
      .split("\n")
      .map((l) => l.replace(/^[\s•\-\d.]+/, "").trim())
      .filter((l) => l.length > 10 && l.length < 300)
      .slice(0, 5);
  };

  const extractConviction = (section) => {
    if (!section) return 0.5;
    const m = section.match(/Conviction:\s*([\d.]+)/i);
    if (m) {
      const v = parseFloat(m[1]);
      return Number.isFinite(v) ? (v > 1 ? v / 100 : v) : 0.5;
    }
    return 0.5;
  };

  // Prefer backend step outputs if available
  let bullText = null;
  let bearText = null;
  if (Array.isArray(backendSteps) && backendSteps.length === 7) {
    bullText = backendSteps[3]?.output || "";
    bearText = backendSteps[4]?.output || "";
  }

  // Fallback to regex extraction from combined text
  if (!bullText) {
    const bullMatch = text.match(/(?:BULL_THESIS|bull[_ ]?case)[:\s]*([\s\S]*?)(?=BEAR_THESIS|bear[_ ]?(?:thesis|case)|CIO_DECISION|CIO Agent|$)/i);
    bullText = bullMatch?.[1] || "";
  }
  if (!bearText) {
    const bearMatch = text.match(/(?:BEAR_THESIS|bear[_ ]?case)[:\s]*([\s\S]*?)(?=CIO_DECISION|CIO Agent|FINAL|REGIME|$)/i);
    bearText = bearMatch?.[1] || "";
  }

  return {
    bull: { points: extractPoints(bullText), conviction: extractConviction(bullText) },
    bear: { points: extractPoints(bearText), conviction: extractConviction(bearText) },
  };
}

/* ── App ── */

export default function App() {
  const [ticker, setTicker] = useState("RELIANCE");
  const [loading, setLoading] = useState(false);
  const [trade, setTrade] = useState(null);
  const [steps, setSteps] = useState(null);
  const [debate, setDebate] = useState({ bull: null, bear: null });
  const [regime, setRegime] = useState(null);
  const [price, setPrice] = useState(null);
  const [priceChange, setPriceChange] = useState(null);
  const [syncAgo, setSyncAgo] = useState(null);
  const [error, setError] = useState(null);
  const [errorId, setErrorId] = useState(0);

  const [timeframe, setTimeframe] = useState("1D");
  const [market, setMarket] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(null);
  const [chartRetryCount, setChartRetryCount] = useState(0);
  const [selectedStepIndex, setSelectedStepIndex] = useState(null);

  const tfConfig = useMemo(() => {
    const map = {
      "1D": { period: "5d", interval: "15m", limit: 180 },
      "1W": { period: "1mo", interval: "1h", limit: 180 },
      "1M": { period: "6mo", interval: "1d", limit: 180 },
      "3M": { period: "1y", interval: "1d", limit: 220 },
      "1Y": { period: "2y", interval: "1d", limit: 260 },
    };
    return map[timeframe] || map["1M"];
  }, [timeframe]);

  useEffect(() => {
    if (!error) return;
    const id = window.setTimeout(() => setError(null), 6500);
    return () => window.clearTimeout(id);
  }, [errorId, error]);

  useEffect(() => {
    if (!market?.timestamp) return;
    const tick = () => {
      const t = Date.parse(market.timestamp);
      if (!Number.isFinite(t)) return;
      const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
      if (sec < 15) return setSyncAgo("Just now");
      if (sec < 60) return setSyncAgo(`${sec}s ago`);
      const min = Math.floor(sec / 60);
      if (min < 60) return setSyncAgo(`${min}m ago`);
      const hr = Math.floor(min / 60);
      return setSyncAgo(`${hr}h ago`);
    };
    tick();
    const id = window.setInterval(tick, 15_000);
    return () => window.clearInterval(id);
  }, [market?.timestamp]);

  const handleRun = useCallback(async (t) => {
    setLoading(true);
    setError(null);
    setTrade(null);
    setSteps(null);
    setDebate({ bull: null, bear: null });
    setSelectedStepIndex(null);

    // Show running state for pipeline
    setSteps([
      { status: "running", summary: "Running AI pipeline…" },
      ...Array(6).fill({ status: "pending" }),
    ]);

    try {
      // Chart data is fetched independently by the useEffect on [ticker, tfConfig].
      // Here we only run the analysis pipeline.
      const analysis = await runAnalysis(t);
      const reply = analysis?.reply || "";
      const backendSteps = analysis?.steps || null;

      // Parse all sections
      const tradeData = parseTrade(reply);
      const normalizedTrade = {
        ...tradeData,
        ticker: tradeData.ticker || t,
        // Prefer regime from agent reply; fall back to market snapshot
        regime: tradeData.regime || market?.regime || null,
        // Prefer parsed entry; fall back to live market price
        entry: tradeData.entry ?? market?.indicators?.price ?? null,
        // Store raw reply for detailed view
        rawReply: reply,
      };
      setTrade(normalizedTrade);
      if (normalizedTrade.regime) setRegime(normalizedTrade.regime);
      if (normalizedTrade.entry != null) setPrice(normalizedTrade.entry);

      setSteps(parsePipelineSteps(reply, backendSteps));
      setDebate(parseBullBear(reply, backendSteps));
    } catch (err) {
      setError(err?.message || String(err));
      setErrorId((x) => x + 1);
      setSteps(null);
    } finally {
      setLoading(false);
    }
  }, [market]);

  useEffect(() => {
    // When ticker or timeframe changes, fetch chart data independently.
    let cancelled = false;
    setChartError(null);
    setChartLoading(true);
    // Clear stale candles immediately so old ticker's chart doesn't linger
    setMarket(null);

    const run = async () => {
      try {
        const marketData = await fetchMarket({ ticker, ...tfConfig });
        if (cancelled) return;
        setMarket(marketData);
        setChartError(null);
        setRegime((r) => r || marketData?.regime || null);
        setPrice((p) => p ?? marketData?.indicators?.price ?? null);

        const candles = marketData?.candles || [];
        if (candles.length >= 2) {
          const prev = candles[candles.length - 2]?.c;
          const last = candles[candles.length - 1]?.c;
          if (Number.isFinite(prev) && Number.isFinite(last) && prev !== 0) {
            setPriceChange(Number((((last - prev) / prev) * 100).toFixed(2)));
          } else {
            setPriceChange(null);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setChartError(err?.message || String(err));
        }
      } finally {
        if (!cancelled) setChartLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [ticker, tfConfig, chartRetryCount]);

  return (
    <>
      <Header
        ticker={ticker}
        setTicker={setTicker}
        onRun={handleRun}
        loading={loading}
        regime={regime}
        syncAgo={syncAgo}
      />

      <main className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* Left Column (60%) */}
        <div className="flex flex-col gap-4 w-[60%] h-full overflow-hidden">
          <DecisionCard trade={trade} />
          <MarketChart
            ticker={ticker}
            price={price}
            priceChange={priceChange}
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            candles={market?.candles || null}
            indicators={market?.indicators || null}
            chartLoading={chartLoading}
            chartError={chartError}
            onRetry={() => setChartRetryCount((n) => n + 1)}
          />
        </div>

        {/* Right Column (40%) */}
        <div className="flex flex-col gap-4 w-[40%] h-full overflow-hidden">
          <PipelineSteps
            steps={steps}
            selectedIndex={selectedStepIndex}
            onSelectStep={setSelectedStepIndex}
          />
          <DebatePanel
            bull={debate.bull}
            bear={debate.bear}
            selectedStepIndex={selectedStepIndex}
          />
        </div>
      </main>

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-danger/90 text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-md animate-fade-in z-50">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-lg">error</span>
            <span className="flex-1 min-w-0 break-words">{error}</span>
            <button
              type="button"
              className="ml-2 text-white/80 hover:text-white transition-colors"
              onClick={() => setError(null)}
              aria-label="Dismiss error"
              title="Dismiss"
            >
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>
        </div>
      )}
    </>
  );
}
