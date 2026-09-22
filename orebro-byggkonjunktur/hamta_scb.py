#!/usr/bin/env python3
"""
Hämtar underlaget till Örebro-analysen från SCB:s statistikdatabas (PxWeb v1).

Körs i GitHub Actions, där api.scb.se är nåbar.

  python3 hamta_scb.py sok      # kartlägger trädet, skriver data/scb/_katalog.json
  python3 hamta_scb.py hamta    # hämtar den explicita listan nedan (standard)

Vad kartläggningen visade, och varför listan ser ut som den gör:

  * Regionalräkenskaperna (NR0105) särredovisar INTE byggverksamhet på länsnivå.
    Länstabellen har bara fem aggregat (varuproducenter, tjänsteproducenter...).
    Full branschindelning finns bara på riksområdesnivå (NUTS2), där Örebro
    ingår i Östra Mellansverige. Därför hämtas båda.
  * Byggsysselsättning per län/kommun finns i stället i RAMS (AM0207), med
    SNI2007-koden F = byggverksamhet. Serien är uppdelad på två tabeller.
  * Lönesummor (AM0302) finns per län UTAN bransch och per bransch UTAN län.
    Länsvis bygglönesumma måste därför skattas, inte hämtas.
  * Skatteunderlag, skattesatser och utjämningsutfall per kommun finns i OE.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "orebro-byggkonjunktur/1.0"}
UTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scb")
V1 = "https://api.scb.se/OV0104/v1/doris/sv/ssd"

PAUS = 1.2
_senaste = [0.0]


def _strypt():
    delta = time.time() - _senaste[0]
    if delta < PAUS:
        time.sleep(PAUS - delta)
    _senaste[0] = time.time()


def hamta_ra(url, data=None, forsok=3):
    """GET, eller POST om data ges. Returnerar bytes."""
    for n in range(forsok):
        _strypt()
        try:
            kropp = json.dumps(data).encode("utf-8") if data is not None else None
            huvuden = dict(UA)
            if kropp:
                huvuden["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=kropp, headers=huvuden)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            detalj = e.read()[:400].decode("latin-1", "replace")
            if e.code == 429:
                time.sleep(5 * (n + 1))
                continue
            if n == forsok - 1:
                raise RuntimeError(f"HTTP {e.code}: {detalj}") from None
            time.sleep(2 * (n + 1))
        except Exception:                                    # noqa: BLE001
            if n == forsok - 1:
                raise
            time.sleep(2 * (n + 1))
    raise RuntimeError(url)


def avkoda(b):
    """SCB skickar csv i latin-1 och json i utf-8. Prova i tur och ordning."""
    for kodning in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return b.decode(kodning)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1", "replace")


def json_hamta(url, data=None):
    return json.loads(avkoda(hamta_ra(url, data)))


# ---------------------------------------------------------------------------
# Explicit hämtningslista
# ---------------------------------------------------------------------------
# Värdespecifikation per variabel:
#   "*"       alla värden
#   "OREBRO"  riket + Örebro län + länets tolv kommuner
#   "BYGG"    de värden vars etikett handlar om byggverksamhet
#   [ ... ]   explicita koder

HAMTNINGAR = [
    {
        "namn": "rams_bygg_kommun_2008_2018",
        "url": f"{V1}/AM/AM0207/AM0207K/DagSNI07KonK",
        "val": {"Region": "OREBRO", "SNI2007": "*", "Kon": "*",
                "ContentsCode": "*", "Tid": "*"},
        "om": "RAMS dagbefolkning per kommun och bransch, 2008-2018",
    },
    {
        "namn": "rams_bygg_kommun_2019_2021",
        "url": f"{V1}/AM/AM0207/AM0207Z/DagSni07KonKN",
        "val": {"Region": "OREBRO", "SNI2007": "*", "Kon": "*",
                "ContentsCode": "*", "Tid": "*"},
        "om": "RAMS dagbefolkning per kommun och bransch, 2019-2021",
    },
    {
        "namn": "nr_lan_aggregat",
        "url": f"{V1}/NR/NR0105/NR0105A/NR0105ENS2010T03A",
        "val": {"Region": ["00", "18"], "SNI2007": "*",
                "ContentsCode": "*", "Tid": "*"},
        "om": "Regionalräkenskaper: BRP, sysselsatta, löner per län (5 aggregat)",
    },
    {
        "namn": "nr_nuts2_bransch",
        "url": f"{V1}/NR/NR0105/NR0105A/NR0105ENS2010T04A",
        "val": {"Region": "*", "SNI2007": "BYGG",
                "ContentsCode": "*", "Tid": "*"},
        "om": "Regionalräkenskaper: byggverksamhet per riksområde (NUTS2)",
    },
    {
        "namn": "nr_investeringar",
        "url": f"{V1}/NR/NR0105/NR0105A/NR0105ENS2010T05A",
        "val": {"Region": "*", "SNI2007": "BYGG",
                "ContentsCode": "*", "Tid": "*"},
        "om": "Fasta bruttoinvesteringar per region och näringsgren",
    },
    {
        "namn": "lonesumma_lan",
        "url": f"{V1}/AM/AM0302/AM0302A/LSUMLan",
        "val": {"Lan": ["00", "18"], "ContentsCode": "*", "Tid": "*"},
        "om": "Lönesummor per län, alla branscher",
    },
    {
        "namn": "lonesumma_bransch_riket",
        "url": f"{V1}/AM/AM0302/AM0302A/LSUMSNI07",
        "val": {"SNI2007": "*", "ContentsCode": "*", "Tid": "*"},
        "om": "Lönesummor per bransch, riket - ger byggets lön per anställd",
    },
    {
        "namn": "skatteunderlag_kommun",
        "url": f"{V1}/OE/OE0101/SkatteKraft",
        "val": {"Region": "OREBRO", "ContentsCode": "*", "Tid": "*"},
        "om": "Skatteunderlag och skattekraft per kommun",
    },
    {
        "namn": "kommunalskatt",
        "url": f"{V1}/OE/OE0101/Kommunalskatt",
        "val": {"Region": "OREBRO", "ContentsCode": "*", "Tid": "*"},
        "om": "Skattesatser per kommun",
    },
    {
        "namn": "utjamning",
        "url": f"{V1}/OE/OE0115/OE0115A/KomEkUtj",
        "val": {"Region": "OREBRO", "ContentsCode": "*", "Tid": "*"},
        "om": "Kommunalekonomisk utjämning, utfall per kommun",
    },
]

BYGG_MONSTER = re.compile(r"byggverksamhet|byggindustri|bygg- och anl", re.I)


def los_varden(spec, variabel):
    koder = [str(x) for x in variabel.get("values", [])]
    texter = variabel.get("valueTexts", [])
    if spec == "*":
        return ["*"], "all"
    if spec == "OREBRO":
        valda = [k for k in koder if k == "00" or k == "18"
                 or (k.startswith("18") and len(k) == 4)]
        return valda, "item"
    if spec == "BYGG":
        valda = [k for k, t in zip(koder, texter) if BYGG_MONSTER.search(t or "")]
        return valda or ["*"], ("item" if valda else "all")
    return [k for k in spec if k in koder] or list(spec), "item"


def kor_hamtningar():
    os.makedirs(UTDATA, exist_ok=True)
    manifest = []
    for h in HAMTNINGAR:
        print(f"\n--- {h['namn']}: {h['om']}")
        try:
            meta = json_hamta(h["url"])
        except Exception as e:                               # noqa: BLE001
            print(f"    metadata misslyckades: {e}")
            manifest.append({"namn": h["namn"], "status": f"metadatafel: {e}"})
            continue

        variabler = {v["code"]: v for v in meta.get("variables", [])}
        fraga = []
        for kod, spec in h["val"].items():
            if kod not in variabler:
                print(f"    varning: variabeln {kod} finns inte "
                      f"(tabellen har {list(variabler)})")
                continue
            varden, filt = los_varden(spec, variabler[kod])
            print(f"    {kod}: {filt} -> {varden[:6]}{'...' if len(varden) > 6 else ''}")
            fraga.append({"code": kod, "selection": {"filter": filt, "values": varden}})

        try:
            csv_text = avkoda(hamta_ra(h["url"], {"query": fraga,
                                                  "response": {"format": "csv"}}))
        except Exception as e:                               # noqa: BLE001
            print(f"    HÄMTNING MISSLYCKADES: {e}")
            manifest.append({"namn": h["namn"], "status": f"fel: {e}"})
            continue

        fil = f"{h['namn']}.csv"
        with open(os.path.join(UTDATA, fil), "w", encoding="utf-8") as f:
            f.write(csv_text)
        rader = csv_text.count("\n")
        print(f"    OK -> {fil} ({rader} rader)")
        for r in csv_text.splitlines()[:3]:
            print(f"      {r[:150]}")
        manifest.append({"namn": h["namn"], "fil": fil, "rader": rader,
                         "titel": meta.get("title", ""), "url": h["url"],
                         "status": "ok"})

    with open(os.path.join(UTDATA, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    ok = sum(1 for m in manifest if m["status"] == "ok")
    print(f"\nKLART: {ok} av {len(HAMTNINGAR)} hämtningar lyckades")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Kartläggning av trädet (bredare än förra gången - BAS missades)
# ---------------------------------------------------------------------------

AMNEN = {
    "NR": re.compile(r"regionalr[aä]kenskap|input-output|tillg[aå]ng och anv", re.I),
    "AM": re.compile(r"arbetsmarknad|syssels[aä]tt|l[oö]nesumm|registerbaserad|"
                     r"yrkesregist|befolkningens", re.I),
    "OE": re.compile(r"skatt|kommunal|utj[aä]mning", re.I),
}


def sok():
    os.makedirs(UTDATA, exist_ok=True)
    katalog = []
    for amne, monster in AMNEN.items():
        try:
            mappar = json_hamta(f"{V1}/{amne}")
        except Exception as e:                               # noqa: BLE001
            print(f"[{amne}] {e}")
            continue
        print(f"\n[{amne}] {len(mappar)} mappar:")
        for m in mappar:
            traff = bool(monster.search(m.get("text", "")))
            print(f"   {'*' if traff else ' '} {m['id']:<10} {m.get('text','')[:66]}")
            if not traff:
                continue
            try:
                noder = json_hamta(f"{V1}/{amne}/{m['id']}")
            except Exception as e:                           # noqa: BLE001
                print(f"       {e}")
                continue
            tabeller = [(n, None) for n in noder if n.get("type") == "t"]
            for u in [n for n in noder if n.get("type") == "l"]:
                try:
                    tabeller += [(n, u["id"]) for n in json_hamta(
                        f"{V1}/{amne}/{m['id']}/{u['id']}") if n.get("type") == "t"]
                except Exception:                            # noqa: BLE001
                    pass
            for t, under in tabeller:
                delar = [amne, m["id"]] + ([under] if under else []) + [t["id"]]
                katalog.append({"id": t["id"], "text": t.get("text", ""),
                                "uppdaterad": t.get("updated"),
                                "url": f"{V1}/" + "/".join(delar)})
            print(f"       {len(tabeller)} tabeller")
    with open(os.path.join(UTDATA, "_katalog.json"), "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False, indent=1)
    print(f"\nSkrev {len(katalog)} tabeller till data/scb/_katalog.json")
    return 0


if __name__ == "__main__":
    lage = sys.argv[1] if len(sys.argv) > 1 else "hamta"
    sys.exit(sok() if lage == "sok" else kor_hamtningar())
