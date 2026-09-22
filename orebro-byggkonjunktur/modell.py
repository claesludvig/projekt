#!/usr/bin/env python3
"""
Byggkonjunkturen i Örebro län: sysselsättning, skatteunderlag, spridningseffekter.

  python3 modell.py          tabeller till stdout
  python3 modell.py --csv    skriver även data/resultat.csv

Sysselsättnings-, löne- och skattedata är hämtade från SCB (se hamta_scb.py).
Multiplikatorer och omställningsantaganden är modellval och varieras i
känslighetsanalysen.
"""

import argparse
import csv
import os
import sys

import parametrar as P

MSEK = 1_000_000


def rad(etikett, *varden, bredd=15, dec=0):
    celler = "".join(
        f"{v:>{bredd},.{dec}f}".replace(",", " ") if isinstance(v, (int, float))
        else f"{v:>{bredd}}" for v in varden)
    return f"{etikett:<54}{celler}"


def kvarvarande_inkomstandel():
    return sum(andel * kvar for andel, kvar in P.OMSTALLNING.values())


def nettoandel():
    return 1.0 - kvarvarande_inkomstandel()


def kor_scenario(nedgang, mult1, mult2, netto=None):
    """nedgang är negativ och mäts från toppåret."""
    bas = P.BYGG_LANET.get(P.TOPPAR)
    direkt = bas * nedgang
    ind1 = direkt * (mult1 - 1.0)
    ind2 = direkt * (mult2 - 1.0)

    brutto = direkt * P.ARSLON_BYGG_LAN + ind2 * P.ARSLON_OVRIGT_LAN
    n = nettoandel() if netto is None else netto
    netto_underlag = brutto * n

    def skatt(u):
        return (u * P.SKATTESATS_KOMMUN_LAN, u * P.SKATTESATS_REGION,
                u * (P.SKATTESATS_KOMMUN_LAN + P.SKATTESATS_REGION))

    bk, br_, bt = skatt(brutto)
    nk, nr, nt = skatt(netto_underlag)
    uk = netto_underlag * P.KOMPENSATIONSGRAD * P.LANSVIS_SKATTESATS_KOMMUN
    ur = netto_underlag * P.KOMPENSATIONSGRAD * P.LANSVIS_SKATTESATS_REGION

    return {
        "nedgang_pct": nedgang * 100,
        "direkt": direkt, "indirekt_typ1": ind1, "indirekt_typ2": ind2,
        "totalt_jobb": direkt + ind2,
        "underlag_brutto": brutto, "underlag_netto": netto_underlag,
        "skatt_brutto_kommun": bk, "skatt_brutto_region": br_, "skatt_brutto": bt,
        "skatt_netto_kommun": nk, "skatt_netto_region": nr, "skatt_netto": nt,
        "utjamning_lokal_chock": uk + ur,
        "kvar_vid_lokal_chock": nt - (uk + ur),
    }


# ---------------------------------------------------------------------------

