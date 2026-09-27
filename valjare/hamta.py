#!/usr/bin/env python3
"""Väljardatabasen, steg 1: hämta rådata.

- SCB (PxWebApi v2): PSU (partisympati per grupp), valdeltagande, valresultat,
  befolkning, utbildning, inkomst, arbete, utsatthet för brott/trygghet.
  Varje tabell sparas i långt format som data/scb/<tabell-id>.csv.gz.
- Dokument (Valu, Valforskningsprogrammet): pdf laddas ned till
  data/kallor/pdf och textextraheras sida för sida till data/kallor/txt.
- Länksidor (Brå NTU, Valmyndigheten, GU): skrapas efter pdf/xlsx-länkar.
  Excelfiler sparas i data/kallor/xlsx med en översikt per flik i txt.

Allt loggas i data/katalog/hamtlogg.json. Tolkning och harmonisering görs i
bygg_db.py, som bara läser det som ligger på disk här."""

import argparse
import itertools
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

from kallor import DOKUMENT, LANKSIDOR, SCB_API, SCB_EXKLUDERA, SCB_SOK, SCB_TABELLER

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCB_DIR = DATA_DIR / "scb"
KALL_DIR = DATA_DIR / "kallor"
KAT_DIR = DATA_DIR / "katalog"
MAX_CELLER_PER_ANROP = 100_000   # SCB tillåter 150 000, marginal för avrundning
UA = {"User-Agent": "valjardatabas/1.0 (github.com/claesludvig/projekt)"}

session = requests.Session()
session.headers.update(UA)
logg: dict = {"start": datetime.now(timezone.utc).isoformat(), "scb": [],
              "dokument": [], "lanksidor": [], "fel": []}


# ---------- http ----------

_senaste_scb: list[float] = []


def _scb_paus():
    """Max 30 anrop per 10 s mot SCB; vi håller oss runt 20."""
    nu = time.time()
    while _senaste_scb and nu - _senaste_scb[0] > 10:
        _senaste_scb.pop(0)
    if len(_senaste_scb) >= 20:
        time.sleep(10 - (nu - _senaste_scb[0]) + 0.2)
    _senaste_scb.append(time.time())


def http(metod: str, url: str, scb: bool = False, **kw) -> requests.Response:
    for forsok in range(5):
        if scb:
            _scb_paus()
        try:
            r = session.request(metod, url, timeout=120, **kw)
        except requests.RequestException as exc:
            fel = str(exc)
        else:
            if r.status_code == 429 or r.status_code >= 500:
                fel = f"HTTP {r.status_code}"
            else:
                return r
        vänta = 3 * (forsok + 1)
        print(f"    {fel} – nytt försök om {vänta}s")
        time.sleep(vänta)
    raise RuntimeError(f"{metod} {url}: {fel}")


# ---------- SCB ----------

def scb_sok(fraga: str) -> list[dict]:
    tabeller, sida = [], 1
    while True:
        r = http("GET", f"{SCB_API}/tables", scb=True,
                 params={"lang": "sv", "query": fraga, "pageSize": 100,
                         "pageNumber": sida})
        r.raise_for_status()
        j = r.json()
        tabeller += j.get("tables", [])
        sidinfo = j.get("page", {})
        if sida >= sidinfo.get("totalPages", 1):
            return tabeller
        sida += 1


def _stig(t: dict) -> str:
    stigar = t.get("paths") or []
    if not stigar:
        return ""
    return " / ".join(p.get("label", p.get("id", "")) for p in stigar[0])


def scb_metadata(tab_id: str) -> dict:
    r = http("GET", f"{SCB_API}/tables/{tab_id}/metadata", scb=True,
             params={"lang": "sv", "outputFormat": "json-stat2"})
    r.raise_for_status()
    return r.json()


def _regiondim(meta: dict) -> str | None:
    roll = meta.get("role", {}) or {}
    if roll.get("geo"):
        return roll["geo"][0]
    for d in meta["id"]:
        if d.lower().startswith("region"):
            return d
    return None


def _tiddim(meta: dict) -> str | None:
    roll = meta.get("role", {}) or {}
    if roll.get("time"):
        return roll["time"][0]
    return "Tid" if "Tid" in meta["id"] else None


def scb_urval(meta: dict, region: str, utelamna=()) -> dict[str, list[str]]:
    urval = {}
    regdim = _regiondim(meta)
    for d in meta["id"]:
        if d in utelamna:
            continue
        koder = list(meta["dimension"][d]["category"]["index"].keys()) \
            if isinstance(meta["dimension"][d]["category"]["index"], dict) \
            else list(meta["dimension"][d]["category"]["index"])
        if d == regdim and region != "alla":
            if region == "riket":
                valda = [k for k in koder if k in ("00", "0", "SE", "Riket")]
            else:  # kommun: riket, län, kommuner
                valda = [k for k in koder if re.fullmatch(r"\d{2}|\d{4}", k)]
            koder = valda or koder[:1]
        urval[d] = koder
    return urval


