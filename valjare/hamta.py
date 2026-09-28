#!/usr/bin/env python3
"""Väljardatabasen, steg 1: hämta rådata.

- SCB (PxWebApi v2): PSU (partisympati per grupp), valdeltagande, valresultat,
  befolkning, utbildning, inkomst, arbete, utsatthet för brott/trygghet.
  Varje tabell sparas i långt format som data/scb/<tabell-id>.csv.gz.
- Dokument (Valu, Valforskningsprogrammet): pdf laddas ned till
  data/kallor/pdf och textextraheras sida för sida till data/kallor/txt.
- Länksidor (Brå NTU, Valmyndigheten, GU): skrapas efter pdf/xlsx-länkar.
  Excelfiler sparas i data/kallor/xlsx med en översikt per flik i txt.
- Riksdagen (data.riksdagen.se): propositioner, betänkanden och voteringar
  (aggregerade per parti och per ledamot) till data/riksdagen.

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
    """bara: ett eller flera teman, kommaseparerade (None = alla)."""
    SCB_DIR.mkdir(parents=True, exist_ok=True)
    teman = set(bara.split(",")) if bara else None
    katalog: dict[str, dict] = {}
    for post in SCB_SOK:
        if teman and post["tema"] not in teman:
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
        if teman and post["tema"] not in teman:
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
    if teman and (KAT_DIR / "scb_katalog.csv").exists():
        # Behåll övriga teman i katalogen (bygg_db och cachen läser den)
        gammal = pd.read_csv(KAT_DIR / "scb_katalog.csv", dtype=str)
        kat_df = pd.concat([kat_df, gammal[~gammal["id"].isin(kat_df["id"])]], ignore_index=True)
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


def hamta_dokument(tvinga: bool = False, bara_sidor: set[str] | None = None):
    print("Dokument")
    for d in DOKUMENT if bara_sidor is None else []:
        logg["dokument"].append(ladda_ned(d["id"], d["url"], d["typ"], tvinga))
    print("Länksidor")
    sedda = {d["url"] for d in DOKUMENT}
    for s in LANKSIDOR:
        if bara_sidor is not None and s["id"] not in bara_sidor:
            continue
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
    for fraga, namn, sok, valj in KOLADA:
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
    for kid, (fraga, namn, titel) in valda.items():
        _kolada_data(kid, fraga, namn, titel, ut_dir)


def _kolada_data(kid: str, fraga: str, namn: str, titel: str, ut_dir: Path, fran: int = 2006):
    # Ett år i taget: varje år ryms på en sida (ca 312 områden), så sidindelningen spelar ingen roll.
    # Finns nyckeltalet redan hämtas bara de tre senaste åren om (äldre år revideras sällan).
    fil = ut_dir / f"{kid}.csv.gz"
    gammal = pd.DataFrame()
    if fil.exists():
        try:
            gammal = pd.read_csv(fil, dtype={"region_kod": str})
        except (pd.errors.EmptyDataError, ValueError):
            gammal = pd.DataFrame()
    if len(gammal) and "ar" in gammal:
        fran = max(fran, int(pd.to_numeric(gammal.ar, errors="coerce").max()) - 2)
    v = []
    for a in range(fran, datetime.now().year + 1):
        try:
            v += _kolada_alla("data", {"kpi_id": kid, "year": a})
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"kolada data {kid} {a}: {exc}")
    rader = []
    for rad in v:
        for x in rad.get("values", []):
            if str(x.get("gender", "T")).upper() in ("T", "TOTAL", "NONE", "") and x.get("value") is not None:
                rader.append({"kpi": kid, "titel": titel, "fraga": fraga, "namn": namn,
                              "region_kod": rad.get("municipality") or rad.get("municipality_id"),
                              "ar": rad.get("period") or rad.get("year"), "varde": x.get("value")})
    df = pd.DataFrame(rader)
    if len(df):   # bara riket, regioner och kommuner (inte jämförelsegrupper)
        df["region_kod"] = df.region_kod.astype(str).str.replace(r"\.0$", "", regex=True)
        df.loc[df.region_kod.str.fullmatch(r"\d{1,3}"), "region_kod"] = df.region_kod.str.zfill(4)
        df = df[df.region_kod.str.fullmatch(r"\d{4}")].drop_duplicates(["region_kod", "ar"])
    if len(gammal) and "ar" in gammal:
        gammal = gammal[pd.to_numeric(gammal.ar, errors="coerce") < fran]
        df = pd.concat([gammal, df], ignore_index=True)
    df.to_csv(fil, index=False, compression={"method": "gzip", "mtime": 0})
    logg.setdefault("kolada", []).append({"id": kid, "namn": namn, "rader": len(df)})
    print(f"  {kid} {namn}: {len(df)} rader")


def hamta_kolada_bred():
    """Hela Koladas nyckeltalskatalog, och de nyckeltal i indikatorer_katalog.KOLADA_BRED som matchar."""
    from indikatorer_katalog import KOLADA_BRED
    from verklighet_katalog import KOLADA
    print("Kolada, hela katalogen")
    try:
        alla = _kolada_alla("kpi", {})
    except Exception as exc:  # noqa: BLE001
        logg["fel"].append(f"kolada katalog: {exc}")
        return
    kat = pd.DataFrame([{"id": k.get("id"), "titel": k.get("title"), "kommuntyp": k.get("municipality_type"),
                         "omrade": k.get("operating_area"), "publicerad": k.get("publication_date"),
                         "enhetsdata": k.get("has_ou_data"), "beskrivning": (k.get("description") or "")[:300]}
                        for k in alla])
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    kat.to_csv(KAT_DIR / "kolada_alla_kpi.csv", index=False)
    print(f"  {len(kat)} nyckeltal i katalogen")
    redan = {k[2] for k in KOLADA}
    rang = {"A": 0, "K": 1, "L": 2}
    val, ut_dir = [], DATA_DIR / "kolada"
    ut_dir.mkdir(parents=True, exist_ok=True)
    for fraga, namn, monster, utesluta in KOLADA_BRED:
        k = kat[kat.titel.fillna("").str.contains(monster, regex=True)]
        if utesluta:
            k = k[~k.titel.str.contains(utesluta, regex=True)]
        if k.empty:
            val.append({"fraga": fraga, "namn": namn, "id": None, "titel": None, "alternativ": 0})
            continue
        k = k.assign(r=k.kommuntyp.map(rang).fillna(3), n=k.titel.str.len()).sort_values(["r", "n"])
        vald = k.iloc[0]
        val.append({"fraga": fraga, "namn": namn, "id": vald.id, "titel": vald.titel, "alternativ": len(k),
                    "ovriga": " | ".join(f"{a}: {b}" for a, b in zip(k.id[1:6], k.titel[1:6]))})
        if vald.id in redan:
            continue
        redan.add(vald.id)
        _kolada_data(vald.id, fraga, namn, vald.titel, ut_dir, fran=2010)
    pd.DataFrame(val).to_csv(KAT_DIR / "kolada_bred_val.csv", index=False)
    print(f"  {sum(1 for v in val if v['id'])} av {len(val)} poster hittade")


def hamta_varldsbanken():
    from verklighet_katalog import VARLDSBANKEN
    ut_dir = DATA_DIR / "varldsbanken"
    ut_dir.mkdir(parents=True, exist_ok=True)
    for _, namn, kod in VARLDSBANKEN:
        try:
            r = http("GET", f"https://api.worldbank.org/v2/country/SWE/indicator/{kod}",
                     params={"format": "json", "per_page": 200})
            j = r.json()
            rader = [{"ar": int(x["date"]), "varde": x["value"]} for x in (j[1] if len(j) > 1 and j[1] else [])
                     if x.get("value") is not None]
            pd.DataFrame(rader).to_csv(ut_dir / f"{kod}.csv", index=False)
            print(f"  Världsbanken {kod}: {len(rader)} år")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"världsbanken {kod}: {exc}")


def hamta_riksbanken():
    from verklighet_katalog import RIKSBANKEN
    ut_dir = DATA_DIR / "riksbanken"
    ut_dir.mkdir(parents=True, exist_ok=True)
    for _, namn, serie in RIKSBANKEN:
        try:
            r = http("GET", f"https://api.riksbank.se/swea/v1/Observations/{serie}/2000-01-01")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            df = pd.DataFrame(r.json())
            df.to_csv(ut_dir / f"{serie}.csv", index=False)
            print(f"  Riksbanken {serie}: {len(df)} observationer")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"riksbanken {serie}: {exc}")


# ---------- Eurostat (nordisk jämförelse) ----------

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


def hamta_eurostat():
    from omraden import EUROSTAT, LANDER
    ut_dir = DATA_DIR / "eurostat"
    ut_dir.mkdir(parents=True, exist_ok=True)
    for sid, ds, filt, namn, _ in EUROSTAT:
        par = [("format", "JSON"), ("lang", "en"), ("sinceTimePeriod", "2000")]
        par += [("geo", g) for g in LANDER] + list(filt.items())
        try:
            r = http("GET", f"{EUROSTAT_API}/{ds}", params=par)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            df = jsonstat_till_df(r.json()).dropna(subset=["varde"])
            # Dimensioner som inte låsts: välj totalvärdet, annars första värdet (loggas)
            for d in [c for c in df.columns if c.endswith("_kod") and c[:-4] not in ("geo", "time", "freq")]:
                koder = list(dict.fromkeys(df[d]))
                if len(koder) > 1:
                    val = next((k for k in koder if k in ("T", "TOTAL", "TOT", "TOT_X_EXT")), koder[0])
                    logg["fel"].append(f"eurostat {sid}: {d[:-4]} ej låst, valde {val} av {koder[:6]}")
                    df = df[df[d] == val]
            ut = pd.DataFrame({"geo": df["geo_kod"], "tid": df["time_kod"], "varde": df["varde"]})
            ut.to_csv(ut_dir / f"{sid}.csv", index=False)
            logg.setdefault("eurostat", []).append({"id": sid, "dataset": ds, "rader": len(ut)})
            print(f"  Eurostat {sid} ({ds}): {len(ut)} rader")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"eurostat {sid} {ds}: {exc}")
            print(f"  Eurostat {sid}: fel {exc}")


# ---------- Genomslag: Wikidata, nyhetsflöden, annonser ----------

MEDIA_DIR = DATA_DIR / "media"


def _wd_hitta(sida: str) -> str | None:
    """Wikipedia-artikel (språk:titel) -> Wikidata-objekt, via Special:ItemByTitle (ingen API)."""
    sprak, titel = sida.split(":", 1)
    r = http("GET", f"https://www.wikidata.org/wiki/Special:ItemByTitle/{sprak}wiki/{titel.replace(' ', '_')}",
             allow_redirects=True)
    m = re.search(r"/wiki/(Q\d+)", r.url) or re.search(r'"wgPageName":"(Q\d+)"', r.text)
    return m[1] if m else None


def _wd_entitet(qid: str) -> dict:
    r = http("GET", f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
    return r.json()["entities"][qid]


def _wd_etikett(ent: dict) -> str:
    lab = ent.get("labels", {})
    return (lab.get("sv") or lab.get("en") or {}).get("value", ent.get("id", ""))


def wd_foljare(ent: dict) -> list[dict]:
    """Alla daterade följarantal (P8687) med plattform och konto."""
    from media_katalog import PLATTFORM
    ut = []
    for st in ent.get("claims", {}).get("P8687", []):
        v = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if not isinstance(v, dict) or "amount" not in v:
            continue
        q = st.get("qualifiers", {})
        tid = next((x["datavalue"]["value"]["time"] for x in q.get("P585", []) if "datavalue" in x), None)
        plattform, konto = "okänd", None
        for prop, namn in PLATTFORM.items():
            if prop in q:
                plattform = namn
                konto = next((str(x["datavalue"]["value"]) for x in q[prop] if "datavalue" in x), None)
                break
        ut.append({"plattform": plattform, "konto": konto, "datum": tid[1:11] if tid else None,
                   "foljare": float(v["amount"]), "rang": st.get("rank")})
    return ut


def wd_ordforande(ent: dict) -> list[str]:
    """Nuvarande ordförande/partiledare (P488 utan slutdatum), senast tillträdd först."""
    kand = []
    for st in ent.get("claims", {}).get("P488", []):
        q = st.get("qualifiers", {})
        if "P582" in q:
            continue
        v = st.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        start = next((x["datavalue"]["value"]["time"] for x in q.get("P580", []) if "datavalue" in x), "")
        if isinstance(v, dict) and v.get("id"):
            kand.append((start, v["id"]))
    return [q for _, q in sorted(kand, reverse=True)]


def hamta_wikidata():
    from media_katalog import PARTI_WIKI
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    rader, objekt = [], []
    for parti, sidor in PARTI_WIKI.items():
        try:
            qid = next((q for q in (_wd_hitta(x) for x in sidor) if q), None)
            if not qid:
                logg["fel"].append(f"wikidata {parti}: hittade inget objekt")
                continue
            ent = _wd_entitet(qid)
            land = [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
                    for c in ent.get("claims", {}).get("P17", [])]
            if "Q34" not in land:   # Sverige
                logg["fel"].append(f"wikidata {parti}: {qid} är inte ett svenskt objekt ({land})")
                continue
            objekt.append({"parti": parti, "roll": "parti", "qid": qid, "namn": _wd_etikett(ent)})
            rader += [{"parti": parti, "roll": "parti", "qid": qid, "namn": _wd_etikett(ent), **f}
                      for f in wd_foljare(ent)]
            for lq in wd_ordforande(ent)[:1]:
                le = _wd_entitet(lq)
                objekt.append({"parti": parti, "roll": "partiledare", "qid": lq, "namn": _wd_etikett(le)})
                rader += [{"parti": parti, "roll": "partiledare", "qid": lq, "namn": _wd_etikett(le), **f}
                          for f in wd_foljare(le)]
            print(f"  Wikidata {parti}: {qid}, {sum(1 for r in rader if r['parti'] == parti)} följarvärden")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"wikidata {parti}: {exc}")
    pd.DataFrame(rader).to_csv(MEDIA_DIR / "foljare.csv", index=False)
    pd.DataFrame(objekt).to_csv(MEDIA_DIR / "wikidata_objekt.csv", index=False)


def las_flode(xml: str) -> list[dict]:
    """RSS 2.0 eller Atom -> titel, beskrivning, länk, publicerad, källa."""
    import xml.etree.ElementTree as ET
    rot = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    ut = []
    for it in rot.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        barn = {c.tag.split("}")[-1]: c for c in it}
        text = lambda k: (barn[k].text or "").strip() if k in barn and barn[k].text else ""  # noqa: E731
        lank = text("link") or (barn["link"].get("href", "") if "link" in barn else "")
        ut.append({"titel": text("title"),
                   "beskrivning": re.sub(r"<[^>]+>", " ", text("description") or text("summary"))[:400],
                   "lank": lank, "publicerad": text("pubDate") or text("published") or text("updated"),
                   "kalla_namn": text("source")})
    return ut


def hamta_rss():
    from urllib.parse import quote

    from media_katalog import FLODEN, GOOGLE_NYHETER, GOOGLE_SOK
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    f = MEDIA_DIR / "artiklar.csv.gz"
    gamla = pd.read_csv(f, dtype=str) if f.exists() else pd.DataFrame()
    nu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    nya = []
    kallor = [(namn, url, None) for namn, url in FLODEN] + \
             [("Google Nyheter", GOOGLE_NYHETER.format(q=quote(q)), p) for p, q in GOOGLE_SOK.items()]
    for namn, url, parti in kallor:
        try:
            r = http("GET", url)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            art = las_flode(r.content)
            nya += [{**a, "flode": namn, "sokt_parti": parti, "hamtad": nu} for a in art]
            print(f"  RSS {namn}{' ' + parti if parti else ''}: {len(art)} artiklar")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"rss {namn} {parti or ''}: {exc}")
    d = pd.concat([gamla, pd.DataFrame(nya, dtype=str)], ignore_index=True)
    if len(d):
        # Samma artikel kan komma i flera flöden och vid flera hämtningar: behåll första
        d = d.drop_duplicates(["flode", "sokt_parti", "lank"], keep="first")
        d.to_csv(f, index=False, compression={"method": "gzip", "mtime": 0})
    print(f"  RSS: {len(nya)} hämtade, {len(d)} artiklar totalt")


def hamta_google_annonser():
    """Googles öppna paket med politiska annonser: bara svenska partiers annonsörer sparas."""
    import tempfile
    import zipfile

    from media_katalog import ANNONSOR, GOOGLE_ANNONSER
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    monster = "|".join(f"(?:{x[4:]})" for x in ANNONSOR.values())
    try:
        with tempfile.TemporaryFile() as tmp:
            with session.get(GOOGLE_ANNONSER, stream=True, timeout=600) as r:
                r.raise_for_status()
                for bit in r.iter_content(1 << 20):
                    tmp.write(bit)
            tmp.seek(0)
            with zipfile.ZipFile(tmp) as z:
                for namn in z.namelist():
                    if not re.search(r"advertiser-(weekly-spend|stats)\.csv$", namn):
                        continue
                    delar = []
                    with z.open(namn) as fil:
                        for bit in pd.read_csv(fil, dtype=str, chunksize=200_000):
                            kol = next((c for c in bit.columns if re.search(r"(?i)advertiser_name", c)), None)
                            if kol:
                                delar.append(bit[bit[kol].str.contains(monster, case=False, regex=True, na=False)])
                    ut = pd.concat(delar) if delar else pd.DataFrame()
                    mal = MEDIA_DIR / ("google_annonser_vecka.csv" if "weekly" in namn else "google_annonsorer.csv")
                    ut.to_csv(mal, index=False)
                    print(f"  Google-annonser {namn}: {len(ut)} rader")
    except Exception as exc:  # noqa: BLE001
        logg["fel"].append(f"google annonser: {exc}")


def hamta_anforanden(tvinga: bool = False):
    """Riksdagens anföranden (bulkfiler): antal och ord per parti, riksmöte och typ av debatt."""
    import io
    import json as js
    import zipfile
    ut = DATA_DIR / "riksdagen"
    ut.mkdir(parents=True, exist_ok=True)
    rmlista = _riksmoten()
    for i, rm in enumerate(rmlista):
        kort = rm.replace("/", "")
        f = ut / f"anforande_{kort}.csv.gz"
        if f.exists() and not tvinga and i < len(rmlista) - 2:
            continue
        kandidater = [f"{RD_API}/dataset/anforande/anforande-{kort}.json.zip"]
        try:
            sida = http("GET", f"{RD_API}/data/anforanden/").text
            kandidater += [urljoin(f"{RD_API}/data/anforanden/", h) for h in re.findall(r'href="([^"]+)"', sida)
                           if re.search(rf"anforande-{kort}\.json\.zip", h)]
        except Exception:  # noqa: BLE001
            pass
        rader = None
        for u in dict.fromkeys(kandidater):
            try:
                r = http("GET", u)
                if r.status_code != 200 or r.content[:2] != b"PK":
                    continue
                rader = []
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    for namn in z.namelist():
                        if not namn.lower().endswith(".json"):
                            continue
                        a = js.loads(z.read(namn).decode("utf-8-sig")).get("anforande", {})
                        text = re.sub(r"<[^>]+>", " ", a.get("anforandetext") or "")
                        rader.append({"parti": (a.get("parti") or "").upper(), "datum": (a.get("dok_datum") or "")[:10],
                                      "typ": a.get("kammaraktivitet") or "", "replik": a.get("replik") or "",
                                      "ord": len(text.split()), "intressent_id": a.get("intressent_id")})
                break
            except Exception as exc:  # noqa: BLE001
                logg["fel"].append(f"riksdagen anföranden {rm} {u}: {exc}")
        if not rader:
            continue
        d = pd.DataFrame(rader)
        d["manad"] = d.datum.str[:7]
        agg = d.groupby(["manad", "parti", "typ", "replik"]).agg(
            anforanden=("ord", "size"), ord=("ord", "sum"), talare=("intressent_id", "nunique")).reset_index()
        agg.insert(0, "rm", rm)
        agg.to_csv(f, index=False, compression={"method": "gzip", "mtime": 0})
        print(f"  riksdagen anföranden {rm}: {len(d)}")


# ---------- Riksdagen (data.riksdagen.se) ----------

RD_API = "https://data.riksdagen.se"
RD_FORSTA = 2014   # riksmöte 2014/15, början av mandatperioden 2014–2018


def _riksmoten() -> list[str]:
    nu = datetime.now(timezone.utc)
    sista = nu.year if nu.month >= 9 else nu.year - 1
    return [f"{a}/{str(a + 1)[2:]}" for a in range(RD_FORSTA, sista + 1)]


def _rd_dokument(doktyp: str, rm: str) -> pd.DataFrame:
    """Alla dokument av en typ under ett riksmöte (dokumentlistan, sida för sida)."""
    url, par, rader, sidor = f"{RD_API}/dokumentlista/", {
        "doktyp": doktyp, "rm": rm, "utformat": "json", "sz": 500, "sort": "datum", "sortorder": "asc"}, [], 0
    while url and sidor < 40:
        j = http("GET", url, params=par).json().get("dokumentlista", {})
        dok = j.get("dokument") or []
        rader += dok if isinstance(dok, list) else [dok]
        url, par, sidor = j.get("@nasta_sida"), None, sidor + 1
    falt = ["dok_id", "rm", "beteckning", "doktyp", "typ", "subtyp", "organ", "titel", "undertitel",
            "datum", "dokument_url_html"]
    return pd.DataFrame([{f: r.get(f) for f in falt} for r in rader]).drop_duplicates("dok_id") \
        if rader else pd.DataFrame(columns=falt)


def _rd_voteringar(rm: str) -> pd.DataFrame | None:
    """Voteringarna per ledamot för ett riksmöte: bulkfilen, annars API:t (csv)."""
    import io
    import zipfile
    kort = rm.replace("/", "")
    kandidater = [f"{RD_API}/dataset/votering/votering-{kort}.csv.zip"]
    try:
        sida = http("GET", f"{RD_API}/data/voteringar/").text
        kandidater += [urljoin(f"{RD_API}/data/voteringar/", h) for h in re.findall(r'href="([^"]+)"', sida)
                       if re.search(rf"votering-{kort}\.csv\.zip", h)]
    except Exception:  # noqa: BLE001
        pass
    for u in dict.fromkeys(kandidater):
        try:
            r = http("GET", u)
            if r.status_code != 200 or not r.content[:2] == b"PK":
                continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                namn = next(n for n in z.namelist() if n.lower().endswith(".csv"))
                with z.open(namn) as f:
                    return pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"riksdagen votering {rm} {u}: {exc}")
    try:
        r = http("GET", f"{RD_API}/voteringlista/", params={"rm": rm, "sz": 1_000_000, "utformat": "csv"})
        if r.status_code == 200 and len(r.content) > 1000:
            return pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), dtype=str)
    except Exception as exc:  # noqa: BLE001
        logg["fel"].append(f"riksdagen voteringlista {rm}: {exc}")
    return None


def _rd_kolumner(v: pd.DataFrame) -> pd.DataFrame:
    """Bulkfilerna saknar ibland rubrikrad. Då blir första raden kolumnnamn; läs tillbaka
    den som data och känn igen kolumnerna på innehållet."""
    if "rost" in [str(c).lower() for c in v.columns]:
        return v.rename(columns=str.lower)
    forsta = pd.DataFrame([[re.sub(r"\.\d+$", "", str(c)) for c in v.columns]], columns=range(v.shape[1]))
    v = pd.concat([forsta, v.set_axis(range(v.shape[1]), axis=1)], ignore_index=True).astype(str)
    prov = v.head(2000)
    test = {
        "rost": lambda x: x.isin(["Ja", "Nej", "Avstår", "Frånvarande"]).mean() > 0.9,
        "avser": lambda x: x.str.contains("sakfrågan|motivreservation", regex=True).mean() > 0.9,
        "rm": lambda x: x.str.fullmatch(r"\d{4}/\d{2}").mean() > 0.9,
        "votering_id": lambda x: x.str.fullmatch(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f-]{27}").mean() > 0.9,
        "datum": lambda x: x.str.match(r"\d{4}-\d{2}-\d{2}").mean() > 0.9,
        "parti": lambda x: x.isin(["S", "M", "SD", "C", "V", "KD", "L", "MP", "FP", "-"]).mean() > 0.9,
        "valkrets": lambda x: x.str.contains("län|kommun|Gotland", regex=True).mean() > 0.9,
        "beteckning": lambda x: x.str.fullmatch(r"[A-ZÅÄÖ][A-Za-zåäö]*\d+").mean() > 0.9,
        "kon": lambda x: x.isin(["man", "kvinna"]).mean() > 0.9,
        "fodd": lambda x: x.str.fullmatch(r"19\d\d|20\d\d").mean() > 0.9,
        "intressent_id": lambda x: x.str.fullmatch(r"\d{9,}").mean() > 0.9,
        "namn": lambda x: x.str.fullmatch(r"[^\d]+ [^\d]+").mean() > 0.9,
    }
    namn = {}
    for c in prov.columns:
        for k, f in test.items():
            if k not in namn.values() and f(prov[c]):
                namn[c] = k
                break
    if "votering_id" in namn.values():   # punkten står direkt efter voterings-id
        i = next(c for c, k in namn.items() if k == "votering_id")
        if i + 1 in prov.columns and i + 1 not in namn:
            namn[i + 1] = "punkt"
    return v.rename(columns=namn)


def _rd_aggregera(v: pd.DataFrame, rm: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per votering och parti respektive per ledamot: antal ja, nej, avstår, frånvarande."""
    v = _rd_kolumner(v)
    rost = v["rost"].str.lower().str.strip().map(
        {"ja": "ja", "nej": "nej", "avstår": "avstar", "frånvarande": "franvarande"})
    v = v.assign(r=rost).dropna(subset=["r"])
    nycklar = [c for c in ("rm", "beteckning", "punkt", "votering_id", "avser", "votering", "datum")
               if c in v.columns]
    per_parti = v.groupby(nycklar + ["parti", "r"], dropna=False).size().unstack(fill_value=0).reset_index()
    led = [c for c in ("intressent_id", "namn", "fornamn", "efternamn", "parti", "valkrets", "kon", "fodd")
           if c in v.columns]
    per_led = v.groupby(led + ["r"], dropna=False).size().unstack(fill_value=0).reset_index().assign(rm=rm)
    return per_parti, per_led


