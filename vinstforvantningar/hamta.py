#!/usr/bin/env python3
"""Vinstförväntningar för OMXS30-bolagen: hämtar analytikerkonsensus (EPS i år
och nästa år) från Yahoo Finance via yfinance, räknar hur prognoserna har
reviderats över 1v/1m/3m per bolag och sammanvägt för indexet, och ritar två
grafer: sammanvägd vinstprognos mot OMXS30-kursen senaste 90 dagarna, och
senaste månadens revidering per bolag.

Allt som går in i mejlet räknas här — rutinen som skriver texten läser bara
data/vinst.json och hittar aldrig på egna siffror."""

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
GRAF_BEHALL_DAGAR = 120
OMXS30_TICKER = "^OMX"

# Yahoos eps_trend: prognos i dag och 7/30/60/90 dagar sedan.
TREND_KOLUMNER = {"nu": "current", 7: "7daysAgo", 30: "30daysAgo", 60: "60daysAgo", 90: "90daysAgo"}
PERIODER = [("1v", 7), ("1m", 30), ("3m", 90)]
HORISONTER = ["0y", "+1y"]  # innevarande och nästa räkenskapsår
KOMMANDE_DAGAR = 21


def _procent(nu, da):
    """Revidering i %. None när jämförelsen inte är meningsfull: saknad
    prognos, byte av tecken eller en vinst nära noll (förlustbolag)."""
    if nu is None or da is None or pd.isna(nu) or pd.isna(da):
        return None
    if da <= 0 or nu <= 0:
        return None
    return (nu / da - 1) * 100


def _float(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(v) else v


def hamta_bolag(ticker: str) -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)
    trend = t.eps_trend
    if trend is None or trend.empty:
        raise RuntimeError("eps_trend saknas")
    ut = {"eps": {}, "revideringar": {}, "analytiker": {}}
    for h in HORISONTER:
        if h not in trend.index:
            continue
        rad = trend.loc[h]
        ut["eps"][h] = {k: _float(rad.get(kol)) for k, kol in TREND_KOLUMNER.items()}

    try:
        rev = t.eps_revisions
        if rev is not None and not rev.empty:
            for h in HORISONTER:
                if h in rev.index:
                    r = rev.loc[h]
                    ut["revideringar"][h] = {
                        "upp_30d": _float(r.get("upLast30days")),
                        "ner_30d": _float(r.get("downLast30days")),
                        "upp_7d": _float(r.get("upLast7days")),
                        "ner_7d": _float(r.get("downLast7Days", r.get("downLast7days"))),
                    }
    except Exception as exc:  # noqa: BLE001
        print(f"  {ticker}: eps_revisions saknas ({exc})")

    try:
        est = t.earnings_estimate
        if est is not None and not est.empty:
            for h in HORISONTER:
                if h in est.index:
                    ut["analytiker"][h] = _float(est.loc[h].get("numberOfAnalysts"))
    except Exception as exc:  # noqa: BLE001
        print(f"  {ticker}: earnings_estimate saknas ({exc})")

    ut["borsvarde"] = None
    try:
        ut["borsvarde"] = _float(t.fast_info["marketCap"])
    except Exception as exc:  # noqa: BLE001
        print(f"  {ticker}: börsvärde saknas ({exc})")

    ut["nasta_rapport"] = None
    try:
        cal = t.calendar or {}
        datum = cal.get("Earnings Date") or []
        if datum:
            ut["nasta_rapport"] = pd.Timestamp(datum[0]).date().isoformat()
    except Exception as exc:  # noqa: BLE001
        print(f"  {ticker}: rapportdatum saknas ({exc})")
    return ut


def bolagsrad(namn: str, ticker: str, d: dict) -> dict:
    rad = {"namn": namn, "ticker": ticker, "borsvarde": d["borsvarde"], "nasta_rapport": d["nasta_rapport"]}
    for h in HORISONTER:
        eps = d["eps"].get(h, {})
        rad[h] = {
            "eps": eps.get("nu"),
            "revidering": {kod: _procent(eps.get("nu"), eps.get(dagar)) for kod, dagar in PERIODER},
            "analytiker": d["analytiker"].get(h),
            **d["revideringar"].get(h, {}),
        }
    e0, e1 = rad["0y"]["eps"], rad["+1y"]["eps"]
    rad["tillvaxt_nasta_ar"] = _procent(e1, e0)
    return rad


