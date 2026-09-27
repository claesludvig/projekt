"""Verklighetsindikatorer per sakfråga: sammanställning och jämförelser.

Tabeller:
  verklighet            en rad per indikator, region och period (riket, län/region, kommun)
  verklighet_forandring indikatorns förändring per mandatperiod i riket, med riktning
                        (bättre/sämre) och frågans förändrade betydelse enligt Valu och SOM
  verklighet_kommun     samband över kommunerna mellan indikatorns förändring under
                        mandatperioden och partiernas förändring
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from verklighet_katalog import FRAGOR, KOLADA, RIKSBANKEN, SCB_SERIER

VALAR = [2010, 2014, 2018, 2022, 2026]
PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]
BATTRE_KOLADA = {namn: b for _, namn, _, _, b in KOLADA}


def _niva(kod: str) -> str:
    kod = str(kod).zfill(4)
    if kod == "0000":
        return "riket"
    return "region" if kod.startswith("00") else "kommun"


def kolada(data_dir: Path) -> pd.DataFrame:
    delar = []
    for f in sorted((data_dir / "kolada").glob("*.csv.gz")):
        try:
            d = pd.read_csv(f, dtype={"region_kod": str})
        except pd.errors.EmptyDataError:
            continue
        if d.empty:
            continue
        d["region_kod"] = d.region_kod.str.zfill(4)
        d = d[d.region_kod.str.fullmatch(r"\d{4}")].drop_duplicates(["region_kod", "ar"])
        delar.append(pd.DataFrame({
            "fraga": d.fraga, "indikator": d.namn, "kalla": "Kolada " + d.kpi,
            "niva": d.region_kod.map(_niva), "region_kod": d.region_kod,
            "period": d.ar.astype(str), "ar_dec": d.ar.astype(float) + 0.5,
            "varde": pd.to_numeric(d.varde, errors="coerce"),
            "battre": d.namn.map(BATTRE_KOLADA)}))
    return pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()


def _tid(t: str) -> tuple[str, float] | None:
    t = str(t)
    if m := re.fullmatch(r"(\d{4})M(\d\d)", t):
        return t, int(m[1]) + (int(m[2]) - 0.5) / 12
    if m := re.fullmatch(r"(\d{4})K(\d)", t):
        return t, int(m[1]) + (int(m[2]) - 0.5) / 4
    if m := re.fullmatch(r"(\d{4})", t):
        return t, int(m[1]) + 0.5
    if m := re.fullmatch(r"(\d{4})-(\d{4})", t):
        return t, int(m[2]) + 0.5
    return None


def _valj_varde(varden: list[str], onskat: str) -> str | None:
    if onskat in varden:
        return onskat
    return next((v for v in varden if v.strip().lower() == onskat.strip().lower()), None)


def scb_serier(scb, katalog: pd.DataFrame, varningar: list) -> pd.DataFrame:
    """En tidsserie per post i SCB_SERIER.

    Variabler som inte anges i "val" väljs automatiskt: ett "totalt"-värde,
    ett nollårsvärde för ålder, annars det enda värdet. Går det inte att välja
    entydigt hoppas serien över och en varning skrivs."""
    kand = katalog[(katalog.tema == "verklighet")]
    delar = []
    for post in SCB_SERIER:
        tab = post["tabell"]
        if not re.fullmatch(r"TAB\d+", tab):
            traff = kand[kand.rubrik.str.contains(tab.replace("(", "(?:").replace("(?:?", "(?"), regex=True, na=False)]
            tabeller = list(traff.id)
        else:
            tabeller = [tab]
        bast = None
        for t in tabeller:
            df = scb(t)
            if df is None or df.empty:
                continue
            df = df[df.ContentsCode.str.contains(post["innehall"], regex=True, na=False)]
            if df.empty:
                continue
            cc = list(dict.fromkeys(df.ContentsCode))
            df = df[df.ContentsCode == cc[0]]
            dims = [c for c in df.columns if not c.endswith("_kod")
                    and c not in ("tabell", "Tid", "ContentsCode", "varde")]
            kvot = post.get("kvot")
            if kvot and kvot[0].startswith("~"):
                kvot = (next((d for d in dims if re.search(kvot[0][1:], d)), kvot[0]), *kvot[1:])
            ok = True
            summera = []
            for d in dims:
                varden = list(dict.fromkeys(df[d].astype(str)))
                if kvot and d == kvot[0]:
                    continue
                onskat = post["val"].get(d)
                if onskat is None:   # nycklar som börjar med ~ är regex mot variabelnamnet
                    onskat = next((v for k, v in post["val"].items()
                                   if k.startswith("~") and re.search(k[1:], d)), None)
                if isinstance(onskat, list):
                    df = df[df[d].isin(onskat)]
                    summera.append(d)
                    continue
                if isinstance(onskat, str) and onskat.startswith("~"):
                    val = next((v for v in varden if re.search(onskat[1:], v)), None)
                else:
                    val = _valj_varde(varden, onskat) if onskat else None
                if val is None:
                    val = next((v for v in varden if re.search(
                        r"(?i)^(totalt|samtliga|hela|riket|män och kvinnor|båda|totala|summa)", v.strip())), None)
                if val is None and re.search(r"(?i)ålder|alder", d):
                    val = next((v for v in varden if re.match(r"^0( år)?$", v.strip())), None)
                if val is None and len(varden) == 1:
                    val = varden[0]
                if val is None:
                    ok = False
                    break
                df = df[df[d].astype(str) == val]
            if not ok or df.empty:
                continue
            if kvot:
                col, tal, nam = kvot
                p = df.groupby(["Tid", col]).varde.sum().unstack()
                hitta = lambda x: next((c for c in p.columns if re.search(x, c)), None)  # noqa: E731
                tal, nam = hitta(tal), [hitta(n) for n in nam]
                if tal is None or None in nam:
                    continue
                s_ = 100 * p[tal] / p[nam].sum(axis=1)
            else:
                s_ = df.groupby("Tid").varde.sum()
            s_ = s_.dropna()
            s_ = s_[[(_tid(t) is not None) for t in s_.index]]
            if bast is None or len(s_) > len(bast[1]):
                bast = (t, s_, cc[0])
        if bast is None:
            varningar.append(f"verklighet: hittade ingen entydig SCB-serie för '{post['namn']}'")
            continue
        t, s_, cc = bast
        delar.append(pd.DataFrame({
            "fraga": post["fraga"], "indikator": post["namn"], "kalla": f"SCB {t}: {cc}",
            "niva": "riket", "region_kod": "0000", "period": list(s_.index),
            "ar_dec": [_tid(x)[1] for x in s_.index], "varde": s_.values, "battre": post["battre"]}))
    return pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()


def riksbanken(data_dir: Path) -> pd.DataFrame:
    delar = []
    for fraga, namn, serie, battre in RIKSBANKEN:
        f = data_dir / "riksbanken" / f"{serie}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f)
        dcol = next((c for c in d.columns if "date" in c.lower()), None)
        vcol = next((c for c in d.columns if "value" in c.lower()), None)
        if not dcol or not vcol:
            continue
        d["t"] = pd.to_datetime(d[dcol]).dt.to_period("M")
        m = d.groupby("t")[vcol].mean()
        delar.append(pd.DataFrame({
            "fraga": fraga, "indikator": namn, "kalla": f"Riksbanken {serie}", "niva": "riket",
            "region_kod": "0000", "period": [str(p).replace("-", "M") for p in m.index],
            "ar_dec": [p.year + (p.month - 0.5) / 12 for p in m.index], "varde": m.values, "battre": battre}))
    return pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()


def _arsvarde(d: pd.DataFrame, ar: int) -> float | None:
    """Värdet för året (medel av månader/kvartal); faller tillbaka på året innan."""
    for a in (ar, ar - 1):
        x = d[np.floor(d.ar_dec) == a].varde.dropna()
        if len(x):
            return float(x.mean())
    return None


def forandring(v: pd.DataFrame, betydelse: pd.DataFrame, som: pd.DataFrame) -> pd.DataFrame:
    """Riksnivå: indikatorns förändring per mandatperiod och frågans betydelse."""
    fraga_valu = {f: vf for f, vf, _ in FRAGOR}
    fraga_som = {f: sf for f, _, sf in FRAGOR}
    rader = []
    r = v[v.niva == "riket"]
    for (fraga, ind), d in r.groupby(["fraga", "indikator"]):
        battre = d.battre.iloc[0]
        for y0, y1 in zip(VALAR, VALAR[1:]):
            a, b = _arsvarde(d, y0), _arsvarde(d, y1)
            if a is None or b is None:
                continue
            pct = 100 * (b - a) / abs(a) if a else None
            riktning = None
            if battre in ("hogre", "lagre") and b != a:
                riktning = "bättre" if (b > a) == (battre == "hogre") else "sämre"
            vb = betydelse[betydelse.fraga == fraga_valu.get(fraga)] if not betydelse.empty else pd.DataFrame()
            sb = som[som.omrade == fraga_som.get(fraga)] if not som.empty else pd.DataFrame()
            gv = lambda df, col, y: (df[df.ar == y][col].mean() if len(df) and (df.ar == y).any() else None)  # noqa: E731
            rader.append({"fraga": fraga, "valu_fraga": fraga_valu.get(fraga), "indikator": ind,
                          "fran": y0, "till": y1, "varde_fran": a, "varde_till": b,
                          "forandring": b - a, "forandring_pct": pct, "riktning": riktning,
                          "valu_betydelse_fran": gv(vb, "andel", y0), "valu_betydelse_till": gv(vb, "andel", y1),
                          # SOM mäts på hösten: hösten före valet
                          "som_fran": gv(sb, "andel", y0 - 1), "som_till": gv(sb, "andel", y1 - 1)})
    return pd.DataFrame(rader)


def kommunsamband(v: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
    """Förändring i indikatorn under mandatperioden mot förändring i partiets andel."""
    k = v[v.niva == "kommun"]
    if k.empty:
        return pd.DataFrame()
    vv = val.dropna(subset=["parti"])
    g = vv.groupby(["ar", "kommunkod", "parti"]).roster.sum()
    andel = (100 * g / g.groupby(level=[0, 1]).transform("sum")).rename("andel").reset_index()
    rader = []
    for (fraga, ind), d in k.groupby(["fraga", "indikator"]):
        d = d.assign(ar=np.floor(d.ar_dec).astype(int))
        for y0, y1 in zip(VALAR, VALAR[1:]):
            a0 = d[d.ar == y0 - 1].set_index("region_kod").varde
            a1 = d[d.ar == min(y1 - 1, d.ar.max())].set_index("region_kod").varde
            if a0.empty or a1.empty or (y1 - 1) - d.ar.max() > 1:
                continue
            dx = (a1 - a0).dropna()
            for p in PARTIER:
                d0 = andel[(andel.ar == y0) & (andel.parti == p)].set_index("kommunkod").andel
                d1 = andel[(andel.ar == y1) & (andel.parti == p)].set_index("kommunkod").andel
                j = pd.concat([dx, d1 - d0, a1], axis=1, keys=["x", "y", "niva"]).dropna()
                if len(j) < 100 or j.x.std() == 0:
                    continue
                rader.append({"fraga": fraga, "indikator": ind, "fran": y0, "till": y1, "parti": p,
                              "r_forandring": float(np.corrcoef(j.x, j.y)[0, 1]),
                              "r_niva": float(np.corrcoef(j.niva, j.y)[0, 1]),
                              "n_kommuner": len(j)})
    return pd.DataFrame(rader)


def fran_fragor(pol: pd.DataFrame, kpi: pd.DataFrame) -> pd.DataFrame:
    """Polisens skjutningar/sprängningar och KPI-serier som verklighetsindikatorer."""
    delar = []
    if not pol.empty:
        for (typ, matt), fraga, namn in ((("skjutningar", "skjutningar"), "lag", "Skjutningar per år"),
                                         (("skjutningar", "avlidna"), "lag", "Döda i skjutningar per år"),
                                         (("sprängningar", "detonationer"), "lag", "Sprängningar per år")):
            d = pol[(pol.typ == typ) & (pol.matt == matt)]
            if d.empty:
                continue
            reg = d[d.polisregion != "Totalt"].groupby(["polisregion", "ar"]).agg(n=("antal", "sum"), m=("manad", "nunique")).reset_index()
            tot = d[d.polisregion == "Totalt"].groupby("ar").agg(n=("antal", "sum"), m=("manad", "nunique")).reset_index()
            tot = tot[tot.m == 12]   # bara hela år
            delar.append(pd.DataFrame({"fraga": fraga, "indikator": namn, "kalla": "Polismyndigheten",
                                       "niva": "riket", "region_kod": "0000", "period": tot.ar.astype(str),
                                       "ar_dec": tot.ar + 0.5, "varde": tot.n.astype(float), "battre": "lagre"}))
            reg = reg[reg.m == 12]
            delar.append(pd.DataFrame({"fraga": fraga, "indikator": namn, "kalla": "Polismyndigheten",
                                       "niva": "polisregion", "region_kod": reg.polisregion, "period": reg.ar.astype(str),
                                       "ar_dec": reg.ar + 0.5, "varde": reg.n.astype(float), "battre": "lagre"}))
    if not kpi.empty:
        for serie, fraga, namn in (("El", "energi", "Elpris egnahem (KPI, 1980=100)"),
                                   ("Bensin", "egen_ekonomi", "Bensinpris (KPI, 1980=100)"),
                                   ("Diesel", "egen_ekonomi", "Dieselpris (KPI, 1980=100)"),
                                   ("Räntekostnader", "egen_ekonomi", "Räntekostnader egnahem (KPI)")):
            d = kpi[kpi.serie == serie]
            if d.empty:
                continue
            delar.append(pd.DataFrame({"fraga": fraga, "indikator": namn, "kalla": "SCB KPI (TAB5160)",
                                       "niva": "riket", "region_kod": "0000",
                                       "period": [f"{a}M{m:02d}" for a, m in zip(d.ar, d.manad)],
                                       "ar_dec": d.ar + (d.manad - 0.5) / 12, "varde": d.index_1980, "battre": "lagre"}))
    return pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()


def bygg(scb, katalog, data_dir, betydelse, som, val, varningar, pol=None, kpi=None):
    extra = fran_fragor(pol if pol is not None else pd.DataFrame(), kpi if kpi is not None else pd.DataFrame())
    delar = [d for d in (kolada(data_dir), scb_serier(scb, katalog, varningar), riksbanken(data_dir), extra)
             if not d.empty]
    v = pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()
    if v.empty:
        return v, pd.DataFrame(), pd.DataFrame()
    v = v.dropna(subset=["varde"])
    return v, forandring(v, betydelse, som), kommunsamband(v, val)
