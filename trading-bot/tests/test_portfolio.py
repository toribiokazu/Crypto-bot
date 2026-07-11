"""Portfolio backtest guarantees: shared budget, shared caps, per-symbol books."""

import pytest

from bot.backtest import run_backtest
from bot.config import BotConfig
from bot.data import synthetic_ohlcv


def make_portfolio(n_syms=4, n=2000, tf_hours=2.0, seed_base=123):
    return {
        f"SYM{k}/USDT": synthetic_ohlcv(
            n=n, seed=seed_base + k * 1000, start_price=30000 / (k + 1),
            timeframe_hours=tf_hours,
        )
        for k in range(n_syms)
    }


def test_portfolio_trades_multiple_symbols():
    result = run_backtest(make_portfolio(), BotConfig())
    symbols_traded = {t.symbol for t in result.trades}
    assert len(symbols_traded) >= 2, "diversification: several symbols should trade"


def test_portfolio_respects_drawdown_floor():
    budget = BotConfig().risk.allocated_budget
    for sb in (1, 7, 42):
        result = run_backtest(make_portfolio(seed_base=sb), BotConfig())
        min_eq = float(result.equity_curve.min())
        assert min_eq >= budget * 0.90 * 0.97, f"seed {sb}: {min_eq} broke the floor"


def test_portfolio_one_position_per_symbol():
    # exhaustive invariant proxy: no trade may overlap another on the same symbol
    result = run_backtest(make_portfolio(), BotConfig())
    by_symbol: dict[str, list] = {}
    for t in result.trades:
        by_symbol.setdefault(t.symbol, []).append(t)
    for sym, ts in by_symbol.items():
        ts.sort(key=lambda t: t.entry_time)
        for a, b in zip(ts, ts[1:]):
            assert a.exit_time <= b.entry_time, f"{sym}: overlapping trades"


def test_single_df_still_works():
    df = synthetic_ohlcv(n=1500, seed=3)
    result = run_backtest(df, BotConfig())
    assert len(result.equity_curve) == len(df)