def _dela(urval: dict[str, list[str]], tiddim: str | None) -> list[dict]:
    """Dela upp ett urval i bitar under anropsgränsen, helst längs tiden."""
    celler = 1
    for v in urval.values():
        celler *= len(v)
    if celler <= MAX_CELLER_PER_ANROP:
        return [urval]
    ordning = sorted(urval, key=lambda d: (d != tiddim, -len(urval[d])))
    for d in ordning:
        if len(urval[d]) > 1:
            halv = len(urval[d]) // 2
            a, b = dict(urval), dict(urval)
            a[d], b[d] = urval[d][:halv], urval[d][halv:]
            return _dela(a, tiddim) + _dela(b, tiddim)
    return [urval]


def jsonstat_till_df(j: dict) -> pd.DataFrame:
    dims = j["id"]
    kategorier = []
    for d in dims:
        kat = j["dimension"][d]["category"]
        idx = kat["index"]
        koder = sorted(idx, key=idx.get) if isinstance(idx, dict) else list(idx)
        etiketter = kat.get("label", {})
        kategorier.append([(k, etiketter.get(k, k)) for k in koder])
    varden = j["value"]
    if isinstance(varden, dict):   # glest format
        n = 1
        for k in kategorier:
            n *= len(k)
        full = [None] * n
        for i, v in varden.items():
            full[int(i)] = v
        varden = full
    rader = []
    for kombination, v in zip(itertools.product(*kategorier), varden):
        rad = {}
        for d, (kod, etikett) in zip(dims, kombination):
            rad[d + "_kod"] = kod
            rad[d] = etikett
        rad["varde"] = v
        rader.append(rad)
    return pd.DataFrame(rader)


def scb_hamta_tabell(tab_id: str, region: str, max_celler: int,
                     utelamna=()) -> tuple[pd.DataFrame, dict]:
    meta = scb_metadata(tab_id)
    urval = scb_urval(meta, region, utelamna)
    celler = 1
    for v in urval.values():
        celler *= len(v)
    info = {"celler": celler, "variabler": {
        d: {"etikett": meta["dimension"][d].get("label", d), "antal": len(urval[d])}
        for d in meta["id"] if d in urval}}
    if utelamna:
        info["utelamnade"] = list(utelamna)
    if celler > max_celler:
        info["status"] = f"hoppad: {celler} celler > {max_celler}"
        return pd.DataFrame(), info
    delar = []
    for bit in _dela(urval, _tiddim(meta)):
        kropp = {"selection": [{"variableCode": d, "valueCodes": v}
                               for d, v in bit.items()]}
        r = http("POST", f"{SCB_API}/tables/{tab_id}/data", scb=True,
                 params={"lang": "sv", "outputFormat": "json-stat2"}, json=kropp)
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        delar.append(jsonstat_till_df(r.json()))
    df = pd.concat(delar, ignore_index=True)
    info["status"] = "ok"
    info["rader"] = len(df)
    info["uppdaterad"] = meta.get("updated")
    info["kalla"] = meta.get("source")
    return df, info


def hamta_scb(bara: str | None):
    SCB_DIR.mkdir(parents=True, exist_ok=True)
    katalog: dict[str, dict] = {}
    for post in SCB_SOK:
        if bara and post["tema"] != bara:
            continue
        print(f"SCB-sökning '{post['sok']}' ({post['tema']})")
        try:
            traffar = scb_sok(post["sok"])
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"scb sök {post['sok']}: {exc}")
            print(f"  fel: {exc}")
            continue
        for t in traffar:
            rad = katalog.setdefault(t["id"], {
                "id": t["id"], "rubrik": t.get("label", ""),
                "forsta": t.get("firstPeriod"), "sista": t.get("lastPeriod"),
                "uppdaterad": t.get("updated"), "stig": _stig(t),
                "variabler": "|".join(t.get("variableNames", []) or []),
                "avvecklad": t.get("discontinued"), "tema": "", "vald": False})
            if re.search(post["rubrik"], rad["rubrik"]) and \
                    not re.search(SCB_EXKLUDERA, rad["rubrik"]):
                rad["vald"] = True
                rad["tema"] = post["tema"]
                rad["_region"] = post["region"]
                rad["_max"] = post["max_celler"]
    for post in SCB_TABELLER:
        if bara and post["tema"] != bara:
            continue
        rad = katalog.setdefault(post["id"], {
            "id": post["id"], "rubrik": post["not"], "forsta": None, "sista": None,
            "uppdaterad": None, "stig": "", "variabler": "", "avvecklad": None})
        rad.update({"vald": True, "tema": post["tema"], "_region": post["region"],
                    "_max": post["max_celler"], "_utelamna": post.get("utelamna", [])})
    kat_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")}
                           for r in katalog.values()])
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    if len(kat_df):
        kat_df.sort_values(["vald", "tema", "id"], ascending=[False, True, True]) \
            .to_csv(KAT_DIR / "scb_katalog.csv", index=False)
    valda = [r for r in katalog.values() if r["vald"]]
    print(f"{len(katalog)} SCB-tabeller hittade, {len(valda)} valda")
    for r in valda:
        print(f"  {r['id']} {r['rubrik'][:90]}")
        post_logg = {"id": r["id"], "rubrik": r["rubrik"], "tema": r["tema"]}
        try:
            df, info = scb_hamta_tabell(r["id"], r["_region"], r["_max"],
                                        r.get("_utelamna", ()))
            post_logg.update(info)
            if len(df):
                df.insert(0, "tabell", r["id"])
                df.to_csv(SCB_DIR / f"{r['id']}.csv.gz", index=False,
                          compression={"method": "gzip", "mtime": 0})
            print(f"    {info['status']} ({info.get('rader', 0)} rader)")
        except Exception as exc:  # noqa: BLE001
            post_logg["status"] = f"fel: {exc}"
            print(f"    fel: {exc}")
        logg["scb"].append(post_logg)


