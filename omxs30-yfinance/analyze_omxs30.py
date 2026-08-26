#!/usr/bin/env python3
"""Räknar ut MA20/MA50 för OMXS30 på flera tidsintervall och plottar dem i samma graf."""

import argparse
import re
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fetch_omxs30 import DEFAULT_PERIOD, TICKER, fetch_data, save_data

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
INTERVALS = ("15m", "1h")
MA_WINDOWS = (20, 50)

# Färg per (intervall, MA-fönster) så linjerna går att skilja åt i samma graf.
LINE_STYLES = {
    ("15m", 20): "#1f77b4",
    ("15m", 50): "#ff7f0e",
    ("1h", 20): "#2ca02c",
    ("1h", 50): "#d62728",
}


def _interval_to_pandas_freq(interval: str) -> str:
    """Yahoo Finance-intervall (t.ex. '15m', '1h', '1d') -> pandas frekvenssträng."""
    match = re.fullmatch(r"(\d*)(m|h|d|wk|mo)", interval)
    if not match:
        raise ValueError(f"Okänt intervall: {interval}")
    amount, unit = match.groups()
    amount = amount or "1"
    unit_map = {"m": "min", "h": "h", "d": "D", "wk": "W", "mo": "MS"}
    return f"{amount}{unit_map[unit]}"


def smooth_close(df, interval: str):
    """OMXS30 har hos Yahoo Finance bara noteringar under en liten del av
    handelsdagen (för det här intervallet runt kl 09:30-11:30 amerikansk tid)
    och saknar data helt resten av dygnet och på helger. Räknar man MA radvis
    på rådatan blandas då flera dagar ihop i samma fönster, vilket gör att
    kurvan ligger still inom varje dag och hoppar en gång per dag i stället
    för att röra sig mjukt. Vi bygger därför ett sammanhängande tidsraster i
    intervallets upplösning och interpolerar linjärt över luckorna, så att
    MA-beräkningen får en kontinuerlig kurva att jobba med."""
    freq = _interval_to_pandas_freq(interval)
    full_index = pd.date_range(df.index.min(), df.index.max(), freq=freq)
    df = df.reindex(df.index.union(full_index)).sort_index()
    df["CloseSmooth"] = df["Close"].interpolate(method="time")
    return df


def add_moving_averages(df, windows=MA_WINDOWS):
    for window in windows:
        df[f"MA{window}"] = df["CloseSmooth"].rolling(window=window).mean()
    return df


def fetch_and_prepare(ticker: str, period: str, interval: str):
    df = fetch_data(ticker=ticker, period=period, interval=interval)
    df = smooth_close(df, interval)
    df = add_moving_averages(df)
    save_data(df, interval=interval)
    return df


def plot_multi_interval(dfs: dict, output_path: Path, ticker: str):
    fig, ax = plt.subplots(figsize=(14, 7))

    for interval, df in dfs.items():
        ax.plot(
            df.index,
            df["CloseSmooth"],
            label=f"Close ({interval})",
            color="grey",
            alpha=0.25,
            linewidth=1,
        )
        for window in MA_WINDOWS:
            ax.plot(
                df.index,
                df[f"MA{window}"],
                label=f"MA{window} ({interval})",
                color=LINE_STYLES[(interval, window)],
                linewidth=1.6,
            )

    ax.set_title(f"{ticker} – MA20/MA50 på {' och '.join(dfs.keys())}-intervall")
    ax.set_xlabel("Datum")
    ax.set_ylabel("Index")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hämta OMXS30 på flera intervall, räkna MA20/MA50 och plotta i samma graf."
    )
    parser.add_argument("--ticker", default=TICKER)
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="Tidsperiod, t.ex. 1mo (default: 1mo)")
    parser.add_argument(
        "--intervals",
        nargs="+",
        default=list(INTERVALS),
        help="Vilka intervall som ska hämtas och plottas (default: 15m 1h)",
    )
    args = parser.parse_args()

    dfs = {}
    for interval in args.intervals:
        dfs[interval] = fetch_and_prepare(args.ticker, args.period, interval)

    output_path = OUTPUT_DIR / "omxs30_ma_multi_interval.png"
    plot_multi_interval(dfs, output_path, args.ticker)
    print(f"Sparade graf till {output_path}")


if __name__ == "__main__":
    main()
