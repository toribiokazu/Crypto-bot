#!/usr/bin/env python3
"""Backtest the strategy before letting it near any account.

Examples:
  # offline sanity check on synthetic regime-switching data
  python run_backtest.py --synthetic --seed 7

  # real history straight from the exchange (public data, no keys needed)
  python run_backtest.py --fetch --limit 3000

  # from a CSV you downloaded yourself (ts,open,high,low,close,volume)
  python run_backtest.py --csv data/BTCUSDT-4h.csv
"""

from __future__ import annotations

import argparse
import sys

from bot.backtest import format_report, run_backtest
from bot.config import load_config
from bot.data import fetch_ohlcv, load_csv, synthetic_ohlcv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--synthetic", action="store_true", help="use generated regime-switching data")
    src.add_argument("--fetch", action="store_true", help="fetch real candles via ccxt")
    src.add_argument("--csv", help="load candles from a CSV file")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--limit", type=int, default=3000, help="candles to fetch/generate")
    ap.add_argument("--seed", type=int, default=42, help="seed for --synthetic")
    ap.add_argument("--trades", action="store_true", help="print every trade")
    args = ap.parse_args()

    cfg = load_config(args.config)
    symbols = cfg.exchange.symbol_list
    tf_hours = {"1m": 1 / 60, "5m": 1 / 12, "15m": 0.25, "30m": 0.5,
                "1h": 1, "2h": 2, "4h": 4, "1d": 24}[cfg.exchange.timeframe]

    if args.synthetic:
        data = {
            sym: synthetic_ohlcv(
                n=args.limit, seed=args.seed + k * 1000,
                start_price=30_000.0 / (k + 1), timeframe_hours=tf_hours,
            )
            for k, sym in enumerate(symbols)
        }
        print(f"Synthetic data: {len(symbols)} symbols x {args.limit} x {cfg.exchange.timeframe} candles (seed={args.seed})")
    elif args.csv:
        data = load_csv(args.csv)
        print(f"CSV data: {len(data)} candles from {args.csv}")
    else:
        ex = cfg.exchange
        data = {}
        for sym in symbols:
            print(f"Fetching {args.limit} x {ex.timeframe} candles of {sym} from {ex.exchange_id}...")
            data[sym] = fetch_ohlcv(ex.exchange_id, sym, ex.timeframe, limit=args.limit)
            print(f"  got {len(data[sym])}: {data[sym].index[0]} .. {data[sym].index[-1]}")

    result = run_backtest(data, cfg)
    print(format_report(result, cfg))

    if args.trades:
        print("\n#   symbol     dir   entry      exit        pnl      R  exit_reason")
        for k, t in enumerate(result.trades, 1):
            d = "LONG " if t.direction > 0 else "SHORT"
            print(
                f"{k:<3d} {t.symbol:<10s}{d} {t.entry:>9.2f} {t.exit:>9.2f} "
                f"{t.pnl:>9.2f} {t.r_multiple:>6.2f}  {t.exit_reason}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
