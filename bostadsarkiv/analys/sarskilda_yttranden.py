#!/usr/bin/env python3
"""Plockar ut reservationer och särskilda yttranden ur utredningarna (SOU)
och kopplar författarna till organisation eller parti.

Steg
1. Varje relevant SOU till och med 1992 läses (data/text/sou). Yttrandena står
   samlade efter betänkandet under rubriker som "Reservation av herrar Cassel
   och Gustafsson" eller "Särskilt yttrande av herr Petzäll". Innehållsförteck-
   ningens rader känns igen på att de följer tätt på varandra och hoppas över.
2. Ledamotsförteckningen i skrivelsen till statsrådet ("tillkallades såsom
   sakkunniga ... direktören Ingvar Petzäll ...") ger förnamn och titel.
3. Personen söks upp i hela arkivet (sökindexet) och de aktörsgrupper som nämns
   närmast namnet räknas (aktorer.py). Riksdagsledamöter får parti ur
   anförandena.

Resultat: data/sarskilda_yttranden.jsonl.gz, en rad per yttrande.

    python analys/sarskilda_yttranden.py
"""

import collections
import csv
import gzip
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import aktorer  # noqa: E402
import kapitel  # noqa: E402
import text  # noqa: E402

DATA = BASE / "data"
DB = DATA / "bostadsarkiv.sqlite"
UT = DATA / "sarskilda_yttranden.jsonl.gz"
SIST_AR = 1992
MAX_TECKEN = 40_000

_KAP = [(a["nr"], a["fran"], a["till"], re.compile(a["mönster"])) for a in kapitel.AVSNITT]

TILLTAL = r"(?:herr|herrar|fru|fröken|fruarna|ledamoten|ledamöterna|experten|experterna|sakkunnige|sakkunniga)"
_RUBRIK = re.compile(
    r"(?P<typ>Reservationer|Reservation|Särskilda yttranden|Särskilt yttrande|Gemensamt särskilt yttrande)"
    r"(?P<mellan>(?:\s+[a-zåäö]+){0,3}?)\s+[Aa]v\s+")
_TOKEN = re.compile(r"\s*(,|och\b|samt\b|dels\b|ock\b|med\b|instämmande\b|av\b|varmed\b|instämmer\b|"
                    r"herr\b|herrar\b|fru\b|fröken\b|ledamoten\b|ledamöterna\b|experten\b|experterna\b|"
                    r"sakkunnige\b|sakkunniga\b|i\s+[A-ZÅÄÖ][\w\-]+|[A-ZÅÄÖ][\w\-]+)")


_EFTER_NAMN = re.compile(r"\s+(?:med instämmande av|varmed instämmer|med instämmande)\s+", re.I)


def sparra_bort(t):
    """'S ä r s k i l t  y t t r a n d e' (spärrad OCR) blir vanliga ord."""
    return re.sub(r"(?:\b\w ){3,}\w\b", lambda m: m.group(0).replace(" ", ""), t)


def kanda_efternamn(t):
    """Efternamn som står efter ett förnamn i betänkandets början."""
    huvud = re.sub(r"\s+", " ", t[:80_000])
    return {m.group(2) for m in re.finditer(r"\b([A-ZÅÄÖ][a-zåäöéü]+(?:-[A-ZÅÄÖ][a-zåäöéü]+)?) "
                                            r"((?:von |af |de )?[A-ZÅÄÖ][a-zåäöéü]+(?:-[A-ZÅÄÖ][a-zåäöéü]+)?)\b", huvud)}


def las_namn(t, pos, kanda):
    """Läs namnlistan från pos så länge orden är kända efternamn, förnamn före
    ett känt efternamn eller bindeord. Returnerar (rubriktext, slutposition)."""
    i, sista, n = pos, pos, 0
    while True:
        m = _TOKEN.match(t, i)
        if not m:
            break
        tok = m.group(1)
        if tok[0].isupper() and not tok.startswith("i "):
            if tok in kanda:
                n += 1
                sista = m.end()
            else:
                nasta = _TOKEN.match(t, m.end())
                if not (nasta and nasta.group(1) in kanda):
                    break
        elif tok.startswith("i ") and n:
            sista = m.end()
        i = m.end()
    return (t[pos:sista], sista) if n else ("", pos)


def ar_av(d):
    m = re.match(r"(\d{4})", d or "")
    return int(m.group(1)) if m else 0


def normalisera_rubrik(s):
    """'S ä r s k i l t' och liknande spärrad OCR blir vanliga ord."""
    return re.sub(r"(?<=\b\w) (?=\w\b)", "", s)


