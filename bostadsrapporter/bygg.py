"""Bygger databasen av det hamta.py har laddat ner.

  data/bostadsrapporter.sqlite   dokument, sida och sida_fts (SQLite FTS5, fulltextsök per sida)
  data/csv/dokument.csv          förteckningen
  webb/data/index.json           förteckningen till sökgränssnittet
  webb/data/text-<aktör>-<n>.json texten per sida, laddas av gränssnittet
"""
import csv, gzip, json, re, sqlite3, unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

from hamta import DATA, pid
from katalog import AKTORER, SLUG, TEMAN, TERM_RX

ROT = Path(__file__).parent
WEBB = ROT / "webb" / "data"
MAX_FIL = 9_000_000

TEMA_RX = {k: re.compile(rx, re.I) for k, (_, rx) in TEMAN.items()}
DALIG_TITEL = re.compile(r"(\.indd|\.docx?|\.pptx?|\.pdf|microsoft|untitled|namnlös|creator|author|adobe|indesign|powerpoint|"
                         r"^dokument\d*$|^[\w-]+_[\w-]+|_final|^\d+$|^layout|^sida \d|^rapport$|^en rapport från)", re.I)


def _rensa(t):
    t = unicodedata.normalize("NFC", t or "").replace("­", "")
    t = re.sub("[\ufffd\u00ad\x00-\x08\x0b\x0e-\x1f]", "", t)
    t = re.sub(r"-\n(?=[a-zåäö])", "", t)          # avstavning
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _titel(r, info, sida1, flera=False):
    kand = []
    if flera:
        # Sidan länkar flera rapporter (årgångar, regioner): sidans rubrik + länktexten
        lt = (r.get("lanktext") or "").strip()
        if lt and len(lt) < 120 and lt.lower() not in (r.get("sidtitel") or "").lower() and not lt.lower().startswith(("ladda ner", "läs", "pdf")):
            st = (r.get("sidtitel") or "").strip()
            kand.append(lt if lt.lower().startswith(st.lower()[:20]) or len(lt) >= 40 else f"{st}: {lt}")
        kand.append(info.get("Title"))
    if not r.get("wp"): kand.append(r.get("sidtitel"))
    kand += [info.get("Title"), r.get("lanktext"), r.get("sidtitel")]
    for k in kand:
        k = (k or "").strip()
        if len(k) > 8 and " " in k and not DALIG_TITEL.search(k) and not k.islower() and not k.lower().startswith(("ladda ner", "läs ", "pdf")):
            return re.sub(r"\s+", " ", k)[:220]
    # första raden på första sidan som ser ut som en rubrik
    for rad in sida1.split("\n")[:15]:
        rad = rad.strip()
        if 12 < len(rad) < 140 and re.search(r"[a-zåäö]{4}", rad): return rad
    namn = unquote(Path(urlparse(r["pdf"]).path).stem)
    return re.sub(r"[_-]+", " ", namn)


def _datum(r, info, flera=False):
    d = r.get("datum")
    if d and d.endswith("-01-01"): d = None                       # bara år ur URL:en
    if d and not r.get("wp") and not flera: return d
    cd = info.get("CreationDate") or ""
    m = re.search(r"(\d{4})", cd); y = int(m[1]) if m else None
    mo = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+(\d+)", cd)
    if y and 1990 < y <= date.today().year:
        mm = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mo[1]) + 1 if mo else 1
        dd = int(mo[2]) if mo else 1
        pdfd = f"{y}-{mm:02d}-{dd:02d}"
        # WordPress-datum är uppladdningen; äldre rapporter flyttades in vid sajtbyten
        if not d or pdfd < d: return pdfd
    return d


TYP_REMISS = re.compile(r"remiss|yttrande|\bdnr\b|diarienummer|departementet|regeringskansliet|synpunkter på", re.I)
TYP_PROGNOS = re.compile(r"prognos|konjunktur|barometer|index|statistik|enkät|kvartalsrapport|läget på|marknadsrapport|"
                         r"undersökning|bostadsmarknadsenkät", re.I)


def _typ(titel, sida1):
    if TYP_REMISS.search(titel) or TYP_REMISS.search(sida1[:700]): return "rem"
    if TYP_PROGNOS.search(titel): return "prog"
    return "rap"


REMISSRAD = re.compile(r"^(remissvar|remissyttrande|yttrande|svar på remiss|angående|ang\.|betr|remiss|synpunkter)|"
                       r"\b(SOU|Ds) ?\d{4}:\d+|\bdnr\b", re.I)


