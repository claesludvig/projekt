"""Bygger partipositionsdatabasen av allt som hämtats.

Varje källa blir dokument (parti, år, slag, titel, länkar) och stycken. Ett stycke som tar upp en
bostadspolitisk fråga (FRAGOR i katalog.py) märks med frågan, så att partiernas formuleringar kan
läggas bredvid varandra period för period.

  data/partipositioner.sqlite  dokument, stycke, stycke_fts (FTS5), parti, fraga, fokus
  data/csv/dokument.csv        förteckningen (medietext ingår inte)
  webb/data/                   sökgränssnittets data
"""
import csv, gzip, json, re, sqlite3, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from katalog import BOSTAD_RX, FRAGA_RX, FRAGOR, PARTI_RX, PARTIER

ROT = Path(__file__).parent
DATA = ROT / "data"
WEBB = ROT / "webb" / "data"
PRX = {k: re.compile(rx, re.I) for k, rx in PARTI_RX.items()}
MEDIENAMN = {"ab": "Aftonbladet", "ex": "Expressen", "dn": "Dagens Nyheter", "svd": "Svenska Dagbladet", "omni": "Omni",
             "ds": "Dagens Samhälle", "hh": "Hem & Hyra", "ft": "Fastighetstidningen", "bv": "Byggvärlden"}
VIVILL_SLAG = {"v": "valmanifest", "p": "partiprogram", "c": "partiprogram", "i": "partiprogram", "h": "handlingsprogram",
               "f": "handlingsprogram", "r": "handlingsprogram"}
SLAGNAMN = {"valmanifest": "Valmanifest", "partiprogram": "Parti-, princip- och idéprogram", "handlingsprogram": "Handlingsprogram",
            "överenskommelse": "Överenskommelse", "regeringsförklaring": "Regeringsförklaring", "motion": "Partiets bostadsmotion",
            "partisajt": "Partiets webbplats i dag", "wayback": "Partiets webbplats, arkivkopia", "media": "Medier"}


