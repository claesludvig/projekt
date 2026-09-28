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
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import region as reg
import valdistrikt as vdm
import fragor
import metod
import kontroller
import lagesbild
import media
from licenser import LICENSER, STATUS_TEXT
import norden as nordm
from omraden import OMRADEN
import riksdag
import valkrets
import verklighet
from verklighet_katalog import FRAGOR, mal
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
    ("val_distrikt_2026", "Valdistrikt 2026: gränser och preliminära röster", "Valmyndigheten",
     "https://www.val.se/valresultat-och-statistik/statistik-och-data/radata-val-2026",
     "Valdistriktens geografi (per län, SWEREF 99 TM) och preliminär rösträkning per distrikt."),
    ("scb_deso", "Statistik per DeSO 2025 och DeSO-gränser", "SCB",
     "https://www.scb.se/vara-tjanster/oppna-data/oppna-geodata/oppna-geodata-for-deso---demografiska-statistikomraden/",
     "Befolkning efter bakgrund, födelseregion, ålder, utbildning, ekonomisk standard, upplåtelseform och sysselsättning i ca 6 000 områden."),
    ("polisen", "Skjutningar och sprängningar per polisregion och månad", "Polismyndigheten",
     "https://polisen.se/om-polisen/polisens-arbete/sprangningar-och-skjutningar/",
     "Bekräftade skjutningar (med avlidna och skadade) sedan 2017 och sprängningar (detonationer, försök, förberedelser) sedan 2018."),
    ("som", "Svenska trender 1986–2025: viktigaste samhällsproblem", "SOM-institutet, Göteborgs universitet",
     "https://www.gu.se/som-institutet", "Öppen fråga om vilka frågor eller samhällsproblem som är viktigast i Sverige, högst tre svar, 1987–2025."),
    ("scb_kpi", "Konsumentprisindex efter produktgrupp", "SCB", "https://www.scb.se/pr0101",
     "Månadsindex 1980–2025 för el, drivmedel, livsmedel m.fl."),
    ("kolada", "Kolada: nyckeltal för kommuner och regioner", "RKA (Rådet för främjande av kommunala analyser)",
     "https://www.kolada.se/", "Väntetider i vården, skolresultat, äldreomsorg, anmälda brott, arbetslöshet, ekonomiskt bistånd, skattesatser, utsläpp, bostadsbyggande m.m. per kommun och region."),
    ("riksbanken", "Styrräntan", "Sveriges riksbank", "https://www.riksbank.se/", "Styrräntan (SWEA-API), månadsmedel."),
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


def register_region() -> pd.DataFrame:
    """Röstande per grupp i varje län och kommun (TAB5107), kön totalt."""
    df = scb("TAB5107")
    if df is None:
        return pd.DataFrame()
    df = df[df.Kon == "totalt"]
    df["mått"] = np.where(df.ContentsCode.str.contains("antal"), "rostberattigade", "andel_rostande")
    w = df.pivot_table(index=["Region_kod", "Region", "Tid", "BakgrVar"], columns="mått",
                       values="varde").reset_index()
    w = w[~w.BakgrVar.str.match(r"^samtliga")]
    w["dimension"] = w.BakgrVar.map(lambda b: next((d for m, d in REG_DIM if re.search(m, b)), "övrigt"))
    w["rostande"] = w.rostberattigade * w.andel_rostande / 100
    return pd.DataFrame({"region_kod": w.Region_kod, "region": w.Region, "ar": w.Tid.astype(int),
                         "dimension": w.dimension, "grupp": w.BakgrVar,
                         "rostberattigade": w.rostberattigade, "andel_rostande": w.andel_rostande,
                         "rostande": w.rostande})


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
    ut["kommunkod"] = ut.kommunkod.astype(str)
    ut.loc[ut.kommunkod.str.len() == 3, "kommunkod"] = ut.kommunkod.str.zfill(4)
    ut = ut[ut.kommunkod.str.fullmatch(r"\d{2}|\d{4}")].dropna(subset=["varde"])
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
    return metod.med_ki(pd.DataFrame(rader), "r", "n_kommuner")


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
    ut.update(webb_region(tabeller))
    ut.update(webb_valkrets(tabeller))
    ut.update(webb_lage(tabeller))
    ut.update(webb_riksdag(tabeller))
    ut.update(webb_omraden(tabeller))
    ut.update(webb_media(tabeller))
    kv = tabeller.get("kvalitet", pd.DataFrame())
    if len(kv):
        ut["kvalitet"] = {"status": max(kv.status, key=kontroller.ORDNING.get),
                          "antal": kv.status.value_counts().to_dict(),
                          "rader": kv[kv.status != "ok"].replace({np.nan: None}).to_dict("records")}
    from riksdag_katalog import KLASSNING
    ut["klassning"] = KLASSNING
    ut["licenser"] = [{"kalla": a, "utgivare": b, "status": c, "status_text": STATUS_TEXT[c], "villkor": d, "url": e}
                      for a, b, c, d, e in LICENSER]
    ut["evidens"] = {e[0]: {"avsnitt": e[1], "niva": e[2], "niva_text": metod.NIVAER[e[2]],
                            "sager": e[3], "sager_inte": e[4]} for e in metod.EVIDENS}
    kv = tabeller["kontroll"]
    ut["kontroll"] = kv[kv.kontroll == "psu_vikt_mot_register"].dropna(axis=1, how="all") \
        .round(1).to_dict("records") if not kv.empty else []
    return ut


