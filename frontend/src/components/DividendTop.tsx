import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, Loader2, Gift } from "lucide-react";
import { cn } from "@/lib/utils";

interface DividendOpportunity {
  symbol: string;
  ex_date?: string;
  dividend_health?: string;
  suggested_entry?: number;
  suggested_stop?: number;
  company?: string;
  days_to_ex?: number;
  dividend_yield_pct?: number;
  current_price?: number;
}

interface DividendData {
  status: string;
  opportunities_count?: number;
  top_opportunities?: DividendOpportunity[];
  message?: string;
  error_message?: string;
}

function formatINR(value: number | null | undefined) {
  if (value === null || value === undefined || isNaN(value)) return "-";
  return value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function DividendTop() {
  const [data, setData] = useState<DividendData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDividend = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/dividend/top");
      const d: DividendData = await res.json();
      if (d.status !== "success") {
        setError(d.error_message || "Failed to fetch dividend opportunities");
      } else {
        setData(d);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDividend();
  }, []);

  const opportunities = data?.top_opportunities ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Gift className="h-5 w-5" />
          Dividend opportunities
        </CardTitle>
        <Button variant="ghost" size="icon" onClick={fetchDividend} disabled={loading}>
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : opportunities.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {data?.message ?? "No upcoming dividend opportunities. Click refresh to scan."}
          </p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground mb-3">
              {data?.opportunities_count ?? 0} opportunities — ask in chat to backtest or paper trade.
            </p>
            <ScrollArea className="h-[220px] rounded-md border overflow-x-auto">
              <Table className="table-fixed w-full min-w-[520px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Health</TableHead>
                    <TableHead>Ex-Date</TableHead>
                    <TableHead className="text-right">Yield %</TableHead>
                    <TableHead className="text-right">Entry</TableHead>
                    <TableHead className="text-right">Stop</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {opportunities.slice(0, 8).map((o) => (
                    <TableRow key={o.symbol}>
                      <TableCell className="font-medium" title={o.company}>{o.symbol?.replace('.NS', '') ?? o.symbol}</TableCell>
                      <TableCell>{o.dividend_health ?? "-"}</TableCell>
                      <TableCell>{o.ex_date ?? "-"}{o.days_to_ex != null ? ` (${o.days_to_ex}d)` : ""}</TableCell>
                      <TableCell className="text-right">{o.dividend_yield_pct != null ? `${o.dividend_yield_pct.toFixed(1)}%` : "-"}</TableCell>
                      <TableCell className="text-right">{formatINR(o.suggested_entry)}</TableCell>
                      <TableCell className="text-right">{formatINR(o.suggested_stop)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </>
        )}
      </CardContent>
    </Card>
  );
}
