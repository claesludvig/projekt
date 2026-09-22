#!/usr/bin/env python3
"""
Hamtar de serier analysen vilar pa fran SCB:s statistikdatabas (PxWeb API v2).

Kors dar api.scb.se ar natverksmassigt oppen. I den har sessionen var domanen
blockerad av egress-policyn, sa parametrarna i parametrar.py ar kalibrerade
skattningar - kor det har skriptet for att ersatta dem med faktiska varden.

Anvandning
----------
  python3 hamta_scb.py sok "regionalrakenskaper sysselsatta"
  python3 hamta_scb.py meta TAB0001
  python3 hamta_scb.py data TAB0001 --valuecodes Region=18 Tid=2015,2016,2017 \
        --out data/sysselsatta.csv
  python3 hamta_scb.py allt          # kor de fordefinierade hamtningarna

Tabell-id:n i SCB:s nya API ar inte stabila over tid. Darfor ar `sok` forsta
steget: leta upp tabellen, verifiera med `meta`, hamta med `data`.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

BAS = "https://api.scb.se/ov0104/v2beta/api/v2"
BAS_V1 = "https://api.scb.se/OV0104/v1/doris/sv/ssd"
OREBRO_LAN = "18"

# Serier analysen behover. Sokstrangarna ar valda for att traffa ratt tabell
# i statistikdatabasen; verifiera alltid med `meta` innan `data`.
SERIER = {
    "syss_bransch_lan": {
        "sok": "regionalrakenskaper sysselsatta bransch lan",
        "kommentar": "NR0105. Sysselsatta (dagbefolkning) per lan och bransch, "
                     "SNI 41-43 = byggverksamhet. Ger direkt effekt.",
    },
    "lonesumma_bransch_lan": {
        "sok": "regionalrakenskaper lonesummor bransch lan",
        "kommentar": "NR0105. Lonesumma per lan och bransch. Ger skatteunderlags"
                     "effekten utan antagande om genomsnittslon.",
    },
    "brp_bransch_lan": {
        "sok": "bruttoregionprodukt BRP bransch lan",
        "kommentar": "NR0105. Foradlingsvarde per lan och bransch - underlag "
                     "for location quotients i FLQ-regionaliseringen.",
    },
    "rams_forvarvsarbetande": {
        "sok": "forvarvsarbetande dagbefolkning naringsgren kommun",
        "kommentar": "RAMS/BAS. Langre serie an NR, kommunnedbruten.",
    },
    "skatteunderlag_kommun": {
        "sok": "skatteunderlag kommun skattekraft",
        "kommentar": "Kommunalt skatteunderlag per kommun - for att satta "
                     "bortfallet i relation till faktisk bas.",
    },
    "io_tabeller": {
        "sok": "input-output tabeller produktgrupper",
        "kommentar": "NR0117. Symmetriska I/O-tabeller, nationella. Ligger ofta "
                     "som xlsx pa scb.se snarare an i API:et.",
    },
}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "orebro-byggkonjunktur/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def sok(query, page_size=20):
    q = urllib.parse.urlencode({"lang": "sv", "query": query, "pageSize": page_size})
    data = json.loads(_get(f"{BAS}/tables?{q}"))
    for t in data.get("tables", []):
        period = f'{t.get("firstPeriod", "?")}-{t.get("lastPeriod", "?")}'
        print(f'{t.get("id", "?"):<16} {period:<14} {t.get("label", "")}')
    if not data.get("tables"):
        print("(inga traffar)", file=sys.stderr)


def meta(table_id):
    data = json.loads(_get(f"{BAS}/tables/{table_id}/metadata?lang=sv"))
    print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])


def hamta(table_id, valuecodes, out=None, fmt="csv"):
    params = [("lang", "sv"), ("outputFormat", fmt)]
    for spec in valuecodes:
        var, _, vals = spec.partition("=")
        for v in vals.split(","):
            params.append((f"valueCodes[{var}]", v))
    url = f"{BAS}/tables/{table_id}/data?{urllib.parse.urlencode(params)}"
    body = _get(url)
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"Skrev {out} ({len(body)} tecken)", file=sys.stderr)
    else:
        print(body)


def allt():
    """Kor sokningen for varje serie sa att ratt tabell-id kan plockas ut."""
    for namn, s in SERIER.items():
        print(f"\n### {namn}\n# {s['kommentar']}")
        try:
            sok(s["sok"], page_size=8)
        except Exception as e:                      # noqa: BLE001
            print(f"  FEL: {e}", file=sys.stderr)
    print("\nValj tabell-id ovan, kor `meta <id>` och sedan `data <id> "
          f"--valuecodes Region={OREBRO_LAN} ...`")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sok"); p.add_argument("query"); p.add_argument("--n", type=int, default=20)
    p = sub.add_parser("meta"); p.add_argument("table_id")
    p = sub.add_parser("data")
    p.add_argument("table_id")
    p.add_argument("--valuecodes", nargs="+", default=[], metavar="VAR=V1,V2")
    p.add_argument("--out")
    p.add_argument("--format", default="csv")
    sub.add_parser("allt")

    a = ap.parse_args()
    if a.cmd == "sok":
        sok(a.query, a.n)
    elif a.cmd == "meta":
        meta(a.table_id)
    elif a.cmd == "data":
        hamta(a.table_id, a.valuecodes, a.out, a.format)
    elif a.cmd == "allt":
        allt()


if __name__ == "__main__":
    main()
