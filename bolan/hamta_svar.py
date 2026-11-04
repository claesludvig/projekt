#!/usr/bin/env python3
"""Hämtar extra data för SVAR-skattningen à la Riksbanken (EK 9/2022):
BNP och konsumtion (SCB NR, säsongrensat fasta priser), hushållens skulder (finansräkenskaper),
styrränta och KIX (Riksbanken SWEA), samt omvärld = euroområdet (Eurostat) som proxy för KIX-vägt."""
from pathlib import Path

import pandas as pd
import requests

from scb import hamta, tid_till_datum

DATA = Path(__file__).resolve().parent / "data"


def swea(serie, fran="1993-01-01"):
    r = requests.get(f"https://api.riksbank.se/swea/v1/Observations/{serie}/{fran}", timeout=60)
    r.raise_for_status()
    s = pd.DataFrame(r.json())
    return s.assign(date=pd.to_datetime(s["date"])).set_index("date")["value"].resample("QE").mean()


def eurostat(ds, **filt):
    url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}"
    r = requests.get(url, params={**filt, "format": "JSON", "lang": "en"}, timeout=60)
    r.raise_for_status()
    js = r.json()
    tid = js["dimension"]["time"]["category"]["index"]
    inv = {v: k for k, v in tid.items()}
    s = pd.Series({inv[int(k)]: v for k, v in js["value"].items()})
    s.index = pd.PeriodIndex([i.replace("-Q", "Q") if "Q" in i else i for i in s.index],
                             freq="Q" if "Q" in s.index[0] else "M").to_timestamp(how="end").normalize()
    return s.sort_index()


def main():
    df = hamta("TAB4553", {"Anvandningstyp": "BNPM,KHUS", "ContentsCode": "NR0103CE", "Tid": "*"})
    df["datum"] = tid_till_datum(df["Tid"])
    nr = df.pivot(index="datum", columns="Anvandningstyp", values="varde").rename(columns={"BNPM": "bnp", "KHUS": "kons"})

    df = hamta("TAB1203", {"Sektor": "S14", "Kontopost": "FL4000", "Motsektor": "S0",
                           "ContentsCode": "FM0103AS", "Tid": "*"})
    df["datum"] = tid_till_datum(df["Tid"])
    skuld = df.set_index("datum")["varde"].rename("hush_skuld")

    ut = pd.concat([nr, skuld, swea("SECBREPOEFF", "1994-06-01").rename("styr"),
                    swea("SEKKIX92").rename("kix"),
                    eurostat("namq_10_gdp", geo="EA20", unit="CLV10_MEUR", s_adj="SCA", na_item="B1GQ").rename("ea_bnp"),
                    eurostat("prc_hicp_midx", geo="EA", unit="I15", coicop="CP00").resample("QE").mean().rename("ea_hicp"),
                    eurostat("irt_st_q", geo="EA", int_rt="IRT_M3").rename("ea_ranta")], axis=1).sort_index()
    ut.to_csv(DATA / "svar_data.csv")
    print(ut.loc["1995":].dropna(how="all").head(3)); print(ut.tail(3)); print(ut.notna().sum())


if __name__ == "__main__":
    main()