def tabell_sysselsattning():
    print("=" * 118)
    print("BYGGKONJUNKTUREN I ÖREBRO LÄN")
    print("Sysselsättning, skatteintäkter och spridningseffekter. "
          f"Data: SCB{'' if P.KALIBRERAD else ' (EJ KALIBRERAD - reservvärden)'}")
    print("=" * 118)

    print("\n\nTABELL 1. BYGGSYSSELSATTA I ÖREBRO LÄN (dagbefolkning)")
    print("-" * 118)
    if P.RAMS_LANET:
        ar = sorted(P.RAMS_LANET)
        print("RAMS 2008-2021 (förvärvsarbetande 16+):")
        for i in range(0, len(ar), 7):
            grupp = ar[i:i + 7]
            print("   " + "  ".join(f"{a}: {P.RAMS_LANET[a]:>6,.0f}".replace(",", " ")
                                    for a in grupp))
    ar = sorted(P.BYGG_LANET)
    print("\nBAS 2020- (sysselsatta 15-74 år, ny serie, ej jämförbar med RAMS i nivå):")
    print("   " + "  ".join(f"{a}: {P.BYGG_LANET[a]:>6,.0f}".replace(",", " ")
                            for a in ar))
    print("   " + "  ".join(f"{a}: {100*P.BYGG_LANET[a]/P.SYSS_LANET[a]:>5.2f}%"
                            for a in ar) + "   (andel av länets sysselsättning)")
    print()
    print(rad(f"Toppår {P.TOPPAR}", P.BYGG_LANET[P.TOPPAR]))
    print(rad(f"Senaste år {P.SENASTE_AR}", P.BYGG_LANET[P.SENASTE_AR]))
    print(rad("FAKTISK FÖRÄNDRING, personer", P.DIREKT_FORANDRING))
    print(rad("FAKTISK FÖRÄNDRING, procent", 100 * P.NEDGANG_LANET, dec=1))
    print(rad("Samma tal för riket, procent", 100 * P.NEDGANG_RIKET, dec=1))
    print(rad("Länets andel av rikets byggsysselsättning, procent",
              100 * P.LANETS_ANDEL_AV_RIKET, dec=2))
    print()
    print(rad(f"Länets TOTALA sysselsättning {P.TOPPAR}", P.SYSS_LANET[P.TOPPAR]))
    print(rad(f"Länets TOTALA sysselsättning {P.SENASTE_AR}",
              P.SYSS_LANET[P.SENASTE_AR]))
    print(rad("  ... förändring", P.SYSS_LANET[P.SENASTE_AR] - P.SYSS_LANET[P.TOPPAR]))
    print("\n  Länets totala sysselsättning STEG medan byggsysselsättningen föll.")
    print("  Arbetskraften absorberades av länets övriga arbetsmarknad, vilket är")
    print("  avgörande för hur stort skatteunderlagsbortfallet blir (tabell 4).")


def tabell_kommuner():
    if not P.BYGG_KOMMUNER:
        return
    print("\n\nTABELL 2. BYGGSYSSELSÄTTNING PER KOMMUN")
    print("-" * 118)
    rader = []
    for namn, serie in P.BYGG_KOMMUNER.items():
        s = {int(a): v for a, v in serie.items() if v is not None}
        if P.TOPPAR in s and P.SENASTE_AR in s:
            rader.append((namn, s[P.TOPPAR], s[P.SENASTE_AR],
                          s[P.SENASTE_AR] - s[P.TOPPAR],
                          100 * (s[P.SENASTE_AR] / s[P.TOPPAR] - 1)))
    rader.sort(key=lambda r: r[3])
    print(f"{'':<54}{str(P.TOPPAR):>15}{str(P.SENASTE_AR):>15}"
          f"{'förändring':>15}{'procent':>15}")
    for namn, a, b, d, p in rader:
        print(rad(namn, a, b, d, p, dec=0) if False else
              f"{namn:<54}{a:>15,.0f}{b:>15,.0f}{d:>+15,.0f}{p:>14.1f}%"
              .replace(",", " "))
    summa = sum(r[3] for r in rader)
    print(f"{'SUMMA kommuner':<54}{'':>15}{'':>15}{summa:>+15,.0f}".replace(",", " "))


