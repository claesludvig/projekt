#!/usr/bin/env python3
"""Bygg & fastighet: veckobrev om de svenska bygg- och fastighetsbolagen.

Hämtar kurser (Yahoo Finance via yfinance), svenska räntor (Riksbankens
SWEA-API) och analytikernas vinstprognoser för byggbolagen, och räknar:
- förändring 1d/2d/3d/1v/2v/1m per bolag, sektorindex och ränta
- egna börsvärdesviktade sektorindex för bygg respektive fastighet
- samband (korrelation 1m/3m) och räntekänslighet: hur mycket
  fastighetsindex rört sig per 10 bp i 5-årsräntan senaste 3 månaderna
- tre grafer

Allt som går in i mejlet räknas här — rutinen som skriver texten läser bara
data/byggfastighet.json och hittar aldrig på egna siffror."""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))
from marknadspuls.hamta import _download  # noqa: E402  (dagsdata + komplettering med timdata)
from vinstforvantningar.hamta import bolagsrad, hamta_bolag  # noqa: E402

DATA_DIR = BASE_DIR / "data"
GRAF_DIR = DATA_DIR / "grafer"
REPO_RAW_URL = "https://raw.githubusercontent.com/claesludvig/projekt"
GRAF_BEHALL_DAGAR = 120
SWEA = "https://api.riksbank.se/swea/v1"
OMXS30_TICKER = "^OMX"

PERIODER = [
    ("1d", "handelsdagar", 1),
    ("2d", "handelsdagar", 2),
    ("3d", "handelsdagar", 3),
    ("1v", "kalenderdagar", 7),
    ("2v", "kalenderdagar", 14),
    ("1m", "kalenderdagar", 30),
    ("3m", "kalenderdagar", 91),
]

# Svenska räntor. Kandidater i prioritetsordning; den första serie som finns
# och ger data används. Hela Riksbankens serielista loggas till
# data/swea_serier.txt så att valet går att kontrollera.
RANTOR = [
    ("Styrränta", ["SECBREPOEFF"]),
    ("Stat 2Y", ["SEGVB2YC"]),
    ("Stat 5Y", ["SEGVB5YC"]),
    ("Stat 10Y", ["SEGVB10YC"]),
    ("Bostadsobl. 2Y", ["SEMB2YCACOMB"]),
    ("Bostadsobl. 5Y", ["SEMB5YCACOMB"]),
]
REFERENSRANTA = "Stat 5Y"   # räntekänslighet och grafer
KORR_FONSTER = {"1m": 30, "3m": 91}
MIN_OBS = 10


# ---------- hämtning ----------

def hamta_kurser(bolag: list, t_o_m: date) -> tuple[dict, list]:
    serier, fel = {}, []
    for b in bolag + [{"ticker": OMXS30_TICKER, "namn": "OMXS30"}]:
        try:
            s = _download(b["ticker"])
        except Exception as exc:  # noqa: BLE001
            s = pd.Series(dtype=float)
            print(f"  {b['namn']}: fel {exc}")
        if len(s):
            s = s[s.index <= pd.Timestamp(t_o_m)]
        if len(s) < 60:
            fel.append(f"{b['namn']} ({b['ticker']}): bara {len(s)} kursrader")
            continue
        serier[b["ticker"]] = s
        print(f"  {b['namn']}: {len(s)} rader, senast {s.index[-1].date()} = {s.iloc[-1]:.2f}")
    return serier, fel


SWEA_PAUS = 13  # sekunder mellan anrop: SWEA utan API-nyckel tillåter bara ett fåtal anrop per minut


def _swea_get(url: str):
    """GET mot SWEA med paus före varje anrop och ett nytt försök efter en
    minut om kvoten ändå slår till (HTTP 429)."""
    for forsok in range(2):
        time.sleep(SWEA_PAUS)
        r = requests.get(url, timeout=30)
        if r.status_code == 429 and forsok == 0:
            print(f"  SWEA: 429, väntar 60 s ({url.rsplit('/', 3)[-3]})")
            time.sleep(60)
            continue
        r.raise_for_status()
        return r.json()


def swea_serielista() -> list:
    return _swea_get(f"{SWEA}/Series")