def _remisstitel(titel, sida1):
    """Remissvar har ofta avsändare, datum eller departement som titel; ta ärendet från första sidan."""
    if re.search(r"[a-zåäö]{3,} [a-zåäö]{3,} [a-zåäö]{3,}", titel) and not re.search(r"departement|\d{4}-\d\d-\d\d", titel):
        return titel
    rader = [x.strip() for x in sida1.split("\n") if x.strip()][:45]
    for i, x in enumerate(rader):
        if REMISSRAD.search(x) and len(x) > 12 and not re.match(r"^(dnr|diarienr)", x, re.I):
            t = x if len(x) > 40 or i + 1 >= len(rader) else f"{x} {rader[i + 1]}"
            return re.sub(r"\s+", " ", t)[:220]
    return titel


def _ordmangd(t):
    return set(re.findall(r"[a-zåäö]{6,}", t.lower()))


def dokument():
    lista = json.loads((DATA / "pdf_lista.json").read_text())
    per_sida = Counter(r["sida"] for r in lista)
    ut = []
    for r in lista:
        f = DATA / "text" / r["aktor"] / f"{pid(r['pdf'])}.json.gz"
        if not f.exists(): continue
        d = json.load(gzip.open(f, "rt", encoding="utf8"))
        sidor = [_rensa(s) for s in d["sidor"]]
        while sidor and not sidor[-1]: sidor.pop()
        allt = "\n".join(sidor)
        if len(allt) < 400: continue                 # inskannad utan text, eller tom
        ord_ = len(allt.split())
        kn = len(TERM_RX.findall(allt))
        flera = per_sida[r["sida"]] > 1
        titel = _titel(r, d["info"], sidor[0] if sidor else "", flera)
        titeltraff = bool(SLUG.search(titel))
        tathet = 1000 * kn / max(ord_, 1)
        if kn < 4 and not (titeltraff and kn >= 1): continue
        g = 2 if (kn >= 40 and tathet >= 3) or (titeltraff and kn >= 15) else 1 if kn >= 12 or titeltraff else 0
        typ = _typ(titel, sidor[0] if sidor else "")
        if typ == "rem": titel = _remisstitel(titel, sidor[0] if sidor else "")
        teman = [k for k, rx in TEMA_RX.items() if len(rx.findall(allt)) >= max(3, ord_ / 4000)]
        ut.append({"id": pid(r["pdf"]), "aktor": r["aktor"], "titel": titel, "datum": _datum(r, d["info"], flera) or r.get("datum"),
                   "sida": r["sida"], "pdf": r["pdf"], "ingress": r.get("ingress") or "", "sidor": sidor,
                   "antal_sidor": len(sidor), "ord": ord_, "traffar": kn, "relevans": g, "teman": teman, "typ": typ,
                   "_ord": _ordmangd(allt)})
    # Samma rapport i flera versioner (läs-/utskriftsversion, uppslag/sidor, omladdad fil): behåll den första
    per = defaultdict(list)
    for x in ut: per[x["aktor"]].append(x)
    behall = []
    for k, xs in per.items():
        xs.sort(key=lambda x: (x["datum"] or "9", -x["antal_sidor"]))
        valda = []
        for x in xs:
            dubbel = False
            for v in valda:
                a, b = x["_ord"], v["_ord"]
                if a and b and len(a & b) / len(a | b) > 0.85:
                    v.setdefault("andra_pdf", []).append(x["pdf"]); dubbel = True; break
            if not dubbel: valda.append(x)
        behall += valda
    for x in behall: del x["_ord"]
    behall.sort(key=lambda x: (x["datum"] or "", x["aktor"]))
    return behall


def sqlite(docs):
    f = DATA / "bostadsrapporter.sqlite"
    f.unlink(missing_ok=True)
    c = sqlite3.connect(f)
    c.executescript("""
    CREATE TABLE aktor (aktor TEXT PRIMARY KEY, namn TEXT);
    CREATE TABLE dokument (id TEXT PRIMARY KEY, aktor TEXT REFERENCES aktor, titel TEXT, datum TEXT, ar INT,
        typ TEXT, relevans INT, traffar INT, antal_sidor INT, ord INT, teman TEXT, sida_url TEXT, pdf_url TEXT, ingress TEXT, andra_pdf TEXT);
    CREATE TABLE sida (id TEXT REFERENCES dokument, sidnr INT, text TEXT, PRIMARY KEY (id, sidnr));
    CREATE VIRTUAL TABLE sida_fts USING fts5(text, content='sida', content_rowid='rowid', tokenize='unicode61 remove_diacritics 0');
    CREATE TABLE tema (tema TEXT PRIMARY KEY, namn TEXT);
    """)
    c.executemany("INSERT INTO aktor VALUES (?,?)", [(k, a["namn"]) for k, a in AKTORER.items()])
    c.executemany("INSERT INTO tema VALUES (?,?)", [(k, n) for k, (n, _) in TEMAN.items()])
    for d in docs:
        c.execute("INSERT INTO dokument VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (d["id"], d["aktor"], d["titel"], d["datum"], int(d["datum"][:4]) if d["datum"] else None, d["typ"], d["relevans"],
                   d["traffar"], d["antal_sidor"], d["ord"], ",".join(d["teman"]), d["sida"], d["pdf"], d["ingress"],
                   "\n".join(d.get("andra_pdf", []))))
        c.executemany("INSERT INTO sida VALUES (?,?,?)", [(d["id"], i + 1, s) for i, s in enumerate(d["sidor"])])
    c.execute("INSERT INTO sida_fts(rowid, text) SELECT rowid, text FROM sida")
    c.execute("CREATE INDEX dokument_aktor ON dokument(aktor, datum)")
    c.commit(); c.execute("VACUUM"); c.close()
    print(f"{f}: {f.stat().st_size / 1e6:.0f} MB")


