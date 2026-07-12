"""Config-variant experiments on the same cached MEXC data."""
import copy
from pathlib import Path

import pandas as pd

from bot.backtest import run_backtest
from bot.config import load_config
from bot.data import load_csv

base = load_config("config.mexc-paper.yaml")
data = {
    sym: load_csv(Path("data_cache") / (sym.replace("/", "_") + ".csv"))
    for sym in base.exchange.symbol_list
}

def run(name, **mods):
    cfg = copy.deepcopy(base)
    for k, v in mods.items():
        obj, attr = (cfg.strategy, k) if hasattr(cfg.strategy, k) else (cfg.risk, k)
        setattr(obj, attr, v)
    r = run_backtest(data, cfg).metrics
    return {
        "variant": name, "ret%": r["total_return_pct"], "trades": r["n_trades"],
        "win%": r["win_rate_pct"], "pf": r["profit_factor"],
        "avg_r": r["avg_r"], "maxdd%": r["max_drawdown_pct"],
    }

rows = [run("baseline")]

# --- entry filter strictness ---
for s in (0.50, 0.65, 0.70, 0.75):
    rows.append(run(f"pattern_score>={s}", min_pattern_score=s))
rows.append(run("rsi_long_max=60", rsi_long_max=60))
rows.append(run("rsi_long_max=55", rsi_long_max=55))
rows.append(run("cooldown=6", cooldown_bars=6))

# --- exit profile ---
for m in (2.0, 2.5, 3.0):
    rows.append(run(f"trail={m}atr", trail_atr_mult=m))
for tr in (1.5, 2.0, 3.0):
    rows.append(run(f"target_r={tr} (no trail)", target_r=tr))
rows.append(run("two-stage trail 2R->2atr", trail_tighten_after_r=2.0, trail_atr_mult_tight=2.0))
rows.append(run("no partial bank", partial_take_r=None))
rows.append(run("bank 50% at 1R", partial_take_fraction=0.5))
rows.append(run("breakeven at 0.7R", breakeven_at_r=0.7))

df = pd.DataFrame(rows).set_index("variant").round(2)
print(df.to_string())
