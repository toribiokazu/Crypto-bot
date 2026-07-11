"""The risk manager is the load-bearing wall — test it hard."""

import pytest

from bot.config import RiskConfig
from bot.risk import RiskManager


def make_rm(**overrides) -> RiskManager:
    cfg = RiskConfig(
        allocated_budget=1000.0,
        risk_per_trade_pct=1.5,
        max_total_risk_pct=10.0,
        max_drawdown_pct=10.0,
        max_open_positions=3,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return RiskManager(cfg)


def test_position_size_from_stop_distance():
    rm = make_rm()
    # risk 1.5% of 1000 = $15; stop distance $50 -> qty 0.3
    qty, risk = rm.position_size("p1", entry=1000.0, stop=950.0, equity=1000.0, available_cash=1000.0)
    assert risk == pytest.approx(15.0)
    assert qty == pytest.approx(15.0 / 50.0)


def test_wider_stop_means_smaller_position():
    rm = make_rm()
    q_narrow, _ = rm.position_size("a", 1000.0, 980.0, 1000.0, 10_000.0)
    q_wide, _ = rm.position_size("b", 1000.0, 900.0, 1000.0, 10_000.0)
    assert q_wide < q_narrow


def test_total_open_risk_never_exceeds_10_percent():
    rm = make_rm(risk_per_trade_pct=4.0, max_open_positions=10)
    total = 0.0
    for i in range(10):
        qty, risk = rm.position_size(f"p{i}", 100.0, 95.0, 1000.0, 1e9)
        if qty == 0:
            break
        rm.register_position(f"p{i}", risk)
        total += risk
    assert total <= 100.0 + 1e-6  # 10% of 1000
    # and the next request must be rejected outright
    qty, _ = rm.position_size("overflow", 100.0, 95.0, 1000.0, 1e9)
    assert qty == 0.0


def test_third_trade_shrinks_into_headroom():
    rm = make_rm(risk_per_trade_pct=4.0)
    for name in ("p1", "p2"):
        _, risk = rm.position_size(name, 100.0, 95.0, 1000.0, 1e9)
        rm.register_position(name, risk)
    # 80 of 100 used; the next 40-risk request must shrink to 20
    _, risk3 = rm.position_size("p3", 100.0, 95.0, 1000.0, 1e9)
    assert risk3 == pytest.approx(20.0)


def test_kill_switch_halts_at_10_percent_drawdown():
    rm = make_rm()
    assert not rm.check_kill_switch(equity=901.0)
    assert rm.check_kill_switch(equity=900.0)  # exactly -10%
    qty, _ = rm.position_size("p", 100.0, 95.0, 900.0, 900.0)
    assert qty == 0.0
    assert "KILL SWITCH" in rm.halt_reason


def test_halt_persists_until_manual_reset():
    rm = make_rm()
    rm.check_kill_switch(equity=850.0)
    assert rm.check_kill_switch(equity=999.0)  # recovery does NOT auto-resume
    rm.reset_halt()
    assert not rm.halted


def test_ceilings_cannot_be_configured_above_10():
    with pytest.raises(ValueError):
        make_rm(max_total_risk_pct=25.0)
    with pytest.raises(ValueError):
        make_rm(max_drawdown_pct=50.0)


def test_no_leverage_cap_by_cash():
    rm = make_rm()
    # tiny cash: position must be capped by what the account can afford
    qty, risk = rm.position_size("p", entry=100.0, stop=99.0, equity=1000.0, available_cash=50.0)
    assert qty * 100.0 <= 50.0 + 1e-9
    assert risk == pytest.approx(qty * 1.0)


def test_stop_move_to_breakeven_releases_risk():
    rm = make_rm()
    qty, risk = rm.position_size("p", 100.0, 95.0, 1000.0, 1e9)
    rm.register_position("p", risk)
    assert rm.total_open_risk == pytest.approx(15.0)
    rm.update_position_risk("p", entry=100.0, stop=100.0, qty=qty, direction=1)
    assert rm.total_open_risk == pytest.approx(0.0)
    # freed headroom is available for the next setup
    qty2, _ = rm.position_size("q", 100.0, 95.0, 1000.0, 1e9)
    assert qty2 > 0
