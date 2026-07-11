"""Event-driven portfolio backtester.

Accepts a single OHLCV DataFrame or a {symbol: DataFrame} dict; all symbols
share one budget, one RiskManager (10% total-risk cap, 10% kill switch,
daily loss pause), and one PaperBroker.

Execution model (deliberately conservative):
- A signal on bar i is filled at the OPEN of bar i+1 (no lookahead).
- Stops are evaluated intrabar: for a long, if low <= stop the exit fills at
  the stop (or at the open if the bar gapped through it).
- Bar ordering per symbol: stop first, then partial take, then target.
- Fees and slippage are charged on every fill.
- One position per symbol; the RiskManager sizes and can veto every entry.
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
    symbol: str
    entry_time: object
    exit_time: object
    direction: int
    entry: float
    exit: float
    qty: float
    pnl: float
    fees: float
    r_multiple: float
    reason: str
    exit_reason: str


@dataclass
class BacktestResult:
    trades: list[TradeRecord]
    equity_curve: pd.Series
    halted: bool
    halt_reason: str
    paused_days: int = 0
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
        span_days = (
            max((eq.index[-1] - eq.index[0]).total_seconds() / 86400.0, 1e-9)
            if len(eq) > 1
            else 1e-9
        )
        m = {
            "final_equity": float(eq.iloc[-1]) if len(eq) else budget,
            "total_return_pct": (float(eq.iloc[-1]) / budget - 1) * 100 if len(eq) else 0.0,
            "n_trades": len(trades),
            "trades_per_day": len(trades) / span_days,
            "win_rate_pct": 100.0 * len(wins) / len(trades) if trades else 0.0,
            "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0,
            "avg_win": gross_win / len(wins) if wins else 0.0,
            "avg_loss": -gross_loss / len(losses) if losses else 0.0,
            "expectancy_per_trade": (gross_win - gross_loss) / len(trades) if trades else 0.0,
            "avg_r": float(np.mean([t.r_multiple for t in trades])) if trades else 0.0,
            "total_fees": sum(t.fees for t in trades),
            "max_drawdown_pct": float(dd.min()) * -100 if len(eq) else 0.0,
            "worst_loss_vs_budget_pct": (
                -min((t.pnl for t in trades), default=0.0) / budget * 100
            ),
            "halted_by_kill_switch": self.halted,
            "paused_days": self.paused_days,
        }
        self.metrics = m
        return m


class _SymbolBook:
    """Per-symbol bar arrays plus a positional cursor into the union clock."""

    def __init__(self, symbol: str, df: pd.DataFrame, warmup: int):
        self.symbol = symbol
        self.df = df
        self.index = df.index
        self.pos_of_ts = {ts: k for k, ts in enumerate(df.index)}
        self.open = df["open"].to_numpy()
        self.high = df["high"].to_numpy()
        self.low = df["low"].to_numpy()
        self.close = df["close"].to_numpy()
        self.atr = df["atr"].to_numpy()
        self.warmup = warmup
        self.pending: Signal | None = None
        self.cooldown_until = -1
        self.last_close: float | None = None


def run_backtest(data: pd.DataFrame | dict[str, pd.DataFrame], cfg: BotConfig) -> BacktestResult:
    scfg = cfg.strategy
    if isinstance(data, pd.DataFrame):
        data = {cfg.exchange.symbol_list[0]: data}

    strat = PriceActionStrategy(scfg)
    risk = RiskManager(cfg.risk)
    broker = PaperBroker(cfg.risk.allocated_budget, cfg.risk.fee_pct, cfg.risk.slippage_pct)

    warmup = scfg.ema_slow + scfg.swing_right + 5
    books = {
        sym: _SymbolBook(sym, add_indicators(df, scfg), warmup) for sym, df in data.items()
    }
    clock = sorted(set().union(*[set(b.index) for b in books.values()]))

    trades: list[TradeRecord] = []
    equity_points: list[float] = []
    equity_index: list = []
    paused_days: set = set()
    entry_fees: dict[str, float] = {}

    def close_at(book: _SymbolBook, pos, price: float, ts, exit_reason: str) -> None:
        fill = broker.close_position(pos.id, price)
        risk.release_position(pos.id)
        if pos.direction > 0:
            pnl = (fill.price - pos.entry) * fill.qty - fill.fee
        else:
            pnl = (pos.entry - fill.price) * fill.qty - fill.fee
        pnl += pos.realized_pnl  # profit already banked by partial exits
        r_unit = pos.risk_amount
        trades.append(
            TradeRecord(
                symbol=book.symbol, entry_time=pos.opened_at, exit_time=ts,
                direction=pos.direction, entry=pos.entry, exit=fill.price,
                qty=fill.qty, pnl=pnl,
                fees=fill.fee + entry_fees.pop(pos.id, 0.0),
                r_multiple=pnl / r_unit if r_unit > 0 else 0.0,
                reason=pos.reason, exit_reason=exit_reason,
            )
        )
        i = book.pos_of_ts[ts]
        book.cooldown_until = i + scfg.cooldown_bars

    def positions_for(sym: str):
        return [p for p in broker.positions.values() if p.symbol == sym]

    for ts in clock:
        # ---- per-symbol bar processing -------------------------------------
        for book in books.values():
            i = book.pos_of_ts.get(ts)
            if i is None:
                continue
            book.last_close = float(book.close[i])
            if i < book.warmup:
                book.pending = None
                continue

            # 1) fill last bar's signal at this bar's open
            if book.pending is not None and risk.can_open:
                sig = book.pending
                entry_px = float(book.open[i])
                valid = (sig.direction > 0 and entry_px > sig.stop) or (
                    sig.direction < 0 and entry_px < sig.stop
                )
                if valid and not positions_for(book.symbol):
                    marks = {s: b.last_close for s, b in books.items() if b.last_close}
                    equity = broker.equity(marks)
                    vs = risk.vol_scalar(float(book.atr[i]), entry_px)
                    qty, risk_amt = risk.position_size(
                        "pending", entry_px, sig.stop, equity, broker.cash, vol_scalar=vs
                    )
                    if qty > 0:
                        cash_before = broker.cash
                        pos = broker.open_position(
                            symbol=book.symbol, direction=sig.direction,
                            qty=qty, price=entry_px, stop=sig.stop, risk_amount=risk_amt,
                            opened_at=ts, reason=sig.reason,
                        )
                        if pos is not None:
                            risk.register_position(pos.id, risk_amt)
                            entry_fees[pos.id] = (
                                cash_before - broker.cash - pos.qty * pos.entry
                                if pos.direction > 0 else 0.0
                            )
            book.pending = None

            # 2) manage this symbol's open position on this bar
            for pos in positions_for(book.symbol):
                r_dist = abs(pos.entry - pos.initial_stop)
                if pos.direction > 0:
                    target = pos.entry + scfg.target_r * r_dist if scfg.target_r else None
                    partial_at = (
                        pos.entry + scfg.partial_take_r * r_dist
                        if scfg.partial_take_r and not pos.partial_done
                        else None
                    )
                    if book.low[i] <= pos.stop:
                        close_at(book, pos, min(float(book.open[i]), pos.stop), ts, "stop")
                        continue
                    if partial_at is not None and book.high[i] >= partial_at:
                        px = max(float(book.open[i]), partial_at)
                        broker.close_partial(pos.id, pos.qty * scfg.partial_take_fraction, px)
                        pos.partial_done = True
                        pos.stop = max(pos.stop, pos.entry)
                        risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, 1)
                    if target is not None and book.high[i] >= target:
                        close_at(book, pos, max(float(book.open[i]), target), ts, "target")
                        continue
                    pos.best_price = max(pos.best_price, float(book.close[i]))
                else:
                    target = pos.entry - scfg.target_r * r_dist if scfg.target_r else None
                    partial_at = (
                        pos.entry - scfg.partial_take_r * r_dist
                        if scfg.partial_take_r and not pos.partial_done
                        else None
                    )
                    if book.high[i] >= pos.stop:
                        close_at(book, pos, max(float(book.open[i]), pos.stop), ts, "stop")
                        continue
                    if partial_at is not None and book.low[i] <= partial_at:
                        px = min(float(book.open[i]), partial_at)
                        broker.close_partial(pos.id, pos.qty * scfg.partial_take_fraction, px)
                        pos.partial_done = True
                        pos.stop = min(pos.stop, pos.entry)
                        risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, -1)
                    if target is not None and book.low[i] <= target:
                        close_at(book, pos, min(float(book.open[i]), target), ts, "target")
                        continue
                    pos.best_price = min(pos.best_price, float(book.close[i]))

                new_stop = strat.manage_stop(
                    pos.direction, pos.entry, pos.initial_stop, pos.stop,
                    pos.best_price, float(book.atr[i]),
                )
                if new_stop != pos.stop:
                    pos.stop = new_stop
                    risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, pos.direction)

        # ---- portfolio-level bookkeeping on the shared clock ---------------
        marks = {s: b.last_close for s, b in books.items() if b.last_close}
        equity = broker.equity(marks)
        equity_points.append(equity)
        equity_index.append(ts)
        risk.check_kill_switch(equity)
        risk.observe(equity, ts.date())
        if risk.paused_today:
            paused_days.add(ts.date())

        # ---- new setups ----------------------------------------------------
        if risk.can_open:
            for book in books.values():
                i = book.pos_of_ts.get(ts)
                if i is None or i < book.warmup:
                    continue
                if i > book.cooldown_until and not positions_for(book.symbol):
                    book.pending = strat.evaluate(book.df, i)

    # liquidate anything still open at the last close for a clean equity number
    for book in books.values():
        for pos in positions_for(book.symbol):
            close_at(book, pos, float(book.close[-1]), book.index[-1], "end_of_data")

    curve = pd.Series(equity_points, index=pd.DatetimeIndex(equity_index))
    result = BacktestResult(
        trades=trades, equity_curve=curve,
        halted=risk.halted, halt_reason=risk.halt_reason,
        paused_days=len(paused_days),
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
        f" Trades per day          : {m['trades_per_day']:>12.1f}",
        f" Win rate                : {m['win_rate_pct']:>11.1f}%",
        f" Profit factor           : {m['profit_factor']:>12.2f}",
        f" Avg win / avg loss      : {m['avg_win']:>8.2f} / {m['avg_loss']:.2f}",
        f" Expectancy per trade    : {m['expectancy_per_trade']:>12.2f}",
        f" Average R multiple      : {m['avg_r']:>12.2f}",
        f" Total fees paid         : {m['total_fees']:>12.2f}",
        f" Max drawdown            : {m['max_drawdown_pct']:>11.2f}%",
        f" Worst single loss/budget: {m['worst_loss_vs_budget_pct']:>11.2f}%",
        f" Daily-pause days        : {m['paused_days']:>12d}",
        f" Kill switch triggered   : {str(m['halted_by_kill_switch']):>12s}",
        "=" * 62,
    ]
    if result.halted:
        lines.append(" " + result.halt_reason)
    return "\n".join(lines)
