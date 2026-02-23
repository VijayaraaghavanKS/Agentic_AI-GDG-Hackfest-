import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2, AlertTriangle, Clock, ChevronDown, ChevronUp, Workflow } from "lucide-react";

const PIPELINE_STEPS = [
  { name: "Regime Analyst", icon: "analytics" },
  { name: "Stock Scanner", icon: "search" },
  { name: "Dividend Scanner", icon: "payments" },
  { name: "Debate (Bull vs Bear)", icon: "gavel" },
  { name: "Trade Executor", icon: "trending_up" },
  { name: "Portfolio Manager", icon: "account_balance" },
  { name: "Autonomous Flow", icon: "smart_toy" },
];

export interface StepData {
  status: "pending" | "running" | "complete" | "flagged";
  summary: string | null;
  output: string | null;
  duration: string | null;
}

interface PipelineStepsProps {
  steps: StepData[] | null;
  selectedIndex: number | null;
  onSelectStep: (index: number | null) => void;
}

function StepIcon({ status }: { status: string }) {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "running":
      return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
    case "flagged":
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function StepOutput({ text }: { text: string }) {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return null;

  return (
    <div className="mt-1 mb-2 p-3 bg-muted/50 border rounded-md overflow-y-auto max-h-48">
      <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
        {lines.map((line, i) => {
          const kv = line.match(/^([A-Za-z][A-Za-z_ ]+):\s*(.+)/);
          if (kv) {
            return (
              <span key={i}>
                <span className="text-primary font-semibold">{kv[1]}:</span>{" "}
                <span className="text-foreground">{kv[2]}</span>
                {"\n"}
              </span>
            );
          }
          if (/^[A-Z_]{3,}/.test(line.trim()) || /^#+\s/.test(line.trim())) {
            return (
              <span key={i} className="text-foreground font-semibold">
                {line}
                {"\n"}
              </span>
            );
          }
          return (
            <span key={i}>
              {line}
              {"\n"}
            </span>
          );
        })}
      </pre>
    </div>
  );
}

export function PipelineSteps({ steps, selectedIndex, onSelectStep }: PipelineStepsProps) {
  const data = PIPELINE_STEPS.map((s, i) => ({
    ...s,
    ...(steps?.[i] || { status: "pending" as const, summary: null, output: null, duration: null }),
  }));

  const completedCount = data.filter((d) => d.status === "complete" || d.status === "flagged").length;
  const hasAnyOutput = data.some((d) => d.output);

  return (
    <Card className="overflow-hidden h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Workflow className="h-5 w-5" />
          AI Pipeline
        </CardTitle>
        <div className="flex items-center gap-2">
          {hasAnyOutput && (
            <span className="text-xs text-muted-foreground">Click step for details</span>
          )}
          <span className="text-xs text-muted-foreground font-mono">
            {completedCount}/{data.length}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-1 flex-1 overflow-y-auto">
        {data.map((d, i) => {
          const selected = selectedIndex === i;
          const clickable = Boolean(d.output);

          return (
            <div key={i}>
              <button
                type="button"
                onClick={() => clickable && onSelectStep(selected ? null : i)}
                className={cn(
                  "w-full text-left flex items-center gap-3 p-2.5 rounded-md border transition-colors",
                  d.status === "running" && "border-primary/40 bg-primary/5",
                  d.status === "flagged" && "border-red-500/30 bg-red-500/5",
                  d.status === "complete" && "border-border",
                  d.status === "pending" && "border-border/50 opacity-60",
                  selected && "ring-1 ring-primary/30 bg-primary/5",
                  clickable && "hover:border-primary/30 hover:bg-accent cursor-pointer"
                )}
              >
                <StepIcon status={d.status} />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{d.name}</span>
                    {d.duration && (
                      <span className="text-xs text-muted-foreground font-mono">{d.duration}</span>
                    )}
                    {d.status === "flagged" && (
                      <span className="text-xs text-red-500 font-mono font-bold">FLAGGED</span>
                    )}
                    {d.status === "running" && (
                      <span className="text-xs text-primary font-mono">Running...</span>
                    )}
                    {d.status === "complete" && clickable && (
                      selected ? (
                        <ChevronUp className="h-3.5 w-3.5 text-primary" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                      )
                    )}
                  </div>
                  {d.summary && (
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">{d.summary}</p>
                  )}
                  {d.status === "pending" && (
                    <p className="text-xs text-muted-foreground mt-0.5">Waiting...</p>
                  )}
                </div>
              </button>
              {selected && d.output && <StepOutput text={d.output} />}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