def swea_serie(serie_id: str, fran: date, till: date) -> pd.Series:
    obs = _swea_get(f"{SWEA}/Observations/{serie_id}/{fran.isoformat()}/{till.isoformat()}")
    if not obs:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(o["date"]): o["value"] for o in obs if o.get("value") is not None}, dtype=float)
    return s.sort_index()


def hamta_rantor(t_o_m: date) -> tuple[dict, dict, list]:
    serier, anvanda, fel = {}, {}, []
    fran = t_o_m - pd.Timedelta(days=200)
    try:
        lista = swea_serielista()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "swea_serier.txt").write_text(
            "\n".join(f"{s.get('seriesId')}\t{s.get('shortDescription')}\t{s.get('observationMaxDate')}" for s in lista),
            encoding="utf-8",
        )
        finns = {s.get("seriesId") for s in lista}
    except Exception as exc:  # noqa: BLE001
        print(f"  SWEA serielista: fel {exc}")
        finns = None
    for namn, kandidater in RANTOR:
        for sid in kandidater:
            if finns is not None and sid not in finns:
                continue
            try:
                s = swea_serie(sid, fran, t_o_m)
            except Exception as exc:  # noqa: BLE001
                print(f"  {namn} ({sid}): fel {exc}")
                fel.append(f"{namn} ({sid}): {exc}")
                continue
            if len(s) >= 20:
                serier[namn], anvanda[namn] = s, sid
                print(f"  {namn} ({sid}): {len(s)} rader, senast {s.index[-1].date()} = {s.iloc[-1]:.3f}")
                break
        else:
            fel.append(f"{namn}: ingen data från Riksbanken ({', '.join(kandidater)})")
    return serier, anvanda, fel


# ---------- beräkningar ----------

def varde_pa_eller_fore(s: pd.Series, dag: pd.Timestamp):
    fore = s[s.index <= dag]
    return fore.iloc[-1] if len(fore) else None


def forandringar(s: pd.Series, bp: bool) -> dict:
    ut, nu, sista = {}, s.iloc[-1], s.index[-1]
    for kod, typ, n in PERIODER:
        if typ == "handelsdagar":
            ref = s.iloc[-1 - n] if len(s) > n else None
        else:
            ref = varde_pa_eller_fore(s, sista - pd.Timedelta(days=n))
        if ref is None:
            ut[kod] = None
        else:
            ut[kod] = round(float((nu - ref) * 100 if bp else (nu / ref - 1) * 100), 2)
    return ut


def sektorindex(serier: dict, bolag: list, vikter: dict) -> pd.Series:
    """Börsvärdesviktat index (start = 100) av dagliga avkastningar, med
    dagens börsvärden som fasta vikter. Enkelt men tillräckligt för att
    följa sektorns rörelse; det är inte Nasdaqs officiella sektorindex."""
    ret, w = [], []
    for b in bolag:
        t = b["ticker"]
        if t in serier and vikter.get(t):
            ret.append(serier[t].pct_change())
            w.append(vikter[t])
    if not ret:
        return pd.Series(dtype=float)
    df = pd.concat(ret, axis=1)
    wv = pd.Series(w, index=df.columns)
    viktad = df.mul(wv, axis=1).sum(axis=1, min_count=1) / df.notna().mul(wv, axis=1).sum(axis=1)
    viktad = viktad.dropna()
    return (1 + viktad).cumprod() * 100


def _dagliga(s: pd.Series, bp: bool) -> pd.Series:
    return s.diff() * 100 if bp else s.pct_change() * 100


def korrelation(a: pd.Series, b: pd.Series, a_bp: bool, b_bp: bool, dagar: int):
    slut = min(a.index[-1], b.index[-1])
    df = pd.concat([_dagliga(a, a_bp), _dagliga(b, b_bp)], axis=1, keys=["a", "b"]).dropna()
    df = df[(df.index > slut - pd.Timedelta(days=dagar)) & (df.index <= slut)]
    if len(df) < MIN_OBS:
        return None
    return round(float(df["a"].corr(df["b"])), 2)


