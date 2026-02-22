import { useMemo, useState, useCallback } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { cn } from "@/lib/utils";

export interface Candle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  rsi?: number | null;
}

export type ChartView = "candlestick" | "line";

interface MarketChartProps {
  candles: Candle[];
  ticker: string;
  view: ChartView;
  className?: string;
}

function formatINR(v: number) {
  return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

// —— Realistic candlestick chart (custom SVG) ——
function CandlestickSVG({
  candles,
  width,
  height,
  onHover,
  hoverIndex,
}: {
  candles: Candle[];
  width: number;
  height: number;
  onHover: (index: number | null) => void;
  hoverIndex: number | null;
}) {
  const padding = { top: 16, right: 48, bottom: 28, left: 52 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const { priceMin, priceMax, volMax, xScale, yScale, volScale } = useMemo(() => {
    const lows = candles.map((c) => c.low);
    const highs = candles.map((c) => c.high);
    const priceMin = Math.min(...lows) * 0.998;
    const priceMax = Math.max(...highs) * 1.002;
    const volMax = Math.max(...candles.map((c) => c.volume), 1) * 1.05;
    const n = candles.length;
    const xScale = (i: number) => padding.left + (i / Math.max(n - 1, 1)) * chartW;
    const yScale = (p: number) => padding.top + chartH - ((p - priceMin) / (priceMax - priceMin)) * chartH;
    const volScale = (v: number) => (v / volMax) * chartH;
    return { priceMin, priceMax, volMax, xScale, yScale, volScale };
  }, [candles, chartW, chartH]);

  const candleWidth = Math.max(2, Math.min(12, chartW / candles.length - 1));
  const volumeHeight = 72;
  const priceChartH = chartH - volumeHeight;

  const yScalePrice = (p: number) =>
    padding.top + priceChartH - ((p - priceMin) / (priceMax - priceMin)) * priceChartH;

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left - padding.left;
      const i = Math.round((x / chartW) * (candles.length - 1));
      if (i >= 0 && i < candles.length) onHover(i);
      else onHover(null);
    },
    [candles.length, chartW, onHover]
  );
  const handleMouseLeave = useCallback(() => onHover(null), [onHover]);

  const priceTicks = useMemo(() => {
    const step = (priceMax - priceMin) / 6;
    return [0, 1, 2, 3, 4, 5, 6].map((i) => priceMin + step * i);
  }, [priceMin, priceMax]);

  const dateTicks = useMemo(() => {
    const step = Math.max(1, Math.floor(candles.length / 6));
    return Array.from({ length: 7 }, (_, i) => Math.min(i * step, candles.length - 1));
  }, [candles.length]);

  const hoverCandle = hoverIndex != null ? candles[hoverIndex] : null;

  return (
    <svg width={width} height={height} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave} className="overflow-visible">
      {/* Grid */}
      {priceTicks.slice(1, -1).map((p, i) => (
        <line
          key={i}
          x1={padding.left}
          y1={yScalePrice(p)}
          x2={padding.left + chartW}
          y2={yScalePrice(p)}
          stroke="currentColor"
          strokeOpacity={0.08}
          strokeDasharray="4 4"
        />
      ))}
      {/* Y-axis labels (price) */}
      {priceTicks.map((p, i) => (
        <text
          key={i}
          x={padding.left - 6}
          y={yScalePrice(p)}
          textAnchor="end"
          dominantBaseline="middle"
          className="fill-muted-foreground text-[10px]"
        >
          {p >= 1000 ? `${(p / 1000).toFixed(1)}k` : p.toFixed(0)}
        </text>
      ))}
      {/* X-axis labels (dates) */}
      {dateTicks.map((i) => (
        <text
          key={i}
          x={padding.left + (i / Math.max(candles.length - 1, 1)) * chartW}
          y={height - 8}
          textAnchor="middle"
          className="fill-muted-foreground text-[10px]"
        >
          {candles[i]?.date?.slice(0, 7) ?? ""}
        </text>
      ))}
      {/* Candlesticks */}
      {candles.map((c, i) => {
        const x = padding.left + (i / Math.max(candles.length - 1, 1)) * chartW;
        const isUp = c.close >= c.open;
        const top = Math.min(c.open, c.close);
        const bottom = Math.max(c.open, c.close);
        const yHigh = yScalePrice(c.high);
        const yLow = yScalePrice(c.low);
        const yTop = yScalePrice(bottom);
        const yBottom = yScalePrice(top);
        const h = Math.max(1, yBottom - yTop);
        const w = candleWidth;
        const highlighted = hoverIndex === i;
        const fill = isUp ? "hsl(142, 76%, 36%)" : "hsl(0, 84%, 60%)";
        const stroke = isUp ? "hsl(142, 76%, 28%)" : "hsl(0, 84%, 50%)";
        return (
          <g key={i}>
            {/* Wick */}
            <line
              x1={x}
              y1={yHigh}
              x2={x}
              y2={yLow}
              stroke={stroke}
              strokeWidth={1}
              opacity={highlighted ? 1 : 0.9}
            />
            {/* Body */}
            <rect
              x={x - w / 2}
              y={yTop}
              width={w}
              height={h}
              fill={fill}
              stroke={stroke}
              strokeWidth={highlighted ? 1.5 : 0.5}
              opacity={highlighted ? 1 : 0.95}
            />
          </g>
        );
      })}
      {/* SMA 20 */}
      {candles.some((c) => c.sma20 != null) && (
        <polyline
          fill="none"
          stroke="hsl(217, 91%, 60%)"
          strokeWidth={1.5}
          points={candles
            .map((c, i) => {
              if (c.sma20 == null) return null;
              const x = padding.left + (i / Math.max(candles.length - 1, 1)) * chartW;
              const y = yScalePrice(c.sma20);
              return `${x},${y}`;
            })
            .filter(Boolean)
            .join(" ")}
        />
      )}
      {/* SMA 50 */}
      {candles.some((c) => c.sma50 != null) && (
        <polyline
          fill="none"
          stroke="hsl(280, 67%, 50%)"
          strokeWidth={1.5}
          points={candles
            .map((c, i) => {
              if (c.sma50 == null) return null;
              const x = padding.left + (i / Math.max(candles.length - 1, 1)) * chartW;
              const y = yScalePrice(c.sma50);
              return `${x},${y}`;
            })
            .filter(Boolean)
            .join(" ")}
        />
      )}
      {/* Volume bars */}
      {candles.map((c, i) => {
        const x = padding.left + (i / Math.max(candles.length - 1, 1)) * chartW;
        const volH = (c.volume / volMax) * volumeHeight;
        const y = height - padding.bottom - volH;
        const w = Math.max(1, candleWidth);
        return (
          <rect
            key={i}
            x={x - w / 2}
            y={y}
            width={w}
            height={volH}
            fill={c.close >= c.open ? "hsl(142, 76%, 36% / 0.4)" : "hsl(0, 84%, 60% / 0.4)"}
          />
        );
      })}
      {/* Tooltip (hover) - SVG rect + text */}
      {hoverCandle && (
        <g transform={`translate(${padding.left + (hoverIndex! / Math.max(candles.length - 1, 1)) * chartW},${padding.top})`}>
          <rect x={-70} y={-78} width={140} height={72} rx={6} fill="hsl(var(--background))" stroke="hsl(var(--border))" strokeWidth={1} />
          <text x={-62} y={-62} className="fill-muted-foreground" fontSize={10}>{hoverCandle.date}</text>
          <text x={-62} y={-50} fontSize={10}>O {formatINR(hoverCandle.open)}  H {formatINR(hoverCandle.high)}</text>
          <text x={-62} y={-38} fontSize={10}>L {formatINR(hoverCandle.low)}  C {formatINR(hoverCandle.close)}</text>
          {(hoverCandle.sma20 != null || hoverCandle.rsi != null) && (
            <text x={-62} y={-26} fontSize={10}>
              {hoverCandle.sma20 != null ? `SMA20 ${formatINR(hoverCandle.sma20)} ` : ""}
              {hoverCandle.rsi != null ? `RSI ${hoverCandle.rsi}` : ""}
            </text>
          )}
          <text x={-62} y={-14} className="fill-muted-foreground" fontSize={10}>Vol: {hoverCandle.volume.toLocaleString()}</text>
        </g>
      )}
    </svg>
  );
}

