function ThesisPanel({ type, points, conviction }) {
  const isBull = type === "bull";
  const color = isBull ? "success" : "danger";
  const icon = isBull ? "trending_up" : "trending_down";
  const label = isBull ? "Bull Case" : "Bear Case";
  const pct = Math.round((conviction || 0) * 100);

  return (
    <div className={`p-4 flex flex-col gap-3 ${!isBull ? "bg-red-900/5" : ""}`}>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-sm font-bold text-${color} flex items-center gap-1`}>
          <span className="material-symbols-outlined text-sm">{icon}</span> {label}
        </span>
        <span className={`text-xs font-mono bg-${color}/10 text-${color} px-2 py-0.5 rounded border border-${color}/20`}>
          {conviction?.toFixed(1) ?? "—"}
        </span>
      </div>

      {/* Conviction Bar */}
      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
        <div
          className={`bg-${color} h-full transition-all duration-700 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Points */}
      <ul className="space-y-2.5 mt-1">
        {(points || []).map((pt, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className={`mt-1 size-1.5 rounded-full bg-${color} shrink-0`} />
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

export default function DebatePanel({ bull, bear }) {
  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg flex-1 flex flex-col overflow-hidden">
      <div className="px-5 py-3 border-b border-border-dark flex items-center gap-2 bg-[#0B0E11]/50">
        <span className="material-symbols-outlined text-slate-400 text-sm">psychology</span>
        <h3 className="text-white font-semibold text-sm">AI Investment Debate</h3>
      </div>
      <div className="grid grid-cols-2 h-full divide-x divide-border-dark overflow-y-auto">
        <ThesisPanel type="bull" points={bull?.points} conviction={bull?.conviction} />
        <ThesisPanel type="bear" points={bear?.points} conviction={bear?.conviction} />
      </div>
    </div>
  );
}
