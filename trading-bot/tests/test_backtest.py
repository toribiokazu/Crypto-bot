"""End-to-end guarantees the backtester must uphold on any data."""

import numpy as np
import pytest

from bot.backtest import run_backtest
from bot.config import BotConfig
from bot.data import synthetic_ohlcv


@pytest.fixture(scope="module")
def cfg():
    c = BotConfig()
    c.validate()
    return c


def run(seed: int, n: int = 2500, cfg: BotConfig | None = None):
    c = cfg or BotConfig()
    return run_backtest(synthetic_ohlcv(n=n, seed=seed), c)


def test_backtest_produces_trades(cfg):
    result = run(seed=42, cfg=cfg)
    assert result.metrics["n_trades"] > 5


def test_drawdown_never_exceeds_kill_switch_floor_materially():
    """Across many seeds, equity must never fall meaningfully below the
    10% floor: the kill switch stops new trades and open risk is capped."""
    budget = BotConfig().risk.allocated_budget
    for seed in range(10):
        result = run(seed=seed)
        floor = budget * 0.90
        min_eq = float(result.equity_curve.min())
        # small tolerance for slippage/fees/gap on the final open position
        assert min_eq >= floor * 0.97, f"seed {seed}: equity {min_eq} broke floor"


def test_single_trade_loss_is_small_vs_budget():
    """No individual trade may lose more than ~2x the per-trade risk
    (gaps can exceed the stop slightly, but never catastrophically)."""
    for seed in (1, 7, 42):
        result = run(seed=seed)
        cfg = BotConfig()
        per_trade = cfg.risk.allocated_budget * cfg.risk.risk_per_trade_pct / 100.0
        for t in result.trades:
            assert t.pnl >= -per_trade * 2.5, f"trade lost {t.pnl}, cap {per_trade}"


def test_no_lookahead_prefix_consistency():
    """Signals must not depend on future bars: trades whose entry occurs
    inside a truncated prefix must be identical for the prefix run."""
    cfg = BotConfig()
    df = synthetic_ohlcv(n=1500, seed=3)
    full = run_backtest(df, cfg)
    prefix_len = 1000
    prefix = run_backtest(df.iloc[:prefix_len], cfg)
    cutoff = df.index[prefix_len - 60]  # ignore the tail where open trades differ
    full_early = [
        (t.entry_time, round(t.entry, 6), t.direction)
        for t in full.trades
        if t.entry_time is not None and t.entry_time < cutoff
    ]
    prefix_early = [
        (t.entry_time, round(t.entry, 6), t.direction)
        for t in prefix.trades
        if t.entry_time is not None and t.entry_time < cutoff
    ]
    assert full_early == prefix_early


def test_equity_curve_matches_cash_after_liquidation():
    result = run(seed=42)
    assert float(result.equity_curve.iloc[-1]) == pytest.approx(
        result.metrics["final_equity"]
    )
    assert np.isfinite(result.metrics["profit_factor"]) or result.metrics["profit_factor"] == float("inf")
