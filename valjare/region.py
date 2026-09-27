"""Regional nedbrytning: län och kommun.

- valresultat_lan: riksdagsval per län 1973–2026 (summerat från kommunerna)
- regionindikatorer: strukturvariabler för län (samma tabeller som kommunerna)
- ntu_lan: Brå NTU per län 2016–2025
- raka: skattade partiprofiler per län och kommun (IPF)
- dekomposition: förändring = sammansättningseffekt + beteendeeffekt
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD", "ÖVR"]

# Registrets grupper (TAB5107) ↔ PSU-tabellernas grupper
REG_TILL_PSU = {
    "ålder (4 klasser)": ("ålder (4 klasser)", {g: g for g in ["18–29 år", "30–49 år", "50–64 år", "65+ år"]}),
    "utbildning (3 nivåer)": ("utbildning", {
        "förgymnasial utbildning": ["förgymnasial utbildning"],
        "gymnasial utbildning": ["gymnasial utbildning"],
        "eftergymnasial utbildning": ["eftergymnasial utbildning mindre än 3 år",
                                      "eftergymnasial utbildning 3 år eller mer"]}),
    "född i Sverige/utrikes": ("född i Sverige/utrikes", {"inrikes födda": "inrikes födda",
                                                          "utrikes födda": "utrikes födda"}),
    "inkomst (kvintil)": ("inkomst (kvintil)", {k: f"{k} %" for k in ["0–20", "21–40", "41–60", "61–80", "81–100"]}),
}


def lansnamn(scb) -> dict[str, str]:
    df = scb("TAB6571")
    if df is None:
        return {}
    d = df[df.Region_kod.str.len() == 2][["Region_kod", "Region"]].drop_duplicates()
    return {k: re.sub(r"^\d+\s+", "", v) for k, v in zip(d.Region_kod, d.Region)}


def valresultat_lan(val: pd.DataFrame, namn: dict) -> pd.DataFrame:
    v = val.dropna(subset=["parti"]).copy()
    v["lan"] = v.kommunkod.str[:2]
    g = v.groupby(["ar", "lan", "parti", "status"], as_index=False).roster.sum()
    g["andel"] = 100 * g.roster / g.groupby(["ar", "lan"]).roster.transform("sum")
    g["lansnamn"] = g.lan.map(namn)
    riket = v.groupby(["ar", "parti", "status"], as_index=False).roster.sum()
    riket["andel"] = 100 * riket.roster / riket.groupby("ar").roster.transform("sum")
    riket["lan"], riket["lansnamn"] = "00", "Riket"
    return pd.concat([g, riket], ignore_index=True)


def ntu_lan(xlsx: Path | None) -> pd.DataFrame:
    if xlsx is None or not xlsx.exists():
        return pd.DataFrame()
    bok = pd.ExcelFile(xlsx)
    rader = []
    for blad in bok.sheet_names:
        if not re.match(r"^R[345]\.\d+\s*$", blad):
            continue
        df = pd.read_excel(bok, sheet_name=blad, header=None)
        rubrik = str(df.iloc[1, 0]).split("\n")[0]
        ind = re.sub(r"^Tabell \S+\s*", "", rubrik)
        ind = re.sub(r"\s*\(\d+(, \d+)*\)", "", ind)
        ind = re.sub(r",? (enligt NTU|\d{4}–\d{4}).*$", "", ind).strip(" .")
        hdr = next((i for i in range(2, 6) if any(re.match(r"^\d{4}", str(x)) for x in df.iloc[i])), None)
        if hdr is None:
            continue
        kol = {j: int(str(x)[:4]) for j, x in enumerate(df.iloc[hdr])
               if re.match(r"^\d{4}", str(x)) and "Konfidens" not in str(x)}
        grupp = df.iloc[:, 0].where(df.index > hdr).ffill()
        for i in range(hdr + 1, len(df)):
            lan = df.iloc[i, 1]
            if not isinstance(lan, str) or len(lan) > 40:
                continue
            for j, ar in kol.items():
                v = pd.to_numeric(df.iloc[i, j], errors="coerce")
                if pd.notna(v):
                    rader.append({"kalla": "bra_ntu", "tabell": blad.strip().replace(".", ":"),
                                  "indikator": ind, "grupp": grupp.iloc[i], "lansnamn": lan.strip(),
                                  "ar": ar, "andel": float(v)})
    return pd.DataFrame(rader)


# ---------- IPF ----------

def _ipf(seed: np.ndarray, rad: np.ndarray, kol: np.ndarray, varv: int = 200) -> np.ndarray:
    m = seed.copy()
    for _ in range(varv):
        m *= (rad / np.maximum(m.sum(1), 1e-12))[:, None]
        m *= (kol / np.maximum(m.sum(0), 1e-12))[None, :]
        if np.abs(m.sum(1) - rad).max() < 1e-6 * rad.sum():
            break
    return m


def _psu_stod(stod: pd.DataFrame, vikt: pd.DataFrame, psu_dim: str, period: str,
              karta: dict) -> pd.DataFrame | None:
    """PSU:s stöd per registergrupp (rad) och parti (kolumn), andelar som summerar till 1."""
    s = stod[(stod.kalla == "scb_psu") & (stod.dimension == psu_dim) & (stod.period == period)
             & (stod.kon == "alla")]
    if s.empty:
        return None
    piv = s.pivot_table(index="grupp", columns="parti", values="andel")
    w = vikt[(vikt.dimension == psu_dim) & (vikt.period == period) & (vikt.kon == "alla")] \
        .set_index("grupp").andel
    ut = {}
    for rg, pg in karta.items():
        pgs = pg if isinstance(pg, list) else [pg]
        pgs = [g for g in pgs if g in piv.index]
        if not pgs:
            return None
        vv = w.reindex(pgs).fillna(1.0)
        ut[rg] = (piv.loc[pgs].mul(vv, axis=0).sum() / vv.sum())
    df = pd.DataFrame(ut).T.reindex(columns=PARTIER).fillna(0.1).clip(lower=0.1)
    return df.div(df.sum(1), axis=0)


def raka(stod, vikt, reg_delt_region: pd.DataFrame, val: pd.DataFrame, namn: dict) -> pd.DataFrame:
    """Skattad partiprofil per region: PSU:s nationella stöd per grupp som
    startvärde, anpassat (IPF) så att raderna summerar till registrets röstande
    per grupp i regionen och kolumnerna till regionens valresultat.

    2026 saknar registerdata om vilka som röstade; där används 2022 års
    sammansättning av de röstande i regionen."""
    if reg_delt_region.empty:
        return pd.DataFrame()
    v = val.dropna(subset=["parti"]).copy()
    v["lan"] = v.kommunkod.str[:2]
    roster = {}
    for ar, d in v.groupby("ar"):
        roster[(ar, "00")] = d.groupby("parti").roster.sum()
        for lan, dl in d.groupby("lan"):
            roster[(ar, lan)] = dl.groupby("parti").roster.sum()
        for k, dk in d.groupby("kommunkod"):
            roster[(ar, k)] = dk.groupby("parti").roster.sum()
    rader = []
    for ar, reg_ar in ((2018, 2018), (2022, 2022), (2026, 2022)):
        for rdim, (psu_dim, karta) in REG_TILL_PSU.items():
            seed = _psu_stod(stod, vikt, psu_dim, f"{ar}M05", karta)
            if seed is None:
                continue
            d = reg_delt_region[(reg_delt_region.ar == reg_ar) & (reg_delt_region.dimension == rdim)]
            for region, dr in d.groupby("region_kod"):
                if (ar, region) not in roster:
                    continue
                n = dr.set_index("grupp").rostande.reindex(seed.index)
                if n.isna().any() or n.sum() <= 0:
                    continue
                V = roster[(ar, region)].reindex(PARTIER).fillna(0).values.astype(float)
                if V.sum() <= 0:
                    continue
                N = n.values / n.sum() * V.sum()
                m = _ipf(seed.values * N[:, None], N, V)
                niva = "riket" if region == "00" else "län" if len(region) == 2 else "kommun"
                metod = ("IPF: PSU-stöd × registrets röstande × valresultat" if ar == reg_ar else
                         "IPF: PSU-stöd × röstande 2022 (sammansättning) × valresultat 2026")
                for i, g in enumerate(seed.index):
                    for j, p in enumerate(PARTIER):
                        rader.append({"niva": niva, "region_kod": region,
                                      "region": namn.get(region, dr.region.iloc[0]),
                                      "ar": ar, "dimension": psu_dim, "grupp": g, "parti": p,
                                      "andel_av_parti": 100 * m[i, j] / max(m[:, j].sum(), 1e-9),
                                      "stod_i_grupp": 100 * m[i, j] / N[i],
                                      "gruppandel": 100 * N[i] / N.sum(), "metod": metod})
    return pd.DataFrame(rader)


# ---------- dekomposition ----------

def _shapley(w0, w1, s0, s1):
    """Δ(Σ w·s) = Σ Δw·s̄ + Σ w̄·Δs (exakt, utan restterm)."""
    samm = ((w1 - w0) * (s0 + s1) / 2).sum()
    bet = ((w0 + w1) / 2 * (s1 - s0)).sum()
    return samm, bet


def dekomposition(stod, vikt, profil_reg, val, utb_kommun: pd.DataFrame, namn: dict) -> pd.DataFrame:
    rader = []
    valar = [1973, 1976, 1979, 1982, 1985, 1988, 1991, 1994, 1998, 2002, 2006, 2010, 2014, 2018, 2022, 2026]

    # (a) Riket ur PSU: vikter och stöd per grupp i maj valåren
    s = stod[(stod.kalla == "scb_psu") & (stod.kon == "alla") & (stod.grupp != "Samtliga")]
    w = vikt[(vikt.kalla == "scb_psu") & (vikt.kon == "alla")]
    for dim in w.dimension.unique():
        perioder = [f"{y}M05" for y in valar if f"{y}M05" in set(w[w.dimension == dim].period)]
        for a, b in zip(perioder, perioder[1:]):
            wa = w[(w.dimension == dim) & (w.period == a)].set_index("grupp").andel / 100
            wb = w[(w.dimension == dim) & (w.period == b)].set_index("grupp").andel / 100
            grp = wa.index.intersection(wb.index)
            if len(grp) < 2:
                continue
            for p in PARTIER[:-1]:
                sa = s[(s.dimension == dim) & (s.period == a) & (s.parti == p)].set_index("grupp").andel.reindex(grp)
                sb = s[(s.dimension == dim) & (s.period == b) & (s.parti == p)].set_index("grupp").andel.reindex(grp)
                if sa.isna().any() or sb.isna().any():
                    continue
                samm, bet = _shapley(wa[grp] / wa[grp].sum(), wb[grp] / wb[grp].sum(), sa, sb)
                rader.append({"niva": "riket", "region_kod": "00", "region": "Riket", "dimension": dim,
                              "fran": int(a[:4]), "till": int(b[:4]), "parti": p,
                              "forandring": samm + bet, "sammansattning": samm, "beteende": bet,
                              "kalla": "psu",
                              "metod": "PSU maj valår: kalibrerade gruppvikter och stöd per grupp"})

    # (b) Län och kommun 2018→2022: registrets röstande + skattat stöd (IPF)
    if not profil_reg.empty:
        pr = profil_reg[profil_reg.ar.isin([2018, 2022])]
        for (niva, region, dim), d in pr.groupby(["niva", "region_kod", "dimension"]):
            for p in PARTIER[:-1]:
                dp = d[d.parti == p].pivot_table(index="grupp", columns="ar",
                                                  values=["gruppandel", "stod_i_grupp"])
                if dp.isna().any().any() or dp.shape[1] < 4:
                    continue
                samm, bet = _shapley(dp[("gruppandel", 2018)] / 100, dp[("gruppandel", 2022)] / 100,
                                     dp[("stod_i_grupp", 2018)], dp[("stod_i_grupp", 2022)])
                rader.append({"niva": niva, "region_kod": region, "region": d.region.iloc[0],
                              "dimension": dim, "fran": 2018, "till": 2022, "parti": p,
                              "forandring": samm + bet, "sammansattning": samm, "beteende": bet,
                              "kalla": "register_ipf",
                              "metod": "register 2018/2022 + skattat stöd per grupp (IPF)"})

    # (c) Kommun/län 2006–2026: befolkningens utbildning (16–74) × PSU:s nationella stöd.
    # Beteende = faktisk förändring − sammansättningseffekt (restpost).
    if not utb_kommun.empty:
        vv = val.dropna(subset=["parti"]).copy()
        vv["lan"] = vv.kommunkod.str[:2]
        andel = {}
        for niva, kol in (("kommun", "kommunkod"), ("län", "lan")):
            g = vv.groupby(["ar", kol, "parti"]).roster.sum()
            andel[niva] = (100 * g / g.groupby(level=[0, 1]).transform("sum"))
        u = utb_kommun.copy()
        for (y0, y1) in zip(valar, valar[1:]):
            if y0 < 2006:
                continue
            a, b = f"{y0}M05", f"{y1}M05"
            s0 = s[(s.dimension == "utbildning") & (s.period == a)].pivot_table(index="grupp", columns="parti", values="andel")
            s1 = s[(s.dimension == "utbildning") & (s.period == b)].pivot_table(index="grupp", columns="parti", values="andel")
            if s0.empty or s1.empty:
                continue
            u0 = u[u.ar == min(y0, u.ar.max())].pivot_table(index="region_kod", columns="grupp", values="andel")
            u1 = u[u.ar == min(y1, u.ar.max())].pivot_table(index="region_kod", columns="grupp", values="andel")
            grp = [g for g in u0.columns if g in s0.index and g in s1.index]
            if len(grp) < 3:
                continue
            for region in u0.index.intersection(u1.index):
                niva = "län" if len(region) == 2 else "kommun"
                if len(region) not in (2, 4):
                    continue
                w0 = u0.loc[region, grp] / u0.loc[region, grp].sum()
                w1 = u1.loc[region, grp] / u1.loc[region, grp].sum()
                for p in PARTIER[:-1]:
                    if p not in s0.columns or p not in s1.columns:
                        continue
                    sbar = (s0.loc[grp, p] + s1.loc[grp, p]) / 2
                    if sbar.isna().any():
                        continue
                    samm = float(((w1 - w0) * sbar).sum())
                    try:
                        fakt = andel[niva].loc[(y1, region, p)] - andel[niva].loc[(y0, region, p)]
                    except KeyError:
                        continue
                    rader.append({"niva": niva, "region_kod": region,
                                  "region": namn.get(region, region), "dimension": "utbildning",
                                  "fran": y0, "till": y1, "parti": p, "forandring": float(fakt),
                                  "sammansattning": samm, "beteende": float(fakt) - samm,
                                  "kalla": "befolkning",
                                  "metod": "befolkningens utbildning (16–74) × PSU:s nationella stöd; beteende = rest"})
    return pd.DataFrame(rader)


PSU_UTB = {"förgymnasial utbildning kortare än 9 år": "förgymnasial utbildning",
           "förgymnasial utbildning, 9 (10) år": "förgymnasial utbildning",
           "gymnasial utbildning, högst 2 år": "gymnasial utbildning",
           "gymnasial utbildning, 3 år": "gymnasial utbildning",
           "eftergymnasial utbildning, mindre än 3 år": "eftergymnasial utbildning mindre än 3 år",
           "eftergymnasial utbildning, 3 år eller mer": "eftergymnasial utbildning 3 år eller mer",
           "forskarutbildning": "eftergymnasial utbildning 3 år eller mer"}


def utbildning_region(scb) -> pd.DataFrame:
    """Befolkningens utbildning 16–74 år per län/kommun och år i PSU:s fyra nivåer."""
    df = scb("TAB3981")
    if df is None:
        return pd.DataFrame()
    ucol = next(c for c in df.columns if c.startswith("Utbildn") and not c.endswith("_kod"))
    df["grupp"] = df[ucol].map(PSU_UTB)
    d = df.dropna(subset=["grupp"]).groupby(["Region_kod", "Tid", "grupp"], as_index=False).varde.sum()
    d["andel"] = 100 * d.varde / d.groupby(["Region_kod", "Tid"]).varde.transform("sum")
    return d.rename(columns={"Region_kod": "region_kod", "Tid": "ar"}).assign(ar=lambda x: x.ar.astype(int))
