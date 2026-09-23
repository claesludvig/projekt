#!/usr/bin/env python3
"""Marknadspulsen: hämtar index, räntor, valutor och råvaror från Yahoo Finance
(yfinance), räknar förändring över 1d/2d/3d/1v/2v/1m, korrelation mellan
utvalda tillgångspar och ritar ett linjediagram per par över senaste månaden.

Allt som går in i mejlet räknas här — rutinen som skriver texten läser bara
data/marknadspuls.json och hittar aldrig på egna siffror."""

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GRAF_DIR = DATA_DIR / "grafer"
REPO_RAW_URL = "https://raw.githubusercontent.com/claesludvig/projekt"
GRAF_BEHALL_DAGAR = 30

# (grupp, namn, ticker-kandidater i prioritetsordning, enhet)
# enhet: "pct" = procentuell förändring, "bp" = räntepunkter, "pts" = indexpunkter (VIX)
INSTRUMENT = [
    ("Aktier", "OMXS30", ["^OMX", "^OMXS30"], "pct"),
    ("Aktier", "DAX", ["^GDAXI"], "pct"),
    ("Aktier", "Stoxx 50", ["^STOXX50E"], "pct"),
    ("Aktier", "S&P 500", ["^GSPC"], "pct"),
    ("Aktier", "Nasdaq 100", ["^NDX"], "pct"),
    ("Aktier", "VIX", ["^VIX"], "pts"),
    ("Räntor", "US 3M", ["^IRX"], "bp"),
    ("Räntor", "US 2Y", ["2YY=F"], "bp"),
    ("Räntor", "US 10Y", ["^TNX"], "bp"),
    ("Räntor", "US 30Y", ["^TYX"], "bp"),
    ("Valutor", "EUR/USD", ["EURUSD=X"], "pct"),
    ("Valutor", "USD/SEK", ["SEK=X", "USDSEK=X"], "pct"),
    ("Valutor", "EUR/SEK", ["EURSEK=X"], "pct"),
    ("Valutor", "EUR/NOK", ["EURNOK=X"], "pct"),
    ("Råvaror", "Brent", ["BZ=F"], "pct"),
    ("Råvaror", "Guld", ["GC=F"], "pct"),
    ("Råvaror", "Koppar", ["HG=F"], "pct"),
]

# Handelsdagar bakåt för de korta perioderna, kalenderdagar för de längre —
# kalenderdagar gör 1v/2v/1m jämförbara mellan marknader med olika helgdagar.
PERIODER = [
    ("1d", "handelsdagar", 1),
    ("2d", "handelsdagar", 2),
    ("3d", "handelsdagar", 3),
    ("1v", "kalenderdagar", 7),
    ("2v", "kalenderdagar", 14),
    ("1m", "kalenderdagar", 30),
]

PAR = [
    ("OMXS30", "Brent"),
    ("OMXS30", "US 10Y"),
    ("EUR/USD", "US 10Y"),
    ("USD/SEK", "OMXS30"),
]
KORR_FONSTER = {"1m": 30, "3m": 91}
MIN_OBS_KORR = 10
GRAF_DAGAR = 30


