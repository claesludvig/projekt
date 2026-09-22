#!/usr/bin/env python3
"""Bevakar Sellpy efter plagg som matchar ett filter och rapporterar nya träffar.

Sellpys sidor är en JavaScript-app: filter och träfflistor renderas i webbläsaren
och finns inte i sidkällan. Skriptet kör därför en riktig Chromium via Playwright,
scrollar fram träffarna och plockar produkterna ur de JSON-svar sidan hämtar —
inte ur DOM:en, vars klassnamn är genererade och byts vid varje release.

Bruk:
    python sellpy_bevakning.py --marke Uniqlo --storlek M --maxpris 50 --uteslut hoodie
    python sellpy_bevakning.py --url "<url kopierad ur Sellpys egna filter>"
    python sellpy_bevakning.py --url "..." --intervall 30 --kommando "notify-send {antal}"
    python sellpy_bevakning.py --url "..." --inspect
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

BASE = "https://www.sellpy.se"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
SEDDA_FIL = OUTPUT_DIR / "sedda.json"
INSPEKT_DIR = OUTPUT_DIR / "inspekt"

# Sellpys klassnamn är genererade, men JSON-svaren har läsbara nycklar. Vilka
# exakt vet vi inte i förväg, så en produkt känns igen på formen: något pris
# plus något namn. Listorna är gissningar i fallande sannolikhet.
PRIS_NYCKLAR = ("price", "pris", "currentprice", "saleprice", "priceamount", "amount")
NAMN_NYCKLAR = ("title", "titel", "name", "namn", "label", "productname", "description")
MARKE_NYCKLAR = ("brand", "brandname", "marke", "märke", "manufacturer")
STORLEK_NYCKLAR = ("size", "storlek", "sizename", "sizelabel", "sizes")
MONSTER_NYCKLAR = ("pattern", "monster", "mönster", "print")
FARG_NYCKLAR = ("color", "colour", "farg", "färg")
KATEGORI_NYCKLAR = ("category", "kategori", "producttype", "type", "garmenttype")
ID_NYCKLAR = ("objectid", "itemid", "articleid", "id", "_id", "uuid", "slug")
URL_NYCKLAR = ("url", "link", "permalink", "href", "slug", "path")

# "M" i ett fält kan stå som "Medium". Jämför på normaliserad form.
STORLEK_SYNONYMER = {
    "XS": {"XS", "XSMALL", "EXTRASMALL"},
    "S": {"S", "SMALL"},
    "M": {"M", "MEDIUM"},
    "L": {"L", "LARGE"},
    "XL": {"XL", "XLARGE", "EXTRALARGE"},
}

# Mönstrade plagg. Används bara när produkten saknar eget mönsterfält.
MONSTRADE_ORD = (
    "randig", "randigt", "rutig", "rutigt", "mönstrad", "mönstrat", "blommig",
    "blommigt", "prickig", "prickigt", "tryck", "print", "grafisk", "logga",
    "paisley", "leopard", "kamouflage", "batik", "tie-dye", "flerfärgad",
)
ENFARGAT_ORD = ("enfärgad", "enfärgat", "enfarg", "solid", "unicolor")


def text_av(v) -> str:
    """Plattar ut ett värde till text. Fälten är ibland dict eller lista."""
    if v is None or isinstance(v, bool):
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        low = {k.lower(): x for k, x in v.items() if isinstance(k, str)}
        for n in ("name", "title", "label", "value", "sv", "text", "namn"):
            if n in low:
                return text_av(low[n])
        return ""
    if isinstance(v, list):
        delar = [t for t in (text_av(x) for x in v) if t]
        return ", ".join(delar)
    return ""


def low_nycklar(d: dict) -> dict:
    return {k.lower(): v for k, v in d.items() if isinstance(k, str)}


def plocka(d: dict, nycklar: tuple[str, ...]) -> str:
    low = low_nycklar(d)
    for n in nycklar:
        if n in low:
            t = text_av(low[n])
            if t:
                return t
    return ""


def plocka_pris(d: dict) -> float | None:
    low = low_nycklar(d)
    for n in PRIS_NYCKLAR:
        if n not in low:
            continue
        v = low[n]
        if isinstance(v, dict):
            inre = low_nycklar(v)
            v = inre.get("amount", inre.get("value", inre.get("current")))
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r"\d[\d\s.,]*", v)
            if m:
                rensat = m.group().replace(" ", "").replace("\xa0", "").replace(",", ".")
                try:
                    return float(rensat)
                except ValueError:
                    continue
    return None


def ser_ut_som_produkt(d: dict) -> bool:
    if plocka_pris(d) is None:
        return False
    return bool(plocka(d, NAMN_NYCKLAR) or plocka(d, MARKE_NYCKLAR))


def samla_produkter(node, ut: list) -> None:
    """Går igenom ett JSON-träd och lägger undan allt som ser ut som en produkt."""
    if isinstance(node, dict):
        if ser_ut_som_produkt(node):
            ut.append(node)
            return  # gräv inte vidare i en träff: varianter blir annars dubbletter
        for v in node.values():
            samla_produkter(v, ut)
    elif isinstance(node, list):
        for v in node:
            samla_produkter(v, ut)


def bygg_url(d: dict) -> str:
    low = low_nycklar(d)
    for n in URL_NYCKLAR:
        if n not in low:
            continue
        t = text_av(low[n])
        if not t or " " in t:
            continue
        if t.startswith("http"):
            return t
        if t.startswith("/"):
            return BASE + t
        if n in ("slug", "path"):
            return f"{BASE}/item/{t}"
    return ""


def normalisera(rå: dict) -> dict:
    return {
        "id": plocka(rå, ID_NYCKLAR),
        "namn": plocka(rå, NAMN_NYCKLAR),
        "marke": plocka(rå, MARKE_NYCKLAR),
        "storlek": plocka(rå, STORLEK_NYCKLAR),
        "monster": plocka(rå, MONSTER_NYCKLAR),
        "farg": plocka(rå, FARG_NYCKLAR),
        "kategori": plocka(rå, KATEGORI_NYCKLAR),
        "rapris": plocka_pris(rå),
        "url": bygg_url(rå),
    }


def nyckel(p: dict) -> str:
    return p["id"] or f"{p['marke']}|{p['namn']}|{p['storlek']}|{p['rapris']}"


def gissa_prisenhet(priser: list[float]) -> str:
    """Sellpy kan rapportera pris i kronor eller i ören. Gissa på fördelningen."""
    riktiga = [p for p in priser if p > 0]
    if not riktiga:
        return "kr"
    hela_hundratal = sum(1 for p in riktiga if p % 100 == 0) / len(riktiga)
    if hela_hundratal > 0.8 and median(riktiga) >= 1000:
        return "ore"
    return "kr"


def matchar_storlek(p: dict, önskad: str) -> bool:
    if not önskad:
        return True
    fältet = re.sub(r"[^A-Za-zÅÄÖåäö0-9,/ ]", "", p["storlek"]).upper()
    if not fältet:
        return False
    varianter = STORLEK_SYNONYMER.get(önskad.upper(), {önskad.upper()})
    delar = {d.strip().replace(" ", "") for d in re.split(r"[,/]", fältet)}
    return bool(delar & varianter)


def monsterstatus(p: dict) -> str:
    """'enfärgat', 'mönstrat' eller 'okänt' — det sista när data saknas."""
    fält = p["monster"].lower()
    if fält:
        if any(o in fält for o in ENFARGAT_ORD):
            return "enfärgat"
        if any(o in fält for o in MONSTRADE_ORD):
            return "mönstrat"
    text = f"{p['namn']} {p['farg']}".lower()
    if any(o in text for o in MONSTRADE_ORD):
        return "mönstrat"
    if any(o in text for o in ENFARGAT_ORD):
        return "enfärgat"
    return "okänt"


def filtrera(produkter: list[dict], args) -> list[dict]:
    uteslut = [o.lower() for o in args.uteslut]
    kvar = []
    for p in produkter:
        if args.marke and args.marke.lower() not in f"{p['marke']} {p['namn']}".lower():
            continue
        if not matchar_storlek(p, args.storlek):
            continue
        if args.maxpris is not None and (p["pris"] is None or p["pris"] > args.maxpris):
            continue
        text = f"{p['namn']} {p['kategori']}".lower()
        if any(o in text for o in uteslut):
            continue
        # Mönster är den svagaste signalen i datat. Fäll bara det som är
        # bevisat mönstrat — 'okänt' får följa med och märks i utskriften.
        if args.enfargat and monsterstatus(p) == "mönstrat":
            continue
        kvar.append(p)
    return kvar


def spara_inspektion(fångade: list[tuple[str, object]]) -> Path:
    INSPEKT_DIR.mkdir(parents=True, exist_ok=True)
    stämpel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fil = INSPEKT_DIR / f"svar-{stämpel}.json"
    fil.write_text(
        json.dumps(
            [{"url": u, "data": d} for u, d in fångade], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return fil


def hämta(url: str, args) -> tuple[list[dict], list[tuple[str, object]]]:
    """Öppnar sidan, scrollar fram allt och returnerar produkter + råa svar."""
    fångade: list[tuple[str, object]] = []
    råa: list[dict] = []

    def på_svar(svar):
        typ = (svar.headers or {}).get("content-type", "")
        if "json" not in typ.lower():
            return
        try:
            data = svar.json()
        except Exception:
            return
        fångade.append((svar.url, data))
        samla_produkter(data, råa)

    with sync_playwright() as pw:
        start = {"headless": not args.synlig}
        if args.chromium:
            start["executable_path"] = args.chromium
        webbläsare = pw.chromium.launch(**start)
        sida = webbläsare.new_context(
            locale="sv-SE",
            viewport={"width": 1400, "height": 1000},
        ).new_page()
        # Bilder och typsnitt behövs inte och belastar bara Sellpy i onödan.
        sida.route(
            re.compile(r"\.(png|jpe?g|webp|gif|svg|woff2?|mp4)($|\?)"),
            lambda rutt: rutt.abort(),
        )
        sida.on("response", på_svar)

        print(f"  Öppnar {url}")
        try:
            sida.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except PlaywrightTimeout:
            print("  [!] Sidan svarade inte i tid")
            webbläsare.close()
            return [], fångade

        # Cookie-rutan lägger sig över listan och stoppar scrollningen.
        for text in ("Godkänn alla", "Acceptera alla", "Godkänn", "Acceptera"):
            try:
                sida.get_by_role("button", name=text, exact=False).first.click(timeout=2500)
                break
            except Exception:
                continue

        sida.wait_for_timeout(2500)

        stillastående = 0
        for varv in range(args.max_scroll):
            innan = len(råa)
            try:
                knapp = sida.get_by_role(
                    "button", name=re.compile(r"visa fler|ladda fler|fler produkter", re.I)
                ).first
                knapp.click(timeout=1500)
            except Exception:
                sida.mouse.wheel(0, 25_000)
            sida.wait_for_timeout(args.paus)
            if len(råa) == innan:
                stillastående += 1
                if stillastående >= 3:
                    break
            else:
                stillastående = 0
                print(f"  scroll {varv + 1}: {len(råa)} produkter i JSON-svaren")

        webbläsare.close()

    return råa, fångade


def kör_en_gång(args) -> list[dict]:
    url = args.url or f"{BASE}/store/brand/{(args.marke or '').lower()}"
    råa, fångade = hämta(url, args)

    if args.inspect:
        fil = spara_inspektion(fångade)
        print(f"\n  {len(fångade)} JSON-svar sparade i {fil}")
        print(f"  {len(råa)} objekt såg ut som produkter. Första:")
        if råa:
            print(json.dumps(råa[0], ensure_ascii=False, indent=2)[:2000])
        return []

    if not råa:
        print("\n  [!] Inga produkter hittades i svaren.")
        print("      Kör om med --inspect och titta i dumpen: antingen laddades")
        print("      inget (fel url) eller så ser produkterna inte ut som skriptet tror.")
        return []

    produkter = {}
    for rå in råa:
        p = normalisera(rå)
        produkter[nyckel(p)] = p
    produkter = list(produkter.values())

    enhet = args.prisenhet
    if enhet == "auto":
        enhet = gissa_prisenhet([p["rapris"] for p in produkter if p["rapris"]])
        print(f"\n  Tolkar priserna som {'ören' if enhet == 'ore' else 'kronor'} "
              f"(styr med --prisenhet kr|ore om det blev fel)")
    for p in produkter:
        p["pris"] = None if p["rapris"] is None else (
            p["rapris"] / 100 if enhet == "ore" else p["rapris"]
        )

    träffar = sorted(filtrera(produkter, args), key=lambda p: p["pris"] or 0)
    print(f"  {len(produkter)} produkter lästa, {len(träffar)} matchar filtret")
    return träffar


def läs_sedda() -> dict:
    if SEDDA_FIL.exists():
        try:
            return json.loads(SEDDA_FIL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  [!] sedda.json gick inte att läsa, börjar om")
    return {}


def skriv_sedda(sedda: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SEDDA_FIL.write_text(json.dumps(sedda, ensure_ascii=False, indent=2), encoding="utf-8")


def rapportera(träffar: list[dict], sedda: dict) -> list[dict]:
    nya = [p for p in träffar if nyckel(p) not in sedda]
    if not träffar:
        print("\n  Inga träffar den här gången.")
        return nya

    print()
    print(f"  {'':3} {'PRIS':>7}  {'STRL':<6} {'MÄRKE':<14} {'MÖNSTER':<9} NAMN")
    print(f"  {'-' * 78}")
    nya_nycklar = {nyckel(n) for n in nya}
    for p in träffar:
        märk = "NY " if nyckel(p) in nya_nycklar else "   "
        pris = f"{p['pris']:.0f} kr" if p["pris"] is not None else "?"
        print(
            f"  {märk} {pris:>7}  {p['storlek'][:6]:<6} {p['marke'][:14]:<14} "
            f"{monsterstatus(p):<9} {p['namn'][:40]}"
        )
        if p["url"]:
            print(f"      {p['url']}")
    print()
    if nya:
        print(f"  {len(nya)} nya sedan förra körningen.")
        sys.stdout.write("\a")
    return nya


def main() -> None:
    p = argparse.ArgumentParser(
        description="Bevakar Sellpy efter plagg som matchar ett filter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Säkrast: bygg filtret i Sellpys egna gränssnitt, kopiera adressen\n"
            "ur webbläsaren och skicka in den med --url. Då slipper skriptet\n"
            "gissa hur Sellpy kodar sina filter i adressen."
        ),
    )
    p.add_argument("--url", help="Färdig Sellpy-adress med filter redan satta")
    p.add_argument("--marke", default="", help="Märke, t.ex. Uniqlo")
    p.add_argument("--storlek", default="", help="Storlek, t.ex. M")
    p.add_argument("--maxpris", type=float, help="Högsta pris i kronor")
    p.add_argument(
        "--uteslut", nargs="*", default=[],
        help="Ord som diskvalificerar ett plagg, t.ex. hoodie huvtröja",
    )
    p.add_argument(
        "--enfargat", action="store_true",
        help="Fäll bort plagg som är bevisat mönstrade (okänt mönster får följa med)",
    )
    p.add_argument(
        "--prisenhet", choices=("auto", "kr", "ore"), default="auto",
        help="Hur priserna i Sellpys JSON ska tolkas (standard: gissa)",
    )
    p.add_argument("--intervall", type=int, help="Kör om var N:e minut i stället för en gång")
    p.add_argument(
        "--kommando",
        help="Skalkommando vid nya träffar. {antal} och {första} byts ut.",
    )
    p.add_argument("--max-scroll", type=int, default=25, help="Högsta antal scroll-varv")
    p.add_argument("--paus", type=int, default=1800, help="Paus mellan scroll i ms")
    p.add_argument("--synlig", action="store_true", help="Visa webbläsarfönstret")
    p.add_argument(
        "--chromium", default=os.environ.get("SELLPY_CHROMIUM"),
        help="Sökväg till en egen Chromium. Standard: den Playwright installerat.",
    )
    p.add_argument("--inspect", action="store_true", help="Dumpa råa JSON-svar och avsluta")
    args = p.parse_args()

    if not args.url and not args.marke:
        p.error("ange --url eller --marke")

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Hämtar från Sellpy")
        träffar = kör_en_gång(args)

        if not args.inspect:
            sedda = läs_sedda()
            nya = rapportera(träffar, sedda)
            nu = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for t in träffar:
                sedda.setdefault(nyckel(t), nu)
            skriv_sedda(sedda)

            if nya and args.kommando:
                kmd = args.kommando.format(
                    antal=len(nya), första=nya[0]["namn"] or nya[0]["url"]
                )
                subprocess.run(kmd, shell=True, check=False)

        if not args.intervall:
            break
        print(f"  Väntar {args.intervall} min\n")
        time.sleep(args.intervall * 60)


if __name__ == "__main__":
    main()
