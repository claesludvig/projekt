"""Tolkare för källor utan API: Valu-rapporter, Valforskningsprogrammets
rapport om partiernas väljare, Brå:s NTU-tabellsamling och Valmyndighetens
rådata. Alla läser filer som hamta.py har lagt i data/kallor."""

import re
from pathlib import Path

import pandas as pd

KALL_DIR = Path(__file__).resolve().parent / "data" / "kallor"

PARTIKOD = {
    "V": "V", "S": "S", "MP": "MP", "C": "C", "L": "L", "FP/L": "L", "FP": "L",
    "KD": "KD", "M": "M", "SD": "SD", "FI": "FI", "ÖVR": "ÖVR", "ÖVRIGA": "ÖVR",
    "NYD": "NYD",
    "VÄNSTERPARTIET": "V", "SOCIALDEMOKRATERNA": "S",
    "ARBETAREPARTIET-SOCIALDEMOKRATERNA": "S", "MILJÖPARTIET": "MP",
    "MILJÖPARTIET DE GRÖNA": "MP", "CENTERPARTIET": "C", "LIBERALERNA": "L",
    "LIBERALERNA (TIDIGARE FOLKPARTIET)": "L", "FOLKPARTIET": "L",
    "KRISTDEMOKRATERNA": "KD", "MODERATERNA": "M", "SVERIGEDEMOKRATERNA": "SD",
    "ÖVRIGA PARTIER": "ÖVR", "ÖVRIGA ANMÄLDA PARTIER": "ÖVR",
}


def partikod(namn: str) -> str | None:
    return PARTIKOD.get(str(namn).strip().upper())


def _sidor(txt: Path) -> list[tuple[int, list[str]]]:
    """Text per sida, med hopslagna mellanrum och utan tomrader."""
    sidor, nr, rader = [], 0, []
    for rad in txt.read_text(encoding="utf-8").splitlines():
        m = re.match(r"===== sida (\d+) =====", rad)
        if m:
            if nr:
                sidor.append((nr, rader))
            nr, rader = int(m.group(1)), []
            continue
        rad = re.sub(r"\s+", " ", rad).strip()
        if rad:
            rader.append(rad)
    if nr:
        sidor.append((nr, rader))
    return sidor


def _tal(s: str) -> float | None:
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ---------- Valu ----------

VALU_DIMENSION = {
    "Kön och ålder": "kön/ålder", "Yrke och fack": "yrke/fack",
    "Utbildning": "utbildning", "Sektor": "sektor",
    "Invandrarröstning 1": "egen uppväxt", "Invandrarröstning 2": "familjens uppväxt",
    "Kyrkogång": "kyrkogång",
}
VALU_SERIE = {
    "Hur röstade kvinnor?": ("kön", "Kvinnor"),
    "Hur röstade män?": ("kön", "Män"),
    "Hur röstade unga förstagångsväljare?": ("ålder", "Unga förstagångsväljare"),
    "Hur röstade väljare 65 år och äldre?": ("ålder", "65+"),
    "Hur röstade LO-medlemmar?": ("fack", "LO"),
    "Hur röstade företagare?": ("yrke", "Företagare"),
}


