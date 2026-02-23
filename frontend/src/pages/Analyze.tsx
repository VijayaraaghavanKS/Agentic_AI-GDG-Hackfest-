import { useState, useEffect, useMemo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DecisionCard, type TradeData } from "@/components/DecisionCard";
import { PipelineSteps, type StepData } from "@/components/PipelineSteps";
import { DebatePanel } from "@/components/DebatePanel";
import { MarketChart, type Candle, type ChartView } from "@/components/MarketChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Play, BarChart3 } from "lucide-react";
import { runAnalysis, fetchMarket } from "@/api";

/* ── Parser helpers ── */

function parseTrade(text: string): TradeData {
  const g = (key: string) => {
    const re = new RegExp(`${key}:\\s*(.+)`, "i");
    const m = text.match(re);
    return m ? m[1].trim() : null;
  };
  const num = (key: string) => {
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

  let killReason = g("Reason") || g("Kill Reason");
  if (!killReason) {
    const reasonBlock = text.match(/Reason:\s*([\s\S]*?)(?=\n\n|\n[A-Z]|\s*$)/i);
    if (reasonBlock) killReason = reasonBlock[1].trim().split("\n").filter(Boolean).join(" ");
  }

  const statusVal = g("Status") || g("Killed") || "";
  const killed = /REJECTED|True/i.test(statusVal);

  return {
    ticker: g("Ticker"),
    action: (g("Verdict") || g("Action") || g("Signal"))?.toUpperCase() ?? null,
    entry: num("Entry") ?? num("Entry Price"),
    stop: num("Stop Loss") ?? num("Stop"),
    target: num("Target"),
    riskReward: num("Risk Reward") ?? num("Risk Reward Ratio"),
    regime: g("Regime"),
    conviction: num("Conviction"),
    killed,
    killReason,
    riskDetails: killed ? extractRiskDetails(text) : null,
  };
}

function extractRiskDetails(text: string) {
  const details: Record<string, string> = {};
  const fields = [
    "Position Size", "Risk Per Share", "Total Risk",
    "Risk Reward", "Risk Reward Ratio", "Conviction",
  ];
  for (const f of fields) {
    const m = text.match(new RegExp(`${f}[:\\s]+([^\\n]+)`, "i"));
    if (m) details[f.toLowerCase().replace(/ /g, "_")] = m[1].trim();
  }
  const reasonBlock = text.match(/(?:Reason|Kill Reason)[:\s]+([\s\S]*?)(?=\n\n[A-Z]|\s*$)/i);
  if (reasonBlock) details.full_reason = reasonBlock[1].trim();
  const regime = text.match(/Regime[:\s]+(\w+)/i);
  if (regime) details.regime = regime[1];
  const action = text.match(/(?:Decision|Action)[:\s]+(\w+)/i);
  if (action) details.action = action[1];
  return Object.keys(details).length > 0 ? details : null;
}

function parsePipelineSteps(text: string, backendSteps?: StepData[] | null): StepData[] {
  const names = [
    "Regime Analyst", "Stock Scanner", "Dividend Scanner",
    "Debate (Bull vs Bear)", "Trade Executor", "Portfolio Manager", "Autonomous Flow",
  ];

  // Prefer backend-provided step data (structured from server)
  if (Array.isArray(backendSteps) && backendSteps.length >= names.length) {
    // Use backend status but ALSO check text patterns as fallback
    // (the LLM may produce output under the root agent's name that maps to a
    //  specific step but isn't attributed to a sub-agent in the event stream)
    const patterns: Record<string, RegExp> = {
      "Regime Analyst": /regime[:\s]*(BULL|BEAR|SIDEWAYS)|market regime|regime_suitability/i,
      "Stock Scanner": /scan_watchlist|breakout|oversold|stocks_scanned|signal_counts|rsi[:\s]*\d|above_50dma|support_zone/i,
      "Dividend Scanner": /dividend|yield|ex.?date/i,
      "Debate (Bull vs Bear)": /bull.*case|bear.*case|bull_thesis|bear_thesis|cio_decision|debate|bull.*advocate|bear.*advocate/i,
      "Trade Executor": /entry.*(?:price)?[:\s]*[\d,.]+|stop.*loss[:\s]*[\d,.]+|target[:\s]*[\d,.]+|risk.?reward|trade.*plan|check_risk|paper.*trade/i,
      "Portfolio Manager": /portfolio|holdings|cash.*(?:balance|available)|unrealized|positions/i,
      "Autonomous Flow": /autonomous|trading.*loop|scan.*execute|auto.*trade/i,
    };

    return backendSteps.map((step, i) => {
      const name = names[i] || "";
      let status = step.status || "pending";
      let summary = step.summary || null;
      const output = step.output || null;

      // If backend says pending but the text contains evidence of this step, upgrade
      if (status === "pending" && patterns[name]?.test(text)) {
        status = "complete";
        if (name === "Regime Analyst") {
          const regime = text.match(/regime[:\s]*(BULL|BEAR|SIDEWAYS)/i);
          summary = regime ? `Market regime: ${regime[1]}` : "Regime analyzed";
        } else if (name === "Trade Executor") {
          if (/REJECTED|SKIPPED|killed/i.test(text)) {
            status = "flagged";
            const reason = text.match(/(?:Reason|Kill Reason):\s*([^\n]+)/i);
            summary = reason ? `REJECTED: ${reason[1].slice(0, 60)}` : "Trade rejected";
          } else {
            const action = text.match(/(?:Decision|Action|Verdict|Signal):\s*(\w+)/i);
            summary = action ? `Decision: ${action[1]}` : "Trade evaluated";
          }
        } else if (name === "Debate (Bull vs Bear)") {
          const verdict = text.match(/(?:Verdict|Decision):\s*(BUY|SELL|HOLD)/i);
          summary = verdict ? `Verdict: ${verdict[1]}` : "Debate complete";
        } else {
          summary = "Complete";
        }
      }

      return { status, summary, output, duration: null } as StepData;
    });
  }

  // Fallback: pure text-based parsing
  return names.map((name) => {
    const patterns: Record<string, RegExp> = {
      "Regime Analyst": /regime[:\s]*(BULL|BEAR|SIDEWAYS)|market regime|regime_suitability/i,
      "Stock Scanner": /scan_watchlist|breakout|oversold|stocks_scanned|signal_counts|rsi[:\s]*\d|above_50dma|support_zone/i,
      "Dividend Scanner": /dividend|yield|ex.?date/i,
      "Debate (Bull vs Bear)": /bull.*case|bear.*case|bull_thesis|bear_thesis|cio_decision|debate|bull.*advocate|bear.*advocate/i,
      "Trade Executor": /entry.*(?:price)?[:\s]*[\d,.]+|stop.*loss[:\s]*[\d,.]+|target[:\s]*[\d,.]+|risk.?reward|trade.*plan|check_risk|paper.*trade/i,
      "Portfolio Manager": /portfolio|holdings|cash.*(?:balance|available)|unrealized|positions/i,
      "Autonomous Flow": /autonomous|trading.*loop|scan.*execute|auto.*trade/i,
    };
    const matched = patterns[name]?.test(text);
    const isFlagged = name === "Trade Executor" && /REJECTED|SKIPPED|killed/i.test(text);

    let summary: string | null = null;
    if (matched) {
      if (name === "Regime Analyst") {
        const regime = text.match(/regime[:\s]*(BULL|BEAR|SIDEWAYS)/i);
        summary = regime ? `Market regime: ${regime[1]}` : "Regime analyzed";
      } else if (name === "Trade Executor") {
        if (isFlagged) {
          const reason = text.match(/(?:Reason|Kill Reason):\s*([^\n]+)/i);
          summary = reason ? `REJECTED: ${reason[1].slice(0, 60)}` : "Trade rejected/skipped";
        } else {
          const action = text.match(/(?:Decision|Action|Verdict|Signal):\s*(\w+)/i);
          summary = action ? `Decision: ${action[1]}` : "Trade evaluated";
        }
      } else if (name === "Debate (Bull vs Bear)") {
        const verdict = text.match(/(?:Verdict|Decision):\s*(BUY|SELL|HOLD)/i);
        summary = verdict ? `Verdict: ${verdict[1]}` : "Debate complete";
      } else {
        summary = "Complete";
      }
    }

    return {
      status: isFlagged ? "flagged" : matched ? "complete" : "pending",
      summary,
      output: null,
      duration: null,
    } as StepData;
  });
}

function parseBullBear(text: string, backendSteps?: StepData[] | null) {
  const extractPoints = (section: string) => {
    if (!section) return [];
    return section
      .split("\n")
      .map((l) => l.replace(/^[\s•\-\d.]+/, "").trim())
      .filter((l) => l.length > 10 && l.length < 300 && !/^(Conviction|BULL_THESIS|BEAR_THESIS|CIO_DECISION):/i.test(l))
      .slice(0, 6);
  };

  const extractConviction = (section: string) => {
    if (!section) return 0.5;
    const m = section.match(/Conviction:\s*([\d.]+)/i);
    if (m) {
      const v = parseFloat(m[1]);
      return Number.isFinite(v) ? (v > 1 ? v / 100 : v) : 0.5;
    }
    return 0.5;
  };

  let bullText = "";
  let bearText = "";

  const tryExtractBullBear = (src: string) => {
    let b = "", r = "";
    // 1. Structured BULL_THESIS / BEAR_THESIS sections
    const bullSection = src.match(/BULL_THESIS:\s*([\s\S]*?)(?=BEAR_THESIS:|CIO_DECISION:|$)/i);
    const bearSection = src.match(/BEAR_THESIS:\s*([\s\S]*?)(?=CIO_DECISION:|BULL_THESIS:|$)/i);
    if (bullSection) b = bullSection[1];
    if (bearSection) r = bearSection[1];
    // 2. CIO_DECISION format: Bull Summary / Bear Summary
    if (!b) {
      const bullSum = src.match(/Bull\s*Summary:\s*([\s\S]*?)(?=Bear\s*Summary:|Reasoning:|$)/i);
      if (bullSum) b = bullSum[1];
    }
    if (!r) {
      const bearSum = src.match(/Bear\s*Summary:\s*([\s\S]*?)(?=Reasoning:|Bull\s*Summary:|$)/i);
      if (bearSum) r = bearSum[1];
    }
    // 3. Generic bull/bear keyword split
    if (!b) {
      const bullSplit = src.match(/(?:bull|bullish)[_ ]?(?:case|thesis|advocate|analysis)?[:\s]+([\s\S]*?)(?=(?:bear|bearish)[_ ]?(?:case|thesis|advocate|analysis|summary)|CIO_DECISION|$)/i);
      b = bullSplit?.[1] || "";
    }
    if (!r) {
      const bearSplit = src.match(/(?:bear|bearish)[_ ]?(?:case|thesis|advocate|analysis)?[:\s]+([\s\S]*?)(?=CIO_DECISION|Reasoning:|$)/i);
      r = bearSplit?.[1] || "";
    }
    return { b, r };
  };

  // Debate output is at step index 3
  if (Array.isArray(backendSteps) && backendSteps.length >= 4) {
    const debateOutput = backendSteps[3]?.output || "";
    if (debateOutput) {
      const { b, r } = tryExtractBullBear(debateOutput);
      bullText = b;
      bearText = r;
    }
    if (!bullText && !bearText && backendSteps[3]?.output) {
      bullText = backendSteps[3].output;
      bearText = backendSteps[3].output;
    }
  }

  // Fallback: parse from full reply text
  if (!bullText || !bearText) {
    const { b, r } = tryExtractBullBear(text);
    if (!bullText) bullText = b;
    if (!bearText) bearText = r;
  }

  return {
    bull: { points: extractPoints(bullText), conviction: extractConviction(bullText) },
    bear: { points: extractPoints(bearText), conviction: extractConviction(bearText) },
  };
}

/* ── Periods / intervals for chart ── */
const PERIODS = [
  { label: "1D", period: "5d", interval: "15m" },
  { label: "1W", period: "1mo", interval: "1h" },
  { label: "1M", period: "6mo", interval: "1d" },
  { label: "3M", period: "1y", interval: "1d" },
  { label: "1Y", period: "2y", interval: "1d" },
];

/* ── Page ── */

export function Analyze() {
  const [ticker, setTicker] = useState("RELIANCE");
  const [loading, setLoading] = useState(false);
  const [trade, setTrade] = useState<TradeData | null>(null);
  const [steps, setSteps] = useState<StepData[] | null>(null);
  const [debate, setDebate] = useState<{ bull: { points: string[]; conviction: number } | null; bear: { points: string[]; conviction: number } | null }>({ bull: null, bear: null });
  const [selectedStepIndex, setSelectedStepIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Chart state
  const [periodIdx, setPeriodIdx] = useState(2); // default 1M
  const [chartView, setChartView] = useState<ChartView>("candlestick");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);

  const currentPeriod = PERIODS[periodIdx];

  // Auto-dismiss error
  useEffect(() => {
    if (!error) return;
    const id = setTimeout(() => setError(null), 6500);
    return () => clearTimeout(id);
  }, [error]);

  // Fetch chart data
  useEffect(() => {
    let cancelled = false;
    setChartLoading(true);
    setChartError(null);

    fetchMarket({
      ticker: ticker.trim() || "RELIANCE",
      period: currentPeriod.period,
      interval: currentPeriod.interval,
      limit: 260,
    })
      .then((d: { candles?: Candle[]; status?: string; error_message?: string }) => {
        if (cancelled) return;
        if (d.status !== "success") {
          setChartError(d.error_message || "Failed to load chart");
          setCandles([]);
        } else {
          setCandles(d.candles || []);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) setChartError(err.message);
      })
      .finally(() => {
        if (!cancelled) setChartLoading(false);
      });

    return () => { cancelled = true; };
  }, [ticker, periodIdx]);

  const handleRun = useCallback(async () => {
    setLoading(true);
    setError(null);
    setTrade(null);
    setSteps(null);
    setDebate({ bull: null, bear: null });
    setSelectedStepIndex(null);

    setSteps([
      { status: "running", summary: "Running AI pipeline…", output: null, duration: null },
      ...Array(6).fill({ status: "pending", summary: null, output: null, duration: null }),
    ]);

    try {
      const analysis = await runAnalysis(ticker);
      const reply = analysis?.reply || "";
      const backendSteps = analysis?.steps || null;
      const backendTrade = analysis?.trade || null;
      const backendDebate = analysis?.debate || null;

      // Build full text from reply + all step outputs for richer parsing
      let fullText = reply;
      if (Array.isArray(backendSteps)) {
        for (const step of backendSteps) {
          if (step?.output) fullText += "\n\n" + step.output;
        }
      }

      // Use structured trade data from server if available, else parse
      if (backendTrade && (backendTrade.action || backendTrade.entry)) {
        setTrade({
          ticker: backendTrade.ticker || ticker,
          action: backendTrade.action || null,
          entry: backendTrade.entry ?? null,
          stop: backendTrade.stop ?? null,
          target: backendTrade.target ?? null,
          riskReward: backendTrade.riskReward ?? null,
          regime: backendTrade.regime || null,
          conviction: backendTrade.conviction ?? null,
          killed: backendTrade.killed || false,
          killReason: backendTrade.killReason || null,
          riskDetails: backendTrade.riskDetails || null,
        });
      } else {
        const tradeData = parseTrade(fullText);
        setTrade({ ...tradeData, ticker: tradeData.ticker || ticker });
      }

      setSteps(parsePipelineSteps(fullText, backendSteps));

      // Use structured debate data from server if available, else parse
      if (backendDebate?.bull || backendDebate?.bear) {
        setDebate({
          bull: backendDebate.bull ? {
            points: backendDebate.bull.points || [],
            conviction: backendDebate.bull.conviction ?? 0.5,
          } : null,
          bear: backendDebate.bear ? {
            points: backendDebate.bear.points || [],
            conviction: backendDebate.bear.conviction ?? 0.5,
          } : null,
        });
      } else {
        setDebate(parseBullBear(fullText, backendSteps));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSteps(null);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleRun();
  };

  return (
    <div className="flex flex-col gap-4 pb-2">
      {/* Ticker Input + Run */}
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="analyze-ticker" className="text-sm text-muted-foreground whitespace-nowrap">
                Ticker
              </label>
              <Input
                id="analyze-ticker"
                placeholder="e.g. RELIANCE, TCS, INFY"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-[160px]"
              />
            </div>
            <Button type="submit" disabled={loading} className="gap-1.5">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {loading ? "Analyzing..." : "Run Analysis"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Decision + Chart (top row) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[480px]">
        <DecisionCard trade={trade} />

        <Card className="flex flex-col min-h-0">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {ticker} Chart
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 overflow-hidden flex-1 flex flex-col min-h-0">
            <div className="flex flex-wrap items-center gap-2">
              {PERIODS.map((p, i) => (
                <Button
                  key={p.label}
                  type="button"
                  variant={periodIdx === i ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPeriodIdx(i)}
                >
                  {p.label}
                </Button>
              ))}
              <div className="flex gap-2 border-l pl-3">
                <Button
                  type="button"
                  variant={chartView === "candlestick" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setChartView("candlestick")}
                >
                  Candlestick
                </Button>
                <Button
                  type="button"
                  variant={chartView === "line" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setChartView("line")}
                >
                  Line
                </Button>
              </div>
            </div>
            {chartLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : chartError ? (
              <p className="text-sm text-destructive py-8">{chartError}</p>
            ) : candles.length > 0 ? (
              <MarketChart candles={candles} ticker={ticker} view={chartView} className="flex-1 min-h-0" />
            ) : (
              <p className="text-sm text-muted-foreground py-8">No chart data.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pipeline + Debate (bottom row) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[400px]">
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

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-destructive text-white px-4 py-3 rounded-lg shadow-lg text-sm max-w-md z-50">
          <div className="flex items-center gap-2">
            <span className="flex-1 min-w-0 break-words">{error}</span>
            <button
              type="button"
              className="ml-2 text-white/80 hover:text-white"
              onClick={() => setError(null)}
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
