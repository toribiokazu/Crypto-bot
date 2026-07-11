"""Event-driven backtester.

Execution model (deliberately conservative):
- A signal on bar i is filled at the OPEN of bar i+1 (no lookahead).
- Stops are evaluated intrabar: for a long, if low <= stop the exit fills at
  the stop (or at the open if the bar gapped through it).
- If a bar could have hit both the stop and the target, the STOP is assumed
  to have been hit first.
- Fees and slippage are charged on every fill.
- The RiskManager sizes every entry and its kill switch halts new entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .broker import PaperBroker
from .config import BotConfig
from .indicators import add_indicators
from .risk import RiskManager
from .strategy import PriceActionStrategy, Signal


@dataclass
class TradeRecord:
    entry_time: object
    exit_time: object
    direction: int
    entry: float
    exit: float
    qty: float
    pnl: float
    r_multiple: float
    reason: str
    exit_reason: str


@dataclass
class BacktestResult:
    trades: list[TradeRecord]
    equity_curve: pd.Series
    halted: bool
    halt_reason: str
    metrics: dict = field(default_factory=dict)

    def compute_metrics(self, budget: float) -> dict:
        eq = self.equity_curve
        trades = self.trades
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        gross_win = sum(t.pnl for t in wins)
        gross_loss = -sum(t.pnl for t in losses)
        peak = eq.cummax()
        dd = (eq - peak) / peak
        m = {
            "final_equity": float(eq.iloc[-1]) if len(eq) else budget,
            "total_return_pct": (float(eq.iloc[-1]) / budget - 1) * 100 if len(eq) else 0.0,
            "n_trades": len(trades),
            "win_rate_pct": 100.0 * len(wins) / len(trades) if trades else 0.0,
            "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0,
            "avg_win": gross_win / len(wins) if wins else 0.0,
            "avg_loss": -gross_loss / len(losses) if losses else 0.0,
            "expectancy_per_trade": (gross_win - gross_loss) / len(trades) if trades else 0.0,
            "avg_r": float(np.mean([t.r_multiple for t in trades])) if trades else 0.0,
            "max_drawdown_pct": float(dd.min()) * -100 if len(eq) else 0.0,
            "worst_loss_vs_budget_pct": (
                -min((t.pnl for t in trades), default=0.0) / budget * 100
            ),
            "halted_by_kill_switch": self.halted,
        }
        self.metrics = m
        return m


def run_backtest(df: pd.DataFrame, cfg: BotConfig) -> BacktestResult:
    scfg = cfg.strategy
    data = add_indicators(df, scfg)
    strat = PriceActionStrategy(scfg)
    risk = RiskManager(cfg.risk)
    broker = PaperBroker(cfg.risk.allocated_budget, cfg.risk.fee_pct, cfg.risk.slippage_pct)

    trades: list[TradeRecord] = []
    equity_points: list[float] = []
    pending: Signal | None = None
    cooldown_until = -1
    warmup = scfg.ema_slow + scfg.swing_right + 5
    n = len(data)

    opens = data["open"].to_numpy()
    highs = data["high"].to_numpy()
    lows = data["low"].to_numpy()
    closes = data["close"].to_numpy()
    atrs = data["atr"].to_numpy()
    index = data.index

    def close_at(pos, price: float, i: int, exit_reason: str) -> None:
        fill = broker.close_position(pos.id, price)
        risk.release_position(pos.id)
        if pos.direction > 0:
            pnl = (fill.price - pos.entry) * pos.qty - fill.fee
        else:
            pnl = (pos.entry - fill.price) * pos.qty - fill.fee
        r_unit = abs(pos.entry - pos.initial_stop) * pos.qty
        trades.append(
            TradeRecord(
                entry_time=pos.opened_at, exit_time=index[i], direction=pos.direction,
                entry=pos.entry, exit=fill.price, qty=pos.qty, pnl=pnl,
                r_multiple=pnl / r_unit if r_unit > 0 else 0.0,
                reason=pos.reason, exit_reason=exit_reason,
            )
        )
        nonlocal cooldown_until
        cooldown_until = i + scfg.cooldown_bars

    for i in range(n):
        if i < warmup:
            equity_points.append(broker.equity(closes[i]))
            continue

        # 1) fill last bar's signal at this bar's open
        if pending is not None and not risk.halted:
            entry_px = float(opens[i])
            stop = pending.stop
            # sanity: the gap didn't already invalidate the setup
            valid = (pending.direction > 0 and entry_px > stop) or (
                pending.direction < 0 and entry_px < stop
            )
            if valid:
                equity = broker.equity(entry_px)
                qty, risk_amt = risk.position_size(
                    "pending", entry_px, stop, equity, broker.cash
                )
                if qty > 0:
                    pos = broker.open_position(
                        symbol=cfg.exchange.symbol, direction=pending.direction,
                        qty=qty, price=entry_px, stop=stop, risk_amount=risk_amt,
                        opened_at=index[i], reason=pending.reason,
                    )
                    if pos is not None:
                        risk.register_position(pos.id, risk_amt)
            pending = None

        # 2) manage open positions on this bar
        for pos in list(broker.positions.values()):
            if pos.direction > 0:
                target = (
                    pos.entry + scfg.target_r * (pos.entry - pos.initial_stop)
                    if scfg.target_r
                    else None
                )
                if lows[i] <= pos.stop:
                    close_at(pos, min(float(opens[i]), pos.stop), i, "stop")
                    continue
                if target is not None and highs[i] >= target:
                    close_at(pos, max(float(opens[i]), target), i, "target")
                    continue
                pos.best_price = max(pos.best_price, float(closes[i]))
            else:
                target = (
                    pos.entry - scfg.target_r * (pos.initial_stop - pos.entry)
                    if scfg.target_r
                    else None
                )
                if highs[i] >= pos.stop:
                    close_at(pos, max(float(opens[i]), pos.stop), i, "stop")
                    continue
                if target is not None and lows[i] <= target:
                    close_at(pos, min(float(opens[i]), target), i, "target")
                    continue
                pos.best_price = min(pos.best_price, float(closes[i]))

            new_stop = strat.manage_stop(
                pos.direction, pos.entry, pos.initial_stop, pos.stop,
                pos.best_price, float(atrs[i]),
            )
            if new_stop != pos.stop:
                pos.stop = new_stop
                risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, pos.direction)

        # 3) mark equity, check the kill switch
        equity = broker.equity(closes[i])
        equity_points.append(equity)
        risk.check_kill_switch(equity)

        # 4) look for a fresh setup completing on this bar
        if not risk.halted and i > cooldown_until and not broker.positions:
            pending = strat.evaluate(data, i)

    # liquidate anything still open at the last close for a clean equity number
    for pos in list(broker.positions.values()):
        close_at(pos, float(closes[-1]), n - 1, "end_of_data")

    curve = pd.Series(equity_points, index=index[: len(equity_points)])
    result = BacktestResult(
        trades=trades, equity_curve=curve,
        halted=risk.halted, halt_reason=risk.halt_reason,
    )
    result.compute_metrics(cfg.risk.allocated_budget)
    return result


def format_report(result: BacktestResult, cfg: BotConfig) -> str:
    m = result.metrics
    lines = [
        "=" * 62,
        " BACKTEST REPORT",
        "=" * 62,
        f" Budget allocated        : {cfg.risk.allocated_budget:>12,.2f}",
        f" Final equity            : {m['final_equity']:>12,.2f}",
        f" Total return            : {m['total_return_pct']:>11.2f}%",
        f" Trades                  : {m['n_trades']:>12d}",
        f" Win rate                : {m['win_rate_pct']:>11.1f}%",
        f" Profit factor           : {m['profit_factor']:>12.2f}",
        f" Avg win / avg loss      : {m['avg_win']:>8.2f} / {m['avg_loss']:.2f}",
        f" Expectancy per trade    : {m['expectancy_per_trade']:>12.2f}",
        f" Average R multiple      : {m['avg_r']:>12.2f}",
        f" Max drawdown            : {m['max_drawdown_pct']:>11.2f}%",
        f" Worst single loss/budget: {m['worst_loss_vs_budget_pct']:>11.2f}%",
        f" Kill switch triggered   : {str(m['halted_by_kill_switch']):>12s}",
        "=" * 62,
    ]
    if result.halted:
        lines.append(" " + result.halt_reason)
    return "\n".join(lines)
