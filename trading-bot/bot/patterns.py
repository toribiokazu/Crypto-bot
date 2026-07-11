"""Candlestick pattern recognition on OHLC data.

Each detector answers: "does a reversal pattern complete at bar i?"
using only bars <= i (no lookahead). Patterns are scored so the strategy
can require a minimum conviction rather than a bare boolean.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class PatternHit:
    name: str
    direction: int  # +1 bullish, -1 bearish
    score: float  # 0..1 conviction


def _body(o: float, c: float) -> float:
    return abs(c - o)


def _range(h: float, l: float) -> float:
    return max(h - l, 1e-12)


def bullish_engulfing(df: pd.DataFrame, i: int) -> PatternHit | None:
    if i < 1:
        return None
    o1, c1 = df["open"].iat[i - 1], df["close"].iat[i - 1]
    o2, c2, h2, l2 = (
        df["open"].iat[i],
        df["close"].iat[i],
        df["high"].iat[i],
        df["low"].iat[i],
    )
    prev_red = c1 < o1
    curr_green = c2 > o2
    engulfs = c2 >= max(o1, c1) and o2 <= min(o1, c1)
    if not (prev_red and curr_green and engulfs and _body(o1, c1) > 0):
        return None
    body_dominance = _body(o2, c2) / _range(h2, l2)
    size_ratio = min(_body(o2, c2) / max(_body(o1, c1), 1e-12), 3.0) / 3.0
    return PatternHit("bullish_engulfing", +1, 0.5 * body_dominance + 0.5 * size_ratio)


def bearish_engulfing(df: pd.DataFrame, i: int) -> PatternHit | None:
    if i < 1:
        return None
    o1, c1 = df["open"].iat[i - 1], df["close"].iat[i - 1]
    o2, c2, h2, l2 = (
        df["open"].iat[i],
        df["close"].iat[i],
        df["high"].iat[i],
        df["low"].iat[i],
    )
    prev_green = c1 > o1
    curr_red = c2 < o2
    engulfs = o2 >= max(o1, c1) and c2 <= min(o1, c1)
    if not (prev_green and curr_red and engulfs and _body(o1, c1) > 0):
        return None
    body_dominance = _body(o2, c2) / _range(h2, l2)
    size_ratio = min(_body(o2, c2) / max(_body(o1, c1), 1e-12), 3.0) / 3.0
    return PatternHit("bearish_engulfing", -1, 0.5 * body_dominance + 0.5 * size_ratio)


def hammer(df: pd.DataFrame, i: int) -> PatternHit | None:
    """Bullish pin bar: long lower wick, close in upper part of the range."""
    o, h, l, c = (
        df["open"].iat[i],
        df["high"].iat[i],
        df["low"].iat[i],
        df["close"].iat[i],
    )
    rng = _range(h, l)
    body = _body(o, c)
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    if body <= 0 or rng <= 0:
        return None
    if lower_wick >= 2.0 * body and upper_wick <= body and (c - l) / rng >= 0.6:
        wick_strength = min(lower_wick / (body + 1e-12), 4.0) / 4.0
        return PatternHit("hammer", +1, 0.5 + 0.5 * wick_strength)
    return None


def shooting_star(df: pd.DataFrame, i: int) -> PatternHit | None:
    """Bearish pin bar: long upper wick, close in lower part of the range."""
    o, h, l, c = (
        df["open"].iat[i],
        df["high"].iat[i],
        df["low"].iat[i],
        df["close"].iat[i],
    )
    rng = _range(h, l)
    body = _body(o, c)
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    if body <= 0 or rng <= 0:
        return None
    if upper_wick >= 2.0 * body and lower_wick <= body and (h - c) / rng >= 0.6:
        wick_strength = min(upper_wick / (body + 1e-12), 4.0) / 4.0
        return PatternHit("shooting_star", -1, 0.5 + 0.5 * wick_strength)
    return None


def momentum_close(df: pd.DataFrame, i: int) -> PatternHit | None:
    """Strong directional close beyond the prior bar's extreme with a
    dominant body — continuation/breakout style confirmation."""
    if i < 1:
        return None
    o, h, l, c = (
        df["open"].iat[i],
        df["high"].iat[i],
        df["low"].iat[i],
        df["close"].iat[i],
    )
    body_dom = _body(o, c) / _range(h, l)
    if body_dom < 0.7:
        return None
    if c > o and c > df["high"].iat[i - 1]:
        return PatternHit("momentum_close", +1, body_dom)
    if c < o and c < df["low"].iat[i - 1]:
        return PatternHit("momentum_close", -1, body_dom)
    return None


ALL_DETECTORS = (bullish_engulfing, bearish_engulfing, hammer, shooting_star, momentum_close)


def detect(df: pd.DataFrame, i: int, direction: int, min_score: float = 0.4) -> PatternHit | None:
    """Best pattern at bar i in the requested direction, or None."""
    best: PatternHit | None = None
    for det in ALL_DETECTORS:
        hit = det(df, i)
        if hit and hit.direction == direction and hit.score >= min_score:
            if best is None or hit.score > best.score:
                best = hit
    return best
