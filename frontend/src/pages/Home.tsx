import { Chat } from "@/components/Chat";
import { MarketRegime } from "@/components/MarketRegime";
import { Portfolio } from "@/components/Portfolio";
import { SignalBoard } from "@/components/SignalBoard";
import { BacktestSummary } from "@/components/BacktestSummary";
import { DividendTop } from "@/components/DividendTop";

export function Home() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1 h-[calc(100vh-7.5rem)]">
        <Chat />
      </div>
      <div className="lg:col-span-2 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <MarketRegime />
          <Portfolio />
          <BacktestSummary />
          <DividendTop />
        </div>
        <SignalBoard />
      </div>
    </div>
  );
}
