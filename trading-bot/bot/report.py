"""Weekly performance review of the live/demo trade journal.

Reads the trades_{mode}.csv written by the live loop and answers the two
questions that matter, in order:

1. CONSISTENCY — is live behaviour matching the backtest's assumptions?
   (losses near -1R, slippage sane, frequency in range). Broken mechanics
   are fixable immediately, whatever the sample size.
2. PERFORMANCE — only once there are enough trades (30+) do win rate and
   expectancy comparisons mean anything. Retuning the algorithm off a
   handful of trades is curve-fitting to noise, and the report says so.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

MIN_TRADES_FOR_TUNING = 30

# what the backtest sims project for the small-account profile
EXPECTED = {
    "win_rate_pct": 46.0,
    "avg_r": 0.10,  # expectancy per trade in R
    "trades_per_week": 3.0,
}


def load_journal(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["closed_at_utc"] = pd.to_datetime(df["closed_at_utc"], utc=True, format="ISO8601")
    for col in ("qty", "entry", "exit", "pnl", "r_multiple"):
        df[col] = pd.to_numeric(df[col])
    return df.sort_values("closed_at_utc").reset_index(drop=True)


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n_trades": 0}
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]
    span_days = max(
        (df["closed_at_utc"].iloc[-1] - df["closed_at_utc"].iloc[0]).total_seconds() / 86400.0,
        1.0,
    )
    cum = df["pnl"].cumsum()
    dd = cum - cum.cummax()
    return {
        "n_trades": len(df),
        "span_days": span_days,
        "trades_per_week": len(df) / span_days * 7,
        "total_pnl": float(df["pnl"].sum()),
        "win_rate_pct": 100.0 * len(wins) / len(df),
        "avg_r": float(df["r_multiple"].mean()),
        "avg_win_r": float(wins["r_multiple"].mean()) if len(wins) else 0.0,
        "avg_loss_r": float(losses["r_multiple"].mean()) if len(losses) else 0.0,
        "worst_r": float(df["r_multiple"].min()),
        "max_drawdown_pnl": float(dd.min()),
        "overshoot_stops": int((df["r_multiple"] < -1.25).sum()),
        "by_symbol": df.groupby("symbol")["pnl"].agg(["count", "sum"]).to_dict("index"),
        "by_exit": df.groupby("exit_reason")["pnl"].agg(["count", "sum"]).to_dict("index"),
    }


def consistency_warnings(s: dict) -> list[str]:
    """Mechanical problems worth fixing at ANY sample size."""
    warns = []
    if s["n_trades"] == 0:
        return warns
    if s["overshoot_stops"] > 0:
        warns.append(
            f"{s['overshoot_stops']} trade(s) lost more than 1.25R — stops are "
            "slipping past their level. Check exchange latency/slippage; the "
            "backtest assumes losses stay near -1R."
        )
    if s["avg_loss_r"] < -1.15:
        warns.append(
            f"Average loss is {s['avg_loss_r']:.2f}R (should be ~-1R): real "
            "slippage/fees exceed the modelled 0.15% per side."
        )
    if s["trades_per_week"] > EXPECTED["trades_per_week"] * 2.5:
        warns.append(
            f"Trading {s['trades_per_week']:.1f}x/week vs ~{EXPECTED['trades_per_week']:.0f} "
            "expected — entries may be misfiring; review the signals in the journal."
        )
    return warns


def verdict(s: dict) -> str:
    if s["n_trades"] == 0:
        return "No trades yet — nothing to review."
    if s["n_trades"] < MIN_TRADES_FOR_TUNING:
        return (
            f"{s['n_trades']} trades is too few to judge the edge "
            f"({MIN_TRADES_FOR_TUNING}+ needed). Fix mechanical warnings if any; "
            "do NOT retune strategy parameters yet — that would be fitting noise."
        )
    wr_gap = s["win_rate_pct"] - EXPECTED["win_rate_pct"]
    r_gap = s["avg_r"] - EXPECTED["avg_r"]
    if s["avg_r"] > 0 and wr_gap > -10:
        return (
            "Live performance is consistent with the backtest projection. "
            "No algorithm change warranted — keep collecting data."
        )
    if r_gap < -0.15:
        return (
            f"Expectancy {s['avg_r']:+.2f}R/trade is materially below the "
            f"projected {EXPECTED['avg_r']:+.2f}R over a meaningful sample. "
            "Candidate causes, in order: costs higher than modelled, regime "
            "mismatch, strategy edge not present live. Review before retuning."
        )
    return "Mixed results — within noise of the projection. Keep collecting data."


def format_report(s: dict, path: str) -> str:
    if s["n_trades"] == 0:
        return f"Journal {path}: no trades recorded yet."
    lines = [
        "=" * 62,
        f" TRADE JOURNAL REVIEW — {path}",
        "=" * 62,
        f" Trades                  : {s['n_trades']:>10d}  ({s['trades_per_week']:.1f}/week over {s['span_days']:.0f} days)",
        f" Total PnL               : {s['total_pnl']:>+10.2f}",
        f" Win rate                : {s['win_rate_pct']:>9.1f}%  (projected ~{EXPECTED['win_rate_pct']:.0f}%)",
        f" Expectancy              : {s['avg_r']:>+9.3f}R  (projected ~{EXPECTED['avg_r']:+.2f}R)",
        f" Avg win / avg loss      : {s['avg_win_r']:+.2f}R / {s['avg_loss_r']:+.2f}R",
        f" Worst trade             : {s['worst_r']:>+9.2f}R",
        f" Max drawdown (PnL)      : {s['max_drawdown_pnl']:>+10.2f}",
        "",
        " By exit reason:",
    ]
    for reason, agg in s["by_exit"].items():
        lines.append(f"   {reason:<12s} {int(agg['count']):>4d} trades  pnl {agg['sum']:+.2f}")
    lines.append("")
    lines.append(" By symbol:")
    for sym, agg in sorted(s["by_symbol"].items(), key=lambda kv: kv[1]["sum"]):
        lines.append(f"   {sym:<12s} {int(agg['count']):>4d} trades  pnl {agg['sum']:+.2f}")
    warns = consistency_warnings(s)
    if warns:
        lines.append("")
        lines.append(" MECHANICAL WARNINGS:")
        for w in warns:
            lines.append(f"   ! {w}")
    lines.append("")
    lines.append(" VERDICT: " + verdict(s))
    lines.append("=" * 62)
    return "\n".join(lines)
