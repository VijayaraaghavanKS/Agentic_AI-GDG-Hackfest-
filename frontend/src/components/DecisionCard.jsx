export default function DecisionCard({ trade }) {
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

  const { ticker, action, entry, stop, target, riskReward, regime, killed, killReason } = trade;
  const isRejected = killed;
  const stampColor = isRejected ? "danger" : "success";
  const stampText = isRejected ? "REJECTED" : "ACCEPTED";
  const actionColor = action === "BUY" ? "text-success" : action === "SELL" ? "text-danger" : "text-slate-400";

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
            {killReason && (
              <div>
                <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Reason</p>
                <p className="text-sm text-slate-400">{killReason}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stamp */}
        <div
          className={`border-[3px] border-${stampColor}/40 text-${stampColor}/80 rounded px-4 py-2 stamp-rotate flex flex-col items-center justify-center select-none backdrop-blur-sm bg-${stampColor}/5 shadow-lg`}
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
    </div>
  );
}
