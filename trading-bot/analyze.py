"""Diagnose where the strategy loses on real MEXC data (cached CSVs)."""
import re
from pathlib import Path

import pandas as pd

from bot.backtest import run_backtest
from bot.config import load_config
from bot.data import load_csv

pd.set_option("display.width", 140)

cfg = load_config("config.mexc-paper.yaml")
data = {
    sym: load_csv(Path("data_cache") / (sym.replace("/", "_") + ".csv"))
    for sym in cfg.exchange.symbol_list
}

res = run_backtest(data, cfg)
t = pd.DataFrame([vars(x) for x in res.trades])
t["entry_time"] = pd.to_datetime(t["entry_time"])
t["exit_time"] = pd.to_datetime(t["exit_time"])
t["month"] = t["exit_time"].dt.to_period("M")
t["pattern"] = t["reason"].str.extract(r"\+ (\w+)")
t["location"] = t["reason"].str.extract(r"pullback to ([\w ]+) \+")
t["hold_bars"] = (t["exit_time"] - t["entry_time"]).dt.total_seconds() / 14400
t["won"] = t["pnl"] > 0

print(f"== BASELINE: {len(t)} trades, pnl {t.pnl.sum():+.2f}, fees {t.fees.sum():.2f} ==\n")

def slice_by(col):
    g = t.groupby(col).agg(
        n=("pnl", "size"), pnl=("pnl", "sum"), avg_r=("r_multiple", "mean"),
        win=("won", "mean"), med_hold=("hold_bars", "median"),
    )
    g["win"] = (g["win"] * 100).round(0)
    return g.sort_values("pnl")

for col in ["symbol", "exit_reason", "pattern", "location", "month"]:
    print(f"-- by {col} --")
    print(slice_by(col).round(2), "\n")

# R-multiple distribution
print("-- R distribution --")
print(t.r_multiple.describe().round(2))
print("\ntop 5 winners / losers (R):", sorted(t.r_multiple, reverse=True)[:5],
      "/", sorted(t.r_multiple)[:5])

# how much the partial-take contributed: trades stopped at breakeven-ish
be = t[(t.exit_reason == "stop") & (t.r_multiple > -0.3) & (t.r_multiple < 0.6)]
print(f"\nbreakeven-zone stops (-0.3R..0.6R): {len(be)} trades, pnl {be.pnl.sum():+.2f}")
full_loss = t[t.r_multiple <= -0.8]
print(f"full -1R losses: {len(full_loss)} trades, pnl {full_loss.pnl.sum():+.2f}")
runners = t[t.r_multiple >= 1.5]
print(f"runners >= 1.5R: {len(runners)} trades, pnl {runners.pnl.sum():+.2f}")

# market regime context: per-pair buy&hold over the window + trend share
print("\n-- market context (window return per pair, % of bars in EMA uptrend) --")
from bot.indicators import add_indicators
rows = []
for sym, df in data.items():
    di = add_indicators(df, cfg.strategy)
    up = (di["ema_fast"] > di["ema_slow"]) & (di["close"] > di["ema_slow"])
    rows.append({
        "symbol": sym,
        "bh_ret_pct": (df.close.iloc[-1] / df.close.iloc[0] - 1) * 100,
        "uptrend_bars_pct": up.mean() * 100,
    })
print(pd.DataFrame(rows).set_index("symbol").round(1).sort_values("bh_ret_pct"))
