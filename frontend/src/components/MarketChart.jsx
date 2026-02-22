export default function MarketChart({ ticker, price, priceChange }) {
  return (
    <div className="bg-surface-dark border border-border-dark rounded-lg flex-1 flex flex-col overflow-hidden min-h-[380px]">
      {/* Chart Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-dark bg-[#0B0E11]/50">
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold text-slate-300">Market Data</span>
          <div className="flex items-center gap-1">
            {["1D", "1W", "1M", "3M", "1Y"].map((tf, i) => (
              <span
                key={tf}
                className={`px-2 py-0.5 rounded text-xs font-mono cursor-pointer transition-all ${
                  i === 0
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                }`}
              >
                {tf}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          {[
            { color: "bg-yellow-500", label: "SMA 20" },
            { color: "bg-blue-500", label: "SMA 50" },
            { color: "bg-purple-500", label: "SMA 200" },
          ].map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className={`size-2 rounded-full ${color}`} />
              <span className="text-slate-400">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Chart Body */}
      <div className="flex-1 relative bg-[#0B0E11] p-4">
        {/* Price Overlay */}
        <div className="absolute top-4 left-4 z-10 flex flex-col">
          <span className="text-3xl font-mono font-bold text-white">
            {price ? `₹${Number(price).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
          </span>
          {priceChange !== undefined && (
            <span className={`text-sm font-mono flex items-center gap-1 ${priceChange >= 0 ? "text-success" : "text-danger"}`}>
              {priceChange >= 0 ? "+" : ""}{priceChange}%
              <span className="material-symbols-outlined text-[14px]">
                {priceChange >= 0 ? "arrow_upward" : "arrow_downward"}
              </span>
            </span>
          )}
        </div>

        {/* SVG Chart (placeholder candles) */}
        <svg className="w-full h-full" viewBox="0 0 800 400" preserveAspectRatio="none">
          {/* Grid */}
          {[100, 200, 300].map((y) => (
            <line key={y} x1="0" y1={y} x2="800" y2={y} stroke="#1f2937" strokeDasharray="4 4" strokeWidth="1" />
          ))}

          {/* SMA Lines */}
          <path d="M0 250 Q 200 240, 400 280 T 800 260" fill="none" stroke="#eab308" strokeWidth="2" opacity="0.8" />
          <path d="M0 220 Q 200 210, 400 250 T 800 240" fill="none" stroke="#3b82f6" strokeWidth="2" opacity="0.6" />
          <path d="M0 200 Q 200 195, 400 210 T 800 220" fill="none" stroke="#a855f7" strokeWidth="1.5" opacity="0.4" />

          {/* Candles */}
          {[
            { x: 50, o: 240, c: 270, h: 220, l: 280, bull: true },
            { x: 100, o: 260, c: 240, h: 230, l: 290, bull: false },
            { x: 150, o: 220, c: 280, h: 200, l: 290, bull: true },
            { x: 250, o: 235, c: 270, h: 235, l: 280, bull: false },
            { x: 300, o: 270, c: 300, h: 270, l: 310, bull: false },
            { x: 350, o: 300, c: 285, h: 280, l: 320, bull: true },
            { x: 400, o: 260, c: 280, h: 250, l: 280, bull: true },
            { x: 450, o: 260, c: 290, h: 260, l: 300, bull: false },
            { x: 500, o: 300, c: 325, h: 300, l: 330, bull: false },
            { x: 550, o: 320, c: 310, h: 310, l: 330, bull: true },
            { x: 600, o: 300, c: 290, h: 290, l: 310, bull: true },
            { x: 650, o: 260, c: 300, h: 250, l: 300, bull: true },
            { x: 700, o: 240, c: 250, h: 240, l: 250, bull: true },
            { x: 750, o: 240, c: 255, h: 240, l: 260, bull: false },
          ].map(({ x, o, c, h, l, bull }, i) => {
            const color = bull ? "#22c55e" : "#ef4444";
            const top = Math.min(o, c);
            const height = Math.abs(c - o) || 2;
            return (
              <g key={i}>
                <line x1={x} y1={h} x2={x} y2={l} stroke={color} strokeWidth="1" />
                <rect x={x - 5} y={top} width="10" height={height} fill={color} />
              </g>
            );
          })}

          {/* Volume */}
          <g opacity="0.2">
            {[50, 100, 150, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750].map((x, i) => (
              <rect key={i} x={x - 5} y={370 - (20 + Math.random() * 40)} width="10" height={20 + Math.random() * 40} fill="#3b82f6" />
            ))}
          </g>
        </svg>

        {/* Ticker label */}
        <div className="absolute bottom-3 right-4 text-xs font-mono text-slate-600">
          {ticker || "—"} · Daily
        </div>
      </div>
    </div>
  );
}