def tabell_effekter(resultat):
    scen = list(resultat)
    r = resultat
    print("\n\nTABELL 3. SPRIDNINGSEFFEKTER (personer)")
    print("-" * 118)
    print(rad("", *scen))
    print(rad("Nedgång från toppåret, procent",
              *[r[s]["nedgang_pct"] for s in scen], dec=1))
    print(rad("Direkt, byggverksamhet", *[r[s]["direkt"] for s in scen]))
    print(rad(f"Indirekt i länet, typ I ({P.MULT_REGIONAL_TYP1['central']})",
              *[r[s]["indirekt_typ1"] for s in scen]))
    print(rad(f"Indirekt + inducerat, typ II ({P.MULT_REGIONAL_TYP2['central']})",
              *[r[s]["indirekt_typ2"] for s in scen]))
    print(rad("SUMMA i länet", *[r[s]["totalt_jobb"] for s in scen]))
    print(rad("Till jämförelse: nationell typ II ("
              f"{P.MULT_NATIONELL_TYP2})",
              *[r[s]["direkt"] * P.MULT_NATIONELL_TYP2 for s in scen]))

    print("\n\nTABELL 4. SKATTEUNDERLAG (mn kr per år)")
    print("-" * 118)
    print(rad(f"Årslön i bygg, länet ({P.ARSLON_BYGG_LAN:,.0f} kr)"
              .replace(",", " "), *["" for _ in scen]))
    print(rad("Bruttobortfall lönesumma",
              *[r[s]["underlag_brutto"] / MSEK for s in scen]))
    print(rad(f"Nettobortfall efter omställning ({nettoandel():.0%} av brutto)",
              *[r[s]["underlag_netto"] / MSEK for s in scen]))

    print("\n\nTABELL 5. SKATTEINTÄKTER (mn kr per år)")
    print("-" * 118)
    print(rad(f"Skattesats: kommun {100*P.SKATTESATS_KOMMUN_LAN:.2f} + region "
              f"{100*P.SKATTESATS_REGION:.2f} = "
              f"{100*(P.SKATTESATS_KOMMUN_LAN+P.SKATTESATS_REGION):.2f} %",
              *["" for _ in scen]))
    print(rad("Mekaniskt brutto, kommunerna",
              *[r[s]["skatt_brutto_kommun"] / MSEK for s in scen]))
    print(rad("Mekaniskt brutto, regionen",
              *[r[s]["skatt_brutto_region"] / MSEK for s in scen]))
    print(rad("Mekaniskt brutto, totalt", *[r[s]["skatt_brutto"] / MSEK for s in scen]))
    print()
    print(rad("Realistiskt netto, kommunerna",
              *[r[s]["skatt_netto_kommun"] / MSEK for s in scen]))
    print(rad("Realistiskt netto, regionen",
              *[r[s]["skatt_netto_region"] / MSEK for s in scen]))
    print(rad("REALISTISKT NETTO, TOTALT", *[r[s]["skatt_netto"] / MSEK for s in scen]))

    print("\n\nTABELL 6. INKOMSTUTJÄMNINGEN (mn kr per år)")
    print("-" * 118)
    print(rad("Om chocken vore unik för länet: kompensation",
              *[r[s]["utjamning_lokal_chock"] / MSEK for s in scen]))
    print(rad("  ... kvar att bära själv",
              *[r[s]["kvar_vid_lokal_chock"] / MSEK for s in scen]))
    print(rad("Riksgemensam chock: kompensation", *[0.0 for _ in scen]))
    print(rad("  ... kvar att bära själv", *[r[s]["skatt_netto"] / MSEK for s in scen]))
    print("\n  Byggnedgången var riksgemensam (länet -%.1f %%, riket -%.1f %%)."
          % (-100 * P.NEDGANG_LANET, -100 * P.NEDGANG_RIKET))
    print("  Medelskattekraften faller lika mycket som den egna, utjämningen ser")
    print("  ingen relativ försämring, och genomslaget blir i praktiken fullt.")


def tabell_proportioner(resultat):
    print("\n\nTABELL 7. PROPORTIONER (observerat scenario)")
    print("-" * 118)
    c = resultat["observerad"]
    skatt_totalt = P.SKATTEUNDERLAG_LANET * (P.SKATTESATS_KOMMUN_LAN
                                             + P.SKATTESATS_REGION)
    print(rad(f"Länets skatteunderlag {P.SKATTEUNDERLAG_AR} (mdr kr)",
              P.SKATTEUNDERLAG_LANET / 1e9, dec=1))
    print(rad("Samlade skatteintäkter, kommuner + region (mdr kr)",
              skatt_totalt / 1e9, dec=1))
    print(rad("Nettobortfallet som andel av dessa (%)",
              100 * c["skatt_netto"] / skatt_totalt, dec=3))
    print(rad("Mekaniskt brutto som andel (%)",
              100 * c["skatt_brutto"] / skatt_totalt, dec=3))
    print(rad("Motsvarar antal kommunala årsarbetare (à 650 tkr)",
              c["skatt_netto"] / 650_000))
    print(rad("Till jämförelse: 1 000 uteblivna invånare (mn kr)",
              -1000 * P.MARGINALINTAKT_PER_INVANARE / MSEK, dec=1))
    print(rad("Direkt bortfall som andel av länets sysselsättning (%)",
              100 * P.DIREKT_FORANDRING / P.SYSS_LANET[P.TOPPAR], dec=2))