def _r(x, d=1):
    return None if x is None or pd.isna(x) else round(float(x), d)


def webb_region(t: dict[str, pd.DataFrame]) -> dict:
    ut = {}
    vl = t["valresultat_lan"]
    if not vl.empty:
        lan = vl[["lan", "lansnamn"]].drop_duplicates().sort_values("lan")
        ut["lan"] = dict(zip(lan.lan, lan.lansnamn))
        ar = sorted(vl.ar.unique())
        ut["lan_val"] = {"t": [int(a) for a in ar], "v": {
            k: {p: [_r(x) for x in d[d.parti == p].set_index("ar").andel.reindex(ar)]
                for p in PARTIER + ["ÖVR"]}
            for k, d in vl.groupby("lan")}}
    pr = t["partiprofil_region"]
    if not pr.empty:
        prl = pr[pr.niva.isin(["län", "riket"])]
        ut["lan_profil"] = {}
        for (ar, dim), d in prl.groupby(["ar", "dimension"]):
            grupper = _grupp_ordning(list(dict.fromkeys(d.grupp)))
            reg = sorted(d.region_kod.unique())
            piv = d.pivot_table(index=["region_kod", "grupp"], columns="parti", values="andel_av_parti")
            alla = d[d.parti == "S"].set_index(["region_kod", "grupp"]).gruppandel
            ut["lan_profil"][f"{ar}|{dim}"] = {
                "g": grupper, "r": reg,
                "v": {p: [[_r(piv[p].get((r, g))) for g in grupper] for r in reg] for p in piv.columns},
                "alla": [[_r(alla.get((r, g))) for g in grupper] for r in reg],
                "metod": d.metod.iloc[0]}
    dk = t["dekomposition"]
    if not dk.empty:
        def paket(d, index):
            per = sorted({(int(a), int(b)) for a, b in zip(d.fran, d.till)})
            nycklar = sorted(d[index].unique())
            ut2 = {"per": [f"{a}–{b}" for a, b in per], "k": nycklar, "v": {}}
            for p, dp in d.groupby("parti"):
                ix = dp.set_index([index, "fran"])
                ut2["v"][p] = {m: [[_r(ix[m].get((k, a)), 2) for a, _ in per] for k in nycklar]
                               for m in ("forandring", "sammansattning", "beteende")}
            return ut2
        ut["dekomp_riket"] = paket(dk[(dk.kalla == "psu") & dk.dimension.isin(
            ["ålder (4 klasser)", "utbildning", "född i Sverige/utrikes", "inkomst (kvintil)",
             "bakgrund", "boende", "sysselsättning", "civilstånd"])], "dimension")
        ut["dekomp_register"] = {
            niva: paket(dk[(dk.kalla == "register_ipf") & (dk.niva == niva)].assign(
                nyckel=lambda x: x.region_kod + "|" + x.dimension), "nyckel")
            for niva in ("riket", "län")}
        ut["dekomp_utb_lan"] = paket(dk[(dk.kalla == "befolkning") & (dk.niva == "län")], "region_kod")
    nl = t["utsatthet_lan"]
    if not nl.empty:
        n = nl[nl.grupp.astype(str).str.startswith("Samtliga")]
        ut["ntu_lan"] = {}
        for ind, d in n.groupby("indikator"):
            ar = sorted(d.ar.unique())
            ut["ntu_lan"][ind] = {"t": [int(a) for a in ar], "v": {
                l: [_r(x) for x in dl.set_index("ar").andel.reindex(ar)] for l, dl in d.groupby("lansnamn")}}
    # --- sakfrågor och verklighet
    pol = t.get("polisen_manad", pd.DataFrame())
    if not pol.empty:
        tot = pol[pol.polisregion == "Totalt"]
        ut["polisen_ar"] = {f"{typ}|{m}": {int(a): int(v) for a, v in d.groupby("ar").antal.sum().items()}
                            for (typ, m), d in tot.groupby(["typ", "matt"])}
        ut["polisen_manader"] = {f"{typ}|{m}": {int(a): int(d[d.ar == a].manad.nunique()) for a in d.ar.unique()}
                                 for (typ, m), d in tot.groupby(["typ", "matt"])}
    kpi = t.get("kpi_manad", pd.DataFrame())
    if not kpi.empty:
        k = kpi[kpi.ar >= 2010]
        ut["kpi"] = {s: {"t": [f"{a}-{m:02d}" for a, m in zip(d.ar, d.manad)],
                         "v": [_r(x) for x in d.forandring_12m], "grupp": d.produktgrupp.iloc[0]}
                     for s, d in k.groupby("serie")}
    fb = t.get("fraga_betydelse", pd.DataFrame())
    if not fb.empty:
        ar = sorted(fb.ar.unique())
        ut["fraga_betydelse"] = {"t": [int(a) for a in ar], "v": {
            f: [_r(x) for x in d.set_index("ar").andel.reindex(ar)] for f, d in fb.groupby("fraga")}}
    fr = t.get("fraga_rang_parti", pd.DataFrame())
    if not fr.empty:
        ut["fraga_rang"] = {int(y): {f: {p: int(x) for p, x in zip(d.parti, d.rang)}
                                     for f, d in dy.groupby("fraga")} for y, dy in fr.groupby("valar")}
    bp = t.get("bast_politik", pd.DataFrame())
    if not bp.empty:
        ut["bast_politik"] = {int(y): {o: {p: _r(x) for p, x in zip(d.parti, d.andel)}
                                       for o, d in dy.groupby("omrade")} for y, dy in bp.groupby("ar")}
    sp = t.get("som_samhallsproblem", pd.DataFrame())
    if not sp.empty:
        ar = sorted(sp.ar.unique())
        ut["som"] = {"t": [int(a) for a in ar], "v": {
            o: [_r(x) for x in d.set_index("ar").andel.reindex(ar)] for o, d in sp.groupby("omrade")}}
    vk = t.get("verklighet", pd.DataFrame())
    if not vk.empty:
        r = vk[(vk.niva == "riket") & (vk.ar_dec >= 2006)]
        ut["fragor_katalog"] = [{"id": a, "valu": b, "som": c} for a, b, c in FRAGOR]
        ut["verk"] = {}
        for (fr, ind), d in r.groupby(["fraga", "indikator"]):
            d = d.sort_values("ar_dec")
            ut["verk"].setdefault(fr, {})[ind] = {
                "t": [round(float(x), 3) for x in d.ar_dec], "v": [_r(x, 2) for x in d.varde],
                "p": list(d.period.astype(str)), "kalla": d.kalla.iloc[0],
                "mal": {k: v for k, v in mal(ind).items() if v is not None}}
    vf = t.get("verklighet_forandring", pd.DataFrame())
    if not vf.empty:
        ut["verk_forandring"] = vf.round(2).replace({np.nan: None}).to_dict("records")
    vkk = t.get("verklighet_kommun", pd.DataFrame())
    if not vkk.empty:
        ut["verk_kommun"] = vkk.round(3).to_dict("records")
    tb = t.get("test_bilar", pd.DataFrame())
    if not tb.empty:
        ut["test_bilar"] = tb.round(3).to_dict("records")
    ts = t.get("test_skjutningar", pd.DataFrame())
    if not ts.empty:
        ut["test_skjutningar"] = ts.round(3).to_dict("records")
    vt = t.get("valdistrikt_tiondel", pd.DataFrame())
    if not vt.empty:
        dist = t["valdistrikt_2026"]
        ok = dist[(dist.giltiga >= 100) & (dist.tackning_yta >= 0.9)]
        ut["distrikt"] = {"n": int(len(ok)), "tackning": float(len(ok) / max(len(dist), 1)), "dec": {
            ind: {"dec": [_r(x, 2) for x in d[d.parti == "S"].sort_values("tiondel").indikator_medel],
                  "v": {p: [_r(x) for x in dp.sort_values("tiondel").andel] for p, dp in d.groupby("parti")}}
            for ind, d in vt.groupby("indikator")}}
    li = t["lansindikator"]
    if not li.empty:
        ut["lan_ind"] = {}
        for ind, d in li.groupby("indikator"):
            ar = sorted(d.ar.unique())
            ut["lan_ind"][ind] = {"t": [int(a) for a in ar], "v": {
                l: [_r(x) for x in dl.set_index("ar").varde.reindex(ar)] for l, dl in d.groupby("lan")}}
    return ut


