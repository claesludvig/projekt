#!/usr/bin/env python3
"""
Byggkonjunkturen i Orebro lan: sysselsattning, skatteunderlag, spridningseffekter.

Kor:  python3 modell.py            (skriver tabeller till stdout)
      python3 modell.py --csv      (skriver aven data/resultat.csv)

Modellen ar medvetet transparent: allt som inte ar hamtat fran SCB ligger i
parametrar.py och varieras i kansligheten langst ned.
"""

import argparse
import csv
import os
import sys

import parametrar as P

MSEK = 1_000_000


# ---------------------------------------------------------------------------
# Byggstenar
# ---------------------------------------------------------------------------

def byggsysselsattning_2022():
    """Niva i lanet vid konjunkturtoppen."""
    return P.RIKET_BYGG_2022 * P.ANDEL_AV_RIKETS_BYGGSYSSELSATTNING


def direkt_effekt(nedgang):
    """Direkt forandring av antalet byggsysselsatta i lanet."""
    return byggsysselsattning_2022() * nedgang


def spridning(direkt, mult):
    """Indirekt + inducerad sysselsattning utover den direkta."""
    return direkt * (mult - 1.0)


def kvarvarande_inkomstandel():
    """
    Andel av den forlorade loneinkomsten som finns kvar i skatteunderlaget
    efter omstallning. 1 - detta ar det faktiska bortfallet.
    """
    return sum(andel * kvar for andel, kvar in P.OMSTALLNING.values())


def nettoandel():
    """Andel av bruttoloneunderlaget som faktiskt lamnar skatteunderlaget."""
    return 1.0 - kvarvarande_inkomstandel()


def skatteunderlag(direkt, indirekt):
    """Bruttoforandring av lonesumman i lanet, kronor."""
    return direkt * P.ARSLON_BYGG_LAN + indirekt * P.ARSLON_OVRIGT_LAN


def skatteintakter(underlag):
    """Kommunal och regional skatteintakt pa ett givet skatteunderlag."""
    kommun = underlag * P.SKATTESATS_KOMMUN_LAN
    region = underlag * P.SKATTESATS_REGION
    return kommun, region, kommun + region


def utjamningskompensation(underlag):
    """
    Vad inkomstutjamningen kompenserar OM bortfallet vore unikt for lanet.
    Vid en riksgemensam nedgang faller medelskattekraften ocksa, och
    kompensationen ar da i princip noll (se README avsnitt 5).
    """
    kommun = underlag * P.KOMPENSATIONSGRAD * P.LANSVIS_SKATTESATS_KOMMUN
    region = underlag * P.KOMPENSATIONSGRAD * P.LANSVIS_SKATTESATS_REGION
    return kommun, region, kommun + region


# ---------------------------------------------------------------------------
# Scenariokorning
# ---------------------------------------------------------------------------

def kor_scenario(nedgang, mult_typ1, mult_typ2):
    d = direkt_effekt(nedgang)
    ind_typ1 = spridning(d, mult_typ1)
    ind_typ2 = spridning(d, mult_typ2)

    brutto = skatteunderlag(d, ind_typ2)
    netto = brutto * nettoandel()

    bk, br, bt = skatteintakter(brutto)
    nk, nr, nt = skatteintakter(netto)
    uk, ur, ut = utjamningskompensation(netto)

    return {
        "nedgang_pct": nedgang * 100,
        "direkt_jobb": d,
        "indirekt_jobb_typ1": ind_typ1,
        "indirekt_inducerat_jobb_typ2": ind_typ2,
        "totalt_jobb_typ2": d + ind_typ2,
        "skatteunderlag_brutto": brutto,
        "skatteunderlag_netto": netto,
        "skatt_brutto_kommun": bk,
        "skatt_brutto_region": br,
        "skatt_brutto_totalt": bt,
        "skatt_netto_kommun": nk,
        "skatt_netto_region": nr,
        "skatt_netto_totalt": nt,
        "utjamning_om_lokal_chock": ut,
        "kvar_efter_utjamning_om_lokal_chock": nt - ut,
    }


# ---------------------------------------------------------------------------
# Utskrift
# ---------------------------------------------------------------------------

