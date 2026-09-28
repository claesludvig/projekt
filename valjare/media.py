"""Partiernas genomslag: följare, omnämnanden, talartid och annonser.

Tabeller:
  media_foljare       daterade följarantal per parti/partiledare och plattform (Wikidata)
  media_foljare_nu    senaste kända värde per konto och plattform
  media_omnamnanden   omnämnanden per parti och vecka i nyhetsflödena, med andel av alla omnämnanden
  media_google_nyheter  artiklar per parti och dag i Google Nyheters sökflöde
  media_talartid      anföranden och ord per parti och riksmöte, även per ledamot
  media_annonser      Googles politiska annonser: utgifter per parti och år

Följare är inte räckvidd: de säger hur många som valt att följa ett konto, inte hur många som
ser inläggen. Omnämnanden räknas i rubrik och ingress och kan vara både positiva och negativa.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from media_katalog import OMNAMNANDE

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]


def foljare(mapp: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = mapp / "foljare.csv"
    if not f.exists():
        return pd.DataFrame(), pd.DataFrame()
    try:
        d = pd.read_csv(f)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), pd.DataFrame()
    if d.empty:
        return d, d
    d = d[d.rang.fillna("normal") != "deprecated"].dropna(subset=["datum", "foljare"])
    d["datum"] = pd.to_datetime(d.datum, errors="coerce")
    d = d.dropna(subset=["datum"]).sort_values("datum")
    nu = d.groupby(["parti", "roll", "namn", "plattform"]).tail(1).reset_index(drop=True)
    # Wikidata uppdateras ojämnt: värden mer än tre år äldre än det senaste jämförs inte (t.ex. ett
    # konto från 2018 mot ett från 2025)
    nu = nu[nu.datum >= nu.datum.max() - pd.DateOffset(years=3)].reset_index(drop=True)
    return d, nu


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
            "media_ledare": pd.DataFrame([{"parti": p, "namn": n} for p, n in ledare.items()])}
