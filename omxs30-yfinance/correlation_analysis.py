#!/usr/bin/env python3
"""Undersöker korrelationen mellan OMXS30, oljepris (Brent) och amerikansk
10-årsränta: rör de sig verkligen ihop, eller bara i det senaste narrativet?"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

TICKERS = {
    "OMXS30": "^OMXS30",
    "Brent-olja": "BZ=F",
    "US10Y-ränta": "^TNX",
}
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_PERIOD = "6mo"
ROLLING_WINDOW = 20


def fetch_daily(ticker: str, period: str) -> pd.Series:
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"Ingen data hämtades för {ticker}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.name = ticker
    # Olika tickers kan komma tillbaka med olika tidszons-/tidsstämpelformat
    # (t.ex. ^OMXS30 tz-aware, BZ=F/^TNX inte), vilket gör att en concat på
    # de råa DatetimeIndex-objekten missar nästan alla dagar. Normalisera
    # till rent kalenderdatum så serierna går att slå ihop dag för dag.
    close.index = pd.to_datetime(close.index.date)
    return close


def build_dataset(period: str) -> pd.DataFrame:
    series = {label: fetch_daily(ticker, period) for label, ticker in TICKERS.items()}
    df = pd.concat(series.values(), axis=1, keys=series.keys())
    return df.dropna(how="any")


def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    returns = pd.DataFrame(index=df.index)
    returns["OMXS30"] = df["OMXS30"].pct_change() * 100
    returns["Brent-olja"] = df["Brent-olja"].pct_change() * 100
    # ^TNX kvoteras i tiondels procentenheter (46.4 = 4,64%). Vi använder
    # den faktiska förändringen i räntepunkter, inte procentuell förändring
    # av räntenivån (som är missvisande nära noll och byter tecken godtyckligt).
    returns["US10Y-ränta (bp)"] = df["US10Y-ränta"].diff() * 10
    return returns.dropna()


def rolling_correlation(returns: pd.DataFrame, window: int = ROLLING_WINDOW) -> pd.DataFrame:
    corr = pd.DataFrame(index=returns.index)
    corr["OMXS30 vs olja"] = returns["OMXS30"].rolling(window).corr(returns["Brent-olja"])
    corr["OMXS30 vs ränta"] = returns["OMXS30"].rolling(window).corr(returns["US10Y-ränta (bp)"])
    return corr.dropna()


def plot(df: pd.DataFrame, corr: pd.DataFrame, output_path: Path, period: str) -> None:
    fig, (ax_price, ax_corr) = plt.subplots(
        2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.3}, layout="constrained"
    )

    normalized = df / df.iloc[0] * 100
    colors = {"OMXS30": "#1f77b4", "Brent-olja": "#d62728", "US10Y-ränta": "#2ca02c"}
    for col in normalized.columns:
        ax_price.plot(normalized.index, normalized[col], label=col, color=colors.get(col), linewidth=1.6)
    ax_price.axhline(100, color="black", linewidth=0.6, alpha=0.4)
    ax_price.set_title(f"OMXS30 vs Brent-olja vs amerikansk 10-årsränta — indexerat till 100 ({period})")
    ax_price.set_ylabel("Index (start = 100)")
    ax_price.legend(loc="best")
    ax_price.grid(alpha=0.2)

    ax_corr.plot(corr.index, corr["OMXS30 vs olja"], label="OMXS30 vs olja", color="#d62728", linewidth=1.6)
    ax_corr.plot(corr.index, corr["OMXS30 vs ränta"], label="OMXS30 vs ränta", color="#2ca02c", linewidth=1.6)
    ax_corr.axhline(0, color="black", linewidth=0.8, alpha=0.6)
    ax_corr.set_ylim(-1, 1)
    ax_corr.set_ylabel(f"Rullande {ROLLING_WINDOW}-dagars korrelation")
    ax_corr.set_title("Hur korrelationen förändras över tid")
    ax_corr.legend(loc="best")
    ax_corr.grid(alpha=0.2)

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Korrelation mellan OMXS30, oljepris och amerikansk 10-årsränta."
    )
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="Tidsperiod, t.ex. 6mo, 1y (default: 6mo)")
    args = parser.parse_args()

    df = build_dataset(args.period)
    returns = compute_returns(df)
    corr = rolling_correlation(returns)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "correlation_prices.csv")
    returns.to_csv(OUTPUT_DIR / "correlation_returns.csv")
    corr.to_csv(OUTPUT_DIR / "correlation_rolling.csv")

    full_corr = returns.corr()
    print("Korrelationsmatris (hela perioden, dagliga förändringar):")
    print(full_corr.round(3).to_string())

    output_path = OUTPUT_DIR / "correlation_chart.png"
    plot(df, corr, output_path, args.period)
    print(f"\nSparade graf till {output_path}")


if __name__ == "__main__":
    main()
