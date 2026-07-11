"""Technical indicators computed with pandas/numpy only (no TA-Lib needed).

All functions take a DataFrame with columns: open, high, low, close, volume
(indexed by timestamp) and return Series aligned to that index.

Lookahead safety: swing_points marks a swing at bar i only using bars up to
i + right, and also returns the bar index at which the swing becomes KNOWN
(confirm_idx = i + right). Consumers must only act on swings whose
confirm_idx <= current bar, which the strategy and backtester enforce.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(50.0)


def swing_points(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    """Detect swing highs/lows (fractals).

    Returns a DataFrame with columns:
      swing_high, swing_low : bool, True at the pivot bar
      confirm_idx           : int positional index where the pivot is confirmed
                              (pivot position + right); -1 where no pivot.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    sh = np.zeros(n, dtype=bool)
    sl = np.zeros(n, dtype=bool)
    confirm = np.full(n, -1, dtype=int)

    for i in range(left, n - right):
        window_h = high[i - left : i + right + 1]
        window_l = low[i - left : i + right + 1]
        if high[i] == window_h.max() and (window_h == high[i]).sum() == 1:
            sh[i] = True
            confirm[i] = i + right
        if low[i] == window_l.min() and (window_l == low[i]).sum() == 1:
            sl[i] = True
            confirm[i] = i + right

    return pd.DataFrame(
        {"swing_high": sh, "swing_low": sl, "confirm_idx": confirm}, index=df.index
    )


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Return a copy of df enriched with every column the strategy needs."""
    out = df.copy()
    out["ema_fast"] = ema(out["close"], cfg.ema_fast)
    out["ema_slow"] = ema(out["close"], cfg.ema_slow)
    out["atr"] = atr(out, cfg.atr_period)
    out["rsi"] = rsi(out["close"], cfg.rsi_period)
    swings = swing_points(out, cfg.swing_left, cfg.swing_right)
    out["swing_high"] = swings["swing_high"]
    out["swing_low"] = swings["swing_low"]
    out["swing_confirm_idx"] = swings["confirm_idx"]
    return out