# ---------- dokument ----------

def _pdf_till_text(pdf: Path, txt: Path):
    import pdfplumber
    with pdfplumber.open(pdf) as doc, txt.open("w", encoding="utf-8") as ut:
        for i, sida in enumerate(doc.pages, 1):
            ut.write(f"\n===== sida {i} =====\n")
            ut.write(sida.extract_text(layout=True) or "")
            ut.write("\n")


def _xlsx_oversikt(xlsx: Path, txt: Path):
    with txt.open("w", encoding="utf-8") as ut:
        blad = pd.read_excel(xlsx, sheet_name=None, header=None, nrows=60)
        for namn, df in blad.items():
            ut.write(f"\n===== flik: {namn} ({df.shape[0]}x{df.shape[1]}) =====\n")
            ut.write(df.dropna(how="all").dropna(axis=1, how="all")
                     .to_string(max_colwidth=40, max_cols=30))
            ut.write("\n")


def ladda_ned(doc_id: str, url: str, typ: str) -> dict:
    post = {"id": doc_id, "typ": typ, "url": url}
    try:
        r = http("GET", url)
        if r.status_code != 200:
            post["status"] = f"HTTP {r.status_code}"
            return post
        ext = Path(url.split("?")[0]).suffix.lower() or ".bin"
        if "pdf" in r.headers.get("Content-Type", ""):
            ext = ".pdf"
        katalog = KALL_DIR / ext.lstrip(".")
        katalog.mkdir(parents=True, exist_ok=True)
        fil = katalog / f"{doc_id}{ext}"
        fil.write_bytes(r.content)
        post["fil"] = str(fil.relative_to(BASE_DIR))
        post["bytes"] = len(r.content)
        txt_dir = KALL_DIR / "txt"
        txt_dir.mkdir(parents=True, exist_ok=True)
        if ext == ".pdf":
            _pdf_till_text(fil, txt_dir / f"{doc_id}.txt")
        elif ext in (".xlsx", ".xls"):
            _xlsx_oversikt(fil, txt_dir / f"{doc_id}.txt")
        post["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        post["status"] = f"fel: {exc}"
    print(f"  {doc_id}: {post['status']}")
    return post


def _slug(s: str) -> str:
    s = re.sub(r"%[0-9A-Fa-f]{2}", "_", s)
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")[:80]


def hamta_dokument():
    print("Dokument")
    for d in DOKUMENT:
        logg["dokument"].append(ladda_ned(d["id"], d["url"], d["typ"]))
    print("Länksidor")
    sedda = {d["url"] for d in DOKUMENT}
    for s in LANKSIDOR:
        post = {"id": s["id"], "url": s["url"], "lankar": []}
        try:
            r = http("GET", s["url"])
            post["status"] = f"HTTP {r.status_code}"
            hrefs = re.findall(r'href="([^"]+)"', r.text)
            lankar = []
            for h in hrefs:
                u = urljoin(s["url"], h.replace("&amp;", "&"))
                if re.search(s["lank"], u) and u not in sedda:
                    sedda.add(u)
                    lankar.append(u)
            for u in lankar[: s["max"]]:
                namn = f"{s['id']}__{_slug(Path(u.split('?')[0]).stem)}"
                post["lankar"].append(ladda_ned(namn, u, s["typ"]))
        except Exception as exc:  # noqa: BLE001
            post["status"] = f"fel: {exc}"
        print(f"  {s['id']}: {post['status']}, {len(post['lankar'])} filer")
        logg["lanksidor"].append(post)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--steg", choices=["alla", "scb", "dokument"], default="alla")
    p.add_argument("--tema", help="bara ett SCB-tema (t.ex. psu)")
    a = p.parse_args()
    if a.steg in ("alla", "scb"):
        hamta_scb(a.tema)
    if a.steg in ("alla", "dokument"):
        hamta_dokument()
    logg["slut"] = datetime.now(timezone.utc).isoformat()
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    (KAT_DIR / "hamtlogg.json").write_text(
        json.dumps(logg, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
