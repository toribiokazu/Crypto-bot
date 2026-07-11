#!/usr/bin/env python3
"""Review the live/demo trade journal.

  python run_report.py                    # auto-detects trades_demo.csv / trades_paper.csv
  python run_report.py --journal my.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bot.report import format_report, load_journal, summarize


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--journal", help="path to a trades CSV; default: all trades_*.csv here")
    args = ap.parse_args()

    paths = [Path(args.journal)] if args.journal else sorted(Path(".").glob("trades_*.csv"))
    if not paths:
        print("No journal files found (trades_demo.csv / trades_paper.csv). "
              "Run the bot first: python run_live.py --mode demo --config config.small.yaml")
        return 1
    for p in paths:
        df = load_journal(p)
        print(format_report(summarize(df), str(p)))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
