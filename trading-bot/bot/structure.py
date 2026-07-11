"""Market structure: trend classification and support/resistance zones.

Everything here is computed strictly from bars <= the current bar, and swing
pivots are only used once confirmed (pivot bar + swing_right bars have closed).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

UP, DOWN, RANGE = 1, -1, 0


@dataclass
class Zone:
    lo: float
    hi: float
    kind: str  # "support" | "resistance"
    touches: int

    def contains(self, price: float, pad: float = 0.0) -> bool:
        return (self.lo - pad) <= price <= (self.hi + pad)


def trend_at(df: pd.DataFrame, i: int) -> int:
    """Trend from EMA alignment + price location. df must carry ema columns."""
    close = df["close"].iat[i]
    fast = df["ema_fast"].iat[i]
    slow = df["ema_slow"].iat[i]
    if pd.isna(fast) or pd.isna(slow):
        return RANGE
    if fast > slow and close > slow:
        return UP
    if fast < slow and close < slow:
        return DOWN
    return RANGE


def confirmed_swings(df: pd.DataFrame, i: int, lookback: int) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """(swing_highs, swing_lows) as (bar_pos, price), confirmed as of bar i."""
    start = max(0, i - lookback)
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    sh = df["swing_high"].to_numpy()
    sl = df["swing_low"].to_numpy()
    ci = df["swing_confirm_idx"].to_numpy()
    for j in range(start, i + 1):
        if ci[j] == -1 or ci[j] > i:
            continue  # not yet confirmed at bar i -> invisible to the bot
        if sh[j]:
            highs.append((j, float(df["high"].iat[j])))
        if sl[j]:
            lows.append((j, float(df["low"].iat[j])))
    return highs, lows


def build_zones(df: pd.DataFrame, i: int, lookback: int, cluster_atr_mult: float = 0.5) -> list[Zone]:
    """Cluster confirmed swing points into horizontal S/R zones."""
    a = df["atr"].iat[i]
    if pd.isna(a) or a <= 0:
        return []
    tol = float(a) * cluster_atr_mult
    highs, lows = confirmed_swings(df, i, lookback)
    zones: list[Zone] = []

    def cluster(points: list[tuple[int, float]], kind: str) -> None:
        for _, price in points:
            placed = False
            for z in zones:
                if z.kind == kind and z.contains(price, pad=tol):
                    z.lo = min(z.lo, price)
                    z.hi = max(z.hi, price)
                    z.touches += 1
                    placed = True
                    break
            if not placed:
                zones.append(Zone(lo=price, hi=price, kind=kind, touches=1))

    cluster(lows, "support")
    cluster(highs, "resistance")
    return zones


def structure_trend(df: pd.DataFrame, i: int, lookback: int) -> int:
    """Trend from swing sequence: higher-highs/higher-lows vs lower/lower."""
    highs, lows = confirmed_swings(df, i, lookback)
    if len(highs) < 2 or len(lows) < 2:
        return RANGE
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    ll = lows[-1][1] < lows[-2][1]
    if hh and hl:
        return UP
    if lh and ll:
        return DOWN
    return RANGE


def combined_trend(df: pd.DataFrame, i: int, lookback: int) -> int:
    """EMA trend and swing-structure trend must not conflict.

    EMA trend leads; structure may abstain (RANGE) but must not oppose.
    """
    ema_t = trend_at(df, i)
    if ema_t == RANGE:
        return RANGE
    struct_t = structure_trend(df, i, lookback)
    if struct_t != RANGE and struct_t != ema_t:
        return RANGE
    return ema_t
