#!/usr/bin/env python3
"""
Hämtar underlaget till Örebro-analysen från SCB:s statistikdatabas.

Körs i GitHub Actions, där api.scb.se är nåbar. Skriptet är autonomt:

  1. Hittar ett fungerande API (PxWeb v2 -> v2beta -> v1).
  2. Letar upp kandidattabeller i de ämnesområden analysen behöver.
  3. Väljer automatiskt de tabeller som har både en regionvariabel med
     Örebro län (kod 18) och en näringsgrensvariabel med byggverksamhet
     (SNI F / 41-43).
  4. Hämtar hela tidsserien för Örebro län och skriver CSV.
  5. Dumpar en fullständig katalog över kandidaterna så att urvalet kan
     granskas och förfinas i nästa körning.

Utdata hamnar i data/scb/. Allt skrivs också till stdout så att körningen
går att följa i Actions-loggen.
"""

import itertools
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "orebro-byggkonjunktur/1.0 (analys av regional byggsysselsattning)"}
UTDATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scb")

V1 = "https://api.scb.se/OV0104/v1/doris/sv/ssd"
V2_KANDIDATER = [
    "https://api.scb.se/ov0104/v2/api/v2",
    "https://api.scb.se/ov0104/v2beta/api/v2",
]

OREBRO = "18"

# SCB:s v1-API tillåter 10 anrop per 10 sekunder.
PAUS = 1.2
_senaste = [0.0]


def _strypt():
    delta = time.time() - _senaste[0]
    if delta < PAUS:
        time.sleep(PAUS - delta)
    _senaste[0] = time.time()


