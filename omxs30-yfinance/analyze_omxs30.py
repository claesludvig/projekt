#!/usr/bin/env python3
"""Räknar ut MA20/MA50 för OMXS30 på flera tidsintervall och plottar dem i samma graf."""

import argparse
import re
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.patches as mpatches
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


def add_trend_strength(df):
    """Normaliserat mått (%) på hur mycket kort trend (MA20) avviker från lång
    trend (MA50), oberoende av prisnivå. Positivt = uppåttrend, negativt =
    nedåttrend. En korsning av nollinjen är en trendvändning, och gör
    momentum jämförbart rakt av mellan olika tidsintervall (som annars ligger
    på samma prisaxel och är svåra att jämföra rättvist)."""
    df["TrendStrength"] = (df["MA20"] - df["MA50"]) / df["MA50"] * 100
    return df


def fetch_and_prepare(ticker: str, period: str, interval: str):
    df = fetch_data(ticker=ticker, period=period, interval=interval)
    df = smooth_close(df, interval)
    df = add_moving_averages(df)
    df = add_trend_strength(df)
    save_data(df, interval=interval)
    return df


MIN_DIVERGENCE_DURATION = pd.Timedelta(hours=2)


def find_divergence_spans(dfs: dict, fast_interval: str, slow_interval: str):
    """Perioder där trendriktningen skiljer sig mellan det snabba och det
    långsamma intervallet (t.ex. uppåttrend på 15m men nedåttrend på 1h,
    eller tvärtom) — en tidig varningssignal om att den kortsiktiga trenden
    kan vara på väg att vända med den större trenden."""
    fast = dfs[fast_interval]["TrendStrength"]
    slow = dfs[slow_interval]["TrendStrength"].reindex(fast.index).ffill()
    disagree = (np.sign(fast) != np.sign(slow)) & fast.notna() & slow.notna()

    spans = []
    start = None
    for ts, flag in disagree.items():
        if flag and start is None:
            start = ts
        elif not flag and start is not None:
            spans.append((start, ts))
            start = None
    if start is not None:
        spans.append((start, disagree.index[-1]))

    return [(s, e) for s, e in spans if (e - s) >= MIN_DIVERGENCE_DURATION]


def plot_multi_interval(dfs: dict, output_path: Path, ticker: str):
    fig, (ax_price, ax_trend) = plt.subplots(
        2,
        1,
        figsize=(14, 9),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.08},
        layout="constrained",
    )

    for interval, df in dfs.items():
        ax_price.plot(
            df.index,
            df["CloseSmooth"],
            label=f"Close ({interval})",
            color="grey",
            alpha=0.25,
            linewidth=1,
        )
        for window in MA_WINDOWS:
            ax_price.plot(
                df.index,
                df[f"MA{window}"],
                label=f"MA{window} ({interval})",
                color=LINE_STYLES[(interval, window)],
                linewidth=1.6,
            )

    ax_price.set_title(f"{ticker} – MA20/MA50 och trendstyrka på {' och '.join(dfs.keys())}-intervall")
    ax_price.set_ylabel("Index")
    ax_price.legend(loc="best", fontsize=8)
    ax_price.grid(alpha=0.2)

    trend_colors = {interval: LINE_STYLES.get((interval, 20), "#333333") for interval in dfs}
    for interval, df in dfs.items():
        ax_trend.plot(
            df.index,
            df["TrendStrength"],
            label=f"Trendstyrka ({interval}): MA20 vs MA50",
            color=trend_colors[interval],
            linewidth=1.4,
        )

    ax_trend.axhline(0, color="black", linewidth=0.8, alpha=0.6)
    ax_trend.set_ylabel("MA20 vs MA50 (%)")
    ax_trend.set_xlabel("Datum")
    ax_trend.grid(alpha=0.2)

    intervals = list(dfs.keys())
    if len(intervals) == 2:
        fast, slow = sorted(intervals, key=lambda i: pd.Timedelta(_interval_to_pandas_freq(i)))
        spans = find_divergence_spans(dfs, fast, slow)
        for start, end in spans:
            ax_price.axvspan(start, end, color="red", alpha=0.08)
            ax_trend.axvspan(start, end, color="red", alpha=0.12)
        if spans:
            divergence_patch = mpatches.Patch(
                color="red", alpha=0.12, label=f"Divergens: {fast} och {slow} är oense om trendriktning"
            )
            handles, labels = ax_trend.get_legend_handles_labels()
            ax_trend.legend(handles + [divergence_patch], labels + [divergence_patch.get_label()], loc="best", fontsize=8)
        else:
            ax_trend.legend(loc="best", fontsize=8)
    else:
        ax_trend.legend(loc="best", fontsize=8)

    ax_price.tick_params(labelbottom=False)
    plt.setp(ax_trend.get_xticklabels(), rotation=30, ha="right")
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
