"""Snapshot MEXC candles for the analysis scripts: spot pairs into
data_cache/ and USDT perpetuals into data_cache_swap/. Existing files are
kept, so delete a CSV (or the whole directory) to refresh it."""
from pathlib import Path

import ccxt
import pandas as pd

from bot.config import load_config
from bot.data import OHLCV_COLS, fetch_ohlcv

cfg = load_config("config.mexc-paper.yaml")

spot = Path("data_cache")
spot.mkdir(exist_ok=True)
for sym in cfg.exchange.symbol_list:
    p = spot / (sym.replace("/", "_") + ".csv")
    if p.exists():
        continue
    df = fetch_ohlcv(cfg.exchange.exchange_id, sym, cfg.exchange.timeframe, limit=1500)
    df.to_csv(p)
    print(f"spot {sym}: {len(df)} rows {df.index[0]} .. {df.index[-1]}")

swap = Path("data_cache_swap")
swap.mkdir(exist_ok=True)
ex = ccxt.mexc({"options": {"defaultType": "swap"}, "enableRateLimit": True})
ex.load_markets()
for sym in cfg.exchange.symbol_list:
    fsym = sym + ":USDT"
    p = swap / (sym.replace("/", "_") + ".csv")
    if p.exists():
        continue
    if fsym not in ex.markets:
        print(f"skip {fsym}: no perpetual on MEXC")
        continue
    rows = ex.fetch_ohlcv(fsym, cfg.exchange.timeframe, limit=1500)
    df = pd.DataFrame(rows, columns=["ts", *OHLCV_COLS])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df.set_index("ts").to_csv(p)
    print(f"swap {fsym}: {len(rows)} rows")
