import { useState, useCallback } from "react";
import Header from "./components/Header";
import DecisionCard from "./components/DecisionCard";
import MarketChart from "./components/MarketChart";
import PipelineSteps from "./components/PipelineSteps";
import DebatePanel from "./components/DebatePanel";
import { runAnalysis } from "./api";

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
    const n = parseFloat(v);
    return isNaN(n) ? null : n;
  };

  return {
    ticker: g("Ticker"),
    action: g("Decision") || g("Action"),
    entry: num("Entry") ?? num("Entry Price"),
    stop: num("Stop") ?? num("Stop Loss"),
    target: num("Target"),
    riskReward: num("Risk Reward"),
    regime: g("Regime"),
    killed: /REJECTED|True/i.test(g("Status") || g("Killed") || ""),
    killReason: g("Reason") || g("Kill Reason"),
  };
}

function parsePipelineSteps(text) {
  const names = [
    "Quant Engine", "Quant Agent", "Sentiment Agent",
    "Bull Agent", "Bear Agent", "CIO Agent", "Risk Engine",
  ];
  return names.map((name) => {
    // Check if this step's output appears in the text
    const patterns = {
      "Quant Engine": /QUANT_SNAPSHOT_GENERATED/i,
      "Quant Agent": /QUANT_ANALYSIS|Overall Quant View/i,
      "Sentiment Agent": /SENTIMENT_SUMMARY|sentiment/i,
      "Bull Agent": /BULL_THESIS|bull case/i,
      "Bear Agent": /BEAR_THESIS|bear case/i,
      "CIO Agent": /CIO_DECISION|Action:/i,
      "Risk Engine": /FINAL_TRADE|REGIME-AWARE TRADING DECISION/i,
    };
    const matched = patterns[name]?.test(text);
    const isFlagged = name === "Risk Engine" && /REJECTED|killed.*true/i.test(text);
    return {
      status: isFlagged ? "flagged" : matched ? "complete" : "pending",
      summary: matched ? (isFlagged ? "Trade flagged by risk engine" : "Completed") : null,
      duration: null,
    };
  });
}

function parseBullBear(text) {
  // Extract bullet-like points from bull/bear thesis sections
  const extractPoints = (section) => {
    if (!section) return [];
    return section
      .split("\n")
      .map((l) => l.replace(/^[\s•\-\d.]+/, "").trim())
      .filter((l) => l.length > 15 && l.length < 300)
      .slice(0, 4);
  };

  const bullMatch = text.match(/bull[_ ]?(?:thesis|case)[:\s]*([\s\S]*?)(?=bear[_ ]?(?:thesis|case)|CIO|$)/i);
  const bearMatch = text.match(/bear[_ ]?(?:thesis|case)[:\s]*([\s\S]*?)(?=CIO|FINAL|REGIME|$)/i);

  return {
    bull: { points: extractPoints(bullMatch?.[1]), conviction: 0.6 },
    bear: { points: extractPoints(bearMatch?.[1]), conviction: 0.7 },
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
  const [syncAgo, setSyncAgo] = useState(null);
  const [error, setError] = useState(null);

  const handleRun = useCallback(async (t) => {
    setLoading(true);
    setError(null);
    setTrade(null);
    setSteps(null);
    setDebate({ bull: null, bear: null });

    // Show running state for pipeline
    setSteps([
      { status: "running", summary: "Fetching market data…" },
      ...Array(6).fill({ status: "pending" }),
    ]);

    try {
      const data = await runAnalysis(t);
      const reply = data.reply || "";

      // Parse all sections
      const tradeData = parseTrade(reply);
      setTrade(tradeData);
      setRegime(tradeData.regime);
      setPrice(tradeData.entry);
      setSyncAgo("Just now");

      setSteps(parsePipelineSteps(reply));
      setDebate(parseBullBear(reply));
    } catch (err) {
      setError(err.message);
      setSteps(null);
    } finally {
      setLoading(false);
    }
  }, []);

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
          <MarketChart ticker={ticker} price={price} />
        </div>

        {/* Right Column (40%) */}
        <div className="flex flex-col gap-4 w-[40%] h-full overflow-hidden">
          <PipelineSteps steps={steps} />
          <DebatePanel bull={debate.bull} bear={debate.bear} />
        </div>
      </main>

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-danger/90 text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-md animate-fade-in z-50">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-lg">error</span>
            <span>{error}</span>
          </div>
        </div>
      )}
    </>
  );
}
