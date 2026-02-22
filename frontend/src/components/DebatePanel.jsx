function ThesisPanel({ type, points, conviction, highlighted }) {
  const isBull = type === "bull";
  const icon = isBull ? "trending_up" : "trending_down";
  const label = isBull ? "Bull Case" : "Bear Case";
  const pct = Math.round((conviction || 0) * 100);

  const cls = isBull
    ? {
        text: "text-success",
        chipBg: "bg-success/10",
        chipText: "text-success",
        chipBorder: "border-success/20",
        dot: "bg-success",
        bar: "bg-success",
        panelBg: "bg-transparent",
        highlight: "ring-1 ring-success/25",
      }
    : {
        text: "text-danger",
        chipBg: "bg-danger/10",
        chipText: "text-danger",
        chipBorder: "border-danger/20",
        dot: "bg-danger",
        bar: "bg-danger",
        panelBg: "bg-danger/5",
        highlight: "ring-1 ring-danger/25",
      };

  return (
    <div className={`p-4 flex flex-col gap-3 ${cls.panelBg} ${highlighted ? cls.highlight : ""}`}>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-sm font-bold ${cls.text} flex items-center gap-1`}>
          <span className="material-symbols-outlined text-sm">{icon}</span> {label}
        </span>
        <span className={`text-xs font-mono ${cls.chipBg} ${cls.chipText} px-2 py-0.5 rounded border ${cls.chipBorder}`}>
          {conviction?.toFixed(1) ?? "—"}
        </span>
      </div>

      {/* Conviction Bar */}
      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
        <div
          className={`${cls.bar} h-full transition-all duration-700 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Points */}
      <ul className="space-y-2.5 mt-1">
        {(points || []).map((pt, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className={`mt-1 size-1.5 rounded-full ${cls.dot} shrink-0`} />
            <p className="text-xs text-slate-400 leading-relaxed">{pt}</p>
          </li>
        ))}
        {(!points || points.length === 0) && (
          <li className="text-xs text-slate-600">No data yet.</li>
        )}
      </ul>
    </div>
  );
}

export default function DebatePanel({ bull, bear, selectedStepIndex }) {
  const selectedLabel =
    selectedStepIndex === 3
      ? "Bull Agent"
      : selectedStepIndex === 4
        ? "Bear Agent"
        : selectedStepIndex === 5
          ? "CIO Agent"
          : selectedStepIndex === 6
            ? "Risk Engine"
            : selectedStepIndex === 2
              ? "Sentiment Agent"
              : selectedStepIndex === 1
                ? "Quant Agent"
                : selectedStepIndex === 0
                  ? "Quant Engine"
                  : null;

  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg flex-1 flex flex-col overflow-hidden">
      <div className="px-5 py-3 border-b border-border-dark flex items-center gap-2 bg-[#0B0E11]/50">
        <span className="material-symbols-outlined text-slate-400 text-sm">psychology</span>
        <h3 className="text-white font-semibold text-sm">AI Investment Debate</h3>
        {selectedLabel && (
          <span className="ml-auto text-xs font-mono text-slate-500">
            Selected: <span className="text-slate-300">{selectedLabel}</span>
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 h-full divide-x divide-border-dark overflow-y-auto">
        <ThesisPanel
          type="bull"
          points={bull?.points}
          conviction={bull?.conviction}
          highlighted={selectedStepIndex === 3}
        />
        <ThesisPanel
          type="bear"
          points={bear?.points}
          conviction={bear?.conviction}
          highlighted={selectedStepIndex === 4}
        />
      </div>
    </div>
  );
}
