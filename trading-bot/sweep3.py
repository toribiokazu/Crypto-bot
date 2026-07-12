"""Futures exploration: long+short on MEXC perpetual data.

MEXC futures taker fee is 0.02% (vs 0.05% spot); funding is NOT modeled.
Direction/regime gating is done by wrapping the strategy so bot code stays
untouched.
"""
import copy
from pathlib import Path

import pandas as pd

import bot.backtest as bt
from bot.config import load_config
from bot.data import load_csv
from bot.indicators import add_indicators
from bot.strategy import PriceActionStrategy

base = load_config("config.mexc-paper.yaml")
base.risk.fee_pct = 0.02
data = {}
for sym in base.exchange.symbol_list:
    p = Path("data_cache_swap") / (sym.replace("/", "_") + ".csv")
    if p.exists():
        data[sym] = load_csv(p)
base.exchange.symbols = list(data)
print(f"{len(data)} perpetual pairs loaded\n")

btc = add_indicators(data["BTC/USDT"], base.strategy)
btc_up = (btc["ema_fast"] > btc["ema_slow"]) & (btc["close"] > btc["ema_slow"])
btc_down = (btc["ema_fast"] < btc["ema_slow"]) & (btc["close"] < btc["ema_slow"])
print(f"BTC bars up-trend {btc_up.mean()*100:.0f}%, down-trend {btc_down.mean()*100:.0f}%\n")


def make_strategy(longs=True, shorts=True, regime=False):
    class Wrapped(PriceActionStrategy):
        def evaluate(self, df, i):
            sig = super().evaluate(df, i)
            if sig is None:
                return None
            if sig.direction > 0 and not longs:
                return None
            if sig.direction < 0 and not shorts:
                return None
            if regime:
                ts = df.index[i]
                if sig.direction > 0 and not bool(btc_up.get(ts, False)):
                    return None
                if sig.direction < 0 and not bool(btc_down.get(ts, False)):
                    return None
            return sig
    return Wrapped


def run(name, longs=True, shorts=True, regime=False, keep=False, **mods):
    cfg = copy.deepcopy(base)
    cfg.strategy.allow_shorts = shorts
    for k, v in mods.items():
        obj = cfg.strategy if hasattr(cfg.strategy, k) else cfg.risk
        setattr(obj, k, v)
    orig = bt.PriceActionStrategy
    bt.PriceActionStrategy = make_strategy(longs, shorts, regime)
    try:
        res = bt.run_backtest(data, cfg)
    finally:
        bt.PriceActionStrategy = orig
    r = res.metrics
    row = {
        "variant": name, "ret%": r["total_return_pct"], "trades": r["n_trades"],
        "win%": r["win_rate_pct"], "pf": r["profit_factor"],
        "avg_r": r["avg_r"], "maxdd%": r["max_drawdown_pct"],
    }
    return (row, res) if keep else row


rows = [
    run("long-only (spot behaviour)", shorts=False),
    run("long-only + BTC regime", shorts=False, regime=True),
    run("long+short"),
    run("short-only"),
    run("long+short + BTC regime", regime=True),
]
row, best = run("short-only + BTC regime", longs=False, regime=True, keep=True)
rows.append(row)
print(pd.DataFrame(rows).set_index("variant").round(2).to_string())

# breakdown of the short side in the combined regime run
_, combo = run("combo detail", regime=True, keep=True)
t = pd.DataFrame([vars(x) for x in combo.trades])
t["pattern"] = t["reason"].str.extract(r"\+ (\w+)")
t["won"] = t.pnl > 0
t["side"] = t.direction.map({1: "long", -1: "short"})
print("\n-- long+short+regime: by side --")
print(t.groupby("side").agg(n=("pnl", "size"), pnl=("pnl", "sum"),
                            win=("won", "mean"), avg_r=("r_multiple", "mean")).round(2))
print("\n-- short trades by pattern --")
s = t[t.direction < 0]
print(s.groupby("pattern").agg(n=("pnl", "size"), pnl=("pnl", "sum"),
                               win=("won", "mean"), avg_r=("r_multiple", "mean")).round(2))
print("\n-- short trades by month --")
s2 = s.copy()
s2["month"] = pd.to_datetime(s2["exit_time"]).dt.tz_localize(None).dt.to_period("M")
print(s2.groupby("month").agg(n=("pnl", "size"), pnl=("pnl", "sum"),
                              win=("won", "mean")).round(2))
