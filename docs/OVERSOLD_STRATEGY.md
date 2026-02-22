# Oversold Bounce Strategy — Explanation & Stop-Loss

## What the strategy does

**Oversold bounce** is a **mean-reversion** strategy used in **sideways or bear** markets (when the market is not in a clear uptrend). The idea: when a stock gets oversold, it often bounces back in the short term.

### Rules (backtest)

1. **Entry**
   - RSI ≤ 35 (oversold).
   - Price **below 50-day moving average** (dip in a weak trend).
   - Buy at the **close** of that day.

2. **Stop loss**
   - **Stop = Entry − (0.6 × ATR)**.
   - ATR = Average True Range (14-day), so the stop is **0.6× recent volatility** below entry.
   - If price hits this level on any later day, we exit at the stop (loss).

3. **Exit (take profit / time limit)**
   - **RSI exit:** if RSI reaches ≥ 45 on a later day, we exit at that day’s close (target “bounce done”).
   - **Max hold:** if neither stop nor RSI exit happens, we exit at the close of **day 10** (no bag-holding).

4. **Position sizing (when enabled)**
   - Risk per trade = 1% of current capital.
   - Quantity = (1% of capital) ÷ (entry − stop), so **one full stop = 1% loss** on the trade.

So the strategy is: **small, quick bounces** with a **tight, volatility-based stop** and a **short max hold**.

---

## Should you increase the stop loss?

**Increasing stop loss** = placing the stop **further below entry** (e.g. 1.2× ATR instead of 0.8× ATR).

### If you **widen** the stop (e.g. 1.0 or 1.2× ATR)

| Effect | What happens |
|--------|----------------|
| **Fewer stop-outs** | Price has more room to dip and then bounce. Some trades that would have exited at “stop_hit” may instead exit at “rsi_exit” or “max_days” and sometimes turn into winners. |
| **Win rate** | Can go **up** (fewer small losses from quick whipsaws). |
| **Loss size when wrong** | Each **losing** trade loses **more** (you exit further below entry). |
| **Risk per trade** | With 1% risk sizing, **risk per share** = entry − stop. Wider stop ⇒ smaller position size for the same 1% risk, so **same risk per trade** but **fewer shares**. |
| **Drawdown** | If many of the “saved” trades still end up losing (but later), drawdown can get **worse**. If they turn into winners, it can get better. |

So: **win rate can improve, but loss size and behaviour of losers matter a lot.**

### If you **keep or tighten** the stop (e.g. stay at 0.8 or try 0.6× ATR)

| Effect | What happens |
|--------|----------------|
| **More stop-outs** | Normal volatility can trigger the stop before the bounce; you get more small, quick losses. |
| **Win rate** | Can go **down** (more “stop_hit” exits). |
| **Loss size when wrong** | Each loss is **smaller** (stop closer to entry). |
| **Discipline** | Fits the idea of “quick bounce or get out”; avoids giving bad trades too much room. |

So: **fewer shares per trade** (tighter risk), **smaller losses per loser**, but **more losers** if the market chops.

---

## Is it “better” to increase stop loss or not?

- **It’s not automatically better to increase it.** It depends on the data and the market:
  - If many losses in the backtest are **stop_hit** and price often **bounces after** your stop, then **slightly** wider stop (e.g. 1.0× ATR) might improve results.
  - If widening the stop just **lets losers run** and you still exit at stop or max_days with a **bigger** loss, then **keeping (or tightening) the stop is better**.

So:

- **Current default 0.6× ATR** is a **very tight** stop so that:
  - One full stop ≈ **1% of capital** (with current sizing).
  - The strategy stays “short-term mean reversion”, not “hope it comes back”.
- **Increasing stop loss** (e.g. 0.8, 1.0, 1.2× ATR) can be **better** only if your backtest (or live data) shows that:
  - Win rate and/or average trade improve enough, and  
  - Average loss and drawdown don’t get too much worse.

**Practical suggestion:** run the backtest with **0.6**, **0.8**, **1.0**, and **1.2× ATR** and compare **win rate**, **avg return per trade**, and **total P&L / drawdown**. Use that to decide; don’t assume “wider = better”.

---

## Summary

- **Strategy:** Oversold bounce = buy when RSI ≤ 35 and below 50-DMA; exit at stop (0.8× ATR), RSI ≥ 45, or 10 days.
- **Stop loss:** Currently **0.6× ATR** below entry (tight).
- **Increasing stop loss** can improve win rate by avoiding some whipsaws but increases loss size when wrong; it is **not always better**. Prefer **backtesting a few stop multiples** (e.g. 0.8, 1.0, 1.2) and choosing based on risk-adjusted results.