def namnlista(s):
    """'herrar Andersson, Gustafsson och Olofgörs med instämmande av herr
    Källenius' -> (['Andersson', 'Gustafsson', 'Olofgörs'], ['Källenius'])."""
    s = re.sub(r"\s+", " ", s).strip(" .:")
    delar = _EFTER_NAMN.split(s, maxsplit=1)

    def lista(x):
        x = re.sub(rf"\b{TILLTAL}\b", " ", x, flags=re.I)
        x = re.sub(r"\b(?:samt|dels|ock|av)\b", ",", x, flags=re.I)
        ut = []
        for n in re.split(r",| och ", x):
            n = n.strip(" .:;-–")
            if 2 <= len(n) <= 40 and n[0].isupper() and not re.search(r"\d", n):
                ut.append(n.split()[-1] if not re.search(r" i ", n) else n.split(" i ")[0].split()[-1])
        return ut
    return lista(delar[0]), (lista(delar[1]) if len(delar) > 1 else [])


def hitta_yttranden(t):
    """Yttrandenas rubriker och texter. Rubriker som följs av en ny rubrik inom
    kort (innehållsförteckningen) hoppas över."""
    t = sparra_bort(t)
    kanda = kanda_efternamn(t)
    traffar = []
    for m in _RUBRIK.finditer(t):
        namn, slut = las_namn(t, m.end(), kanda)
        if namn:
            traffar.append((m, namn, slut))
    ut = []
    for i, (m, namn, slut) in enumerate(traffar):
        nasta = traffar[i + 1][0].start() if i + 1 < len(traffar) else len(t)
        kropp = t[slut:nasta]
        b = re.search(r"(?:Bilaga\s+\d|BILAGA\s+\d|Bilagor\b|Författningsförslag|Litteraturförteckning|"
                      r"Statens offentliga utredningar \d{4} Kronologisk)", kropp)
        if b and b.start() > 300:
            kropp = kropp[:b.start()]
        ren = re.sub(r"\[PDF-sida \d+\]", " ", kropp)
        if len(re.sub(r"\s+", "", ren)) < 600:
            continue
        borjan = ren[:300]
        if (len(re.findall(r"(?<!\S)\d{1,3}(?!\S)", borjan)) >= 5
                or re.search(r"bifogas|därmed slutfört|Stockholm den \d", borjan)):
            continue  # innehållsförteckning eller följebrev
        sida = re.findall(r"\[PDF-sida (\d+)\]", t[:m.start()])
        ut.append({"typ": "reservation" if m.group("typ").lower().startswith("reservation") else "särskilt yttrande",
                   "rubrik": re.sub(r"\s+", " ", t[m.start():slut]).strip(),
                   "vem": namn, "sida": sida[-1] if sida else "",
                   "text": re.sub(r"\s+", " ", ren).strip()[:MAX_TECKEN]})
    return ut


_TITLAR = (r"(?:[a-zåäö\.\-]+(?:\s[a-zåäö\.\-]+){0,6}?)")


def ledamoter(t, efternamn):
    """Presentationen av en person i betänkandets början: titel och förnamn."""
    huvud = re.sub(r"\s+", " ", t[:60_000])
    ut = {}
    for e in efternamn:
        m = None
        for m in re.finditer(rf"((?:[a-zåäö][a-zåäö\.\-]*\s){{1,7}})([A-ZÅÄÖ][\w\-]+(?:\s[A-ZÅÄÖ][\w\-]+)?)\s{re.escape(e)}\b", huvud):
            break
        if m:
            ut[e] = {"titel": m.group(1).strip(), "fornamn": m.group(2), "namn": f"{m.group(2)} {e}",
                     "presentation": huvud[max(0, m.start() - 40):m.end() + 120]}
    return ut


