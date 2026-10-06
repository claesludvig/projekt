#!/usr/bin/env python3
"""Bygger datafilerna till den publicerade söksidan (webb/index.html).

Anförandena tas med i sin helhet. För propositioner, betänkanden, motioner
och utredningar tas de stycken med som nämner bostadsbyggandet eller
träffar ett kapitelavsnitts mönster (högst MAX_STYCKEN per dokument),
eftersom fulltexterna är för stora för en webbsida. Hela texten finns i
sökdatabasen och hos källan.

Varje källa märks med de avsnitt i kapitlet den hör till (kapitel.py).
Filerna delas upp per period, så att sidan bara laddar den period som visas.

    python bygg_db.py && python bygg_webb.py
"""

import json
import re
import sqlite3
from pathlib import Path

import aktorer
import kapitel
import katalog

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "data" / "bostadsarkiv.sqlite"
UT = BASE_DIR / "webb" / "data"
MAX_STYCKEN = 30
MAX_TECKEN = 1100
MAX_FIL = 14_000_000
GRAD = {"låg": 0, "medel": 1, "hög": 2}
PERIODER = [(1939, 1944), (1945, 1959), (1960, 1974), (1975, 1989), (1990, 2009), (2010, 2026)]

_KARNA = re.compile("|".join(f"(?:{p})" for p in katalog.KARNA.values()))
_BRED = re.compile("|".join(f"(?:{p})" for p in katalog.BRED.values()))
_AKT = re.compile("|".join(p.pattern for _, p in aktorer._MONSTER))
_KAP = [(a["nr"], a["fran"], a["till"], re.compile(a["mönster"])) for a in kapitel.AVSNITT]


def avsnitt_for(ar, low):
    return [nr for nr, f, t, p in _KAP if f <= ar <= t and p.search(low)]


