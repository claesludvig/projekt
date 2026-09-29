"""Partiernas program: kontroll av citat och jämförelse mellan partierna (underlag: partier_katalog)."""

import re
from itertools import combinations
from pathlib import Path

import pandas as pd

from partier_katalog import PROGRAM, PROGRAM_NAMN, STANDPUNKTER

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]


def normalisera(t: str) -> str:
    """Samma jämförelseform för citat och källtext: utan mjuka bindestreck, nollbredds- och punkttecken,
    avstavning vid radbrytning och med ett mellanslag mellan orden."""
    t = t.replace("­", "").replace("​", "").replace(" ", " ")
    t = re.sub(r"===== sida \d+ =====", " ", t)
    t = re.sub(r"[●•à]\s", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def texter(kall_dir: Path) -> dict[str, dict[str, str]]:
    """Parti -> {dokument-id: normaliserad text} för de program som finns hämtade."""
    ut = {}
    for p, dok in PROGRAM.items():
        ut[p] = {d: normalisera(f.read_text(encoding="utf-8")) for d in dok
                 if (f := kall_dir / "txt" / f"{d}.txt").exists()}
    return ut


def tabell(kall_dir: Path, dokument: list[dict] | None = None) -> pd.DataFrame:
    """En rad per område, fråga och parti med svar, citat och det dokument citatet finns i (None om det inte hittas)."""
    tx = texter(kall_dir)
    url = {d["id"]: d["url"] for d in (dokument or [])}
    rader = []
    for omr, omr_namn, fragor in STANDPUNKTER:
        for fid, forslag, svar in fragor:
            for p in PARTIER:
                s, citat = svar.get(p, (None, None))
                kalla = next((d for d, t in tx.get(p, {}).items() if citat and normalisera(citat) in t), None)
                rader.append({"omrade": omr, "omrade_namn": omr_namn, "fraga": fid, "forslag": forslag, "parti": p,
                              "svar": s, "citat": citat, "dokument": kalla, "url": url.get(kalla),
                              "program_hamtat": bool(tx.get(p))})
    return pd.DataFrame(rader)


def likhet(t: pd.DataFrame) -> pd.DataFrame:
    """Parvis: andel av frågorna där båda partierna tar ställning och svarar lika (delvis räknas som eget svar)."""
    rader = []
    for a, b in combinations(PARTIER, 2):
        x = t[t.parti == a].set_index(["fraga"]).svar
        y = t[t.parti == b].set_index(["fraga"]).svar
        bada = x.notna() & y.notna()
        n = int(bada.sum())
        rader.append({"parti_a": a, "parti_b": b, "fragor": n,
                      "lika": int((x[bada] == y[bada]).sum()), "andel_lika": 100 * (x[bada] == y[bada]).mean() if n else None})
    return pd.DataFrame(rader)
