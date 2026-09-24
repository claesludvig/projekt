#!/usr/bin/env python3
"""Byggpulsen: hämtar egna och öppna månadsserier som rör sig före byggandet,
väger ihop dem till ett ledande index (index.py) och testar indexet i
efterhand mot SCB:s påbörjade lägenheter.

Källor:
- Platsannonser inom bygg och anläggning: JobTech (Arbetsförmedlingen),
  historiska annonser per publiceringsmånad. Varje körning sparar dessutom
  dagens antal aktiva annonser i data/annonser_dag.csv, en egen serie som
  inte finns någon annanstans.
- Bygglov och påbörjade lägenheter: SCB (PxWebApi 2), kvartal.
- Statsobligationsränta 5 år: Riksbanken (SWEA).
- Byggbolagens aktier: Yahoo Finance, likaviktat (bolagen i
  byggfastighet/bolag.json).

Bara hela månader används. Allt som går in i en text räknas här och sparas
i data/byggpuls.json."""

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
import numpy as np
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import index as bpi  # noqa: E402

DATA_DIR = BASE_DIR / "data"
GRAF_DIR = DATA_DIR / "grafer"
SERIER_CSV = DATA_DIR / "serier.csv"
MAL_CSV = DATA_DIR / "mal.csv"
DAG_CSV = DATA_DIR / "annonser_dag.csv"
REPO_RAW_URL = "https://raw.githubusercontent.com/claesludvig/projekt"
GRAF_BEHALL_DAGAR = 400

JOBSEARCH = "https://jobsearch.api.jobtechdev.se/search"
HISTORICAL = "https://historical.api.jobtechdev.se/search"
TAXONOMY = "https://taxonomy.api.jobtechdev.se/v1/taxonomy/main/concepts"
SCB_BASER = ["https://statistikdatabasen.scb.se/api/v2", "https://api.scb.se/ov0104/v2beta/api/v2"]
SWEA = "https://api.riksbank.se/swea/v1"
SWEA_PAUS = 13
MIN_ANNONSER = 5000  # färre annonser totalt en månad = för ofullständig för att räkna andel
JOBTECH_OMHAMTA_MAN = 3  # senaste månaderna hämtas om varje gång (annonser registreras i efterhand)
HEADERS = {"accept": "application/json", "User-Agent": "byggpuls (github.com/claesludvig/projekt)"}


def _get(url: str, params=None, forsok: int = 3, paus: float = 2.0):
    """GET med nya försök vid nätverksfel, 429 och 5xx (längre paus vid 429)."""
    for i in range(forsok):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if i == forsok - 1:
                raise
            kvot = exc.response is not None and exc.response.status_code == 429
            time.sleep(paus * 2 ** i * (10 if kvot else 1))


