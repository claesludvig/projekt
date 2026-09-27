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
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

from kallor import DOKUMENT, GEODATA, LANKSIDOR, SCB_API, SCB_EXKLUDERA, SCB_SOK, SCB_TABELLER

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


def scb_urval(meta: dict, region: str, utelamna=(), senaste: int | None = None) -> dict[str, list[str]]:
    urval = {}
    regdim = _regiondim(meta)
    tiddim = _tiddim(meta)
    for d in meta["id"]:
        if d in utelamna:
            continue
        koder = list(meta["dimension"][d]["category"]["index"].keys()) \
            if isinstance(meta["dimension"][d]["category"]["index"], dict) \
            else list(meta["dimension"][d]["category"]["index"])
        if d == regdim and region != "alla":
            if region == "deso":
                valda = [k for k in koder if re.match(r"^\d{4}[A-C]\d{4}", k)]
            elif region == "riket":
                valda = [k for k in koder if k in ("00", "0", "SE", "Riket")]
            else:  # kommun: riket, län, kommuner
                valda = [k for k in koder if re.fullmatch(r"\d{2}|\d{4}", k)]
            koder = valda or koder[:1]
        if d == tiddim and senaste:
            koder = koder[-senaste:]
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
    mi = pd.MultiIndex.from_product([[k for k, _ in kat] for kat in kategorier], names=dims)
    ut = {}
    for niva, (d, kat) in enumerate(zip(dims, kategorier)):
        koder = mi.get_level_values(niva)
        ut[d + "_kod"] = koder
        ut[d] = koder.map(dict(kat))
    ut["varde"] = pd.to_numeric(pd.Series(varden, dtype="object"), errors="coerce").values
    return pd.DataFrame(ut)


def scb_hamta_tabell(tab_id: str, region: str, max_celler: int,
                     utelamna=(), senaste: int | None = None) -> tuple[pd.DataFrame, dict]:
    meta = scb_metadata(tab_id)
    urval = scb_urval(meta, region, utelamna, senaste)
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


def hamta_scb(bara: str | None, tvinga: bool = False):
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
            if post.get("max_tabeller") and sum(
                    1 for x in katalog.values() if x.get("_post") == post["sok"]) >= post["max_tabeller"]:
                continue
            text = rad["rubrik"] + " | " + rad["stig"] if post.get("med_stig") else rad["rubrik"]
            if re.search(post["rubrik"], text) and not re.search(SCB_EXKLUDERA, rad["rubrik"]) \
                    and not (post.get("exkludera") and re.search(post["exkludera"], text)):
                rad["vald"] = True
                rad["tema"] = post["tema"]
                rad["_region"] = post["region"]
                rad["_max"] = post["max_celler"]
                rad["_senaste"] = post.get("senaste")
                rad["_post"] = post["sok"]
    for post in SCB_TABELLER:
        if bara and post["tema"] != bara:
            continue
        nyckel = post["id"] + post.get("suffix", "")
        rad = katalog.setdefault(nyckel, {
            "id": nyckel, "rubrik": post["not"], "forsta": None, "sista": None,
            "uppdaterad": None, "stig": "", "variabler": "", "avvecklad": None})
        rad.update({"vald": True, "tema": post["tema"], "_region": post["region"],
                    "_max": post["max_celler"], "_utelamna": post.get("utelamna", []),
                    "_senaste": post.get("senaste"), "_tab": post["id"]})
    kat_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")}
                           for r in katalog.values()])
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    forra = {}
    if (KAT_DIR / "scb_katalog.csv").exists() and not tvinga:
        f = pd.read_csv(KAT_DIR / "scb_katalog.csv", dtype=str)
        forra = dict(zip(f["id"], f["uppdaterad"].fillna("")))
    if len(kat_df):
        kat_df.sort_values(["vald", "tema", "id"], ascending=[False, True, True]) \
            .to_csv(KAT_DIR / "scb_katalog.csv", index=False)
    valda = [r for r in katalog.values() if r["vald"]]
    print(f"{len(katalog)} SCB-tabeller hittade, {len(valda)} valda")
    for r in valda:
        print(f"  {r['id']} {r['rubrik'][:90]}")
        post_logg = {"id": r["id"], "rubrik": r["rubrik"], "tema": r["tema"]}
        if r.get("uppdaterad") and forra.get(r["id"]) == str(r["uppdaterad"]) \
                and (SCB_DIR / f"{r['id']}.csv.gz").exists():
            post_logg["status"] = "oförändrad, ej hämtad"
            logg["scb"].append(post_logg)
            print("    oförändrad")
            continue
        try:
            df, info = scb_hamta_tabell(r.get("_tab", r["id"]), r["_region"], r["_max"],
                                        r.get("_utelamna", ()), r.get("_senaste"))
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


