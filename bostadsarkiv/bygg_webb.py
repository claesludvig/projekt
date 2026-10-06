#!/usr/bin/env python3
"""Bygger datafilerna till den publicerade söksidan (webb/index.html).

Anförandena tas med i sin helhet. För propositioner, betänkanden och
utredningar tas de stycken med som innehåller en kärnterm (högst
MAX_STYCKEN per dokument), eftersom fulltexterna är för stora för en
webbsida. Hela texten finns i sökdatabasen och hos källan.

    python bygg_db.py && python bygg_webb.py
"""

import json
import re
import sqlite3
from pathlib import Path

import katalog

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "data" / "bostadsarkiv.sqlite"
UT = BASE_DIR / "webb" / "data"
MAX_STYCKEN = 30
MAX_TECKEN = 1100
MAX_FIL = 14_000_000
GRAD = {"låg": 0, "medel": 1, "hög": 2}

_KARNA = re.compile("|".join(f"(?:{p})" for p in katalog.KARNA.values()))
_BRED = re.compile("|".join(f"(?:{p})" for p in katalog.BRED.values()))


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


def stycken(db, dok_id):
    ut, reserv = [], []
    for sida, txt in db.execute("SELECT sida, text FROM avsnitt WHERE dok_id = ? ORDER BY nr", (dok_id,)):
        for st in txt.split("\n\n"):
            low = st.lower()
            if _KARNA.search(low):
                ut.append([sida, klipp(st, _KARNA)])
            elif len(reserv) < 10 and _BRED.search(low):
                reserv.append([sida, klipp(st, _BRED)])
    if not ut:
        ut = reserv
    return ut[:MAX_STYCKEN], len(ut)


def skriv_delar(namn, poster, nyckel_ar):
    """Dela upp i filer om högst MAX_FIL byte, i årsordning."""
    filer, buf, storlek = [], [], 0
    for p in poster:
        s = len(json.dumps(p, ensure_ascii=False).encode()) + 1
        if buf and storlek + s > MAX_FIL:
            filer.append(buf)
            buf, storlek = [], 0
        buf.append(p)
        storlek += s
    if buf:
        filer.append(buf)
    index = []
    for i, f in enumerate(filer, 1):
        fn = f"{namn}-{i}.json"
        (UT / fn).write_text(json.dumps(f, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index.append({"fil": fn, "fran": nyckel_ar(f[0]), "till": nyckel_ar(f[-1]), "antal": len(f),
                      "byte": (UT / fn).stat().st_size})
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

    anf = []
    for (aid, prot_id, rm, prot_nr, datum, anf_nr, talare, parti, replik, rubrik, grad,
         karntermer, text) in db.execute(
            """SELECT id, prot_id, rm, prot_nr, datum, anf_nr, talare, parti, replik, rubrik,
                      grad, karntermer, text FROM anforanden ORDER BY datum, prot_id, anf_nr"""):
        anf.append({"d": datum, "p": prot_id, "r": f"{rm}:{prot_nr}", "n": anf_nr, "s": talare,
                    "f": parti, "k": replik, "h": rub(rubrik), "g": GRAD.get(grad, 0), "x": text})

    dok = []
    for (did, doktyp, bet, titel, datum, url, pdf, grad, karna, karntermer, ord_, kalla) in db.execute(
            """SELECT id, doktyp, beteckning, titel, datum, url, pdf_url, grad, karna, karntermer,
                      ord, kalla FROM dokument WHERE relevant = 1 ORDER BY datum, beteckning"""):
        ps, n = stycken(db, did)
        dok.append({"id": did, "t": doktyp, "b": bet, "ti": titel, "d": datum, "u": url,
                    "pdf": pdf, "g": GRAD.get(grad, 0), "kn": karna,
                    "kt": [t.split(":")[0] for t in karntermer.split(";") if t][:4],
                    "o": ord_, "kb": int(kalla == "kb"), "ps": ps, "pn": n})

    index = {
        "rubriker": rubriker,
        "anforanden": skriv_delar("anf", anf, lambda p: p["d"][:4]),
        "dokument": skriv_delar("dok", dok, lambda p: p["d"][:4]),
        "uppdaterad": db.execute("SELECT MAX(hamtad) FROM dokument").fetchone()[0],
        "protokoll": db.execute("SELECT COUNT(*) FROM protokoll").fetchone()[0],
        "bedomda": db.execute("SELECT COUNT(*) FROM dokument").fetchone()[0],
    }
    (UT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                                   encoding="utf-8")
    tot = sum(f.stat().st_size for f in UT.glob("*.json"))
    print(f"{len(anf)} anföranden, {len(dok)} dokument, {len(list(UT.glob('*.json')))} filer, "
          f"{tot / 1e6:.0f} MB")
    for k in ("anforanden", "dokument"):
        for f in index[k]:
            print(f"  {f['fil']}: {f['fran']}–{f['till']}, {f['antal']} poster, {f['byte'] / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
