#!/usr/bin/env python3
"""Bostadsarkivet: hämtar källmaterial om bostadsbyggandet 1990–i dag.

Källor
- Riksdagens protokoll (data.riksdagen.se): alla kammarprotokoll hämtas,
  delas upp i anföranden och de anföranden som rör bostadsbyggandet sparas
  med talare, parti, datum och ärende.
- SOU, Ds och kommittédirektiv (data.riksdagen.se): kandidater hittas med
  riksdagens sökmotor (katalog.SOKFRAGOR), fulltexten hämtas och bedöms.
  Riksdagen har SOU från 1997.
- SOU 1990–1999 från Kungliga biblioteket (sou.kb.se): inskannade PDF:er med
  OCR-text. Alla som saknas hos riksdagen hämtas och bedöms, eftersom KB
  inte har någon fulltextsökning.

Hämtningen är inkrementell: det som redan finns i data/protokoll.csv och
data/dokument.csv hämtas inte igen (utom --om).

    python hamta.py alla
    python hamta.py protokoll --fran 2024
    python hamta.py riksdagsdok --typ sou
    python hamta.py kb
"""

import argparse
import csv
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import requests

import katalog
import text

BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "data"
TEXT_DIR = DATA / "text"
ANF_DIR = DATA / "anforanden"
PROT_CSV = DATA / "protokoll.csv"
DOK_CSV = DATA / "dokument.csv"
LOGG = DATA / "hamtlogg.json"

RD = "https://data.riksdagen.se"
KB_INDEX = "https://sou.kb.se/"

PROT_FALT = ["dok_id", "rm", "nummer", "datum", "titel", "anforanden", "relevanta", "hamtad"]
DOK_FALT = ["id", "kalla", "doktyp", "beteckning", "rm", "nummer", "datum", "titel", "organ",
            "url", "pdf_url", "ord", "karna", "bred", "karntermer", "bredtermer",
            "titeltraff", "relevant", "grad", "textfil", "hamtad"]

_lokal = threading.local()
logg = {"start": datetime.now().isoformat(timespec="seconds"), "fel": [], "antal": {}}


