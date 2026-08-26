"""Checks for the trend logic.

    python3 -m market.tests.test_trend

Built on constructed series whose answer is known in advance, so the classifier
is verified without a network round trip.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..brief import build_report
from ..config import DEFAULT_TIMEFRAMES
from ..providers import SyntheticProvider
from ..trend import (
    Alignment,
    Direction,
    InsufficientData,
    TrendConfig,
    analyse_instrument,
    classify_timeframe,
    resolve_alignment,
)

CFG = TrendConfig()


def _series(values) -> pd.Series:
    index = pd.date_range("2026-08-01", periods=len(values), freq="15min")
    return pd.Series(np.asarray(values, dtype=float), index=index)


def _drifting(n: int, drift: float, vol: float = 0.0, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    shocks = rng.normal(0.0, vol, n)
    return _series(100.0 * np.exp(np.cumsum(np.full(n, drift) + shocks)))


def test_rising_series_is_up() -> None:
    tf = classify_timeframe(_drifting(60, 0.002, vol=0.001), "15m", "15 min", CFG)
    assert tf.direction is Direction.UP, tf.direction
    assert tf.strength == 3, (tf.strength, tf.z_score)
    assert tf.confirmations == 2, tf.votes
    assert tf.pct_change > 0


def test_falling_series_is_down() -> None:
    tf = classify_timeframe(_drifting(60, -0.002, vol=0.001), "15m", "15 min", CFG)
    assert tf.direction is Direction.DOWN, tf.direction
    assert tf.strength == 3, (tf.strength, tf.z_score)
    assert tf.pct_change < 0


def test_strength_grades_with_distance_past_the_gate() -> None:
    """Strength must vary with the size of the move, not sit pinned at 3."""
    strengths = [
        classify_timeframe(
            _drifting(80, drift, vol=0.004, seed=11), "15m", "15 min", CFG
        ).strength
        for drift in (0.0004, 0.0009, 0.0018)
    ]
    assert strengths == [1, 2, 3], strengths


def test_zero_variance_series_does_not_explode() -> None:
    """A perfectly smooth path has no measured noise to divide by."""
    tf = classify_timeframe(_drifting(60, 0.002, vol=0.0), "15m", "15 min", CFG)
    assert tf.direction is Direction.UP
    assert tf.z_score < 1e6, tf.z_score


def test_flat_series_is_flat() -> None:
    tf = classify_timeframe(_series([100.0] * 60), "1h", "1 timme", CFG)
    assert tf.direction is Direction.FLAT, tf.votes
    assert tf.strength == 0


def test_noise_rarely_produces_a_confident_verdict() -> None:
    """A random walk genuinely drifts sometimes, so this can never be zero.

    What it must not do is call a strong trend on most windows. The gate is set
    so roughly one window in five clears it; anything much above that means the
    EMA readings have started overriding the volatility scaling again.
    """
    calls = 0
    for seed in range(30):
        tf = classify_timeframe(_drifting(80, 0.0, vol=0.004, seed=seed),
                                "15m", "15 min", CFG)
        if tf.direction is not Direction.FLAT and tf.strength == 3:
            calls += 1
    assert calls <= 8, f"{calls}/30 starka utslag på ren brus"


def test_volatility_scaling_mutes_the_same_move() -> None:
    """Identical drift, more noise — the momentum vote should back off."""
    quiet = classify_timeframe(_drifting(80, 0.0004, vol=0.0004, seed=3),
                               "15m", "15 min", CFG)
    noisy = classify_timeframe(_drifting(80, 0.0004, vol=0.010, seed=3),
                               "15m", "15 min", CFG)
    assert abs(noisy.z_score) < abs(quiet.z_score), (noisy.z_score, quiet.z_score)


def test_short_series_raises() -> None:
    try:
        classify_timeframe(_series([100.0] * 5), "15m", "15 min", CFG)
    except InsufficientData:
        return
    raise AssertionError("förväntade InsufficientData")


def test_alignment_cases() -> None:
    up, down, flat = Direction.UP, Direction.DOWN, Direction.FLAT

    assert resolve_alignment([up, up, up]) is Alignment.ALIGNED_UP
    assert resolve_alignment([down, down, down]) is Alignment.ALIGNED_DOWN
    # The case that motivated the whole thing: 15m up, 1h still down.
    assert resolve_alignment([up, down, down]) is Alignment.REBOUND
    assert resolve_alignment([down, up, up]) is Alignment.PULLBACK
    assert resolve_alignment([flat, flat, flat]) is Alignment.FLAT
    # A flat middle rung must not break an otherwise consistent picture.
    assert resolve_alignment([up, flat, up]) is Alignment.ALIGNED_UP
    assert resolve_alignment([up, down, up]) is Alignment.MIXED


def test_unavailable_timeframe_is_recorded_not_dropped() -> None:
    trend = analyse_instrument(
        symbol="TEST",
        label="Test",
        series_by_timeframe={
            "15m": ("15 min", _drifting(60, 0.002)),
            "1h": ("1 timme", _series([100.0] * 4)),  # too short
        },
        cfg=CFG,
    )
    assert "15m" in trend.timeframes
    assert trend.unavailable == ("1h",)


def test_synthetic_rebound_reaches_the_rebound_verdict() -> None:
    """End to end: a long down leg with a late rally must read as a rebound."""
    provider = SyntheticProvider(assignments={"REB": "rebound"})
    report = build_report(
        provider,
        instruments=(__import__("market").Instrument("REB", "Rebound"),),
        timeframes=DEFAULT_TIMEFRAMES,
    )
    trend = report.trends[0]
    assert trend.timeframes["15m"].direction is Direction.UP, trend.timeframes["15m"].votes
    assert trend.timeframes["1d"].direction is Direction.DOWN, trend.timeframes["1d"].votes
    assert trend.alignment is Alignment.REBOUND, trend.alignment


def test_report_records_provider_failures() -> None:
    class Broken:
        name = "broken"

        def close_series(self, symbol, timeframe):
            from ..providers import MarketDataError
            raise MarketDataError("nere")

    report = build_report(
        Broken(),
        instruments=(__import__("market").Instrument("X", "X"),),
        timeframes=DEFAULT_TIMEFRAMES,
    )
    assert report.trends == []
    assert "X" in report.errors


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - test harness
            failed += 1
            print(f"FAIL  {test.__name__}: {exc}")
        else:
            print(f"ok    {test.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} godkända")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
