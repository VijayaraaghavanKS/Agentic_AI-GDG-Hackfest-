import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Gavel, Copy, Check, ShieldAlert, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface RiskDetails {
  regime?: string;
  action?: string;
  risk_reward?: string;
  risk_reward_ratio?: string;
  risk_per_share?: string;
  position_size?: string;
  total_risk?: string;
  full_reason?: string;
}

export interface TradeData {
  ticker: string | null;
  action: string | null;
  entry: number | null;
  stop: number | null;
  target: number | null;
  riskReward: number | null;
  regime: string | null;
  conviction: number | null;
  killed: boolean;
  killReason: string | null;
  riskDetails: RiskDetails | null;
}

function RejectionExplainer({ reason, action, regime }: { reason: string; action?: string | null; regime?: string | null }) {
  const r = reason.toLowerCase();
  let explanation: string | null = null;

  if (r.includes("hold action requires no trade")) {
    explanation = "The CIO Agent decided to HOLD. The risk engine rejects HOLD signals since there is no entry/exit to validate.";
  } else if (r.includes("conflicts with regime")) {
    explanation = `The trade direction (${action || "?"}) conflicts with the current market regime (${regime || "?"}). Going against the prevailing trend is blocked.`;
  } else if (r.includes("risk_per_share") && r.includes("not positive")) {
    explanation = "The stop loss is at or beyond the entry price, making the trade mathematically invalid.";
  } else if (r.includes("position_size") && r.includes("< 1")) {
    explanation = "Risk per share is too large relative to portfolio equity. Position size rounds to zero shares.";
  } else if (r.includes("risk_reward_ratio") && r.includes("min_risk_reward")) {
    explanation = "The potential reward does not justify the risk. Risk/reward ratio is below the minimum threshold.";
  }

  if (!explanation) return null;
  return <p className="text-muted-foreground leading-relaxed mt-1 text-xs">{explanation}</p>;
}

