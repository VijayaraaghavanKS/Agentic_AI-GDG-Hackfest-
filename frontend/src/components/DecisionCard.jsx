import { useMemo, useState } from "react";

/* Provide human-readable explanations for common risk engine rejection reasons */
function RejectionExplainer({ reason, action, regime }) {
  if (!reason) return null;
  const r = reason.toLowerCase();
  let explanation = null;

  if (r.includes("hold action requires no trade")) {
    explanation = "The CIO Agent decided to HOLD (no trade). The risk engine automatically rejects HOLD signals since there is no entry/exit to validate. This typically happens when the market regime is NEUTRAL and there is no clear directional edge.";
  } else if (r.includes("conflicts with regime")) {
    explanation = `The trade direction (${action || "?"}) conflicts with the current market regime (${regime || "?"}). For example, attempting to SELL in a BULL regime or BUY in a BEAR regime is blocked as it goes against the prevailing trend.`;
  } else if (r.includes("risk_per_share") && r.includes("not positive")) {
    explanation = "The calculated risk per share is zero or negative, meaning the stop loss is at or beyond the entry price. This makes the trade mathematically invalid — there must be a positive distance between entry and stop loss.";
  } else if (r.includes("position_size") && r.includes("< 1")) {
    explanation = "The risk per share is too large relative to the portfolio equity. With 1% max risk per trade, the position size rounds to zero shares. This protects against outsized single-trade losses.";
  } else if (r.includes("risk_reward_ratio") && r.includes("min_risk_reward")) {
    explanation = "The potential reward does not justify the risk. The risk/reward ratio is below the minimum threshold (typically 1:1.5). The target price is too close to entry relative to the stop loss distance.";
  }

  if (!explanation) return null;
  return <p className="text-slate-400 leading-relaxed mt-1">{explanation}</p>;
}