def _download(ticker: str) -> pd.Series:
    import yfinance as yf

    idag = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    raw = yf.download(
        ticker,
        start=(idag - pd.Timedelta(days=190)).strftime("%Y-%m-%d"),
        end=(idag + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    close = raw["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    close.index = pd.to_datetime(close.index.date)
    close = close[~close.index.duplicated(keep="last")].astype(float)

    # Yahoos dagsserie för index saknar ofta gårdagens stängning på morgonen
    # (svensk tid) fast timdatan har den. Fyll på avslutade dagar med sista
    # timstapelns stängning — i praktiken samma som dagsstängningen.
    try:
        tim = yf.Ticker(ticker).history(period="5d", interval="1h", auto_adjust=False)["Close"].dropna()
        if len(tim):
            dagar = pd.to_datetime(tim.index.tz_localize(None).date if tim.index.tz is None else tim.index.date)
            per_dag = pd.Series(tim.values, index=dagar).groupby(level=0).last()
            nya = per_dag[(per_dag.index > close.index[-1]) & (per_dag.index < idag)] if len(close) else per_dag
            if len(nya):
                print(f"  {ticker}: kompletterade {', '.join(str(d.date()) for d in nya.index)} från timdata")
                close = pd.concat([close, nya.astype(float)])
    except Exception as exc:  # noqa: BLE001
        print(f"  {ticker}: timdata misslyckades ({exc})")
    return close


def _omxs30_fran_market_db() -> pd.Series:
    """Nödutgång om Yahoo inte ger daglig OMXS30-historik: sista 1h-noteringen
    per dag ur market.db, som fetch_omxs30.yml fyller på varje vardag."""
    import sqlite3

    db_path = BASE_DIR.parent / "omxs30-yfinance" / "data" / "market.db"
    if not db_path.exists():
        return pd.Series(dtype=float)
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT datetime, close FROM omxs30_intraday WHERE interval = '1h' ORDER BY datetime", conn
        )
    if df.empty:
        return pd.Series(dtype=float)
    ts = pd.to_datetime(df["datetime"], utc=True)
    s = pd.Series(df["close"].values, index=pd.to_datetime(ts.dt.date)).dropna()
    return s.groupby(level=0).last().astype(float)


def hamta_alla(t_o_m: date) -> tuple[dict, dict, list]:
    """Returnerar (serier per namn, använd ticker per namn, fel-lista). Rader
    efter t_o_m kapas, så att dagens ofullständiga stapel (FX och terminer
    handlas när rutinen kör på morgonen) inte blandas med gårdagens
    stängningskurser för aktier."""
    serier, tickers, fel = {}, {}, []
    for _grupp, namn, kandidater, _enhet in INSTRUMENT:
        s, anvand = pd.Series(dtype=float), None
        for ticker in kandidater:
            try:
                s = _download(ticker)
            except Exception as exc:  # noqa: BLE001 — ett instrument får aldrig fälla hela körningen
                print(f"  {namn} ({ticker}): fel {exc}")
                s = pd.Series(dtype=float)
            s = s[s.index <= pd.Timestamp(t_o_m)]
            if len(s) >= 25:
                anvand = ticker
                break
            print(f"  {namn} ({ticker}): bara {len(s)} rader, provar nästa kandidat")
        if anvand is None and namn == "OMXS30":
            s = _omxs30_fran_market_db()
            s = s[s.index <= pd.Timestamp(t_o_m)]
            if len(s) >= 25:
                anvand = "market.db (1h → dag)"
        if anvand is None:
            fel.append(f"{namn}: ingen användbar data från {', '.join(kandidater)}")
            continue
        serier[namn], tickers[namn] = s, anvand
        print(f"  {namn} ({anvand}): {len(s)} rader, senast {s.index[-1].date()} = {s.iloc[-1]:.4f}")
    return serier, tickers, fel


def forandring(nu: float, da: float, enhet: str) -> float:
    if enhet == "pct":
        return (nu / da - 1) * 100
    if enhet == "bp":
        # Yahoo kvoterar räntor i procent (4,64) — äldre ^TNX-data i tiondelar (46,4).
        return (nu - da) * (100 if max(abs(nu), abs(da)) < 25 else 10)
    return nu - da


def varde_pa_eller_fore(s: pd.Series, dag: pd.Timestamp):
    fore = s[s.index <= dag]
    return (fore.index[-1], fore.iloc[-1]) if len(fore) else (None, None)


def berakna_tabell(serier: dict, tickers: dict) -> list:
    grupper: dict = {}
    for grupp, namn, _k, enhet in INSTRUMENT:
        if namn not in serier:
            continue
        s = serier[namn]
        senast_dag, senast = s.index[-1], s.iloc[-1]
        rad = {
            "namn": namn,
            "ticker": tickers[namn],
            "enhet": enhet,
            "datum": senast_dag.date().isoformat(),
            "senast": round(float(senast), 4),
            "forandring": {},
        }
        for kod, typ, n in PERIODER:
            if typ == "handelsdagar":
                ref = s.iloc[-1 - n] if len(s) > n else None
            else:
                _d, ref = varde_pa_eller_fore(s, senast_dag - pd.Timedelta(days=n))
            rad["forandring"][kod] = None if ref is None else round(float(forandring(senast, ref, enhet)), 2)
        grupper.setdefault(grupp, []).append(rad)
    return [{"grupp": g, "rader": r} for g, r in grupper.items()]


def _dagliga_forandringar(s: pd.Series, enhet: str) -> pd.Series:
    if enhet == "bp":
        return s.diff() * (100 if s.abs().max() < 25 else 10)
    return s.pct_change() * 100


def _enhet(namn: str) -> str:
    return next(e for _g, n, _k, e in INSTRUMENT if n == namn)


def korrelation(serier: dict, a: str, b: str, dagar: int):
    slut = min(serier[a].index[-1], serier[b].index[-1])
    start = slut - pd.Timedelta(days=dagar)
    ra = _dagliga_forandringar(serier[a], _enhet(a))
    rb = _dagliga_forandringar(serier[b], _enhet(b))
    df = pd.concat([ra, rb], axis=1, keys=[a, b]).dropna()
    df = df[(df.index > start) & (df.index <= slut)]
    if len(df) < MIN_OBS_KORR:
        return None, len(df)
    return round(float(df[a].corr(df[b])), 2), len(df)


FARG_A, FARG_B = "#1a365d", "#c05621"


def rita_par(serier: dict, a: str, b: str, path: Path) -> None:
    slut = max(serier[a].index[-1], serier[b].index[-1])
    start = slut - pd.Timedelta(days=GRAF_DAGAR)
    sa = serier[a][serier[a].index >= start]
    sb = serier[b][serier[b].index >= start]

    fig, ax = plt.subplots(figsize=(5.6, 3), dpi=110, layout="constrained")
    ax.plot(sa.index, sa / sa.iloc[0] * 100, color=FARG_A, linewidth=2, label=f"{a} (index 100)")
    ax.axhline(100, color="#a0aec0", linewidth=0.8)
    ax.set_ylabel("Index, start = 100", fontsize=9, color="#4a5568")

    handles, labels = ax.get_legend_handles_labels()
    if _enhet(b) == "bp":
        # En ränta går inte att indexera meningsfullt — visa nivån på högeraxeln.
        ax2 = ax.twinx()
        ax2.plot(sb.index, sb, color=FARG_B, linewidth=2, label=f"{b} (%, höger axel)")
        ax2.tick_params(labelsize=9, colors="#4a5568")
        for side in ("top",):
            ax2.spines[side].set_visible(False)
        h2, l2 = ax2.get_legend_handles_labels()
        handles, labels = handles + h2, labels + l2
    else:
        ax.plot(sb.index, sb / sb.iloc[0] * 100, color=FARG_B, linewidth=2, label=f"{b} (index 100)")
        handles, labels = ax.get_legend_handles_labels()

    ax.legend(handles, labels, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9, frameon=False,
              borderaxespad=0.2)
    ax.tick_params(labelsize=9, colors="#4a5568")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.grid(alpha=0.25)
    for side in ("top", "right") if _enhet(b) != "bp" else ("top",):
        ax.spines[side].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


def _slug(namn: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in namn).strip("_").replace("__", "_")


def rensa_gamla_grafer(idag: date) -> None:
    if not GRAF_DIR.exists():
        return
    for katalog in GRAF_DIR.iterdir():
        try:
            dag = date.fromisoformat(katalog.name)
        except ValueError:
            continue
        if (idag - dag).days > GRAF_BEHALL_DAGAR:
            for f in katalog.iterdir():
                f.unlink()
            katalog.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description="Marknadspulsen: tabeller, korrelationer och grafer.")
    parser.add_argument("--inkludera-idag", action="store_true", help="Behåll dagens (ofullständiga) stapel.")
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "main"))
    args = parser.parse_args()

    idag = datetime.now(timezone.utc).date()
    t_o_m = idag if args.inkludera_idag else idag - pd.Timedelta(days=1)
    t_o_m = pd.Timestamp(t_o_m).date()
    print(f"Hämtar data t.o.m. {t_o_m}")
    serier, tickers, fel = hamta_alla(t_o_m)

    tabell = berakna_tabell(serier, tickers)

    graf_katalog = GRAF_DIR / idag.isoformat()
    graf_katalog.mkdir(parents=True, exist_ok=True)
    par_ut = []
    for a, b in PAR:
        if a not in serier or b not in serier:
            fel.append(f"Paret {a}–{b} hoppades över: data saknas")
            continue
        fil = graf_katalog / f"{_slug(a)}_mot_{_slug(b)}.png"
        rita_par(serier, a, b, fil)
        korr = {}
        for kod, dagar in KORR_FONSTER.items():
            varde, n = korrelation(serier, a, b, dagar)
            korr[kod] = {"varde": varde, "obs": n}
        rel = fil.relative_to(BASE_DIR.parent).as_posix()
        par_ut.append(
            {
                "a": a,
                "b": b,
                "korrelation": korr,
                "graf": rel,
                "graf_url": f"{REPO_RAW_URL}/{args.branch}/{rel}",
            }
        )
    rensa_gamla_grafer(idag)

    ut = {
        "genererad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_t_o_m": t_o_m.isoformat(),
        "perioder": [p[0] for p in PERIODER],
        "periodforklaring": "1d–3d = handelsdagar bakåt, 1v/2v/1m = senaste stängning 7/14/30 kalenderdagar bakåt. "
        "Räntor i baspunkter, VIX i punkter, övrigt i procent.",
        "korrelationsforklaring": "Pearson på dagliga förändringar (inte nivåer). Amerikanska och europeiska "
        "stängningar sker vid olika tidpunkter, vilket dämpar dagliga korrelationer något.",
        "tabell": tabell,
        "par": par_ut,
        "fel": fel,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "marknadspuls.json").write_text(json.dumps(ut, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skrev {DATA_DIR / 'marknadspuls.json'} ({sum(len(g['rader']) for g in tabell)} instrument, {len(par_ut)} par)")
    if fel:
        print("Problem:\n  " + "\n  ".join(fel))
    if not serier:
        raise SystemExit("Ingen data alls hämtades — avbryter.")


if __name__ == "__main__":
    main()