def _rensa(t):
    t = unicodedata.normalize("NFC", t or "")
    t = re.sub("[�­\x00-\x08\x0b\x0e-\x1f]", "", t)
    t = re.sub(r"-\n(?=[a-zåäö])", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def stycken(text):
    """Dela i stycken; sammanfoga radbrutna rader, dela för långa."""
    ut = []
    for p in re.split(r"\n\s*\n", _rensa(text)):
        p = re.sub(r"\s*\n\s*", " ", p).strip()
        if len(p) < 25: continue
        while len(p) > 1600:
            i = p.rfind(". ", 0, 1400); i = i + 1 if i > 400 else 1400
            ut.append(p[:i].strip()); p = p[i:].strip()
        ut.append(p)
    return ut


def fragor(p):
    return [k for k, rx in FRAGA_RX.items() if rx.search(p)]


def partier_i(text):
    return [k for k, rx in PRX.items() if rx.search(text)]


def dokumenten():
    docs = []
    # Vivill
    for d in json.loads((DATA / "vivill" / "lista.json").read_text()):
        f = DATA / "vivill" / "text" / f"{d['id']}.txt"
        if not f.exists() or d["slag"].endswith("_eu"): continue
        slag = VIVILL_SLAG.get(d["slag"], "partiprogram")
        docs.append({"id": f"viv_{d['id']}", "partier": [d["parti"]], "ar": d["ar"], "datum": str(d["ar"]), "slag": slag,
                     "titel": d["titel"], "undertyp": d["slagnamn"], "url": d["url"], "pdf": d["pdf"], "kalla": "SND Vivill",
                     "text": f.read_text()})
    # Överenskommelser, regeringsförklaringar, motioner
    for mapp, slag in (("avtal", "överenskommelse"), ("regdekl", "regeringsförklaring"), ("mot", "motion")):
        for f in sorted((DATA / "dok" / mapp).glob("*.json")):
            try: d = json.loads(f.read_text())
            except json.JSONDecodeError: continue
            titel = d["titel"] + (f" ({d['beteckning']})" if d.get("beteckning") else "")
            docs.append({"id": f"{mapp}_{d['id']}", "partier": d.get("partier") or [], "ar": d["ar"], "datum": d.get("datum") or str(d["ar"]),
                         "slag": slag, "titel": titel, "undertyp": d.get("subtyp") or d.get("slag"), "url": d["url"], "pdf": "",
                         "kalla": {"avtal": "", "regdekl": "Regeringen.se", "mot": "Riksdagen"}[mapp], "text": d["text"],
                         "rm": d.get("rm")})
    # Partiernas webbplatser i dag och i Wayback
    for f in sorted((DATA / "partisajter").glob("*.jsonl")):
        for i, l in enumerate(f.read_text().splitlines()):
            try: d = json.loads(l)
            except json.JSONDecodeError: continue
            ar = int((d.get("datum") or d["hamtad"])[:4])
            docs.append({"id": f"sajt_{d['parti']}_{i}", "partier": [d["parti"]], "ar": ar, "datum": d.get("datum") or d["hamtad"],
                         "slag": "partisajt", "titel": d["titel"] or d["url"], "undertyp": f"hämtad {d['hamtad']}", "url": d["url"],
                         "pdf": "", "kalla": "Partiets webbplats", "text": d["text"]})
    for f in sorted((DATA / "wayback").glob("*.jsonl")) if (DATA / "wayback").exists() else []:
        for i, l in enumerate(f.read_text().splitlines()):
            try: d = json.loads(l)
            except json.JSONDecodeError: continue
            docs.append({"id": f"wb_{d['parti']}_{d['tidsstampel']}_{i}", "partier": [d["parti"]], "ar": d["ar"],
                         "datum": f"{d['tidsstampel'][:4]}-{d['tidsstampel'][4:6]}-{d['tidsstampel'][6:8]}", "slag": "wayback",
                         "titel": d["titel"] or d["url"], "undertyp": d["url"], "url": d["arkiv"], "pdf": "", "kalla": "Wayback Machine",
                         "text": d["text"]})
    # Medier
    sett = set()
    for namn in ("wp.jsonl", "artiklar.jsonl"):
        f = DATA / "media" / namn
        if not f.exists(): continue
        for l in f.read_text().splitlines():
            try: d = json.loads(l)
            except json.JSONDecodeError: continue
            if d["url"] in sett: continue
            sett.add(d["url"])
            text = (d.get("titel") or "") + "\n\n" + (d.get("ingress") or "") + "\n\n" + (d.get("text") or "")
            datum = (d.get("datum") or "")[:10]
            if not re.match(r"\d{4}", datum): continue
            docs.append({"id": f"med_{len(sett)}", "partier": partier_i(text), "ar": int(datum[:4]), "datum": datum, "slag": "media",
                         "titel": d.get("titel") or d["url"], "undertyp": MEDIENAMN.get(d["medium"], d["medium"]), "url": d["url"],
                         "pdf": "", "kalla": MEDIENAMN.get(d["medium"], d["medium"]), "text": text, "ingress": d.get("ingress") or ""})
    f = DATA / "media" / "gnews.jsonl"
    if f.exists():
        for l in f.read_text().splitlines():
            d = json.loads(l)
            if not d.get("datum"): continue
            docs.append({"id": f"gn_{abs(hash(d['url'])) % 10**12}", "partier": partier_i(d["titel"] + " " + d["sokord"]), "ar": int(d["datum"][:4]),
                         "datum": d["datum"], "slag": "media", "titel": d["titel"], "undertyp": d.get("kalla") or "Google Nyheter",
                         "url": d["url"], "pdf": "", "kalla": d.get("kalla") or "Google Nyheter", "text": d["titel"], "rubrik_bara": True})
    return docs


def bearbeta(docs):
    ut = []
    for d in docs:
        st = stycken(d["text"])
        rel = []
        for i, p in enumerate(st):
            fr = fragor(p)
            if fr or BOSTAD_RX.search(p):
                rel.append({"nr": i + 1, "text": p, "fragor": fr, "partier": partier_i(p) if d["slag"] in ("media", "överenskommelse", "regeringsförklaring") else []})
        n_bostad = len(rel); n_fraga = sum(1 for r in rel if r["fragor"])
        # Partiernas egna program och sidor tas med om de alls tar upp bostäder; medier och webbsidor kräver mer
        if d["slag"] in ("media", "partisajt", "wayback") and n_fraga < 1 and not d.get("rubrik_bara"): continue
        if d["slag"] == "media" and not d.get("rubrik_bara") and not d["partier"]: continue
        if not rel and not d.get("rubrik_bara"): continue
        ord_ = max(1, len(d["text"].split()))
        d.update({"stycken": rel if d["slag"] != "media" else rel[:40], "antal_stycken": len(st), "ord": ord_,
                  "fragor": sorted({f for r in rel for f in r["fragor"]}),
                  "andel": round(sum(len(r["text"].split()) for r in rel) / ord_, 4)})
        ut.append(d)
    return ut


def fokus(docs):
    """Hur stor del av partiets valmanifest och program som ägnas varje fråga, per valår."""
    rader = []
    for d in docs:
        if d["slag"] not in ("valmanifest", "partiprogram", "handlingsprogram") or len(d["partier"]) != 1: continue
        ord_fr = Counter()
        for r in d["stycken"]:
            for f in r["fragor"]: ord_fr[f] += len(r["text"].split())
        bostad = sum(len(r["text"].split()) for r in d["stycken"])
        rader.append({"parti": d["partier"][0], "ar": d["ar"], "slag": d["slag"], "dok": d["id"], "ord": d["ord"],
                      "bostad": round(1000 * bostad / d["ord"], 1), **{f: round(1000 * ord_fr[f] / d["ord"], 2) for f in FRAGOR}})
    return rader


def sqlite(docs, fok):
    f = DATA / "partipositioner.sqlite"; f.unlink(missing_ok=True)
    c = sqlite3.connect(f)
    c.executescript("""
    CREATE TABLE parti (parti TEXT PRIMARY KEY, kod TEXT, namn TEXT);
    CREATE TABLE fraga (fraga TEXT PRIMARY KEY, namn TEXT);
    CREATE TABLE dokument (id TEXT PRIMARY KEY, slag TEXT, undertyp TEXT, partier TEXT, ar INT, datum TEXT, titel TEXT,
        url TEXT, pdf TEXT, kalla TEXT, fragor TEXT, ord INT, andel_bostad REAL, text TEXT);
    CREATE TABLE stycke (dok TEXT REFERENCES dokument, nr INT, text TEXT, fragor TEXT, partier TEXT, PRIMARY KEY (dok, nr));
    CREATE VIRTUAL TABLE stycke_fts USING fts5(text, content='stycke', content_rowid='rowid', tokenize='unicode61 remove_diacritics 0');
    CREATE TABLE fokus (parti TEXT, ar INT, slag TEXT, dok TEXT, ord INT, bostad REAL, %s);
    """ % ", ".join(f"{k} REAL" for k in FRAGOR))
    c.executemany("INSERT INTO parti VALUES (?,?,?)", [(k, p["kod"], p["namn"]) for k, p in PARTIER.items()])
    c.executemany("INSERT INTO fraga VALUES (?,?)", [(k, n) for k, (n, _) in FRAGOR.items()])
    for d in docs:
        c.execute("INSERT INTO dokument VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (d["id"], d["slag"], d.get("undertyp"), ",".join(d["partier"]),
                  d["ar"], d["datum"], d["titel"], d["url"], d.get("pdf"), d.get("kalla"), ",".join(d["fragor"]), d["ord"], d["andel"], d["text"]))
        c.executemany("INSERT INTO stycke VALUES (?,?,?,?,?)", [(d["id"], r["nr"], r["text"], ",".join(r["fragor"]), ",".join(r["partier"])) for r in d["stycken"]])
    c.execute("INSERT INTO stycke_fts(rowid, text) SELECT rowid, text FROM stycke")
    c.executemany(f"INSERT INTO fokus VALUES ({','.join('?' * (6 + len(FRAGOR)))})",
                  [(r["parti"], r["ar"], r["slag"], r["dok"], r["ord"], r["bostad"], *[r[k] for k in FRAGOR]) for r in fok])
    c.commit(); c.execute("VACUUM"); c.close()
    print(f"{f.name}: {f.stat().st_size / 1e6:.0f} MB")
    # Publik version för git: medieartiklarnas text ersätts med rubrik och ingress (upphovsrätt)
    import gzip as gz, shutil
    pub = DATA / "partipositioner_publik.sqlite"; shutil.copy(f, pub)
    c = sqlite3.connect(pub)
    c.execute("DELETE FROM stycke WHERE dok IN (SELECT id FROM dokument WHERE slag = 'media')")
    c.execute("UPDATE dokument SET text = titel WHERE slag = 'media'")
    c.execute("INSERT INTO stycke_fts(stycke_fts) VALUES ('rebuild')")
    c.commit(); c.execute("VACUUM"); c.close()
    with open(pub, "rb") as i, gz.open(str(pub) + ".gz", "wb", 9) as o: shutil.copyfileobj(i, o)
    pub.unlink()