def session():
    s = getattr(_lokal, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = "bostadsarkivet/1.0 (forskning; github.com/claesludvig/projekt)"
        _lokal.s = s
    return s


def hamta_url(url, forsok=5, **kw):
    for i in range(forsok):
        try:
            r = session().get(url, timeout=kw.pop("timeout", 120), **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            fel = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            fel = str(e)[:200]
        time.sleep(3 * 2 ** i)
    raise RuntimeError(f"{url}: {fel}")


def notera_fel(vad, e):
    print(f"  FEL {vad}: {e}", flush=True)
    logg["fel"].append({"vad": vad, "fel": str(e)[:300]})


# --- CSV-tillstånd -------------------------------------------------------------

def las_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class CsvSkrivare:
    """Lägger till rader direkt, så att ett avbrott inte förlorar något."""

    def __init__(self, p, falt):
        ny = not p.exists()
        p.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(p, "a", encoding="utf-8", newline="")
        self.w = csv.DictWriter(self.f, fieldnames=falt, extrasaction="ignore")
        if ny:
            self.w.writeheader()

    def skriv(self, rad):
        self.w.writerow(rad)
        self.f.flush()

    def stang(self):
        self.f.close()


def ta_bort_rader(p, nycklar, faltnamn):
    rader = [r for r in las_csv(p) if r[faltnamn] not in nycklar]
    falt = PROT_FALT if p == PROT_CSV else DOK_FALT
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=falt, extrasaction="ignore")
        w.writeheader()
        w.writerows(rader)


def skriv_text(relsokvag, innehall):
    p = DATA / relsokvag
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(innehall)


def filnamn(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")


# --- Riksdagens dokumentlista -----------------------------------------------------

def dokumentlista(**param):
    """Alla träffar i riksdagens dokumentlista, sida för sida."""
    param = {"utformat": "json", "sz": 500, "sort": "datum", "sortorder": "asc", **param}
    ut, sida = [], 1
    while True:
        r = hamta_url(f"{RD}/dokumentlista/", params={**param, "p": sida})
        d = r.json()["dokumentlista"]
        ut.extend(d.get("dokument") or [])
        if sida >= int(d.get("@sidor") or 1):
            return ut
        sida += 1


def rd_text(dok_id):
    r = hamta_url(f"{RD}/dokument/{dok_id}.html", timeout=300)
    if r is None:
        return ""
    r.encoding = "utf-8"
    return text.html_till_text(r.text)


# --- Protokoll ------------------------------------------------------------------

def rm_fil(rm):
    return ANF_DIR / f"{rm.replace('/', '-')}.jsonl.gz"


def bearbeta_protokoll(dok):
    t = rd_text(dok["dok_id"])
    anf = text.dela_protokoll(t)
    if not anf:
        # Bilagor till protokollen (skriftliga svar, frågor) saknar anföranden;
        # då bedöms varje avsnitt för sig. Numren 1000+ skiljer dem från anföranden.
        anf = [{"nr": 1000 + i, "talare": "", "parti": "", "replik": False,
                "rubrik": rub, "text": txt}
               for i, (rub, txt) in enumerate(text.dela_avsnitt_rubrik(t), 1)]
    rel = []
    for a in anf:
        karna, bred = text.rakna(a["text"])
        if not (text.anforande_relevant(karna, bred) or text.titeltraff(a["rubrik"])):
            continue
        rel.append({
            "prot_id": dok["dok_id"], "rm": dok["rm"], "prot_nr": dok["beteckning"],
            "datum": dok["datum"][:10], "anf_nr": a["nr"], "talare": a["talare"],
            "parti": a["parti"], "replik": a["replik"], "rubrik": a["rubrik"],
            "karna": sum(karna.values()), "bred": sum(bred.values()),
            "karntermer": text.termstrang(karna), "bredtermer": text.termstrang(bred),
            "grad": text.anforande_grad(karna), "ord": text.antal_ord(a["text"]),
            "url": f"https://www.riksdagen.se/sv/dokument-och-lagar/dokument/protokoll/_{dok['dok_id']}",
            "text": a["text"],
        })
    return dok, len(anf), rel, len(t)


def hamta_protokoll(fran, till, arbetare, om=False, grans=None, tomma=False):
    tidigare = las_csv(PROT_CSV)
    klara = {r["dok_id"] for r in tidigare}
    if tomma:
        # Protokoll där inga anföranden hittades görs om (t.ex. efter ändrad tolkning).
        omg = {r["dok_id"] for r in tidigare if r["anforanden"] == "0"}
        if omg:
            ta_bort_rader(PROT_CSV, omg, "dok_id")
            rensa_anforanden(omg)
            klara -= omg
    lista = []
    for ar in range(fran, till + 1):
        d = dokumentlista(doktyp="prot", **{"from": f"{ar}-01-01", "tom": f"{ar}-12-31"})
        lista.extend(d)
        print(f"Protokoll {ar}: {len(d)}", flush=True)
    sedda, unika = set(), []
    for d in lista:
        if d["dok_id"] not in sedda:
            sedda.add(d["dok_id"])
            unika.append(d)
    if om:
        omg = {d["dok_id"] for d in unika} & klara
        if omg:
            ta_bort_rader(PROT_CSV, omg, "dok_id")
            rensa_anforanden(omg)
            klara -= omg
    att_gora = [d for d in unika if d["dok_id"] not in klara]
    if grans:
        att_gora = att_gora[:grans]
    print(f"Protokoll att hämta: {len(att_gora)} av {len(unika)}", flush=True)

    skr = CsvSkrivare(PROT_CSV, PROT_FALT)
    filer = {}
    n_rel = n_fel = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(arbetare) as ex:
            fut = {ex.submit(bearbeta_protokoll, d): d for d in att_gora}
            for i, f in enumerate(as_completed(fut), 1):
                d = fut[f]
                try:
                    dok, n_anf, rel, n_tecken = f.result()
                except Exception as e:
                    n_fel += 1
                    notera_fel(f"protokoll {d['dok_id']}", e)
                    continue
                if rel:
                    fh = filer.get(dok["rm"])
                    if fh is None:
                        ANF_DIR.mkdir(parents=True, exist_ok=True)
                        fh = filer[dok["rm"]] = gzip.open(rm_fil(dok["rm"]), "at", encoding="utf-8")
                    for a in rel:
                        fh.write(json.dumps(a, ensure_ascii=False) + "\n")
                    fh.flush()
                n_rel += len(rel)
                skr.skriv({"dok_id": dok["dok_id"], "rm": dok["rm"], "nummer": dok["beteckning"],
                           "datum": dok["datum"][:10], "titel": dok["titel"], "anforanden": n_anf,
                           "relevanta": len(rel), "hamtad": date.today().isoformat()})
                if i % 50 == 0 or i == len(att_gora):
                    takt = i / max(time.time() - t0, 1)
                    print(f"  {i}/{len(att_gora)} protokoll, {n_rel} relevanta anföranden, "
                          f"{n_fel} fel, {takt:.1f}/s", flush=True)
    finally:
        skr.stang()
        for fh in filer.values():
            fh.close()
    logg["antal"]["protokoll"] = {"hamtade": len(att_gora) - n_fel, "relevanta_anforanden": n_rel, "fel": n_fel}


def rensa_anforanden(prot_ids):
    for p in ANF_DIR.glob("*.jsonl.gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            rader = [r for r in f if json.loads(r)["prot_id"] not in prot_ids]
        with gzip.open(p, "wt", encoding="utf-8") as f:
            f.writelines(rader)


# --- SOU, Ds, direktiv från riksdagen -------------------------------------------

def beteckning(doktyp, rm, nr):
    pref = {"sou": "SOU", "ds": "Ds", "dir": "Dir."}[doktyp]
    return f"{pref} {rm}:{nr}"


def bedom_dokument(meta, t, kalla):
    karna, bred = text.rakna(t)
    ord_ = text.antal_ord(t)
    tt = text.titeltraff(meta["titel"])
    rel = text.dokument_relevant(karna, ord_, tt)
    rad = {**meta, "kalla": kalla, "ord": ord_, "karna": sum(karna.values()),
           "bred": sum(bred.values()), "karntermer": text.termstrang(karna),
           "bredtermer": text.termstrang(bred), "titeltraff": int(tt), "relevant": int(rel),
           "grad": text.grad(karna, ord_, tt) if rel else "", "textfil": "",
           "hamtad": date.today().isoformat()}
    if rel and t.strip():
        rad["textfil"] = f"text/{meta['doktyp']}/{filnamn(meta['id'])}.txt.gz"
        huvud = (f"{rad['beteckning']}\n{rad['titel']}\nKälla: {rad['url']}\n"
                 f"Datum: {rad['datum']}\n\n")
        skriv_text(rad["textfil"], huvud + t)
    return rad


def bearbeta_rd_dokument(d):
    meta = {"id": d["dok_id"], "doktyp": d["doktyp"],
            "beteckning": beteckning(d["doktyp"], d["rm"], d["beteckning"]),
            "rm": d["rm"], "nummer": d["beteckning"], "datum": d["datum"][:10],
            "titel": " ".join(x for x in [d.get("titel"), d.get("undertitel")] if x).strip(),
            "organ": d.get("organ") or "",
            "url": f"https://www.riksdagen.se/sv/dokument-och-lagar/dokument/_{d['dok_id']}",
            "pdf_url": ""}
    fil = ((d.get("filbilaga") or {}).get("fil") or [])
    if isinstance(fil, dict):
        fil = [fil]
    if fil:
        meta["pdf_url"] = fil[0].get("url", "")
    t = rd_text(d["dok_id"])
    if len(t) < 500 and meta["pdf_url"]:
        t = pdf_text(meta["pdf_url"])
    return bedom_dokument(meta, t, "riksdagen")


def hamta_riksdagsdok(typer, fran, arbetare, om=False, grans=None):
    klara = {r["id"] for r in las_csv(DOK_CSV)}
    for typ in typer:
        kand = {}
        for q in katalog.SOKFRAGOR:
            for d in dokumentlista(doktyp=typ, sok=q, **{"from": f"{fran}-01-01"}):
                kand.setdefault(d["dok_id"], d)
            print(f"{typ}: '{q}' -> {len(kand)} kandidater totalt", flush=True)
        if om:
            omg = set(kand) & klara
            if omg:
                ta_bort_rader(DOK_CSV, omg, "id")
                klara -= omg
        att_gora = [d for d in kand.values() if d["dok_id"] not in klara]
        if grans:
            att_gora = att_gora[:grans]
        print(f"{typ}: {len(att_gora)} att hämta av {len(kand)}", flush=True)
        kor_dokument(att_gora, bearbeta_rd_dokument, arbetare, typ, lambda d: d["dok_id"])


def kor_dokument(att_gora, funk, arbetare, namn, nyckel):
    skr = CsvSkrivare(DOK_CSV, DOK_FALT)
    n_rel = n_fel = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(arbetare) as ex:
            fut = {ex.submit(funk, d): d for d in att_gora}
            for i, f in enumerate(as_completed(fut), 1):
                try:
                    rad = f.result()
                except Exception as e:
                    n_fel += 1
                    notera_fel(f"{namn} {nyckel(fut[f])}", e)
                    continue
                n_rel += int(rad["relevant"])
                skr.skriv(rad)
                if i % 25 == 0 or i == len(att_gora):
                    print(f"  {namn}: {i}/{len(att_gora)}, {n_rel} relevanta, {n_fel} fel, "
                          f"{i / max(time.time() - t0, 1):.2f}/s", flush=True)
    finally:
        skr.stang()
    logg["antal"][namn] = {"hamtade": len(att_gora) - n_fel, "relevanta": n_rel, "fel": n_fel}


# --- KB: SOU 1990–1999 ------------------------------------------------------------

def pdf_text(url):
    """Ladda ned en PDF till en tom katalog, ta ut texten med pdftotext och
    radera PDF:en. Sidbrytningar blir '[PDF-sida N]'."""
    tmp = Path(tempfile.mkdtemp(prefix="bostadsarkiv_", dir=os.environ.get("BOSTADSARKIV_TMP")))
    try:
        pdf = tmp / "dok.pdf"
        r = hamta_url(url, timeout=600, stream=True)
        if r is None:
            return ""
        with open(pdf, "wb") as f:
            for bit in r.iter_content(1 << 20):
                f.write(bit)
        ut = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"],
                            capture_output=True, timeout=600)
        raw = ut.stdout.decode("utf-8", "replace")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sidor = raw.split("\f")
    delar = []
    for i, s in enumerate(sidor, 1):
        s = text.stada(s)
        if s:
            delar.append(f"[PDF-sida {i}]\n\n{s}")
    return "\n\n".join(delar)


def kb_index(fran, till):
    r = hamta_url(KB_INDEX)
    r.encoding = "utf-8"
    rader = re.findall(
        r'<a href="(http://urn\.kb\.se/resolve\?urn=urn:nbn:se:kb:sou-(\d+))"[^>]*\s*">'
        r"(\d{4}):([^<]+)</a>\s*([^<]*)", r.text)
    ut = []
    for url, urn, ar, nr, titel in rader:
        if fran <= int(ar) <= till:
            ut.append({"urn": urn, "url": url, "ar": ar, "nr": nr.strip(),
                       "titel": re.sub(r"\s+", " ", titel).strip()})
    return ut


def kb_pdf_url(urn, urn_url):
    # Metadatasidan som URN-resolvern pekar på; resolvern ger ofta 503.
    r = hamta_url(f"https://weburn.kb.se/metadata/{urn[-3:]}/SOU_{urn}.htm")
    if r is None:
        r = hamta_url(urn_url)
    if r is None:
        return ""
    m = re.search(r'href="(https?://weburn\.kb\.se/[^"]+\.pdf)"', r.text)
    return m.group(1) if m else ""


def bearbeta_kb(d):
    pdf = kb_pdf_url(d["urn"], d["url"])
    if not pdf:
        raise RuntimeError("ingen PDF-länk på KB:s sida")
    meta = {"id": f"KB-SOU-{d['urn']}", "doktyp": "sou",
            "beteckning": f"SOU {d['ar']}:{d['nr']}", "rm": d["ar"], "nummer": d["nr"],
            "datum": d["ar"], "titel": d["titel"], "organ": "", "url": d["url"], "pdf_url": pdf}
    return bedom_dokument(meta, pdf_text(pdf), "kb")


def hamta_kb(fran, till, arbetare, om=False, grans=None):
    befintliga = las_csv(DOK_CSV)
    klara = {r["id"] for r in befintliga}
    # SOU som riksdagen redan har (samma beteckning, utan dellbokstav) hoppas över.
    hos_rd = {r["beteckning"] for r in befintliga if r["kalla"] == "riksdagen" and r["doktyp"] == "sou"}
    rd_alla = set()
    for ar in range(max(fran, 1997), till + 1):
        for d in dokumentlista(doktyp="sou", rm=str(ar)):
            rd_alla.add(f"SOU {d['rm']}:{d['beteckning']}")
    hos_rd |= rd_alla
    idx = kb_index(fran, till)
    if om:
        omg = {f"KB-SOU-{d['urn']}" for d in idx} & klara
        if omg:
            ta_bort_rader(DOK_CSV, omg, "id")
            klara -= omg

    def bas(nr):
        return re.match(r"\d+", nr).group(0) if re.match(r"\d+", nr) else nr

    att_gora = [d for d in idx if f"KB-SOU-{d['urn']}" not in klara
                and f"SOU {d['ar']}:{bas(d['nr'])}" not in hos_rd]
    if grans:
        att_gora = att_gora[:grans]
    print(f"KB: {len(idx)} SOU {fran}–{till} i KB:s förteckning, {len(att_gora)} att hämta "
          f"({len(rd_alla)} finns hos riksdagen)", flush=True)
    kor_dokument(att_gora, bearbeta_kb, arbetare, "kb", lambda d: f"SOU {d['ar']}:{d['nr']}")


# --- Huvudprogram -------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vad", choices=["alla", "protokoll", "riksdagsdok", "kb"])
    ap.add_argument("--fran", type=int, default=katalog.FRAN_AR)
    ap.add_argument("--till", type=int, default=date.today().year)
    ap.add_argument("--typ", nargs="*", default=["sou", "ds", "dir"], help="för riksdagsdok")
    ap.add_argument("--arbetare", type=int, default=4)
    ap.add_argument("--om", action="store_true", help="hämta om det som redan finns")
    ap.add_argument("--grans", type=int, help="högst så många nya (för test)")
    ap.add_argument("--tomma", action="store_true", help="gör om protokoll utan anföranden")
    a = ap.parse_args()
    DATA.mkdir(exist_ok=True)

    if a.vad in ("alla", "riksdagsdok"):
        hamta_riksdagsdok(a.typ, a.fran, a.arbetare, a.om, a.grans)
    if a.vad in ("alla", "kb"):
        hamta_kb(a.fran, min(a.till, 1999), max(1, a.arbetare - 1), a.om, a.grans)
    if a.vad in ("alla", "protokoll"):
        hamta_protokoll(a.fran, a.till, a.arbetare, a.om, a.grans, a.tomma)

    logg["slut"] = datetime.now().isoformat(timespec="seconds")
    tidigare = json.loads(LOGG.read_text()) if LOGG.exists() else []
    LOGG.write_text(json.dumps((tidigare + [logg])[-50:], ensure_ascii=False, indent=1))
    print("Klart.", json.dumps(logg["antal"], ensure_ascii=False))


if __name__ == "__main__":
    main()