export function DecisionCard({ trade }: { trade: TradeData | null }) {
  const [copied, setCopied] = useState(false);
  const isRejected = Boolean(trade?.killed);

  if (!trade) {
    return (
      <Card className="relative overflow-hidden">
        <CardContent className="py-8">
          <div className="flex items-center gap-3 mb-4">
            <Gavel className="h-6 w-6 text-muted-foreground" />
            <h2 className="text-xl font-bold text-muted-foreground">No Analysis Yet</h2>
          </div>
          <p className="text-muted-foreground text-sm">Enter a ticker and click "Run Analysis" to begin.</p>
        </CardContent>
      </Card>
    );
  }

  const { ticker, action, entry, stop, target, riskReward, regime, killReason, riskDetails, conviction } = trade;
  const stampText = isRejected ? "REJECTED" : "ACCEPTED";

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
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // ignore clipboard failures
    }
  };

  return (
    <Card className="relative overflow-hidden">
      <CardContent className="pt-6">
        <div className="flex justify-between items-start">
          <div className="space-y-4 flex-1">
            {/* Ticker + Direction Badge */}
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-3xl font-bold tracking-tight">{ticker}</h2>
              <Badge variant="outline" className="text-xs">
                {ticker?.includes(".NS") ? "NSE" : ticker?.includes(".BO") ? "BSE" : "EQ"}
              </Badge>
              {action && action !== "HOLD" && (
                <Badge
                  className={cn(
                    "text-xs",
                    action === "BUY"
                      ? "bg-green-500/10 text-green-600 border-green-500/30"
                      : "bg-red-500/10 text-red-600 border-red-500/30"
                  )}
                >
                  {action === "BUY" ? (
                    <><TrendingUp className="h-3 w-3 mr-1" /> BUY</>
                  ) : (
                    <><TrendingDown className="h-3 w-3 mr-1" /> SELL</>
                  )}
                </Badge>
              )}
              {action === "HOLD" && (
                <Badge variant="secondary" className="text-xs">
                  <Minus className="h-3 w-3 mr-1" /> HOLD
                </Badge>
              )}
            </div>

            <p className="text-muted-foreground text-sm">
              Regime: <span className="font-semibold text-foreground">{regime || "—"}</span>
            </p>

            {/* Metrics Grid */}
            <div className="grid grid-cols-4 gap-6">
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Decision</p>
                <p className={cn(
                  "text-xl font-mono font-bold",
                  action === "BUY" ? "text-green-600 dark:text-green-400" : action === "SELL" ? "text-red-600 dark:text-red-400" : "text-muted-foreground"
                )}>
                  {action || "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Entry</p>
                <p className="text-xl font-mono">{entry ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Stop Loss</p>
                <p className="text-xl font-mono text-red-600 dark:text-red-400">{stop ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Target</p>
                <p className="text-xl font-mono text-green-600 dark:text-green-400">{target ?? "—"}</p>
              </div>
            </div>

            {/* Risk Reward */}
            <div className="flex items-center gap-6">
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Risk Reward</p>
                <p className="text-lg font-mono font-bold">{riskReward ?? "—"}</p>
              </div>
              {conviction != null && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase font-semibold mb-1">Conviction</p>
                  <p className="text-lg font-mono font-bold">{conviction}</p>
                </div>
              )}
            </div>

            {/* Rejection Details */}
            {isRejected && (
              <div className="p-3 rounded-md border border-red-500/20 bg-red-500/5">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert className="h-4 w-4 text-red-500" />
                  <p className="text-sm font-semibold text-red-600 dark:text-red-400">Risk Engine Rejection</p>
                </div>
                <p className="text-sm text-foreground mb-2">
                  {killReason || "Trade did not pass risk validation checks."}
                </p>
                {riskDetails && (
                  <div className="mt-2 space-y-1 text-xs font-mono">
                    {riskDetails.regime && riskDetails.action && (
                      <div className="flex justify-between text-muted-foreground">
                        <span>Direction vs Regime:</span>
                        <span className="text-foreground">{riskDetails.action} in {riskDetails.regime} regime</span>
                      </div>
                    )}
                    {riskDetails.risk_reward_ratio && (
                      <div className="flex justify-between text-muted-foreground">
                        <span>Risk/Reward Ratio:</span>
                        <span className="text-foreground">{riskDetails.risk_reward_ratio}</span>
                      </div>
                    )}
                    {riskDetails.risk_per_share && (
                      <div className="flex justify-between text-muted-foreground">
                        <span>Risk Per Share:</span>
                        <span className="text-foreground">{riskDetails.risk_per_share}</span>
                      </div>
                    )}
                    {riskDetails.position_size && (
                      <div className="flex justify-between text-muted-foreground">
                        <span>Position Size:</span>
                        <span className="text-foreground">{riskDetails.position_size}</span>
                      </div>
                    )}
                    {riskDetails.full_reason && riskDetails.full_reason !== killReason && (
                      <div className="mt-2 pt-2 border-t border-red-500/10">
                        <p className="text-muted-foreground mb-0.5">Full Explanation:</p>
                        <p className="text-foreground whitespace-pre-wrap">{riskDetails.full_reason}</p>
                      </div>
                    )}
                  </div>
                )}
                {!riskDetails && killReason && (
                  <RejectionExplainer reason={killReason} action={action} regime={regime} />
                )}
              </div>
            )}
          </div>

          {/* Stamp */}
          <div
            className={cn(
              "border-[3px] rounded px-4 py-2 -rotate-12 flex flex-col items-center justify-center select-none shrink-0 ml-4",
              isRejected
                ? "border-red-500/40 text-red-500/80 bg-red-500/5"
                : "border-green-500/40 text-green-500/80 bg-green-500/5"
            )}
          >
            {action && action !== "HOLD" && (
              <span className={cn(
                "text-[11px] font-mono font-bold uppercase tracking-widest mb-0.5",
                action === "BUY" ? "text-green-600" : "text-red-600"
              )}>
                {action}
              </span>
            )}
            <span className="text-2xl font-black tracking-widest uppercase">
              {stampText}
            </span>
            {isRejected ? (
              <span className="text-[10px] font-mono font-bold uppercase tracking-wide mt-1 max-w-[140px] text-center leading-tight">
                {action && action !== "HOLD" ? `${action} signal killed` : "Risk check failed"}
              </span>
            ) : (
              action && action !== "HOLD" && (
                <span className={cn(
                  "text-[10px] font-mono font-bold uppercase tracking-wide mt-1",
                  action === "BUY" ? "text-green-600/70" : "text-red-600/70"
                )}>
                  {action === "BUY" ? "Long position" : "Short position"}
                </span>
              )
            )}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy} className="gap-1.5">
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
