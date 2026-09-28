"""Riksdagsvalkretsarna (29): valresultat, mandat och verklighetsindikatorer.

Kommunernas indelning i valkretsar tas ur Valmyndighetens resultatfil. Tre län
är delade (Stockholm, Skåne, Västra Götaland). Indikatorer som finns per kommun
viktas ihop med antalet röstberättigade 2026. Indikatorer som bara finns per
region eller län får länets värde, och Polisens siffror polisregionens värde;
kolumnen kallniva säger vilket.

Tabeller:
  valkrets             en rad per valkrets (namn, län, kommuner, mandat)
  valkrets_kommun      kommun -> valkrets
  valresultat_valkrets partiernas andel och mandat per valkrets och val
  valkrets_indikator   indikator per valkrets och år, med rikets värde och plats av 29
  valkrets_oversikt    senaste värdet och förändringen på fyra år, mot riket
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from fragor import POLISREGION_LAN
from tolka import partikod
from verklighet_katalog import mal

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]
LAN_POLISREGION = {l: r for r, ls in POLISREGION_LAN.items() for l in ls}
# NTU-indikatorer (Brå) som visas per valkrets, med kort namn
NTU = {
    "Självrapporterad utsatthet för något brott mot enskild person": "Utsatt för brott mot person (NTU, %)",
    "Otrygghet vid utevistelse sent på kvällen i det egna bostadsområdet": "Otrygg ute sent i området (NTU, %)",
    "Oro över brottsligheten i samhället": "Oro över brottsligheten (NTU, %)",
    "Förtroende för rättsväsendet som helhet": "Förtroende för rättsväsendet (NTU, %)",
    "Förtroende för polisens sätt att bedriva sitt arbete": "Förtroende för polisen (NTU, %)",
}
STRUKTUR = {  # kommunindikator -> (fråga, namn)
    "utländsk bakgrund": ("befolkning", "Utländsk bakgrund (%)"),
    "eftergymnasial ≥3 år (25–64)": ("befolkning", "Eftergymnasial utbildning ≥3 år, 25–64 (%)"),
    "valdeltagande riksdagsval": ("demokrati", "Valdeltagande riksdagsval (%)"),
}


def _kol(df: pd.DataFrame, monster: str) -> str:
    return next(c for c in df.columns if re.search(monster, str(c), re.I | re.S))


def karta(xlsx: Path) -> pd.DataFrame:
    k = pd.read_excel(xlsx, sheet_name="Per Kommun")
    k = pd.DataFrame({
        "kommunkod": k[_kol(k, r"^kommunkod")].astype(int).astype(str).str.zfill(4),
        "kommun": k[_kol(k, r"^kommunnamn|^kommun$")],
        "valkrets_kod": k[_kol(k, r"valkretskod")].astype(int).astype(str).str.zfill(2),
        "valkrets": k[_kol(k, r"valkrets$")]}).drop_duplicates()
    k["lan"] = k.kommunkod.str[:2]
    return k.sort_values(["valkrets_kod", "kommunkod"]).reset_index(drop=True)


def rostberattigade(xlsx: Path) -> pd.Series:
    """Röstberättigade 2026 per kommun (summa över valdistrikten)."""
    d = pd.read_excel(xlsx, sheet_name="Per distrikt")
    dk, kk, rb = _kol(d, r"valdistriktskod"), _kol(d, r"^kommunkod"), _kol(d, r"röstberättigade")
    d = d.drop_duplicates(dk)
    return d.groupby(d[kk].astype(int).astype(str).str.zfill(4))[rb].sum()


def resultat(xlsx: Path, kar: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
    """Andel och mandat per parti och valkrets: 1998–2022 ur kommunresultaten
    (dagens indelning), 2022 och 2026 ur Valmyndighetens valkretsfil."""
    v = pd.read_excel(xlsx, sheet_name="Valkrets")
    kod = v[_kol(v, r"valkretskod")].astype(int).astype(str).str.zfill(2)
    kat = v[_kol(v, r"parti|kategori")].astype(str)
    rader = []
    for ar, rcol, acol, mcol in ((2026, r"antal.*röster 2026", r"andel.*röster 2026", r"mandat 2026"),
                                 (2022, r"antal.*röster 2022", r"andel.*röster 2022", r"mandat 2022")):
        r, m = pd.to_numeric(v[_kol(v, rcol)], errors="coerce"), pd.to_numeric(v[_kol(v, mcol)], errors="coerce")
        andel = pd.to_numeric(v[_kol(v, acol)], errors="coerce")
        for k, ka, ro, an, ma in zip(kod, kat, r, andel, m):
            if re.search(r"(?i)^valdeltagande", ka):
                rader.append({"ar": ar, "valkrets_kod": k, "parti": "valdeltagande", "roster": None,
                              "andel": 100 * an if an <= 1 else an, "mandat": None, "kalla": "Valmyndigheten"})
                continue
            p = None if re.search(r"(?i)ogiltig|giltiga röster|röstberättigade", ka) else partikod(ka)
            if p:
                rader.append({"ar": ar, "valkrets_kod": k, "parti": p, "roster": ro, "andel": None,
                              "mandat": ma, "kalla": "Valmyndigheten"})
    d = pd.DataFrame(rader)
    hist = val[(val.ar >= 1998) & (val.ar < 2022)].dropna(subset=["parti"]).merge(
        kar[["kommunkod", "valkrets_kod"]], on="kommunkod")
    hist = hist.groupby(["ar", "valkrets_kod", "parti"]).roster.sum().reset_index() \
        .assign(kalla="SCB, kommunresultat i dagens valkretsindelning")
    d = pd.concat([hist, d], ignore_index=True)
    p = d.parti != "valdeltagande"
    tot = d[p].groupby(["ar", "valkrets_kod"]).roster.transform("sum")
    d.loc[p, "andel"] = 100 * d.loc[p, "roster"] / tot
    return d


def _vagt(d: pd.DataFrame, kar: pd.DataFrame, w: pd.Series, summa: bool) -> pd.DataFrame:
    """kommunkod, ar, varde -> valkrets_kod, ar, varde (kräver 80 % täckning)."""
    d = d.merge(kar[["kommunkod", "valkrets_kod"]], on="kommunkod").assign(w=lambda x: x.kommunkod.map(w))
    d = d.dropna(subset=["varde", "w"])
    W = kar.assign(w=kar.kommunkod.map(w)).groupby("valkrets_kod").w.sum()
    g = d.groupby(["valkrets_kod", "ar"])
    ut = pd.DataFrame({
        "varde": g.varde.sum() if summa else g.apply(lambda x: np.average(x.varde, weights=x.w), include_groups=False),
        "tackning": g.w.sum()}).reset_index()
    ut["tackning"] = ut.tackning / ut.valkrets_kod.map(W)
    return ut[ut.tackning >= 0.8]


def indikatorer(kar, w, verk, kommunind, ntu_lan, lansnamn, pol, scb, dist) -> pd.DataFrame:
    vk_lan = kar.groupby("valkrets_kod").lan.first()
    delar = []

    def lagg(d, fraga, namn, kalla, kallniva, riket):
        """d: valkrets_kod, ar, varde; riket: Series ar -> värde."""
        if d.empty:
            return
        d = d.assign(fraga=fraga, indikator=namn, kalla=kalla, kallniva=kallniva)
        d["riket"] = d.ar.map(riket)
        delar.append(d[["fraga", "indikator", "kalla", "kallniva", "valkrets_kod", "ar", "varde", "riket"]])

    # Kolada m.fl. (verklighet): kommuner om de finns, annars regionens värde
    v = verk[verk.niva.isin(["kommun", "region", "riket"])].copy()
    v["ar"] = np.floor(v.ar_dec).astype(int)
    for (fraga, ind), d in v.groupby(["fraga", "indikator"]):
        d = d.groupby(["niva", "region_kod", "ar"]).varde.mean().reset_index()
        riket = d[d.niva == "riket"].set_index("ar").varde
        kallor = verk[verk.indikator == ind].kalla.iloc[0]
        k = d[d.niva == "kommun"].rename(columns={"region_kod": "kommunkod"})
        fran_kommun = _vagt(k, kar, w, summa=bool(re.search(r"totalt \(", ind))) if len(k) else pd.DataFrame()
        r = d[d.niva == "region"]
        fran_lan = pd.DataFrame()
        if len(r):
            r = r.assign(lan=r.region_kod.str[2:])
            fran_lan = pd.DataFrame([{"valkrets_kod": vk, "ar": a, "varde": x}
                                     for vk, l in vk_lan.items() for a, x in
                                     r[r.lan == l].set_index("ar").varde.items()])
        if len(fran_kommun):
            lagg(fran_kommun, fraga, ind, kallor, "kommuner", riket)
            # år som saknas i kommundata men finns per region fylls inte i: blandas inte
        elif len(fran_lan):
            lagg(fran_lan, fraga, ind, kallor, "län", riket)

    # Befolkningens sammansättning och valdeltagande (SCB, per kommun)
    for ki, (fraga, namn) in STRUKTUR.items():
        k = kommunind[kommunind.indikator == ki][["kommunkod", "ar", "varde"]]
        if k.empty:
            continue
        alla = k.assign(w=k.kommunkod.map(w)).dropna()
        riket = alla.groupby("ar").apply(lambda x: np.average(x.varde, weights=x.w), include_groups=False)
        lagg(_vagt(k, kar, w, False), fraga, namn, "SCB", "kommuner", riket)

    # Brå NTU per län
    if not ntu_lan.empty:
        kod = {n: k for k, n in lansnamn.items()}
        n = ntu_lan[ntu_lan.grupp.astype(str).str.startswith("Samtliga") & ntu_lan.indikator.isin(NTU)]
        for ind, d in n.groupby("indikator"):
            riket = d[d.lansnamn == "Hela landet"].set_index("ar").andel
            d = d.assign(lan=d.lansnamn.map(kod)).dropna(subset=["lan"])
            ut = pd.DataFrame([{"valkrets_kod": vk, "ar": a, "varde": x}
                               for vk, l in vk_lan.items() for a, x in d[d.lan == l].set_index("ar").andel.items()])
            lagg(ut, "lag", NTU[ind], "Brå, NTU", "län", riket)

    # Polisen: skjutningar och sprängningar per 100 000 invånare i polisregionen
    bef = scb("TAB6571") if scb else None
    if pol is not None and not pol.empty and bef is not None:
        bef = bef[(bef.Kon == "totalt") & (bef.UtlBakgrund == "totalt") & (bef.Region_kod.str.len() == 2)]
        bef = bef.assign(pr=bef.Region_kod.map(LAN_POLISREGION), ar=bef.Tid.astype(int)).dropna(subset=["pr"])
        bpr = bef.groupby(["pr", "ar"]).varde.sum()
        brik = bef.groupby("ar").varde.sum()
        for (typ, matt), namn in ((("skjutningar", "skjutningar"), "Skjutningar per 100 000 inv"),
                                  (("skjutningar", "avlidna"), "Döda i skjutningar per 100 000 inv"),
                                  (("sprängningar", "detonationer"), "Sprängningar per 100 000 inv")):
            d = pol[(pol.typ == typ) & (pol.matt == matt)]
            if d.empty:
                continue
            g = d.groupby(["polisregion", "ar"]).agg(n=("antal", "sum"), m=("manad", "nunique")).reset_index()
            g = g[g.m == 12]
            g["bef"] = [bpr.get((r, min(a, bef.ar.max()))) for r, a in zip(g.polisregion, g.ar)]
            g["per"] = 1e5 * g.n / g.bef
            tot = g[g.polisregion == "Totalt"]
            riket = pd.Series(1e5 * tot.n.values / [brik.get(min(a, bef.ar.max())) for a in tot.ar], index=tot.ar)
            ut = pd.DataFrame([{"valkrets_kod": vk, "ar": a, "varde": x}
                               for vk, l in vk_lan.items()
                               for a, x in g[g.polisregion == LAN_POLISREGION.get(l)].set_index("ar").per.items()])
            lagg(ut.dropna(), "lag", namn, "Polismyndigheten", "polisregion", riket)

    # Valdeltagandets skillnad inom valkretsen (valdistrikten 2026)
    if dist is not None and not dist.empty:
        d = dist[(dist.giltiga >= 100) & dist["låg ekonomisk standard"].notna()] \
            .merge(kar[["kommunkod", "valkrets_kod"]], on="kommunkod")

        def gap(x):
            q = x["låg ekonomisk standard"].rank(pct=True)
            fattig, rik = x[q > 0.8], x[q <= 0.2]
            return 100 * (fattig.giltiga.sum() / fattig.rostberattigade.sum()
                          - rik.giltiga.sum() / rik.rostberattigade.sum())
        per = d.groupby("valkrets_kod").apply(gap, include_groups=False).rename("varde").reset_index().assign(ar=2026)
        lagg(per, "demokrati", "Valdeltagande 2026: femtedelen distrikt med mest låg ekonomisk standard "
             "minus femtedelen med minst (e.)", "Valmyndigheten, SCB (DeSO)", "valdistrikt",
             pd.Series({2026: gap(d)}))

    if not delar:
        return pd.DataFrame()
    ut = pd.concat(delar, ignore_index=True)
    ut["rang"] = ut.groupby(["indikator", "ar"]).varde.rank(ascending=False, method="min")
    ut["antal"] = ut.groupby(["indikator", "ar"]).varde.transform("count")
    return ut


def oversikt(ind: pd.DataFrame) -> pd.DataFrame:
    """Senaste år per indikator och valkrets, förändring på fyra år mot riket."""
    rader = []
    for (ind_, vk), d in ind.groupby(["indikator", "valkrets_kod"]):
        d = d.set_index("ar").sort_index()
        a = d.index.max()
        f = a - 4 if (a - 4) in d.index else None
        m = mal(ind_)
        rad = {"indikator": ind_, "fraga": d.fraga.iloc[0], "kallniva": d.kallniva.iloc[0],
               "valkrets_kod": vk, "ar": int(a), "varde": d.varde[a], "riket": d.riket[a],
               "rang": d.rang[a], "antal": d.antal[a], "fran_ar": f,
               "forandring": None if f is None else d.varde[a] - d.varde[f],
               "riket_forandring": None if f is None else d.riket[a] - d.riket[f],
               "mal_riktning": m["mal_riktning"], "mal_varde": m["mal_varde"]}
        rader.append(rad)
    return pd.DataFrame(rader)


def bygg(xlsx_resultat, val, verk, kommunind, ntu_lan, lansnamn, pol, scb, dist):
    if xlsx_resultat is None or not Path(xlsx_resultat).exists():
        return {}
    kar = karta(xlsx_resultat)
    w = rostberattigade(xlsx_resultat)
    res = resultat(xlsx_resultat, kar, val)
    ind = indikatorer(kar, w, verk, kommunind, ntu_lan, lansnamn, pol, scb, dist)
    m = res[res.parti.isin(PARTIER + ["ÖVR"])].groupby(["valkrets_kod", "ar"]).mandat.sum().unstack()
    vk = kar.groupby(["valkrets_kod", "valkrets"]).agg(
        lan=("lan", "first"), kommuner=("kommun", lambda x: ", ".join(x)), n_kommuner=("kommun", "size")).reset_index()
    vk["rostberattigade_2026"] = vk.valkrets_kod.map(kar.assign(w=kar.kommunkod.map(w)).groupby("valkrets_kod").w.sum())
    vk["mandat_2022"] = vk.valkrets_kod.map(m.get(2022))
    vk["mandat_2026"] = vk.valkrets_kod.map(m.get(2026))
    return {"valkrets": vk, "valkrets_kommun": kar, "valresultat_valkrets": res,
            "valkrets_indikator": ind, "valkrets_oversikt": oversikt(ind) if not ind.empty else pd.DataFrame()}
