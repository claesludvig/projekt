#!/usr/bin/env python3
"""Hämtar senaste makro/FICC-rapporterna (fulltext) från SEB Research.

research.sebgroup.com är en JS-SPA (ren HTML-hämtning ger bara "Loading...").
Sidan anropar dock en öppen JSON-API under huven - mapi/v2/reports - som
fungerar med ett vanligt GET utan inloggning eller cookies. Vi hämtar de N
senaste rapporterna över alla kategorier (ingen reporttype-filtrering,
eftersom enskilda kategorier kan vara veckor/månader mellan inlägg) och
städar bort HTML ur brödtexten."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE = "https://research.sebgroup.com"
REPORTS_URL = f"{BASE}/mapi/v2/reports"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
MAX_REPORTS = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_reports(nbrows: int = MAX_REPORTS) -> list[dict]:
    r = httpx.get(REPORTS_URL, headers=HEADERS, params={"nbrows": nbrows}, timeout=30.0)
    r.raise_for_status()
    data = r.json()

    articles = []
    for rep in data.get("reports", []):
        fulltext = clean_html(rep.get("text", ""))
        if not fulltext:
            continue
        articles.append(
            {
                "url": f"{BASE}/macro-ficc/reports/{rep.get('articleId')}",
                "title": rep.get("title", "").strip(),
                "heading": rep.get("heading", "").strip(),
                "published": (rep.get("publishedDate") or "")[:10],
                "assetClass": rep.get("assetClass", []),
                "reportType": rep.get("reportType", ""),
                "fulltext": fulltext,
            }
        )
    return articles


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Hämtar de {MAX_REPORTS} senaste rapporterna från {REPORTS_URL} ...")
    articles = fetch_reports()
    articles.sort(key=lambda a: a.get("published", ""), reverse=True)

    for a in articles:
        print(f"  {a['published']} | {a['reportType']:<20} | {a['title']} ({len(a['fulltext'].split())} ord)")

    output_path = OUTPUT_DIR / "latest_articles.json"
    output_path.write_text(
        json.dumps(
            {"fetched_at": datetime.now(timezone.utc).isoformat(), "articles": articles},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSparade {len(articles)} rapporter till {output_path}")


if __name__ == "__main__":
    main()