def valu(txt: Path, kalla_id: str) -> tuple[pd.DataFrame, list[str]]:
    """Partival per väljargrupp ur en Valu-rapport.

    Två tabelltyper: tvärsnitt ("Partival i riksdagsvalet ÅÅÅÅ" med partier som
    kolumner och grupper som rader) och tidsserier ("Hur röstade X?" med år som
    kolumner och partier som rader)."""
    rader, varningar = [], []
    for sidnr, text in _sidor(txt):
        if not text:
            continue
        rubrik = text[0]
        # --- tidsserier
        if rubrik in VALU_SERIE:
            dim, grupp = VALU_SERIE[rubrik]
            hdr = next((r for r in text if r.startswith("Parti ")), None)
            if not hdr:
                continue
            ar = [int(a) for a in re.findall(r"\b(19\d\d|20\d\d)\b", hdr)]
            # "22001188" = dubbeltryckt 2018 i pdf:en
            hdr_tok = hdr.split()[1:]
            ar = []
            for t in hdr_tok:
                if re.fullmatch(r"(19|20)\d\d", t):
                    ar.append(int(t))
                elif re.fullmatch(r"(\d)\1(\d)\2(\d)\3(\d)\4", t):
                    ar.append(int(t[::2]))
            for r in text:
                tok = r.split()
                p = partikod(tok[0]) if tok else None
                if not p or len(tok) - 1 != len(ar):
                    continue
                for a, v in zip(ar, tok[1:]):
                    rader.append({"kalla": kalla_id, "sida": sidnr, "val": "RD", "ar": a,
                                  "dimension": dim, "grupp": grupp, "parti": p,
                                  "andel": _tal(v)})
            continue
        # --- tvärsnitt
        valar = next((int(m.group(1)) for r in text[:4]
                      if (m := re.search(r"Partival i (?:riksdagsvalet|EU-parlamentsvalet) (\d{4})", r))), None)
        partihdr = next((r for r in text[:8] if re.search(r"\bV S MP C\b", r)), None)
        if not valar or not partihdr or rubrik.startswith(("Väljarströmmar", "Politiska")):
            continue
        dim = VALU_DIMENSION.get(rubrik, rubrik.lower())
        partier = [partikod(t) for t in partihdr.split() if partikod(t)]
        har_antal = "personer" in partihdr or any("Antal" in r for r in text[:6])
        start = text.index(partihdr) + 1
        prefix, forall, sedda = [], "", set()
        for r in text[start:]:
            tok = r.split()
            if "~100" not in tok:
                if re.fullmatch(r"[\d\s]+", r):     # sidnummer
                    continue
                if r.startswith(("Kommentar", "Vägda resultat")):
                    break
                prefix.append(r)
                continue
            i = tok.index("~100")
            antal = _tal("".join(tok[i + 1:])) if har_antal and len(tok) > i + 1 else None
            siffror = tok[:i]
            varden = siffror[-len(partier):]
            etikett = " ".join(prefix + siffror[: len(siffror) - len(partier)]).strip()
            prefix = []
            if any(_tal(v) is None for v in varden) or len(varden) != len(partier):
                varningar.append(f"{kalla_id} s.{sidnr}: kunde inte tolka '{r}'")
                continue
            # Radetiketter som "Kvinnor 18 - 30" följs av "31 - 64": ärv förled
            m = re.match(r"^(Kvinnor|Män)\s+(\d.*)$", etikett)
            if m:
                forall, etikett = m.group(1), f"{m.group(1)} {m.group(2)}"
            elif forall and re.match(r"^\d", etikett) and dim == "kön/ålder" and \
                    any(x.startswith(forall) for x in sedda):
                etikett = f"{forall} {etikett}"
            if not etikett:
                varningar.append(f"{kalla_id} s.{sidnr}: rad utan etikett '{r}'")
                continue
            if etikett in sedda:        # "Privat" står två gånger i sektortabellen
                continue
            sedda.add(etikett)
            if len(varden) < len(partier):
                continue
            for p, v in zip(partier, varden):
                rader.append({"kalla": kalla_id, "sida": sidnr,
                              "val": "EP" if "EU" in partihdr else "RD", "ar": valar,
                              "dimension": dim, "grupp": etikett, "parti": p,
                              "andel": _tal(v), "antal_svar": antal})
    df = pd.DataFrame(rader)
    if len(df):
        df["grupp"] = df["grupp"].str.replace(r"(\d) - (\d)", r"\1–\2", regex=True)
    return df, varningar


# ---------- Valforskningsprogrammet: Partiernas väljare 2018–2022 ----------

GU_PARTI = {"Vänsterpartiets": "V", "Miljöpartiets": "MP", "Socialdemokraternas": "S",
            "Centerpartiets": "C", "Liberalernas": "L", "Kristdemokraternas": "KD",
            "Moderaternas": "M", "Sverigedemokraternas": "SD"}


def gu_partiernas_valjare(txt: Path, kalla_id: str) -> tuple[pd.DataFrame, list[str]]:
    """Tabell B.0–B.8: sammansättningen av alla väljare och varje partis
    väljare 2018 och 2022 (andel procent av partiets väljare i varje grupp)."""
    rader, varningar = [], []
    parti, dim = None, None
    for sidnr, text in _sidor(txt):
        for r in text:
            m = re.match(r"^Tabell (B\.\d) Sammansättningen", r)
            if m:
                parti = "ALLA" if m.group(1) == "B.0" else next(
                    (k for n, k in GU_PARTI.items() if n in r), "?")
                dim = None
                continue
            if re.match(r"^Tabell [A-Z]\.\d", r):
                parti = None
                continue
            if r.startswith("Kommentar"):
                parti = None
            if parti is None or r.startswith(("Antal svarande", "Fortsättning",
                                               "Alla-väljare", "Alla ", "procent")):
                continue
            if re.search(r"-väljare 2018", r):
                continue
            m = re.match(r"^(.*?[^\d\s–-])\s+(\d+)\s+(\d+)\s+[+\-–]?\s*\d+\s*\**\s*$", r)
            if m and dim:
                etikett = m.group(1).strip()
                for ar, v in ((2018, m.group(2)), (2022, m.group(3))):
                    rader.append({"kalla": kalla_id, "sida": sidnr, "ar": ar,
                                  "dimension": dim, "grupp": etikett, "parti": parti,
                                  "andel": float(v)})
            elif not re.search(r"\d", r) and len(r) < 40:
                dim = r.lower()
            elif re.search(r"\d", r) and dim and len(r) < 90:
                varningar.append(f"{kalla_id} s.{sidnr}: kunde inte tolka '{r}'")
    df = pd.DataFrame(rader)
    if len(df):
        # Radbrytningar i pdf:en kan ge dubbletter; behåll första
        df = df.drop_duplicates(["ar", "dimension", "grupp", "parti"])
    return df, varningar