def viktat(rader: list, varde) -> tuple:
    """Börsvärdesviktat medel över bolag där värdet finns. Returnerar (medel, antal)."""
    par = [(r["borsvarde"], varde(r)) for r in rader if r["borsvarde"] and varde(r) is not None]
    if not par:
        return None, 0
    vikt = sum(w for w, _ in par)
    return sum(w * v for w, v in par) / vikt, len(par)


def eps_index(rader_rå: dict, rader: list, h: str) -> pd.Series:
    """Sammanvägd vinstprognos, index 100 för 90 dagar sedan, i de fem
    punkter Yahoo ger (−90, −60, −30, −7, 0 dagar). Bara bolag med positiv
    prognos i samtliga punkter räknas, så att urvalet är detsamma hela vägen."""
    idag = pd.Timestamp(datetime.now(timezone.utc).date())
    punkter = [90, 60, 30, 7, "nu"]
    varden = {p: [] for p in punkter}
    vikter = []
    for r in rader:
        eps = rader_rå[r["ticker"]]["eps"].get(h, {})
        serie = [eps.get(p) for p in punkter]
        if not r["borsvarde"] or any(v is None or v <= 0 for v in serie):
            continue
        vikter.append(r["borsvarde"])
        for p, v in zip(punkter, serie):
            varden[p].append(v / serie[0] * 100)
    if not vikter:
        return pd.Series(dtype=float)
    tot = sum(vikter)
    idx = [idag - pd.Timedelta(days=0 if p == "nu" else p) for p in punkter]
    return pd.Series([sum(w * v for w, v in zip(vikter, varden[p])) / tot for p in punkter], index=idx)


