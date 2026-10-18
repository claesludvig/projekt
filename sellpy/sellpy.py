#!/usr/bin/env python3
"""Sellpy-sök och annonsbevakning.

Sellpys sajt söker via Algolia med en publik söknyckel (läsbehörighet, samma som
webbläsaren använder). Vi frågar samma index direkt och får då tillgång till all
strukturerad metadata: märke, typ, storlek, skick, färg, material, mått i cm,
pris och publiceringstid — och kan filtrera på allt det, vilket sajten själv inte
alltid låter en göra (t.ex. midjemått 80–86 cm eller innerbenslängd).

Användning:
  python sellpy.py sok "levis 501" --marke "Levi Strauss & Co" --matt waistInCm=80-86 --max-pris 300
  python sellpy.py facetter "levis 501"            # vilka värden finns att filtrera på
  python sellpy.py bevaka                          # kör alla sökningar i bevakningar.json

Bevakningen sparar sedda annonser i data/sedda.json och skriver nya träffar
(och prissänkningar på redan sedda) till data/nya.json och data/nya.md."""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BEVAKNINGAR = BASE_DIR / "bevakningar.json"
SEDDA = DATA_DIR / "sedda.json"
GLOM_EFTER_DAGAR = 30  # annonser som inte synts på så länge (sålda) rensas ur sedda.json

# Publik söknyckel från sellpy.se:s egen frontend-config (config.prod.*.bundle.js)
APP_ID = "M6WNFR0LVI"
SOK_NYCKEL = "313e09c3b00b6e2da5dbe382cd1c8f4b"
INDEX = {
    "nyast": "prod_marketItem_se_saleStartedAt_desc",
    "relevans": "prod_marketItem_se_relevance",
    "billigast": "prod_marketItem_se_price_asc",
    "dyrast": "prod_marketItem_se_price_desc_virtual",
}
ANNONS_URL = "https://www.sellpy.se/item/{}"

# Svenska filternamn -> Algolia-attribut (listor = ELLER inom filtret, OCH mellan filter)
FACETTER = {
    "marke": "metadata.brand",
    "typ": "metadata.type",
    "storlek": "metadata.size",
    "skick": "metadata.condition",
    "farg": "metadata.color",
    "material": "metadata.material",
    "monster": "metadata.pattern",
    "kon": "metadata.demography",
    "kategori": "searchableExternalCategory",
    "langd": "metadata.pantsLength",
    "midjehojd": "metadata.waistRise",
    "stil": "style",
}
# Mått i cm som går att filtrera numeriskt, se `facetter`
MATT = ["waistInCm", "innerLegLengthInCm", "lengthInCm", "widthInCm", "heightInCm", "heelHeightInCm"]


