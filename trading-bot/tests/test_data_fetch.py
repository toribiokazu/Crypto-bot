import ccxt
import pytest

from bot.broker import CcxtBroker
from bot.data import fetch_ohlcv

TF_MS = 4 * 3600 * 1000
NOW_MS = 1_752_000_000_000  # fixed "now" so tests are deterministic


class FakeMexc:
    """Mimics MEXC pagination: 500 rows per call, most recent page when
    since is omitted, full history available when paginating from `since`."""

    PAGE = 500
    HISTORY = 5000  # candles of history available on the venue

    rateLimit = 0
    urls: dict = {"test": None}

    def __init__(self, params=None):
        self.first_ts = NOW_MS - self.HISTORY * TF_MS

    def parse_timeframe(self, timeframe):
        assert timeframe == "4h"
        return TF_MS // 1000

    def milliseconds(self):
        return NOW_MS

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
        limit = min(limit, self.PAGE)
        if since is None:
            since = NOW_MS - limit * TF_MS
        start = max(since, self.first_ts)
        start += (-start) % TF_MS  # align up to the candle grid
        rows = []
        ts = start
        while len(rows) < limit and ts <= NOW_MS:
            rows.append([ts, 1.0, 1.0, 1.0, 1.0, 1.0])
            ts += TF_MS
        return rows


@pytest.fixture
def fake_mexc(monkeypatch):
    monkeypatch.setattr(ccxt, "fakemexc", FakeMexc, raising=False)


def test_fetch_paginates_past_exchange_page_cap(fake_mexc):
    df = fetch_ohlcv("fakemexc", "BTC/USDT", "4h", limit=1500)
    assert len(df) == 1500
    # ends at the present, not 1500 candles ago
    assert df.index[-1].value // 10**6 >= NOW_MS - TF_MS
    assert df.index.is_monotonic_increasing
    assert not df.index.duplicated().any()


def test_fetch_explicit_since_still_honoured(fake_mexc):
    since = NOW_MS - 800 * TF_MS
    df = fetch_ohlcv("fakemexc", "BTC/USDT", "4h", limit=600, since_ms=since)
    assert len(df) == 600
    assert df.index[0].value // 10**6 >= since


def test_fetch_short_history_returns_what_exists(fake_mexc, monkeypatch):
    monkeypatch.setattr(FakeMexc, "HISTORY", 300)
    df = fetch_ohlcv("fakemexc", "BTC/USDT", "4h", limit=1500)
    assert 250 <= len(df) <= 301  # everything the venue has, no crash


def test_demo_broker_refuses_exchange_without_testnet():
    with pytest.raises(RuntimeError, match="no testnet"):
        CcxtBroker("mexc", "key", "secret", testnet=True)