def omxs30_kurs(dagar: int = 95) -> pd.Series:
    import yfinance as yf

    idag = pd.Timestamp(datetime.now(timezone.utc).date())
    raw = yf.download(
        OMXS30_TICKER,
        start=(idag - pd.Timedelta(days=dagar)).strftime("%Y-%m-%d"),
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
    return close[close.index < idag].astype(float)


FARG_KURS, FARG_0Y, FARG_1Y = "#718096", "#1a365d", "#c05621"
C_UPP, C_NER = "#276749", "#c53030"


def rita_vinst_mot_kurs(kurs: pd.Series, eps0: pd.Series, eps1: pd.Series, ar0: str, ar1: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.6, 3.1), dpi=110, layout="constrained")
    if len(kurs):
        start = eps1.index[0] if len(eps1) else kurs.index[0]
        k = kurs[kurs.index >= start]
        if len(k):
            ax.plot(k.index, k / k.iloc[0] * 100, color=FARG_KURS, linewidth=1.6, label="OMXS30-kursen")
    for serie, farg, etikett in ((eps0, FARG_0Y, f"Vinstprognos {ar0}"), (eps1, FARG_1Y, f"Vinstprognos {ar1}")):
        if len(serie):
            ax.plot(serie.index, serie.values, color=farg, linewidth=2.2, marker="o", markersize=4, label=etikett)
    ax.axhline(100, color="#a0aec0", linewidth=0.8)
    ax.set_ylabel("Index, 90 dagar sedan = 100", fontsize=9, color="#4a5568")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9, frameon=False, borderaxespad=0.2)
    ax.tick_params(labelsize=9, colors="#4a5568")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.grid(alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


def rita_revideringar(rader: list, h: str, period: str, ar: str, path: Path) -> None:
    med = [(r["namn"], r[h]["revidering"][period]) for r in rader if r[h]["revidering"][period] is not None]
    med.sort(key=lambda x: x[1])
    if not med:
        return
    fig, ax = plt.subplots(figsize=(5.6, 0.2 * len(med) + 0.8), dpi=110, layout="constrained")
    namn = [m[0] for m in med]
    varden = [m[1] for m in med]
    ax.barh(namn, varden, color=[C_UPP if v > 0 else C_NER for v in varden], height=0.65)
    ax.axvline(0, color="#4a5568", linewidth=0.8)
    ax.set_xlabel(f"Ändrad vinstprognos {ar}, senaste månaden (%)", fontsize=9, color="#4a5568")
    ax.tick_params(labelsize=9, colors="#4a5568")
    ax.grid(axis="x", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


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


def spara_historik(idag: date, rader: list) -> None:
    """Veckovis ögonblicksbild per bolag, så att längre serier än Yahoos 90
    dagar kan byggas framöver."""
    path = DATA_DIR / "historik.csv"
    nya = pd.DataFrame(
        [
            {"datum": idag.isoformat(), "ticker": r["ticker"], "eps_0y": r["0y"]["eps"], "eps_1y": r["+1y"]["eps"],
             "borsvarde": r["borsvarde"]}
            for r in rader
        ]
    )
    if path.exists():
        gammal = pd.read_csv(path)
        gammal = gammal[gammal["datum"] != idag.isoformat()]
        nya = pd.concat([gammal, nya], ignore_index=True)
    nya.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vinstförväntningar för OMXS30-bolagen.")
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "main"))
    args = parser.parse_args()

    idag = datetime.now(timezone.utc).date()
    bolag = json.loads((BASE_DIR / "bolag.json").read_text(encoding="utf-8"))["bolag"]

    rå, rader, fel = {}, [], []
    for b in bolag:
        try:
            d = hamta_bolag(b["ticker"])
        except Exception as exc:  # noqa: BLE001 — ett bolag får aldrig fälla hela körningen
            fel.append(f"{b['namn']} ({b['ticker']}): {exc}")
            print(f"  {b['namn']}: FEL {exc}")
            continue
        rå[b["ticker"]] = d
        rad = bolagsrad(b["namn"], b["ticker"], d)
        rader.append(rad)
        print(f"  {b['namn']}: EPS 0y {rad['0y']['eps']}, +1y {rad['+1y']['eps']}, "
              f"rev +1y 1m {rad['+1y']['revidering']['1m']}, börsvärde {rad['borsvarde']}")

    if not rader:
        raise SystemExit("Inga prognoser alls hämtades — avbryter.")

    ar0, ar1 = str(idag.year), str(idag.year + 1)
    index = {"revidering": {}, "antal_bolag": {}}
    for h in HORISONTER:
        index["revidering"][h] = {}
        for kod, _d in PERIODER:
            v, n = viktat(rader, lambda r, h=h, kod=kod: r[h]["revidering"][kod])
            index["revidering"][h][kod] = None if v is None else round(v, 2)
            index["antal_bolag"][h] = n

    hojda = [r["namn"] for r in rader if (r["+1y"]["revidering"]["1m"] or 0) > 0.05]
    sankta = [r["namn"] for r in rader if (r["+1y"]["revidering"]["1m"] or 0) < -0.05]
    index["bredd_1m"] = {"hojda": len(hojda), "sankta": len(sankta),
                         "oforandrade": len([r for r in rader if r["+1y"]["revidering"]["1m"] is not None]) - len(hojda) - len(sankta)}
    upp = sum(r["+1y"].get("upp_30d") or 0 for r in rader)
    ner = sum(r["+1y"].get("ner_30d") or 0 for r in rader)
    index["analytikerrevideringar_30d"] = {"upp": int(upp), "ner": int(ner)}
    tillv, _n = viktat(rader, lambda r: r["tillvaxt_nasta_ar"])
    index["tillvaxt_nasta_ar"] = None if tillv is None else round(tillv, 1)

    eps0, eps1 = eps_index(rå, rader, "0y"), eps_index(rå, rader, "+1y")
    try:
        kurs = omxs30_kurs()
    except Exception as exc:  # noqa: BLE001
        kurs = pd.Series(dtype=float)
        fel.append(f"OMXS30-kursen: {exc}")
    kurs_3m = None
    if len(kurs) and len(eps1):
        k = kurs[kurs.index >= eps1.index[0]]
        if len(k) > 1:
            kurs_3m = (k.iloc[-1] / k.iloc[0] - 1) * 100
    eps1_3m = None if not len(eps1) else eps1.iloc[-1] - 100
    index["kurs_3m"] = None if kurs_3m is None else round(kurs_3m, 1)
    index["eps_nasta_ar_3m"] = None if eps1_3m is None else round(eps1_3m, 1)
    index["vardering_3m"] = (
        None if kurs_3m is None or eps1_3m is None else round(((1 + kurs_3m / 100) / (1 + eps1_3m / 100) - 1) * 100, 1)
    )

    graf_katalog = GRAF_DIR / idag.isoformat()
    graf_katalog.mkdir(parents=True, exist_ok=True)
    grafer = {}
    for nyckel, fil, rita in (
        ("vinst_mot_kurs", "vinst_mot_kurs.png", lambda p: rita_vinst_mot_kurs(kurs, eps0, eps1, ar0, ar1, p)),
        ("revideringar_1m", "revideringar_1m.png", lambda p: rita_revideringar(rader, "+1y", "1m", ar1, p)),
    ):
        path = graf_katalog / fil
        rita(path)
        if path.exists():
            rel = path.relative_to(BASE_DIR.parent).as_posix()
            grafer[nyckel] = f"{REPO_RAW_URL}/{args.branch}/{rel}"
    rensa_gamla_grafer(idag)

    rader.sort(key=lambda r: (r["+1y"]["revidering"]["1m"] is None, -(r["+1y"]["revidering"]["1m"] or 0)))
    for r in rader:
        for h in HORISONTER:
            r[h]["revidering"] = {k: None if v is None else round(v, 2) for k, v in r[h]["revidering"].items()}
        if r["tillvaxt_nasta_ar"] is not None:
            r["tillvaxt_nasta_ar"] = round(r["tillvaxt_nasta_ar"], 1)

    med_1m = [r for r in rader if r["+1y"]["revidering"]["1m"] is not None]
    kommande = sorted(
        [
            {"namn": r["namn"], "datum": r["nasta_rapport"]}
            for r in rader
            if r["nasta_rapport"] and 0 <= (date.fromisoformat(r["nasta_rapport"]) - idag).days <= KOMMANDE_DAGAR
        ],
        key=lambda x: x["datum"],
    )

    ut = {
        "genererad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datum": idag.isoformat(),
        "vecka": idag.isocalendar().week,
        "ar": {"0y": ar0, "+1y": ar1},
        "perioder": [p[0] for p in PERIODER],
        "index": index,
        "eps_index": {
            h: [{"datum": d.date().isoformat(), "varde": round(v, 2)} for d, v in s.items()]
            for h, s in (("0y", eps0), ("+1y", eps1))
        },
        "storsta_hojningar": [r["namn"] for r in med_1m[:3] if r["+1y"]["revidering"]["1m"] > 0],
        "storsta_sankningar": [r["namn"] for r in reversed(med_1m[-3:]) if r["+1y"]["revidering"]["1m"] < 0],
        "bolag": rader,
        "kommande_rapporter": kommande,
        "grafer": grafer,
        "metod": (
            "Analytikerkonsensus för vinst per aktie (EPS) enligt Yahoo Finance. Revidering = ändring av "
            "konsensusprognosen över perioden, i %. Indexsiffror är viktade med börsvärde. Bolag med förlust "
            "eller byte av tecken i prognosen räknas inte. Investor och Industrivärden ingår inte. "
            f"{ar0} och {ar1} avser innevarande och nästa räkenskapsår."
        ),
        "fel": fel,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "vinst.json").write_text(json.dumps(ut, ensure_ascii=False, indent=2), encoding="utf-8")
    spara_historik(idag, rader)
    print(f"Skrev vinst.json: {len(rader)} bolag, index {json.dumps(index, ensure_ascii=False)}")
    if fel:
        print("Problem:\n  " + "\n  ".join(fel))


if __name__ == "__main__":
    main()
