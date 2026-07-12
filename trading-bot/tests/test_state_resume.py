import pytest

from bot.config import BotConfig
from bot.live import LiveTrader


def _trader(tmp_path, name="state.json"):
    cfg = BotConfig()
    cfg.risk.allocated_budget = 100.0
    return LiveTrader(cfg, mode="paper", state_path=str(tmp_path / name))


def test_paper_positions_survive_restart(tmp_path):
    t1 = _trader(tmp_path)
    pos = t1.broker.open_position(
        "BTC/USDT", +1, qty=0.001, price=50_000.0, stop=48_000.0,
        risk_amount=2.0, opened_at="2026-07-12T00:00:00+00:00", reason="test setup",
    )
    t1.risk.register_position(pos.id, 2.0)
    t1._save_state(t1.broker.equity({"BTC/USDT": 50_000.0}))

    t2 = _trader(tmp_path)  # fresh process, same state file
    assert len(t2.broker.positions) == 1
    p = next(iter(t2.broker.positions.values()))
    assert p.symbol == "BTC/USDT"
    assert p.qty == pytest.approx(pos.qty)
    assert p.entry == pytest.approx(pos.entry)
    assert p.initial_stop == pytest.approx(pos.initial_stop)
    assert p.risk_amount == pytest.approx(2.0)
    assert t2.broker.cash == pytest.approx(t1.broker.cash)
    # risk manager knows about the restored position again
    assert t2.risk.total_open_risk == pytest.approx(t1.risk.total_open_risk)
    # equity is identical before/after the restart
    marks = {"BTC/USDT": 51_000.0}
    assert t2.broker.equity(marks) == pytest.approx(t1.broker.equity(marks))


def test_restored_breakeven_stop_carries_zero_risk(tmp_path):
    t1 = _trader(tmp_path)
    pos = t1.broker.open_position(
        "ETH/USDT", +1, qty=0.01, price=3000.0, stop=2900.0, risk_amount=1.0,
    )
    t1.risk.register_position(pos.id, 1.0)
    pos.stop = pos.entry  # breakeven reached before the restart
    t1.risk.update_position_risk(pos.id, pos.entry, pos.stop, pos.qty, 1)
    t1._save_state(100.0)

    t2 = _trader(tmp_path)
    assert t2.risk.total_open_risk == pytest.approx(0.0)


def test_halted_state_still_restored(tmp_path):
    t1 = _trader(tmp_path)
    t1.risk.halted = True
    t1.risk.halt_reason = "KILL SWITCH: test"
    t1._save_state(89.0)
    t2 = _trader(tmp_path)
    assert t2.risk.halted is True
    assert "KILL SWITCH" in t2.risk.halt_reason


def test_old_state_format_does_not_crash(tmp_path):
    t1 = _trader(tmp_path)
    p = tmp_path / "state.json"
    p.write_text(
        '{"mode": "paper", "halted": false, "open_positions": '
        '[{"id": "P9", "symbol": "BTC/USDT", "direction": 1, "qty": 1.0, '
        '"entry": 100.0, "stop": 95.0, "reason": "old", "partial_done": false, '
        '"realized_pnl": 0.0}]}'
    )
    t2 = _trader(tmp_path)
    assert t2.broker.positions == {}  # skipped, not crashed
