#!/usr/bin/env python3
"""Provar alla kandidat-URL:er i sources.json och rapporterar vilka som lever.

Kors i GitHub Actions (dar natet ar oppet). Resultatet hamnar i
data/sources_status.json och anvands av collect.py for att slippa prova om
doda URL:er varje gang.
"""

from __future__ import annotations

import feedparser

from common import hamta, las_kallor, nu_iso, ser_ut_som_flode, skriv_json


def prova_flode(url: str) -> dict:
    r = hamta(url, timeout=20.0)
    if r is None:
        return {"url": url, "ok": False, "orsak": "kunde inte hamtas"}
    text = r.text
    if not ser_ut_som_flode(text):
        return {"url": url, "ok": False, "orsak": f"inte ett flode (status {r.status_code})"}
    feed = feedparser.parse(r.content)
    antal = len(feed.entries)
    if antal == 0:
        return {"url": url, "ok": False, "orsak": "tomt flode"}
    return {
        "url": url,
        "ok": True,
        "antal_poster": antal,
        "flodestitel": feed.feed.get("title", ""),
        "senaste_rubrik": feed.entries[0].get("title", ""),
    }


def prova_sida(url: str) -> dict:
    r = hamta(url, timeout=25.0)
    if r is None:
        return {"url": url, "ok": False, "orsak": "kunde inte hamtas"}
    return {"url": url, "ok": True, "status": r.status_code, "bytes": len(r.content)}


def main() -> None:
    kallor = las_kallor()
    resultat = []

    for kalla in kallor["kallor"]:
        print(f"== {kalla['namn']} ==")
        post = {"id": kalla["id"], "namn": kalla["namn"], "feed": None, "listning": None, "prov": []}

        for url in kalla.get("feeds", []):
            p = prova_flode(url)
            post["prov"].append({"typ": "feed", **p})
            status = "OK" if p["ok"] else p.get("orsak", "fel")
            print(f"  feed  {url} -> {status}")
            if p["ok"] and post["feed"] is None:
                post["feed"] = url

        if post["feed"] is None:
            for url in kalla.get("listningar", []):
                p = prova_sida(url)
                post["prov"].append({"typ": "listning", **p})
                print(f"  sida  {url} -> {'OK' if p['ok'] else p.get('orsak')}")
                if p["ok"] and post["listning"] is None:
                    post["listning"] = url

        post["anvandbar"] = bool(post["feed"] or post["listning"])
        resultat.append(post)
        print()

    sokvag = skriv_json("sources_status.json", {"kontrollerad": nu_iso(), "kallor": resultat})

    levande = [r for r in resultat if r["anvandbar"]]
    print(f"Skrev {sokvag}")
    print(f"\nSAMMANFATTNING: {len(levande)}/{len(resultat)} kallor anvandbara")
    for r in resultat:
        markering = "OK  " if r["anvandbar"] else "DOD "
        via = r["feed"] or r["listning"] or "-"
        print(f"  {markering} {r['namn'][:44]:<44} {via}")


if __name__ == "__main__":
    main()
