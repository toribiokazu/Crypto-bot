"""Price-action strategy: trend + pullback to structure + pattern confirmation.

The playbook (long side; shorts are the mirror image):

1. TREND    — EMA alignment (fast > slow, price above slow) AND the swing
              structure (higher highs / higher lows) must agree or abstain.
2. LOCATION — price has pulled back INTO value: the bar touches the fast EMA
              or a confirmed support zone. We never chase extended moves.
3. TRIGGER  — a bullish reversal candlestick (engulfing, hammer, momentum
              close) completes at that location, and RSI is not overbought.
4. STOP     — below the pattern's low minus an ATR buffer. If the implied
              stop is wider than max_stop_atr_mult * ATR, the setup is skipped:
              wide stops mean bad location.
5. EXIT     — asymmetric by design: stop moves to breakeven at +1R, then an
              ATR chandelier trail follows the move. Losers are cut at -1R,
              winners are left to run. This is how the system stays profitable
              without needing a high win rate.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import patterns, structure
from .config import StrategyConfig


@dataclass
class Signal:
    direction: int  # +1 long, -1 short
    entry_hint: float  # close of the signal bar (fills happen at next open)
    stop: float
    reason: str


class PriceActionStrategy:
    def __init__(self, cfg: StrategyConfig):
        self.cfg = cfg

    def evaluate(self, df: pd.DataFrame, i: int) -> Signal | None:
        """Look for a setup completing at bar i. df must be indicator-enriched."""
        cfg = self.cfg
        if i < cfg.ema_slow + cfg.swing_right:
            return None
        a = df["atr"].iat[i]
        if pd.isna(a) or a <= 0:
            return None

        trend = structure.combined_trend(df, i, cfg.structure_lookback)
        if trend == structure.UP:
            return self._long_setup(df, i, float(a))
        if trend == structure.DOWN and cfg.allow_shorts:
            return self._short_setup(df, i, float(a))
        return None

    # ---------------------------------------------------------------- longs
    def _long_setup(self, df: pd.DataFrame, i: int, a: float) -> Signal | None:
        cfg = self.cfg
        low = float(df["low"].iat[i])
        close = float(df["close"].iat[i])
        ema_fast = float(df["ema_fast"].iat[i])
        pad = a * cfg.zone_touch_atr_mult

        touched_value = low <= ema_fast + pad
        zone_hit = None
        if not touched_value:
            for z in structure.build_zones(df, i, cfg.structure_lookback, cfg.zone_cluster_atr_mult):
                if z.kind == "support" and z.contains(low, pad=pad):
                    zone_hit = z
                    break
            if zone_hit is None:
                return None

        if float(df["rsi"].iat[i]) > cfg.rsi_long_max:
            return None
        hit = patterns.detect(df, i, direction=+1, min_score=cfg.min_pattern_score)
        if hit is None:
            return None

        pattern_low = min(low, float(df["low"].iat[i - 1]))
        stop = pattern_low - a * cfg.stop_atr_buffer
        if close - stop > a * cfg.max_stop_atr_mult or stop >= close:
            return None

        where = "support zone" if zone_hit else "fast EMA"
        return Signal(
            direction=+1,
            entry_hint=close,
            stop=stop,
            reason=f"uptrend pullback to {where} + {hit.name} (score {hit.score:.2f})",
        )

    # --------------------------------------------------------------- shorts
    def _short_setup(self, df: pd.DataFrame, i: int, a: float) -> Signal | None:
        cfg = self.cfg
        high = float(df["high"].iat[i])
        close = float(df["close"].iat[i])
        ema_fast = float(df["ema_fast"].iat[i])
        pad = a * cfg.zone_touch_atr_mult

        touched_value = high >= ema_fast - pad
        zone_hit = None
        if not touched_value:
            for z in structure.build_zones(df, i, cfg.structure_lookback, cfg.zone_cluster_atr_mult):
                if z.kind == "resistance" and z.contains(high, pad=pad):
                    zone_hit = z
                    break
            if zone_hit is None:
                return None

        if float(df["rsi"].iat[i]) < cfg.rsi_short_min:
            return None
        hit = patterns.detect(df, i, direction=-1, min_score=cfg.min_pattern_score)
        if hit is None:
            return None

        pattern_high = max(high, float(df["high"].iat[i - 1]))
        stop = pattern_high + a * cfg.stop_atr_buffer
        if stop - close > a * cfg.max_stop_atr_mult or stop <= close:
            return None

        where = "resistance zone" if zone_hit else "fast EMA"
        return Signal(
            direction=-1,
            entry_hint=close,
            stop=stop,
            reason=f"downtrend rally to {where} + {hit.name} (score {hit.score:.2f})",
        )

    # ---------------------------------------------------------------- exits
    def manage_stop(
        self,
        direction: int,
        entry: float,
        initial_stop: float,
        current_stop: float,
        best_price: float,
        a: float,
    ) -> float:
        """Return the updated stop for an open position (never loosens).

        best_price is the most favourable close since entry (max close for
        longs, min close for shorts).
        """
        cfg = self.cfg
        r = abs(entry - initial_stop)
        if r <= 0:
            return current_stop
        # two-stage trail: loose while the trend develops, tight once the
        # runner is deep in profit so reversals give back less
        mult = cfg.trail_atr_mult
        if cfg.trail_tighten_after_r is not None:
            deep = (
                best_price >= entry + cfg.trail_tighten_after_r * r
                if direction > 0
                else best_price <= entry - cfg.trail_tighten_after_r * r
            )
            if deep:
                mult = cfg.trail_atr_mult_tight
        new_stop = current_stop
        if direction > 0:
            if best_price >= entry + cfg.breakeven_at_r * r:
                new_stop = max(new_stop, entry)  # breakeven
                new_stop = max(new_stop, best_price - mult * a)
        else:
            if best_price <= entry - cfg.breakeven_at_r * r:
                new_stop = min(new_stop, entry)
                new_stop = min(new_stop, best_price + mult * a)
        return new_stop
