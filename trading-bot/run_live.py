#!/usr/bin/env python3
"""Run the bot against live market data.

  python run_live.py --mode paper   # live data, simulated fills, no keys
  python run_live.py --mode demo    # real orders on the exchange TESTNET

Demo mode needs testnet API keys in .env (see .env.example). The bot refuses
to start in demo mode unless exchange.testnet is true in config.yaml.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bot.config import load_config
from bot.live import LiveTrader


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["paper", "demo"], default="paper")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--state", default="state.json")
    ap.add_argument("--once", action="store_true", help="run one decision cycle and exit")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")],
    )

    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
        except ImportError:
            logging.warning("python-dotenv not installed; export keys manually")

    cfg = load_config(args.config)
    trader = LiveTrader(cfg, mode=args.mode, state_path=args.state)
    if args.once:
        trader.on_candle_close()
        return 0
    trader.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
