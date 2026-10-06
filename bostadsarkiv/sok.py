#!/usr/bin/env python3
"""Sök i bostadsarkivet (data/bostadsarkiv.sqlite).

Frågan följer SQLite FTS5: ord efter varandra måste alla finnas, "citat"
söker fras, * efter ett ord söker prefix, OR och NOT fungerar.

    python sok.py 'räntebidrag*'
    python sok.py '"allmännyttiga bostadsföretag"' --typ prot --fran 2008 --till 2011
    python sok.py 'investeringsstöd* hyres*' --parti S V --csv utdrag.csv
    python sok.py --oversikt
"""

import argparse
import csv
import sqlite3
import sys
import textwrap
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "bostadsarkiv.sqlite"

ANF = """
SELECT 'prot' AS typ, a.id AS ref, a.ar, bm25(sok_anf, 1.0, 0.3) AS rang,
       snippet(sok_anf, 0, '[', ']', ' … ', 40) AS utdrag, a.datum,
       'Prot. ' || a.rm || ':' || a.prot_nr || ', anf. ' || a.anf_nr AS kalla,
       a.talare || CASE WHEN a.parti <> '' THEN ' (' || a.parti || ')' ELSE '' END
         || ' – ' || a.rubrik AS titel,
       a.url, a.parti
FROM sok_anf JOIN anforanden a ON a.rowid = sok_anf.rowid
WHERE sok_anf MATCH ?"""

AVS = """
SELECT d.doktyp AS typ, CAST(v.id AS TEXT) AS ref, d.ar, bm25(sok_avs, 1.0, 0.3) AS rang,
       snippet(sok_avs, 0, '[', ']', ' … ', 40) AS utdrag, d.datum,
       d.beteckning || CASE WHEN v.sida <> '' THEN ', PDF-s. ' || v.sida ELSE '' END AS kalla,
       d.titel, d.url, '' AS parti
FROM sok_avs JOIN avsnitt v ON v.id = sok_avs.rowid JOIN dokument d ON d.id = v.dok_id
WHERE sok_avs MATCH ?"""


def sok(db, q, typ=None, fran=None, till=None, parti=None, sortera="rang", grans=50):
    """Sök i anföranden och utredningsavsnitt. Partifilter gäller bara
    anföranden (utredningarna utesluts då)."""
    delar, arg = [], []
    for sql, ar_kol, ar_typer in ((ANF, "a.ar", ["prot"]), (AVS, "d.ar", ["sou", "ds", "dir"])):
        valda = [t for t in ar_typer if not typ or t in typ]
        if not valda or (parti and "prot" not in valda):
            continue
        del_arg = [q]
        if ar_typer != ["prot"] and len(valda) < 3:
            sql += f" AND d.doktyp IN ({','.join('?' * len(valda))})"
            del_arg += valda
        if fran:
            sql += f" AND {ar_kol} >= ?"
            del_arg.append(fran)
        if till:
            sql += f" AND {ar_kol} <= ?"
            del_arg.append(till)
        if parti:
            sql += f" AND a.parti IN ({','.join('?' * len(parti))})"
            del_arg += [p.upper() for p in parti]
        delar.append(sql)
        arg += del_arg
    if not delar:
        return []
    sql = " UNION ALL ".join(delar)
    sql += " ORDER BY " + ("datum, rang" if sortera == "datum" else "rang")
    if grans:
        sql += f" LIMIT {int(grans)}"
    db.row_factory = sqlite3.Row
    return db.execute(sql, arg).fetchall()


def oversikt(db):
    print("Relevanta källor per typ och årtionde:\n")
    rader = db.execute("""
        SELECT typ, (ar / 5) * 5 AS period, COUNT(*) FROM kallor
        GROUP BY typ, period ORDER BY typ, period""").fetchall()
    for typ, period, n in rader:
        print(f"  {typ:5} {period}–{period + 4}: {n:6}")
    print("\nAnföranden per parti:")
    for parti, n in db.execute("""SELECT parti, COUNT(*) FROM anforanden GROUP BY parti
                                   ORDER BY 2 DESC"""):
        print(f"  {parti or '(utan parti)':12} {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fraga", nargs="?")
    ap.add_argument("--typ", nargs="*", choices=["prot", "sou", "ds", "dir"])
    ap.add_argument("--fran", type=int)
    ap.add_argument("--till", type=int)
    ap.add_argument("--parti", nargs="*")
    ap.add_argument("--datum", action="store_true", help="sortera på datum i stället för relevans")
    ap.add_argument("-n", type=int, default=30, help="antal träffar (0 = alla)")
    ap.add_argument("--csv", help="skriv träffarna till en CSV-fil")
    ap.add_argument("--oversikt", action="store_true")
    a = ap.parse_args()
    if not DB.exists():
        sys.exit("Databasen saknas – kör python bygg_db.py först.")
    db = sqlite3.connect(DB)
    if a.oversikt:
        return oversikt(db)
    if not a.fraga:
        ap.error("ange en sökfråga")
    rader = sok(db, a.fraga, a.typ, a.fran, a.till, a.parti, "datum" if a.datum else "rang",
                a.n or None)
    if a.csv:
        with open(a.csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["datum", "typ", "kalla", "titel", "utdrag", "url"])
            for r in rader:
                w.writerow([r["datum"], r["typ"], r["kalla"], r["titel"], r["utdrag"], r["url"]])
        print(f"{len(rader)} träffar till {a.csv}")
        return
    for r in rader:
        print(f"{r['datum']}  {r['kalla']}  {r['titel'][:90]}")
        print(textwrap.indent(textwrap.fill(r["utdrag"].replace("\n", " "), 100), "    "))
        print(f"    {r['url']}\n")
    print(f"{len(rader)} träffar")


if __name__ == "__main__":
    main()
