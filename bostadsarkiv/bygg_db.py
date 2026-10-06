#!/usr/bin/env python3
"""Bygger den sökbara databasen data/bostadsarkiv.sqlite av det som
hamta.py har sparat.

Tabeller
- dokument: alla bedömda SOU, Ds, direktiv, propositioner och betänkanden
  (även de som inte bedömdes relevanta, med träffräkning, så att urvalet
  går att granska)
- protokoll: alla genomgångna kammarprotokoll
- anforanden: relevanta anföranden med talare, parti, ärende och text
- avsnitt: de relevanta dokumentens text i avsnitt om ca 2 000 tecken, med
  PDF-sida (KB) eller närmaste rubrik (riksdagen)
- sok_anf, sok_avs: FTS5-index över anföranden och avsnitt (pekar på
  texten i tabellerna, så att den inte lagras två gånger)

    python bygg_db.py
"""

import csv
import gzip
import json
import re
import sqlite3
import time
from pathlib import Path

import text as textmodul

BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "data"
DB = DATA / "bostadsarkiv.sqlite"
AVSNITT_TECKEN = 2000

SCHEMA = """
CREATE TABLE dokument (
  id TEXT PRIMARY KEY, kalla TEXT, doktyp TEXT, beteckning TEXT, rm TEXT, nummer TEXT,
  datum TEXT, ar INTEGER, titel TEXT, organ TEXT, url TEXT, pdf_url TEXT, ord INTEGER,
  karna INTEGER, bred INTEGER, karntermer TEXT, bredtermer TEXT, titeltraff INTEGER,
  relevant INTEGER, grad TEXT, textfil TEXT, hamtad TEXT);
CREATE TABLE protokoll (
  dok_id TEXT PRIMARY KEY, rm TEXT, nummer TEXT, datum TEXT, titel TEXT,
  anforanden INTEGER, relevanta INTEGER, hamtad TEXT);
CREATE TABLE anforanden (
  id TEXT PRIMARY KEY, prot_id TEXT, rm TEXT, prot_nr TEXT, datum TEXT, ar INTEGER,
  anf_nr INTEGER, talare TEXT, parti TEXT, replik INTEGER, rubrik TEXT, karna INTEGER,
  bred INTEGER, karntermer TEXT, bredtermer TEXT, grad TEXT, ord INTEGER, url TEXT, text TEXT,
  kammare TEXT);
CREATE TABLE avsnitt (
  id INTEGER PRIMARY KEY, dok_id TEXT, nr INTEGER, sida TEXT, rubrik TEXT, text TEXT);
CREATE VIRTUAL TABLE sok_anf USING fts5(
  text, rubrik, content = 'anforanden', tokenize = "unicode61 remove_diacritics 0");
CREATE VIRTUAL TABLE sok_avs USING fts5(
  text, rubrik, content = 'avsnitt', content_rowid = 'id',
  tokenize = "unicode61 remove_diacritics 0");
CREATE INDEX anf_datum ON anforanden(datum);
CREATE INDEX anf_parti ON anforanden(parti);
CREATE INDEX avs_dok ON avsnitt(dok_id);
CREATE VIEW kallor AS
  SELECT 'prot' AS typ, id, datum, ar, 'Prot. ' || rm || ':' || prot_nr || ', anf. ' || anf_nr AS beteckning,
         talare || CASE WHEN parti <> '' THEN ' (' || parti || ')' ELSE '' END AS titel,
         rubrik, grad, karna, url
    FROM anforanden
  UNION ALL
  SELECT doktyp, id, datum, ar, beteckning, titel, organ, grad, karna, url
    FROM dokument WHERE relevant = 1;
"""


def las_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def las_jsonl_gz(p):
    """Rader i en gzip-fil som kan vara ofullständig (hämtningen pågår eller
    avbröts); det som går att läsa används."""
    try:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for rad in f:
                if rad.strip():
                    yield json.loads(rad)
    except (EOFError, json.JSONDecodeError) as e:
        print(f"  varning: {p.name} slutar ofullständigt ({e.__class__.__name__})")


def ar_av(datum):
    m = re.match(r"(\d{4})", datum or "")
    return int(m.group(1)) if m else None