def rantekanslighet(index: pd.Series, ranta: pd.Series, dagar: int = 91):
    """Regressionslutning: indexets dagliga avkastning (%) per 10 bp ändring
    i räntan, senaste `dagar` dagarna. Negativt = sektorn faller när räntan stiger."""
    df = pd.concat([_dagliga(index, False), _dagliga(ranta, True)], axis=1, keys=["r", "bp"]).dropna()
    df = df[df.index > df.index[-1] - pd.Timedelta(days=dagar)]
    if len(df) < MIN_OBS or df["bp"].var() == 0:
        return None
    beta = df["r"].cov(df["bp"]) / df["bp"].var()
    return round(float(beta * 10), 2)


# ---------- grafer ----------

INDEXNAMN = {"Bygg": "Byggindex", "Fastighet": "Fastighetsindex"}
FARG = {"Fastighet": "#1a365d", "Bygg": "#c05621", "OMXS30": "#718096", "ranta": "#2f855a"}


def _stil(ax):
    ax.tick_params(labelsize=9, colors="#4a5568")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)


def rita_index_mot_ranta(index: pd.Series, namn: str, ranta: pd.Series, rnamn: str, dagar: int, path: Path) -> None:
    slut = index.index[-1]
    i = index[index.index >= slut - pd.Timedelta(days=dagar)]
    r = ranta[(ranta.index >= i.index[0]) & (ranta.index <= slut)]
    fig, ax = plt.subplots(figsize=(5.6, 3.0), dpi=110, layout="constrained")
    ax.plot(i.index, i / i.iloc[0] * 100, color=FARG[namn], linewidth=2, label=f"{INDEXNAMN[namn]} (index 100)")
    ax.axhline(100, color="#a0aec0", linewidth=0.8)
    ax.set_ylabel("Index, start = 100", fontsize=9, color="#4a5568")
    ax2 = ax.twinx()
    ax2.plot(r.index, r, color=FARG["ranta"], linewidth=2, label=f"{rnamn} (%, höger axel, inverterad)")
    ax2.invert_yaxis()  # stigande ränta nedåt, så att linjerna rör sig ihop när sambandet är det väntade
    ax2.tick_params(labelsize=9, colors="#4a5568")
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=1, fontsize=9, frameon=False,
              borderaxespad=0.2)
    _stil(ax)
    ax.spines["right"].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


def rita_relativ(indexar: dict, dagar: int, path: Path) -> None:
    slut = min(s.index[-1] for s in indexar.values())
    fig, ax = plt.subplots(figsize=(5.6, 3.0), dpi=110, layout="constrained")
    for namn, s in indexar.items():
        s = s[(s.index >= slut - pd.Timedelta(days=dagar)) & (s.index <= slut)]
        ax.plot(s.index, s / s.iloc[0] * 100, color=FARG[namn], linewidth=2 if namn != "OMXS30" else 1.6,
                label=namn)
    ax.axhline(100, color="#a0aec0", linewidth=0.8)
    ax.set_ylabel("Index, start = 100", fontsize=9, color="#4a5568")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=9, frameon=False, borderaxespad=0.2)
    _stil(ax)
    ax.spines["right"].set_visible(False)
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


# ---------- huvudprogram ----------

