"""Partiernas genomslag: följare, omnämnanden, talartid och annonser.

Tabeller:
  media_foljare       daterade följarantal per parti/partiledare och plattform (Wikidata)
  media_foljare_nu    senaste kända värde per konto och plattform
  media_omnamnanden   omnämnanden per parti och vecka i nyhetsflödena, med andel av alla omnämnanden
  media_google_nyheter  artiklar per parti och dag i Google Nyheters sökflöde
  media_talartid      anföranden och ord per parti och riksmöte, även per ledamot
  media_annonser      Googles politiska annonser: utgifter per parti och år
  media_wikipedia     sidvisningar per månad på svenska Wikipedia, parti och partiledare
  media_gdelt         svenskspråkiga nyhetsartiklar som nämner partiet per månad (GDELT), andel och ton
  media_sakfragor     sakfrågor som nämns i samma artikel som partiet (nyhetsflödena)
  media_rd_aktivitet  motioner, interpellationer och skriftliga frågor per parti och riksmöte

Följare är inte räckvidd: de säger hur många som valt att följa ett konto, inte hur många som
ser inläggen. Omnämnanden räknas i rubrik och ingress och kan vara både positiva och negativa.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from media_katalog import OMNAMNANDE

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]


AKTUELL_DAGAR = 365   # äldre följarvärden visas inte som aktuella


def foljare(mapp: Path, idag: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Alla daterade följarvärden (egna mätningar och Wikidata) och det senaste per konto och plattform.
    Egna mätningar (foljare_matt.csv) går före Wikidata samma dag. Värden äldre än AKTUELL_DAGAR räknas
    inte som aktuella och hamnar inte i "nu"."""
    delar = []
    f = mapp / "foljare_matt.csv"
    if f.exists():
        m = pd.read_csv(f)
        if len(m):
            delar.append(m.assign(kalla="mätt"))
    f = mapp / "foljare.csv"
    if f.exists():
        try:
            w = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            w = pd.DataFrame()
        if len(w):
            w = w[w.rang.fillna("normal") != "deprecated"]
            delar.append(w.assign(kalla="Wikidata"))
    if not delar:
        return pd.DataFrame(), pd.DataFrame()
    d = pd.concat(delar, ignore_index=True).dropna(subset=["datum", "foljare"])
    d["datum"] = pd.to_datetime(d.datum, errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    d = d.dropna(subset=["datum"])
    d["prio"] = (d.kalla == "mätt").astype(int)
    d = d.sort_values(["datum", "prio"])
    nu = d.groupby(["parti", "roll", "plattform"]).tail(1)
    idag = pd.Timestamp.now().normalize() if idag is None else pd.Timestamp(idag)
    nu = nu[nu.datum >= idag - pd.Timedelta(days=AKTUELL_DAGAR)].reset_index(drop=True)
    return d.drop(columns="prio").reset_index(drop=True), nu.drop(columns="prio")


def _veckor(d: pd.Series) -> pd.Series:
    return d.dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time.dt.date.astype(str)


def artiklar(mapp: Path, ledare: dict[str, str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = mapp / "artiklar.csv.gz"
    if not f.exists():
        return pd.DataFrame(), pd.DataFrame()
    a = pd.read_csv(f, dtype=str)
    a["tid"] = pd.to_datetime(a.publicerad, errors="coerce", utc=True, format="mixed")
    a["tid"] = a.tid.fillna(pd.to_datetime(a.hamtad, errors="coerce", utc=True))
    a = a.dropna(subset=["tid"])
    # Nyhetsflödena: omnämnanden per parti (partinamn och partiledarens fullständiga namn)
    red = a[a.sokt_parti.isna()].drop_duplicates("lank").copy()
    text = (red.titel.fillna("") + " " + red.beskrivning.fillna(""))
    rader = []
    for p, rx in OMNAMNANDE.items():
        m = text.str.contains(rx, regex=True)
        if ledare and ledare.get(p):
            m = m | text.str.contains(re.escape(ledare[p]), regex=True)
        red[p] = m
    red["vecka"] = _veckor(red.tid)
    for (v, fl), d in red.groupby(["vecka", "flode"]):
        for p in PARTIER:
            rader.append({"vecka": v, "flode": fl, "parti": p, "artiklar": int(d[p].sum()), "totalt": len(d)})
    om = pd.DataFrame(rader)
    if len(om):
        tot = om.groupby(["vecka", "flode"]).artiklar.transform("sum")
        om["andel_av_omnamnanden"] = 100 * om.artiklar / tot.replace(0, np.nan)
    # Google Nyheter: artiklar per sökt parti och dag
    g = a[a.sokt_parti.notna()].copy()
    gn = g.assign(dag=g.tid.dt.date.astype(str)).groupby(["dag", "sokt_parti"]).size() \
        .rename("artiklar").reset_index().rename(columns={"sokt_parti": "parti"}) if len(g) else pd.DataFrame()
    return om, gn


def talartid(rd_mapp: Path, ledamoter: pd.DataFrame) -> pd.DataFrame:
    delar = []
    for f in sorted(rd_mapp.glob("anforande_*.csv.gz")):
        try:
            delar.append(pd.read_csv(f, dtype={"rm": str, "parti": str}))
        except pd.errors.EmptyDataError:
            continue
    if not delar:
        return pd.DataFrame()
    d = pd.concat(delar, ignore_index=True)
    d["parti"] = d.parti.replace({"FP": "L"})
    d = d[d.parti.isin(PARTIER)]
    g = d.groupby(["rm", "parti"]).agg(anforanden=("anforanden", "sum"), ord=("ord", "sum")).reset_index()
    rep = d[d.replik.astype(str).str.upper().isin(["Y", "J", "JA", "TRUE", "1"])] \
        .groupby(["rm", "parti"]).anforanden.sum().rename("repliker")
    g = g.merge(rep, on=["rm", "parti"], how="left").fillna({"repliker": 0})
    tot = g.groupby("rm").ord.transform("sum")
    g["andel_av_orden"] = 100 * g.ord / tot
    if len(ledamoter):
        n = ledamoter[ledamoter.voteringar > 0].groupby(["rm", "parti"]).size().rename("ledamoter")
        g = g.merge(n, on=["rm", "parti"], how="left")
        g["ord_per_ledamot"] = g.ord / g.ledamoter
        g["andel_av_ledamoterna"] = 100 * g.ledamoter / g.groupby("rm").ledamoter.transform("sum")
    return g


def annonser(mapp: Path) -> pd.DataFrame:
    from media_katalog import ANNONSOR
    f = mapp / "google_annonser_vecka.csv"
    if not f.exists():
        return pd.DataFrame()
    try:
        d = pd.read_csv(f, dtype=str)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if d.empty:
        return d
    namn = next(c for c in d.columns if re.search(r"(?i)advertiser_name", c))
    vecka = next((c for c in d.columns if re.search(r"(?i)week", c)), None)
    spend = next((c for c in d.columns if re.search(r"(?i)spend.*sek", c)), None) or \
        next((c for c in d.columns if re.search(r"(?i)spend.*eur", c)), None)
    if not vecka or not spend:
        return pd.DataFrame()
    d["parti"] = None
    for p, rx in ANNONSOR.items():
        d.loc[d.parti.isna() & d[namn].str.contains(rx, regex=True, na=False), "parti"] = p
    d = d.dropna(subset=["parti"])
    d["ar"] = d[vecka].str[:4].astype(int)
    d["utgift"] = pd.to_numeric(d[spend], errors="coerce")
    ut = d.groupby(["ar", "parti"]).agg(utgift=("utgift", "sum"), annonsorer=(namn, "nunique")).reset_index()
    ut["valuta"] = "SEK" if "sek" in spend.lower() else "EUR"
    return ut


def wikipedia(mapp: Path) -> pd.DataFrame:
    f = mapp / "wikipedia_visningar.csv"
    if not f.exists():
        return pd.DataFrame()
    d = pd.read_csv(f)
    return d[d.parti.isin(PARTIER)].sort_values(["parti", "roll", "manad"]).reset_index(drop=True)


def gdelt(mapp: Path) -> pd.DataFrame:
    """Per parti och månad: artiklar som nämner partiet, andel av alla partiomnämnanden och genomsnittlig ton
    (vägd med antalet artiklar per dag). GDELT:s ton går från -100 till +100; nyheter ligger oftast under noll."""
    f = mapp / "gdelt.csv.gz"
    if not f.exists():
        return pd.DataFrame()
    d = pd.read_csv(f, dtype={"dag": str})
    d["manad"] = d.dag.str[:4] + "-" + d.dag.str[4:6]
    art = d[d.matt == "artiklar"][["parti", "dag", "manad", "varde"]].rename(columns={"varde": "artiklar"})
    ton = d[d.matt == "ton"][["parti", "dag", "varde"]].rename(columns={"varde": "ton"})
    m = art.merge(ton, on=["parti", "dag"], how="left")
    m["tonvikt"] = m.ton * m.artiklar
    g = m.groupby(["manad", "parti"]).agg(artiklar=("artiklar", "sum"), tonvikt=("tonvikt", "sum")).reset_index()
    g["ton"] = g.tonvikt / g.artiklar.replace(0, np.nan)
    g["andel"] = 100 * g.artiklar / g.groupby("manad").artiklar.transform("sum").replace(0, np.nan)
    # Pågående månad är ofullständig men andelen är jämförbar; totalen jämförs inte
    return g.drop(columns="tonvikt")


def sakfragor(mapp: Path, ledare: dict[str, str] | None = None) -> pd.DataFrame:
    """Hur ofta partiet nämns i samma artikel som en sakfråga (media_katalog.SAKORD), i nyhetsflödena
    och Google Nyheter. Andel av partiets artiklar; en artikel kan höra till flera frågor."""
    from media_katalog import SAKORD as ORD
    f = mapp / "artiklar.csv.gz"
    if not f.exists():
        return pd.DataFrame()
    a = pd.read_csv(f, dtype=str).drop_duplicates("lank")
    text = a.titel.fillna("") + " " + a.beskrivning.fillna("")
    # Partinamnen tas bort innan frågorna söks, annars träffar "Miljöpartiet" frågan miljö
    lag = text.str.replace("|".join(f"(?:{rx})" for rx in OMNAMNANDE.values()), " ", regex=True).str.lower()
    rader = []
    for p, rx in OMNAMNANDE.items():
        m = text.str.contains(rx, regex=True)
        if ledare and ledare.get(p):
            m = m | text.str.contains(re.escape(ledare[p]), regex=True)
        n = int(m.sum())
        if not n:
            continue
        for fr, orx in ORD.items():
            k = int((m & lag.str.contains(orx, regex=True)).sum())
            rader.append({"parti": p, "fraga": fr, "artiklar": k, "partiets_artiklar": n, "andel": 100 * k / n})
    ut = pd.DataFrame(rader)
    if len(ut):
        tid = pd.to_datetime(a.hamtad, errors="coerce")
        ut["fran"], ut["till"] = str(tid.min())[:10], str(tid.max())[:10]
    return ut


def rd_aktivitet(rd_mapp: Path, ledamoter: pd.DataFrame | None) -> pd.DataFrame:
    f = rd_mapp / "aktivitet.csv"
    if not f.exists():
        return pd.DataFrame()
    d = pd.read_csv(f, dtype={"rm": str}).pivot_table(index=["rm", "parti"], columns="typ", values="antal",
                                                      aggfunc="sum").reset_index()
    d.columns.name = None
    if ledamoter is not None and len(ledamoter):
        n = ledamoter[ledamoter.voteringar > 0].groupby(["rm", "parti"]).size().rename("ledamoter")
        d = d.merge(n, on=["rm", "parti"], how="left")
        typer = [c for c in ("mot", "ip", "fr") if c in d]
        d["per_ledamot"] = d[typer].sum(axis=1) / d.ledamoter
    return d


def bygg(data_dir: Path, ledamoter: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    mapp = data_dir / "media"
    fl, nu = foljare(mapp)
    ledare = {}
    if len(nu):
        ledare = nu[nu.roll == "partiledare"].drop_duplicates("parti").set_index("parti").namn.to_dict()
    obj = mapp / "wikidata_objekt.csv"
    if obj.exists():
        o = pd.read_csv(obj)
        ledare = {**o[o.roll == "partiledare"].drop_duplicates("parti").set_index("parti").namn.to_dict(), **ledare}
    om, gn = artiklar(mapp, ledare)
    return {"media_foljare": fl, "media_foljare_nu": nu, "media_omnamnanden": om, "media_google_nyheter": gn,
            "media_talartid": talartid(data_dir / "riksdagen", ledamoter if ledamoter is not None else pd.DataFrame()),
            "media_annonser": annonser(mapp),
            "media_wikipedia": wikipedia(mapp), "media_gdelt": gdelt(mapp),
            "media_sakfragor": sakfragor(mapp, ledare),
            "media_rd_aktivitet": rd_aktivitet(data_dir / "riksdagen", ledamoter),
            "media_ledare": pd.DataFrame([{"parti": p, "namn": n} for p, n in ledare.items()])}