def webb_valkrets(t: dict[str, pd.DataFrame]) -> dict:
    vk = t.get("valkrets", pd.DataFrame())
    if vk.empty:
        return {}
    res, ind = t["valresultat_valkrets"], t["valkrets_indikator"]
    ut = {"lista": [{"kod": r.valkrets_kod, "namn": r.valkrets, "lan": r.lan, "kommuner": r.kommuner,
                     "rostb": int(r.rostberattigade_2026) if pd.notna(r.rostberattigade_2026) else None,
                     "m22": None if pd.isna(r.mandat_2022) else int(r.mandat_2022),
                     "m26": None if pd.isna(r.mandat_2026) else int(r.mandat_2026)} for r in vk.itertuples()]}
    ar = sorted(res.ar.unique())
    ut["t"] = [int(a) for a in ar]
    ut["val"] = {k: {p: [_r(x) for x in d[d.parti == p].set_index("ar").andel.reindex(ar)]
                     for p in PARTIER + ["ÖVR", "valdeltagande"]} for k, d in res.groupby("valkrets_kod")}
    # Riket: röster summerade över valkretsarna; valdeltagandet viktat med röstberättigade 2026
    rp = res[res.parti.isin(PARTIER + ["ÖVR"])].groupby(["ar", "parti"]).roster.sum()
    rp = (100 * rp / rp.groupby(level=0).transform("sum")).unstack()
    vd = res[res.parti == "valdeltagande"].assign(w=lambda x: x.valkrets_kod.map(
        dict(zip(vk.valkrets_kod, vk.rostberattigade_2026))))
    vd = vd.dropna(subset=["andel", "w"]).groupby("ar").apply(
        lambda x: np.average(x.andel, weights=x.w), include_groups=False)
    ut["val"]["00"] = {**{p: [_r(x) for x in rp[p].reindex(ar)] if p in rp else [None] * len(ar)
                          for p in PARTIER + ["ÖVR"]},
                       "valdeltagande": [_r(x) for x in vd.reindex(ar)]}
    m = res[res.mandat.notna()]
    ut["mandat"] = {k: {p: [None if pd.isna(x) else int(x) for x in d[d.parti == p].set_index("ar").mandat.reindex([2022, 2026])]
                        for p in PARTIER + ["ÖVR"]} for k, d in m.groupby("valkrets_kod")}
    ut["ind"] = {}
    i = ind[ind.ar >= 2010]
    for (fr, namn), d in i.groupby(["fraga", "indikator"]):
        ar = sorted(d.ar.unique())
        m_ = {k: v for k, v in mal(namn).items() if v is not None}
        ut["ind"][namn] = {"fraga": fr, "kallniva": d.kallniva.iloc[0], "kalla": d.kalla.iloc[0], "mal": m_,
                           "t": [int(a) for a in ar],
                           "riket": [_r(x, 2) for x in d.groupby("ar").riket.first().reindex(ar)],
                           "v": {k: [_r(x, 2) for x in dk.set_index("ar").varde.reindex(ar)]
                                 for k, dk in d.groupby("valkrets_kod")},
                           "rang": {k: [None if pd.isna(x) else int(x) for x in dk.set_index("ar").rang.reindex(ar)]
                                    for k, dk in d.groupby("valkrets_kod")},
                           "antal": [int(x) for x in d.groupby("ar").antal.first().reindex(ar).fillna(0)]}
    return {"valkrets": ut}


