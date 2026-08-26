"""Multi-timeframe trend classification.

The question this answers: is the short timeframe pointing the same way as the
longer ones? A 15-minute rally inside a falling 1-hour trend is a rebound, not
a turn, and the two deserve different words.

Each timeframe is classified on its own by three independent votes, then the
per-timeframe directions are compared to produce an alignment verdict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"

    @property
    def label(self) -> str:
        return {"up": "Upp", "down": "Ner", "flat": "Neutral"}[self.value]

    @property
    def arrow(self) -> str:
        return {"up": "▲", "down": "▼", "flat": "→"}[self.value]


class Alignment(str, Enum):
    ALIGNED_UP = "aligned_up"
    ALIGNED_DOWN = "aligned_down"
    REBOUND = "rebound"
    PULLBACK = "pullback"
    MIXED = "mixed"
    FLAT = "flat"

    @property
    def label(self) -> str:
        return {
            "aligned_up": "Samstämmig upp",
            "aligned_down": "Samstämmig ner",
            "rebound": "Rekyl upp i nedtrend",
            "pullback": "Rekyl ner i upptrend",
            "mixed": "Blandad bild",
            "flat": "Riktningslöst",
        }[self.value]

    @property
    def note(self) -> str:
        return {
            "aligned_up": "Alla tidsintervall pekar åt samma håll uppåt.",
            "aligned_down": "Alla tidsintervall pekar åt samma håll nedåt.",
            "rebound": "Kort sikt vänder upp men den längre trenden är fortsatt ner.",
            "pullback": "Kort sikt viker ner men den längre trenden är fortsatt upp.",
            "mixed": "Tidsintervallen säger emot varandra utan tydligt mönster.",
            "flat": "Ingen av tidsintervallen har en tydlig riktning.",
        }[self.value]


class InsufficientData(ValueError):
    """Raised when a series is too short to classify honestly."""


@dataclass(frozen=True)
class TrendConfig:
    lookback_bars: int = 20
    ema_fast: int = 9
    ema_slow: int = 21
    slope_bars: int = 5
    # A move must clear this many standard deviations of its own timeframe's
    # noise before any direction is called. Lower values call more turns and
    # more noise with them.
    z_threshold: float = 1.3
    flat_eps: float = 0.0002  # relative; keeps EMA votes from flapping on noise
    # Floor under the noise estimate. A series with (near) zero measured
    # variance would otherwise divide a real move by nothing and report an
    # arbitrarily large z. Expressed as a fraction of price.
    noise_floor: float = 0.0005
    # z-score cuts for the reported strength, from the gate upwards.
    strength_cuts: tuple[float, float] = (2.0, 3.0)

    @property
    def required_bars(self) -> int:
        return max(self.lookback_bars + 1, self.ema_slow + self.slope_bars)


@dataclass(frozen=True)
class TimeframeTrend:
    key: str
    label: str
    direction: Direction
    pct_change: float  # over lookback_bars, in percent
    z_score: float  # move size relative to this timeframe's own noise
    strength: int  # 0-3, graded by how far past the gate the move is
    confirmations: int  # how many of the two EMA readings backed the gate
    last_price: float
    votes: dict[str, int]

    @property
    def bars_summary(self) -> str:
        sign = "+" if self.pct_change >= 0 else "−"
        return f"{sign}{abs(self.pct_change):.2f} %"


@dataclass(frozen=True)
class InstrumentTrend:
    symbol: str
    label: str
    timeframes: dict[str, TimeframeTrend]
    unavailable: tuple[str, ...]
    alignment: Alignment

    @property
    def last_price(self) -> float | None:
        """Price from the shortest available timeframe — the freshest print."""
        for tf in self.timeframes.values():
            return tf.last_price
        return None


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _sign(value: float, eps: float) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def classify_timeframe(
    closes: pd.Series,
    key: str,
    label: str,
    cfg: TrendConfig | None = None,
) -> TimeframeTrend:
    """Classify one timeframe's direction from a series of closing prices.

    `momentum` is the gate, not a vote: the move over the lookback window,
    divided by what this timeframe's own noise would produce over the same
    span. Scaling matters — 0.2 % in 15 minutes is a real move, the same
    0.2 % on a daily bar is nothing. Below `z_threshold` the answer is flat
    regardless of what anything else says.

    The two EMA readings only confirm or veto:

    * `ema_cross` — fast EMA above or below the slow EMA.
    * `ema_slope` — which way the slow EMA has travelled recently.

    They are deliberately kept subordinate because they are near-duplicates of
    each other; as equal votes the pair would routinely outvote the only
    volatility-aware signal and call a direction on drift that is within noise.
    Both must disagree with the gate to veto it.
    """
    cfg = cfg or TrendConfig()
    closes = closes.dropna().astype(float)

    if len(closes) < cfg.required_bars:
        raise InsufficientData(
            f"{key}: {len(closes)} staplar, behöver {cfg.required_bars}"
        )

    last = float(closes.iloc[-1])
    prior = float(closes.iloc[-(cfg.lookback_bars + 1)])
    pct = (last / prior - 1.0) if prior else 0.0

    returns = closes.pct_change().dropna()
    sigma = float(returns.std())
    # Expected size of a lookback-length move if it were pure noise.
    noise = max(sigma * math.sqrt(cfg.lookback_bars), cfg.noise_floor)
    z = pct / noise

    ema_fast = _ema(closes, cfg.ema_fast)
    ema_slow = _ema(closes, cfg.ema_slow)

    cross_rel = (float(ema_fast.iloc[-1]) - float(ema_slow.iloc[-1])) / last if last else 0.0
    slow_now = float(ema_slow.iloc[-1])
    slow_then = float(ema_slow.iloc[-(cfg.slope_bars + 1)])
    slope_rel = (slow_now - slow_then) / last if last else 0.0

    momentum = _sign(z, cfg.z_threshold)
    ema_cross = _sign(cross_rel, cfg.flat_eps)
    ema_slope = _sign(slope_rel, cfg.flat_eps)
    votes = {"momentum": momentum, "ema_cross": ema_cross, "ema_slope": ema_slope}

    confirmations = sum(1 for v in (ema_cross, ema_slope) if v == momentum)
    vetoed = momentum != 0 and all(v == -momentum for v in (ema_cross, ema_slope))

    if momentum == 0 or vetoed:
        direction = Direction.FLAT
        strength = 0
    else:
        direction = Direction.UP if momentum > 0 else Direction.DOWN
        # Graded by how far past the gate the move is, not by how many
        # indicators agreed: the two EMA readings almost always agree with the
        # gate once it opens, so counting them would report a constant.
        mild, strong = cfg.strength_cuts
        magnitude = abs(z)
        strength = 3 if magnitude >= strong else 2 if magnitude >= mild else 1

    return TimeframeTrend(
        key=key,
        label=label,
        direction=direction,
        pct_change=pct * 100.0,
        z_score=z,
        strength=strength,
        confirmations=confirmations,
        last_price=last,
        votes=votes,
    )


def resolve_alignment(directions: list[Direction]) -> Alignment:
    """Compare per-timeframe directions, given shortest-first.

    Only non-flat timeframes carry a vote; a flat middle rung does not break an
    otherwise consistent picture.
    """
    active = [d for d in directions if d is not Direction.FLAT]
    if not active:
        return Alignment.FLAT
    if all(d is Direction.UP for d in active):
        return Alignment.ALIGNED_UP
    if all(d is Direction.DOWN for d in active):
        return Alignment.ALIGNED_DOWN

    shortest, longest = active[0], active[-1]
    if shortest is Direction.UP and longest is Direction.DOWN:
        return Alignment.REBOUND
    if shortest is Direction.DOWN and longest is Direction.UP:
        return Alignment.PULLBACK
    return Alignment.MIXED


def analyse_instrument(
    symbol: str,
    label: str,
    series_by_timeframe: dict[str, tuple[str, pd.Series]],
    cfg: TrendConfig | None = None,
) -> InstrumentTrend:
    """Classify every timeframe for one instrument and resolve the alignment.

    `series_by_timeframe` maps a timeframe key to its (label, closes) pair and
    must already be ordered shortest first.
    """
    cfg = cfg or TrendConfig()
    trends: dict[str, TimeframeTrend] = {}
    unavailable: list[str] = []

    for key, (tf_label, closes) in series_by_timeframe.items():
        try:
            trends[key] = classify_timeframe(closes, key, tf_label, cfg)
        except InsufficientData:
            unavailable.append(key)

    alignment = resolve_alignment([t.direction for t in trends.values()])

    return InstrumentTrend(
        symbol=symbol,
        label=label,
        timeframes=trends,
        unavailable=tuple(unavailable),
        alignment=alignment,
    )
