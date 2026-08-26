#!/usr/bin/env python3
"""Hämtar senaste FX- och räntor-artiklar (fulltext) från ING THINK.

Baserad på samma beprövade metod som ing_hamtare.py (RSS + listningssida,
metadata ur JSON-LD, brödtext ur <main>), men fristående utan
korpus_db/ramverk-beroenden: skriver bara till en JSON-fil.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup

BASE = "https://think.ing.com"
RSS = "https://think.ing.com/rss/"
LISTING_PAGES = {
    "FX": "https://think.ing.com/market/fx/",
    "Rates": "https://think.ing.com/market/rates/",
}
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
MAX_PER_CATEGORY = 6

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def normalize(url: str) -> str:
    url = url.split("?")[0].split("#")[0]
    if url.startswith("/"):
        url = BASE + url
    return url.rstrip("/") + "/"


def urls_from_rss(tag: str) -> list[str]:
    try:
        r = httpx.get(RSS, headers=HEADERS, follow_redirects=True, timeout=20.0)
        feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"  [!] RSS-fel: {e}")
        return []
    urls = []
    for entry in feed.entries:
        tags = [t.get("term", "").lower() for t in entry.get("tags", [])]
        if tag.lower() in tags and "/articles/" in entry.get("link", ""):
            urls.append(normalize(entry["link"]))
    return urls


def urls_from_listing(url: str) -> list[str]:
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=25.0)
        soup = BeautifulSoup(r.content, "html.parser")
    except Exception as e:
        print(f"  [!] Listnings-fel: {e}")
        return []
    urls = set()
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "/articles/" in h and not h.rstrip("/").endswith("articles"):
            urls.add(normalize(h))
    return sorted(urls)


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def fetch_article(url: str) -> dict | None:
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=30.0)
        r.raise_for_status()
    except Exception as e:
        print(f"    FEL {url}: {e}")
        return None

    soup = BeautifulSoup(r.content, "html.parser")

    title = published = author = ""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        for it in (data if isinstance(data, list) else [data]):
            if isinstance(it, dict) and "article" in str(it.get("@type", "")).lower():
                title = clean(it.get("headline", ""))
                published = (it.get("datePublished", "") or "")[:10]
                au = it.get("author")
                if isinstance(au, dict):
                    author = clean(au.get("name", ""))
                elif isinstance(au, list):
                    author = ", ".join(clean(a.get("name", "")) for a in au if isinstance(a, dict))
    if not title:
        h1 = soup.find("h1")
        title = clean(h1.get_text()) if h1 else url

    main = soup.find("main") or soup
    blocks = main.find_all(["p", "h2", "h3", "li"])
    texts = [clean(b.get_text(" ")) for b in blocks]
    texts = [t for t in texts if len(t) > 1]
    while texts and len(texts[0]) < 40 and "." not in texts[0]:
        texts.pop(0)
    fulltext = "\n".join(texts)

    return {"url": url, "title": title, "published": published, "author": author, "fulltext": fulltext}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_articles = []

    for category, listing_url in LISTING_PAGES.items():
        print(f"== {category} ==")
        urls = urls_from_rss(category.lower()) + urls_from_listing(listing_url)

        seen, unique_urls = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique_urls.append(u)
        unique_urls = unique_urls[:MAX_PER_CATEGORY]

        for u in unique_urls:
            print(f"  Hämtar: {u} ...", end=" ", flush=True)
            art = fetch_article(u)
            if not art or not art["fulltext"]:
                print("tom/fel")
                continue
            art["category"] = category
            all_articles.append(art)
            print(f"OK ({len(art['fulltext'].split())} ord)")

    all_articles.sort(key=lambda a: a.get("published", ""), reverse=True)

    output_path = OUTPUT_DIR / "latest_articles.json"
    output_path.write_text(
        json.dumps(
            {"fetched_at": datetime.now(timezone.utc).isoformat(), "articles": all_articles},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nSparade {len(all_articles)} artiklar till {output_path}")


if __name__ == "__main__":
    main()