def webb_riksdag(t: dict[str, pd.DataFrame]) -> dict:
    ut = {}
    op = t.get("opinion", pd.DataFrame())
    ft = riksdag.fortroende(op)
    if len(ft):
        ut["fortroende"] = {s: {int(a): _r(x) for a, x in zip(d.ar, d.andel)} for s, d in ft.groupby("serie")}
    of, ob = t.get("opinion_forslag", pd.DataFrame()), t.get("opinion_beslut", pd.DataFrame())
    if len(of):
        lista = []
        for oid, d in of.groupby("id", sort=False):
            b = ob[ob.id == oid].sort_values("datum", ascending=False) if len(ob) else pd.DataFrame()
            lista.append({"id": oid, "forslag": d.forslag.iloc[0], "fraga": d.fraga.iloc[0],
                          "v": {int(a): _r(x) for a, x in zip(d.ar, d.andel)},
                          "n": int(len(b)),
                          "beslut": [{"titel": r.titel, "datum": r.datum, "url": r.url, "bet": r.betankande,
                                      "ja": None if pd.isna(getattr(r, "ja", np.nan)) else int(r.ja),
                                      "nej": None if pd.isna(getattr(r, "nej", np.nan)) else int(r.nej),
                                      "utfall": getattr(r, "utfall", None) if isinstance(getattr(r, "utfall", None), str) else None,
                                      "pos": {p: getattr(r, f"p_{p}", None) for p in PARTIER
                                              if isinstance(getattr(r, f"p_{p}", None), str)}}
                                     for r in b.head(8).itertuples()]})
        ut["opinion"] = lista
    ak = t.get("riksdag_aktivitet", pd.DataFrame())
    if len(ak):
        rm = sorted(ak.rm.unique())
        ut["rd_aktivitet"] = {"rm": rm, "v": {f: [int(x) for x in d.set_index("rm").get("propositioner", pd.Series(dtype=float)).reindex(rm).fillna(0)]
                                               for f, d in ak.groupby("fraga")}}
    ss = t.get("riksdag_samstammighet", pd.DataFrame())
    if len(ss):
        ut["rd_samst"] = {per: {"n": int(d.n.max()), "m": [[_r(d[(d.parti_a == a) & (d.parti_b == b)].andel_lika.mean())
                                                           for b in PARTIER] for a in PARTIER]}
                          for per, d in ss.groupby("period")}
    pf = t.get("riksdag_parti_fraga", pd.DataFrame())
    if len(pf):
        ut["rd_parti_fraga"] = {per: {f: {r.parti: _r(r.andel_vinnande) for r in dd.itertuples()}
                                      for f, dd in d.groupby("fraga")} for per, d in pf.groupby("period")}
    dok = t.get("riksdag_dokument", pd.DataFrame())
    if len(dok):
        pr = dok[dok.doktyp == "prop"].assign(fraga=lambda x: x.fragor.fillna("").str.split(",")).explode("fraga")
        pr = pr[pr.fraga != ""].sort_values("datum", ascending=False)
        ut["rd_prop"] = {f: [{"titel": r.titel, "datum": r.datum, "url": r.url, "rm": r.rm, "bet": r.beteckning}
                             for r in d.head(15).itertuples()] for f, d in pr.groupby("fraga")}
    led = t.get("riksdag_ledamot", pd.DataFrame())
    if len(led) and "valkrets" in led:
        per_rm = led.groupby("rm").voteringar.max()
        rm = max((r for r, n in per_rm.items() if n >= 50), default=None)
        if rm:
            l = led[(led.rm == rm) & led.parti.isin(PARTIER)].sort_values(["valkrets", "parti", "namn"])
            ut["rd_ledamot"] = {"rm": rm, "v": {k: [{"namn": r.namn, "parti": r.parti, "narvaro": _r(r.narvaro),
                                                     "n": int(r.voteringar)} for r in d.itertuples()]
                                                for k, d in l.groupby("valkrets")}}
    return ut


