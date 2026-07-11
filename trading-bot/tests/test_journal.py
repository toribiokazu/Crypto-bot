"""Journal writing (live loop) and journal analysis (weekly report)."""

import pytest

from bot.broker import Fill, Position
from bot.config import BotConfig
from bot.live import LiveTrader
from bot.report import consistency_warnings, load_journal, summarize, verdict


@pytest.fixture()
def trader(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = BotConfig()
    cfg.validate()
    return LiveTrader(cfg, mode="paper", state_path=str(tmp_path / "state.json"))


def make_pos(pnl_side: str) -> tuple[Position, Fill]:
    pos = Position(
        id="T1", symbol="BTC/USDT", direction=1, qty=0.001, entry=50_000.0,
        initial_stop=49_000.0, stop=49_000.0, best_price=50_000.0,
        risk_amount=1.0, opened_at="2026-07-01T00:00:00+00:00", reason="test setup",
    )
    exit_px = 52_000.0 if pnl_side == "win" else 49_000.0
    return pos, Fill(price=exit_px, qty=0.001, fee=0.05)


def test_journal_appends_and_reloads(trader):
    pos, fill = make_pos("win")
    trader._journal(pos, fill, "target")
    pos2, fill2 = make_pos("loss")
    trader._journal(pos2, fill2, "stop")

    df = load_journal(trader.journal_path)
    assert len(df) == 2
    assert set(df["exit_reason"]) == {"target", "stop"}
    # win pnl: (52000-50000)*0.001 - 0.05 = 1.95 -> +1.95R on $1 risk
    assert df["pnl"].iloc[0] == pytest.approx(1.95)
    assert df["r_multiple"].iloc[0] == pytest.approx(1.95)


def test_summary_and_verdict_small_sample(trader):
    for side, reason in [("win", "target"), ("loss", "stop"), ("loss", "stop")]:
        pos, fill = make_pos(side)
        trader._journal(pos, fill, reason)
    s = summarize(load_journal(trader.journal_path))
    assert s["n_trades"] == 3
    assert s["win_rate_pct"] == pytest.approx(100.0 / 3.0)
    assert "too few" in verdict(s)  # must refuse to judge the edge on 3 trades


def test_consistency_warning_on_stop_overshoot(trader):
    pos, _ = make_pos("loss")
    # exit far past the stop: -1.55R after fees -> mechanical warning expected
    bad_fill = Fill(price=48_450.0, qty=0.001, fee=0.05)
    trader._journal(pos, bad_fill, "stop")
    s = summarize(load_journal(trader.journal_path))
    warns = consistency_warnings(s)
    assert any("slipping" in w or "1.25R" in w for w in warns)