export default function DecisionCard({ trade }) {
  const isRejected = Boolean(trade?.killed);

  const stampClasses = useMemo(() => {
    if (isRejected) {
      return {
        border: "border-danger/40",
        text: "text-danger/80",
        bg: "bg-danger/5",
        badgeBg: "bg-danger/10",
        badgeText: "text-danger",
      };
    }
    return {
      border: "border-success/40",
      text: "text-success/80",
      bg: "bg-success/5",
      badgeBg: "bg-success/10",
      badgeText: "text-success",
    };
  }, [isRejected]);

  const [copied, setCopied] = useState(false);

  if (!trade) {
    return (
      <div className="bg-surface-dark border border-border-dark rounded-lg p-6 relative overflow-hidden shrink-0 animate-fade-in">
        <div className="absolute right-0 top-0 opacity-[0.03] pointer-events-none">
          <span className="material-symbols-outlined text-[200px]">gavel</span>
        </div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-2xl font-bold text-slate-500 tracking-tight">No Analysis Yet</h2>
        </div>
        <p className="text-slate-600 text-sm">Enter a ticker and click "Run Analysis" to begin.</p>
      </div>
    );
  }

  const { ticker, action, entry, stop, target, riskReward, regime, killReason, riskDetails, conviction } = trade;
  const stampText = isRejected ? "REJECTED" : "ACCEPTED";
  const actionColor = action === "BUY" ? "text-success" : action === "SELL" ? "text-danger" : "text-slate-400";

  const handleCopy = async () => {
    try {
      const lines = [
        `Ticker: ${ticker || "—"}`,
        `Regime: ${regime || "—"}`,
        `Decision: ${action || "—"}`,
        `Entry: ${entry ?? "—"}`,
        `Stop: ${stop ?? "—"}`,
        `Target: ${target ?? "—"}`,
        `Risk Reward: ${riskReward ?? "—"}`,
        isRejected ? `Status: REJECTED` : `Status: ACCEPTED`,
        killReason ? `Reason: ${killReason}` : null,
      ].filter(Boolean);

      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // ignore clipboard failures
    }
  };

  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg p-6 relative overflow-hidden shrink-0 animate-fade-in">
      {/* Watermark */}
      <div className="absolute right-0 top-0 opacity-[0.03] pointer-events-none">
        <span className="material-symbols-outlined text-[200px]">gavel</span>
      </div>

      <div className="flex justify-between items-start relative z-10">
        <div>
          {/* Ticker */}
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-3xl font-bold text-white tracking-tight">{ticker}</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
              {ticker?.includes(".NS") ? "NSE" : ticker?.includes(".BO") ? "BSE" : "EQ"}
            </span>
          </div>
          <p className="text-slate-500 text-sm mb-6">Regime: <span className="text-slate-300 font-semibold">{regime || "—"}</span></p>

          {/* Metrics Grid */}
          <div className="grid grid-cols-4 gap-8">
            <div>
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Decision</p>
              <p className={`text-xl font-mono font-bold ${actionColor}`}>{action || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Entry</p>
              <p className="text-xl font-mono text-white">{entry ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Stop Loss</p>
              <p className="text-xl font-mono text-danger">{stop ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Target</p>
              <p className="text-xl font-mono text-success">{target ?? "—"}</p>
            </div>
          </div>

          {/* Risk Reward */}
          <div className="mt-4 flex items-center gap-6">
            <div>
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Risk Reward</p>
              <p className="text-lg font-mono text-white font-bold">{riskReward ?? "—"}</p>
            </div>
            {conviction != null && (
              <div>
                <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Conviction</p>
                <p className="text-lg font-mono text-white font-bold">{conviction}</p>
              </div>
            )}
          </div>

          {/* Rejection Details Panel */}
          {isRejected && (
            <div className="mt-4 p-3 rounded-md border border-danger/20 bg-danger/5">
              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-danger text-[18px]">block</span>
                <p className="text-sm font-semibold text-danger">Risk Engine Rejection</p>
              </div>
              <p className="text-sm text-slate-300 mb-2">
                {killReason || "Trade did not pass risk validation checks."}
              </p>
              {riskDetails && (
                <div className="mt-2 space-y-1 text-xs font-mono">
                  {riskDetails.regime && riskDetails.action && (
                    <div className="flex justify-between text-slate-400">
                      <span>Direction vs Regime:</span>
                      <span className="text-slate-300">{riskDetails.action} in {riskDetails.regime} regime</span>
                    </div>
                  )}
                  {riskDetails.risk_reward && (
                    <div className="flex justify-between text-slate-400">
                      <span>Risk/Reward Ratio:</span>
                      <span className="text-slate-300">{riskDetails.risk_reward}</span>
                    </div>
                  )}
                  {riskDetails.risk_reward_ratio && (
                    <div className="flex justify-between text-slate-400">
                      <span>Risk/Reward Ratio:</span>
                      <span className="text-slate-300">{riskDetails.risk_reward_ratio}</span>
                    </div>
                  )}
                  {riskDetails.risk_per_share && (
                    <div className="flex justify-between text-slate-400">
                      <span>Risk Per Share:</span>
                      <span className="text-slate-300">{riskDetails.risk_per_share}</span>
                    </div>
                  )}
                  {riskDetails.position_size && (
                    <div className="flex justify-between text-slate-400">
                      <span>Position Size:</span>
                      <span className="text-slate-300">{riskDetails.position_size}</span>
                    </div>
                  )}
                  {riskDetails.total_risk && (
                    <div className="flex justify-between text-slate-400">
                      <span>Total Risk:</span>
                      <span className="text-slate-300">{riskDetails.total_risk}</span>
                    </div>
                  )}
                  {riskDetails.full_reason && riskDetails.full_reason !== killReason && (
                    <div className="mt-2 pt-2 border-t border-danger/10">
                      <p className="text-slate-500 mb-0.5">Full Explanation:</p>
                      <p className="text-slate-400 whitespace-pre-wrap">{riskDetails.full_reason}</p>
                    </div>
                  )}
                </div>
              )}
              {!riskDetails && killReason && (
                <div className="mt-1 text-xs text-slate-500 font-mono">
                  <RejectionExplainer reason={killReason} action={action} regime={regime} />
                </div>
              )}
            </div>
          )}

          {/* Non-rejected reason (if any) */}
          {!isRejected && killReason && (
            <div className="mt-4">
              <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Note</p>
              <p className="text-sm text-slate-400">{killReason}</p>
            </div>
          )}
        </div>

        {/* Stamp */}
        <div
          className={`border-[3px] ${stampClasses.border} ${stampClasses.text} rounded px-4 py-2 stamp-rotate flex flex-col items-center justify-center select-none backdrop-blur-sm ${stampClasses.bg} shadow-lg`}
        >
          <span className="text-2xl font-black tracking-widest uppercase" style={{ fontFamily: "'Stencil', 'Impact', sans-serif" }}>
            {stampText}
          </span>
          {isRejected && (
            <span className="text-[10px] font-mono font-bold uppercase tracking-wide mt-1">
              {killReason || "Risk check failed"}
            </span>
          )}
        </div>
      </div>

      <div className="mt-5 flex items-center justify-end gap-2 relative z-10">
        {copied && (
          <span className={`text-xs font-mono px-2 py-1 rounded border border-border-dark ${stampClasses.badgeBg} ${stampClasses.badgeText}`}>
            Copied
          </span>
        )}
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border-dark bg-[#0B0E11]/60 hover:bg-[#0B0E11] text-xs text-slate-300 transition-colors"
          title="Copy trade to clipboard"
          aria-label="Copy trade to clipboard"
        >
          <span className="material-symbols-outlined text-[16px]">content_copy</span>
          Copy
        </button>
      </div>
    </div>
  );
}