# ---------- Brå NTU ----------

NTU_DIM = [
    (r"år$", "ålder"), (r"född|Utrikes", "födelseland"),
    (r"(?i)gymnasial", "utbildning"), (r"Sammanboende|Ensamstående", "familj"),
    (r"Småhus|Flerfamiljshus", "boendeform"), (r"städer|Storstäder|landsbygd", "kommungrupp"),
    (r"[Oo]mråden", "områdestyp"),
]


def ntu(xlsx: Path, kalla_id: str) -> tuple[pd.DataFrame, list[str]]:
    """Alla flikar 'andel ... inom olika grupper' i Brå:s tabellsamling."""
    rader, varningar = [], []
    bok = pd.ExcelFile(xlsx)
    for blad in bok.sheet_names:
        if not re.match(r"^[345][A-Z](\.1)?$", blad):
            continue
        df = pd.read_excel(bok, sheet_name=blad, header=None)
        rubrik = str(df.iloc[1, 0])
        if "olika grupper" not in rubrik:
            continue
        indikator = re.sub(r"^Tabell \S+\s*", "", rubrik.split("\n")[0])
        indikator = re.sub(r"\s*\(\d+(, \d+)*\)", "", indikator)
        indikator = re.sub(r",? (enligt NTU|\d{4}–\d{4}).*$", "", indikator).strip(" .")
        hdr_rad = next(i for i in range(2, 6) if any(
            re.match(r"^\d{4}", str(x)) for x in df.iloc[i]))
        kol = {}
        for j, x in enumerate(df.iloc[hdr_rad]):
            m = re.match(r"^(\d{4})(\*)?", str(x))
            if m and "Konfidens" not in str(x):
                kol[j] = (int(m.group(1)), bool(m.group(2)))
        for i in range(hdr_rad + 1, len(df)):
            etikett = df.iloc[i, 0]
            if not isinstance(etikett, str) or len(etikett) > 90:
                continue
            if " - " in etikett:
                kon, grupp = etikett.split(" - ", 1)
            elif etikett in ("Män", "Kvinnor"):
                kon, grupp = etikett, "Samtliga"
            else:
                kon, grupp = "Samtliga", etikett
            dim = "samtliga" if grupp.startswith("Samtliga") else next(
                (d for mönster, d in NTU_DIM if re.search(mönster, grupp)), "övrigt")
            for j, (ar, jfr) in kol.items():
                v = pd.to_numeric(df.iloc[i, j], errors="coerce")
                if pd.notna(v):
                    rader.append({"kalla": kalla_id, "tabell": blad.replace(".", ":"),
                                  "indikator": indikator, "kon": kon, "dimension": dim,
                                  "grupp": grupp, "ar": ar, "andel": float(v),
                                  "ej_jamforbar_bakat": jfr})
    return pd.DataFrame(rader), varningar


# ---------- Valmyndigheten 2026 ----------

def val2026_kommun(xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx, sheet_name="Per Kommun")
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    kol_antal = next(c for c in df.columns if c.startswith("Preliminärt antal"))
    kol_andel = next(c for c in df.columns if c.startswith("Preliminär andel"))
    ut = pd.DataFrame({
        "ar": 2026, "kommunkod": df["Kommunkod"].astype(str).str.zfill(4),
        "kommun": df["Kommunnamn"], "kategori": df["Parti/Kategori"],
        "roster": pd.to_numeric(df[kol_antal], errors="coerce"),
        "andel": pd.to_numeric(df[kol_andel], errors="coerce") * 100,
    })
    ut["parti"] = ut["kategori"].map(partikod)
    ut["status"] = "preliminärt"
    return ut


# ---------- Valu: viktiga frågor och bäst politik ----------

