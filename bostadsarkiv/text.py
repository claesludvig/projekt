"""Textbehandling för bostadsarkivet: HTML till text, termträffar, relevans
och uppdelning av riksdagsprotokoll i anföranden."""

import html as htmlmod
import re

import katalog

_KARNA = {k: re.compile(v) for k, v in katalog.KARNA.items()}
_BRED = {k: re.compile(v) for k, v in katalog.BRED.items()}


# --- Text ---------------------------------------------------------------------

def html_till_text(h):
    """Riksdagens HTML till text. Rubriker blir egna stycken som börjar med
    '# ', stycken skiljs med tom rad."""
    h = re.sub(r"(?is)<(style|script|head)\b.*?</\1>", " ", h)
    h = re.sub(r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>",
               lambda m: "\n\n# " + re.sub(r"<[^>]+>", " ", m.group(1)) + "\n\n", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|li|tr|table|h[1-6])>", "\n\n", h)
    h = re.sub(r"(?i)<(td|th)[^>]*>", " ", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = htmlmod.unescape(h).replace("\xa0", " ")
    return stada(h)


def stada(t):
    """Slå ihop avstavning vid radbrytning och rader inom stycken."""
    t = t.replace("\r", "")
    t = re.sub(r"(\w)-[ \t]*\n[ \t]*(?=[a-zåäöé])", r"\1", t)
    stycken = []
    for s in re.split(r"\n[ \t]*\n+", t):
        s = re.sub(r"[ \t]*\n[ \t]*", " ", s)
        s = re.sub(r"[ \t]+", " ", s).strip()
        if s and s != "#":
            stycken.append(s)
    return "\n\n".join(stycken)


def normalisera(t):
    t = t.lower()
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)
    return re.sub(r"\s+", " ", t)


def antal_ord(t):
    return len(re.findall(r"\w+", t))


# --- Träffar och relevans -----------------------------------------------------

def rakna(t, redan_normaliserad=False):
    """Antal träffar per kärn- och bredterm."""
    n = t if redan_normaliserad else normalisera(t)
    karna = {k: len(p.findall(n)) for k, p in _KARNA.items()}
    bred = {k: len(p.findall(n)) for k, p in _BRED.items()}
    return {k: v for k, v in karna.items() if v}, {k: v for k, v in bred.items() if v}


def titeltraff(titel):
    n = normalisera(titel or "")
    return any(p.search(n) for p in list(_KARNA.values()) + list(_BRED.values()))


def termstrang(d):
    return ";".join(f"{k}:{v}" for k, v in sorted(d.items(), key=lambda x: -x[1]))


def anforande_relevant(karna, bred):
    if sum(karna.values()) >= katalog.ANF_MIN_KARNA:
        return True
    return (sum(bred.values()) >= katalog.ANF_MIN_BRED
            and len(bred) >= katalog.ANF_MIN_BRED_KATEGORIER)


def tathet(karna, ord_):
    return 10000 * sum(karna.values()) / max(ord_, 1)


def dokument_relevant(karna, ord_, titel_traff):
    k = sum(karna.values())
    if titel_traff or k >= katalog.DOK_MIN_KARNA:
        return True
    return k >= 2 and tathet(karna, ord_) >= katalog.DOK_MIN_TATHET


def anforande_grad(karna):
    k = sum(karna.values())
    return "hög" if k >= 3 else ("medel" if k >= 1 else "låg")


def grad(karna, ord_, titel_traff=False):
    t = tathet(karna, ord_)
    if titel_traff or t >= katalog.GRAD_HOG:
        return "hög"
    return "medel" if t >= katalog.GRAD_MEDEL else "låg"


def dela_avsnitt_rubrik(t):
    """Dela text vid rubriker; returnerar (rubrik, text)."""
    ut, rub, buf = [], "", []
    for st in t.split("\n\n"):
        if st.startswith("# ") or _PARAGRAF.match(st):
            if buf:
                ut.append((rub, "\n\n".join(buf)))
            rub, buf = (st[2:] if st.startswith("# ") else st)[:200], []
        else:
            buf.append(st)
    if buf:
        ut.append((rub, "\n\n".join(buf)))
    return ut


# --- Protokoll ----------------------------------------------------------------

