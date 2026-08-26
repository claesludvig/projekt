"""Command line entry point.

    python3 -m market.cli --provider yfinance --out out/market.png
    python3 -m market.cli --provider synthetic --json
    python3 -m market.cli --record snapshots/     # save data for offline replay
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .brief import (
    build_report,
    format_text_summary,
    render_report_chart,
    report_to_dict,
)
from .config import DEFAULT_WATCHLIST, Instrument, timeframes_by_key
from .providers import build_provider, record_snapshot
from .trend import TrendConfig


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="market",
        description="Trendläge per tidsintervall för en bevakningslista.",
    )
    parser.add_argument("--provider", default="yfinance",
                        choices=["yfinance", "csv", "synthetic"])
    parser.add_argument("--csv-dir", default="snapshots",
                        help="Katalog för csv-providern och --record.")
    parser.add_argument("--symbols", nargs="*",
                        help="Yahoo-symboler. Utan flaggan används standardlistan.")
    parser.add_argument("--timeframes", nargs="*",
                        help="T.ex. 15m 1h 1d. Standard: alla tre.")
    parser.add_argument("--focus", help="Symbol som får prispanelerna.")
    parser.add_argument("--out", default="out/market.png", help="Sökväg för PNG.")
    parser.add_argument("--theme", default="light", choices=["light", "dark"])
    parser.add_argument("--json", action="store_true", help="Skriv rapporten som JSON.")
    parser.add_argument("--no-chart", action="store_true")
    parser.add_argument("--record", metavar="DIR",
                        help="Spara hämtade serier som CSV och avsluta.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    timeframes = timeframes_by_key(tuple(args.timeframes) if args.timeframes else None)

    if args.symbols:
        instruments = tuple(Instrument(s, s) for s in args.symbols)
    else:
        instruments = DEFAULT_WATCHLIST

    provider = build_provider(args.provider, args.csv_dir)

    if args.record:
        written = record_snapshot(
            provider, [i.symbol for i in instruments], timeframes, args.record
        )
        for path in written:
            print(f"skrev {path}")
        if not written:
            print("inget kunde hämtas", file=sys.stderr)
            return 1
        return 0

    report = build_report(provider, instruments, timeframes, TrendConfig())

    if not report.trends:
        print("Ingen data kunde hämtas.", file=sys.stderr)
        for symbol, reason in report.errors.items():
            print(f"  {symbol}: {reason}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))
    else:
        print(format_text_summary(report))

    if not args.no_chart:
        path = render_report_chart(report, Path(args.out), args.focus, args.theme)
        if path:
            print(f"\nGraf: {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