def tabell_kanslighet():
    print("\n\nTABELL 8. KÄNSLIGHET - nettobortfall skatteintäkter, "
          "observerad nedgång (mn kr/år)")
    print("-" * 118)
    n = P.NEDGANG_LANET

    def k(mult2=None, netto=None, lon=None):
        gammal = P.ARSLON_BYGG_LAN
        if lon:
            P.ARSLON_BYGG_LAN = lon
        res = kor_scenario(n, P.MULT_REGIONAL_TYP1["central"],
                           mult2 or P.MULT_REGIONAL_TYP2["central"], netto)
        P.ARSLON_BYGG_LAN = gammal
        return res["skatt_netto"] / MSEK

    print(rad("BASFALL", k(), dec=1))
    for etikett, m in (("låg 1,35", P.MULT_REGIONAL_TYP2["lag"]),
                       ("hög 1,70", P.MULT_REGIONAL_TYP2["hog"]),
                       (f"nationell {P.MULT_NATIONELL_TYP2} (fel regionalt)",
                        P.MULT_NATIONELL_TYP2)):
        print(rad(f"Multiplikator typ II: {etikett}"[:53], k(mult2=m), dec=1))
    for etikett, v in (("20 % försvinner", 0.20), ("50 % försvinner", 0.50),
                       ("100 %, ingen återinkomst alls", 1.00)):
        print(rad(f"Omställning: {etikett}", k(netto=v), dec=1))
    print(rad("Årslön 380 tkr", k(lon=380_000), dec=1))
    print(rad("Årslön 455 tkr (riksnivå, ingen länsjustering)",
              k(lon=P.ARSLON_BYGG_RIKET), dec=1))


def tabell_empiriskt_test():
    diff = P.K.get("skatteunderlag_tillvaxt_minus_riket", {})
    if not diff:
        return
    print("\n\nTABELL 9. EMPIRISKT TEST - syns byggnedgången i länets skatteunderlag?")
    print("-" * 118)
    print("Örebro läns skatteunderlagstillväxt minus rikets, procentenheter per år:")
    ar = sorted(diff)[-12:]
    for i in range(0, len(ar), 6):
        grupp = ar[i:i + 6]
        print("   " + "  ".join(f"{a}: {100*diff[a]:+5.2f}" for a in grupp))
    fore = [diff[a] for a in ar if a < "2022"]
    efter = [diff[a] for a in ar if a >= "2022"]
    if fore and efter:
        print()
        print(rad("Snitt före 2022 (procentenheter)", 100 * sum(fore) / len(fore), dec=2))
        print(rad("Snitt 2022 och senare", 100 * sum(efter) / len(efter), dec=2))
        print("\n  Länets skatteunderlag har halkat efter riket med ungefär en halv")
        print("  procentenhet om året sedan mitten av 2010-talet. Gapet är något")
        print("  större efter 2022 än före, men 2021 - innan nedgången bet - var det")
        print("  större än något år därefter. Skillnaden ligger inom seriens egen")
        print("  variation. Byggnedgången går alltså inte att utläsa ur aggregatet,")
        print("  vilket den heller inte borde: 497 personer är 0,33 procent av")
        print("  länets sysselsättning, och bruttoeffekten 0,4 procent av")
        print("  skatteunderlaget - mindre än driften mot riket ett enskilt år.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    resultat = {namn: kor_scenario(n, P.MULT_REGIONAL_TYP1["central"],
                                   P.MULT_REGIONAL_TYP2["central"])
                for namn, n in P.SCENARIER_NEDGANG.items()}

    tabell_sysselsattning()
    tabell_kommuner()
    tabell_effekter(resultat)
    tabell_proportioner(resultat)
    tabell_kanslighet()
    tabell_empiriskt_test()

    if args.csv:
        os.makedirs("data", exist_ok=True)
        falt = list(next(iter(resultat.values())))
        with open("data/resultat.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["scenario"] + falt)
            for namn, v in resultat.items():
                w.writerow([namn] + [f"{v[x]:.1f}" for x in falt])
        print("\n\nSkrev data/resultat.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