def hamta_riksdagen(tvinga: bool = False):
    """Propositioner, betänkanden, voteringar (aggregerade) och propositionernas betänkanden."""
    ut = DATA_DIR / "riksdagen"
    ut.mkdir(parents=True, exist_ok=True)
    rmlista = _riksmoten()
    for i, rm in enumerate(rmlista):
        kort = rm.replace("/", "")
        farsk = tvinga or i >= len(rmlista) - 2   # de två senaste riksmötena hämtas alltid
        for doktyp in ("prop", "bet"):
            f = ut / f"{doktyp}_{kort}.csv"
            if f.exists() and not farsk:
                continue
            try:
                d = _rd_dokument(doktyp, rm)
                d.to_csv(f, index=False)
                print(f"  riksdagen {doktyp} {rm}: {len(d)}")
            except Exception as exc:  # noqa: BLE001
                logg["fel"].append(f"riksdagen {doktyp} {rm}: {exc}")
        f = ut / f"votering_{kort}.csv.gz"
        if f.exists() and not farsk:
            continue
        v = _rd_voteringar(rm)
        if v is None or v.empty:
            print(f"  riksdagen voteringar {rm}: inga")
            continue
        try:
            pp, pl = _rd_aggregera(v, rm)
            pp.to_csv(f, index=False, compression={"method": "gzip", "mtime": 0})
            pl.to_csv(ut / f"ledamot_{kort}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
            print(f"  riksdagen voteringar {rm}: {len(v)} röster, {pp.votering_id.nunique()} voteringar")
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"riksdagen aggregera {rm}: {exc} ({list(v.columns)[:25]})")
    # Propositionernas betänkanden (dokumentstatus), bara de som saknas
    f = ut / "prop_bet.csv"
    gamla = pd.read_csv(f, dtype=str) if f.exists() else pd.DataFrame(columns=["prop_id", "bet_rm", "bet"])
    klara = set(gamla.prop_id)
    props = pd.concat([pd.read_csv(x, dtype=str) for x in sorted(ut.glob("prop_*.csv"))
                       if x.stat().st_size > 50], ignore_index=True)
    nya = []
    for pid, rm in zip(props.dok_id, props.rm):
        # Bara mandatperioderna från 2018 används i kopplingen till opinionen
        if pid in klara or not isinstance(pid, str) or str(rm)[:4] < "2018":
            continue
        try:
            j = http("GET", f"{RD_API}/dokumentstatus/{pid}.json").json().get("dokumentstatus", {})
            ref = (j.get("dokreferens") or {}).get("referens") or []
            ref = ref if isinstance(ref, list) else [ref]
            bet = [(r.get("ref_dok_rm") or rm, r.get("ref_dok_bet")) for r in ref
                   if (r.get("ref_dok_typ") or "").lower() == "bet" and r.get("ref_dok_bet")]
            nya += [{"prop_id": pid, "bet_rm": a, "bet": b} for a, b in dict.fromkeys(bet)] or \
                   [{"prop_id": pid, "bet_rm": None, "bet": None}]
        except Exception as exc:  # noqa: BLE001
            logg["fel"].append(f"riksdagen dokumentstatus {pid}: {exc}")
        if len(nya) and len(nya) % 200 == 0:
            pd.concat([gamla, pd.DataFrame(nya)]).to_csv(f, index=False)
    pd.concat([gamla, pd.DataFrame(nya, columns=["prop_id", "bet_rm", "bet"])]).to_csv(f, index=False)
    print(f"  riksdagen: {len(nya)} nya kopplingar proposition → betänkande")


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
    p.add_argument("--steg", choices=["alla", "scb", "dokument", "geo", "verklighet", "vecka", "riksdagen", "media"],
                   default="alla",
                   help="vecka = bara månadsserierna till lägesbilden (SCB, Polisen, Riksbanken)")
    p.add_argument("--tema", help="bara ett SCB-tema (t.ex. psu)")
    p.add_argument("--tvinga", action="store_true", help="hämta allt, även oförändrat")
    a = p.parse_args()
    if a.steg in ("alla", "scb"):
        hamta_scb(a.tema, a.tvinga)
    if a.steg in ("alla", "dokument"):
        hamta_dokument(a.tvinga)
    if a.steg in ("alla", "verklighet"):
        hamta_kolada()
        hamta_kolada_bred()
        hamta_riksbanken()
        hamta_varldsbanken()
        hamta_eurostat()
    if a.steg in ("alla", "geo"):
        hamta_geodata()
    if a.steg in ("alla", "riksdagen", "vecka"):
        hamta_riksdagen(a.tvinga)
        hamta_anforanden(a.tvinga)
    if a.steg in ("alla", "vecka", "media"):
        hamta_wikidata()
        hamta_rss()
    if a.steg == "alla":
        hamta_google_annonser()
    if a.steg == "vecka":
        hamta_scb("manad,priser", a.tvinga)
        hamta_dokument(a.tvinga, bara_sidor={"polisen"})
        hamta_riksbanken()
    logg["slut"] = datetime.now(timezone.utc).isoformat()
    KAT_DIR.mkdir(parents=True, exist_ok=True)
    (KAT_DIR / "hamtlogg.json").write_text(
        json.dumps(logg, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