def csvfil(docs):
    (DATA / "csv").mkdir(exist_ok=True)
    with open(DATA / "csv" / "dokument.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "slag", "undertyp", "partier", "ar", "datum", "titel", "url", "kalla", "fragor", "andel_bostad"])
        for d in docs:
            w.writerow([d["id"], d["slag"], d.get("undertyp"), ",".join(d["partier"]), d["ar"], d["datum"], d["titel"], d["url"],
                        d.get("kalla"), ",".join(d["fragor"]), d["andel"]])


def webb(docs, fok):
    WEBB.mkdir(parents=True, exist_ok=True)
    for f in WEBB.glob("*.json"): f.unlink()
    filer, buf, storlek = [], [], 0
    def spara():
        nonlocal buf, storlek
        if not buf: return
        namn = f"stycken-{len(filer) + 1}.json"; b = json.dumps(buf, ensure_ascii=False, separators=(",", ":")).encode()
        (WEBB / namn).write_bytes(b); filer.append({"fil": namn, "byte": len(b)}); buf, storlek = [], 0
    idx = []
    for d in sorted(docs, key=lambda d: (d["slag"] == "media", d["ar"])):
        st = [[r["nr"], r["text"], r["fragor"], r["partier"]] for r in d["stycken"]]
        buf.append([len(idx), st]); storlek += sum(len(r[1]) for r in st)
        idx.append({"id": d["id"], "s": d["slag"], "u": d.get("undertyp") or "", "p": d["partier"], "y": d["ar"], "d": d["datum"],
                    "t": d["titel"][:300], "l": d["url"], "pdf": d.get("pdf") or "", "k": d.get("kalla") or "", "q": d["fragor"],
                    "a": d["andel"], "n": len(d["stycken"]), "f": len(filer), "in": (d.get("ingress") or "")[:300]})
        if storlek > 8_000_000: spara()
    spara()
    (WEBB / "index.json").write_text(json.dumps({
        "uppdaterad": date.today().isoformat(),
        "partier": [{"k": k, "kod": p["kod"], "namn": p["namn"]} for k, p in PARTIER.items()],
        "fragor": [{"k": k, "namn": n, "rx": rx} for k, (n, rx) in FRAGOR.items()],
        "slag": SLAGNAMN, "filer": filer, "docs": idx, "fokus": fok}, ensure_ascii=False, separators=(",", ":")))
    print(f"webb: {len(idx)} dokument, {len(filer)} styckefiler, {sum(f['byte'] for f in filer) / 1e6:.0f} MB")


if __name__ == "__main__":
    docs = bearbeta(dokumenten())
    print(Counter(d["slag"] for d in docs))
    fok = fokus(docs)
    sqlite(docs, fok); csvfil(docs); webb(docs, fok)