_ANF = re.compile(r"^Anf\.\s*(\d+)\s+(.{2,160}?):\s*(.*)$", re.S)
_PARTI = re.compile(r"\(([A-Za-zÅÄÖåäö]{1,4})\)")
_PARAGRAF = re.compile(r"^(?:\d+\s*§|§\s*\d+)\s")


def _tolka_talare(huvud):
    replik = bool(re.search(r"\breplik\b", huvud, re.I))
    m = _PARTI.search(huvud)
    parti = m.group(1).upper() if m else ""
    namn = _PARTI.sub("", huvud)
    namn = re.sub(r"\breplik\b", "", namn, flags=re.I)
    namn = re.sub(r"\s+", " ", namn).strip(" ,")
    # Versaler i protokollen ("PER-OLA ERIKSSON") blir "Per-Ola Eriksson";
    # titlar som "Statsrådet" eller "Bostadsminister" behålls.
    namn = " ".join(w.title() if w.isupper() and len(w) > 1 else w for w in namn.split())
    return namn, parti, replik


def dela_protokoll(text):
    """Dela upp protokolltext (från html_till_text) i anföranden.

    Returnerar en lista med dict: nr, talare, parti, replik, rubrik, text.
    Ett anförande slutar vid nästa 'Anf.', vid en rubrik eller vid en ny
    paragraf i protokollet (t.ex. '5 § Beslut om ...')."""
    anf, aktuell, rubrik = [], None, ""
    for st in text.split("\n\n"):
        if st.startswith("# "):
            rub = st[2:].strip()
            if aktuell:
                anf.append(aktuell)
                aktuell = None
            if rub and not re.match(r"^(Anf\.|Prot\.|Protokoll|Riksdagens protokoll)", rub):
                rubrik = rub
            m = _ANF.match(rub)
            if not m:
                continue
            st = rub
        m = _ANF.match(st)
        if m:
            if aktuell:
                anf.append(aktuell)
            namn, parti, replik = _tolka_talare(m.group(2))
            aktuell = {"nr": int(m.group(1)), "talare": namn, "parti": parti,
                       "replik": replik, "rubrik": rubrik, "stycken": []}
            if m.group(3).strip():
                aktuell["stycken"].append(m.group(3).strip())
            continue
        if _PARAGRAF.match(st):
            if aktuell:
                anf.append(aktuell)
                aktuell = None
            rubrik = st[:200]
            continue
        if aktuell:
            aktuell["stycken"].append(st)
    if aktuell:
        anf.append(aktuell)
    for a in anf:
        a["text"] = _sy_ihop(a.pop("stycken"), a["rubrik"])
    return [a for a in anf if a["text"]]


# Sidhuvuden i de inskannade protokollen ("Prot. 1991/92:49", "19 december
# 1991", "1 Riksdagens protokoll 1991192. Nr 49").
_SIDHUVUD = re.compile(
    r"^(?:Prot\.\s*\d{4}\s*/\s*\d{2,4}\s*:\s*\d+"
    r"|\d{1,2}\s+(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4}"
    r"|\d*\s*Riksdagens protokoll\s+\d{4}.{0,20}Nr\s*\d+"
    r"|\d{1,4})$", re.I)


_SIDHUVUD_I_TEXT = re.compile(
    r"\s*(?:Prot\.|Prof\.)\s*\d{4}\s*/\s*\d{2,4}\s*:\s*\d+"
    r"(?:\s+\d{1,2}\s+(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4})?\s*")


def rensa_sidhuvud(t):
    """Ta bort sidhuvuden som OCR:en lagt mitt i ett stycke."""
    return _SIDHUVUD_I_TEXT.sub(" ", t).replace("  ", " ")


def _sy_ihop(stycken, rubrik):
    """Ta bort sidhuvuden och kantrubriker och laga stycken som brutits vid
    sidbyte."""
    kant = re.sub(r"^(?:\d+\s*§|§\s*\d+)\s*", "", rubrik or "").strip().lower()
    ut = []
    for s in stycken:
        if _SIDHUVUD.match(s) or (kant and s.strip().lower() == kant):
            continue
        if ut and not re.search(r"[.!?:”\")]$", ut[-1]) and re.match(r"^[a-zåäö]", s):
            ut[-1] = ut[-1] + " " + s
        else:
            ut.append(s)
    return rensa_sidhuvud("\n\n".join(ut))
