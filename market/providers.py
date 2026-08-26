"""Price sources for the market brief.

Three providers behind one interface:

* `YFinanceProvider` — live data from Yahoo Finance.
* `CsvProvider` — replays snapshots recorded earlier. Use this when the machine
  running the brief cannot reach Yahoo directly.
* `SyntheticProvider` — deterministic generated paths, for tests and demos.
  Never present its output as market data.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from .config import Timeframe


class MarketDataError(RuntimeError):
    """A provider could not return a usable series."""


class Provider(Protocol):
    name: str

    def close_series(self, symbol: str, timeframe: Timeframe) -> pd.Series:
        """Return closing prices indexed by timestamp, oldest first."""


# --------------------------------------------------------------------------
# Live
# --------------------------------------------------------------------------


class YFinanceProvider:
    name = "yfinance"

    def __init__(self, auto_adjust: bool = False) -> None:
        self.auto_adjust = auto_adjust

    def close_series(self, symbol: str, timeframe: Timeframe) -> pd.Series:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - depends on install
            raise MarketDataError("yfinance är inte installerat") from exc

        try:
            frame = yf.Ticker(symbol).history(
                period=timeframe.period,
                interval=timeframe.interval,
                auto_adjust=self.auto_adjust,
            )
        except Exception as exc:
            raise MarketDataError(
                f"{symbol} {timeframe.key}: hämtning misslyckades ({exc})"
            ) from exc

        if frame.empty or "Close" not in frame:
            raise MarketDataError(f"{symbol} {timeframe.key}: tom serie från Yahoo")

        series = frame["Close"].dropna()
        if series.empty:
            raise MarketDataError(f"{symbol} {timeframe.key}: inga stängningskurser")
        return series


# --------------------------------------------------------------------------
# Recorded
# --------------------------------------------------------------------------


def _slug(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", symbol).strip("_").lower()


class CsvProvider:
    name = "csv"

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def _path(self, symbol: str, timeframe: Timeframe) -> Path:
        return self.directory / f"{_slug(symbol)}__{timeframe.key}.csv"

    def close_series(self, symbol: str, timeframe: Timeframe) -> pd.Series:
        path = self._path(symbol, timeframe)
        if not path.exists():
            raise MarketDataError(f"{symbol} {timeframe.key}: saknar {path.name}")
        frame = pd.read_csv(path, parse_dates=["timestamp"])
        series = frame.set_index("timestamp")["close"].dropna()
        if series.empty:
            raise MarketDataError(f"{symbol} {timeframe.key}: tom fil {path.name}")
        return series


def record_snapshot(
    provider: Provider,
    symbols: list[str],
    timeframes: tuple[Timeframe, ...],
    directory: str | Path,
) -> list[Path]:
    """Persist a provider's series as CSVs a `CsvProvider` can replay later.

    Run this where the data source is reachable; replay it anywhere.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for symbol in symbols:
        for timeframe in timeframes:
            try:
                series = provider.close_series(symbol, timeframe)
            except MarketDataError:
                continue
            path = directory / f"{_slug(symbol)}__{timeframe.key}.csv"
            series.rename("close").rename_axis("timestamp").to_frame().to_csv(path)
            written.append(path)

    return written


# --------------------------------------------------------------------------
# Synthetic
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """A shape to generate, not a forecast.

    The path is built once at the finest granularity and then thinned for the
    longer timeframes, so the timeframes stay consistent with each other the
    way real ones do — a late `final_drift` leg shows up on 15m long before it
    can bend the daily.
    """

    base_drift: float
    final_drift: float
    final_bars: int
    vol: float = 0.0016


SCENARIOS: dict[str, Scenario] = {
    "aligned_up": Scenario(base_drift=0.00016, final_drift=0.00016, final_bars=0),
    "aligned_down": Scenario(base_drift=-0.00016, final_drift=-0.00016, final_bars=0),
    # The late leg is deliberately shorter than the 1h lookback window (20 bars
    # of 4, so 80 base bars). It therefore dominates 15m while the older move
    # still dominates 1h and 1d — the divergence these scenarios exist to show.
    "rebound": Scenario(base_drift=-0.00120, final_drift=0.00200, final_bars=22),
    "pullback": Scenario(base_drift=0.00120, final_drift=-0.00200, final_bars=22),
    "choppy": Scenario(base_drift=0.0, final_drift=0.0, final_bars=0, vol=0.0026),
}

# How many base bars make up one bar of each timeframe.
_THINNING = {"15m": 1, "1h": 4, "1d": 26}


class SyntheticProvider:
    """Deterministic generated prices. For tests and demos only."""

    name = "synthetic"

    def __init__(
        self,
        assignments: dict[str, str] | None = None,
        default_scenario: str = "choppy",
        base_bars: int = 1600,
        seed: int = 20260826,
    ) -> None:
        self.assignments = assignments or {}
        self.default_scenario = default_scenario
        self.base_bars = base_bars
        self.seed = seed

    def _base_path(self, symbol: str) -> pd.Series:
        name = self.assignments.get(symbol, self.default_scenario)
        scenario = SCENARIOS[name]

        # Seed from the symbol so a symbol's path is stable across runs.
        # crc32, not hash(): string hashing is salted per process, which would
        # make "deterministic" output differ between runs.
        rng = np.random.default_rng(self.seed + zlib.crc32(symbol.encode()))

        drifts = np.full(self.base_bars, scenario.base_drift)
        if scenario.final_bars:
            drifts[-scenario.final_bars :] = scenario.final_drift

        shocks = rng.normal(0.0, scenario.vol, self.base_bars)
        path = 100.0 * np.exp(np.cumsum(drifts + shocks))

        index = pd.date_range(
            end=pd.Timestamp("2026-08-26 12:00"),
            periods=self.base_bars,
            freq="15min",
        )
        return pd.Series(path, index=index, name="close")

    def close_series(self, symbol: str, timeframe: Timeframe) -> pd.Series:
        step = _THINNING.get(timeframe.key)
        if step is None:
            raise MarketDataError(
                f"{timeframe.key}: syntetisk data saknar upplösning för intervallet"
            )
        base = self._base_path(symbol)
        thinned = base.iloc[::-1].iloc[::step].iloc[::-1]
        return thinned.tail(120)


def build_provider(kind: str, csv_dir: str | Path | None = None) -> Provider:
    if kind == "yfinance":
        return YFinanceProvider()
    if kind == "csv":
        if csv_dir is None:
            raise ValueError("csv-providern kräver en katalog")
        return CsvProvider(csv_dir)
    if kind == "synthetic":
        return SyntheticProvider(
            assignments={
                "^OMX": "aligned_up",
                "^GSPC": "aligned_up",
                "^IXIC": "pullback",
                "^TNX": "aligned_down",
                "BZ=F": "aligned_down",
                "SEK=X": "rebound",
            }
        )
    raise ValueError(f"Okänd provider: {kind}")
