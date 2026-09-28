"""Nordisk jämförelse (Eurostat): en rad per serie, land och period.

Tabell norden: id, namn, enhet, geo, land, period, ar_dec, varde.
"""

import re
from pathlib import Path

import pandas as pd

from omraden import BERAKNADE, EUROSTAT, LANDER


def _ar_dec(t: str) -> float | None:
    t = str(t)
    if m := re.fullmatch(r"(\d{4})", t):
        return int(m[1]) + 0.5
    if m := re.fullmatch(r"(\d{4})-S([12])", t):
        return int(m[1]) + (0.25 if m[2] == "1" else 0.75)
    if m := re.fullmatch(r"(\d{4})-?Q(\d)", t):
        return int(m[1]) + (int(m[2]) - 0.5) / 4
    if m := re.fullmatch(r"(\d{4})-?M?(\d{2})", t):
        return int(m[1]) + (int(m[2]) - 0.5) / 12
    return None


def bygg(data_dir: Path) -> pd.DataFrame:
    mapp = data_dir / "eurostat"
    serier = {}
    info = {sid: (namn, enhet) for sid, _, _, namn, enhet in EUROSTAT}
    for sid in info:
        f = mapp / f"{sid}.csv"
        if not f.exists():
            continue
        try:
            d = pd.read_csv(f, dtype={"geo": str, "tid": str})
        except pd.errors.EmptyDataError:
            continue
        if len(d):
            serier[sid] = d.groupby(["geo", "tid"]).varde.mean()
    for sid, namn, enhet, fn in BERAKNADE:
        try:
            s = fn(serier).dropna()
        except KeyError:
            continue
        if len(s):
            serier[sid] = s
            info[sid] = (namn, enhet)
    rader = []
    for sid, s in serier.items():
        for (geo, tid), v in s.items():
            if geo in LANDER and _ar_dec(tid) is not None:
                rader.append({"id": sid, "namn": info[sid][0], "enhet": info[sid][1], "geo": geo,
                              "land": LANDER[geo], "period": tid, "ar_dec": _ar_dec(tid), "varde": float(v)})
    return pd.DataFrame(rader)


def till_verklighet(n: pd.DataFrame) -> pd.DataFrame:
    """Sveriges värden för serier som saknas i den nationella statistiken (försvar enligt COFOG)."""
    if n.empty:
        return n
    d = n[(n.geo == "SE") & (n.id == "forsvar_bnp")]
    return pd.DataFrame({"fraga": "forsvar", "indikator": "Offentliga utgifter för försvar, % av BNP (COFOG)",
                         "kalla": "Eurostat gov_10a_exp", "niva": "riket", "region_kod": "0000",
                         "period": d.period, "ar_dec": d.ar_dec, "varde": d.varde})
