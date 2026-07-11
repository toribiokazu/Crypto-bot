"""Market data: exchange fetch (ccxt), CSV files, and a synthetic generator.

The synthetic generator exists so the backtester and test-suite run with no
network access. It produces regime-switching price series (trends, ranges,
shakeouts) that stress the strategy more honestly than a pure random walk.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def fetch_ohlcv(
    exchange_id: str,
    symbol: str,
    timeframe: str,
    limit: int = 1000,
    since_ms: int | None = None,
    testnet: bool = False,
    api_key: str = "",
    api_secret: str = "",
    max_batches: int = 20,
) -> pd.DataFrame:
    """Fetch OHLCV candles via ccxt, paginating past the per-call limit."""
    import ccxt  # imported lazily: not needed for backtests on CSV/synthetic

    klass = getattr(ccxt, exchange_id)
    ex = klass({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
    if testnet:
        if not ex.urls.get("test"):
            raise RuntimeError(
                f"{exchange_id} has no testnet/sandbox. Demo mode needs an "
                "exchange with one (binance, bybit); paper mode works anywhere."
            )
        ex.set_sandbox_mode(True)

    rows: list[list[float]] = []
    cursor = since_ms
    for _ in range(max_batches):
        batch = ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=min(limit - len(rows), 1000))
        if not batch:
            break
        rows.extend(batch)
        if len(rows) >= limit or len(batch) < 2:
            break
        cursor = batch[-1][0] + 1
        time.sleep((ex.rateLimit or 200) / 1000.0)

    df = pd.DataFrame(rows, columns=["ts", *OHLCV_COLS])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.drop_duplicates("ts").set_index("ts").sort_index()
    return df[OHLCV_COLS].astype(float)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load candles from CSV with columns: ts (ISO or ms), open,high,low,close,volume."""
    df = pd.read_csv(path)
    ts = df.columns[0]
    if pd.api.types.is_numeric_dtype(df[ts]):
        df[ts] = pd.to_datetime(df[ts], unit="ms", utc=True)
    else:
        df[ts] = pd.to_datetime(df[ts], utc=True)
    df = df.set_index(ts).sort_index()
    df.columns = [c.lower() for c in df.columns]
    return df[OHLCV_COLS].astype(float)


def synthetic_ohlcv(
    n: int = 3000,
    seed: int = 42,
    start_price: float = 30_000.0,
    timeframe_hours: float = 4,
) -> pd.DataFrame:
    """Regime-switching synthetic candles (bull trend / bear trend / chop).

    Regimes persist for 80–300 bars. Volatility clusters, and each candle's
    high/low wicks are generated so intrabar stop-hit simulation is meaningful.
    Drift/vol are calibrated for 4h bars and rescaled GBM-style (drift ~ dt,
    vol ~ sqrt(dt)) for other timeframes.
    """
    rng = np.random.default_rng(seed)
    dt = timeframe_hours / 4.0
    drifts = {"bull": 0.0012 * dt, "bear": -0.0012 * dt, "chop": 0.0}
    vols = {k: v * dt**0.5 for k, v in {"bull": 0.012, "bear": 0.016, "chop": 0.008}.items()}
    regimes = list(drifts)

    closes = np.empty(n)
    opens = np.empty(n)
    highs = np.empty(n)
    lows = np.empty(n)
    vols_out = np.empty(n)

    price = start_price
    i = 0
    regime = "bull"
    while i < n:
        length = int(rng.integers(80, 300))
        drift, vol = drifts[regime], vols[regime]
        for _ in range(min(length, n - i)):
            o = price
            r = rng.normal(drift, vol)
            # occasional shakeout wick against the move
            c = o * float(np.exp(r))
            body_hi, body_lo = max(o, c), min(o, c)
            wick = abs(rng.normal(0, vol * 0.8)) * o
            h = body_hi + wick * float(rng.uniform(0.2, 1.0))
            l = body_lo - wick * float(rng.uniform(0.2, 1.0))
            opens[i], highs[i], lows[i], closes[i] = o, h, max(l, 1e-9), c
            vols_out[i] = float(rng.lognormal(4, 0.5))
            price = c
            i += 1
            if i >= n:
                break
        regime = regimes[int(rng.integers(0, len(regimes)))]

    idx = pd.date_range("2023-01-01", periods=n, freq=f"{int(timeframe_hours * 60)}min", tz="UTC")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": vols_out},
        index=idx,
    )
