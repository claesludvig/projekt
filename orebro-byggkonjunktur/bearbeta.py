#!/usr/bin/env python3
"""
Läser SCB-uttagen i data/scb/ och skriver data/kalibrering.json.

parametrar.py läser den filen och ersätter sina antaganden med faktiska
värden där sådana finns. Kör efter hamta_scb.py.
"""

import csv
import json
import os

HAR = os.path.dirname(os.path.abspath(__file__))
SCB = os.path.join(HAR, "data", "scb")
UT = os.path.join(HAR, "data", "kalibrering.json")

RIKET = "00 Riket"
LANET = "18 Örebro län"
BYGG_BAS = "F byggindustri"
TOTALT_BAS = "A-U+US Total"


def las(namn):
    with open(os.path.join(SCB, namn), encoding="utf-8") as f:
        return list(csv.reader(f))


def arskolumner(rubriker, prefix):
    """(kolumnindex, årtal) för de rubriker som börjar med prefix."""
    return [(i, h.split()[-1]) for i, h in enumerate(rubriker) if h.startswith(prefix)]


def tal(s):
    s = (s or "").strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# BAS: sysselsatta per region och bransch
# ---------------------------------------------------------------------------

def bas_serier():
    r = las("bas_ar_preliminar.csv")
    kol = [(i, h.split()[-1]) for i, h in enumerate(r[0]) if "arbetsställets" in h]

    def plocka(region, bransch):
        for x in r[1:]:
            if (x[0] == region and x[2] == bransch
                    and x[1] == "totalt" and x[3] == "totalt"):
                return {a: tal(x[i]) for i, a in kol}
        return {}

    kommuner = {}
    for x in r[1:]:
        kod = x[0].split()[0]
        if (x[2] == BYGG_BAS and x[1] == "totalt" and x[3] == "totalt"
                and kod.startswith("18") and len(kod) == 4):
            kommuner[x[0]] = {a: tal(x[i]) for i, a in kol}

    return {
        "ar": [a for _, a in kol],
        "bygg_riket": plocka(RIKET, BYGG_BAS),
        "bygg_lanet": plocka(LANET, BYGG_BAS),
        "totalt_riket": plocka(RIKET, TOTALT_BAS),
        "totalt_lanet": plocka(LANET, TOTALT_BAS),
        "bygg_kommuner": kommuner,
    }


def rams_serie():
    """RAMS 2008-2021, för den längre bakgrunden. Män + kvinnor."""
    ut = {}
    for fil in ("rams_bygg_kommun_2008_2018.csv", "rams_bygg_kommun_2019_2021.csv"):
        r = las(fil)
        kol = arskolumner(r[0], "Antal")
        for x in r[1:]:
            if x[0] == LANET and x[1].startswith("F bygg"):
                for i, a in kol:
                    ut[a] = ut.get(a, 0) + (tal(x[i]) or 0)
    return ut


# ---------------------------------------------------------------------------
# Lön
# ---------------------------------------------------------------------------

def lonesummor(bygg_riket):
    """Lönesumma per sysselsatt i bygg (riket) och länets relativa lönenivå."""
    r = las("lonesumma_bransch_riket.csv")
    kol = arskolumner(r[0], "Lönesumma")
    bygg = {}
    for x in r[1:]:
        if x[0].startswith("F bygg"):
            bygg = {a: tal(x[i]) for i, a in kol}
    per_syss = {a: (bygg[a] * 1e9 / bygg_riket[a])
                for a in bygg if bygg.get(a) and bygg_riket.get(a)}

    # Länets lönenivå relativt riket: lönesumma per sysselsatt, alla branscher
    rl = las("lonesumma_lan.csv")
    koll = arskolumner(rl[0], "Lönesumma")
    lan = nat = {}
    for x in rl[1:]:
        if x[0] == LANET:
            lan = {a: tal(x[i]) for i, a in koll}
        if x[0] == RIKET:
            nat = {a: tal(x[i]) for i, a in koll}
    return per_syss, lan, nat


# ---------------------------------------------------------------------------
# Skatt
# ---------------------------------------------------------------------------

def skattedata():
    r = las("skatteunderlag_kommun.csv")
    kol = arskolumner(r[0], "Skatteunderlag")
    underlag = {x[0]: {a: tal(x[i]) for i, a in kol} for x in r[1:]}

    r = las("kommunalskatt.csv")
    kol = arskolumner(r[0], "Skattesats, total kommunal")
    satser = {x[0]: {a: tal(x[i]) for i, a in kol} for x in r[1:]}

    r = las("utjamning.csv")
    kol = arskolumner(r[0], "Inkomstutjämning")
    utj = {x[0]: {a: tal(x[i]) for i, a in kol} for x in r[1:]}
    return underlag, satser, utj


