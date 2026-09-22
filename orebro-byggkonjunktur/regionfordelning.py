#!/usr/bin/env python3
"""
Byggsysselsättningens fördelning på län: var aktiviteten är koncentrerad,
hur koncentrationen förändrats, och var nedgången respektive vändningen ligger.

  python3 regionfordelning.py

Läser data/scb/bas_ar_alla_lan.csv, bas_manad_alla_lan_bygg.csv och
rams_bygg_alla_lan_2008_2018.csv. Samtliga län summerar till riket.
"""

import csv
import os

SCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scb")
RIKET = "00 Riket"
BYGG = "F byggindustri"
TOTALT = "A-U+US Total"


def las(namn):
    with open(os.path.join(SCB, namn), encoding="utf-8") as f:
        return list(csv.reader(f))


def tal(s):
    s = (s or "").strip()
    return float(s) if s and s != ".." else None


def kort(namn):
    return namn.split(" ", 1)[1] if " " in namn else namn


def bas_ar():
    r = las("bas_ar_alla_lan.csv")
    kol = [(i, h.split()[-1]) for i, h in enumerate(r[0]) if "arbetsställets" in h]

    def plocka(bransch):
        return {x[0]: {a: tal(x[i]) for i, a in kol} for x in r[1:]
                if x[2] == bransch and x[1] == "totalt" and x[3] == "totalt"}

    return [a for _, a in kol], plocka(BYGG), plocka(TOTALT)


def tabell_andelar(ar, bygg, tot):
    riket = bygg[RIKET]
    lan = {k: v for k, v in bygg.items() if k != RIKET}
    forsta, sist = ar[0], ar[-1]
    jmf = "2022" if "2022" in ar else forsta

    kontroll = sum(v[sist] for v in lan.values())
    print("=" * 108)
    print("BYGGSYSSELSÄTTNINGENS FÖRDELNING PÅ LÄN")
    print(f"Kontroll {sist}: summa län {kontroll:,.0f} mot riket {riket[sist]:,.0f}"
          .replace(",", " "))
    print("=" * 108)

    print(f"\n{'Län':<24}" + "".join(f"{a:>8}" for a in ar)
          + f"{'ändr pe':>10}{'personer':>11}{'procent':>9}")
    print("-" * 108)
    rader = [(k, {a: 100 * v[a] / riket[a] for a in ar}, v) for k, v in lan.items()]
    for k, andel, v in sorted(rader, key=lambda x: -x[1][sist]):
        print(f"{kort(k):<24}" + "".join(f"{andel[a]:>8.2f}" for a in ar)
              + f"{andel[sist]-andel[jmf]:>+10.2f}"
              + f"{v[sist]-v[jmf]:>+11,.0f}".replace(",", " ")
              + f"{100*(v[sist]/v[jmf]-1):>8.1f}%")

    andelar = sorted((100 * v[sist] / riket[sist] for v in lan.values()), reverse=True)
    tandelar = sorted((100 * tot[k][sist] / tot[RIKET][sist] for k in lan), reverse=True)
    print("\nKONCENTRATION " + sist)
    for n in (1, 3, 6, 10):
        print(f"  {n:>2} största länen: {sum(andelar[:n]):>5.1f} % av byggsysselsättningen"
              f"   (all sysselsättning: {sum(tandelar[:n]):.1f} %)")
    print(f"  Herfindahl: bygg {sum(a**2 for a in andelar):.0f}, "
          f"all sysselsättning {sum(a**2 for a in tandelar):.0f}")


