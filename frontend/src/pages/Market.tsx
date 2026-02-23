import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, BarChart3 } from "lucide-react";
import { MarketChart, type Candle, type ChartView } from "@/components/MarketChart";

const PERIODS = [
  { label: "1M", value: "1mo" },
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "2Y", value: "2y" },
];

const INTERVALS = [
  { label: "Daily", value: "1d" },
  { label: "Weekly", value: "1wk" },
];

const DEFAULT_TICKER = "RELIANCE";

export function Market() {
  const [ticker, setTicker] = useState(DEFAULT_TICKER);
  const [period, setPeriod] = useState("6mo");
  const [chartInterval, setChartInterval] = useState("1d");
  const [limit] = useState(500);
  const [data, setData] = useState<{ candles: Candle[]; ticker: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartView, setChartView] = useState<ChartView>("candlestick");

  const fetchMarket = () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      ticker: ticker.trim() || DEFAULT_TICKER,
      period,
      interval: chartInterval,
      limit: String(limit),
    });
    fetch(`/api/market?${params}`)
      .then((res) => res.json())
      .then((d) => {
        if (d.status !== "success") {
          setError(d.error_message || "Failed to load market data");
          setData(null);
        } else {
          setData({ candles: d.candles, ticker: d.ticker });
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Network error");
        setData(null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchMarket();
  }, [period, chartInterval]);

  const handleTickerSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchMarket();
  };

  return (
    <div className="flex flex-col gap-4 min-h-[calc(100vh-7.5rem)]">
      <Card className="flex flex-col flex-1 min-h-[500px]">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Market Chart
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 flex-1 flex flex-col min-h-0">
          <form onSubmit={handleTickerSubmit} className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="ticker" className="text-sm text-muted-foreground whitespace-nowrap">
                Ticker
              </label>
              <Input
                id="ticker"
                placeholder="e.g. RELIANCE, ^NSEI"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-[140px]"
              />
            </div>
            <div className="flex gap-2">
              {PERIODS.map((p) => (
                <Button
                  key={p.value}
                  type="button"
                  variant={period === p.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setPeriod(p.value)}
                >
                  {p.label}
                </Button>
              ))}
            </div>
            <div className="flex gap-2">
              {INTERVALS.map((i) => (
                <Button
                  key={i.value}
                  type="button"
                  variant={chartInterval === i.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setChartInterval(i.value)}
                >
                  {i.label}
                </Button>
              ))}
            </div>
            <Button type="submit" size="sm">
              Apply
            </Button>
            <div className="flex gap-2 border-l pl-3">
              <Button
                type="button"
                variant={chartView === "candlestick" ? "default" : "outline"}
                size="sm"
                onClick={() => setChartView("candlestick")}
              >
                Candlestick
              </Button>
              <Button
                type="button"
                variant={chartView === "line" ? "default" : "outline"}
                size="sm"
                onClick={() => setChartView("line")}
              >
                Line
              </Button>
            </div>
          </form>

          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive py-8">{error}</p>
          ) : data && data.candles.length > 0 ? (
            <>
              <p className="text-sm text-muted-foreground">
                {data.ticker} · {period} · {chartInterval}
              </p>
              <MarketChart candles={data.candles} ticker={data.ticker} view={chartView} className="flex-1 min-h-0" />
            </>
          ) : (
            <p className="text-sm text-muted-foreground py-8">No data. Change ticker or period and Apply.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