def rad(etikett, *varden, bredd=14, dec=0):
    celler = "".join(f"{v:>{bredd},.{dec}f}".replace(",", " ") if isinstance(v, (int, float))
                     else f"{v:>{bredd}}" for v in varden)
    return f"{etikett:<52}{celler}"


def skriv_tabeller(resultat):
    scen = list(resultat.keys())
    r = resultat

    print("=" * 112)
    print("BYGGKONJUNKTUREN I OREBRO LAN - ESTIMERADE EFFEKTER, TOPP 2022 TILL BOTTEN 2025")
    print("=" * 112)
    print(f"\nByggsysselsatta i lanet 2022 (utgangsniva): {byggsysselsattning_2022():,.0f}".replace(",", " "))
    print(f"Andel av rikets byggsysselsattning:         {P.ANDEL_AV_RIKETS_BYGGSYSSELSATTNING:.2%}")
    print(f"Andel av loneinkomsten som forsvinner ur skatteunderlaget efter omstallning: "
          f"{nettoandel():.0%}")

    print("\n\nTABELL 1. SYSSELSATTNING (personer)")
    print("-" * 112)
    print(rad("", *[f"{s}" for s in scen]))
    print(rad("Nedgang, byggsysselsattning (%)", *[r[s]["nedgang_pct"] for s in scen], dec=1))
    print(rad("Direkt effekt, bygg", *[r[s]["direkt_jobb"] for s in scen]))
    print(rad("Indirekt (typ I, underleverantorer i lanet)",
              *[r[s]["indirekt_jobb_typ1"] for s in scen]))
    print(rad("Indirekt + inducerat (typ II)",
              *[r[s]["indirekt_inducerat_jobb_typ2"] for s in scen]))
    print(rad("SUMMA sysselsattningseffekt i lanet", *[r[s]["totalt_jobb_typ2"] for s in scen]))

    print("\n\nTABELL 2. SKATTEUNDERLAG (mn kr per ar)")
    print("-" * 112)
    print(rad("Bruttobortfall lonesumma",
              *[r[s]["skatteunderlag_brutto"] / MSEK for s in scen]))
    print(rad("Nettobortfall efter omstallning",
              *[r[s]["skatteunderlag_netto"] / MSEK for s in scen]))

    print("\n\nTABELL 3. SKATTEINTAKTER (mn kr per ar)")
    print("-" * 112)
    print(rad("Mekaniskt brutto: kommunerna",
              *[r[s]["skatt_brutto_kommun"] / MSEK for s in scen]))
    print(rad("Mekaniskt brutto: regionen",
              *[r[s]["skatt_brutto_region"] / MSEK for s in scen]))
    print(rad("Mekaniskt brutto: totalt",
              *[r[s]["skatt_brutto_totalt"] / MSEK for s in scen]))
    print()
    print(rad("Realistiskt netto: kommunerna",
              *[r[s]["skatt_netto_kommun"] / MSEK for s in scen]))
    print(rad("Realistiskt netto: regionen",
              *[r[s]["skatt_netto_region"] / MSEK for s in scen]))
    print(rad("Realistiskt netto: TOTALT",
              *[r[s]["skatt_netto_totalt"] / MSEK for s in scen]))

    print("\n\nTABELL 4. INKOMSTUTJAMNINGEN (mn kr per ar)")
    print("-" * 112)
    print(rad("Om chocken vore unik for lanet: kompensation",
              *[r[s]["utjamning_om_lokal_chock"] / MSEK for s in scen]))
    print(rad("  ... kvar att bara sjalv",
              *[r[s]["kvar_efter_utjamning_om_lokal_chock"] / MSEK for s in scen]))
    print(rad("Riksgemensam chock: kompensation", *["0" for _ in scen]))
    print(rad("  ... kvar att bara sjalv",
              *[r[s]["skatt_netto_totalt"] / MSEK for s in scen]))

    print("\n\nTABELL 5. PROPORTIONER (central-scenariot)")
    print("-" * 112)
    c = r["central"]
    tot_skatteunderlag = P.SKATTEUNDERLAG_PER_INV_LAN * P.BEFOLKNING_LAN
    tot_skatt = tot_skatteunderlag * (P.SKATTESATS_KOMMUN_LAN + P.SKATTESATS_REGION)
    print(rad("Lanets samlade skatteintakter (mdr kr)", tot_skatt / 1e9, dec=1))
    print(rad("Bortfallet som andel av dessa (%)",
              100 * c["skatt_netto_totalt"] / tot_skatt, dec=2))
    print(rad("Mekaniskt brutto som andel (%)",
              100 * c["skatt_brutto_totalt"] / tot_skatt, dec=2))
    print(rad("Motsvarar antal kommunala arsarbetare (a 650 tkr)",
              c["skatt_netto_totalt"] / 650_000))
    print(rad("Jamforelse: 1 000 uteblivna invanare (mn kr)",
              1000 * P.MARGINALINTAKT_PER_INVANARE / MSEK, dec=1))


