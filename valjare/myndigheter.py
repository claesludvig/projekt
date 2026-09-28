"""Tolkar för myndigheternas Excelfiler (data/kallor/xlsx, hämtade via kallor.py).

Migrationsverket publicerar beviljade uppehållstillstånd som en fil per år med en
flik per indelning. Fliken "Månad, första" har uppehållsgrund (Anknytning,
Arbetsmarknad, EU/EES, Skydd, Studier, Verkställighetshinder) och en detaljgrund
per rad och en kolumn per månad. ".." betyder att värdet är skyddat (röjandekontroll);
gruppernas totalrader är ändå fullständiga, så bara de används.

Övriga filer i data/kallor (Försäkringskassans veckostatistik för sjukpenning slutade
2022, Arbetsförmedlingens yrkesbarometer är prognoser per yrke) tolkas inte.
"""

import re
from pathlib import Path

import pandas as pd

GRUNDER = ["Anknytning", "Arbetsmarknad", "EU/EES", "Skydd", "Studier", "Verkställighetshinder", "Totalt"]


def _manadsflik(fil: Path, flik: str = "Månad, första") -> pd.DataFrame:
    """En fil -> (period, grund, antal) från gruppernas totalrader."""
    try:
        r = pd.read_excel(fil, sheet_name=flik, header=None, dtype=str)
    except (ValueError, KeyError, OSError):
        return pd.DataFrame()
    rubrik = next((i for i, rad in r.iterrows()
                   if any(re.fullmatch(r"\d{4}-\d{2}", str(x).strip()) for x in rad)), None)
    if rubrik is None:
        return pd.DataFrame()
    manader = {j: str(x).strip() for j, x in r.iloc[rubrik].items() if re.fullmatch(r"\d{4}-\d{2}", str(x).strip())}
    rader, grund = [], None
    for _, rad in r.iloc[rubrik + 1:].iterrows():
        g, d = str(rad.iloc[0]).strip(), str(rad.iloc[1]).strip()
        if g not in ("nan", ""):
            grund = g
        if d != "Totalt" or grund not in GRUNDER:
            continue
        for j, m in manader.items():
            v = pd.to_numeric(str(rad.iloc[j]).replace(" ", "").replace("\xa0", ""), errors="coerce")
            if pd.notna(v):
                rader.append({"period": m, "grund": grund, "antal": int(v)})
    return pd.DataFrame(rader)


def beviljade_uppehallstillstand(kall_dir: Path) -> pd.DataFrame:
    """Beviljade förstagångstillstånd per månad och uppehållsgrund, alla årsfiler och översikten.
    Kolumner: period (ÅÅÅÅ-MM), grund, antal. Månader utan värde (framtida) saknas."""
    filer = sorted((kall_dir / "xlsx").glob("migrationsverket__Beviljade_uppeh*.xlsx"))
    delar = [_manadsflik(f) for f in filer]
    delar = [d for d in delar if len(d)]
    if not delar:
        return pd.DataFrame(columns=["period", "grund", "antal"])
    # Översikten (innevarande år) är nyast; vid dubbletter gäller den senast lästa filen
    d = pd.concat(delar, ignore_index=True).drop_duplicates(["period", "grund"], keep="last")
    return d.sort_values(["grund", "period"]).reset_index(drop=True)
