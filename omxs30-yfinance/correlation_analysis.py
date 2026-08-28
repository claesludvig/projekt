#!/usr/bin/env python3
"""Undersöker korrelationen mellan OMXS30, oljepris (Brent) och amerikansk
10-årsränta: rör de sig verkligen ihop, eller bara i det senaste narrativet?

Priserna hämtas inkrementellt och lagras i den delade SQLite-databasen
(market.db) istället för att hämtas om i sin helhet varje körning; OMXS30-
delen delar rakt av 1h-tabellen med fetch_omxs30.py/analyze_omxs30.py."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

import db
from fetch_omxs30 import TICKER as OMXS30_TICKER, fetch_incremental

DAILY_TICKERS = {
    "Brent-olja": "BZ=F",
    "US10Y-ränta": "^TNX",
}
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
ROLLING_WINDOW = 10
INCREMENTAL_BUFFER_DAYS = 5
BACKFILL_DAYS_DAILY = 730


def fetch_daily_incremental(conn, label: str, ticker: str) -> None:
    latest = db.latest_daily_date(conn, label)
    if latest is None:
        window_days = BACKFILL_DAYS_DAILY
    else:
        gap_days = max((pd.Timestamp.now().normalize() - pd.Timestamp(latest)).days + 2, INCREMENTAL_BUFFER_DAYS)
        window_days = gap_days

    start = (pd.Timestamp.now().normalize() - pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")
    raw = yf.download(ticker, start=start, interval="1d", auto_adjust=False, progress=False)
    if raw.empty:
        raise RuntimeError(f"Ingen data hämtades för {ticker}")
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    # Normalisera till rent kalenderdatum så serierna går att slå ihop dag för dag.
    close.index = pd.to_datetime(close.index.date)
    db.upsert_daily(conn, label, close)


def omxs30_daily_proxy(conn) -> pd.Series:
    """^OMXS30 saknar i praktiken historik via yfinance vid interval="1d" på
    den här datakällan (en riktig körning gav bara dagens rad, oavsett
    period) — samma typ av begränsning som vi ser för intradagsdata i
    övriga omxs30-yfinance-projektet. Härleder istället en daglig proxy från
    den 1h-data som redan ackumuleras i market.db: sista noteringen per
    kalenderdag."""
    fetch_incremental(conn, OMXS30_TICKER, "1h")
    intraday = db.read_intraday(conn, "1h")
    daily_index = pd.to_datetime(intraday.index.date)
    close = pd.Series(intraday["Close"].values, index=daily_index)
    daily = close.groupby(daily_index).last().dropna()
    daily.name = "OMXS30"
    return daily


def build_dataset(conn) -> pd.DataFrame:
    for label, ticker in DAILY_TICKERS.items():
        fetch_daily_incremental(conn, label, ticker)

    series = {"OMXS30": omxs30_daily_proxy(conn)}
    series.update({label: db.read_daily(conn, label) for label in DAILY_TICKERS})
    for label, s in series.items():
        print(f"  {label}: {len(s)} rader, {s.index.min()} -> {s.index.max()}")
    dframe = pd.concat(series.values(), axis=1, keys=series.keys())
    merged = dframe.dropna(how="any")
    print(f"  Efter sammanslagning (gemensamma datum): {len(merged)} rader")
    return merged


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


def plot(df: pd.DataFrame, corr: pd.DataFrame, output_path: Path, period_label: str) -> None:
    fig, (ax_price, ax_corr) = plt.subplots(
        2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.3}, layout="constrained"
    )

    normalized = df / df.iloc[0] * 100
    colors = {"OMXS30": "#1f77b4", "Brent-olja": "#d62728", "US10Y-ränta": "#2ca02c"}
    for col in normalized.columns:
        ax_price.plot(normalized.index, normalized[col], label=col, color=colors.get(col), linewidth=1.6)
    ax_price.axhline(100, color="black", linewidth=0.6, alpha=0.4)
    ax_price.set_title(f"OMXS30 vs Brent-olja vs amerikansk 10-årsränta — indexerat till 100 ({period_label})")
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
        description="Korrelation mellan OMXS30, oljepris och amerikansk 10-årsränta (inkrementell, market.db)."
    )
    parser.parse_args()

    conn = db.connect()
    df = build_dataset(conn)
    returns = compute_returns(df)
    corr = rolling_correlation(returns)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "correlation_prices.csv")
    returns.to_csv(OUTPUT_DIR / "correlation_returns.csv")
    corr.to_csv(OUTPUT_DIR / "correlation_rolling.csv")

    full_corr = returns.corr()
    print("Korrelationsmatris (hela lagrad historik, dagliga förändringar):")
    print(full_corr.round(3).to_string())

    output_path = OUTPUT_DIR / "correlation_chart.png"
    plot(df, corr, output_path, f"{len(df)} dagar, lagrad historik")
    print(f"\nSparade graf till {output_path}")


if __name__ == "__main__":
    main()