def kanslighet(bas_nedgang):
    """Hur mycket varje enskilt antagande flyttar nettoresultatet."""
    print("\n\nTABELL 6. KANSLIGHET - nettobortfall skatteintakter, central nedgang (mn kr/ar)")
    print("-" * 112)

    def berakna(mult2=None, netto_override=None, arslon=None, andel=None):
        m2 = mult2 if mult2 is not None else P.MULT_REGIONAL_TYP2["central"]
        gammal_lon = P.ARSLON_BYGG_LAN
        gammal_andel = P.ANDEL_AV_RIKETS_BYGGSYSSELSATTNING
        if arslon:
            P.ARSLON_BYGG_LAN = arslon
        if andel:
            P.ANDEL_AV_RIKETS_BYGGSYSSELSATTNING = andel
        d = direkt_effekt(bas_nedgang)
        ind = spridning(d, m2)
        brutto = skatteunderlag(d, ind)
        n = netto_override if netto_override is not None else nettoandel()
        _, _, t = skatteintakter(brutto * n)
        P.ARSLON_BYGG_LAN = gammal_lon
        P.ANDEL_AV_RIKETS_BYGGSYSSELSATTNING = gammal_andel
        return t / MSEK

    bas = berakna()
    print(rad("BASFALL", bas, dec=1))
    print(rad("Regional multiplikator typ II = 1,35 (lag)",
              berakna(mult2=P.MULT_REGIONAL_TYP2["lag"]), dec=1))
    print(rad("Regional multiplikator typ II = 1,70 (hog)",
              berakna(mult2=P.MULT_REGIONAL_TYP2["hog"]), dec=1))
    print(rad("Nationell multiplikator 2,00 (fel anvand regionalt)",
              berakna(mult2=P.MULT_NATIONELL_TYP2), dec=1))
    print(rad("Omstallning: 25 % av inkomsten forsvinner",
              berakna(netto_override=0.25), dec=1))
    print(rad("Omstallning: 50 % av inkomsten forsvinner",
              berakna(netto_override=0.50), dec=1))
    print(rad("Omstallning: 100 % (ingen aterinkomst alls)",
              berakna(netto_override=1.00), dec=1))
    print(rad("Arslon 400 tkr", berakna(arslon=400_000), dec=1))
    print(rad("Arslon 500 tkr", berakna(arslon=500_000), dec=1))
    print(rad("Lanets byggandel 2,50 %", berakna(andel=0.0250), dec=1))
    print(rad("Lanets byggandel 3,00 %", berakna(andel=0.0300), dec=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true", help="skriv aven data/resultat.csv")
    args = ap.parse_args()

    resultat = {}
    for namn, nedgang in P.SCENARIER_NEDGANG.items():
        resultat[namn] = kor_scenario(
            nedgang,
            P.MULT_REGIONAL_TYP1["central"],
            P.MULT_REGIONAL_TYP2["central"],
        )

    skriv_tabeller(resultat)
    kanslighet(P.SCENARIER_NEDGANG["central"])

    if args.csv:
        os.makedirs("data", exist_ok=True)
        falt = list(next(iter(resultat.values())).keys())
        with open("data/resultat.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["scenario"] + falt)
            for namn, v in resultat.items():
                w.writerow([namn] + [f"{v[k]:.1f}" for k in falt])
        print("\n\nSkrev data/resultat.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
