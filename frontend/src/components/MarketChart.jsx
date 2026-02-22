import { useMemo, useRef, useState } from "react";

const VIEW_W = 800;
const VIEW_H = 360;
const VOL_H = 48;
const CHART_H = VIEW_H - VOL_H - 10;

function computeSMA(values, period) {
  if (!Array.isArray(values) || values.length < period) return [];
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function buildLinePath(pts, toX, toY) {
  let d = "";
  for (let i = 0; i < pts.length; i++) {
    const v = pts[i];
    if (!Number.isFinite(v)) continue;
    const x = toX(i).toFixed(2);
    const y = toY(v).toFixed(2);
    d += d ? ` L ${x} ${y}` : `M ${x} ${y}`;
  }
  return d;
}

function generatePlaceholder(ticker = "DEMO", count = 80) {
  let seed = ticker.split("").reduce((s, c) => s + c.charCodeAt(0), 42);
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  };
  const candles = [];
  let close = 1400 + rand() * 800;
  for (let i = 0; i < count; i++) {
    const chg = (rand() - 0.49) * 0.03;
    const open = close;
    close = Math.max(50, open * (1 + chg));
    const hi = Math.max(open, close) * (1 + rand() * 0.007);
    const lo = Math.min(open, close) * (1 - rand() * 0.007);
    candles.push({
      t: new Date(Date.now() - (count - i) * 86400000).toISOString(),
      o: open, h: hi, l: lo, c: close,
      v: 2e6 + rand() * 8e6,
      _ph: true,
    });
  }
  return candles;
}

