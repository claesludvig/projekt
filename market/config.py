"""Watchlist and timeframe definitions for the morning market brief."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Timeframe:
    """One rung on the timeframe ladder.

    `interval` and `period` are Yahoo Finance arguments. Yahoo caps intraday
    history: 15m data reaches back ~60 days, 1m only ~7, so `period` is chosen
    per interval rather than shared.
    """

    key: str
    label: str
    interval: str
    period: str


# Ordered short to long. Alignment logic depends on this order.
DEFAULT_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe("15m", "15 min", "15m", "5d"),
    Timeframe("1h", "1 timme", "60m", "1mo"),
    Timeframe("1d", "1 dag", "1d", "6mo"),
)


@dataclass(frozen=True)
class Instrument:
    symbol: str
    label: str


DEFAULT_WATCHLIST: tuple[Instrument, ...] = (
    Instrument("^OMX", "OMXS30"),
    Instrument("^GSPC", "S&P 500"),
    Instrument("^IXIC", "Nasdaq"),
    Instrument("^TNX", "US 10 år"),
    Instrument("BZ=F", "Brent"),
    Instrument("SEK=X", "USD/SEK"),
)


def timeframes_by_key(keys: tuple[str, ...] | None = None) -> tuple[Timeframe, ...]:
    """Select timeframes by key, preserving the short-to-long ordering."""
    if not keys:
        return DEFAULT_TIMEFRAMES
    known = {tf.key: tf for tf in DEFAULT_TIMEFRAMES}
    missing = [k for k in keys if k not in known]
    if missing:
        raise ValueError(
            f"Okänt tidsintervall: {', '.join(missing)}. "
            f"Tillgängliga: {', '.join(known)}"
        )
    return tuple(tf for tf in DEFAULT_TIMEFRAMES if tf.key in set(keys))