def dela_avsnitt(t):
    """Dela text i avsnitt om ca AVSNITT_TECKEN tecken längs styckegränser.
    Returnerar (sida, rubrik, text)."""
    sida, rubrik, buf, ut = "", "", [], []

    def tom():
        if buf:
            ut.append((sida_start[0], rubrik_start[0], "\n\n".join(buf)))
            buf.clear()

    sida_start, rubrik_start = [""], [""]
    for st in t.split("\n\n"):
        m = re.match(r"^\[PDF-sida (\d+)\]$", st)
        if m:
            sida = m.group(1)
            continue
        if st.startswith("# "):
            tom()
            rubrik = st[2:].strip()[:200]
            continue
        if not buf:
            sida_start[0], rubrik_start[0] = sida, rubrik
        buf.append(st)
        if sum(len(b) for b in buf) >= AVSNITT_TECKEN:
            tom()
    tom()
    return ut


def main():
    t0 = time.time()
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(tmp)
    db.executescript(SCHEMA)

    # Dokument: senaste raden per id gäller (omhämtning lägger till nya rader).
    dok = {}
    for r in las_csv(DATA / "dokument.csv"):
        dok[r["id"]] = r
    # Samma SOU kan finnas både hos riksdagen och KB; riksdagens version gäller.
    rd_bet = {r["beteckning"] for r in dok.values() if r["kalla"] == "riksdagen"}
    for r in dok.values():
        if r["kalla"] == "kb" and r["beteckning"] in rd_bet:
            r["relevant"] = "0"
        db.execute(
            "INSERT INTO dokument VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["id"], r["kalla"], r["doktyp"], r["beteckning"], r["rm"], r["nummer"],
             r["datum"], ar_av(r["datum"]), r["titel"], r["organ"], r["url"], r["pdf_url"],
             int(r["ord"] or 0), int(r["karna"] or 0), int(r["bred"] or 0), r["karntermer"],
             r["bredtermer"], int(r["titeltraff"] or 0), int(r["relevant"] or 0), r["grad"],
             r["textfil"], r["hamtad"]))

    n_avs = 0
    for r in dok.values():
        if r["relevant"] != "1" or not r["textfil"]:
            continue
        p = DATA / r["textfil"]
        if not p.exists():
            continue
        with gzip.open(p, "rt", encoding="utf-8") as f:
            t = f.read()
        t = t.split("\n\n", 1)[1] if "\n\n" in t else t  # huvudet med beteckning och källa
        for nr, (sida, rub, txt) in enumerate(dela_avsnitt(t), 1):
            db.execute("INSERT INTO avsnitt (dok_id, nr, sida, rubrik, text) VALUES (?,?,?,?,?)",
                       (r["id"], nr, sida, rub, txt))
            n_avs += 1

    prot = {}
    for r in las_csv(DATA / "protokoll.csv"):
        prot[r["dok_id"]] = r
    db.executemany("INSERT INTO protokoll VALUES (?,?,?,?,?,?,?,?)",
                   [(r["dok_id"], r["rm"], r["nummer"], r["datum"], r["titel"],
                     int(r["anforanden"] or 0), int(r["relevanta"] or 0), r["hamtad"])
                    for r in prot.values()])

    n_anf, sedda = 0, set()
    for p in sorted((DATA / "anforanden").glob("*.jsonl.gz")):
        for a in las_jsonl_gz(p):
            aid = f"{a['prot_id']}-{a['anf_nr']}"
            if aid in sedda:
                continue
            sedda.add(aid)
            db.execute(
                "INSERT INTO anforanden VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (aid, a["prot_id"], a["rm"], a["prot_nr"], a["datum"], ar_av(a["datum"]),
                 a["anf_nr"], a["talare"], a["parti"], int(a["replik"]), a["rubrik"],
                 a["karna"], a["bred"], a["karntermer"], a["bredtermer"], a["grad"],
                 a["ord"], a["url"], textmodul.rensa_sidhuvud(a["text"]), a.get("kammare", "")))
            n_anf += 1

    for t in ("sok_anf", "sok_avs"):
        db.execute(f"INSERT INTO {t}({t}) VALUES ('rebuild')")
        db.execute(f"INSERT INTO {t}({t}) VALUES ('optimize')")
    db.commit()
    db.close()
    tmp.replace(DB)
    rel = sum(1 for r in dok.values() if r["relevant"] == "1")
    print(f"{DB.name}: {len(dok)} dokument bedömda, {rel} relevanta, {n_avs} avsnitt; "
          f"{len(prot)} protokoll, {n_anf} anföranden; {DB.stat().st_size / 1e6:.0f} MB, "
          f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
