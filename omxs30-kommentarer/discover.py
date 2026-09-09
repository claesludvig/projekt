#!/usr/bin/env python3
"""Hittar vilka som faktiskt kommenterar OMXS30 - och hur ofta.

Metoden: Google News RSS soks pa ett antal OMXS30-fraser. Varje traff har en
utgivare och ett datum. Genom att rakna distinkta publiceringsdagar per utgivare
och jamfora med antalet borsdagar i fonstret far vi ett matt pa hur daglig
utgivaren faktiskt ar - i stallet for att gissa.

Resultatet ackumuleras i data/kommentatorer_historik.json, sa tackningen blir
battre for varje korning. data/kommentatorer.json ar den sammanraknade vyn.
"""

from __future__ import annotations

import argparse
import json

import urllib.parse
from collections import defaultdict
from datetime import date, timedelta

import feedparser

from common import (
    DATA_DIR,
    borsdagar,
    hamta,
    las_kallor,
    normalisera,
    nu_iso,
    parsa_datum,
    relevanspoang,
    skriv_json,
)

GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=sv&gl=SE&ceid=SE:sv"
HISTORIK = DATA_DIR / "kommentatorer_historik.json"


def sok(fras: str, dagar: int) -> list[dict]:
    q = urllib.parse.quote(f"{fras} when:{dagar}d")
    url = GOOGLE_NEWS.format(q=q)
    print(f"  Soker: {fras} (senaste {dagar} dagarna)")
    r = hamta(url, timeout=30.0)
    if not r:
        return []
    feed = feedparser.parse(r.content)
    traffar = []
    for e in feed.entries:
        titel = normalisera(e.get("title", ""))
        utgivare = ""
        if e.get("source"):
            utgivare = normalisera(getattr(e.source, "title", "") or e.source.get("title", ""))
        if not utgivare and " - " in titel:
            utgivare = titel.rsplit(" - ", 1)[1]
        # Google News lagger till " - Utgivare" sist i rubriken
        if utgivare and titel.endswith(f" - {utgivare}"):
            titel = titel[: -len(f" - {utgivare}")]
        datum = parsa_datum(e.get("published_parsed") or e.get("published", ""))
        if not utgivare or not datum:
            continue
        traffar.append(
            {
                "utgivare": utgivare,
                "datum": datum,
                "titel": titel,
                "lank": e.get("link", ""),
                "fras": fras,
                "relevans": relevanspoang(titel),
            }
        )
    print(f"    {len(traffar)} traffar")
    return traffar


def las_historik() -> dict:
    if HISTORIK.exists():
        try:
            return json.loads(HISTORIK.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"artiklar": {}}


def nyckel(t: dict) -> str:
    return f"{t['utgivare']}|{t['datum']}|{t['titel'][:120]}"


def bedom_kadens(andel: float) -> str:
    if andel >= 0.6:
        return "daglig"
    if andel >= 0.35:
        return "nastan daglig"
    if andel >= 0.12:
        return "veckovis"
    return "sporadisk"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dagar", type=int, default=30, help="Sokfonster i dagar (default 30)")
    p.add_argument("--min-relevans", type=int, default=3, help="Lagsta relevanspoang pa rubriken")
    args = p.parse_args()

    kallor = las_kallor()
    fraser = kallor.get("sokfrasor_google_news", ["OMXS30"])

    historik = las_historik()
    artiklar = historik.get("artiklar", {})
    nya = 0

    for fras in fraser:
        for t in sok(fras, args.dagar):
            if t["relevans"] < args.min_relevans:
                continue
            k = nyckel(t)
            if k not in artiklar:
                artiklar[k] = t
                nya += 1

    # Behall ett rullande fonster pa 180 dagar sa filen inte vaxer i all evighet
    grans = (date.today() - timedelta(days=180)).isoformat()
    artiklar = {k: v for k, v in artiklar.items() if v["datum"] >= grans}

    skriv_json("kommentatorer_historik.json", {"uppdaterad": nu_iso(), "artiklar": artiklar})

    # Sammanstall per utgivare
    per_utgivare: dict[str, dict] = defaultdict(
        lambda: {"antal": 0, "dagar": set(), "rubriker": [], "lankar": {}}
    )
    for t in artiklar.values():
        u = per_utgivare[t["utgivare"]]
        u["antal"] += 1
        u["dagar"].add(t["datum"])
        u["rubriker"].append({"datum": t["datum"], "titel": t["titel"], "lank": t["lank"]})

    if artiklar:
        alla_datum = sorted({t["datum"] for t in artiklar.values()})
        fran = date.fromisoformat(alla_datum[0])
        till = date.fromisoformat(alla_datum[-1])
    else:
        fran = till = date.today()
    mojliga = borsdagar(fran, till) or [date.today().isoformat()]

    lista = []
    for utgivare, u in per_utgivare.items():
        dagar = sorted(u["dagar"])
        andel = len([d for d in dagar if d in mojliga]) / len(mojliga)
        rubriker = sorted(u["rubriker"], key=lambda r: r["datum"], reverse=True)[:5]
        lista.append(
            {
                "utgivare": utgivare,
                "antal_artiklar": u["antal"],
                "distinkta_dagar": len(dagar),
                "andel_borsdagar": round(andel, 3),
                "kadens": bedom_kadens(andel),
                "senaste": dagar[-1] if dagar else "",
                "exempel": rubriker,
            }
        )

    lista.sort(key=lambda x: (-x["andel_borsdagar"], -x["antal_artiklar"]))

    ut = {
        "uppdaterad": nu_iso(),
        "fonster": {"fran": fran.isoformat(), "till": till.isoformat(), "borsdagar": len(mojliga)},
        "sokfrasor": fraser,
        "antal_artiklar": len(artiklar),
        "nya_denna_korning": nya,
        "kommentatorer": lista,
    }
    sokvag = skriv_json("kommentatorer.json", ut)

    print(f"\n{nya} nya artiklar, {len(artiklar)} totalt i fonstret.")
    print(f"Skrev {len(lista)} kommentatorer till {sokvag}\n")
    print(f"{'Utgivare':<38} {'art':>4} {'dagar':>6} {'andel':>6}  kadens")
    print("-" * 78)
    for k in lista[:25]:
        print(
            f"{k['utgivare'][:38]:<38} {k['antal_artiklar']:>4} {k['distinkta_dagar']:>6} "
            f"{k['andel_borsdagar']:>6.2f}  {k['kadens']}"
        )


if __name__ == "__main__":
    main()
