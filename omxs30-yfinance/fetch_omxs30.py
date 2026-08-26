#!/usr/bin/env python3
"""Hämtar historisk kursdata för OMXS30 från Yahoo Finance via yfinance."""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

TICKER = "^OMXS30"
DEFAULT_PERIOD = "1mo"
DEFAULT_INTERVAL = "15m"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"


def fetch_data(ticker: str = TICKER, period: str = DEFAULT_PERIOD, interval: str = DEFAULT_INTERVAL):
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"Ingen data hämtades för {ticker} (period={period}, interval={interval})")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "Datetime"
    return df


def save_data(df, interval: str = DEFAULT_INTERVAL, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_path = output_dir / f"omxs30_{interval}_{timestamp}.csv"
    df.to_csv(timestamped_path)
    df.to_csv(output_dir / f"omxs30_{interval}_latest.csv")
    return timestamped_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hämta OMXS30-kursdata från Yahoo Finance via yfinance."
    )
    parser.add_argument("--ticker", default=TICKER, help="Yahoo Finance-ticker (default: ^OMXS30)")
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="Tidsperiod, t.ex. 1mo, 5d (default: 1mo)")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL, help="Intervall, t.ex. 15m, 1h, 1d (default: 15m)")
    args = parser.parse_args()

    df = fetch_data(args.ticker, args.period, args.interval)
    path = save_data(df, args.interval)
    print(f"Sparade {len(df)} rader ({args.interval}-data, {args.period}) till {path}")


if __name__ == "__main__":
    main()
