"""Partiernas program: kontroll av citat och jämförelse mellan partierna (underlag: partier_katalog)."""

import json
import re
from itertools import combinations
from pathlib import Path

import pandas as pd

from partier_katalog import POLITIK_OMRADEN, PROGRAM, PROGRAM_NAMN, STANDPUNKTER

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]


def normalisera(t: str) -> str:
    """Samma jämförelseform för citat och källtext: utan mjuka bindestreck, nollbredds- och punkttecken,
    avstavning vid radbrytning och med ett mellanslag mellan orden."""
    t = re.sub("­\\s*", "", t).replace("​", "").replace(" ", " ")
    t = re.sub(r"===== sida \d+ =====", " ", t)
    t = re.sub(r"[●•à]\s", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def texter(kall_dir: Path) -> dict[str, dict[str, str]]:
    """Parti -> {dokument-id: normaliserad text} för de program som finns hämtade. Partiets ämnessidor
    (Politik A–Ö) ingår också, med sidans adress som dokument-id."""
    ut = {}
    for p, dok in PROGRAM.items():
        ut[p] = {d: normalisera(f.read_text(encoding="utf-8")) for d in dok
                 if (f := kall_dir / "txt" / f"{d}.txt").exists()}
        for u, sida in _politik_rå(kall_dir, p).items():
            ut[p][u] = normalisera(sida["text"])
    return ut


# ---------- Partiernas samlada politik (Politik A–Ö) ----------

# Rubriker där sidans egentliga innehåll tar slut (nyhetsflöden, relaterade sidor, kontaktrutor)
SLUT = re.compile(r"^\s*(## )?(läs mer\s*$|uppdaterad:|senast uppdaterad|andra läste även|vi har svaren|hittade du den information|uppdaterades senast|slutet på menyn|dela länken)|"
                  r"^## (senaste nytt|nyheter|relaterade|mer om|läs mer|läs också|aktuellt|kontakt|"
                  r"talesperson|våra talesperson|dela|prenumerera|bli medlem|engagera dig|här kan du läsa|"
                  r"fler nyheter|artiklar|debattartiklar|pressmeddelanden|mer från|se även|tillbaka)", re.I | re.M)
BRUS = re.compile(r"^(←|tillbaka till a-ö|hem|hoppa över menyn|politik som gör skillnad|vår politik|"
                  r"politik a[–-]ö|a till ö|dela|dela på .*|kopiera länk|skriv ut|\d{4}-\d\d-\d\d|"
                  r"(senast )?(uppdaterad|publicerad)?:? ?\d{1,2} (januari|februari|mars|april|maj|juni|juli|augusti|"
                  r"september|oktober|november|december) \d{4})$", re.I)
VILL = re.compile(r"(vill|föreslår|anser att|kräver|driver|vi ska|det här gör vi|så här|våra förslag|vår politik för)"
                  r"[^.]{0,40}:?$", re.I)


def _politik_rå(kall_dir: Path, parti: str) -> dict:
    f = kall_dir / "politik" / f"{parti}.json"
    return json.loads(f.read_text(encoding="utf-8"))["sidor"] if f.exists() else {}


def rensa_sida(text: str, titel: str) -> list[str]:
    """Ämnessidans stycken utan navigering, dubblerad rubrik och det som följer efter innehållet."""
    m = SLUT.search(text)
    if m:
        text = text[:m.start()]
    stycken, sedda = [], set()
    for rad in text.split("\n"):
        rad = re.sub(r"\s+", " ", rad).strip().lstrip("←").strip()
        if not rad or BRUS.match(rad) or re.search(r" \| (Sverigedemokraterna|Moderaterna|Liberalerna|Centerpartiet|"
                                                   r"Kristdemokraterna|Miljöpartiet|Socialdemokraterna|Vänsterpartiet)$", rad) or rad.lstrip("# ").strip().lower() in (titel.lower(), ""):
            continue
        if rad in sedda:
            continue
        sedda.add(rad)
        if rad.endswith("...") or rad.endswith("…"):   # avkortade puffar för andra sidor
            continue
        stycken.append(rad)
    # Rubriker utan eget innehåll (följs direkt av en annan rubrik eller sidans slut)
    return [x for i, x in enumerate(stycken)
            if not (x.startswith("## ") and (i + 1 == len(stycken) or stycken[i + 1].startswith("## ")))]


def vill_lista(stycken: list[str]) -> list[str]:
    """Punkterna under rubriker som "Partiet vill:" eller efter en inledning som slutar med "vill vi:"."""
    ut, i = [], 0
    while i < len(stycken):
        s = stycken[i]
        rubrik = s.startswith("## ")
        if (rubrik and VILL.search(s[3:].strip())) or (not rubrik and s.endswith(":") and VILL.search(s)):
            j = i + 1
            while j < len(stycken) and not stycken[j].startswith("## ") and len(stycken[j]) < 400 \
                    and not (stycken[j].endswith(":") and VILL.search(stycken[j])):
                ut.append(stycken[j])
                j += 1
            i = j
        else:
            i += 1
    return [x for x in dict.fromkeys(ut) if len(x) > 8]


OMR_RE = [(oid, namn, re.compile(r, re.I)) for oid, namn, r in POLITIK_OMRADEN]


def omraden_for(titel: str, text: str) -> list[str]:
    """Områdena för en ämnessida: efter rubriken, annars efter vilket områdes mönster som oftast finns i texten."""
    traff = [oid for oid, _, r in OMR_RE if r.search(titel)]
    if traff:
        return traff
    antal = sorted(((len(r.findall(text)), oid) for oid, _, r in OMR_RE), reverse=True)
    return [antal[0][1]] if antal and antal[0][0] >= 3 else ["ovrigt"]


def politik(kall_dir: Path) -> pd.DataFrame:
    """En rad per parti och ämnessida: rubrik, adress, hämtdatum, områden, inledning, vill-punkter och hela texten."""
    rader = []
    for p in PARTIER:
        for u, sida in _politik_rå(kall_dir, p).items():
            titel = re.sub(r"\s+", " ", sida["titel"]).strip()
            st = rensa_sida(sida["text"], titel)
            if sum(len(x) for x in st) < 150:
                continue
            ingress = next((x for x in st if not x.startswith("## ") and len(x) > 60), "")
            rader.append({"parti": p, "titel": titel, "url": u, "hamtad": sida["hamtad"][:10],
                          "omraden": omraden_for(titel, " ".join(st)), "ingress": ingress,
                          "vill": vill_lista(st), "stycken": st, "ord": sum(len(x.split()) for x in st)})
    return pd.DataFrame(rader)


def tabell(kall_dir: Path, dokument: list[dict] | None = None) -> pd.DataFrame:
    """En rad per område, fråga och parti med svar, citat och det dokument citatet finns i (None om det inte hittas)."""
    tx = texter(kall_dir)
    url = {d["id"]: d["url"] for d in (dokument or [])}
    rader = []
    for omr, omr_namn, fragor in STANDPUNKTER:
        for fid, forslag, svar in fragor:
            for p in PARTIER:
                s, citat = svar.get(p, (None, None))
                kalla = next((d for d, t in tx.get(p, {}).items() if citat and normalisera(citat) in t), None)
                rader.append({"omrade": omr, "omrade_namn": omr_namn, "fraga": fid, "forslag": forslag, "parti": p,
                              "svar": s, "citat": citat, "dokument": kalla,
                              "url": kalla if kalla and kalla.startswith("http") else url.get(kalla),
                              "program_hamtat": bool(tx.get(p))})
    return pd.DataFrame(rader)


def likhet(t: pd.DataFrame) -> pd.DataFrame:
    """Parvis: andel av frågorna där båda partierna tar ställning och svarar lika (delvis räknas som eget svar)."""
    rader = []
    for a, b in combinations(PARTIER, 2):
        x = t[t.parti == a].set_index(["fraga"]).svar
        y = t[t.parti == b].set_index(["fraga"]).svar
        bada = x.notna() & y.notna()
        n = int(bada.sum())
        rader.append({"parti_a": a, "parti_b": b, "fragor": n,
                      "lika": int((x[bada] == y[bada]).sum()), "andel_lika": 100 * (x[bada] == y[bada]).mean() if n else None})
    return pd.DataFrame(rader)
