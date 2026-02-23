import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Swords } from "lucide-react";

interface ThesisData {
  points: string[];
  conviction: number;
}

interface DebatePanelProps {
  bull: ThesisData | null;
  bear: ThesisData | null;
  selectedStepIndex: number | null;
}

const STEP_LABELS: Record<number, string> = {
  0: "Regime Analyst",
  1: "Stock Scanner",
  2: "Dividend Scanner",
  3: "Debate (Bull vs Bear)",
  4: "Trade Executor",
  5: "Portfolio Manager",
  6: "Autonomous Flow",
};

function ThesisPanel({
  type,
  points,
  conviction,
  highlighted,
}: {
  type: "bull" | "bear";
  points: string[];
  conviction: number;
  highlighted: boolean;
}) {
  const isBull = type === "bull";
  const pct = Math.round((conviction || 0) * 100);

  return (
    <div
      className={cn(
        "p-4 flex flex-col gap-3",
        highlighted && (isBull ? "ring-1 ring-green-500/25" : "ring-1 ring-red-500/25"),
        !isBull && "bg-red-500/5 dark:bg-red-500/5"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={cn(
            "text-sm font-bold flex items-center gap-1.5",
            isBull ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
          )}
        >
          {isBull ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
          {isBull ? "Bull Case" : "Bear Case"}
        </span>
        <span
          className={cn(
            "text-xs font-mono px-2 py-0.5 rounded border",
            isBull
              ? "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20"
              : "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20"
          )}
        >
          {conviction?.toFixed(1) ?? "—"}
        </span>
      </div>

      {/* Conviction Bar */}
      <div className="w-full bg-muted h-1.5 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full transition-all duration-700 ease-out rounded-full",
            isBull ? "bg-green-500" : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Points */}
      <ul className="space-y-2.5 mt-1">
        {(points || []).map((pt, i) => (
          <li key={i} className="flex items-start gap-2">
            <span
              className={cn(
                "mt-1.5 size-1.5 rounded-full shrink-0",
                isBull ? "bg-green-500" : "bg-red-500"
              )}
            />
            <p className="text-xs text-muted-foreground leading-relaxed">{pt}</p>
          </li>
        ))}
        {(!points || points.length === 0) && (
          <li className="text-xs text-muted-foreground">No data yet.</li>
        )}
      </ul>
    </div>
  );
}

export function DebatePanel({ bull, bear, selectedStepIndex }: DebatePanelProps) {
  const selectedLabel = selectedStepIndex != null ? STEP_LABELS[selectedStepIndex] ?? null : null;

  return (
    <Card className="overflow-hidden h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Swords className="h-5 w-5" />
          AI Investment Debate
        </CardTitle>
        {selectedLabel && (
          <span className="text-xs font-mono text-muted-foreground truncate ml-2">
            Selected: <span className="text-foreground">{selectedLabel}</span>
          </span>
        )}
      </CardHeader>
      <CardContent className="p-0 flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 sm:divide-x">
          <ThesisPanel
            type="bull"
            points={bull?.points || []}
            conviction={bull?.conviction || 0}
            highlighted={selectedStepIndex === 3}
          />
          <ThesisPanel
            type="bear"
            points={bear?.points || []}
            conviction={bear?.conviction || 0}
            highlighted={selectedStepIndex === 3}
          />
        </div>
      </CardContent>
    </Card>
  );
}