def _fraga_namn(s: str) -> str:
    s = re.sub(r"^\d+\.\s*", "", s).strip()
    s = s.replace("Åldreomsorgen", "Äldreomsorgen").replace("Sysselsättningen", "Sysselsättning")
    s = s.replace("Svensk ekonomi", "Svenska ekonomin").replace("Vinster i välfärden",
                                                                 "Frågan om vinster i välfärden")
    return s


def valu_fragor(txt: Path, kalla_id: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(betydelse per fråga och år, rang per parti, bäst politik per område och parti).

    Betydelse: andel som anger att frågan har mycket stor betydelse för partivalet.
    Rang: frågans rangordning bland partiets väljare (1 = viktigast).
    Bäst politik: andel som anger att partiet har bäst politik på området."""
    betydelse, rang, bast = [], [], []
    for sidnr, text in _sidor(txt):
        if not text:
            continue
        rub = text[0]
        if rub.startswith("Viktiga frågor för valet av parti"):
            hdr = next((r for r in text if r.startswith("Fråga ")), "")
            tok = hdr.split()[1:]
            ar = []
            for t in tok:                      # årskolumner; sluta vid förändringskolumnen
                if re.fullmatch(r"(19|20)\d\d", t):
                    if ar and int(t) <= ar[-1]:
                        break
                    ar.append(int(t))
            partier = [partikod(t) for t in tok if partikod(t)]
            for r in text:
                m = re.match(r"^(\d+\.\s*.+?)\s+((?:[-\d+]+\s*)+)$", r)
                if not m:
                    continue
                namn = _fraga_namn(m.group(1))
                v = m.group(2).split()
                if ar and len(ar) <= len(v):
                    for a, x in zip(ar, v[:len(ar)]):
                        if re.fullmatch(r"\d+", x):
                            betydelse.append({"kalla": kalla_id, "ar": a, "fraga": namn, "andel": float(x)})
                elif partier and len(v) == len(partier):
                    valar = int(re.search(r"(20\d\d)", kalla_id.replace("2014_", "")).group(1)) \
                        if re.search(r"20\d\d", kalla_id) else None
                    for p, x in zip(partier, v):
                        rang.append({"kalla": kalla_id, "fraga": namn, "parti": p, "rang": int(x),
                                     "sida": sidnr, "valar": valar})
        elif rub.startswith("Bäst politik"):
            hdr = next((r for r in text if re.search(r"\bV S MP\b", r)), "")
            partier = [partikod(t) for t in hdr.split() if partikod(t)] + ["INGEN"]
            prefix = []
            for r in text[text.index(hdr) + 1:] if hdr in text else []:
                tok = r.split()
                if "~100" not in tok:
                    if not re.fullmatch(r"[\d\s]+", r) and not r.startswith(("Vägda", "Kommentar")):
                        prefix.append(r)
                    continue
                i = tok.index("~100")
                v = tok[i - len(partier):i]
                namn = " ".join(prefix + tok[:i - len(partier)]).strip()
                prefix = []
                if all(re.fullmatch(r"\d+", x) for x in v):
                    for p, x in zip(partier, v):
                        bast.append({"kalla": kalla_id, "omrade": _fraga_namn(namn), "parti": p,
                                     "andel": float(x)})
    return pd.DataFrame(betydelse), pd.DataFrame(rang), pd.DataFrame(bast)


# ---------- SOM-institutet: viktigaste samhällsproblem ----------

def som_samhallsproblem(txt: Path, kalla_id: str) -> pd.DataFrame:
    """Andel som nämner området bland de (högst tre) viktigaste samhällsproblemen, 1987–.

    Årtalen i tabellhuvudet är roterade i pdf:en och läses baklänges ("7891" = 1987)."""
    rader = []
    for sidnr, text in _sidor(txt):
        if not any("VIKTIGASTE SAMHÄLLSPROBLEM" in r for r in text):
            continue
        ar = []
        for r in text:
            tok = r.split()
            if len(tok) > 10 and all(re.fullmatch(r"\d{4}", t) for t in tok):
                kand = [int(t[::-1]) for t in tok]
                if all(1980 <= a <= 2035 for a in kand) and kand == sorted(kand):
                    ar = kand
                    break
        if not ar:
            continue
        for r in text:
            m = re.match(r"^([A-ZÅÄÖ][^\d]+?)\s+([\d\s]+)$", r)
            if not m or m.group(1).startswith(("Antal", "År")):
                continue
            v = m.group(2).split()
            if len(v) != len(ar):
                continue
            for a, x in zip(ar, v):
                rader.append({"kalla": kalla_id, "ar": a, "omrade": m.group(1).strip(), "andel": float(x)})
    return pd.DataFrame(rader)
