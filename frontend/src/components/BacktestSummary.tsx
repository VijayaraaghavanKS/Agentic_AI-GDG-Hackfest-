import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Loader2, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

type OversoldVariant = "best5" | "first5";

interface BacktestRow {
  symbol: string;
  win_rate_pct?: number;
  avg_return_pct?: number;
  pnl_inr?: number;
  total_trades?: number;
}

interface BacktestDataBest {
  status: string;
  total_passed?: number;
  total_best_pnl_inr?: number;
  best_stocks?: BacktestRow[];
  error_message?: string;
}

interface BacktestDataFirst {
  status: string;
  starting_capital_inr?: number;
  ending_capital_inr?: number;
  total_pnl_inr?: number;
  total_pnl_pct?: number;
  stocks_with_trades?: number;
  top_by_win_rate?: BacktestRow[];
  per_stock?: BacktestRow[];
  error_message?: string;
}

function formatINR(value: number | null | undefined) {
  if (value === null || value === undefined || isNaN(value)) return "-";
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function BacktestSummary() {
  const [variant, setVariant] = useState<OversoldVariant>("best5");
  const [data, setData] = useState<BacktestDataBest | BacktestDataFirst | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBacktest = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      if (variant === "best5") {
        const res = await fetch("/api/backtest/oversold-best?top_n=5");
        const d: BacktestDataBest = await res.json();
        if (d.status !== "success") {
          setError(d.error_message || "Backtest failed");
        } else {
          setData(d);
        }
      } else {
        const res = await fetch("/api/backtest/oversold-summary?max_stocks=5");
        const d: BacktestDataFirst = await res.json();
        if (d.status !== "success") {
          setError(d.error_message || "Backtest failed");
        } else {
          setData(d);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const isBest = variant === "best5";
  const bestData = data as BacktestDataBest | null;
  const firstData = data as BacktestDataFirst | null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Oversold backtest (Nifty 50)
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={fetchBacktest} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-3">
          <Button
            variant={variant === "best5" ? "default" : "outline"}
            size="sm"
            onClick={() => setVariant("best5")}
          >
            Top 5 (best)
          </Button>
          <Button
            variant={variant === "first5" ? "default" : "outline"}
            size="sm"
            onClick={() => setVariant("first5")}
          >
            First 5 (Nifty)
          </Button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Running 2Y backtest {isBest ? "(all 50, then top 5)" : "(first 5)"}…
            </span>
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : data ? (
          <div className="space-y-4">
            {isBest && bestData ? (
              <>
                <p className="text-xs text-muted-foreground">
                  Best 5 = stocks that pass win rate ≥50%, ≥3 trades (from full Nifty 50 backtest).
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stocks passing</span>
                    <span className="font-medium">{bestData.total_passed ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">P&L (top 5 only)</span>
                    <span
                      className={cn(
                        "font-medium",
                        (bestData.total_best_pnl_inr ?? 0) >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      )}
                    >
                      {formatINR(bestData.total_best_pnl_inr)}
                    </span>
                  </div>
                </div>
                {bestData.best_stocks && bestData.best_stocks.length > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-xs font-medium text-muted-foreground mb-2">Top 5 (best performers)</p>
                    <div className="space-y-1 text-sm">
                      {bestData.best_stocks.map((row) => (
                        <div key={row.symbol} className="flex justify-between">
                          <span className="font-medium">{row.symbol.replace(".NS", "")}</span>
                          <span className="text-muted-foreground">
                            {row.win_rate_pct ?? "-"}% win, {row.avg_return_pct != null ? `${row.avg_return_pct.toFixed(2)}%` : "-"} avg
                            {row.pnl_inr != null ? ` · ${formatINR(row.pnl_inr)}` : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : firstData ? (
              <>
                <p className="text-xs text-muted-foreground">
                  First 5 = first 5 stocks in Nifty 50 watchlist order (RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK).
                </p>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Starting capital</span>
                    <span className="font-medium">{formatINR(firstData.starting_capital_inr)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Ending capital</span>
                    <span className="font-medium">{formatINR(firstData.ending_capital_inr)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total P&L</span>
                    <span
                      className={cn(
                        "font-medium",
                        (firstData.total_pnl_inr ?? 0) >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      )}
                    >
                      {formatINR(firstData.total_pnl_inr)}
                      {firstData.total_pnl_pct != null ? ` (${firstData.total_pnl_pct}%)` : ""}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stocks with trades</span>
                    <span className="font-medium">{firstData.stocks_with_trades ?? 0}</span>
                  </div>
                </div>
                {(firstData.per_stock?.length ?? 0) > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-xs font-medium text-muted-foreground mb-2">First 5 (Nifty order)</p>
                    <div className="space-y-1 text-sm">
                      {(firstData.per_stock ?? []).slice(0, 5).map((row) => (
                        <div key={row.symbol} className="flex justify-between">
                          <span className="font-medium">{row.symbol.replace(".NS", "")}</span>
                          <span className="text-muted-foreground">
                            {row.win_rate_pct != null ? `${row.win_rate_pct}%` : "-"} win, {row.avg_return_pct != null ? `${row.avg_return_pct.toFixed(2)}%` : "-"} avg
                            {row.pnl_inr != null ? ` · ${formatINR(row.pnl_inr)}` : ""}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Choose Top 5 (best) or First 5 (Nifty), then click refresh to run 2Y oversold backtest.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