def tabell_intensitet(ar, bygg, tot):
    sist = ar[-1]
    jmf = "2022" if "2022" in ar else ar[0]
    print("\n\nBYGGINTENSITET OCH LOKALISERINGSKVOT")
    print("Byggets andel av länets EGEN sysselsättning. LQ = länets andel av rikets")
    print("byggsysselsättning delat med dess andel av all sysselsättning.")
    print("-" * 108)
    print(f"{'Län':<24}{'bygg% ' + jmf:>12}{'bygg% ' + sist:>12}{'ändring':>10}"
          f"{'LQ':>8}{'byggsyss':>12}")
    rader = []
    for k in bygg:
        if k == RIKET:
            continue
        lq = ((bygg[k][sist] / bygg[RIKET][sist])
              / (tot[k][sist] / tot[RIKET][sist]))
        rader.append((k, 100 * bygg[k][jmf] / tot[k][jmf],
                      100 * bygg[k][sist] / tot[k][sist], lq, bygg[k][sist]))
    for k, i0, i1, lq, n in sorted(rader, key=lambda x: -x[3]):
        print(f"{kort(k):<24}{i0:>12.2f}{i1:>12.2f}{i1-i0:>+10.2f}{lq:>8.2f}"
              + f"{n:>12,.0f}".replace(",", " "))


def tabell_langre_sikt():
    try:
        r = las("rams_bygg_alla_lan_2008_2018.csv")
    except FileNotFoundError:
        return
    kol = [(i, h.split()[-1]) for i, h in enumerate(r[0]) if h.startswith("Antal")]
    ar = [a for _, a in kol]
    d = {}
    for x in r[1:]:
        if x[1].startswith("F bygg"):
            d.setdefault(x[0], {a: 0.0 for a in ar})
            for i, a in kol:
                d[x[0]][a] += tal(x[i]) or 0
    riket = d[RIKET]
    lan = {k: v for k, v in d.items() if k != RIKET}
    a0, a1 = ar[0], ar[-1]
    print(f"\n\nLÄNGRE SIKT: ANDELAR ENLIGT RAMS {a0}-{a1}")
    print("(annan källa och definition än BAS - jämför andelar, inte nivåer)")
    print("-" * 108)
    print(f"{'Län':<24}{a0:>10}{a1:>10}{'ändr pe':>10}")
    for k, v in sorted(lan.items(), key=lambda x: -x[1][a1]):
        p0, p1 = 100 * v[a0] / riket[a0], 100 * v[a1] / riket[a1]
        print(f"{kort(k):<24}{p0:>10.2f}{p1:>10.2f}{p1-p0:>+10.2f}")
    t0 = sorted((100 * v[a0] / riket[a0] for v in lan.values()), reverse=True)
    t1 = sorted((100 * v[a1] / riket[a1] for v in lan.values()), reverse=True)
    print(f"\n  3 största länen: {a0} {sum(t0[:3]):.1f} %  ->  {a1} {sum(t1[:3]):.1f} %")


def tabell_vandning():
    try:
        r = las("bas_manad_alla_lan_bygg.csv")
    except FileNotFoundError:
        return
    kol = [(i, h.split()[-1]) for i, h in enumerate(r[0]) if "arbetsställets" in h]
    d = {x[0]: {a: tal(x[i]) for i, a in kol} for x in r[1:]
         if x[1] == "totalt" and x[3] == "totalt"}
    manader = sorted({a for v in d.values() for a in v if v[a]})
    sista_ar = manader[-1][:4]
    n = int(manader[-1][-2:])
    tidigare = str(int(sista_ar) - 1)

    def period(serie, y):
        v = [serie[f"{y}M{i:02d}"] for i in range(1, n + 1)
             if serie.get(f"{y}M{i:02d}")]
        return sum(v) / len(v) if len(v) == n else None

    print(f"\n\nVÄNDNINGEN: {sista_ar}M01-{manader[-1][-3:]} jämfört med samma "
          f"period {tidigare}")
    print("-" * 108)
    rader = []
    for k, v in d.items():
        a, b = period(v, tidigare), period(v, sista_ar)
        if a and b:
            rader.append((k, a, b, 100 * (b / a - 1)))
    for k, a, b, p in sorted(rader, key=lambda x: -x[3]):
        markering = "  <-- riket" if k == RIKET else ""
        print(f"{kort(k):<24}{a:>12,.0f}{b:>12,.0f}{p:>+9.1f}%{markering}"
              .replace(",", " "))


def main():
    ar, bygg, tot = bas_ar()
    tabell_andelar(ar, bygg, tot)
    tabell_intensitet(ar, bygg, tot)
    tabell_langre_sikt()
    tabell_vandning()


if __name__ == "__main__":
    main()
