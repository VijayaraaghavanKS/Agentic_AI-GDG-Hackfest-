const PIPELINE_STEPS = [
  { name: "Quant Engine", icon: "calculate" },
  { name: "Quant Agent", icon: "analytics" },
  { name: "Sentiment Agent", icon: "psychology" },
  { name: "Bull Agent", icon: "trending_up" },
  { name: "Bear Agent", icon: "trending_down" },
  { name: "CIO Agent", icon: "gavel" },
  { name: "Risk Engine", icon: "shield" },
];

function StepItem({ step, index, status, summary, duration, selected, onSelect }) {
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

  const selectedRing = selected ? "ring-1 ring-primary/30 bg-primary/5" : "";
  const clickable = typeof onSelect === "function";

  return (
    <button
      type="button"
      onClick={() => clickable && onSelect(selected ? null : index)}
      className={`w-full text-left flex items-center gap-3 p-3 rounded-md ${bgClass} border ${borderClass} ${selectedRing} animate-slide-in ${clickable ? "hover:border-primary/30 hover:bg-primary/5 cursor-pointer" : ""}`}
      style={{ animationDelay: `${index * 80}ms` }}
      aria-pressed={selected ? "true" : "false"}
      title={`${step.name}${summary ? ` — ${summary}` : ""}`}
    >
      <div className={`size-6 rounded-full ${iconBg} flex items-center justify-center shrink-0`}>
        <span className="material-symbols-outlined text-[16px]">{iconSymbol}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-slate-200">{step.name}</span>
          {duration && <span className="text-xs text-slate-500 font-mono">{duration}</span>}
          {isFlagged && <span className="text-xs text-danger font-mono font-bold">FLAGGED</span>}
          {isRunning && <span className="text-xs text-primary font-mono">Running...</span>}
          {isComplete && !isFlagged && !isRunning && selected && (
            <span className="material-symbols-outlined text-[14px] text-primary">expand_less</span>
          )}
          {isComplete && !isFlagged && !isRunning && !selected && (
            <span className="material-symbols-outlined text-[14px] text-slate-600">expand_more</span>
          )}
        </div>
        {summary && <p className="text-xs text-slate-500 mt-0.5 truncate">{summary}</p>}
        {isPending && <p className="text-xs text-slate-600 mt-0.5">Waiting...</p>}
      </div>
    </button>
  );
}

function StepOutput({ text }) {
  if (!text) return null;
  // Clean up and format the output text
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return null;

  return (
    <div className="mt-1 mb-2 mx-2 p-3 bg-[#0B0E11] border border-border-dark/50 rounded-md overflow-y-auto max-h-48 animate-fade-in">
      <pre className="text-xs text-slate-400 whitespace-pre-wrap font-mono leading-relaxed">
        {lines.map((line, i) => {
          // Highlight key-value lines
          const kv = line.match(/^([A-Za-z][A-Za-z_ ]+):\s*(.+)/);
          if (kv) {
            return (
              <span key={i}>
                <span className="text-primary/80 font-semibold">{kv[1]}:</span>{" "}
                <span className="text-slate-300">{kv[2]}</span>
                {"\n"}
              </span>
            );
          }
          // Highlight section headers (all caps or ending with colon)
          if (/^[A-Z_]{3,}/.test(line.trim()) || /^#+\s/.test(line.trim())) {
            return (
              <span key={i} className="text-slate-200 font-semibold">
                {line}
                {"\n"}
              </span>
            );
          }
          return <span key={i}>{line}{"\n"}</span>;
        })}
      </pre>
    </div>
  );
}

export default function PipelineSteps({ steps, selectedIndex, onSelectStep }) {
  // steps: array of { status, summary, duration, output } matching PIPELINE_STEPS order
  const data = PIPELINE_STEPS.map((s, i) => ({
    ...s,
    ...(steps?.[i] || { status: "pending", summary: null, duration: null, output: null }),
  }));

  const completedCount = data.filter((d) => d.status === "complete" || d.status === "flagged").length;
  const hasAnyOutput = data.some((d) => d.output);

  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg flex flex-col overflow-hidden max-h-[55%]">
      <div className="px-5 py-3 border-b border-border-dark flex justify-between items-center bg-[#0B0E11]/50">
        <h3 className="text-white font-semibold text-sm">AI Pipeline Execution</h3>
        <div className="flex items-center gap-2">
          {hasAnyOutput && (
            <span className="text-[10px] text-slate-600">Click step for details</span>
          )}
          <span className="text-xs text-slate-500 font-mono">
            {completedCount}/{data.length} steps
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {data.map((d, i) => (
          <div key={i}>
            <StepItem
              step={d}
              index={i}
              status={d.status}
              summary={d.summary}
              duration={d.duration}
              selected={selectedIndex === i}
              onSelect={d.output ? onSelectStep : undefined}
            />
            {selectedIndex === i && d.output && <StepOutput text={d.output} />}
          </div>
        ))}
      </div>
    </div>
  );
}
