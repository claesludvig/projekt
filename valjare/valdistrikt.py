"""Valdistrikt 2026 kopplade till SCB:s DeSO-statistik.

Nyckeln data/geo/valdistrikt_deso.csv (från geo.py) anger hur stor del av
varje DeSO-områdes yta som ligger i varje valdistrikt. Distriktets värde är
ett befolkningsvägt medel av DeSO-värdena, där DeSO-befolkningen fördelas
på distrikten efter yta.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

import metod

from tolka import partikod

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD", "ÖVR"]


def _deso(scb_dir: Path, tab: str) -> pd.DataFrame | None:
    f = scb_dir / f"{tab}_deso.csv.gz"
    if not f.exists():
        return None
    df = pd.read_csv(f, dtype=str)
    df["varde"] = pd.to_numeric(df["varde"], errors="coerce")
    df = df[df.Region_kod.str.endswith("_DeSO2025")]
    df["deso"] = df.Region_kod.str[:9]
    return df


def _alder_start(etikett: str) -> int | None:
    m = re.match(r"(\d+)", etikett)
    return int(m.group(1)) if m else None


def deso_indikatorer(scb_dir: Path) -> pd.DataFrame:
    """En rad per DeSO med befolkning och strukturvariabler (procent)."""
    ut = {}
    df = _deso(scb_dir, "TAB6571")
    if df is not None:
        d = df[df.Kon == "totalt"].pivot_table(index="deso", columns="UtlBakgrund", values="varde")
        ut["befolkning"] = d["totalt"]
        ut["utländsk bakgrund"] = 100 * d["utländsk bakgrund"] / d["totalt"]
    df = _deso(scb_dir, "TAB6572")
    if df is not None:
        d = df[df.Kon == "totalt"].pivot_table(index="deso", columns="Fodelseregion", values="varde")
        ovr = next((c for c in d.columns if c.startswith("övriga världen")), None)
        if ovr:
            ut["född utanför Europa"] = 100 * d[ovr] / d["totalt"]
    df = _deso(scb_dir, "TAB6574")
    if df is not None:
        d = df[(df.Kon == "totalt") & (df.Alder != "totalt")].copy()
        d["start"] = d.Alder.map(_alder_start)
        vuxna = d[d.start >= 20].groupby("deso").varde.sum()
        ut["65 år och äldre (av 20+)"] = 100 * d[d.start >= 65].groupby("deso").varde.sum() / vuxna
        ut["20–34 år (av 20+)"] = 100 * d[(d.start >= 20) & (d.start < 35)].groupby("deso").varde.sum() / vuxna
    df = _deso(scb_dir, "TAB6534")
    if df is not None:
        d = df.pivot_table(index="deso", columns="UtbildningsNiva", values="varde")
        kand = [c for c in d.columns if not c.startswith("uppgift")]
        ut["eftergymnasial ≥3 år (25–65)"] = 100 * d[[c for c in kand if "3 år eller mer" in c]].sum(1) / d[kand].sum(1)
        ut["förgymnasial (25–65)"] = 100 * d[[c for c in kand if c.startswith("förgymnasial")]].sum(1) / d[kand].sum(1)
    df = _deso(scb_dir, "TAB6685")
    if df is not None:
        d = df[df.Alder == "totalt ålder"].pivot_table(index="deso", columns="ContentsCode", values="varde")
        for c, namn in (("Låg ekonomisk", "låg ekonomisk standard"), ("Hög ekonomisk", "hög ekonomisk standard")):
            k = next((x for x in d.columns if x.startswith(c)), None)
            if k:
                ut[namn] = d[k]
    df = _deso(scb_dir, "TAB6253")
    if df is not None:
        d = df.pivot_table(index="deso", columns="Upplatelseform", values="varde")
        kand = [c for c in d.columns if c not in ("totalt", "uppgift saknas")]
        ut["hyresrätt"] = 100 * d["hyresrätt"] / d[kand].sum(1)
        ut["småhus/äganderätt"] = 100 * d["äganderätt"] / d[kand].sum(1)
    df = _deso(scb_dir, "TAB6680")
    if df is not None:
        alder = next((a for a in ("20–64 år", "20–65 år", "20–66 år") if a in set(df.Alder)), None)
        if alder:
            d = df[(df.Kon == "totalt") & (df.Alder == alder)].pivot_table(
                index="deso", columns="ContentsCode", values="varde")
            ut[f"sysselsättningsgrad ({alder})"] = 100 * d["antal sysselsatta"] / d["antal totalt"]
    return pd.DataFrame(ut)


def distrikt_roster(xlsx: Path | None) -> pd.DataFrame:
    if xlsx is None or not xlsx.exists():
        return pd.DataFrame()
    df = pd.read_excel(xlsx, sheet_name=1, dtype=str)
    df = df[df.Valdistriktskod.str.len() == 8]      # uppsamlingsdistrikt bort
    df["Röster"] = pd.to_numeric(df["Röster"], errors="coerce")
    df["parti"] = df["Parti/kategori"].map(partikod)
    bas = df.groupby("Valdistriktskod").agg(namn=("Valdistriktsnamn", "first"),
                                             kommunkod=("Kommunkod", "first"),
                                             kommun=("Kommun", "first"), lan=("Länskod", "first"))
    p = df.dropna(subset=["parti"]).pivot_table(index="Valdistriktskod", columns="parti",
                                                 values="Röster", aggfunc="sum")
    ut = bas.join(p.reindex(columns=PARTIER).fillna(0))
    kat = df.pivot_table(index="Valdistriktskod", columns="Parti/kategori", values="Röster", aggfunc="sum")
    ut["giltiga"] = kat.get("Summa giltiga röster")
    ut["rostberattigade"] = kat.get("Röstberättigade")
    return ut.reset_index().rename(columns={"Valdistriktskod": "valdistrikt"})


def distrikt(nyckel: Path, scb_dir: Path, xlsx: Path | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(valdistrikt med strukturvariabler och röster, tiondelstabell, samband)."""
    if not nyckel.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    x = pd.read_csv(nyckel, dtype={"valdistrikt": str, "deso": str})
    ind = deso_indikatorer(scb_dir)
    rost = distrikt_roster(xlsx)
    if ind.empty or rost.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    m = x.merge(ind, left_on="deso", right_index=True, how="left")
    m["vikt"] = m.andel_av_deso * m.befolkning
    vars_ = [c for c in ind.columns if c != "befolkning"]
    g = m.groupby("valdistrikt")
    di = pd.DataFrame({"befolkning_skattad": g.vikt.sum(), "tackning_yta": g.andel_av_distrikt.sum()})
    for c in vars_:
        ok = m[c].notna() & (m.vikt > 0)
        taljare = (m.vikt * m[c]).where(ok).groupby(m.valdistrikt).sum()
        namnare = m.vikt.where(ok).groupby(m.valdistrikt).sum()
        di[c] = (taljare / namnare).where(namnare > 0)
    dist = rost.merge(di, left_on="valdistrikt", right_index=True, how="left")
    for p in PARTIER:
        dist[f"andel_{p}"] = 100 * dist[p] / dist.giltiga
    dist["valdeltagande"] = 100 * dist.giltiga / dist.rostberattigade

    ok = dist[(dist.giltiga >= 100) & (dist.tackning_yta >= 0.9) & (dist.befolkning_skattad >= 100)]
    tio, samb = [], []
    for c in vars_ + ["valdeltagande"]:
        d = ok.dropna(subset=[c]).copy()
        if len(d) < 500:
            continue
        d["tiondel"] = pd.qcut(d[c].rank(method="first"), 10, labels=False) + 1
        for t, dt in d.groupby("tiondel"):
            for p in PARTIER:
                tio.append({"indikator": c, "tiondel": int(t), "parti": p,
                            "andel": 100 * dt[p].sum() / dt.giltiga.sum(),
                            "indikator_medel": float(dt[c].mean()), "n_distrikt": len(dt)})
        for p in PARTIER:
            samb.append({"indikator": c, "parti": p, "n_distrikt": len(d),
                         "r": float(np.corrcoef(d[c], d[f"andel_{p}"])[0, 1])})
    # Intervallet bortser från att närliggande distrikt liknar varandra och är därför för smalt.
    return dist, pd.DataFrame(tio), metod.med_ki(pd.DataFrame(samb), "r", "n_distrikt")