// —— Line chart (Recharts) ——
function LineChartView({ data, volMax }: { data: Candle[] & { isUp?: boolean }[]; volMax: number }) {
  return (
    <>
      <div className="h-[340px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 12, right: 12, left: 12, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickFormatter={(v) => v.slice(0, 7)}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="price"
              domain={["auto", "auto"]}
              tick={{ fontSize: 10 }}
              tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v))}
              width={52}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload;
                return (
                  <div className="rounded-lg border bg-background px-3 py-2 text-xs shadow-md">
                    <div className="font-medium text-muted-foreground">{p.date}</div>
                    <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
                      <span>O</span><span>{formatINR(p.open)}</span>
                      <span>H</span><span>{formatINR(p.high)}</span>
                      <span>L</span><span>{formatINR(p.low)}</span>
                      <span>C</span><span>{formatINR(p.close)}</span>
                      {p.sma20 != null && <><span>SMA20</span><span>{formatINR(p.sma20)}</span></>}
                      {p.rsi != null && <><span>RSI</span><span>{p.rsi}</span></>}
                    </div>
                    <div className="mt-1 text-muted-foreground">Vol: {p.volume.toLocaleString()}</div>
                  </div>
                );
              }}
            />
            <Area
              yAxisId="price"
              type="monotone"
              dataKey="close"
              fill="hsl(var(--primary) / 0.12)"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
            />
            {data.some((d) => d.sma20 != null) && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="sma20"
                stroke="hsl(217, 91%, 60%)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            )}
            {data.some((d) => d.sma50 != null) && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="sma50"
                stroke="hsl(280, 67%, 50%)"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="h-[72px] w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 4, right: 12, left: 12, bottom: 4 }}>
            <Bar dataKey="volume" fill="transparent" barSize={Math.max(2, 400 / data.length)} radius={0}>
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.isUp ? "hsl(142, 76%, 36% / 0.35)" : "hsl(0, 84%, 60% / 0.35)"} />
              ))}
            </Bar>
            <YAxis hide domain={[0, volMax * 1.1]} />
            <XAxis dataKey="date" hide />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}

export function MarketChart({ candles, ticker, view, className }: MarketChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const data = useMemo(() => {
    return candles.map((c) => ({
      ...c,
      bodyHigh: Math.max(c.open, c.close),
      bodyLow: Math.min(c.open, c.close),
      isUp: c.close >= c.open,
    }));
  }, [candles]);

  const volMax = useMemo(() => Math.max(...data.map((d) => d.volume), 1), [data]);

  if (data.length === 0) return null;

  function CandlestickWrapper({ width = 800, height = 420 }: { width?: number; height?: number }) {
    return (
      <CandlestickSVG
        candles={candles}
        width={width}
        height={height}
        onHover={setHoverIndex}
        hoverIndex={hoverIndex}
      />
    );
  }

  return (
    <div className={cn("w-full", className)}>
      {view === "candlestick" ? (
        <div className="h-[420px] w-full" style={{ minHeight: 420 }}>
          <ResponsiveContainer width="100%" height="100%">
            <CandlestickWrapper />
          </ResponsiveContainer>
        </div>
      ) : (
        <LineChartView data={data} volMax={volMax} />
      )}
    </div>
  );
}