def manader(fran: str, till: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(pd.Timestamp(fran + "-01"), till, freq="MS")


# ---------- JobTech ----------

def jobtech_yrkesomrade(konfig: dict) -> str:
    try:
        lista = _get(TAXONOMY, {"type": "occupation-field"})
        for c in lista:
            if c.get("taxonomy/preferred-label", "").strip().lower() == konfig["yrkesomrade_namn"].lower():
                print(f"  Yrkesområde {c['taxonomy/preferred-label']}: {c['taxonomy/id']}")
                return c["taxonomy/id"]
        print(f"  Hittade inte '{konfig['yrkesomrade_namn']}' i taxonomin, använder reserv-id")
    except Exception as exc:  # noqa: BLE001
        print(f"  Taxonomin: fel {exc}, använder reserv-id")
    return konfig["yrkesomrade_id_reserv"]


def _antal(url: str, params: dict) -> int:
    d = _get(url, {**params, "limit": 0})
    tot = d.get("total")
    return int(tot["value"] if isinstance(tot, dict) else tot)


def jobtech_historik(falt: str, man: pd.DatetimeIndex, cache: pd.DataFrame) -> tuple[dict, list]:
    """Antal annonser publicerade per månad: bygg och anläggning, och alla
    yrken (nämnare för andelen). Månader som redan finns i cache hämtas
    inte om, utom de senaste."""
    ut = {"annonser_bygg": {}, "annonser_alla": {}}
    fel, omhamta = [], set(man[-JOBTECH_OMHAMTA_MAN:])
    for m in man:
        fran = m.strftime("%Y-%m-%dT00:00:00")
        till = (m + pd.DateOffset(months=1)).strftime("%Y-%m-%dT00:00:00")
        for kol, extra in (("annonser_bygg", {"occupation-field": falt}), ("annonser_alla", {})):
            if m not in omhamta and kol in cache and m in cache.index and pd.notna(cache.at[m, kol]):
                ut[kol][m] = cache.at[m, kol]
                continue
            try:
                ut[kol][m] = _antal(HISTORICAL, {"historical-from": fran, "historical-to": till, **extra})
            except Exception as exc:  # noqa: BLE001
                fel.append(f"JobTech {kol} {m:%Y-%m}: {exc}")
    for kol in ut:
        s = pd.Series(ut[kol], dtype=float)
        # Historik-API:t fylls på i efterhand, så de senaste månaderna är
        # ofullständiga. Andelen bygg av alla annonser håller ändå; bara
        # månader med för få annonser för en stabil andel stryks.
        s[pd.Series(ut["annonser_alla"], dtype=float).reindex(s.index) < MIN_ANNONSER] = np.nan
        ut[kol] = s
        if s.notna().any():
            print(f"  {kol}: {s.notna().sum()} månader, senast {s.dropna().index[-1]:%Y-%m} = {s.dropna().iloc[-1]:.0f}")
    return ut, fel


def jobtech_nulage(falt: str, idag: date) -> list:
    """Dagens antal aktiva annonser: sparas i annonser_dag.csv."""
    try:
        rad = {"datum": idag.isoformat(), "aktiva_bygg": _antal(JOBSEARCH, {"occupation-field": falt}),
               "aktiva_alla": _antal(JOBSEARCH, {})}
    except Exception as exc:  # noqa: BLE001
        return [f"JobTech aktiva annonser: {exc}"]
    df = pd.read_csv(DAG_CSV) if DAG_CSV.exists() else pd.DataFrame(columns=list(rad))
    df = pd.concat([df[df["datum"] != rad["datum"]], pd.DataFrame([rad])]).sort_values("datum")
    df.to_csv(DAG_CSV, index=False)
    print(f"  Aktiva annonser idag: bygg {rad['aktiva_bygg']}, alla {rad['aktiva_alla']}")
    return []


# ---------- SCB (PxWebApi 2, json-stat2) ----------

class Scb:
    def __init__(self):
        self.bas = None
        for b in SCB_BASER:
            try:
                _get(f"{b}/config", forsok=1)
                self.bas = b
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  SCB {b}: {exc}")
        if self.bas is None:
            raise RuntimeError("inget SCB-API svarar")
        print(f"  SCB-API: {self.bas}")

    def sok(self, fraga: str) -> list:
        return _get(f"{self.bas}/tables", {"query": fraga, "lang": "sv", "pageSize": 30}).get("tables", [])

    def metadata(self, tabell: str) -> dict:
        return _get(f"{self.bas}/tables/{tabell}/metadata", {"lang": "sv"})

    def data(self, tabell: str, urval: dict) -> dict:
        params = {"lang": "sv", "outputFormat": "json-stat2"}
        for dim, koder in urval.items():
            params[f"valueCodes[{dim}]"] = koder if isinstance(koder, str) else ",".join(koder)
        return _get(f"{self.bas}/tables/{tabell}/data", params)


def jsonstat_serie(d: dict) -> pd.Series:
    """json-stat2 → tidsserie. Väljs flera värden i en icke-tidsdimension
    (t.ex. både flerbostadshus och småhus) summeras de."""
    dims, storlek = list(d["id"]), list(d["size"])
    roll = d.get("role", {}).get("time") or [x for x in dims if x.lower().startswith("tid")]
    tid = roll[0]
    kat = d["dimension"][tid]["category"]["index"]
    koder = sorted(kat, key=kat.get) if isinstance(kat, dict) else kat
    varden = d["value"]
    if isinstance(varden, dict):
        varden = [varden.get(str(i)) for i in range(int(np.prod(storlek)))]
    arr = np.array([np.nan if v is None else float(v) for v in varden]).reshape(storlek)
    arr = np.moveaxis(arr, dims.index(tid), -1).reshape(-1, len(koder))
    summa = np.where(np.isnan(arr).all(axis=0), np.nan, np.nansum(arr, axis=0))
    return pd.Series(summa, index=[_scb_tid(k) for k in koder]).sort_index()


def _scb_tid(kod: str) -> pd.Timestamp:
    if "M" in kod:
        return pd.Timestamp(f"{kod[:4]}-{kod[5:7]}-01")
    if "K" in kod:
        return pd.Period(f"{kod[:4]}Q{kod[-1]}", "Q").start_time
    return pd.Timestamp(f"{kod[:4]}-01-01")


NYCKELORD = {"bygglov_lgh": ["riket", "totalt", "samtliga", "lägenheter"],
             "paborjade_lgh": ["påbörjade", "riket", "samtliga", "totalt", "flerbostadshus och småhus"]}


def _auto_urval(meta: dict, nyckelord: list) -> dict:
    """Välj hela tidsaxeln och, för övriga dimensioner, första värdet vars
    etikett innehåller ett nyckelord (annars första värdet)."""
    urval = {}
    tid = meta.get("role", {}).get("time", [])
    for dim in meta["id"]:
        kat = meta["dimension"][dim]["category"]
        if dim in tid or dim.lower().startswith("tid"):
            urval[dim] = "*"
            continue
        etiketter = kat.get("label", {})
        idx = kat["index"]
        koder = sorted(idx, key=idx.get) if isinstance(idx, dict) else idx
        val = next((k for o in nyckelord for k in koder if o in etiketter.get(k, "").lower()), koder[0])
        urval[dim] = [val]
    return urval


def scb_serier(konfig: dict, logg: list) -> tuple[dict, list]:
    ut, fel = {}, []
    try:
        scb = Scb()
    except Exception as exc:  # noqa: BLE001
        return ut, [f"SCB: {exc}"]
    for fraga in konfig.get("_utforska", []):
        try:
            traffar = scb.sok(fraga)
        except Exception as exc:  # noqa: BLE001
            logg.append(f"## Utforska '{fraga}': fel {exc}")
            continue
        logg.append(f"## Utforska '{fraga}': {len(traffar)} träffar")
        logg += [f"{t.get('id')}\t{t.get('timeUnit')}\t{t.get('firstPeriod')}–{t.get('lastPeriod')}\t{t.get('label')}"
                 for t in traffar]
    for nyckel, k in konfig.items():
        if nyckel.startswith("_"):
            continue
        try:
            tabell = k.get("tabell")
            if not tabell:
                traffar = scb.sok(k["sok"])
                logg.append(f"## Sök '{k['sok']}' ({nyckel})")
                for t in traffar:
                    logg.append(f"{t.get('id')}\t{t.get('timeUnit')}\t{t.get('firstPeriod')}–{t.get('lastPeriod')}\t{t.get('label')}")
                kandidater = [t for t in traffar if t.get("timeUnit") == k["tidsenhet"]
                              and k["etikett"] in t.get("label", "").lower()]
                if not kandidater:
                    raise RuntimeError(f"ingen tabell hittad för '{k['sok']}'")
                tabell = max(kandidater, key=lambda t: str(t.get("lastPeriod")))["id"]
            meta = scb.metadata(tabell)
            logg.append(f"## Tabell {tabell} ({nyckel}): {meta.get('label')}")
            for dim in meta["id"]:
                kat = meta["dimension"][dim]["category"]
                idx = kat["index"]
                koder = sorted(idx, key=idx.get) if isinstance(idx, dict) else idx
                visa = [f"{c}={kat.get('label', {}).get(c, '')}" for c in koder[:25]]
                logg.append(f"  {dim} ({len(koder)}): " + "; ".join(visa))
            urval = k.get("urval") or _auto_urval(meta, NYCKELORD.get(nyckel, []))
            logg.append(f"  urval: {json.dumps(urval, ensure_ascii=False)}")
            s = jsonstat_serie(scb.data(tabell, urval)).dropna()
            ut[nyckel] = s
            print(f"  {nyckel} ({tabell}): {len(s)} värden, senast {s.index[-1]:%Y-%m} = {s.iloc[-1]:.0f}")
        except Exception as exc:  # noqa: BLE001
            fel.append(f"SCB {nyckel}: {exc}")
            print(f"  SCB {nyckel}: fel {exc}")
    return ut, fel


# ---------- Riksbanken och Yahoo ----------

def swea_manad(serie_id: str, fran: date, till: date) -> pd.Series:
    time.sleep(SWEA_PAUS)
    obs = _get(f"{SWEA}/Observations/{serie_id}/{fran.isoformat()}/{till.isoformat()}", paus=30)
    s = pd.Series({pd.Timestamp(o["date"]): o["value"] for o in obs if o.get("value") is not None}, dtype=float)
    return s.resample("MS").mean()


def byggaktier_manad(fran: str) -> pd.Series:
    """Likaviktat index av byggbolagens månadssnittkurser (utdelningsjusterade).
    Bolag som saknar historik tidigt kommer in när de börsnoteras."""
    import yfinance as yf

    bolag = json.loads((BASE_DIR.parent / "byggfastighet" / "bolag.json").read_text(encoding="utf-8"))["bygg"]
    tickers = [b["ticker"] for b in bolag]
    start = (pd.Timestamp(fran + "-01") - pd.DateOffset(months=14)).strftime("%Y-%m-%d")
    raw = yf.download(tickers, start=start, interval="1d", auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    man = raw.resample("MS").mean()
    avk = man.pct_change(fill_method=None).mean(axis=1, skipna=True)
    print(f"  Byggaktier: {man.notna().sum().to_dict()}")
    return (1 + avk.fillna(0)).cumprod() * 100


# ---------- grafer ----------

FARG = {"pca": "#1a365d", "lika": "#a0aec0", "mal": "#c05621"}


def _stil(ax):
    ax.tick_params(labelsize=9, colors="#4a5568")
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)


def rita_index(index: pd.Series, lika: pd.Series, mal: pd.Series, ledtid: int, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=110, layout="constrained")
    ax.plot(lika.index, lika, color=FARG["lika"], linewidth=1.2, label="Likaviktat")
    ax.plot(index.index, index, color=FARG["pca"], linewidth=2, label="Byggpulsen")
    ax.axhline(0, color="#718096", linewidth=0.8)
    ax.set_ylabel("Standardavvikelser", fontsize=9, color="#4a5568")
    h, l = ax.get_legend_handles_labels()
    if len(mal) and isinstance(mal.index, pd.DatetimeIndex):
        ax2 = ax.twinx()
        m = mal.copy()
        m.index = m.index - pd.DateOffset(months=3 * ledtid)
        ax2.plot(m.index, m, color=FARG["mal"], linewidth=1.6, linestyle="--",
                 label=f"Påbörjade lgh, årsförändring % (höger, flyttad {ledtid} kv bakåt)")
        ax2.tick_params(labelsize=9, colors="#4a5568")
        ax2.spines["top"].set_visible(False)
        h2, l2 = ax2.get_legend_handles_labels()
        h, l = h + h2, l + l2
    ax.legend(h, l, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8, frameon=False, borderaxespad=0.2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _stil(ax)
    fig.savefig(path)
    plt.close(fig)


def rita_bidrag(rader: list, manad: str, path: Path) -> None:
    rader = [r for r in rader if r["bidrag"] is not None]
    fig, ax = plt.subplots(figsize=(6.4, 0.5 + 0.45 * len(rader)), dpi=110, layout="constrained")
    y = range(len(rader))
    v = [r["bidrag"] for r in rader]
    ax.barh(list(y), v, color=["#276749" if x > 0 else "#c53030" for x in v])
    ax.set_yticks(list(y), [r["namn"] for r in rader], fontsize=9)
    ax.axvline(0, color="#718096", linewidth=0.8)
    ax.set_xlabel(f"Bidrag till Byggpulsen {manad}, standardavvikelser", fontsize=9, color="#4a5568")
    ax.invert_yaxis()
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

def _r(x, d=2):
    return None if x is None or pd.isna(x) else round(float(x), d)


def main() -> None:
    parser = argparse.ArgumentParser(description="Byggpulsen: eget ledande index för byggandet.")
    parser.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME", "main"))
    parser.add_argument("--utan-hamtning", action="store_true", help="räkna bara om från sparade serier")
    args = parser.parse_args()

    idag = datetime.now(timezone.utc).date()
    sista_hela = pd.Timestamp(idag.replace(day=1)) - pd.DateOffset(months=1)
    konfig = json.loads((BASE_DIR / "kallor.json").read_text(encoding="utf-8"))
    man = manader(konfig["start"], sista_hela)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache = pd.read_csv(SERIER_CSV, index_col=0, parse_dates=True) if SERIER_CSV.exists() else pd.DataFrame()
    mal_cache = pd.read_csv(MAL_CSV, index_col=0, parse_dates=True).iloc[:, 0] if MAL_CSV.exists() else pd.Series(dtype=float)
    fel, scb_logg = [], []

    if args.utan_hamtning:
        ra, mal = cache.copy(), mal_cache
    else:
        kol = {}
        print("JobTech:")
        falt = jobtech_yrkesomrade(konfig["jobtech"])
        hist, f = jobtech_historik(falt, man, cache)
        kol.update(hist)
        fel += f[:10] + ([f"… och {len(f) - 10} JobTech-fel till"] if len(f) > 10 else [])
        fel += jobtech_nulage(falt, idag)

        print("SCB:")
        scb, f = scb_serier(konfig["scb"], scb_logg)
        fel += f
        if "bygglov_lgh" in scb:
            # kvartal → månader: varje månad i kvartalet får kvartalets värde
            q = scb["bygglov_lgh"]
            kol["bygglov_lgh"] = q.reindex(pd.date_range(q.index[0], q.index[-1] + pd.DateOffset(months=2), freq="MS")).ffill(limit=2)
        mal = scb.get("paborjade_lgh", mal_cache)
        if scb_logg:
            (DATA_DIR / "scb_tabeller.txt").write_text("\n".join(scb_logg) + "\n", encoding="utf-8")

        print("Riksbanken:")
        try:
            kol["stat_5y"] = swea_manad(konfig["swea"]["Stat 5Y"], date.fromisoformat(konfig["start"] + "-01") - pd.Timedelta(days=400), idag)
            print(f"  Stat 5Y: senast {kol['stat_5y'].dropna().index[-1]:%Y-%m} = {kol['stat_5y'].dropna().iloc[-1]:.2f}")
        except Exception as exc:  # noqa: BLE001
            fel.append(f"SWEA Stat 5Y: {exc}")

        print("Yahoo:")
        try:
            kol["byggaktier"] = byggaktier_manad(konfig["start"])
        except Exception as exc:  # noqa: BLE001
            fel.append(f"Yahoo byggaktier: {exc}")

        ra = pd.DataFrame({k: v for k, v in kol.items() if len(v)})
        # behåll gamla värden om en källa föll bort den här gången
        for k in cache.columns:
            if k not in ra:
                ra[k] = cache[k]
        tidigast = pd.Timestamp(konfig["start"] + "-01") - pd.DateOffset(months=15)
        ra = ra[(ra.index >= tidigast) & (ra.index <= sista_hela)].sort_index()
        ra.index.name = "manad"
        ra.to_csv(SERIER_CSV)
        if len(mal):
            mal.rename("paborjade_lgh").to_csv(MAL_CSV, index_label="kvartal")

    if "annonser_bygg" in ra and "annonser_alla" in ra:
        # Byggets andel av alla platsannonser: tål att Platsbankens totala
        # volym svänger av skäl som inte har med konjunkturen att göra.
        ra["andel_annonser_bygg"] = ra["annonser_bygg"] / ra["annonser_alla"] * 100

    komp = [k for k in konfig["komponenter"] if k["id"] in ra and ra[k["id"]].notna().sum() > 24]
    saknas = [k["namn"] for k in konfig["komponenter"] if k not in komp]
    if saknas:
        fel.append("Komponenter utan data (ingår inte): " + ", ".join(saknas))
    pca = bpi.bygg_index(ra, komp, "pca")
    if pca is None:
        (DATA_DIR / "byggpuls.json").write_text(json.dumps({"datum": idag.isoformat(), "fel": fel}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit("För få komponenter för att räkna indexet:\n  " + "\n  ".join(fel))
    lika = bpi.bygg_index(ra, komp, "lika")

    print("Efterhandstest:")
    mal_ar = bpi.mal_arsforandring(mal) if len(mal) >= 12 else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    test = {}
    if len(mal_ar):
        rt_pca = bpi.realtidsindex(ra, komp, "pca")
        rt_lika = bpi.realtidsindex(ra, komp, "lika")
        test = {
            "realtid_pca": bpi.ledkorrelation(rt_pca, mal_ar),
            "realtid_lika": bpi.ledkorrelation(rt_lika, mal_ar),
            "hela_urvalet_pca": bpi.ledkorrelation(pca["index"], mal_ar),
        }
        test["realtid_fran"] = None if not len(rt_pca) else rt_pca.index[0].strftime("%Y-%m")
        for k, v in test.items():
            print(f"  {k}: {v}")
    kandidat = [r for r in test.get("realtid_pca", []) if r["korrelation"] is not None]
    bast = max(kandidat, key=lambda r: r["korrelation"]) if kandidat else None

    idx = pca["index"]
    sista = idx.index[-1]
    rader = []
    for k in komp:
        s = ra[k["id"]].dropna()
        z = pca["z"][k["id"]]
        sig = bpi.transformera(ra[k["id"]], k["transform"]).dropna()
        rader.append({
            "id": k["id"], "namn": k["namn"], "vikt": _r(pca["vikter"][k["id"]], 3),
            "senaste_manad": s.index[-1].strftime("%Y-%m"), "senaste_varde": _r(s.iloc[-1], 2),
            "signal": _r(sig.iloc[-1], 1) if len(sig) else None,
            "signal_enhet": "procentenheter mot för ett år sedan" if k["transform"] == "diff12" else "% mot för ett år sedan",
            "z": _r(z.get(sista)), "bidrag": _r(pca["bidrag"][k["id"]].get(sista)),
            "tecken": k["tecken"], "fordrojning_man": k["fordrojning_man"],
        })

    def fore(n):
        t = sista - pd.DateOffset(months=n)
        return _r(idx.get(t))

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
        grafer[nyckel] = f"{REPO_RAW_URL}/{args.branch}/{path.relative_to(BASE_DIR.parent).as_posix()}"

    ledtid = bast["ledtid_kvartal"] if bast else 0
    fran = sista - pd.DateOffset(years=8)
    spara("index", "byggpuls.png", lambda p: rita_index(idx[idx.index >= fran], lika["index"][lika["index"].index >= fran],
                                                         mal_ar[mal_ar.index >= fran - pd.DateOffset(months=3 * ledtid)], ledtid, p))
    spara("bidrag", "bidrag.png", lambda p: rita_bidrag(rader, sista.strftime("%Y-%m"), p))
    rensa_gamla_grafer(idag)

    dag = pd.read_csv(DAG_CSV) if DAG_CSV.exists() else pd.DataFrame()
    ut = {
        "genererad": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datum": idag.isoformat(),
        "manad": sista.strftime("%Y-%m"),
        "index": {
            "senast": _r(idx.iloc[-1]), "for_1_man": fore(1), "for_3_man": fore(3), "for_12_man": fore(12),
            "likaviktat_senast": _r(lika["index"].get(sista)),
            "komponenter_i_senaste": int(pca["bidrag"].loc[sista].notna().sum()), "komponenter_totalt": len(komp),
        },
        "komponenter": rader,
        "vikter_metod": pca["metod"],
        "efterhandstest": test,
        "bast_ledtid": bast,
        "serie": [{"manad": t.strftime("%Y-%m"), "pca": _r(v), "lika": _r(lika["index"].get(t))}
                  for t, v in idx[idx.index > sista - pd.DateOffset(months=36)].items()],
        "annonser_idag": None if dag.empty else dag.iloc[-1].to_dict(),
        "grafer": grafer,
        "metod": (
            "Varje komponent görs om till en årsförändring (annonserna: 3 månaders snitt), vänds så att "
            "högre = starkare byggande och standardiseras. Vikterna är laddningarna på första principalkomponenten, "
            "dvs. den rörelse komponenterna har gemensamt; ingen vikt är satt för hand. Indexet mäts i "
            "standardavvikelser från snittet sedan starten: 0 = normalt, ±1 = ovanligt starkt/svagt. En komponent "
            "som publiceras senare (bygglov, kvartal) behåller sitt senaste värde tills nästa normalt kommer. Efterhandstestet "
            "räknar om indexet varje månad med bara den data som då var publicerad (vikter skattade på data fram "
            "till dess) och jämför med årsförändringen i påbörjade lägenheter (rullande fyra kvartal) 0–4 kvartal "
            "senare. Byggaktierna är likaviktade och bara dagens bolag (överlevnadsbias)."
        ),
        "fel": fel,
    }
    (DATA_DIR / "byggpuls.json").write_text(json.dumps(ut, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Byggpulsen {ut['manad']}: {ut['index']['senast']} (likaviktat {ut['index']['likaviktat_senast']})")
    print(f"Vikter: {pca['vikter'].round(3).to_dict()}")
    if fel:
        print("Problem:\n  " + "\n  ".join(fel))


if __name__ == "__main__":
    main()