def webb_media(t: dict[str, pd.DataFrame]) -> dict:
    ut = {}
    nu = t.get("media_foljare_nu", pd.DataFrame())
    fl = t.get("media_foljare", pd.DataFrame())
    if len(nu):
        ut["foljare"] = {"nu": [{"parti": r.parti, "roll": r.roll, "namn": r.namn, "plattform": r.plattform,
                                 "datum": str(r.datum)[:10], "foljare": int(r.foljare), "kalla": r.kalla,
                                 "konto": str(r.konto), "verifierad": None if pd.isna(getattr(r, "verifierad", None))
                                 else bool(r.verifierad)} for r in nu.itertuples()],
                         "ej_matbara": ["Instagram", "Threads"],
                         "serie": {f"{p}|{roll}|{pl}": {"d": [str(x)[:10] for x in d.datum], "v": [int(x) for x in d.foljare]}
                                   for (p, roll, pl), d in fl.groupby(["parti", "roll", "plattform"]) if len(d) > 1}}
    om = t.get("media_omnamnanden", pd.DataFrame())
    if len(om):
        tot = om.groupby(["vecka", "parti"]).artiklar.sum().unstack().fillna(0)
        andel = 100 * tot.div(tot.sum(axis=1).replace(0, np.nan), axis=0)
        per_flode = om.groupby(["flode", "parti"]).artiklar.sum().unstack().fillna(0)
        ut["omnamnanden"] = {"veckor": list(tot.index), "antal": {p: [int(x) for x in tot.get(p, pd.Series(0, index=tot.index))] for p in PARTIER},
                             "andel": {p: [_r(x) for x in andel.get(p, pd.Series(np.nan, index=andel.index))] for p in PARTIER},
                             "flode": {f: {p: int(r.get(p, 0)) for p in PARTIER} for f, r in per_flode.iterrows()},
                             "artiklar": int(om.drop_duplicates(["vecka", "flode"]).totalt.sum())}
    gn = t.get("media_google_nyheter", pd.DataFrame())
    if len(gn):
        sista = sorted(gn.dag.unique())[-30:]
        g = gn[gn.dag.isin(sista)].groupby("parti").artiklar.sum()
        ut["google_nyheter"] = {"fran": sista[0], "till": sista[-1], "v": {p: int(g.get(p, 0)) for p in PARTIER}}
    ta = t.get("media_talartid", pd.DataFrame())
    if len(ta):
        rm = sorted(ta.rm.unique())
        kol = [c for c in ("anforanden", "ord", "repliker", "andel_av_orden", "andel_av_ledamoterna", "ord_per_ledamot") if c in ta]
        ut["talartid"] = {"rm": rm, "v": {p: {c: [_r(x) for x in d.set_index("rm")[c].reindex(rm)] for c in kol}
                                          for p, d in ta.groupby("parti")}}
    an = t.get("media_annonser", pd.DataFrame())
    if len(an):
        ar = sorted(an.ar.unique())
        ut["annonser"] = {"ar": [int(a) for a in ar], "valuta": an.valuta.iloc[0],
                          "v": {p: [_r(x, 0) for x in d.set_index("ar").utgift.reindex(ar)] for p, d in an.groupby("parti")}}
    from media_katalog import FORSKNING, MEDIEBAROMETERN, POLITIKNYHETER_ALDER
    ut["mediebarometern"] = MEDIEBAROMETERN
    ut["politiknyheter_alder"] = POLITIKNYHETER_ALDER
    ut["forskning_media"] = FORSKNING
    sf = t.get("som_fortroende", pd.DataFrame())
    if len(sf):
        m = sf[sf.institution.isin(["radio och tv", "dagspressen"])]
        ar = sorted(m.ar.unique())
        ut["medieforttroende"] = {"ar": [int(a) for a in ar], "v": {
            i: {g: [None if pd.isna(x) else int(x) for x in d.set_index("ar").andel.reindex(ar)] for g, d in di.groupby("grupp")}
            for i, di in m.groupby("institution")},
            "fa": {i: {g: [int(a) for a in d[d.fa_svar].ar] for g, d in di.groupby("grupp")} for i, di in m.groupby("institution")}}
    wp = t.get("media_wikipedia", pd.DataFrame())
    if len(wp):
        man = sorted(wp.manad.unique())
        ut["wikipedia"] = {"manader": man, "namn": {f"{p}|{r}": d.namn.iloc[-1] for (p, r), d in wp.groupby(["parti", "roll"])},
                           "v": {f"{p}|{r}": [None if pd.isna(x) else int(x) for x in d.set_index("manad").visningar.reindex(man)]
                                 for (p, r), d in wp.groupby(["parti", "roll"])}}
    gd = t.get("media_gdelt", pd.DataFrame())
    if len(gd):
        man = sorted(gd.manad.unique())
        ut["gdelt"] = {"manader": man, **{k: {p: [_r(x) for x in d.set_index("manad")[k].reindex(man)] for p, d in gd.groupby("parti")}
                                          for k in ("andel", "ton")},
                       "artiklar": {p: [None if pd.isna(x) else int(x) for x in d.set_index("manad").artiklar.reindex(man)]
                                    for p, d in gd.groupby("parti")}}
    sf = t.get("media_sakfragor", pd.DataFrame())
    if len(sf):
        from verklighet_katalog import FRAGOR
        namn = {f: n for f, n, _ in FRAGOR}
        fr = [f for f in namn if f in set(sf.fraga)] + sorted(set(sf.fraga) - set(namn))
        ut["sakfragor"] = {"fragor": fr, "namn": {f: namn.get(f, f) for f in fr}, "fran": sf.fran.iloc[0], "till": sf.till.iloc[0],
                           "n": {p: int(d.partiets_artiklar.iloc[0]) for p, d in sf.groupby("parti")},
                           "v": {p: {r.fraga: _r(r.andel) for r in d.itertuples()} for p, d in sf.groupby("parti")}}
    ak = t.get("media_rd_aktivitet", pd.DataFrame())
    if len(ak):
        rm = sorted(ak.rm.unique())
        kol = [c for c in ("mot", "ip", "fr", "ledamoter", "per_ledamot") if c in ak]
        ut["rd_partiaktivitet"] = {"rm": rm, "v": {p: {c: [_r(x) for x in d.set_index("rm")[c].reindex(rm)] for c in kol}
                                              for p, d in ak.groupby("parti")}}
    return ut


