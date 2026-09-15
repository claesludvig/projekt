#!/usr/bin/env python3
"""Hämtar styrräntan från Riksbankens SWEA-API.

SCB publicerar inte styrräntan — den är Riksbankens, och finns inte någonstans
i statistikdatabasen. Eftersom räntespreaden mot styrräntan är hela poängen med
prisbenet hämtas den separat härifrån i stället för att approximeras."""

from __future__ import annotations

import pandas as pd
import requests

SWEA_BASE = "https://api.riksbank.se/swea/v1"
POLICYRANTA = "SECBREPOEFF"
TIMEOUT = 30


def hamta_policyranta(sedan_ar: int = 2015, serie: str = POLICYRANTA) -> pd.Series:
    """Månadsserie med styrräntan, tagen som månadens sista noterade värde.

    SWEA levererar dagliga observationer och noterar bara dagar då räntan
    ändrats eller publicerats, så serien är gles. Därför tas sista värdet per
    månad och luckorna fylls framåt — en oförändrad styrränta noteras inte om,
    men den gäller fortfarande."""
    url = f"{SWEA_BASE}/Observations/{serie}/{sedan_ar}-01-01"
    resp = requests.get(url, timeout=TIMEOUT,
                        headers={"User-Agent": "byggkredit-scb/1.0",
                                 "Accept": "application/json"})
    resp.raise_for_status()
    poster = resp.json()
    if not isinstance(poster, list) or not poster:
        raise RuntimeError(f"SWEA gav inget data för {serie}")

    rader = [(pd.Period(pd.Timestamp(p["date"]), freq="M"), float(p["value"]))
             for p in poster if p.get("value") is not None]
    if not rader:
        raise RuntimeError(f"SWEA gav bara tomma värden för {serie}")

    frame = pd.DataFrame(rader, columns=["tid", "varde"])
    manadsvis = frame.groupby("tid")["varde"].last().sort_index()
    manadsvis.index = pd.PeriodIndex(manadsvis.index, freq="M")
    full = pd.period_range(manadsvis.index.min(), manadsvis.index.max(), freq="M")
    return manadsvis.reindex(full).ffill()


def som_tidig_tabell(sedan_ar: int = 2015) -> pd.DataFrame:
    """Samma långa format som PxWeb-serierna, så att allt kan ligga i en fil."""
    serie = hamta_policyranta(sedan_ar)
    return pd.DataFrame({
        "serie": "styrranta",
        "roll": "pris",
        "tid": serie.index,
        "kategori": "Totalt",
        "innehall": "Policyränta",
        "varde": serie.to_numpy(),
    })
