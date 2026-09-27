#!/usr/bin/env python3
"""Väljardatabasen, steg 2: tolka rådata och bygg data/valjare.sqlite.

Läser det hamta.py lagt på disk (SCB-tabeller, Valu- och GU-rapporter som
text, Brå:s och Valmyndighetens Excelfiler) och bygger harmoniserade tabeller:

  kalla               källförteckning
  partistod           andel av en grupp som röstar/sympatiserar med ett parti
  gruppvikt           gruppens andel av väljarkåren
  partiprofil         andel av ett partis väljare som tillhör en grupp
                      (parti = 'ALLA' är hela väljarkåren)
  valresultat_kommun  riksdagsvalresultat per kommun 1973–2026
  kommunindikator     strukturvariabler per kommun och år
  kommunsamband       korrelation parti ↔ strukturvariabel över kommuner, per val
  utsatthet           Brå NTU: utsatthet, otrygghet, oro, förtroende per grupp
  partiexponering     partiväljarnas förväntade utsatthet givet sammansättning
  valdeltagande_grupp SCB register: röstberättigade och valdeltagande per grupp
  kontroll            kvalitetskontroller (t.ex. skattade vs registrerade vikter)

Skriver även data/csv/<tabell>.csv och data/webb.json (underlag för index.html)."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import tolka
from tolka import partikod

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCB_DIR = DATA_DIR / "scb"
KALL_DIR = DATA_DIR / "kallor"
CSV_DIR = DATA_DIR / "csv"
DB = DATA_DIR / "valjare.sqlite"

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]
Z = 1.96
varningar: list[str] = []


def scb(tab: str) -> pd.DataFrame | None:
    f = SCB_DIR / f"{tab}.csv.gz"
    if not f.exists():
        varningar.append(f"SCB-tabell {tab} saknas")
        return None
    df = pd.read_csv(f, dtype=str)
    df["varde"] = pd.to_numeric(df["varde"], errors="coerce")
    return df


def katalog() -> pd.DataFrame:
    f = DATA_DIR / "katalog" / "scb_katalog.csv"
    return pd.read_csv(f) if f.exists() else pd.DataFrame(columns=["id", "rubrik", "tema", "vald"])


def _ar_dec(tid: str) -> float:
    m = re.match(r"(\d{4})M(\d\d)", str(tid))
    return int(m.group(1)) + (int(m.group(2)) - 1) / 12 if m else float(str(tid)[:4])


# ---------- källor ----------

KALLOR = [
    ("scb_psu", "Partisympatiundersökningen (PSU)", "SCB",
     "https://www.scb.se/ME0201",
     "Urvalsundersökning två gånger per år (maj, nov). Partisympati per grupp med felmarginal. "
     "Åldersserien går tillbaka till 1972, övriga grupper till 2006."),
    ("svt_valu", "SVT:s vallokalsundersökning (Valu)", "SVT / Göteborgs universitet / KTH",
     "https://omoss.svt.se/",
     "Enkät till väljare vid vallokaler på valdagen och vid förtidsröstning. Tvärsnitt per "
     "väljargrupp för 2018, 2022 och 2026 samt tidsserier 1991–2026 för några grupper."),
    ("gu_partiernas_valjare", "Partiernas väljare 2018–2022 (rapport 2026:7)",
     "Valforskningsprogrammet, Göteborgs universitet",
     "https://www.gu.se/valforskningsprogrammet",
     "Sammansättningen av varje partis väljare 2018 och 2022, från sammanslagna SOM- och "
     "valundersökningar (ca 20 000 svarande per år)."),
    ("scb_register_val", "Valdeltagande i riksdagsval efter bakgrundsvariabler (ME0105)", "SCB",
     "https://www.statistikdatabasen.scb.se/",
     "Registerbaserat: röstberättigade och andel röstande per grupp 2018 och 2022."),
    ("scb_valresultat", "Riksdagsval, valresultat per kommun 1973–2022 (ME0104)", "SCB",
     "https://www.statistikdatabasen.scb.se/", "Slutligt valresultat per kommun och parti."),
    ("val_2026", "Preliminärt valresultat riksdagsvalet 2026", "Valmyndigheten",
     "https://www.val.se/valresultat-och-statistik/statistik-och-data/radata-val-2026",
     "Vallokalernas preliminära rösträkning per kommun. Ersätts av slutligt resultat när det publiceras."),
    ("scb_struktur", "Befolkning, utbildning, inkomst och ekonomisk standard per kommun", "SCB",
     "https://www.statistikdatabasen.scb.se/", "BE0101, UF0506, HE0110 m.fl."),
    ("scb_ulf", "Undersökningarna av levnadsförhållanden (ULF/SILC), otrygghet", "SCB",
     "https://www.scb.se/ulf", "Utsatthet för hot och våld, oro och otrygghet per grupp, 2008–2025 "
     "(tvåårsperioder till 2019). Samma utbildnings-, inkomst- och födelselandsgrupper som PSU."),
    ("bra_ntu", "Nationella trygghetsundersökningen (NTU), tabellsamling 2007–2025", "Brå",
     "https://bra.se/statistik/statistik-fran-enkatundersokningar/nationella-trygghetsundersokningen",
     "Utsatthet för brott, otrygghet, oro och förtroende för rättsväsendet per grupp."),
]


# ---------- PSU ----------

TOTAL_RE = re.compile(r"^\s*(totalt|samtliga|hela väljarkåren|sverige, totalt)", re.I)
PSU_DIM = [
    (r"ålder, 4", "ålder (4 klasser)"), (r"ålder, 7", "ålder (7 klasser)"),
    (r"utbildningsnivå", "utbildning"), (r"inkomstintervall", "inkomst (kvintil)"),
    (r"utrikes/inrikes", "född i Sverige/utrikes"), (r"utländsk/svensk", "bakgrund"),
    (r"fackförbund", "fack (anställda)"), (r"sektor", "sektor (sysselsatta)"),
    (r"sysselsatt", "sysselsättning"), (r"bostadstyp", "boende"),
    (r"civilstånd", "civilstånd"), (r"barn", "barn"),
    (r"SSYK.*väljarkåren", "yrke (SSYK)"), (r"SSYK.*sysselsatta", "yrke (SSYK, sysselsatta)"),
    (r"8 grupper", "region (8)"), (r"10 grupper", "region (10)"),
]


def psu() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    kat = katalog()
    tabeller = kat[kat.rubrik.str.match(r"^Partisympati efter", na=False)]
    stod, vikter, kontroll = [], [], []
    for _, t in tabeller.iterrows():
        df = scb(t["id"])
        if df is None:
            continue
        dim = next((d for m, d in PSU_DIM if re.search(m, t["rubrik"])), None)
        if dim is None:
            varningar.append(f"PSU {t['id']}: okänd dimension '{t['rubrik']}'")
            continue
        pcol = "Partisympati" if "Partisympati" in df else "Parti"
        grundcols = {pcol, "Kon", "ContentsCode", "Tid", "tabell", "varde"}
        gcols = [c for c in df.columns if not c.endswith("_kod") and c not in grundcols]
        if len(gcols) != 1:
            varningar.append(f"PSU {t['id']}: {gcols}")
            continue
        g = gcols[0]
        if "Kon" not in df:
            df["Kon"] = "totalt"
        df["kon"] = np.where(df["Kon"].str.contains("totalt"), "alla", df["Kon"])
        df["mått"] = np.where(df["ContentsCode"].str.contains("Felmarginal"), "fel", "andel")
        w = df.pivot_table(index=["Tid", "kon", g, pcol], columns="mått", values="varde",
                           aggfunc="first").reset_index()
        w["parti"] = w[pcol].map(lambda x: partikod(x) or ("ÖVR" if "övrig" in x.lower() else x))
        w["total"] = w[g].str.match(TOTAL_RE)
        w = w.dropna(subset=["andel"])
        for r in w.itertuples():
            stod.append({"kalla": "scb_psu", "tabell": t["id"], "period": r.Tid,
                         "ar": int(r.Tid[:4]), "ar_dec": _ar_dec(r.Tid), "val": "PSU",
                         "dimension": dim, "grupp": "Samtliga" if r.total else getattr(r, g),
                         "kon": r.kon, "parti": r.parti, "andel": r.andel,
                         "felmarginal": getattr(r, "fel", np.nan)})
        # Gruppstorlek ur felmarginalen: m = z·sqrt(p(1-p)/n) ⇒ n = z²p(1-p)/m²
        w["p"] = w["andel"] / 100
        w["m"] = w["fel"] / 100
        ok = w[(w.p > 0.03) & (w.p < 0.97) & (w.m > 0)].copy()
        ok["n"] = Z ** 2 * ok.p * (1 - ok.p) / ok.m ** 2
        n = ok.groupby(["Tid", "kon", g, "total"]).n.median().reset_index()
        for (tid, kon), d in n.groupby(["Tid", "kon"]):
            grp = d[~d.total]
            if len(grp) < 2:
                continue
            andel = grp.set_index(g).n / grp.n.sum()
            for grupp, a in andel.items():
                vikter.append({"kalla": "scb_psu", "tabell": t["id"], "period": tid,
                               "ar": int(tid[:4]), "ar_dec": _ar_dec(tid), "dimension": dim,
                               "grupp": grupp, "kon": kon, "andel": 100 * a,
                               "metod": "skattad ur felmarginaler"})
            # Kontroll: återskapar vikterna totalen?
            sub = w[(w.Tid == tid) & (w.kon == kon)]
            tot = sub[sub.total].set_index("parti").andel
            grp_p = sub[~sub.total].pivot_table(index=g, columns="parti", values="andel")
            grp_p = grp_p.reindex(andel.index)
            skattad = (grp_p.mul(andel, axis=0)).sum(min_count=1)
            fel = (skattad - tot).reindex([p for p in PARTIER if p in tot]).abs()
            if len(fel.dropna()):
                kontroll.append({"kontroll": "psu_vikter_återskapar_total", "tabell": t["id"],
                                 "dimension": dim, "period": tid, "kon": kon,
                                 "medelfel_procentenheter": float(fel.mean()),
                                 "maxfel_procentenheter": float(fel.max())})
    return pd.DataFrame(stod), pd.DataFrame(vikter), pd.DataFrame(kontroll)


KALIB = {  # PSU-dimension -> (registerdimension, PSU-grupp -> registergrupp)
    "utbildning": ("utbildning (3 nivåer)", lambda g: "eftergymnasial utbildning"
                   if g.startswith("eftergymnasial") else g),
    "född i Sverige/utrikes": ("född i Sverige/utrikes", lambda g: g),
    "ålder (4 klasser)": ("ålder (4 klasser)", lambda g: g),
    "inkomst (kvintil)": ("inkomst (kvintil)", lambda g: g.replace(" %", "")),
}


def kalibrera(vikter: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """Rätta PSU-vikterna för bortfall: faktor = register/PSU per grupp i maj
    2018 och 2022, linjärt interpolerad däremellan och konstant utanför.
    Felmarginalerna bygger på oviktade antal svarande, så utan rättning får
    grupper som svarar oftare (äldre, högutbildade) för stor vikt."""
    if reg.empty:
        return vikter
    ut = vikter.copy()
    for dim, (rdim, karta) in KALIB.items():
        stod = {}
        for ar in (2018, 2022):
            p = ut[(ut.dimension == dim) & (ut.period == f"{ar}M05") & (ut.kon == "alla")]
            r = reg[(reg.dimension == rdim) & (reg.ar == ar)].set_index("grupp").andel
            if p.empty or r.empty:
                break
            psum = p.assign(g=p.grupp.map(karta)).groupby("g").andel.sum()
            stod[ar + 4 / 12] = (r / psum).dropna()
        if len(stod) != 2:
            continue
        (x0, f0), (x1, f1) = sorted(stod.items())
        mask = ut.dimension == dim
        for i in ut.index[mask]:
            g = karta(ut.at[i, "grupp"])
            if g not in f0 or g not in f1:
                continue
            t = min(max((ut.at[i, "ar_dec"] - x0) / (x1 - x0), 0), 1)
            ut.at[i, "andel"] *= f0[g] + t * (f1[g] - f0[g])
        ut.loc[mask, "andel"] = 100 * ut.loc[mask, "andel"] / ut[mask].groupby(
            ["tabell", "period", "kon"]).andel.transform("sum")
        ut.loc[mask, "metod"] = "skattad ur felmarginaler, kalibrerad mot register 2018/2022"
    return ut


def profil_ur_stod(stod: pd.DataFrame, vikter: pd.DataFrame) -> pd.DataFrame:
    """Andel av partiets väljare i grupp g: w_g·p_gp / Σ w·p."""
    s = stod[(stod.grupp != "Samtliga") & (stod.kon == "alla")]
    v = vikter[vikter.kon == "alla"]
    m = s.merge(v[["tabell", "period", "grupp", "andel"]].rename(columns={"andel": "vikt"}),
                on=["tabell", "period", "grupp"])
    m["bidrag"] = m.vikt * m.andel
    m["andel_av_parti"] = 100 * m.bidrag / m.groupby(["tabell", "period", "parti"]).bidrag.transform("sum")
    ut = m[["kalla", "tabell", "period", "ar", "ar_dec", "dimension", "grupp", "parti",
            "andel_av_parti"]].rename(columns={"andel_av_parti": "andel"})
    alla = v.assign(parti="ALLA")[["kalla", "tabell", "period", "ar", "ar_dec", "dimension",
                                   "grupp", "parti", "andel"]]
    ut = pd.concat([ut, alla], ignore_index=True)
    ut["metod"] = "härledd: PSU-stöd × skattad gruppvikt"
    return ut


# ---------- Valu och GU ----------

VALU_ORDNING = ["valu_rd_2026_seminarium", "valu_rd_2014_2022", "valu_rd_2014_2018"]
YRKE = {"Arbetare", "Tjänsteman", "Jordbrukare", "Företagare"}
FACK = {"LO", "TCO", "SACO"}


def valu() -> pd.DataFrame:
    delar = []
    for prio, doc in enumerate(VALU_ORDNING):
        f = KALL_DIR / "txt" / f"{doc}.txt"
        if not f.exists():
            varningar.append(f"Valu {doc} saknas")
            continue
        df, v = tolka.valu(f, doc)
        varningar.extend(v)
        df["prio"] = prio
        delar.append(df)
    if not delar:
        return pd.DataFrame()
    df = pd.concat(delar, ignore_index=True)
    # Samma år/grupp i flera rapporter: nyaste rapporten gäller
    df = df.sort_values("prio").drop_duplicates(["ar", "dimension", "grupp", "parti"])

    def dela(r):
        g = r.grupp
        if r.dimension == "kön/ålder":
            if g in ("Kvinnor", "Män"):
                return "kön"
            return "kön × ålder" if g.startswith(("Kvinnor", "Män")) else "ålder"
        if r.dimension == "yrke/fack":
            return "yrke" if g in YRKE else "fack" if g in FACK else "sysselsättning"
        return r.dimension
    df["dimension"] = df.apply(dela, axis=1)
    df["kalla"] = "svt_valu"
    df["kalla_dokument"] = df.pop("kalla") if "kalla" in df else None
    df = df.rename(columns={"kalla_dokument": "dokument"})
    df["kalla"] = "svt_valu"
    df["period"] = df["ar"].astype(str)
    df["ar_dec"] = df["ar"] + 8 / 12
    df["kon"] = "alla"
    return df.drop(columns=["prio"])


def gu() -> pd.DataFrame:
    f = next((KALL_DIR / "txt").glob("gu_rapporter__2026_7_Partiernas*.txt"), None)
    if f is None:
        varningar.append("GU-rapporten Partiernas väljare saknas")
        return pd.DataFrame()
    df, v = tolka.gu_partiernas_valjare(f, "gu_partiernas_valjare")
    varningar.extend(v)
    df["period"] = df["ar"].astype(str)
    df["ar_dec"] = df["ar"] + 8 / 12
    df["tabell"] = "B.0–B.8"
    df["metod"] = "publicerad sammansättning"
    return df


# ---------- SCB register: valdeltagande och väljarkårens sammansättning ----------

REG_DIM = [(r"år$", "ålder (4 klasser)"), (r"utbildning", "utbildning (3 nivåer)"),
           (r"födda$", "född i Sverige/utrikes"), (r"^\d", "inkomst (kvintil)"),
           (r"förstagångs", "förstagångsväljare")]


def register() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = scb("TAB5107")
    if df is None:
        return pd.DataFrame(), pd.DataFrame()
    df = df[df.Region.isin(["Riket"])]
    df["mått"] = np.where(df.ContentsCode.str.contains("antal"), "rostberattigade", "andel_rostande")
    w = df.pivot_table(index=["Tid", "Kon", "BakgrVar"], columns="mått", values="varde").reset_index()
    w = w[~w.BakgrVar.str.match(r"^samtliga")]
    w["dimension"] = w.BakgrVar.map(lambda b: next((d for m, d in REG_DIM if re.search(m, b)), "övrigt"))
    w["kon"] = np.where(w.Kon == "totalt", "alla", w.Kon)
    w["rostande"] = w.rostberattigade * w.andel_rostande / 100
    w["ar"] = w.Tid.astype(int)
    delt = w.rename(columns={"BakgrVar": "grupp"})[
        ["ar", "kon", "dimension", "grupp", "rostberattigade", "andel_rostande", "rostande"]]
    v = delt[delt.kon == "alla"].copy()
    v["andel"] = 100 * v.rostande / v.groupby(["ar", "dimension"]).rostande.transform("sum")
    v = v.assign(kalla="scb_register_val", tabell="TAB5107", period=v.ar.astype(str),
                 ar_dec=v.ar + 8 / 12, kon="alla", metod="register: röstande")
    return delt, v[["kalla", "tabell", "period", "ar", "ar_dec", "dimension", "grupp", "kon",
                    "andel", "metod"]]


def kontroll_vikter(vikter: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """Jämför PSU-vikter (maj valåret) med registrets röstande."""
    if reg.empty:
        return pd.DataFrame()
    rader = []
    par = {"utbildning": ("utbildning (3 nivåer)", lambda g: "eftergymnasial utbildning"
                          if g.startswith("eftergymnasial") else g),
           "född i Sverige/utrikes": ("född i Sverige/utrikes", lambda g: g),
           "ålder (4 klasser)": ("ålder (4 klasser)", lambda g: g),
           "inkomst (kvintil)": ("inkomst (kvintil)", lambda g: g.replace(" %", "").replace("–", "–"))}
    for psu_dim, (reg_dim, karta) in par.items():
        for ar in (2018, 2022):
            p = vikter[(vikter.dimension == psu_dim) & (vikter.period == f"{ar}M05") & (vikter.kon == "alla")]
            r = reg[(reg.dimension == reg_dim) & (reg.ar == ar)]
            if p.empty or r.empty:
                continue
            p = p.assign(g=p.grupp.map(karta)).groupby("g").andel.sum()
            r = r.set_index("grupp").andel
            for g in r.index:
                if g in p.index:
                    rader.append({"kontroll": "psu_vikt_mot_register", "dimension": psu_dim,
                                  "period": str(ar), "grupp": g, "psu_skattad": float(p[g]),
                                  "register": float(r[g]), "diff": float(p[g] - r[g])})
    return pd.DataFrame(rader)


# ---------- kommuner ----------

def valresultat_kommun() -> pd.DataFrame:
    delar = []
    df = scb("TAB2706")
    if df is not None:
        df["mått"] = np.where(df.ContentsCode.str.startswith("Antal"), "roster", "andel")
        w = df.pivot_table(index=["Region_kod", "Region", "Partimm", "Tid"], columns="mått",
                           values="varde").reset_index()
        w["parti"] = w.Partimm.map(partikod)
        delar.append(pd.DataFrame({
            "ar": w.Tid.astype(int), "kommunkod": w.Region_kod.str.zfill(4), "kommun": w.Region,
            "kategori": w.Partimm, "parti": w.parti, "roster": w.roster, "andel": w.andel,
            "status": "slutligt"}))
    f = next((KALL_DIR / "xlsx").glob("val_radata_2026__*riksdagsval-utan-uppsamlingsdistrikt.xlsx"), None)
    f_slut = next((KALL_DIR / "xlsx").glob("val_radata_2026__slutlig*riksdag*.xlsx"), None)
    if f_slut:
        varningar.append(f"Slutligt 2026-resultat finns ({f_slut.name}) men tolkas ännu inte")
    if f is not None:
        try:
            delar.append(tolka.val2026_kommun(f))
        except Exception as exc:  # noqa: BLE001
            varningar.append(f"val 2026: {exc}")
    ut = pd.concat(delar, ignore_index=True)
    ut = ut[ut.kommunkod.str.fullmatch(r"\d{4}")]
    return ut


def kommunindikatorer() -> pd.DataFrame:
    rader = []

    def lagg(df, ar, kod, namn, varde, tabell, enhet="procent"):
        rader.append(pd.DataFrame({"ar": ar, "kommunkod": kod, "indikator": namn,
                                   "varde": varde, "tabell": tabell, "enhet": enhet}))

    df = scb("TAB6571")        # utländsk bakgrund, 2010–
    if df is not None:
        d = df[df.Kon == "totalt"].pivot_table(index=["Region_kod", "Tid"], columns="UtlBakgrund",
                                                values="varde").reset_index()
        lagg(d, d.Tid.astype(int), d.Region_kod, "utländsk bakgrund",
             100 * d["utländsk bakgrund"] / d["totalt"], "TAB6571")
    for tab in ("TAB3981",):   # utbildning 16–74, 1985– (om hämtad)
        df = scb(tab) if (SCB_DIR / f"{tab}.csv.gz").exists() else None
        if df is not None:
            ucol = next(c for c in df.columns if c.startswith("Utbildn") and not c.endswith("_kod"))
            d = df.groupby(["Region_kod", "Tid", ucol]).varde.sum().unstack()
            hog = [c for c in d.columns if "3 år eller mer" in c or c == "forskarutbildning"]
            d = (100 * d[hog].sum(axis=1) / d.sum(axis=1)).reset_index(name="v")
            lagg(d, d.Tid.astype(int), d.Region_kod, "eftergymnasial ≥3 år (16–74)", d.v, tab)
    for tab in ("TAB5956", "TAB6534"):   # utbildning 25–64/65
        df = scb(tab)
        if df is None:
            continue
        d = df.pivot_table(index=["Region_kod", "Tid"], columns="UtbildningsNiva", values="varde")
        hog = [c for c in d.columns if "3 år eller mer" in c]
        eft = [c for c in d.columns if c.startswith("eftergymnasial")]
        forg = [c for c in d.columns if c.startswith("förgymnasial")]
        s = d.sum(axis=1)
        d = d.reset_index()
        lagg(d, d.Tid.astype(int), d.Region_kod, "eftergymnasial ≥3 år (25–64)",
             100 * d[hog].sum(axis=1) / s.values, tab)
        lagg(d, d.Tid.astype(int), d.Region_kod, "eftergymnasial (25–64)",
             100 * d[eft].sum(axis=1) / s.values, tab)
        lagg(d, d.Tid.astype(int), d.Region_kod, "förgymnasial (25–64)",
             100 * d[forg].sum(axis=1) / s.values, tab)
    df = scb("TAB6685")        # låg/hög ekonomisk standard 2011–
    if df is not None:
        d = df[df.Alder == "totalt ålder"]
        for innehall, namn in (("Låg ekonomisk", "låg ekonomisk standard"),
                               ("Hög ekonomisk", "hög ekonomisk standard")):
            x = d[d.ContentsCode.str.startswith(innehall)]
            lagg(x, x.Tid.astype(int), x.Region_kod, namn, x.varde, "TAB6685")
    df = scb("TAB2707")        # valdeltagande riksdagsval 1973–
    if df is not None:
        x = df[df.ContentsCode.str.contains("riksdagsval")]
        lagg(x, x.Tid.astype(int), x.Region_kod, "valdeltagande riksdagsval", x.varde, "TAB2707")
    if not rader:
        return pd.DataFrame()
    ut = pd.concat(rader, ignore_index=True)
    ut["kommunkod"] = ut.kommunkod.astype(str).str.zfill(4)
    ut = ut[ut.kommunkod.str.fullmatch(r"\d{4}")].dropna(subset=["varde"])
    # Samma indikator/år från två tabeller (5956/6534 överlappar ej, men säkra)
    return ut.drop_duplicates(["ar", "kommunkod", "indikator"], keep="last")


def kommunsamband(val: pd.DataFrame, ind: pd.DataFrame) -> pd.DataFrame:
    rader = []
    valar = sorted(val.ar.unique())
    for indikator, di in ind.groupby("indikator"):
        tillg = sorted(di.ar.unique())
        for y in valar:
            nara = [a for a in tillg if abs(a - y) <= 2]
            if not nara:
                continue
            ia = min(nara, key=lambda a: (abs(a - y), a > y))
            x = di[di.ar == ia].set_index("kommunkod").varde
            for p in PARTIER:
                v = val[(val.ar == y) & (val.parti == p)].set_index("kommunkod").andel
                j = pd.concat([x, v], axis=1, keys=["x", "y"]).dropna()
                if len(j) < 30 or j.y.std() == 0:
                    continue
                r = float(np.corrcoef(j.x, j.y)[0, 1])
                lutning = float(np.polyfit(j.x, j.y, 1)[0])
                rader.append({"valar": int(y), "parti": p, "indikator": indikator,
                              "indikator_ar": int(ia), "r": r, "lutning": lutning,
                              "n_kommuner": len(j)})
    return pd.DataFrame(rader)


# ---------- Brå NTU ----------

def utsatthet() -> pd.DataFrame:
    f = next((KALL_DIR / "xlsx").glob("bra_ntu__Tabellsamling*.xlsx"), None)
    if f is None:
        varningar.append("NTU-tabellsamling saknas")
        return pd.DataFrame()
    df, v = tolka.ntu(f, "bra_ntu")
    varningar.extend(v)
    return df


ULF_DIM = [(r"(?i)utbildning", "utbildning"), (r"kvintil", "inkomst"),
           (r"^(Inrikes|Utrikes) född$", "födelseland"), (r"bakgrund", "bakgrund"),
           (r"^\d.*år$", "ålder"), (r"^SE\d\d", "region"),
           (r"storstad|mindre stad|glesbefolk", "boendeort"),
           (r"^-? ?Arbete|Studier|Arbetslös|Pensionär", "sysselsättning"),
           (r"arbetaryrke|tjänstemannayrke", "klass")]


def ulf() -> pd.DataFrame:
    """SCB:s ULF/SILC: utsatthet för hot och våld m.m. per grupp, 2008–."""
    df = scb("TAB6089")
    if df is None:
        return pd.DataFrame()
    df = df[df.Kon == "kvinnor och män"]
    df["mått"] = df.ContentsCode.map({"Andel personer, procent": "andel",
                                      "Felmarginal för andelen, procent": "felmarginal"})
    w = df.dropna(subset=["mått"]).pivot_table(index=["Indikator", "Redovisningsgrupp", "Tid"],
                                               columns="mått", values="varde").reset_index()
    w["grupp"] = w.Redovisningsgrupp.str.replace(r"^- ", "", regex=True)
    w["dimension"] = w.grupp.map(lambda g: "samtliga" if re.match(r"(?i)^(samtliga|totalt 16\+)", g)
                                 else next((d for m, d in ULF_DIM if re.search(m, g)), "övrigt"))
    return pd.DataFrame({"kalla": "scb_ulf", "tabell": "TAB6089",
                         "indikator": "ULF: " + w.Indikator.str.strip(), "kon": "Samtliga",
                         "dimension": w.dimension, "grupp": w.grupp,
                         "ar": w.Tid.str[-4:].astype(int), "andel": w.andel,
                         "felmarginal": w.felmarginal, "ej_jamforbar_bakat": False})


ULF_KARTA = {
    "utbildning": {"förgymnasial utbildning": "Förgymnasial utbildning",
                   "gymnasial utbildning": "Gymnasial utbildning",
                   "eftergymnasial utbildning mindre än 3 år": "Eftergymnasial utbildning, kortare än 3 år",
                   "eftergymnasial utbildning 3 år eller mer": "Eftergymnasial utbildning, 3 år eller längre"},
    "född i Sverige/utrikes": {"utrikes födda": "Utrikes född", "inrikes födda": "Inrikes född"},
    "inkomst (kvintil)": {"0–20 %": "kvintil 1 (lägsta inkomsterna)", "21–40 %": "kvintil 2 (näst lägsta inkomsterna)",
                          "41–60 %": "kvintil 3 (mellersta inkomsterna)", "61–80 %": "kvintil 4 (näst högsta inkomsterna)",
                          "81–100 %": "kvintil 5 (högsta inkomsterna)"},
}

NTU_KARTA = {
    "utbildning": {"förgymnasial utbildning": "Förgymnasial", "gymnasial utbildning": "Gymnasial",
                   "eftergymnasial utbildning mindre än 3 år": "Eftergymnasial",
                   "eftergymnasial utbildning 3 år eller mer": "Eftergymnasial"},
    "född i Sverige/utrikes": {"utrikes födda": "Utrikesfödda",
                               "inrikes födda": "Svenskfödda med minst en svenskfödd förälder"},
}
EXPONERING = [
    "Självrapporterad utsatthet för något brott mot enskild person",
    "Självrapporterad utsatthet för misshandel", "Självrapporterad utsatthet för hot",
    "Otrygghet vid utevistelse sent på kvällen i det egna bostadsområdet",
    "Oro över brottsligheten i samhället", "Förtroende för rättsväsendet som helhet",
]


def partiexponering(profil: pd.DataFrame, ntu: pd.DataFrame) -> pd.DataFrame:
    ntu_del = ntu[ntu.kalla == "bra_ntu"] if "kalla" in ntu else ntu
    ulf_del = ntu[ntu.kalla == "scb_ulf"] if "kalla" in ntu else ntu.iloc[0:0]
    return pd.concat([_exponering(profil, ntu_del, NTU_KARTA, EXPONERING),
                      _exponering(profil, ulf_del, ULF_KARTA, None)], ignore_index=True)


def _exponering(profil, ntu, kartor, indikatorer) -> pd.DataFrame:
    """Σ_g andel av partiets väljare i g × andel utsatta i g (NTU, samma år).

    Fångar bara den del av skillnaden som följer av partiväljarnas
    sammansättning på en dimension, inte skillnader inom grupperna."""
    if ntu.empty or profil.empty:
        return pd.DataFrame()
    rader = []
    n = ntu[ntu.kon == "Samtliga"]
    if indikatorer:
        n = n[n.indikator.isin(indikatorer)]
    for dim, karta in kartor.items():
        p = profil[(profil.dimension == dim) & profil.period.str.endswith("M05")].copy()
        p["ntu_grupp"] = p.grupp.map(karta)
        p = p.dropna(subset=["ntu_grupp"])
        for (ind, ar), d in n.groupby(["indikator", "ar"]):
            pa = p[p.ar == ar]
            if pa.empty:
                continue
            m = pa.merge(d[["grupp", "andel"]].rename(columns={"grupp": "ntu_grupp", "andel": "utsatt"}),
                         on="ntu_grupp")
            if m.empty:
                continue
            m["bidrag"] = m.andel * m.utsatt
            vikt = m.groupby("parti").andel.sum()
            e = m.groupby("parti").bidrag.sum() / vikt
            for parti, varde in e.items():
                rader.append({"indikator": ind, "ar": int(ar), "dimension": dim,
                              "parti": parti, "forvantad_andel": float(varde),
                              "tackning": float(vikt[parti])})
    return pd.DataFrame(rader)


# ---------- webbunderlag ----------

ORDNING = [r"(?i)^förgymnasial", r"(?i)^gymnasial", r"(?i)^eftergymnasial.*(mindre|kortare) än 3",
           r"(?i)^eftergymnasial.*3 år", r"(?i)^okänd|uppgift saknas|^övriga"]


def _grupp_ordning(grupper: list[str]) -> list[str]:
    """Utbildningsnivåer från låg till hög; övriga grupper i källans ordning."""
    def nyckel(ig):
        i, g = ig
        rang = next((r for r, m in enumerate(ORDNING) if re.search(m, g)), None)
        return (0, rang, i) if rang is not None and rang < 4 else (1 if rang is None else 2, 0, i)
    return [g for _, g in sorted(enumerate(grupper), key=nyckel)]


def _kub(df: pd.DataFrame, tid: str, varde: str = "andel") -> dict:
    """Kompakt form för webben: {dimension: {g: grupper, t: perioder,
    v: {parti: [[värde per grupp] per period]}}}."""
    ut = {}
    for dim, d in df.groupby("dimension", sort=False):
        grupper = _grupp_ordning(list(dict.fromkeys(d.grupp)))
        tider = sorted(d[tid].unique())
        v = {}
        for parti, dp in d.groupby("parti"):
            piv = dp.pivot_table(index=tid, columns="grupp", values=varde, aggfunc="first") \
                .reindex(index=tider, columns=grupper)
            v[parti] = [[None if pd.isna(x) else round(float(x), 1) for x in rad]
                        for rad in piv.values]
        ut[dim] = {"g": grupper, "t": [str(x) for x in tider], "v": v}
    return ut


def webb(tabeller: dict[str, pd.DataFrame]) -> dict:
    prof, stod = tabeller["partiprofil"], tabeller["partistod"]
    vikt = tabeller["gruppvikt"]
    ut = {"skapad": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
          "partier": PARTIER,
          "kallor": tabeller["kalla"].to_dict("records")}
    ut["profil_gu"] = _kub(prof[prof.kalla == "gu_partiernas_valjare"], "ar")
    ut["profil_psu"] = _kub(prof[prof.kalla == "scb_psu"], "period")
    s = stod[(stod.kon == "alla")]
    ut["stod_psu"] = _kub(s[s.kalla == "scb_psu"], "period")
    ut["stod_valu"] = _kub(s[s.kalla == "svt_valu"], "ar")
    ut["psu_metod"] = vikt[vikt.kalla == "scb_psu"].groupby("dimension").metod.first().to_dict()
    ks = tabeller["kommunsamband"]
    if not ks.empty:
        ut["kommunsamband"] = {
            ind: {"t": sorted(int(x) for x in d.valar.unique()),
                  "v": {p: [None if pd.isna(x) else round(float(x), 3) for x in
                            dp.set_index("valar").r.reindex(sorted(d.valar.unique()))]
                        for p, dp in d.groupby("parti")},
                  "indikator_ar": {int(k): int(v) for k, v in
                                   d.groupby("valar").indikator_ar.first().items()}}
            for ind, d in ks.groupby("indikator")}
    pe = tabeller["partiexponering"]
    if not pe.empty:
        ut["exponering"] = {
            f"{ind}|{dim}": {"t": sorted(int(x) for x in d.ar.unique()),
                             "v": {p: [None if pd.isna(x) else round(float(x), 2) for x in
                                       dp.set_index("ar").forvantad_andel.reindex(sorted(d.ar.unique()))]
                                   for p, dp in d.groupby("parti")}}
            for (ind, dim), d in pe.groupby(["indikator", "dimension"])}
    nt = tabeller["utsatthet"]
    if not nt.empty:
        n = nt[(nt.kon == "Samtliga") & (nt.indikator.isin(EXPONERING) | (nt.kalla == "scb_ulf"))]
        ut["ntu"] = {ind: _kub(d.assign(parti="alla"), "ar") for ind, d in n.groupby("indikator")}
    kv = tabeller["kontroll"]
    ut["kontroll"] = kv[kv.kontroll == "psu_vikt_mot_register"].dropna(axis=1, how="all") \
        .round(1).to_dict("records") if not kv.empty else []
    return ut


def main():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    print("PSU")
    stod_psu, vikt_psu, kontroll_psu = psu()
    print(f"  {len(stod_psu)} stödrader, {len(vikt_psu)} vikter")
    print("Register (valdeltagande)")
    reg_delt, vikt_reg = register()
    print("Valu")
    stod_valu = valu()
    print(f"  {len(stod_valu)} rader")
    print("Valforskningsprogrammet")
    prof_gu = gu()
    print(f"  {len(prof_gu)} rader")
    print("Valresultat och kommunindikatorer")
    val = valresultat_kommun()
    ind = kommunindikatorer()
    samband = kommunsamband(val, ind) if not ind.empty else pd.DataFrame()
    print("NTU")
    ntu = pd.concat([utsatthet(), ulf()], ignore_index=True)

    vikt_psu = kalibrera(vikt_psu, vikt_reg)
    partistod = pd.concat([stod_psu, stod_valu], ignore_index=True)
    gruppvikt = pd.concat([vikt_psu, vikt_reg], ignore_index=True)
    profil = pd.concat([profil_ur_stod(stod_psu, vikt_psu), prof_gu], ignore_index=True)
    kontroll = pd.concat([kontroll_psu, kontroll_vikter(vikt_psu, vikt_reg)], ignore_index=True)
    tabeller = {
        "kalla": pd.DataFrame(KALLOR, columns=["kalla", "namn", "utgivare", "url", "beskrivning"]),
        "partistod": partistod, "gruppvikt": gruppvikt, "partiprofil": profil,
        "valresultat_kommun": val, "kommunindikator": ind, "kommunsamband": samband,
        "utsatthet": ntu, "partiexponering": partiexponering(profil[profil.kalla == "scb_psu"], ntu),
        "valdeltagande_grupp": reg_delt, "kontroll": kontroll,
        "varningar": pd.DataFrame({"varning": varningar}),
    }
    if DB.exists():
        DB.unlink()
    with sqlite3.connect(DB) as con:
        for namn, df in tabeller.items():
            df.to_sql(namn, con, index=False)
            df.to_csv(CSV_DIR / f"{namn}.csv", index=False)
            print(f"  {namn}: {len(df)} rader")
    (DATA_DIR / "webb.json").write_text(
        json.dumps(webb(tabeller), ensure_ascii=False, separators=(",", ":"), default=float),
        encoding="utf-8")
    print(f"{len(varningar)} varningar")


if __name__ == "__main__":
    main()