def main() -> None:
    parser = argparse.ArgumentParser(description="Bygg & fastighet: kurser, svenska räntor och vinstprognoser.")
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "main"))
    args = parser.parse_args()

    idag = datetime.now(timezone.utc).date()
    t_o_m = idag - pd.Timedelta(days=1)
    t_o_m = pd.Timestamp(t_o_m).date()
    konfig = json.loads((BASE_DIR / "bolag.json").read_text(encoding="utf-8"))
    grupper = {"Bygg": konfig["bygg"], "Fastighet": konfig["fastighet"]}
    alla = konfig["bygg"] + konfig["fastighet"]

    print("Kurser:")
    kurser, fel = hamta_kurser(alla, t_o_m)
    print("Räntor:")
    rantor, ranteserier, rfel = hamta_rantor(t_o_m)
    fel += rfel

    # Börsvärden (vikter) och vinstprognoser. Prognoser bara för byggbolagen:
    # fastighetsbolagens EPS domineras av orealiserade värdeförändringar och
    # säger lite om den löpande intjäningen (förvaltningsresultatet).
    print("Börsvärden och prognoser:")
    import yfinance as yf

    vikter, prognoser = {}, []
    for b in alla:
        if b["ticker"] not in kurser:
            continue
        if b in konfig["bygg"]:
            try:
                d = hamta_bolag(b["ticker"])
                vikter[b["ticker"]] = d["borsvarde"]
                rad = bolagsrad(b["namn"], b["ticker"], d)
                if rad["+1y"]["eps"] is not None:
                    prognoser.append(rad)
            except Exception as exc:  # noqa: BLE001
                print(f"  {b['namn']}: prognos saknas ({exc})")
        if not vikter.get(b["ticker"]):
            try:
                vikter[b["ticker"]] = float(yf.Ticker(b["ticker"]).fast_info["marketCap"])
            except Exception as exc:  # noqa: BLE001
                print(f"  {b['namn']}: börsvärde saknas ({exc})")

    index = {g: sektorindex(kurser, bolag, vikter) for g, bolag in grupper.items()}
    if OMXS30_TICKER in kurser:
        index["OMXS30"] = kurser[OMXS30_TICKER]

    tabell = []
    idx_rader = []
    for namn in ("Bygg", "Fastighet", "OMXS30"):
        s = index.get(namn)
        if s is None or not len(s):
            continue
        idx_rader.append({"namn": INDEXNAMN.get(namn, namn), "enhet": "pct",
                          "datum": s.index[-1].date().isoformat(), "senast": round(float(s.iloc[-1]), 2),
                          "forandring": forandringar(s, False)})
    tabell.append({"grupp": "Index", "rader": idx_rader})
    for g, bolag in grupper.items():
        rader = []
        for b in bolag:
            s = kurser.get(b["ticker"])
            if s is None:
                continue
            rader.append({"namn": b["namn"], "ticker": b["ticker"], "enhet": "pct",
                          "datum": s.index[-1].date().isoformat(), "senast": round(float(s.iloc[-1]), 2),
                          "borsvarde_mdkr": None if not vikter.get(b["ticker"]) else round(vikter[b["ticker"]] / 1e9, 1),
                          "forandring": forandringar(s, False)})
        rader.sort(key=lambda r: -(r["forandring"]["1m"] if r["forandring"]["1m"] is not None else -1e9))
        tabell.append({"grupp": g, "rader": rader})
    r_rader = [{"namn": n, "serie": ranteserier[n], "enhet": "bp", "datum": s.index[-1].date().isoformat(),
                "senast": round(float(s.iloc[-1]), 3), "forandring": forandringar(s, True)}
               for n, s in rantor.items()]
    if r_rader:
        tabell.append({"grupp": "Räntor", "rader": r_rader})

    # Kontroll: en bostadsobligation som på en enskild dag rör sig mer än
    # 12 bp annorlunda än statsobligationen med samma löptid har troligen
    # bytt referensobligation i Riksbankens serie. Sådana hopp flaggas, och
    # alla räntor sparas i rantor.csv så att det går att granska.
    anmarkningar = []
    if rantor:
        pd.DataFrame(rantor).to_csv(DATA_DIR / "rantor.csv")
    for mb, stat in (("Bostadsobl. 2Y", "Stat 2Y"), ("Bostadsobl. 5Y", "Stat 5Y")):
        if mb in rantor and stat in rantor:
            diff = pd.concat([rantor[mb].diff() * 100, rantor[stat].diff() * 100], axis=1, keys=["mb", "stat"]).dropna()
            diff = diff[diff.index > diff.index[-1] - pd.Timedelta(days=91)]
            hopp = diff[(diff["mb"] - diff["stat"]).abs() > 12]
            for dag, rad in hopp.iterrows():
                anmarkningar.append(
                    f"{mb} {dag.date().isoformat()}: {rad['mb']:+.1f} bp mot {rad['stat']:+.1f} bp för {stat}. "
                    "Troligen byte av referensobligation, inte en marknadsrörelse; förändringar över den dagen är osäkra."
                )
    samband = {}
    ref = rantor.get(REFERENSRANTA)
    for g in ("Fastighet", "Bygg"):
        s = index.get(g)
        if s is None or not len(s) or ref is None:
            continue
        samband[g] = {
            "mot": REFERENSRANTA,
            "korrelation": {k: korrelation(s, ref, False, True, d) for k, d in KORR_FONSTER.items()},
            "per_10bp_3m": rantekanslighet(s, ref),
        }

    graf_katalog = GRAF_DIR / idag.isoformat()
    graf_katalog.mkdir(parents=True, exist_ok=True)
    grafer = {}

    def spara(nyckel, fil, rita):
        path = graf_katalog / fil
        try:
            rita(path)
        except Exception as exc:  # noqa: BLE001
            fel.append(f"Grafen {fil}: {exc}")
            return
        rel = path.relative_to(BASE_DIR.parent).as_posix()
        grafer[nyckel] = f"{REPO_RAW_URL}/{args.branch}/{rel}"

    if ref is not None:
        for g in ("Fastighet", "Bygg"):
            if g in index and len(index[g]):
                spara(f"{g.lower()}_mot_ranta", f"{g.lower()}_mot_ranta.png",
                      lambda p, g=g: rita_index_mot_ranta(index[g], g, ref, REFERENSRANTA, 91, p))
    rel_index = {k: index[k] for k in ("Fastighet", "Bygg", "OMXS30") if k in index and len(index[k])}
    if len(rel_index) >= 2:
        spara("relativ_3m", "relativ_3m.png", lambda p: rita_relativ(rel_index, 91, p))
    rensa_gamla_grafer(idag)

    for r in prognoser:
        for h in ("0y", "+1y"):
            r[h]["revidering"] = {k: None if v is None else round(v, 2) for k, v in r[h]["revidering"].items()}
        if r["tillvaxt_nasta_ar"] is not None:
            r["tillvaxt_nasta_ar"] = round(r["tillvaxt_nasta_ar"], 1)
    prognoser.sort(key=lambda r: -(r["+1y"]["revidering"]["1m"] if r["+1y"]["revidering"]["1m"] is not None else -1e9))
    kommande = sorted(
        [{"namn": r["namn"], "datum": r["nasta_rapport"]} for r in prognoser
         if r["nasta_rapport"] and 0 <= (date.fromisoformat(r["nasta_rapport"]) - idag).days <= 21],
        key=lambda x: x["datum"],
    )

    ut = {
        "genererad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datum": idag.isoformat(),
        "data_t_o_m": t_o_m.isoformat(),
        "vecka": idag.isocalendar().week,
        "ar": {"0y": str(idag.year), "+1y": str(idag.year + 1)},
        "perioder": [p[0] for p in PERIODER],
        "tabell": tabell,
        "samband": samband,
        "prognoser_bygg": prognoser,
        "kommande_rapporter": kommande,
        "grafer": grafer,
        "metod": (
            "Kurser: Yahoo Finance. Räntor: Riksbanken (SWEA; Riksbanken publicerar inte swapräntor, bostadsobligationerna är närmaste mått på finansieringskostnaden). Sektorindexen är egna, börsvärdesviktade med "
            "dagens börsvärden, och inte Nasdaqs officiella index. Räntor i baspunkter, övrigt i procent. "
            "1d–3d = handelsdagar, 1v–3m = kalenderdagar bakåt. Korrelation på dagliga förändringar. "
            f"Räntekänslighet = sektorindexets rörelse i % per 10 bp högre {REFERENSRANTA}, senaste 3 månaderna. "
            "Vinstprognoser (analytikerkonsensus) bara för byggbolagen: fastighetsbolagens vinst per aktie "
            "domineras av värdeförändringar."
        ),
        "anmarkningar": anmarkningar,
        "fel": fel,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "byggfastighet.json").write_text(json.dumps(ut, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skrev byggfastighet.json. Samband: {json.dumps(samband, ensure_ascii=False)}")
    if fel:
        print("Problem:\n  " + "\n  ".join(fel))
    if not kurser:
        raise SystemExit("Inga kurser hämtades — avbryter.")


if __name__ == "__main__":
    main()
