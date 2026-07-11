import pandas as pd

from bot import patterns


def make_df(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df["volume"] = 1.0
    return df


def test_bullish_engulfing_detected():
    df = make_df([
        [100.0, 101.0, 97.0, 98.0],   # red
        [97.5, 103.0, 97.0, 102.5],   # green body engulfs prior body
    ])
    hit = patterns.bullish_engulfing(df, 1)
    assert hit is not None and hit.direction == 1


def test_bullish_engulfing_rejects_non_engulfing():
    df = make_df([
        [100.0, 101.0, 97.0, 98.0],
        [98.5, 100.0, 98.0, 99.5],  # green but body inside prior body
    ])
    assert patterns.bullish_engulfing(df, 1) is None


def test_hammer_detected():
    # long lower wick, small body near the top
    df = make_df([[100.0, 100.6, 96.0, 100.5]])
    hit = patterns.hammer(df, 0)
    assert hit is not None and hit.direction == 1


def test_shooting_star_detected():
    df = make_df([[100.0, 104.0, 99.5, 99.6]])
    hit = patterns.shooting_star(df, 0)
    assert hit is not None and hit.direction == -1


def test_momentum_close_needs_dominant_body():
    df = make_df([
        [100.0, 101.0, 99.0, 100.5],
        [100.5, 103.0, 100.4, 102.9],  # big body closing above prior high
    ])
    hit = patterns.momentum_close(df, 1)
    assert hit is not None and hit.direction == 1
    df2 = make_df([
        [100.0, 101.0, 99.0, 100.5],
        [100.5, 104.0, 99.0, 101.2],  # closes above prior high but wicky
    ])
    assert patterns.momentum_close(df2, 1) is None


def test_detect_returns_best_in_direction():
    df = make_df([
        [100.0, 101.0, 97.0, 98.0],
        [97.5, 103.0, 97.0, 102.5],
    ])
    hit = patterns.detect(df, 1, direction=+1)
    assert hit is not None
    assert patterns.detect(df, 1, direction=-1) is None