def webb_omraden(t: dict[str, pd.DataFrame]) -> dict:
    n = t.get("norden", pd.DataFrame())
    vk = t.get("verklighet", pd.DataFrame())
    lb = t.get("lagesbild", pd.DataFrame())
    finns_verk = set(vk.indikator.unique()) if len(vk) else set()
    finns_lage = set(lb.id) if len(lb) else set()
    finns_nord = set(n.id.unique()) if len(n) else set()
    ut = {"omraden": [{**{k: o[k] for k in ("id", "namn", "fragor", "intro", "myndigheter", "luckor")},
                       "sverige": [x for x in o["sverige"] if x in finns_verk],
                       "saknas": [x for x in o["sverige"] if x not in finns_verk],
                       "lage": [x for x in o["lage"] if x in finns_lage],
                       "norden": [x for x in o["norden"] if x in finns_nord]} for o in OMRADEN]}
    if len(n):
        ut["norden"] = {}
        for sid, d in n[n.ar_dec >= 2005].groupby("id"):
            t_ = sorted(d.ar_dec.unique())
            per = d.drop_duplicates("ar_dec").set_index("ar_dec").period
            ut["norden"][sid] = {"namn": d.namn.iloc[0], "enhet": d.enhet.iloc[0], "t": [round(float(x), 3) for x in t_],
                                 "p": [per[x] for x in t_],
                                 "v": {g: [_r(x, 3) for x in dg.set_index("ar_dec").varde.reindex(t_)]
                                       for g, dg in d.groupby("geo")}}
    return ut


