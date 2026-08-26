"""Assembles the market section of the morning brief."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .charts import render_dashboard
from .config import DEFAULT_TIMEFRAMES, DEFAULT_WATCHLIST, Instrument, Timeframe
from .providers import MarketDataError, Provider
from .trend import InstrumentTrend, TrendConfig, analyse_instrument


@dataclass
class Report:
    generated_at: datetime
    provider: str
    timeframes: tuple[Timeframe, ...]
    trends: list[InstrumentTrend]
    series: dict[str, dict[str, pd.Series]]
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def timeframe_keys(self) -> list[str]:
        return [tf.key for tf in self.timeframes]

    @property
    def timeframe_labels(self) -> dict[str, str]:
        return {tf.key: tf.label for tf in self.timeframes}


def build_report(
    provider: Provider,
    instruments: tuple[Instrument, ...] = DEFAULT_WATCHLIST,
    timeframes: tuple[Timeframe, ...] = DEFAULT_TIMEFRAMES,
    cfg: TrendConfig | None = None,
) -> Report:
    """Fetch every instrument on every timeframe and classify what came back.

    A symbol that fails on one timeframe is still reported on the others; a
    symbol that fails everywhere is recorded in `errors` rather than dropped
    silently.
    """
    cfg = cfg or TrendConfig()
    trends: list[InstrumentTrend] = []
    series_by_symbol: dict[str, dict[str, pd.Series]] = {}
    errors: dict[str, str] = {}

    for instrument in instruments:
        collected: dict[str, tuple[str, pd.Series]] = {}
        raw: dict[str, pd.Series] = {}
        failures: list[str] = []

        for timeframe in timeframes:
            try:
                series = provider.close_series(instrument.symbol, timeframe)
            except MarketDataError as exc:
                failures.append(f"{timeframe.key}: {exc}")
                continue
            collected[timeframe.key] = (timeframe.label, series)
            raw[timeframe.key] = series

        if not collected:
            errors[instrument.symbol] = "; ".join(failures) or "ingen data"
            continue

        trends.append(
            analyse_instrument(
                symbol=instrument.symbol,
                label=instrument.label,
                series_by_timeframe=collected,
                cfg=cfg,
            )
        )
        series_by_symbol[instrument.symbol] = raw

    return Report(
        generated_at=datetime.now(timezone.utc),
        provider=provider.name,
        timeframes=timeframes,
        trends=trends,
        series=series_by_symbol,
        errors=errors,
    )


def report_to_dict(report: Report) -> dict:
    """Plain structure for templating an email or JSON payload."""
    return {
        "generated_at": report.generated_at.isoformat(),
        "provider": report.provider,
        "timeframes": [
            {"key": tf.key, "label": tf.label} for tf in report.timeframes
        ],
        "instruments": [
            {
                "symbol": trend.symbol,
                "label": trend.label,
                "last_price": trend.last_price,
                "alignment": trend.alignment.value,
                "alignment_label": trend.alignment.label,
                "alignment_note": trend.alignment.note,
                "unavailable": list(trend.unavailable),
                "timeframes": {
                    key: {
                        "direction": tf.direction.value,
                        "direction_label": tf.direction.label,
                        "pct_change": round(tf.pct_change, 3),
                        "z_score": round(tf.z_score, 2),
                        "strength": tf.strength,
                        "confirmations": tf.confirmations,
                        "last_price": tf.last_price,
                        "votes": tf.votes,
                    }
                    for key, tf in trend.timeframes.items()
                },
            }
            for trend in report.trends
        ],
        "errors": report.errors,
    }


def render_report_chart(
    report: Report,
    path: str | Path,
    focus_symbol: str | None = None,
    theme: str = "light",
) -> Path | None:
    """Render the dashboard PNG. Returns None when there is nothing to draw."""
    if not report.trends:
        return None

    focus = report.trends[0]
    if focus_symbol:
        focus = next(
            (t for t in report.trends if t.symbol == focus_symbol), report.trends[0]
        )

    stamp = report.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    subtitle = f"{stamp} · källa: {report.provider}"
    if report.provider == "synthetic":
        subtitle += " · SYNTETISK DATA, EJ MARKNADSKURSER"

    return render_dashboard(
        trends=report.trends,
        tf_keys=report.timeframe_keys,
        tf_labels=report.timeframe_labels,
        focus=focus,
        focus_series=report.series.get(focus.symbol, {}),
        path=path,
        theme=theme,
        subtitle=subtitle,
    )


def format_text_summary(report: Report) -> str:
    """The plain-text block that goes into the email body."""
    lines: list[str] = []
    width = max((len(t.label) for t in report.trends), default=10)

    for trend in report.trends:
        cells = []
        for key in report.timeframe_keys:
            tf = trend.timeframes.get(key)
            cells.append(f"{key} {tf.direction.arrow} {tf.bars_summary}" if tf
                         else f"{key} –")
        lines.append(
            f"{trend.label.ljust(width)}  {'  |  '.join(cells)}   → {trend.alignment.label}"
        )

    if report.errors:
        lines.append("")
        for symbol, reason in report.errors.items():
            lines.append(f"({symbol} kunde inte hämtas: {reason})")

    return "\n".join(lines)
