"""Trailing-stop management: breakeven, chandelier, optional two-stage."""

import pytest

from bot.config import StrategyConfig
from bot.strategy import PriceActionStrategy


def make_strat(**kw) -> PriceActionStrategy:
    cfg = StrategyConfig()
    for k, v in kw.items():
        setattr(cfg, k, v)
    return PriceActionStrategy(cfg)


def test_stop_untouched_before_breakeven_threshold():
    s = make_strat(breakeven_at_r=1.0)
    # +0.5R only: stop must not move
    stop = s.manage_stop(1, entry=100.0, initial_stop=95.0, current_stop=95.0,
                         best_price=102.5, a=2.0)
    assert stop == 95.0


def test_breakeven_and_trail_after_1r():
    s = make_strat(breakeven_at_r=1.0, trail_atr_mult=3.5, trail_tighten_after_r=None)
    stop = s.manage_stop(1, 100.0, 95.0, 95.0, best_price=110.0, a=2.0)
    # breakeven (100) vs chandelier 110 - 7 = 103 -> 103
    assert stop == pytest.approx(103.0)


def test_stop_never_loosens():
    s = make_strat(trail_tighten_after_r=None)
    stop = s.manage_stop(1, 100.0, 95.0, current_stop=104.0, best_price=106.0, a=2.0)
    assert stop >= 104.0


def test_two_stage_trail_tightens_when_enabled():
    s = make_strat(trail_atr_mult=3.5, trail_tighten_after_r=3.0, trail_atr_mult_tight=2.0)
    # +4R (best 120 on 5-wide risk): tight trail 120 - 2*2 = 116
    stop = s.manage_stop(1, 100.0, 95.0, 95.0, best_price=120.0, a=2.0)
    assert stop == pytest.approx(116.0)
    # disabled -> loose trail 120 - 7 = 113
    s2 = make_strat(trail_atr_mult=3.5, trail_tighten_after_r=None)
    assert s2.manage_stop(1, 100.0, 95.0, 95.0, 120.0, 2.0) == pytest.approx(113.0)
