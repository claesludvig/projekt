#!/usr/bin/env python3
"""Delad SQLite-lagring för OMXS30-intradagsdata och dagliga priser
(Brent-olja, US10Y-ränta). Byggd för inkrementella körningar: varje
körning hämtar bara nya observationer sedan senast och skriver in dem
här, istället för att hämta om hela historiken från yfinance varje gång.
Det gör körningarna snabbare och låter historiken växa längre bak i
tiden än Yahoos eget retention-fönster för intradagsdata (~60 dagar för
15m, ~730 dagar för 1h) annars skulle tillåta."""

from pathlib import Path
import sqlite3

import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "data" / "market.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS omxs30_intraday (
    interval TEXT NOT NULL,
    datetime TEXT NOT NULL,
    close REAL,
    high REAL,
    low REAL,
    open REAL,
    volume REAL,
    PRIMARY KEY (interval, datetime)
);

CREATE TABLE IF NOT EXISTS daily_prices (
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL,
    PRIMARY KEY (ticker, date)
);
"""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _clean(value):
    return float(value) if pd.notna(value) else None


def latest_intraday_datetime(conn: sqlite3.Connection, interval: str):
    row = conn.execute(
        "SELECT MAX(datetime) FROM omxs30_intraday WHERE interval = ?", (interval,)
    ).fetchone()
    return row[0]


def upsert_intraday(conn: sqlite3.Connection, interval: str, df: pd.DataFrame) -> int:
    """df förväntas vara indexerad på Datetime (tz-aware UTC) med kolumnerna
    Close/High/Low/Open/Volume."""
    rows = [
        (
            interval,
            ts.isoformat(),
            _clean(row.get("Close")),
            _clean(row.get("High")),
            _clean(row.get("Low")),
            _clean(row.get("Open")),
            _clean(row.get("Volume")),
        )
        for ts, row in df.iterrows()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO omxs30_intraday "
        "(interval, datetime, close, high, low, open, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def read_intraday(conn: sqlite3.Connection, interval: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT datetime, close, high, low, open, volume FROM omxs30_intraday "
        "WHERE interval = ? ORDER BY datetime",
        conn,
        params=(interval,),
    )
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.set_index("datetime")
    df.index.name = "Datetime"
    df.columns = ["Close", "High", "Low", "Open", "Volume"]
    return df


def latest_daily_date(conn: sqlite3.Connection, ticker: str):
    row = conn.execute("SELECT MAX(date) FROM daily_prices WHERE ticker = ?", (ticker,)).fetchone()
    return row[0]


def upsert_daily(conn: sqlite3.Connection, ticker: str, series: pd.Series) -> int:
    """series förväntas vara indexerad på datum, värde = close."""
    rows = [
        (ticker, pd.Timestamp(d).date().isoformat(), _clean(v))
        for d, v in series.items()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices (ticker, date, close) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def read_daily(conn: sqlite3.Connection, ticker: str) -> pd.Series:
    df = pd.read_sql_query(
        "SELECT date, close FROM daily_prices WHERE ticker = ? ORDER BY date",
        conn,
        params=(ticker,),
    )
    return pd.Series(df["close"].values, index=pd.to_datetime(df["date"]), name=ticker)
