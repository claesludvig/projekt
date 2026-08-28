#!/usr/bin/env python3
"""Hämtar OMXS30-intradagsdata från Yahoo Finance via yfinance, inkrementellt
in i den delade SQLite-databasen (market.db) istället för att hämta om hela
historiken varje körning. Första körningen (tom databas) gör en full backfill
upp till Yahoos retention-gräns för respektive intervall; varje körning
därefter hämtar bara en liten buffert sedan senaste lagrade observationen."""

import argparse

import pandas as pd
import yfinance as yf

import db

TICKER = "^OMXS30"
DEFAULT_INTERVAL = "15m"

# Yahoos ungefärliga maxhistorik (dagar) per intervall - styr hur långt
# tillbaka en första backfill hämtar när databasen är tom.
MAX_BACKFILL_DAYS = {"15m": 60, "1h": 730}
DEFAULT_MAX_BACKFILL_DAYS = 60
INCREMENTAL_BUFFER_DAYS = 5


def fetch_raw(ticker: str, interval: str, start: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, interval=interval, auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError(f"Ingen data hämtades för {ticker} (start={start}, interval={interval})")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "Datetime"
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    return df


def fetch_incremental(conn, ticker: str = TICKER, interval: str = DEFAULT_INTERVAL) -> int:
    """Hämtar bara nya observationer sedan senast lagrade datapunkt och
    upsertar in dem i databasen. Returnerar antal hämtade rader i svaret
    från Yahoo (inte antal faktiskt nya, eftersom bufferten avsiktligt
    överlappar redan lagrad data för att inte missa några luckor)."""
    max_days = MAX_BACKFILL_DAYS.get(interval, DEFAULT_MAX_BACKFILL_DAYS)
    latest = db.latest_intraday_datetime(conn, interval)
    if latest is None:
        window_days = max_days
    else:
        last_ts = pd.Timestamp(latest)
        gap_days = max((pd.Timestamp.now(tz="UTC") - last_ts).days + 2, INCREMENTAL_BUFFER_DAYS)
        window_days = min(gap_days, max_days)

    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")
    raw = fetch_raw(ticker, interval, start)
    return db.upsert_intraday(conn, interval, raw)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hämta OMXS30-intradagsdata inkrementellt till market.db."
    )
    parser.add_argument("--ticker", default=TICKER, help="Yahoo Finance-ticker (default: ^OMXS30)")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL, help="Intervall, t.ex. 15m, 1h (default: 15m)")
    args = parser.parse_args()

    conn = db.connect()
    fetched = fetch_incremental(conn, args.ticker, args.interval)
    total = len(db.read_intraday(conn, args.interval))
    print(f"Hämtade {fetched} rader ({args.interval}) från Yahoo. Databasen har nu {total} rader totalt för intervallet.")


if __name__ == "__main__":
    main()
