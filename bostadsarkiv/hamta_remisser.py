#!/usr/bin/env python3
"""Hämtar remissvar från regeringen.se.

Regeringen publicerar remisserna med varje remissinstans svar som egen PDF.
Här hämtas alla remisser inom politikområdet Bostäder och samhällsplanering,
plus de remisser inom Finansmarknad som gäller bolån, bostäder eller kredit.
Varje svar blir en rad i data/dokument.csv med doktyp "rem", remissinstansen
i kolumnen organ och fulltexten i data/text/rem/. Alla svar sparas, även
kommunernas och myndigheternas; aktörsgruppen sätts i bygg_db.py.

Äldre remissvar (före ca 2005) finns inte digitalt hos regeringen. För dem
används propositionernas redovisning av remissvaren (se aktorer.py).

    python hamta_remisser.py
"""

import argparse
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import hamta

RK = "https://www.regeringen.se"
OMRADEN = {1217: None, 1231: re.compile(r"bostad|bolån|amortering|hyr|bygg|fastighet|kredit|plan", re.I)}
MANADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september",
           "oktober", "november", "december"]


def lista_remisser():
    ut = {}
    for omrade, titelfilter in OMRADEN.items():
        sida = 1
        while True:
            r = hamta.hamta_url(
                f"{RK}/Filter/GetFilteredItems",
                params={"lang": "sv", "filterType": "Taxonomy", "filterByType": "FilterablePageBase",
                        "preFilteredCategories": 2099, "rootPageReference": 0, "page": sida,
                        "pageSize": 100, "displayLimited": "False",
                        "filteredPoliticalAreaCategories": omrade},
                headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"})
            d = r.json()
            poster = re.findall(r'href="(/remisser/[^"]+)"[^>]*>(.*?)</a>', d["Message"], re.S)
            for url, titel in poster:
                titel = html.unescape(re.sub(r"<[^>]+>|\s+", " ", titel)).strip()
                if titelfilter and not titelfilter.search(titel):
                    continue
                ut.setdefault(url, titel)
            if not poster or sida * 100 >= int(d.get("TotalCount") or 0):
                break
            sida += 1
        print(f"Område {omrade}: {len(ut)} remisser hittills", flush=True)
    return ut


def remiss_sida(url):
    r = hamta.hamta_url(RK + url)
    h = r.text
    m = re.search(r'<h1 id="h1id">\s*(.*?)\s*(?:<span class="h1-vignette">(.*?)</span>)?\s*</h1>', h, re.S)
    titel = html.unescape(re.sub(r"<[^>]+>|\s+", " ", m.group(1))).strip() if m else ""
    diarie = html.unescape(m.group(2)).replace("Diarienummer:", "").strip() if m and m.group(2) else ""
    t = re.search(r'<time datetime="(\d{1,2}) (\w+) (\d{4})"', h)
    datum = (f"{t.group(3)}-{MANADER.index(t.group(2).lower()) + 1:02d}-{int(t.group(1)):02d}"
             if t and t.group(2).lower() in MANADER else "")
    svar = []
    for href, namn in re.findall(r'<a[^>]+href="([^"]+\.pdf)"[^>]*>(.*?)</a>', h, re.S):
        namn = html.unescape(re.sub(r"<[^>]+>|\s+", " ", namn)).strip()
        namn = re.sub(r"\s*\((?:pdf|PDF)[^)]*\)\s*$", "", namn)
        if re.search(r"remissmissiv|remisslista|missiv|sändlista", namn, re.I):
            continue
        svar.append((namn, href if href.startswith("http") else RK + href))
    return titel, diarie, datum, svar


def bearbeta_svar(d):
    meta = {"id": d["id"], "doktyp": "rem", "beteckning": f"Remissvar {d['diarie'] or d['remiss'][:40]}",
            "rm": d["datum"][:4], "nummer": "", "datum": d["datum"],
            "titel": f"{d['organ']} om {d['remiss']}", "organ": d["organ"],
            "url": d["sida"], "pdf_url": d["pdf"]}
    t = hamta.pdf_text(d["pdf"])
    rad = hamta.bedom_dokument(meta, t, "regeringen")
    # Alla svar på en bostadsremiss sparas, även de som inte nämner kärntermerna.
    if not rad["relevant"] and t.strip():
        rad["relevant"] = 1
        rad["grad"] = "låg"
        rad["textfil"] = f"text/rem/{hamta.filnamn(meta['id'])}.txt.gz"
        hamta.skriv_text(rad["textfil"], f"{meta['beteckning']}\n{meta['titel']}\nKälla: {meta['url']}\n"
                                         f"Datum: {meta['datum']}\n\n" + t)
    return rad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arbetare", type=int, default=4)
    ap.add_argument("--grans", type=int)
    a = ap.parse_args()
    klara = {r["id"] for r in hamta.las_csv(hamta.DOK_CSV)}
    remisser = lista_remisser()
    print(f"{len(remisser)} remisser", flush=True)
    att_gora = []
    for i, (url, listtitel) in enumerate(remisser.items(), 1):
        try:
            titel, diarie, datum, svar = remiss_sida(url)
        except Exception as e:
            hamta.notera_fel(f"remiss {url}", e)
            continue
        for organ, pdf in svar:
            rid = "REM-" + hamta.filnamn(url.strip("/").split("/")[-1])[:60] + "-" + hamta.filnamn(organ)[:50]
            if rid in klara:
                continue
            att_gora.append({"id": rid, "remiss": titel or listtitel, "diarie": diarie, "datum": datum,
                             "organ": organ, "pdf": pdf, "sida": RK + url})
        if i % 20 == 0:
            print(f"  {i}/{len(remisser)} remissidor, {len(att_gora)} svar att hämta", flush=True)
        time.sleep(0.3)
    if a.grans:
        att_gora = att_gora[:a.grans]
    print(f"{len(att_gora)} remissvar att hämta", flush=True)
    hamta.kor_dokument(att_gora, bearbeta_svar, a.arbetare, "remissvar", lambda d: d["id"])
    print("Klart.", hamta.logg["antal"])


if __name__ == "__main__":
    main()
