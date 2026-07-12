"""Structural experiments: BTC regime filter and per-pattern entry subsets.
Implemented by wrapping the strategy, so bot code stays untouched."""
import copy
from pathlib import Path

import pandas as pd

import bot.backtest as bt
from bot.config import load_config
from bot.data import load_csv
from bot.indicators import add_indicators
from bot.strategy import PriceActionStrategy

base = load_config("config.mexc-paper.yaml")
data = {
    sym: load_csv(Path("data_cache") / (sym.replace("/", "_") + ".csv"))
    for sym in base.exchange.symbol_list
}

# BTC regime: EMA(21) > EMA(55) and close above EMA(55), per closed 4h bar
btc = add_indicators(data["BTC/USDT"], base.strategy)
btc_up = ((btc["ema_fast"] > btc["ema_slow"]) & (btc["close"] > btc["ema_slow"]))
print(f"BTC uptrend share of bars: {btc_up.mean()*100:.1f}%")


def make_strategy(regime=False, patterns_allowed=None):
    class Wrapped(PriceActionStrategy):
        def evaluate(self, df, i):
            if regime and not bool(btc_up.get(df.index[i], False)):
                return None
            sig = super().evaluate(df, i)
            if sig and patterns_allowed and not any(p in sig.reason for p in patterns_allowed):
                return None
            return sig
    return Wrapped


def run(name, regime=False, patterns_allowed=None, **mods):
    cfg = copy.deepcopy(base)
    for k, v in mods.items():
        obj = cfg.strategy if hasattr(cfg.strategy, k) else cfg.risk
        setattr(obj, k, v)
    orig = bt.PriceActionStrategy
    bt.PriceActionStrategy = make_strategy(regime, patterns_allowed)
    try:
        r = bt.run_backtest(data, cfg).metrics
    finally:
        bt.PriceActionStrategy = orig
    return {
        "variant": name, "ret%": r["total_return_pct"], "trades": r["n_trades"],
        "win%": r["win_rate_pct"], "pf": r["profit_factor"],
        "avg_r": r["avg_r"], "maxdd%": r["max_drawdown_pct"],
    }


rows = [
    run("baseline"),
    run("BTC regime filter", regime=True),
    run("no engulfing", patterns_allowed=["hammer", "momentum_close"]),
    run("momentum_close only", patterns_allowed=["momentum_close"]),
    run("regime + no engulfing", regime=True, patterns_allowed=["hammer", "momentum_close"]),
    run("regime + momentum only", regime=True, patterns_allowed=["momentum_close"]),
    run("regime + rsi60", regime=True, rsi_long_max=60),
    run("regime + target_r=2", regime=True, target_r=2.0),
    run("regime + no engulf + rsi60", regime=True,
        patterns_allowed=["hammer", "momentum_close"], rsi_long_max=60),
]
print(pd.DataFrame(rows).set_index("variant").round(2).to_string())
