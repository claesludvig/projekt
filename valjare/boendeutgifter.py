"""Boendeutgifternas andel av inkomsten per inkomstgrupp, ålder, hushållstyp och upplåtelseform.

Hämtar SCB:s boendeutgiftstabeller (HEK 2004–2013, Boendeutgifter 2015–2024) och Eurostats
EU-SILC-tabeller om boendekostnader för Sverige och skriver dem i långt format till
data/boendeutgifter/. Sammanställningen står i boendeutgifter.md.

    python boendeutgifter.py
"""

import csv
import itertools
import time
from pathlib import Path

import requests

SCB = "https://statistikdatabasen.scb.se/api/v2/tables/"
SCB_TABELLER = {
    "TAB4557": "Boendeutgiftsprocent efter upplåtelseform och ålder 2015–2024",
    "TAB4377": "Boendeutgiftsprocent efter upplåtelseform och hushållstyp 2015–2024",
    "TAB1178": "Boendeutgiftsprocent efter region och upplåtelseform 2020–2024",
    "TAB1179": "Boendeutgiftsprocent efter upplåtelseform och lägenhetstyp 2020–2024",
    "TAB1182": "Boendeutgift efter inkomstkvartil och upplåtelseform 2020–2024",
    "TAB4551": "Boendeutgift efter upplåtelseform och ålder 2015–2024",
    "TAB830": "Boendeutgiftsprocent efter region, upplåtelseform och hushållstyp 2004–2013 (HEK)",
}
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EUROSTAT_TABELLER = {
    "ilc_mded01": "Boendekostnadernas andel av disponibel inkomst (medel), hushållstyp och fattigdomsstatus",
    "ilc_lvho08a": "Median av boendekostnadsandelen, ålder, kön och fattigdomsstatus",
    "ilc_lvho08b": "Median av boendekostnadsandelen, urbaniseringsgrad",
    "ilc_lvho07a": "Hög boendekostnadsbelastning (>40 %), ålder, kön och fattigdomsstatus",
    "ilc_lvho07b": "Hög boendekostnadsbelastning (>40 %), inkomstkvintil",
    "ilc_lvho07c": "Hög boendekostnadsbelastning (>40 %), upplåtelseform",
    "ilc_lvho07d": "Hög boendekostnadsbelastning (>40 %), urbaniseringsgrad",
    "ilc_lvho07e": "Hög boendekostnadsbelastning (>40 %), hushållstyp",
    "ilc_lvho26": "Hög boendekostnadsbelastning (>40 %), ålder, kön och födelseland",
    "ilc_lvho28": "Fördelning efter boendekostnadsandel och upplåtelseform",
    "ilc_mded04": "Upplevd ekonomisk börda av boendekostnaden",
}
UT = Path(__file__).parent / "data" / "boendeutgifter"


def platta(d: dict, hoppa: set[str]):
    """Rader (dimensioner, tid, värde, flagga) ur ett json-stat2-svar."""
    ids, size = d["id"], d["size"]
    kat = [sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1]) for k in ids]
    lab = [d["dimension"][k]["category"].get("label", {}) for k in ids]
    varden, status = d["value"], d.get("status") or {}
    for kombination in itertools.product(*kat):
        idx = 0
        for (_, i), s in zip(kombination, size):
            idx = idx * s + i
        v = varden[idx] if isinstance(varden, list) else varden.get(str(idx))
        if v is None:
            continue
        val = {k: (lab[n].get(c, c) if k not in hoppa else c) for n, (k, (c, _)) in enumerate(zip(ids, kombination))}
        flagga = status[idx] if isinstance(status, list) else status.get(str(idx), "")
        yield val, v, flagga or ""


def scb() -> None:
    with (UT / "scb_boendeutgifter.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tabell", "dimensioner", "matt", "ar", "varde"])
        for tab in SCB_TABELLER:
            meta = requests.get(f"{SCB}{tab}/metadata", params={"lang": "sv"}, timeout=60).json()
            urval = {f"valuecodes[{k}]": "*" for k in meta["id"]}
            d = requests.get(f"{SCB}{tab}/data", params={"lang": "sv", "outputFormat": "json-stat2", **urval},
                             timeout=120).json()
            for val, v, _ in platta(d, set()):
                dims = ";".join(f"{k}={val[k]}" for k in d["id"] if k not in ("ContentsCode", "Tid"))
                w.writerow([tab, dims, val["ContentsCode"], val["Tid"], v])
            time.sleep(1)  # SCB tillåter ett fåtal anrop per sekund


def eurostat() -> None:
    with (UT / "eurostat_boendekostnader.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dataset", "dimensioner", "ar", "varde", "flagga"])
        for ds in EUROSTAT_TABELLER:
            d = requests.get(EUROSTAT + ds, params={"geo": "SE", "lang": "en"}, timeout=120).json()
            for val, v, flagga in platta(d, set(d["id"])):
                dims = ";".join(f"{k}={val[k]}" for k in d["id"] if k not in ("freq", "geo", "time", "unit"))
                w.writerow([ds, dims, val["time"], v, flagga])


if __name__ == "__main__":
    UT.mkdir(parents=True, exist_ok=True)
    scb()
    eurostat()