def algolia(index, params):
    req = urllib.request.Request(
        f"https://{APP_ID}-dsn.algolia.net/1/indexes/{index}/query",
        data=json.dumps(params).encode(),
        headers={
            "X-Algolia-Application-Id": APP_ID,
            "X-Algolia-API-Key": SOK_NYCKEL,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def bygg_params(s):
    """Översätter en sökning (dict med svenska nycklar) till Algolia-parametrar."""
    facet_filters = []
    for nyckel, attr in FACETTER.items():
        varden = s.get(nyckel)
        if not varden:
            continue
        if isinstance(varden, str):
            varden = [varden]
        facet_filters.append([f"{attr}:{v}" for v in varden])
    numeric = ["price_SE.amount>0"]  # utan pris = privat/osåld vara som inte går att köpa
    if s.get("min_pris") is not None:
        numeric.append(f"price_SE.amount>={int(s['min_pris'] * 100)}")
    if s.get("max_pris") is not None:
        numeric.append(f"price_SE.amount<={int(s['max_pris'] * 100)}")
    for namn, (lo, hi) in (s.get("matt") or {}).items():
        if lo is not None:
            numeric.append(f"metadata.measurement.{namn}>={lo}")
        if hi is not None:
            numeric.append(f"metadata.measurement.{namn}<={hi}")
    if s.get("dagar"):
        sedan = datetime.now(timezone.utc).timestamp() - s["dagar"] * 86400
        numeric.append(f"saleStartedAt>={int(sedan * 1000)}")
    params = {"query": s.get("fraga", ""), "facetFilters": facet_filters, "numericFilters": numeric}
    params.update(s.get("algolia") or {})  # fri utbyggnad för avancerade filter
    return params


def normalisera(hit):
    m = hit.get("metadata") or {}
    pris = (hit.get("price_SE") or {}).get("amount")
    farg = m.get("color") or []
    return {
        "id": hit["objectID"],
        "url": ANNONS_URL.format(hit["objectID"]),
        "titel": " ".join(str(x) for x in [m.get("brand"), m.get("type"), visa_storlek(m.get("size"))] if x),
        "marke": m.get("brand"),
        "modell": (m.get("model") or "").strip() or None,
        "typ": m.get("type"),
        "storlek": m.get("size"),
        "skick": m.get("condition"),
        "farg": ", ".join(farg) if isinstance(farg, list) else farg,
        "matt": m.get("measurement") or {},
        "defekter": [d.get("type") for d in m.get("defects") or [] if isinstance(d, dict)],
        "pris": pris / 100 if pris is not None else None,
        "publicerad": datetime.fromtimestamp(hit["saleStartedAt"] / 1000, timezone.utc).isoformat(timespec="minutes")
        if hit.get("saleStartedAt") else None,
        "reserverad": bool(hit.get("isReserved")),
        "favoriter": hit.get("favouriteCount"),
        "bild": (hit.get("images") or [None])[0],
    }


def visa_storlek(s):
    if not s:
        return None
    # "PANTS-INCH-32" -> "32", "WMN-INT-M" -> "M", "SHOES-EU-38" -> "38"
    return s.rsplit("-", 1)[-1] if "-" in s and s.upper() != s.lower() else s


def sok(s, antal=50):
    index = INDEX[s.get("sortering", "nyast")]
    params = bygg_params(s)
    params["hitsPerPage"] = min(antal, 1000)
    res = algolia(index, params)
    return res["nbHits"], [normalisera(h) for h in res["hits"]]


def facetter(s, max_varden=30):
    params = bygg_params(s)
    params.update({"hitsPerPage": 0, "facets": ["*"], "maxValuesPerFacet": max_varden})
    res = algolia(INDEX["relevans"], params)
    return res["nbHits"], res.get("facets", {}), res.get("facets_stats", {})


def rad(a, prefix=""):
    matt = ", ".join(f"{k.replace('InCm', '')} {v} cm" for k, v in a["matt"].items())
    delar = [f"{a['pris']:.0f} kr" if a["pris"] is not None else "?", a["titel"], a["skick"], a["farg"], matt]
    if a["modell"]:
        delar.insert(2, a["modell"])
    if a["reserverad"]:
        delar.append("RESERVERAD")
    return prefix + " | ".join(str(d) for d in delar if d) + f"\n    {a['url']}"


# --- Bevakning ---------------------------------------------------------------

def bevaka(bevakningar, sedda):
    """Kör alla bevakningar. Returnerar (nya, prissankta) per bevakning och uppdaterar `sedda`."""
    nu = datetime.now(timezone.utc).isoformat(timespec="minutes")
    resultat = []
    for b in bevakningar:
        if b.get("aktiv") is False:
            continue
        namn = b["namn"]
        forsta_korning = namn not in sedda
        tidigare = sedda.setdefault(namn, {})
        _, traffar = sok({**b, "sortering": "nyast"}, antal=b.get("max_traffar", 200))
        nya, sankta = [], []
        for a in traffar:
            gammal = tidigare.get(a["id"])
            if gammal is None:
                if not forsta_korning:  # första körningen bara registrerar, annars flod av "nya"
                    nya.append(a)
            elif a["pris"] is not None and gammal.get("pris") is not None and a["pris"] < gammal["pris"]:
                sankta.append({**a, "tidigare_pris": gammal["pris"]})
            # Datum (inte klockslag) som "senast", så filen bara ändras när något faktiskt hänt eller dygnet bytts
            tidigare[a["id"]] = {"pris": a["pris"], "sedd": (gammal or {}).get("sedd", nu), "senast": nu[:10]}
        grans = (datetime.now(timezone.utc) - timedelta(days=GLOM_EFTER_DAGAR)).date().isoformat()
        for id_ in [i for i, v in tidigare.items() if v.get("senast", nu) < grans]:
            del tidigare[id_]
        resultat.append({"namn": namn, "forsta_korning": forsta_korning, "antal_traffar": len(traffar),
                         "nya": nya, "prissankta": sankta})
    return resultat


def skriv_rapport(resultat):
    nu = datetime.now(timezone.utc).isoformat(timespec="minutes")
    (DATA_DIR / "nya.json").write_text(json.dumps({"kord": nu, "bevakningar": resultat},
                                                  ensure_ascii=False, indent=1))
    rader = [f"# Sellpy-bevakning {nu}", ""]
    for r in resultat:
        if r["forsta_korning"]:
            rader.append(f"## {r['namn']}: första körningen, {r['antal_traffar']} annonser registrerade")
            continue
        if not r["nya"] and not r["prissankta"]:
            continue
        rader.append(f"## {r['namn']}")
        for a in r["nya"]:
            rader.append(f"- **Ny:** [{a['titel']}]({a['url']}) — {a['pris']:.0f} kr, {a['skick']}"
                         + (f", {a['modell']}" if a["modell"] else ""))
        for a in r["prissankta"]:
            rader.append(f"- **Prissänkt:** [{a['titel']}]({a['url']}) — {a['tidigare_pris']:.0f} → {a['pris']:.0f} kr")
        rader.append("")
    (DATA_DIR / "nya.md").write_text("\n".join(rader) + "\n")


# --- CLI ----------------------------------------------------------------------

def sokning_fran_args(a):
    s = {"fraga": a.fraga or "", "sortering": a.sortera, "min_pris": a.min_pris, "max_pris": a.max_pris,
         "dagar": a.dagar}
    for nyckel in FACETTER:
        if getattr(a, nyckel, None):
            s[nyckel] = getattr(a, nyckel)
    matt = {}
    for m in a.matt or []:
        namn, _, intervall = m.partition("=")
        lo, _, hi = intervall.partition("-")
        matt[namn] = (float(lo) if lo else None, float(hi) if hi else None)
    s["matt"] = matt
    return s


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="kommando", required=True)
    for namn in ("sok", "facetter"):
        sp = sub.add_parser(namn)
        sp.add_argument("fraga", nargs="?")
        for nyckel in FACETTER:
            sp.add_argument(f"--{nyckel}", action="append", help=f"filtrerar på {FACETTER[nyckel]} (kan upprepas)")
        sp.add_argument("--min-pris", type=float)
        sp.add_argument("--max-pris", type=float)
        sp.add_argument("--matt", action="append", metavar="NAMN=MIN-MAX",
                        help=f"måttfilter i cm, t.ex. waistInCm=80-86 eller innerLegLengthInCm=82-. Namn: {', '.join(MATT)}")
        sp.add_argument("--dagar", type=float, help="bara annonser publicerade senaste N dagarna")
        sp.add_argument("--sortera", choices=list(INDEX), default="nyast")
        sp.add_argument("-n", "--antal", type=int, default=25)
        sp.add_argument("--json", action="store_true")
    bp = sub.add_parser("bevaka")
    bp.add_argument("--fil", type=Path, default=BEVAKNINGAR)
    a = p.parse_args()

    if a.kommando == "sok":
        total, traffar = sok(sokning_fran_args(a), a.antal)
        if a.json:
            print(json.dumps(traffar, ensure_ascii=False, indent=1))
        else:
            print(f"{total} träffar (visar {len(traffar)})\n")
            for t in traffar:
                print(rad(t))
    elif a.kommando == "facetter":
        total, f, stats = facetter(sokning_fran_args(a))
        print(f"{total} träffar\n")
        visa = {v: k for k, v in FACETTER.items()}
        for attr, varden in sorted(f.items()):
            if attr in visa:
                print(f"--{visa[attr]}  ({attr})")
                print("   " + ", ".join(f"{k} ({n})" for k, n in varden.items()))
        for attr, st in stats.items():
            if attr.startswith("metadata.measurement."):
                print(f"--matt {attr.split('.')[-1]}=…  min {st['min']}, max {st['max']}, snitt {st['avg']:.0f}")
    elif a.kommando == "bevaka":
        DATA_DIR.mkdir(exist_ok=True)
        bevakningar = json.loads(a.fil.read_text())
        sedda = json.loads(SEDDA.read_text()) if SEDDA.exists() else {}
        resultat = bevaka(bevakningar, sedda)
        SEDDA.write_text(json.dumps(sedda, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        skriv_rapport(resultat)
        for r in resultat:
            status = "första körningen" if r["forsta_korning"] else f"{len(r['nya'])} nya, {len(r['prissankta'])} prissänkta"
            print(f"{r['namn']}: {r['antal_traffar']} träffar, {status}")
            for t in r["nya"]:
                print(rad(t, "  NY  "))
            for t in r["prissankta"]:
                print(rad(t, f"  ↓ från {t['tidigare_pris']:.0f}  "))


if __name__ == "__main__":
    sys.exit(main())