export default function MarketChart({
  ticker,
  price,
  priceChange,
  timeframe = "1M",
  onTimeframeChange,
  candles: rawCandles,
  indicators,
  chartLoading = false,
  chartError = null,
  onRetry,
}) {
  const svgRef = useRef(null);
  const [hoverIdx, setHoverIdx] = useState(null);
  const [hoverPos, setHoverPos] = useState(null);

  const isPlaceholder = !Array.isArray(rawCandles) || rawCandles.length < 10;
  const candles = useMemo(
    () => (isPlaceholder ? generatePlaceholder(ticker || "DEMO", 80) : rawCandles),
    [isPlaceholder, rawCandles, ticker]
  );

  const yDomain = useMemo(() => {
    let lo = Infinity, hi = -Infinity;
    for (const c of candles) {
      if (Number.isFinite(c.l)) lo = Math.min(lo, c.l);
      if (Number.isFinite(c.h)) hi = Math.max(hi, c.h);
    }
    if (!Number.isFinite(lo) || lo === hi) return null;
    const pad = (hi - lo) * 0.07;
    return { lo: lo - pad, hi: hi + pad };
  }, [candles]);

  const maxVol = useMemo(() => Math.max(...candles.map((c) => c.v || 0), 1), [candles]);

  const sma = useMemo(() => {
    const cls = candles.map((c) => c.c);
    return {
      s20: computeSMA(cls, 20),
      s50: computeSMA(cls, 50),
      s200: computeSMA(cls, 200),
    };
  }, [candles]);

  const n = candles.length;
  const step = n > 1 ? VIEW_W / n : VIEW_W;
  const bw = Math.max(1.5, step * 0.55);

  const toX = (i) => i * step + step / 2;
  const toY = (p) => {
    if (!yDomain) return CHART_H / 2;
    return ((yDomain.hi - p) / (yDomain.hi - yDomain.lo)) * CHART_H;
  };

  const onMouseMove = (e) => {
    const el = svgRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const relX = e.clientX - r.left;
    const idx = Math.min(Math.max(0, Math.floor((relX / r.width) * n)), n - 1);
    setHoverIdx(idx);
    setHoverPos({ x: relX, y: e.clientY - r.top, w: r.width, h: r.height });
  };
  const onMouseLeave = () => { setHoverIdx(null); setHoverPos(null); };

  const priceY = price && yDomain ? toY(Number(price)) : null;

  return (
    <div
      className="bg-surface-dark border border-border-dark rounded-lg flex-1 flex flex-col"
      style={{ minHeight: 340, overflow: "hidden" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-dark bg-[#0B0E11]/60 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-slate-300">
            {ticker || "—"} Chart
          </span>
          {isPlaceholder && !chartLoading && !chartError && (
            <span className="text-[10px] font-mono text-slate-600 border border-slate-700 rounded px-1.5 py-0.5">
              PREVIEW
            </span>
          )}
          <div className="flex items-center gap-0.5">
            {["1D", "1W", "1M", "3M", "1Y"].map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => typeof onTimeframeChange === "function" && onTimeframeChange(tf)}
                className={`px-2 py-0.5 rounded text-xs font-mono transition-all ${
                  tf === timeframe
                    ? "bg-primary/15 text-primary border border-primary/25"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/60"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          {[
            { stroke: "#eab308", label: "SMA 20", desc: "20-day avg", dash: false },
            { stroke: "#3b82f6", label: "SMA 50", desc: "50-day avg", dash: false },
            { stroke: "#a855f7", label: "SMA 200", desc: "200-day avg", dash: false },
            { stroke: "#135bec", label: "Price", desc: "Current", dash: true },
          ].map(({ stroke, label, desc, dash }) => (
            <div key={label} className="flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-slate-800/40" title={`${label}: ${desc}`}>
              <svg width="18" height="4">
                <line x1="0" y1="2" x2="18" y2="2" stroke={stroke} strokeWidth="2" strokeDasharray={dash ? "4 3" : "none"} />
              </svg>
              <span style={{ color: stroke }} className="font-semibold">{label}</span>
              <span className="text-slate-600 text-[10px] hidden sm:inline">{desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG area */}
      <div className="flex-1 relative bg-[#0B0E11]" style={{ minHeight: 240 }}>
        {/* Loading overlay */}
        {chartLoading && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[#0B0E11]/80 backdrop-blur-[2px]">
            <div className="flex flex-col items-center gap-3">
              <span className="material-symbols-outlined text-primary text-4xl animate-spin" style={{ animationDuration: "1.2s" }}>refresh</span>
              <p className="text-sm text-slate-400 font-mono">
                Fetching <span className="text-white font-semibold">{ticker}</span> market data…
              </p>
            </div>
          </div>
        )}

        {/* Error overlay (only when no real candles available) */}
        {chartError && isPlaceholder && !chartLoading && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[#0B0E11]/90 backdrop-blur-[2px]">
            <div className="flex flex-col items-center gap-3 max-w-xs text-center px-4">
              <span className="material-symbols-outlined text-danger text-4xl">wifi_off</span>
              <p className="text-sm text-slate-300 font-semibold">Chart data unavailable</p>
              <p className="text-xs text-slate-500 font-mono break-words">{chartError}</p>
              {typeof onRetry === "function" && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="mt-1 px-4 py-1.5 rounded border border-primary/40 bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-colors"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        )}

        {/* Price badge */}
        <div className="absolute top-3 left-4 z-10 pointer-events-none flex items-baseline gap-2">
          <span className="text-2xl font-mono font-bold text-white">
            {price
              ? `${Number(price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : candles.length
              ? candles[candles.length - 1].c.toFixed(2)
              : "—"}
          </span>
          {priceChange != null && (
            <span
              className={`text-xs font-mono font-semibold flex items-center gap-0.5 ${
                priceChange >= 0 ? "text-success" : "text-danger"
              }`}
            >
              {priceChange >= 0 ? "+" : ""}
              {priceChange}%
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>
                {priceChange >= 0 ? "arrow_upward" : "arrow_downward"}
              </span>
            </span>
          )}
        </div>

        <svg
          ref={svgRef}
          style={{ display: "block", width: "100%", height: "100%" }}
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="none"
          onMouseMove={onMouseMove}
          onMouseLeave={onMouseLeave}
        >
          {/* Grid */}
          {[0.2, 0.4, 0.6, 0.8].map((f) => (
            <line
              key={f}
              x1="0" y1={f * CHART_H}
              x2={VIEW_W} y2={f * CHART_H}
              stroke="#1e293b" strokeWidth="1"
            />
          ))}

          {/* Volume bars */}
          {candles.map((c, i) => {
            const bull = c.c >= c.o;
            const barH = Math.max(2, (c.v / maxVol) * VOL_H);
            return (
              <rect
                key={`v${i}`}
                x={toX(i) - bw / 2}
                y={VIEW_H - 4 - barH}
                width={bw}
                height={barH}
                fill={bull ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}
              />
            );
          })}

          {/* SMA lines */}
          {sma.s20.some(Boolean) && (
            <path
              d={buildLinePath(sma.s20, toX, toY)}
              fill="none" stroke="#eab308" strokeWidth="1.5" opacity="0.85"
            />
          )}
          {sma.s50.some(Boolean) && (
            <path
              d={buildLinePath(sma.s50, toX, toY)}
              fill="none" stroke="#3b82f6" strokeWidth="1.5" opacity="0.7"
            />
          )}
          {sma.s200.some(Boolean) && (
            <path
              d={buildLinePath(sma.s200, toX, toY)}
              fill="none" stroke="#a855f7" strokeWidth="1.2" opacity="0.5"
            />
          )}

          {/* Candles */}
          {candles.map((c, i) => {
            const bull = c.c >= c.o;
            const col = bull ? "#22c55e" : "#ef4444";
            const cx = toX(i);
            const yH = toY(c.h);
            const yL = toY(c.l);
            const yO = toY(c.o);
            const yC = toY(c.c);
            const bodyTop = Math.min(yO, yC);
            const bodyH = Math.max(1.5, Math.abs(yC - yO));
            const dimmed = hoverIdx !== null && hoverIdx !== i;

            return (
              <g key={i} opacity={dimmed ? 0.35 : 1}>
                <line x1={cx} y1={yH} x2={cx} y2={yL} stroke={col} strokeWidth={hoverIdx === i ? 1.5 : 0.8} />
                <rect
                  x={cx - bw / 2} y={bodyTop}
                  width={bw} height={bodyH}
                  fill={col} rx="0.3"
                />
              </g>
            );
          })}

          {/* Current price dashed line */}
          {priceY !== null && (
            <g>
              <line
                x1="0" y1={priceY} x2={VIEW_W} y2={priceY}
                stroke="#135bec" strokeWidth="1" strokeDasharray="6 4" opacity="0.7"
              />
              <rect x={VIEW_W - 58} y={priceY - 10} width="58" height="20" fill="#135bec" rx="3" />
              <text
                x={VIEW_W - 29} y={priceY + 5}
                fill="white" fontSize="13" textAnchor="middle"
                fontFamily="monospace"
              >
                {Number(price).toFixed(0)}
              </text>
            </g>
          )}

          {/* Hover crosshair */}
          {hoverIdx !== null && candles[hoverIdx] && (
            <g>
              <line
                x1={toX(hoverIdx)} y1="0" x2={toX(hoverIdx)} y2={VIEW_H}
                stroke="#475569" strokeDasharray="3 3" strokeWidth="1"
              />
              <line
                x1="0" y1={toY(candles[hoverIdx].c)} x2={VIEW_W} y2={toY(candles[hoverIdx].c)}
                stroke="#475569" strokeDasharray="3 3" strokeWidth="1"
              />
            </g>
          )}
        </svg>

        {/* Hover tooltip */}
        {hoverIdx !== null && hoverPos && candles[hoverIdx] && (
          <div
            className="absolute z-20 pointer-events-none"
            style={{
              left: Math.min(hoverPos.x + 14, hoverPos.w - 196),
              top: Math.max(6, hoverPos.y - 68),
            }}
          >
            <div className="bg-[#15191E]/96 border border-border-dark rounded-lg px-3 py-2.5 text-xs font-mono shadow-2xl backdrop-blur-sm w-[188px]">
              <p className="text-slate-400 mb-1.5 text-[11px] truncate">
                {new Date(candles[hoverIdx].t).toLocaleString(undefined, {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: candles[hoverIdx]._ph ? undefined : "2-digit",
                  minute: candles[hoverIdx]._ph ? undefined : "2-digit",
                })}
              </p>
              <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 items-center">
                <span className="text-slate-500">O</span>
                <span className="text-right text-slate-300">{candles[hoverIdx].o.toFixed(2)}</span>
                <span className="text-slate-500">H</span>
                <span className="text-right text-success">{candles[hoverIdx].h.toFixed(2)}</span>
                <span className="text-slate-500">L</span>
                <span className="text-right text-danger">{candles[hoverIdx].l.toFixed(2)}</span>
                <span className="text-slate-500">C</span>
                <span className={`text-right font-bold ${candles[hoverIdx].c >= candles[hoverIdx].o ? "text-success" : "text-danger"}`}>
                  {candles[hoverIdx].c.toFixed(2)}
                </span>
                <span className="text-slate-500">Vol</span>
                <span className="text-right text-slate-400">
                  {((candles[hoverIdx].v || 0) / 1e6).toFixed(2)}M
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Bottom info bar */}
        <div className="absolute bottom-2 left-3 right-3 flex justify-between items-end pointer-events-none z-10">
          <div className="text-[11px] font-mono text-slate-600 flex gap-3">
            {indicators && (
              <>
                <span>
                  RSI{" "}
                  <span
                    className={
                      Number(indicators.rsi) > 70
                        ? "text-danger"
                        : Number(indicators.rsi) < 30
                        ? "text-success"
                        : "text-slate-400"
                    }
                  >
                    {Number(indicators.rsi).toFixed(1)}
                  </span>
                </span>
                <span>
                  ATR <span className="text-slate-400">{Number(indicators.atr).toFixed(2)}</span>
                </span>
                <span>
                  Vol% <span className="text-slate-400">{(Number(indicators.volatility) * 100).toFixed(1)}</span>
                </span>
              </>
            )}
          </div>
          <span className="text-[11px] font-mono text-slate-600">
            {ticker || "—"} · {timeframe}
          </span>
        </div>
      </div>
    </div>
  );
}
