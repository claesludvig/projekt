#!/usr/bin/env python3
"""Hamtar dagens OMXS30-kommentarer fran kallorna i sources.json.

Skriver:
  data/latest_commentary.json  - alla hamtade texter med relevans och ton
  data/dagsvy.json             - per dag: antal kommentarer, tonfordelning, teman
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

import feedparser
from bs4 import BeautifulSoup

from common import (
    DATA_DIR,
    hamta,
    las_kallor,
    normalisera,
    nu_iso,
    parsa_datum,
    relevanspoang,
    ser_ut_som_flode,
    skriv_json,
    tonlage,
)

STATUS_PATH = DATA_DIR / "sources_status.json"

# Stoppord vid temautvinning
STOPP = set(
    """och att det som en av for i pa med den de har ar om men till inte var vi
    kan sa ett vid ur samt eller efter under mot fran nar mer mest ocksa
    the and for with that this from will has have was are its
    procent bolag aktier aktien index borsen marknaden""".split()
)


def kanda_urler() -> dict[str, dict]:
    if not STATUS_PATH.exists():
        return {}
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return {k["id"]: k for k in data.get("kallor", [])}


def flode_for(kalla: dict, status: dict) -> str | None:
    """Valjer forst en URL som check_sources.py redan bekraftat."""
    kand = status.get(kalla["id"], {})
    if kand.get("feed"):
        return kand["feed"]
    for url in kalla.get("feeds", []):
        r = hamta(url, timeout=20.0)
        if r and ser_ut_som_flode(r.text):
            return url
    return None


def poster_fran_flode(url: str, dagar: int) -> list[dict]:
    r = hamta(url, timeout=25.0)
    if not r:
        return []
    feed = feedparser.parse(r.content)
    grans = (date.today() - timedelta(days=dagar)).isoformat()
    poster = []
    for e in feed.entries:
        publicerad = parsa_datum(e.get("published_parsed") or e.get("published", ""))
        if publicerad and publicerad < grans:
            continue
        sammanfattning = normalisera(BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" "))
        poster.append(
            {
                "titel": normalisera(e.get("title", "")),
                "url": e.get("link", ""),
                "publicerad": publicerad,
                "sammanfattning": sammanfattning[:600],
                "forfattare": normalisera(e.get("author", "")),
            }
        )
    return poster


def poster_fran_listning(kalla: dict, status: dict) -> list[dict]:
    url = status.get(kalla["id"], {}).get("listning") or next(iter(kalla.get("listningar", [])), None)
    if not url:
        return []
    r = hamta(url, timeout=25.0)
    if not r:
        return []
    soup = BeautifulSoup(r.content, "html.parser")
    monster = kalla.get("lank_monster", "/")
    bas = re.match(r"https?://[^/]+", url)
    bas = bas.group(0) if bas else ""
    sedda, poster = set(), []
    for a in soup.find_all("a", href=True):
        titel = normalisera(a.get_text(" "))
        if len(titel) < 25 or monster not in a["href"]:
            continue
        lank = a["href"]
        if lank.startswith("/"):
            lank = bas + lank
        if not lank.startswith("http") or lank in sedda:
            continue
        sedda.add(lank)
        poster.append({"titel": titel, "url": lank, "publicerad": "", "sammanfattning": "", "forfattare": ""})
    return poster


def hamta_fulltext(url: str) -> tuple[str, str, str]:
    """Returnerar (fulltext, publicerad, forfattare) for en artikel-URL."""
    r = hamta(url, timeout=30.0)
    if not r:
        return "", "", ""
    soup = BeautifulSoup(r.content, "html.parser")

    publicerad = forfattare = ""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:  # noqa: BLE001
            continue
        for it in data if isinstance(data, list) else [data]:
            if not isinstance(it, dict):
                continue
            if "article" in str(it.get("@type", "")).lower() or it.get("datePublished"):
                publicerad = publicerad or (it.get("datePublished", "") or "")[:10]
                au = it.get("author")
                if isinstance(au, dict):
                    forfattare = forfattare or normalisera(au.get("name", ""))
                elif isinstance(au, list):
                    forfattare = forfattare or ", ".join(
                        normalisera(a.get("name", "")) for a in au if isinstance(a, dict)
                    )

    kropp = soup.find("article") or soup.find("main") or soup
    for skrap in kropp.find_all(["script", "style", "nav", "footer", "aside"]):
        skrap.decompose()
    stycken = [normalisera(b.get_text(" ")) for b in kropp.find_all(["p", "h2", "h3", "li"])]
    stycken = [s for s in stycken if len(s) > 30]
    return "\n".join(stycken), publicerad, forfattare


def teman(texter: list[str], antal: int = 12) -> list[list]:
    ord_ = Counter()
    for t in texter:
        for w in re.findall(r"[a-zA-ZåäöÅÄÖ]{4,}", (t or "").lower()):
            if w not in STOPP:
                ord_[w] += 1
    return [[w, n] for w, n in ord_.most_common(antal)]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dagar", type=int, default=3, help="Hur langt tillbaka poster racknas (default 3)")
    p.add_argument("--max-per-kalla", type=int, default=6)
    p.add_argument("--min-relevans", type=int, default=3)
    p.add_argument("--utan-fulltext", action="store_true", help="Hoppa over artikelhamtning")
    args = p.parse_args()

    kallor = las_kallor()
    status = kanda_urler()
    poster_ut, kallstatus = [], []

    for kalla in kallor["kallor"]:
        print(f"== {kalla['namn']} ==")
        flode = flode_for(kalla, status)
        if flode:
            rader = poster_fran_flode(flode, args.dagar)
            kalltyp = "feed"
        else:
            rader = poster_fran_listning(kalla, status)
            kalltyp = "listning"
        print(f"  {len(rader)} poster via {kalltyp}")

        relevanta = []
        for rad in rader:
            rad["relevans"] = relevanspoang(rad["titel"], rad["sammanfattning"])
            if rad["relevans"] >= args.min_relevans:
                relevanta.append(rad)
        relevanta.sort(key=lambda r: (-r["relevans"], r.get("publicerad", "")))
        relevanta = relevanta[: args.max_per_kalla]
        print(f"  {len(relevanta)} relevanta for OMXS30")

        for rad in relevanta:
            fulltext = ""
            if not args.utan_fulltext and rad["url"]:
                fulltext, pub, forf = hamta_fulltext(rad["url"])
                rad["publicerad"] = rad["publicerad"] or pub
                rad["forfattare"] = rad["forfattare"] or forf
            text = fulltext or rad["sammanfattning"]
            poster_ut.append(
                {
                    "kalla_id": kalla["id"],
                    "kalla": kalla["namn"],
                    "kalltyp": kalla.get("typ", ""),
                    "titel": rad["titel"],
                    "url": rad["url"],
                    "publicerad": rad["publicerad"],
                    "forfattare": rad["forfattare"],
                    "sammanfattning": rad["sammanfattning"],
                    "fulltext": text,
                    "ord": len(text.split()),
                    "relevans": relevanspoang(rad["titel"], text),
                    "ton": tonlage(text),
                }
            )
            print(f"    + {rad['titel'][:70]}")

        kallstatus.append(
            {
                "id": kalla["id"],
                "namn": kalla["namn"],
                "kadens": kalla.get("forvantad_kadens", ""),
                "hamtat_via": kalltyp if rader else "misslyckades",
                "antal_relevanta": len(relevanta),
            }
        )
        print()

    poster_ut.sort(key=lambda x: (x.get("publicerad", ""), x["relevans"]), reverse=True)
    skriv_json(
        "latest_commentary.json",
        {"hamtad": nu_iso(), "kallor": kallstatus, "kommentarer": poster_ut},
    )

    per_dag = defaultdict(list)
    for post in poster_ut:
        per_dag[post["publicerad"] or "okant"].append(post)

    dagsvy = []
    for dag in sorted(per_dag, reverse=True):
        poster = per_dag[dag]
        toner = Counter(p["ton"]["etikett"] for p in poster)
        dagsvy.append(
            {
                "datum": dag,
                "antal": len(poster),
                "kallor": sorted({p["kalla"] for p in poster}),
                "ton": {"positiv": toner["positiv"], "neutral": toner["neutral"], "negativ": toner["negativ"]},
                "teman": teman([p["fulltext"] for p in poster]),
                "rubriker": [{"kalla": p["kalla"], "titel": p["titel"], "url": p["url"]} for p in poster],
            }
        )
    skriv_json("dagsvy.json", {"uppdaterad": nu_iso(), "dagar": dagsvy})

    print(f"Totalt {len(poster_ut)} kommentarer fran {len({p['kalla_id'] for p in poster_ut})} kallor.")


if __name__ == "__main__":
    main()