def csvfil(docs):
    (DATA / "csv").mkdir(exist_ok=True)
    with open(DATA / "csv" / "dokument.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "aktor", "namn", "datum", "titel", "typ", "relevans", "traffar", "antal_sidor", "teman", "sida_url", "pdf_url"])
        for d in docs:
            w.writerow([d["id"], d["aktor"], AKTORER[d["aktor"]]["namn"], d["datum"], d["titel"], d["typ"], d["relevans"],
                        d["traffar"], d["antal_sidor"], ",".join(d["teman"]), d["sida"], d["pdf"]])


def _utdrag(d, n=3):
    """De stycken som tar upp mest av ämnet, till listan innan texten är laddad."""
    st = []
    for i, s in enumerate(d["sidor"]):
        for p in re.split(r"\n\s*\n", s):
            p = re.sub(r"\s*\n\s*", " ", p).strip()
            if 120 < len(p) < 1400:
                st.append((len(TERM_RX.findall(p)), i + 1, p))
    st.sort(key=lambda x: (-x[0], x[1]))
    return [[s, p] for k, s, p in sorted(st[:n], key=lambda x: x[1]) if k]


def webb(docs):
    WEBB.mkdir(parents=True, exist_ok=True)
    for f in WEBB.glob("text-*.json"): f.unlink()
    filer, buf, storlek, nr = [], {}, 0, Counter()
    def spara(k):
        nonlocal buf, storlek
        if not buf: return
        nr[k] += 1; namn = f"text-{k}-{nr[k]}.json"
        b = json.dumps(buf, ensure_ascii=False, separators=(",", ":")).encode()
        (WEBB / namn).write_bytes(b)
        filer.append({"fil": namn, "aktor": k, "byte": len(b), "ids": list(buf)})
        buf, storlek = {}, 0
    for k in AKTORER:
        for d in (x for x in docs if x["aktor"] == k):
            buf[d["id"]] = d["sidor"]; storlek += sum(len(s) for s in d["sidor"]) * 1.05
            if storlek > MAX_FIL: spara(k)
        spara(k)
    fil_for = {i: n for n, f in enumerate(filer) for i in f["ids"]}
    for f in filer: del f["ids"]
    per_ar = defaultdict(lambda: defaultdict(int))
    for d in docs:
        if d["datum"]: per_ar[d["datum"][:4]][d["aktor"]] += 1
    idx = {
        "uppdaterad": date.today().isoformat(),
        "aktorer": [{"k": k, "namn": a["namn"], "antal": sum(d["aktor"] == k for d in docs)} for k, a in AKTORER.items()],
        "teman": [{"k": k, "namn": n, "antal": sum(k in d["teman"] for d in docs)} for k, (n, _) in TEMAN.items()],
        "per_ar": per_ar, "filer": filer,
        "typer": {t: sum(d["typ"] == t for d in docs) for t in ("rap", "prog", "rem")},
        "docs": [{"id": d["id"], "a": d["aktor"], "d": d["datum"] or "", "ti": d["titel"], "u": d["sida"], "pdf": d["pdf"],
                  "in": d["ingress"][:400], "g": d["relevans"], "t": d["typ"], "kn": d["traffar"], "s": d["antal_sidor"],
                  "tm": d["teman"], "f": fil_for[d["id"]], "ps": _utdrag(d)} for d in docs],
    }
    (WEBB / "index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")))
    print(f"webb: {len(docs)} dokument, {len(filer)} textfiler, {sum(f['byte'] for f in filer) / 1e6:.0f} MB")


if __name__ == "__main__":
    docs = dokument()
    print(Counter(d["aktor"] for d in docs), Counter(d["relevans"] for d in docs))
    sqlite(docs); csvfil(docs); webb(docs)