def ladda_ned(doc_id: str, url: str, typ: str, tvinga: bool = False) -> dict:
    post = {"id": doc_id, "typ": typ, "url": url}
    if not tvinga and url.lower().split("?")[0].endswith(".pdf") and \
            (KALL_DIR / "txt" / f"{doc_id}.txt").exists():
        post["status"] = "text finns, ej hämtad"
        return post
    try:
        r = http("GET", url)
        if r.status_code != 200:
            post["status"] = f"HTTP {r.status_code}"
            return post
        seg = next((x for x in reversed(url.split("?")[0].split("/"))
                    if re.search(r"\.(pdf|xlsx?|zip|csv)$", x, re.I)), url.split("?")[0])
        ext = Path(seg).suffix.lower() or ".bin"
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


def hamta_dokument(tvinga: bool = False):
    print("Dokument")
    for d in DOKUMENT:
        logg["dokument"].append(ladda_ned(d["id"], d["url"], d["typ"], tvinga))
    print("Länksidor")
    sedda = {d["url"] for d in DOKUMENT}
    for s in LANKSIDOR:
        post = {"id": s["id"], "url": s["url"], "lankar": []}
        try:
            r = http("GET", s["url"])
            post["status"] = f"HTTP {r.status_code}"
            sidor = [(s["url"], r.text)]
            # Följ undersidor (samma webbplats) vars adress matchar "folj"
            if s.get("folj"):
                for h in dict.fromkeys(re.findall(r'href="([^"#]+)"', r.text)):
                    u = urljoin(s["url"], h.replace("&amp;", "&"))
                    if re.search(s["folj"], u) and urlparse(u).netloc == urlparse(s["url"]).netloc \
                            and not re.search(r"\.(pdf|xlsx?|zip)", u, re.I) and u != s["url"]:
                        try:
                            sidor.append((u, http("GET", u).text))
                        except Exception:  # noqa: BLE001
                            pass
                    if len(sidor) > 25:
                        break
            lankar = []
            for bas, html in sidor:
                for h in re.findall(r'href="([^"]+)"', html):
                    u = urljoin(bas, h.replace("&amp;", "&"))
                    if re.search(s["lank"], u) and u not in sedda:
                        sedda.add(u)
                        lankar.append(u)
            for u in lankar[: s["max"]]:
                seg = next((x for x in reversed(u.split("?")[0].split("/"))
                            if re.search(r"\.(pdf|xlsx?|zip|csv)$", x, re.I)), u.split("?")[0].split("/")[-1])
                namn = f"{s['id']}__{_slug(Path(seg).stem)}"
                post["lankar"].append(ladda_ned(namn, u, s["typ"], tvinga or s.get("alltid", False)))
        except Exception as exc:  # noqa: BLE001
            post["status"] = f"fel: {exc}"
        print(f"  {s['id']}: {post['status']}, {len(post['lankar'])} filer")
        logg["lanksidor"].append(post)


# ---------- Kolada och Riksbanken ----------

KOLADA_API = "https://api.kolada.se/v3"


def _kolada_alla(sokvag: str, params: dict) -> list[dict]:
    """v3: frågeparametrar, sidor via page/per_page, nästa sida anges i next_url."""
    ut, url, par, sedda = [], f"{KOLADA_API}/{sokvag}", {**params, "per_page": 5000}, set()
    while url and url not in sedda and len(sedda) < 200:
        sedda.add(url)
        r = http("GET", url, params=par)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        j = r.json()
        ut += j.get("values", [])
        url, par = j.get("next_url") or j.get("next_page"), None   # nästa sida är en färdig adress
    return ut


