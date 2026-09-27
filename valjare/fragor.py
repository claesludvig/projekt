"""Sakfrågorna och verkligheten: brottslighet, priser och vad väljarna prioriterar.

- polisen_manad: skjutningar (avlidna, skadade) och sprängningar per polisregion och månad
- kpi_manad: KPI per produktgrupp (el, drivmedel, livsmedel m.fl.), 12-månadersförändring
- fraga_betydelse / fraga_rang_parti / bast_politik: Valu 1998–2026
- som_samhallsproblem: SOM-institutets viktigaste samhällsproblem 1987–
- test_bilar: kommunernas bilinnehav mot partiernas förändring, val för val
- test_skjutningar: skjutningar per invånare i polisregionen mot partiernas förändring
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

import tolka

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]

# Polisregioner → län (Polismyndighetens indelning sedan 2015)
POLISREGION_LAN = {
    "Nord": ["22", "23", "24", "25"], "Mitt": ["03", "19", "21"], "Stockholm": ["01", "09"],
    "Öst": ["04", "05", "06"], "Väst": ["13", "14"], "Syd": ["07", "08", "10", "12"],
    "Bergslagen": ["17", "18", "20"],
}
VALU_ORDNING = ["valu_rd_2026_seminarium", "valu_rd_2014_2022", "valu_rd_2014_2018"]
KPI_GRUPPER = [  # (namn på sidan, SCB:s produktgrupp i TAB5160)
    ("El", r"^elström, egnahem$"),
    ("El, lägenhet", r"^elström, hyres"),
    ("Bensin", r"^bensin 95"),
    ("Diesel", r"^dieselolja$"),
    ("Räntekostnader", r"^räntekostnader, egnahem$"),
]


def polisen_manad(kall_dir: Path) -> pd.DataFrame:
    delar = [tolka.polisen(f, f.stem) for f in sorted((kall_dir / "txt").glob("polisen__*.txt"))]
    delar = [d for d in delar if not d.empty]
    if not delar:
        return pd.DataFrame()
    d = pd.concat(delar, ignore_index=True)
    d["arsfil"] = ~d.kalla.str.contains("tolv")
    return d.sort_values("arsfil", ascending=False) \
        .drop_duplicates(["typ", "matt", "polisregion", "ar", "manad"]).drop(columns="arsfil") \
        .sort_values(["typ", "matt", "polisregion", "ar", "manad"]).reset_index(drop=True)


def kpi_manad(scb) -> pd.DataFrame:
    df = scb("TAB5160")
    if df is None:
        return pd.DataFrame()
    df = df[df.ContentsCode == "Konsumentprisindex (KPI)"]
    gcol = next((c for c in df.columns if not c.endswith("_kod")
                 and c not in ("tabell", "ContentsCode", "Tid", "varde")), None)
    if gcol is None:
        return pd.DataFrame()
    rader = []
    grupper = list(dict.fromkeys(df[gcol]))
    for namn, monster in KPI_GRUPPER:
        g = next((x for x in grupper if re.search(monster, re.sub(r"^[\d.]+\s*", "", x))
                  or re.search(monster, x)), None)
        if g is None:
            continue
        s = df[df[gcol] == g].copy()
        s["t"] = pd.PeriodIndex(s.Tid.str.replace("M", "-"), freq="M")
        s = s.sort_values("t").set_index("t").varde
        yoy = 100 * (s / s.shift(12) - 1)
        for t, v in s.items():
            rader.append({"serie": namn, "produktgrupp": g, "ar": t.year, "manad": t.month,
                          "index_1980": v, "forandring_12m": yoy.get(t)})
    return pd.DataFrame(rader)


def valu_fragor(kall_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    b, r, s = [], [], []
    for prio, doc in enumerate(VALU_ORDNING):
        f = kall_dir / "txt" / f"{doc}.txt"
        if not f.exists():
            continue
        bb, rr, ss = tolka.valu_fragor(f, doc)
        valar = int(re.findall(r"20\d\d", doc)[-1])
        b.append(bb.assign(prio=prio))
        r.append(rr.assign(valar=valar))
        s.append(ss.assign(ar=valar))
    bet = pd.concat(b, ignore_index=True).sort_values("prio") \
        .drop_duplicates(["ar", "fraga"]).drop(columns="prio") if b else pd.DataFrame()
    return bet, pd.concat(r, ignore_index=True) if r else pd.DataFrame(), \
        pd.concat(s, ignore_index=True) if s else pd.DataFrame()


def som(kall_dir: Path) -> pd.DataFrame:
    for doc in ("som_trender_1986_2025", "som_trender_1986_2022"):
        f = kall_dir / "txt" / f"{doc}.txt"
        if f.exists():
            d = tolka.som_samhallsproblem(f, doc)
            if not d.empty:
                return d
    return pd.DataFrame()


def _andelar(val: pd.DataFrame, niva: str) -> pd.DataFrame:
    v = val.dropna(subset=["parti"]).copy()
    v["nyckel"] = v.kommunkod if niva == "kommun" else v.kommunkod.str[:2]
    g = v.groupby(["ar", "nyckel", "parti"]).roster.sum()
    return (100 * g / g.groupby(level=[0, 1]).transform("sum")).rename("andel").reset_index()


def test_bilar(scb, val: pd.DataFrame) -> pd.DataFrame:
    """Bilar i trafik per 1 000 invånare (året före valet) mot förändringen i
    partiets andel sedan förra valet, över kommunerna."""
    bil = pd.concat([d for d in (scb("TAB6091"), scb("TAB6589")) if d is not None])
    bef = scb("TAB6571")
    if bil is None or bef is None or bil.empty:
        return pd.DataFrame()
    bil = bil[bil.Bestand == "i trafik"].assign(ar=lambda x: x.Tid.astype(int))
    bef = bef[(bef.Kon == "totalt") & (bef.UtlBakgrund == "totalt")].assign(ar=lambda x: x.Tid.astype(int))
    per = bil.merge(bef[["Region_kod", "ar", "varde"]], on=["Region_kod", "ar"], suffixes=("_bil", "_bef"))
    per = per[per.Region_kod.str.len() == 4]
    per["bilar_per_1000"] = 1000 * per.varde_bil / per.varde_bef
    a = _andelar(val, "kommun")
    rader = []
    valar = sorted(a.ar.unique())
    for y0, y1 in zip(valar, valar[1:]):
        if y1 < 2018:
            continue
        ar_bil = max([x for x in per.ar.unique() if x <= y1 - 1], default=None)
        if ar_bil is None:
            continue
        x = per[per.ar == ar_bil].set_index("Region_kod").bilar_per_1000
        for p in PARTIER:
            d0 = a[(a.ar == y0) & (a.parti == p)].set_index("nyckel").andel
            d1 = a[(a.ar == y1) & (a.parti == p)].set_index("nyckel").andel
            j = pd.concat([x, d1 - d0], axis=1, keys=["x", "y"]).dropna()
            if len(j) < 50:
                continue
            rader.append({"fran": int(y0), "till": int(y1), "parti": p, "bilar_ar": int(ar_bil),
                          "r": float(np.corrcoef(j.x, j.y)[0, 1]),
                          "lutning_per_100_bilar": float(np.polyfit(j.x, j.y, 1)[0] * 100),
                          "n_kommuner": len(j)})
    return pd.DataFrame(rader)


def test_skjutningar(pol: pd.DataFrame, val: pd.DataFrame, scb) -> pd.DataFrame:
    """Skjutningar per 100 000 invånare i polisregionen under mandatperioden mot
    förändringen i partiets andel. Bara sju regioner – en indikation, inget test."""
    bef = scb("TAB6571")
    if pol.empty or bef is None:
        return pd.DataFrame()
    bef = bef[(bef.Kon == "totalt") & (bef.UtlBakgrund == "totalt") & (bef.Region_kod.str.len() == 2)]
    lan_reg = {l: r for r, ls in POLISREGION_LAN.items() for l in ls}
    bef = bef.assign(pr=bef.Region_kod.map(lan_reg), ar=bef.Tid.astype(int)).dropna(subset=["pr"])
    a = _andelar(val, "län")
    v = val.dropna(subset=["parti"]).assign(pr=lambda x: x.kommunkod.str[:2].map(lan_reg))
    g = v.groupby(["ar", "pr", "parti"]).roster.sum()
    andel = (100 * g / g.groupby(level=[0, 1]).transform("sum")).rename("andel").reset_index()
    sk = pol[(pol.typ == "skjutningar") & (pol.matt == "skjutningar") & (pol.polisregion != "Totalt")]
    rader = []
    for y0, y1 in ((2018, 2022), (2022, 2026)):
        # Mandatperioden: oktober valåret till och med augusti nästa valår
        ym = sk.ar * 100 + sk.manad
        n = sk[(ym >= y0 * 100 + 10) & (ym <= y1 * 100 + 8)]
        manader = n.groupby("polisregion").size().max() if len(n) else 0
        if manader < 36:
            continue
        antal = n.groupby("polisregion").antal.sum()
        b = bef[bef.ar == min(y1 - 1, bef.ar.max())].groupby("pr").varde.sum()
        per100k = 1e5 * antal / b / (n.drop_duplicates(["ar", "manad"]).shape[0] / 12)
        for p in PARTIER:
            d0 = andel[(andel.ar == y0) & (andel.parti == p)].set_index("pr").andel
            d1 = andel[(andel.ar == y1) & (andel.parti == p)].set_index("pr").andel
            j = pd.concat([per100k, d1 - d0], axis=1, keys=["x", "y"]).dropna()
            for reg, rad in j.iterrows():
                rader.append({"fran": y0, "till": y1, "parti": p, "polisregion": reg,
                              "skjutningar_per_100k_ar": float(rad.x), "forandring": float(rad.y),
                              "r_over_regioner": float(np.corrcoef(j.x, j.y)[0, 1]) if len(j) > 2 else None})
    return pd.DataFrame(rader)