def organisation(db, namn, ar, presentation):
    """Aktörsgrupper och organisationsnamn som står närmast personens namn i
    arkivet, i första hand inom tio år från yttrandet."""
    grupper = collections.Counter()
    org = collections.Counter()
    for g in aktorer.grupper_i(presentation.lower()):
        grupper[g] += 3
    q = f'"{namn}"'
    try:
        rader = db.execute(
            "SELECT v.text, d.ar FROM sok_avs JOIN avsnitt v ON v.id = sok_avs.rowid "
            "JOIN dokument d ON d.id = v.dok_id WHERE sok_avs MATCH ? LIMIT 400", (q,)).fetchall()
    except sqlite3.OperationalError:
        rader = []
    if len(rader) < 3 and " " in namn:
        try:
            rader += db.execute(
                "SELECT v.text, d.ar FROM sok_avs JOIN avsnitt v ON v.id = sok_avs.rowid "
                "JOIN dokument d ON d.id = v.dok_id WHERE sok_avs MATCH ? LIMIT 400",
                (f'"{namn.split()[-1]}"',)).fetchall()
        except sqlite3.OperationalError:
            pass
        namn = namn.split()[-1]
    for x, a in rader:
        if a and abs(a - ar) > 12:
            continue
        x = re.sub(r"\s+", " ", x)
        for m in re.finditer(re.escape(namn), x):
            nara = x[max(0, m.start() - 160):m.end() + 60]
            for g in aktorer.grupper_i(nara.lower()):
                grupper[g] += 1
            for o in re.findall(r"((?:[Ss]venska|[Ss]veriges|[A-ZÅÄÖ][a-zåäö]+s)\s[A-ZÅÄÖa-zåäö\- ]{3,50}?"
                                r"(?:förening|förbund|föreningen|förbundet|delegation|delegationen|organisation|"
                                r"kassa|kassan|institut|bank|banken|riksförbund|centralorganisation))", nara):
                org[o.strip()] += 1
    return grupper, org


def parti(db, efternamn, ar, presentation):
    pres = presentation.lower()
    i = pres.find(efternamn.lower())
    fore = pres[max(0, i - 220):i] if i >= 0 else ""
    if "riksdag" not in fore and "kammare" not in fore:
        return ""
    m = re.search(rf"{re.escape(efternamn)}(?:\s+i\s+([A-ZÅÄÖ][\w\-]+))?", presentation)
    tal = efternamn + (f" i {m.group(1)}" if m and m.group(1) else "")
    r = db.execute("SELECT parti, COUNT(*) FROM anforanden WHERE talare LIKE ? AND ar BETWEEN ? AND ? "
                   "AND parti <> '' GROUP BY parti ORDER BY 2 DESC LIMIT 1",
                   (f"%{tal}%", ar - 6, ar + 6)).fetchone()
    return r[0] if r else "riksdagsledamot"


def main():
    db = sqlite3.connect(DB)
    rader = [r for r in csv.DictReader(open(DATA / "dokument.csv", encoding="utf-8"))
             if r["doktyp"] == "sou" and r["relevant"] == "1" and r["textfil"] and 0 < ar_av(r["datum"]) <= SIST_AR]
    print(f"{len(rader)} utredningar till och med {SIST_AR}", flush=True)
    n = 0
    with gzip.open(UT, "wt", encoding="utf-8") as ut:
        for i, r in enumerate(rader, 1):
            t = gzip.open(DATA / r["textfil"], "rt", encoding="utf-8").read().split("\n\n", 1)[-1]
            t = sparra_bort(text.sy_ihop_rader(t))
            ytt = hitta_yttranden(t)
            if not ytt:
                continue
            ar = ar_av(r["datum"])
            alla = sorted({e for y in ytt for lst in namnlista(y["vem"]) for e in lst})
            led = ledamoter(t, alla)
            personer = {}
            for e in alla:
                p = led.get(e, {"titel": "", "fornamn": "", "namn": e, "presentation": ""})
                g, o = organisation(db, p["namn"], ar, p["presentation"]) if p["fornamn"] else (collections.Counter(), collections.Counter())
                personer[e] = {**p, "grupper": dict(g.most_common(4)), "org": dict(o.most_common(3)),
                               "parti": parti(db, e, ar, p["presentation"])}
            for y in ytt:
                forf, inst = namnlista(y["vem"])
                low = y["text"].lower()
                kap = [nr for nr, f, tt, p in _KAP if f <= ar <= tt and p.search(low)]
                rad = {"sou": r["beteckning"], "id": r["id"], "titel": r["titel"], "ar": ar, "url": r["url"],
                       **y, "forfattare": forf, "instammer": inst,
                       "personer": {e: personer.get(e) for e in forf + inst},
                       "kapitel": kap, "karntraffar": len(re.findall("|".join(f"(?:{v})" for v in __import__("katalog").KARNA.values()), low))}
                ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
                n += 1
            if i % 50 == 0:
                print(f"  {i}/{len(rader)} utredningar, {n} yttranden", flush=True)
    print(f"Klart: {n} yttranden till {UT}")


if __name__ == "__main__":
    main()