def hamta_kolada():
    """Nyckeltal per kommun, region och riket för verklighetsindikatorerna."""
    from verklighet_katalog import KOLADA
    print("Kolada")
    kat, valda = [], {}
    for fraga, namn, sok, valj, _ in KOLADA:
        if re.fullmatch(r"[NU]\d{5}", sok):          # känt id
            try:
                meta = _kolada_alla(f"kpi/{sok}", {})
            except Exception:  # noqa: BLE001
                meta = []
            titel = meta[0].get("title", namn) if meta else namn
            valda[sok] = (fraga, namn, titel)
            kat.append({"fraga": fraga, "namn": namn, "sok": sok, "id": sok, "titel": titel, "matchar": True})
            print(f"  {namn}: id {sok}")
            continue
        try:
            traffar = _kolada_alla("kpi", {"title": sok})
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"kolada sök {sok}: {exc}")
            continue
        vald = None
        for t in traffar:
            ok = re.search(valj, t.get("title", "")) is not None
            kat.append({"fraga": fraga, "namn": namn, "sok": sok, "id": t.get("id"),
                        "titel": t.get("title"), "matchar": ok,
                        "kommun": t.get("municipality_type"), "fran": t.get("publication_date")})
            if ok and vald is None:
                vald = t
        if vald:
            valda[vald["id"]] = (fraga, namn, vald["title"])
        print(f"  {namn}: {len(traffar)} träffar, vald {vald['id'] if vald else '–'}")
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(kat).to_csv(KAT_DIR / "kolada_katalog.csv", index=False)
    ut_dir = DATA_DIR / "kolada"
    ut_dir.mkdir(parents=True, exist_ok=True)
    ar = [str(a) for a in range(2006, datetime.now().year + 1)]
    for kid, (fraga, namn, titel) in valda.items():
        try:
            v = _kolada_alla("data", {"kpi_id": kid, "year": ar})
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"kolada data {kid}: {exc}")
            continue
        rader = []
        for rad in v:
            for x in rad.get("values", []):
                if x.get("gender") in ("T", None) and x.get("value") is not None:
                    rader.append({"kpi": kid, "titel": titel, "fraga": fraga, "namn": namn,
                                  "region_kod": rad.get("municipality") or rad.get("municipality_id"),
                                  "ar": rad.get("period") or rad.get("year"), "varde": x.get("value")})
        df = pd.DataFrame(rader)
        if len(df):   # bara riket, regioner och kommuner (inte jämförelsegrupper)
            df = df[df.region_kod.astype(str).str.fullmatch(r"\d{4}")].drop_duplicates(["region_kod", "ar"])
        df.to_csv(ut_dir / f"{kid}.csv.gz", index=False,
                                   compression={"method": "gzip", "mtime": 0})
        logg.setdefault("kolada", []).append({"id": kid, "namn": namn, "rader": len(df)})
        print(f"  {kid} {namn}: {len(df)} rader")


def hamta_riksbanken():
    from verklighet_katalog import RIKSBANKEN
    ut_dir = DATA_DIR / "riksbanken"
    ut_dir.mkdir(parents=True, exist_ok=True)
    for _, namn, serie, _ in RIKSBANKEN:
        try:
            r = http("GET", f"https://api.riksbank.se/swea/v1/Observations/{serie}/2000-01-01")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            df = pd.DataFrame(r.json())
            df.to_csv(ut_dir / f"{serie}.csv", index=False)
            print(f"  Riksbanken {serie}: {len(df)} observationer")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"riksbanken {serie}: {exc}")


# ---------- geodata ----------

GEO_DIR = DATA_DIR / "geo_ra"      # råfiler, ej i git (stora)


def _github_filer(repo: str, monster: str) -> list[str]:
    """Råfil-URL:er i ett publikt GitHub-repo vars sökväg matchar mönstret."""
    r = http("GET", f"https://api.github.com/repos/{repo}")
    if r.status_code != 200:
        return []
    gren = r.json().get("default_branch", "main")
    r = http("GET", f"https://api.github.com/repos/{repo}/git/trees/{gren}?recursive=1")
    if r.status_code != 200:
        return []
    return [f"https://raw.githubusercontent.com/{repo}/{gren}/{t['path']}"
            for t in r.json().get("tree", []) if re.search(monster, t["path"], re.I)]


def _hamta_alla(gid: str, urls: list[str], rapport: list[str]):
    """Hämta flera filer (t.ex. en per län), packa upp och slå ihop till en gpkg."""
    import zipfile
    import geopandas as gpd
    mapp = GEO_DIR / gid
    mapp.mkdir(parents=True, exist_ok=True)
    delar = []
    for i, u in enumerate(dict.fromkeys(urls)):
        try:
            r = http("GET", u)
            if r.status_code != 200:
                rapport.append(f"  {u}: HTTP {r.status_code}")
                continue
            fil = mapp / f"del{i:02d}{Path(u.split('?')[0]).suffix.lower()}"
            fil.write_bytes(r.content)
            if fil.suffix == ".zip":
                with zipfile.ZipFile(fil) as z:
                    z.extractall(mapp / f"del{i:02d}")
                lager = [q for q in (mapp / f"del{i:02d}").rglob("*")
                         if q.suffix.lower() in (".gpkg", ".geojson", ".json", ".shp")]
            else:
                lager = [fil]
            for q in lager[:1]:
                g = gpd.read_file(q)
                delar.append(g.to_crs(3006) if g.crs else g.set_crs(3006))
        except Exception as exc:  # noqa: BLE001
            rapport.append(f"  {u}: {exc}")
    if not delar:
        return
    alla = pd.concat(delar, ignore_index=True)
    ut = GEO_DIR / f"{gid}.gpkg"
    gpd.GeoDataFrame(alla, geometry="geometry", crs=3006).to_file(ut, driver="GPKG")
    (GEO_DIR / f"{gid}.las").write_text(str(ut), encoding="utf-8")
    rapport.append(f"  {len(delar)} filer, {len(alla)} objekt -> {ut.name}")


