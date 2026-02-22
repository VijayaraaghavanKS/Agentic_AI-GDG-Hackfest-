import { useState } from "react";

export default function Header({ ticker, setTicker, onRun, loading, regime, syncAgo }) {
  const [input, setInput] = useState(ticker || "");

  const handleRun = () => {
    const t = input.trim().toUpperCase();
    if (!t) return;
    setTicker(t);
    onRun(t);
  };

  return (
    <header className="h-16 border-b border-border-dark bg-surface-dark px-6 flex items-center justify-between shrink-0 z-20">
      {/* Left */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="size-8 bg-primary/20 rounded flex items-center justify-center text-primary">
            <span className="material-symbols-outlined text-xl">candlestick_chart</span>
          </div>
          <h1 className="text-white text-lg font-bold tracking-tight">Regime-Aware Command Center</h1>
        </div>

        <div className="h-6 w-px bg-border-dark mx-2" />

        {/* Ticker Search */}
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 group-focus-within:text-primary transition-colors">
            <span className="material-symbols-outlined text-[20px]">search</span>
          </div>
          <input
            className="bg-[#0B0E11] border border-border-dark text-white text-sm rounded-md w-64 pl-10 p-2 focus:ring-1 focus:ring-primary focus:border-primary placeholder-slate-600 font-mono transition-all outline-none"
            placeholder="Search Ticker (e.g. RELIANCE)"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
          />
        </div>
      </div>

      {/* Right */}
      <div className="flex items-center gap-4">
        {/* Regime Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0B0E11] rounded border border-border-dark">
          <span className="material-symbols-outlined text-slate-400 text-[18px]">show_chart</span>
          <span className="text-xs text-slate-400 font-medium">REGIME:</span>
          <span className="text-xs text-slate-200 font-bold tracking-wide">{regime || "—"}</span>
        </div>

        {/* Sync */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0B0E11] rounded border border-border-dark">
          <span className="material-symbols-outlined text-slate-400 text-[18px]">sync</span>
          <span className="text-xs text-slate-400 font-medium">SYNC:</span>
          <span className="text-xs text-success font-mono">{syncAgo || "—"}</span>
        </div>

        {/* Run Button */}
        <button
          onClick={handleRun}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded shadow-[0_0_15px_rgba(19,91,236,0.5)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          <span className="material-symbols-outlined text-[20px]">
            {loading ? "hourglass_top" : "play_arrow"}
          </span>
          {loading ? "Running…" : "Run Analysis"}
        </button>
      </div>
    </header>
  );
}