def webb_lage(t: dict[str, pd.DataFrame]) -> dict:
    lb = t.get("lagesbild", pd.DataFrame())
    if lb.empty:
        return {}
    ser = t["lagesbild_serie"]
    ser = ser[ser.period.str[:4].astype(int) >= date.today().year - 8]
    return {"lage": {"rader": lb.round(3).replace({np.nan: None}).to_dict("records"),
                     "serier": {k: {"p": list(d.period), "v": [_r(x, 2) for x in d.varde]}
                                for k, d in ser.groupby("id")}}}


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
    ind_alla = kommunindikatorer()
    ind = ind_alla[ind_alla.kommunkod.str.len() == 4]
    ind_lan = ind_alla[ind_alla.kommunkod.str.len() == 2].rename(columns={"kommunkod": "lan"})
    samband = kommunsamband(val, ind) if not ind.empty else pd.DataFrame()
    print("Län")
    namn = reg.lansnamn(scb)
    val_lan = reg.valresultat_lan(val, namn)
    ind_lan["lansnamn"] = ind_lan.lan.map(namn)
    ntu_lan = reg.ntu_lan(next((KALL_DIR / "xlsx").glob("bra_ntu__Resultat_f*l*n_NTU*.xlsx"), None))
    print("NTU")
    ntu = pd.concat([utsatthet(), ulf()], ignore_index=True)

    vikt_psu = kalibrera(vikt_psu, vikt_reg)
    print("Skattade profiler per region (IPF)")
    rr = register_region()
    namn_alla = {**dict(zip(rr.region_kod, rr.region)), **namn}
    profil_region = reg.raka(stod_psu, vikt_psu, rr, val, namn_alla)
    print(f"  {len(profil_region)} rader")
    print("Valdistrikt 2026")
    dist, dist_tio, dist_samb = vdm.distrikt(
        DATA_DIR / "geo" / "valdistrikt_deso.csv", SCB_DIR,
        next((KALL_DIR / "xlsx").glob("val_radata_2026__*rostfil*distrikt*.xlsx"), None))
    print(f"  {len(dist)} distrikt, {len(dist_tio)} tiondelsrader")
    print("Sakfrågor och verklighet")
    pol = fragor.polisen_manad(KALL_DIR)
    kpi = fragor.kpi_manad(scb)
    f_bet, f_rang, f_bast = fragor.valu_fragor(KALL_DIR)
    som_p = fragor.som(KALL_DIR)
    t_bil = fragor.test_bilar(scb, val)
    t_skj = fragor.test_skjutningar(pol, val, scb)
    print(f"  polisen {len(pol)}, kpi {len(kpi)}, valu-frågor {len(f_bet)}/{len(f_rang)}/{len(f_bast)}, "
          f"som {len(som_p)}, test bilar {len(t_bil)}, test skjutningar {len(t_skj)}")
    print("Verklighetsindikatorer")
    nord = nordm.bygg(DATA_DIR)
    print(f"  Norden (Eurostat): {len(nord)} rader, {nord.id.nunique() if len(nord) else 0} serier")
    verk, verk_f, verk_k = verklighet.bygg(scb, katalog(), DATA_DIR, f_bet, som_p, val, varningar, pol, kpi,
                                           nordm.till_verklighet(nord))
    print(f"  {len(verk)} rader, {verk.indikator.nunique() if len(verk) else 0} indikatorer")
    verk_ind = verk[["fraga", "indikator", "kalla"]].drop_duplicates("indikator").reset_index(drop=True)
    verk_ind.insert(0, "indikator_id", range(len(verk_ind)))
    k_ = verk[verk.niva == "kommun"]
    verk_kv = pd.DataFrame({"indikator_id": k_.indikator.map(dict(zip(verk_ind.indikator, verk_ind.indikator_id))),
                            "kommunkod": k_.region_kod, "ar": np.floor(k_.ar_dec).astype(int), "varde": k_.varde})
    print("Valkretsar")
    vk = valkrets.bygg(next((KALL_DIR / "xlsx").glob("val_radata_2026__preliminar-riksdagsval-utan*.xlsx"), None),
                       val, verk, ind, ntu_lan, namn, pol, scb, dist)
    print("  " + ", ".join(f"{k} {len(v)}" for k, v in vk.items()))
    print("Lägesbild")
    lb, lb_serie, _ = lagesbild.bygg(scb, katalog(), pol, kpi, DATA_DIR)
    print(f"  {len(lb)} serier: " + ", ".join(f"{r.id} ({r.status})" for r in lb.itertuples()))
    print("Riksdagen och opinionen")
    rd = riksdag.bygg(DATA_DIR, KALL_DIR)
    print("  " + ", ".join(f"{k} {len(v)}" for k, v in rd.items()))
    print("Genomslag")
    med = media.bygg(DATA_DIR, rd.get("riksdag_ledamot"))
    print("  " + ", ".join(f"{k} {len(v)}" for k, v in med.items()))
    print("Dekomposition")
    dekomp = reg.dekomposition(stod_psu, vikt_psu, profil_region, val, reg.utbildning_region(scb), namn_alla)
    print(f"  {len(dekomp)} rader")
    partistod = pd.concat([stod_psu, stod_valu], ignore_index=True)
    gruppvikt = pd.concat([vikt_psu, vikt_reg], ignore_index=True)
    profil = pd.concat([profil_ur_stod(stod_psu, vikt_psu), prof_gu], ignore_index=True)
    kontroll = pd.concat([kontroll_psu, kontroll_vikter(vikt_psu, vikt_reg)], ignore_index=True)
    tabeller = {
        "kalla": pd.DataFrame(KALLOR, columns=["kalla", "namn", "utgivare", "url", "beskrivning"]),
        "partistod": partistod, "gruppvikt": gruppvikt, "partiprofil": profil,
        "valresultat_kommun": val, "kommunindikator": ind, "kommunsamband": samband,
        "utsatthet": ntu, "partiexponering": partiexponering(profil[profil.kalla == "scb_psu"], ntu),
        "valdeltagande_grupp": reg_delt, "valdeltagande_region": rr,
        "valresultat_lan": val_lan, "lansindikator": ind_lan, "utsatthet_lan": ntu_lan,
        "partiprofil_region": profil_region, "dekomposition": dekomp,
        "polisen_manad": pol, "kpi_manad": kpi, "fraga_betydelse": f_bet,
        "fraga_rang_parti": f_rang, "bast_politik": f_bast, "som_samhallsproblem": som_p,
        "test_bilar": t_bil, "test_skjutningar": t_skj,
        # Kommunvärdena lagras kompakt (kod i stället för text per rad) för att hålla nere storleken
        "verklighet": verk[verk.niva != "kommun"], "verklighet_indikator": verk_ind,
        "verklighet_kommunvarden": verk_kv,
        "verklighet_forandring": verk_f, "verklighet_kommun": verk_k,
        "valdistrikt_2026": dist, "valdistrikt_tiondel": dist_tio, "valdistrikt_samband": dist_samb,
        **vk, **rd, **med, "norden": nord, "lagesbild": lb, "lagesbild_serie": lb_serie,
        "evidensniva": pd.DataFrame(metod.EVIDENS, columns=["id", "avsnitt", "niva", "sager", "sager_inte"]),
        "kontroll": kontroll,
        "varningar": pd.DataFrame({"varning": varningar}),
        "licens": pd.DataFrame(LICENSER, columns=["kalla", "utgivare", "status", "villkor", "url"]),
    }
    print("Kvalitetskontroller")
    kval = kontroller.kor(tabeller, DATA_DIR, varningar)
    print("  " + ", ".join(f"{k}: {n}" for k, n in kval.status.value_counts().items()))
    tabeller["kvalitet"] = kval
    if DB.exists():
        DB.unlink()
    with sqlite3.connect(DB) as con:
        for namn, df in tabeller.items():
            if df.shape[1] == 0:
                print(f"  {namn}: tom, hoppas över")
                continue
            df.to_sql(namn, con, index=False)
            if len(df) > 150_000:   # stora tabeller komprimeras
                df.to_csv(CSV_DIR / f"{namn}.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
                (CSV_DIR / f"{namn}.csv").unlink(missing_ok=True)
            else:
                df.to_csv(CSV_DIR / f"{namn}.csv", index=False)
            print(f"  {namn}: {len(df)} rader")
    (DATA_DIR / "webb.json").write_text(
        json.dumps(webb(tabeller), ensure_ascii=False, separators=(",", ":"), default=float),
        encoding="utf-8")
    print(f"{len(varningar)} varningar")


if __name__ == "__main__":
    main()