def hamta_geodata():
    """DeSO-gränser (SCB WFS) och valdistrikt 2026 (Valmyndigheten, med
    GitHub-kopior som reserv). Sammanfattning av filerna i katalog/geo.txt."""
    print("Geodata")
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    rapport = []
    for g in GEODATA:
        kandidater = list(g.get("url", []))
        if g.get("sida"):
            try:
                r = http("GET", g["sida"])
                for h in re.findall(r'href="([^"]+)"', r.text):
                    u = urljoin(g["sida"], h.replace("&amp;", "&"))
                    if re.search(g["lank"], u):
                        kandidater.insert(0, u)
            except Exception as exc:  # noqa: BLE001
                rapport.append(f"{g['id']}: sidfel {exc}")
        for repo, monster in g.get("github", []):
            try:
                kandidater += _github_filer(repo, monster)
            except Exception as exc:  # noqa: BLE001
                rapport.append(f"{g['id']}: github {repo} {exc}")
        rapport.append(f"{g['id']}: kandidater {kandidater}")
        if g.get("alla") and g.get("sida"):
            sidfiler = [u for u in kandidater if "val.se" in u]
            if sidfiler:
                _hamta_alla(g["id"], sidfiler, rapport)
                continue
        for u in kandidater:
            try:
                r = http("GET", u)
            except Exception as exc:  # noqa: BLE001
                rapport.append(f"  {u}: {exc}")
                continue
            if r.status_code != 200 or len(r.content) < 10_000:
                rapport.append(f"  {u}: HTTP {r.status_code}, {len(r.content)} byte")
                continue
            ext = Path(u.split("?")[0]).suffix.lower()
            if "geopackage" in u.lower():
                ext = ".gpkg"
            fil = GEO_DIR / f"{g['id']}{ext or '.bin'}"
            fil.write_bytes(r.content)
            rapport.append(f"  hämtad {u} -> {fil.name} ({len(r.content)} byte)")
            try:
                import geopandas as gpd
                if ext == ".zip":
                    import zipfile
                    with zipfile.ZipFile(fil) as z:
                        rapport.append(f"    zip: {z.namelist()[:20]}")
                        z.extractall(GEO_DIR / g["id"])
                    lager = [q for q in (GEO_DIR / g["id"]).rglob("*")
                             if q.suffix.lower() in (".gpkg", ".geojson", ".json", ".shp")]
                    las = lager[0] if lager else None
                else:
                    las = fil
                if las is not None:
                    gdf = gpd.read_file(las)
                    rapport.append(f"    {las.name}: {len(gdf)} objekt, crs {gdf.crs}, "
                                   f"kolumner {list(gdf.columns)}")
                    rapport.append("    " + gdf.drop(columns="geometry").head(3).to_string().replace("\n", "\n    "))
                    (GEO_DIR / f"{g['id']}.las").write_text(str(las), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                rapport.append(f"    kunde inte läsa: {exc}")
            break
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    (KAT_DIR / "geo.txt").write_text("\n".join(rapport), encoding="utf-8")
    print("\n".join(rapport)[:3000])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--steg", choices=["alla", "scb", "dokument", "geo", "verklighet"], default="alla")
    p.add_argument("--tema", help="bara ett SCB-tema (t.ex. psu)")
    p.add_argument("--tvinga", action="store_true", help="hämta allt, även oförändrat")
    a = p.parse_args()
    if a.steg in ("alla", "scb"):
        hamta_scb(a.tema, a.tvinga)
    if a.steg in ("alla", "dokument"):
        hamta_dokument(a.tvinga)
    if a.steg in ("alla", "verklighet"):
        hamta_kolada()
        hamta_riksbanken()
    if a.steg in ("alla", "geo"):
        hamta_geodata()
    logg["slut"] = datetime.now(timezone.utc).isoformat()
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    (KAT_DIR / "hamtlogg.json").write_text(
        json.dumps(logg, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
