const PIPELINE_STEPS = [
  { name: "Quant Engine", icon: "calculate" },
  { name: "Quant Agent", icon: "analytics" },
  { name: "Sentiment Agent", icon: "psychology" },
  { name: "Bull Agent", icon: "trending_up" },
  { name: "Bear Agent", icon: "trending_down" },
  { name: "CIO Agent", icon: "gavel" },
  { name: "Risk Engine", icon: "shield" },
];

function StepItem({ step, index, status, summary, duration }) {
  const isComplete = status === "complete";
  const isRunning = status === "running";
  const isFlagged = status === "flagged";
  const isPending = status === "pending";

  let borderClass = "border-border-dark/50";
  let bgClass = "bg-[#0B0E11]/50";
  let iconBg = "bg-slate-800 text-slate-500";
  let iconSymbol = step.icon;

  if (isComplete) {
    iconBg = "bg-success/20 text-success";
    iconSymbol = "check";
  } else if (isRunning) {
    borderClass = "border-primary/40";
    bgClass = "bg-primary/5";
    iconBg = "bg-primary/20 text-primary animate-pulse";
    iconSymbol = "hourglass_top";
  } else if (isFlagged) {
    borderClass = "border-danger/30";
    bgClass = "bg-danger/5";
    iconBg = "bg-danger/20 text-danger";
    iconSymbol = "priority_high";
  }

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-md ${bgClass} border ${borderClass} animate-slide-in`}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className={`size-6 rounded-full ${iconBg} flex items-center justify-center shrink-0`}>
        <span className="material-symbols-outlined text-[16px]">{iconSymbol}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-slate-200">{step.name}</span>
          {duration && <span className="text-xs text-slate-500 font-mono">{duration}</span>}
          {isFlagged && <span className="text-xs text-danger font-mono font-bold">FLAGGED</span>}
          {isRunning && <span className="text-xs text-primary font-mono">Running…</span>}
        </div>
        {summary && <p className="text-xs text-slate-500 mt-0.5 truncate">{summary}</p>}
        {isPending && <p className="text-xs text-slate-600 mt-0.5">Waiting…</p>}
      </div>
    </div>
  );
}

export default function PipelineSteps({ steps }) {
  // steps: array of { status, summary, duration } matching PIPELINE_STEPS order
  const data = PIPELINE_STEPS.map((s, i) => ({
    ...s,
    ...(steps?.[i] || { status: "pending", summary: null, duration: null }),
  }));

  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg flex flex-col overflow-hidden max-h-[55%]">
      <div className="px-5 py-3 border-b border-border-dark flex justify-between items-center bg-[#0B0E11]/50">
        <h3 className="text-white font-semibold text-sm">AI Pipeline Execution</h3>
        <span className="text-xs text-slate-500 font-mono">
          {data.filter((d) => d.status === "complete").length}/{data.length} steps
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {data.map((d, i) => (
          <StepItem key={i} step={d} index={i} status={d.status} summary={d.summary} duration={d.duration} />
        ))}
      </div>
    </div>
  );
}
