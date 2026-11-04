#!/usr/bin/env python3
"""Hämtar SCB-serier för bolån (räntebindning), bostadspriser, bygglov,
påbörjanden och hushållens konsumtion, samt styrräntan från Riksbanken.
Sparar en CSV per serie i data/ (bred, en kolumn per kategori)."""
from pathlib import Path

import pandas as pd
import requests

from scb import hamta, tid_till_datum

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)


def bred(df, kol, namn=None):
    df = df.copy()
    df["datum"] = tid_till_datum(df["Tid"])
    ut = df.pivot_table(index="datum", columns=kol, values="varde", aggfunc="first")
    if namn:
        ut = ut.rename(columns=namn)
    return ut


def main():
    # 1. Hushållens lån hos MFI efter ursprunglig resp. återstående räntebindning (mnkr, stock)
    df = hamta("TAB1538", {"Referenssektor": "1.1", "Motpartssektor": "10",
                           "RantebindningFM5001": "*", "ContentsCode": "*", "Tid": "*"})
    df["serie"] = df["ContentsCode"].map({"000008JC": "urspr", "000008JA": "aterst"}) + "_" + df["RantebindningFM5001"]
    bred(df, "serie").to_csv(DATA / "hushall_lan_rantebindning.csv")

    # 2. Bolån (bostadsändamål) hos MFI efter ursprunglig räntebindning (mnkr, stock)
    df = hamta("TAB2811", {"Referenssektor": "1.1", "Motpartssektor": "2c",
                           "Rantebindningstid": "*", "ContentsCode": "*", "Tid": "*"})
    bred(df, "Rantebindningstid").to_csv(DATA / "bolan_rantebindning.csv")

    # 3. Bolåneräntor (MFI+BKI+AIF), nya avtal och utestående, efter bindningstid (%)
    df = hamta("TAB5783", {"Referenssektor": "1", "Motpartssektor": "2c", "Avtal": "*",
                           "Rantebindningstid": "1,1.1.1,1.1.2.1,1.1.2.2.1,1.1.2.2.2,1.1.2.3",
                           "ContentsCode": "*", "Tid": "*"})
    df["serie"] = df["Avtal"].map({"0200": "utest", "0100": "nya"}) + "_" + df["Rantebindningstid"]
    bred(df, "serie").to_csv(DATA / "bolanerantor.csv")

    # 4. Fastighetsprisindex småhus, kvartal
    df = hamta("TAB1150", {"Region": "00,0010,0020,0030", "ContentsCode": "*", "Tid": "*"})
    bred(df, "Region", {"00": "riket", "0010": "sthlm", "0020": "gbg", "0030": "malmo"}).to_csv(DATA / "fastpi_smahus.csv")

    # 5. Bygglov nybyggnad, lägenheter, riket, kvartal
    df = hamta("TAB2534", {"Region": "00", "Hustyp": "1113,21,2224", "ContentsCode": "*", "Tid": "*"})
    bred(df, "Hustyp", {"1113": "smahus", "21": "flerbo", "2224": "special"}).to_csv(DATA / "bygglov.csv")

    # 6. Påbörjade och färdigställda lägenheter, riket, kvartal
    df = hamta("TAB4572", {"Region": "00", "Hustyp": "*", "ContentsCode": "*", "Tid": "*"})
    df["serie"] = df["ContentsCode"].map({"BO0101A4": "pab", "BO0101A3": "fardig"}) + "_" + df["Hustyp"].str.lower()
    bred(df, "serie").to_csv(DATA / "paborjade.csv")

    # 7. Hushållens konsumtionsindikator per COICOP: månad och vecka, säsongrensad fasta priser
    df = hamta("TAB6932", {"AndamalCOICOP": "*", "ContentsCode": "000008R7", "Tid": "*"})
    bred(df, "AndamalCOICOP").to_csv(DATA / "konsumtion_manad_coicop.csv")
    df = hamta("TAB6930", {"AndamalCOICOP": "*", "ContentsCode": "000008QZ", "Tid": "*"})
    df["datum"] = pd.to_datetime(df["Tid"].str.replace("V", "-W") + "-0", format="%G-W%V-%w")
    df.pivot(index="datum", columns="AndamalCOICOP", values="varde").to_csv(DATA / "konsumtion_vecka_coicop.csv")

    # 8. Nationalräkenskaper: hushållens konsumtion per ändamål, säsongrensad fasta priser, kvartal
    df = hamta("TAB6331", {"Andamal": "*", "ContentsCode": "0000079L", "Tid": "*"})
    bred(df, "Andamal").to_csv(DATA / "konsumtion_nr_kvartal.csv")

    # 9. Styrräntan (Riksbanken SWEA), månadsmedel
    r = requests.get("https://api.riksbank.se/swea/v1/Observations/SECBREPOEFF/2005-01-01", timeout=60)
    r.raise_for_status()
    s = pd.DataFrame(r.json()).assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["value"]
    s.resample("ME").mean().rename("styrranta").to_csv(DATA / "styrranta.csv")
    print("Klart:", sorted(p.name for p in DATA.glob("*.csv")))


if __name__ == "__main__":
    main()