def senaste(d):
    ar = sorted(a for a in d if d[a] is not None)
    return (ar[-1], d[ar[-1]]) if ar else (None, None)


def main():
    bas = bas_serier()
    rams = rams_serie()
    per_syss, lonlan, lonriket = lonesummor(bas["bygg_riket"])
    underlag, satser, utj = skattedata()

    bl, br = bas["bygg_lanet"], bas["bygg_riket"]
    ar = [a for a in bas["ar"] if bl.get(a)]
    toppar = max(ar, key=lambda a: bl[a])
    sist = ar[-1]

    ar_su, v_su = senaste(underlag.get(LANET, {}))
    ar_sats, v_sats = senaste(satser.get(LANET, {}))
    ar_lon, v_lon = senaste(per_syss)

    # befolkningsviktad utjämning per invånare i länets kommuner, senaste året
    kommun_utj = {k: senaste(v) for k, v in utj.items() if k.split()[0].startswith("18")}

    kal = {
        "kalla": "SCB statistikdatabasen via GitHub Actions",
        "bas_byggsysselsatta_lanet": bl,
        "bas_byggsysselsatta_riket": br,
        "bas_totalt_lanet": bas["totalt_lanet"],
        "bas_totalt_riket": bas["totalt_riket"],
        "bas_bygg_kommuner": bas["bygg_kommuner"],
        "rams_byggsysselsatta_lanet_2008_2021": rams,
        "toppar": toppar,
        "senaste_ar": sist,
        "nedgang_lanet_fran_topp": (bl[sist] / bl[toppar] - 1),
        "nedgang_riket_fran_topp": (br[sist] / br[max(ar, key=lambda a: br[a])] - 1),
        "direkt_forandring_personer": bl[sist] - bl[toppar],
        "lanets_andel_av_rikets_bygg": bl[sist] / br[sist],
        "byggandel_av_lanets_syss": {a: bl[a] / bas["totalt_lanet"][a] for a in ar},
        "lonesumma_per_byggsysselsatt_riket": per_syss,
        "lonesumma_per_byggsysselsatt_riket_senaste": {"ar": ar_lon, "varde": v_lon},
        "lonesumma_lanet_mdr": lonlan,
        "lonesumma_riket_mdr": lonriket,
        "skatteunderlag_lanet": {"ar": ar_su, "varde": v_su},
        "skatteunderlag_kommuner": {k: senaste(v) for k, v in underlag.items()
                                    if k.split()[0].startswith("18")},
        "skattesats_lanet": {"ar": ar_sats, "varde": v_sats},
        "skattesats_kommuner": {k: senaste(v) for k, v in satser.items()
                                if k.split()[0].startswith("18")},
        "inkomstutjamning_per_invanare": kommun_utj,
    }

    with open(UT, "w", encoding="utf-8") as f:
        json.dump(kal, f, ensure_ascii=False, indent=1)

    print("KALIBRERING MOT SCB-DATA")
    print("-" * 74)
    print(f"Byggsysselsatta i Örebro län, {ar[0]}-{sist}:")
    print("   " + "  ".join(f"{a}:{int(bl[a]):,}".replace(",", " ") for a in ar))
    print(f"Topp {toppar} ({int(bl[toppar]):,}".replace(",", " ")
          + f") -> {sist} ({int(bl[sist]):,}".replace(",", " ")
          + f"): {int(bl[sist]-bl[toppar]):+} personer, {100*kal['nedgang_lanet_fran_topp']:+.1f} %")
    print(f"Riket från topp: {100*kal['nedgang_riket_fran_topp']:+.1f} %")
    print(f"Länets andel av rikets byggsysselsättning: "
          f"{100*kal['lanets_andel_av_rikets_bygg']:.2f} %")
    print(f"Byggets andel av länets sysselsättning: "
          f"{100*kal['byggandel_av_lanets_syss'][toppar]:.2f} % ({toppar}) -> "
          f"{100*kal['byggandel_av_lanets_syss'][sist]:.2f} % ({sist})")
    print(f"Länets TOTALA sysselsättning {toppar}: "
          f"{int(bas['totalt_lanet'][toppar]):,}".replace(",", " ")
          + f" -> {sist}: {int(bas['totalt_lanet'][sist]):,}".replace(",", " "))
    print(f"Lönesumma per byggsysselsatt (riket, {ar_lon}): {v_lon:,.0f} kr".replace(",", " "))
    print(f"Skatteunderlag Örebro län ({ar_su}): {v_su/1e9:,.1f} mdr kr".replace(",", " "))
    print(f"Total kommunal skattesats i länet ({ar_sats}): {v_sats} %")
    print(f"\nSkrev {os.path.relpath(UT, HAR)}")


if __name__ == "__main__":
    main()