def klipp(st, pat):
    """Stycket, eller ett utsnitt runt första träffen om det är långt."""
    if len(st) <= MAX_TECKEN:
        return st
    m = pat.search(st.lower())
    a = max(0, (m.start() if m else 0) - MAX_TECKEN // 3)
    a = st.rfind(" ", 0, a) + 1 if a else 0
    b = st.find(" ", a + MAX_TECKEN)
    b = len(st) if b < 0 else b
    return ("… " if a else "") + st[a:b] + (" …" if b < len(st) else "")


def dokument_stycken(db, dok_id, ar, rem=False):
    """Stycken med kärnträff, kapitelträff eller aktörers ställningstaganden.
    Returnerar (stycken, antal, kapitelavsnitt, aktörsgrupper). Ett stycke är
    [sida, text] eller [sida, text, "bygg,fast"] när aktörer tar ställning."""
    kap_pat = [p for _, f, t, p in _KAP if f <= ar <= t]
    ut, akt_ut, reserv, kap, akt = [], [], [], set(), set()
    for nr, (sida, txt) in enumerate(db.execute(
            "SELECT sida, text FROM avsnitt WHERE dok_id = ? ORDER BY nr", (dok_id,)), 1):
        for st in txt.split("\n\n"):
            low = st.lower()
            k = set(avsnitt_for(ar, low))
            kap |= k
            g = [] if rem else aktorer.stallningstagande(low)
            if g:
                akt |= set(g)
                akt_ut.append([sida, klipp(st, _AKT),
                               ",".join(g)])
            elif _KARNA.search(low) or k or (rem and nr == 1 and len(ut) < 3):
                pat = _KARNA if _KARNA.search(low) else next((p for p in kap_pat if p.search(low)), _BRED)
                ut.append([sida, klipp(st, pat)])
            elif len(reserv) < 10 and _BRED.search(low):
                reserv.append([sida, klipp(st, _BRED)])
    if not ut and not akt_ut:
        ut = reserv
    gr = MAX_STYCKEN // 2 if rem else MAX_STYCKEN
    valda = akt_ut[:gr] + ut[:gr]
    return valda, len(ut) + len(akt_ut), sorted(kap), sorted(akt)


def period(ar):
    for i, (f, t) in enumerate(PERIODER):
        if f <= ar <= t:
            return i
    return len(PERIODER) - 1


def skriv_delar(namn, poster):
    """Dela upp per period och därefter i filer om högst MAX_FIL byte."""
    index = []
    for pi, (f, t) in enumerate(PERIODER):
        filer, buf, storlek = [], [], 0
        for p in (p for p in poster if period(int(p["d"][:4])) == pi):
            s = len(json.dumps(p, ensure_ascii=False).encode()) + 1
            if buf and storlek + s > MAX_FIL:
                filer.append(buf)
                buf, storlek = [], 0
            buf.append(p)
            storlek += s
        if buf:
            filer.append(buf)
        for i, del_ in enumerate(filer, 1):
            fn = f"{namn}-{f}-{i}.json"
            (UT / fn).write_text(json.dumps(del_, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            index.append({"fil": fn, "period": pi, "antal": len(del_), "byte": (UT / fn).stat().st_size})
    return index


def main():
    UT.mkdir(parents=True, exist_ok=True)
    for f in UT.glob("*.json"):
        f.unlink()
    db = sqlite3.connect(DB)

    rubriker, rub_idx = [], {}

    def rub(r):
        if r not in rub_idx:
            rub_idx[r] = len(rubriker)
            rubriker.append(r)
        return rub_idx[r]

    anf_akt = {}
    for ref, g in db.execute("SELECT ref, grupp FROM aktorsstycken WHERE typ = 'prot'"):
        anf_akt.setdefault(ref, set()).add(g)
    anf = []
    for (aid, prot_id, rm, prot_nr, datum, ar, anf_nr, talare, parti, replik, rubrik, grad, text,
         kammare) in db.execute(
            """SELECT id, prot_id, rm, prot_nr, datum, ar, anf_nr, talare, parti, replik, rubrik,
                      grad, text, kammare FROM anforanden ORDER BY datum, prot_id, anf_nr"""):
        p = {"d": datum, "p": prot_id, "r": f"{rm}:{prot_nr}", "n": anf_nr, "s": talare,
             "f": parti, "k": replik, "h": rub(rubrik), "g": GRAD.get(grad, 0), "x": text}
        if kammare:
            p["c"] = kammare
        kap = avsnitt_for(ar or 0, (text + " " + rubrik).lower())
        if kap:
            p["a"] = kap
        if aid in anf_akt:
            p["ak"] = sorted(anf_akt[aid])
        anf.append(p)

    dok = []
    for (did, doktyp, bet, titel, datum, ar, url, pdf, grad, karna, karntermer, ord_, kalla, organ) in db.execute(
            """SELECT id, doktyp, beteckning, titel, datum, ar, url, pdf_url, grad, karna, karntermer,
                      ord, kalla, organ FROM dokument WHERE relevant = 1 ORDER BY datum, beteckning"""):
        ps, n, kap, akt = dokument_stycken(db, did, ar or 0, rem=doktyp == "rem")
        if doktyp == "rem":
            akt = [aktorer.grupp_for_organisation(organ)]
        p = {"id": did, "t": doktyp, "b": bet, "ti": titel, "d": datum, "u": url,
             "pdf": pdf, "g": GRAD.get(grad, 0), "kn": karna,
             "kt": [t.split(":")[0] for t in karntermer.split(";") if t][:4],
             "o": ord_, "kb": int(kalla == "kb"), "ps": ps, "pn": n}
        kap = sorted(set(kap) | set(avsnitt_for(ar or 0, titel.lower())))
        if kap:
            p["a"] = kap
        if akt:
            p["ak"] = akt
        if doktyp == "rem":
            p["org"] = organ
        dok.append(p)

    kap_antal = {a["nr"]: 0 for a in kapitel.AVSNITT}
    for p in anf + dok:
        for k in p.get("a", []):
            kap_antal[k] += 1
    per_antal = [sum(1 for p in anf + dok if period(int(p["d"][:4])) == i) for i in range(len(PERIODER))]

    akt_antal = {}
    for p in anf + dok:
        for g in p.get("ak", []):
            akt_antal[g] = akt_antal.get(g, 0) + 1
    per_ar = {}
    for p in anf:
        per_ar.setdefault(p["d"][:4], [0, 0])[0] += 1
    for p in dok:
        per_ar.setdefault(p["d"][:4], [0, 0])[1] += 1
    index = {
        "rubriker": rubriker,
        "per_ar": per_ar,
        "aktorer": [{"k": k, "namn": n, "bransch": k in aktorer.BRANSCH, "antal": akt_antal.get(k, 0)}
                    for k, n, _ in aktorer.GRUPPER],
        "perioder": [{"fran": f, "till": t, "antal": per_antal[i]} for i, (f, t) in enumerate(PERIODER)],
        "kapitel": [{"nr": a["nr"], "namn": a["namn"], "fran": a["fran"], "till": a["till"],
                     "antal": kap_antal[a["nr"]]} for a in kapitel.AVSNITT],
        "filer": skriv_delar("dok", dok) + skriv_delar("anf", anf),
        "uppdaterad": db.execute("SELECT MAX(hamtad) FROM dokument").fetchone()[0],
        "protokoll": db.execute("SELECT COUNT(*) FROM protokoll").fetchone()[0],
        "bedomda": db.execute("SELECT COUNT(*) FROM dokument").fetchone()[0],
        "per_typ": dict(db.execute("SELECT typ, COUNT(*) FROM kallor GROUP BY typ").fetchall()),
    }
    (UT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                                   encoding="utf-8")
    tot = sum(f.stat().st_size for f in UT.glob("*.json"))
    print(f"{len(anf)} anföranden, {len(dok)} dokument, {len(list(UT.glob('*.json')))} filer, "
          f"{tot / 1e6:.0f} MB")
    for i, (f, t) in enumerate(PERIODER):
        mb = sum(x["byte"] for x in index["filer"] if x["period"] == i) / 1e6
        print(f"  {f}–{t}: {per_antal[i]} källor, {mb:.1f} MB")
    for a in index["kapitel"]:
        print(f"  avsnitt {a['nr']} {a['namn']}: {a['antal']}")


if __name__ == "__main__":
    main()
