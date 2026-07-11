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
    qty, risk = rm.position_size("p", entry=100.0, stop=95.0, equity=1000.0, available_cash=50.0)
    assert qty * 100.0 <= 50.0 + 1e-9
    assert risk == pytest.approx(qty * 5.0)


def test_cost_gate_rejects_tight_stops():
    rm = make_rm()  # fee 0.10 + slip 0.05 per side -> 0.3% round trip
    # 1% stop < 5 x 0.3% -> rejected regardless of signal quality
    qty, _ = rm.position_size("p", entry=100.0, stop=99.0, equity=1000.0, available_cash=1000.0)
    assert qty == 0.0
    # 5% stop passes the gate
    qty, _ = rm.position_size("p", entry=100.0, stop=95.0, equity=1000.0, available_cash=1000.0)
    assert qty > 0.0


def test_vol_scalar_shrinks_risk_in_hot_markets():
    rm = make_rm()  # vol_target_atr_pct = 0.6 by default
    assert rm.vol_scalar(atr=0.5, price=100.0) == pytest.approx(1.0)  # 0.5% <= target
    assert rm.vol_scalar(atr=1.2, price=100.0) == pytest.approx(0.5)  # 1.2% -> half size


def test_daily_loss_pause():
    rm = make_rm()  # daily_loss_pause_pct = 3.0 by default
    from datetime import date

    d1, d2 = date(2026, 1, 1), date(2026, 1, 2)
    rm.observe(1000.0, d1)
    rm.observe(985.0, d1)  # -1.5% intraday: fine
    assert rm.can_open
    rm.observe(969.0, d1)  # -3.1% intraday: paused for the day
    assert rm.paused_today and not rm.can_open
    qty, _ = rm.position_size("p", 100.0, 95.0, 969.0, 969.0)
    assert qty == 0.0
    rm.observe(969.0, d2)  # new day: trading resumes automatically
    assert not rm.paused_today and rm.can_open


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
