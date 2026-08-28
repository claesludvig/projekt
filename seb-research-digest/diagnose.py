#!/usr/bin/env python3
"""Engångsskript: undersöker hur research.sebgroup.com/macro-ficc faktiskt
är uppbyggd (RSS? JSON-LD? artikellänkar? paywall?) innan vi bygger en
riktig scraper. Sandboxens nätverksproxy blockerar sebgroup.com helt, så
detta måste köras via GitHub Actions och inspekteras i job-loggen -
samma mönster som för ING THINK."""

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

CANDIDATE_URLS = [
    "https://research.sebgroup.com/macro-ficc",
    "https://research.sebgroup.com/",
    "https://research.sebgroup.com/rss",
    "https://research.sebgroup.com/feed",
]


def dump(url: str) -> None:
    print(f"\n{'=' * 70}\nGET {url}")
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=25.0)
    except Exception as e:
        print(f"  FEL: {e}")
        return
    print(f"  status={r.status_code} final_url={r.url} content-type={r.headers.get('content-type')}")
    print(f"  body length: {len(r.content)} bytes")

    ct = r.headers.get("content-type", "")
    if "html" not in ct:
        print(f"  raw snippet: {r.text[:1000]!r}")
        return

    soup = BeautifulSoup(r.content, "html.parser")
    title = soup.find("title")
    print(f"  <title>: {title.get_text() if title else None}")

    meta_desc = soup.find("meta", attrs={"name": "description"})
    print(f"  meta description: {meta_desc.get('content') if meta_desc else None}")

    rss_links = soup.find_all("link", attrs={"type": lambda t: t and "rss" in t.lower()})
    print(f"  <link rel=alternate rss> tags found: {len(rss_links)}")
    for rl in rss_links[:5]:
        print(f"    {rl.get('href')}")

    ldjson = soup.find_all("script", type="application/ld+json")
    print(f"  JSON-LD <script> blocks: {len(ldjson)}")
    for block in ldjson[:3]:
        print(f"    snippet: {(block.string or '')[:300]!r}")

    all_links = soup.find_all("a", href=True)
    print(f"  total <a href> tags: {len(all_links)}")
    interesting = [a["href"] for a in all_links if any(
        kw in a["href"].lower() for kw in ("macro", "ficc", "research", "article", "report", "publication")
    )]
    print(f"  links containing macro/ficc/research/article/report/publication ({len(interesting)}):")
    seen = set()
    for h in interesting:
        if h not in seen:
            seen.add(h)
            print(f"    {h}")
        if len(seen) >= 40:
            break

    # Body text sample to eyeball paywall/login-gate language
    body_text = soup.get_text(" ", strip=True)
    print(f"\n  body text sample (first 1500 chars):\n{body_text[:1500]}")


def main() -> None:
    for url in CANDIDATE_URLS:
        dump(url)


if __name__ == "__main__":
    main()