def hamta(url, data=None, forsok=3):
    """GET, eller POST om data ges. Returnerar text."""
    for n in range(forsok):
        _strypt()
        try:
            kropp = json.dumps(data).encode("utf-8") if data is not None else None
            huvuden = dict(UA)
            if kropp:
                huvuden["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=kropp, headers=huvuden)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode("utf-8-sig")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (n + 1))
                continue
            if n == forsok - 1:
                raise
            time.sleep(2 * (n + 1))
        except Exception:                                    # noqa: BLE001
            if n == forsok - 1:
                raise
            time.sleep(2 * (n + 1))
    raise RuntimeError(url)


def json_hamta(url, data=None):
    return json.loads(hamta(url, data))


# ---------------------------------------------------------------------------
# Identifiering av rätt variabler och värden
# ---------------------------------------------------------------------------

BYGG_MONSTER = re.compile(
    r"byggverksamhet|byggindustri|bygg- och anl|construction", re.IGNORECASE)
BYGG_KODER = {"F", "41-43", "41+42+43", "45", "F, 41-43", "SNI41-43"}

REGION_MONSTER = re.compile(r"region|l[aä]n|kommun", re.IGNORECASE)


def hitta_variabel(variabler, monster, koder=None):
    """Returnerar (variabelkod, [matchande värdekoder]) eller None."""
    for v in variabler:
        koder_i_var = v.get("values") or v.get("valueCodes") or []
        texter = v.get("valueTexts") or v.get("valueLabels") or []
        traffar = []
        for kod, text in itertools.zip_longest(koder_i_var, texter, fillvalue=""):
            if koder and str(kod).strip() in koder:
                traffar.append(kod)
            elif monster and monster.search(str(text)):
                traffar.append(kod)
        if traffar:
            return v.get("code") or v.get("id"), traffar
    return None


def hittar_orebro(variabler):
    for v in variabler:
        kod = v.get("code") or v.get("id") or ""
        if not REGION_MONSTER.search(kod) and not REGION_MONSTER.search(v.get("text", "")):
            continue
        varden = [str(x) for x in (v.get("values") or v.get("valueCodes") or [])]
        if OREBRO in varden:
            return kod, [OREBRO]
        # kommunnivå: alla kommuner i Örebro län börjar på 18
        lans_kommuner = [x for x in varden if x.startswith("18") and len(x) == 4]
        if lans_kommuner:
            return kod, lans_kommuner
    return None


# ---------------------------------------------------------------------------
# API v1: navigera trädet
# ---------------------------------------------------------------------------

AMNEN = {
    "NR": re.compile(r"regionalr[aä]kenskap|input-output|tillg[aå]ng och anv", re.I),
    "AM": re.compile(r"registerbaserad|arbetsmarknadsstatistik|l[oö]nesumm|yrkesregist", re.I),
    "OE": re.compile(r"skatt|kommunal", re.I),
    "HE": re.compile(r"inkomst", re.I),
}


def v1_katalog():
    """Går igenom utvalda ämnesområden och returnerar kandidattabeller."""
    kandidater = []
    for amne, monster in AMNEN.items():
        try:
            mappar = json_hamta(f"{V1}/{amne}")
        except Exception as e:                               # noqa: BLE001
            print(f"  [{amne}] kunde inte läsas: {e}")
            continue
        traffade = [m for m in mappar if monster.search(m.get("text", ""))]
        print(f"  [{amne}] {len(mappar)} mappar, {len(traffade)} matchar sökprofilen")
        for m in traffade:
            sokvag = f"{V1}/{amne}/{m['id']}"
            try:
                noder = json_hamta(sokvag)
            except Exception as e:                           # noqa: BLE001
                print(f"    {m['id']}: {e}")
                continue
            # en nivå till om det är undermappar
            tabeller = [n for n in noder if n.get("type") == "t"]
            for under in [n for n in noder if n.get("type") == "l"]:
                try:
                    tabeller += [
                        dict(n, _under=under["id"])
                        for n in json_hamta(f"{sokvag}/{under['id']}")
                        if n.get("type") == "t"
                    ]
                except Exception:                            # noqa: BLE001
                    pass
            print(f"    {m['id']} ({m.get('text','')[:50]}): {len(tabeller)} tabeller")
            for t in tabeller:
                delar = [amne, m["id"]]
                if t.get("_under"):
                    delar.append(t["_under"])
                delar.append(t["id"])
                kandidater.append({
                    "id": t["id"],
                    "text": t.get("text", ""),
                    "uppdaterad": t.get("updated"),
                    "url": f"{V1}/" + "/".join(delar),
                    "amne": amne,
                })
    return kandidater


# ---------------------------------------------------------------------------
# Huvudflöde
# ---------------------------------------------------------------------------

def sakert_filnamn(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)[:90]


def main():
    os.makedirs(UTDATA, exist_ok=True)
    print("=" * 78)
    print("SCB-hämtning: byggsysselsättning och skatteunderlag i Örebro län")
    print("=" * 78)

    print("\n1. Letar kandidattabeller i statistikdatabasen (v1-trädet)")
    kandidater = v1_katalog()
    print(f"\n   {len(kandidater)} tabeller totalt i de valda ämnesområdena")

    print("\n2. Läser metadata och väljer ut relevanta tabeller")
    katalog, valda = [], []
    for k in kandidater:
        try:
            meta = json_hamta(k["url"])
        except Exception as e:                               # noqa: BLE001
            print(f"   {k['id']}: metadata misslyckades ({e})")
            continue
        variabler = meta.get("variables", [])
        post = dict(k, titel=meta.get("title", ""), variabler=[
            {
                "kod": v.get("code"),
                "text": v.get("text"),
                "antal_varden": len(v.get("values", [])),
                "exempel": list(zip(v.get("values", [])[:8], v.get("valueTexts", [])[:8])),
            }
            for v in variabler
        ])

        region = hittar_orebro(variabler)
        bygg = hitta_variabel(variabler, BYGG_MONSTER, BYGG_KODER)
        post["har_orebro"] = bool(region)
        post["har_bygg"] = bool(bygg)
        katalog.append(post)

        if region and bygg:
            valda.append((k, meta, region, bygg))
            print(f"   VALD  {k['id']:<28} {meta.get('title','')[:70]}")

    with open(os.path.join(UTDATA, "_katalog.json"), "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False, indent=1)
    print(f"\n   Skrev katalog över {len(katalog)} tabeller till data/scb/_katalog.json")
    print(f"   {len(valda)} tabeller har både Örebro län och byggverksamhet")

    print("\n3. Hämtar data för Örebro län")
    manifest = []
    for k, meta, (regvar, regvarden), (byggvar, byggvarden) in valda:
        fraga = [
            {"code": regvar, "selection": {"filter": "item", "values": regvarden}},
            {"code": byggvar, "selection": {"filter": "item", "values": byggvarden}},
        ]
        # alla år, alla mått
        for v in meta.get("variables", []):
            kod = v.get("code")
            if kod in (regvar, byggvar):
                continue
            if v.get("time") or kod in ("Tid", "ContentsCode"):
                fraga.append({"code": kod, "selection": {"filter": "all", "values": ["*"]}})
        try:
            csv_text = hamta(k["url"], {"query": fraga, "response": {"format": "csv"}})
        except Exception as e:                               # noqa: BLE001
            print(f"   {k['id']}: hämtning misslyckades ({e})")
            manifest.append({"id": k["id"], "status": f"fel: {e}"})
            continue
        namn = sakert_filnamn(f"{k['id']}_{meta.get('title','')[:40]}") + ".csv"
        with open(os.path.join(UTDATA, namn), "w", encoding="utf-8") as f:
            f.write(csv_text)
        rader = csv_text.count("\n")
        print(f"   OK    {namn}  ({rader} rader)")
        print("         " + "\n         ".join(csv_text.splitlines()[:4]))
        manifest.append({
            "id": k["id"], "titel": meta.get("title", ""), "fil": namn,
            "rader": rader, "url": k["url"],
            "regionvariabel": regvar, "branschvariabel": byggvar,
            "status": "ok",
        })

    with open(os.path.join(UTDATA, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    lyckade = sum(1 for m in manifest if m.get("status") == "ok")
    print(f"\nKLART: {lyckade} av {len(valda)} tabeller hämtade till data/scb/")
    if not lyckade:
        print("Inget hämtat - granska data/scb/_katalog.json och justera urvalet.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
