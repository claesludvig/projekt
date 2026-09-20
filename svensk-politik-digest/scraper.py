#!/usr/bin/env python3
"""Hämtar ny rapportering och kommentar om svensk politik och regeringsbildningen.

Samma grundmetod som ing-think-digest och seb-research-digest (hämta lista,
plocka metadata ur JSON-LD, brödtext ur <main>, skriv JSON till data/), med två
tillägg som den här bevakningen kräver:

1. Utskicket är inkrementellt. data/seen.json är ett arkiv över allt som redan
   skickats ut; latest_articles.json innehåller bara det som tillkommit sedan
   förra körningen. Kör man två gånger samma dag blir andra körningen tom om
   inget hänt, i stället för att upprepa gårdagens material.
2. Flödena är breda nyhetsflöden, inte ämnesflöden som ING:s FX-sida. Därför
   filtreras varje post mot ämnesorden i sources.py innan den tas med.

Betalvägg: DN, SvD och Expressen ger sällan fulltext till en oinloggad hämtare.
Posterna tas ändå med — med rubrik och ingress från RSS, och paywall-flaggan
satt — eftersom vem som skriver vad och med vilken vinkel är halva poängen med
kommentarsbevakningen.
"""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx
from bs4 import BeautifulSoup

from sources import (
    COMMENTATORS,
    PARTIES,
    PAYWALL_MARKERS,
    SOURCES,
    TOPIC_TERMS,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
SEEN_PATH = OUTPUT_DIR / "seen.json"
LATEST_PATH = OUTPUT_DIR / "latest_articles.json"
DIGEST_PATH = OUTPUT_DIR / "digest.md"

MAX_PER_SOURCE = 25
MAX_AGE_DAYS = 10        # poster äldre än så här tas inte med ens om de är osedda
SEEN_RETENTION_DAYS = 180  # hur länge arkivet minns en URL

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    # DN svarar 406 Not Acceptable och Sveriges Radio 403 på en förfrågan utan
    # Accept-header. Samma sträng täcker både artikelsidor och RSS-flöden.
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/rss+xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "sv-SE,sv;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

# En delad klient i stället för fristående httpx.get-anrop: DN släpper igenom de
# tre första hämtningarna och svarar 406 på resten när varje anrop kommer utan
# cookies och utan uppehåll. Klienten behåller cookies och återanvänder
# anslutningen, och HOST_DELAY håller takten nere per värd.
CLIENT = httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0)
HOST_DELAY = 1.5
BLOCKED = (403, 406, 429)
_last_call: dict[str, float] = {}


def http_get(url: str) -> httpx.Response:
    """Hämtar en URL med paus per värd och ett andra försök vid avvisning."""
    host = httpx.URL(url).host

    def once(target: str) -> httpx.Response:
        h = httpx.URL(target).host
        wait = HOST_DELAY - (time.monotonic() - _last_call.get(h, 0.0))
        if wait > 0:
            time.sleep(wait)
        _last_call[h] = time.monotonic()
        return CLIENT.get(target)

    r = once(url)
    if r.status_code in BLOCKED:
        # Avvisad: vänta ut en eventuell strypning och försök igen.
        time.sleep(3.0)
        r = once(url)
    if r.status_code in BLOCKED and host.startswith("www."):
        # Sveriges Radio svarar 403 på www.sverigesradio.se men serverar
        # samma artikel utan prefixet.
        r = once(url.replace("://www.", "://", 1))
    r.raise_for_status()
    return r


# --------------------------------------------------------------------------
# Hjälpfunktioner
# --------------------------------------------------------------------------

def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def strip_html(html: str) -> str:
    return clean(BeautifulSoup(html or "", "html.parser").get_text(" "))


def normalize(url: str) -> str:
    """Tar bort spårningsparametrar så att samma artikel inte räknas två gånger."""
    url = (url or "").split("#")[0]
    if "?" in url:
        base, _, query = url.partition("?")
        keep = [
            p for p in query.split("&")
            if p and not p.lower().startswith(("utm_", "cmpid", "ref=", "at_medium"))
        ]
        url = base + ("?" + "&".join(keep) if keep else "")
    return url.rstrip("/")


def title_key(title: str) -> str:
    """Nyckel för att fånga samma TT-text publicerad hos flera avsändare."""
    t = re.sub(r"[^\wåäöÅÄÖ ]+", "", (title or "").lower())
    return hashlib.sha1(clean(t).encode("utf-8")).hexdigest()


def entry_date(entry) -> str:
    for field in ("published_parsed", "updated_parsed"):
        tm = entry.get(field)
        if tm:
            return datetime(*tm[:6], tzinfo=timezone.utc).date().isoformat()
    return ""


# --------------------------------------------------------------------------
# Ämnesfilter
# --------------------------------------------------------------------------

def relevance(text: str) -> list[str]:
    """Returnerar matchade nyckelord — tom lista betyder 'inte politisk nog'."""
    low = (text or "").lower()
    hits = [t for t in TOPIC_TERMS if t in low]
    # Räkna per parti, inte per söksträng: varianterna överlappar som
    # delsträngar och ett parti får aldrig räknas två gånger.
    parties = sorted(
        name for name, variants in PARTIES.items() if any(v in low for v in variants)
    )
    if hits:
        return hits + parties
    # Utan ämnesord krävs två olika partier för att undvika lösa omnämnanden.
    return parties if len(parties) >= 2 else []


def find_commentator(*fields: str) -> str:
    blob = " ".join(f or "" for f in fields).lower()
    for name in COMMENTATORS:
        if name.lower() in blob:
            return name
    return ""


# --------------------------------------------------------------------------
# Hämtning
# --------------------------------------------------------------------------

def resolve_feed(source: dict):
    """Provar källans kandidat-URL:er och tar den första som ger poster."""
    for url in source["urls"]:
        try:
            feed = feedparser.parse(http_get(url).content)
        except Exception as e:
            print(f"    [!] {url}: {e}")
            continue
        if feed.entries:
            return url, feed.entries
        print(f"    [!] {url}: inga poster")
    return "", []


def fetch_fulltext(url: str) -> tuple[str, str, bool, str]:
    """Returnerar (brödtext, författare, paywall, fel).

    Betalvägg och hämtningsfel måste hållas isär: båda ger kort eller tom
    brödtext, men det ena betyder "texten finns bakom inloggning" och det
    andra "vi kom inte fram". Blandas de ihop ser ett trasigt flöde ut som en
    betalvägg och felet upptäcks aldrig.
    """
    try:
        r = http_get(url)
    except Exception as e:
        return "", "", False, str(e).split("\n")[0][:200]

    soup = BeautifulSoup(r.content, "html.parser")

    author = ""
    body = ""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        for it in (data if isinstance(data, list) else [data]):
            if not isinstance(it, dict):
                continue
            if "article" not in str(it.get("@type", "")).lower():
                continue
            body = body or clean(it.get("articleBody", ""))
            au = it.get("author")
            if isinstance(au, dict):
                author = author or clean(au.get("name", ""))
            elif isinstance(au, list):
                names = [clean(a.get("name", "")) for a in au if isinstance(a, dict)]
                author = author or ", ".join(n for n in names if n)

    if not body:
        main = soup.find("article") or soup.find("main") or soup
        texts = [clean(b.get_text(" ")) for b in main.find_all(["p", "h2", "h3"])]
        body = "\n".join(t for t in texts if len(t) > 40)

    low = body.lower()
    paywall = any(m in low for m in PAYWALL_MARKERS) or 0 < len(body.split()) < 60
    return body, author, paywall, ""


# --------------------------------------------------------------------------
# Arkiv över redan utskickat material
# --------------------------------------------------------------------------

def load_seen() -> dict:
    if not SEEN_PATH.exists():
        return {"urls": {}, "titles": {}}
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[!] Kunde inte läsa {SEEN_PATH} ({e}) — börjar om med tomt arkiv")
        return {"urls": {}, "titles": {}}
    data.setdefault("urls", {})
    data.setdefault("titles", {})
    return data


def prune_seen(seen: dict) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)).isoformat()
    for bucket in ("urls", "titles"):
        seen[bucket] = {k: v for k, v in seen[bucket].items() if v >= cutoff}
    return seen


# --------------------------------------------------------------------------
# Utskrift
# --------------------------------------------------------------------------

def write_digest(articles: list[dict], generated_at: str, skipped: dict) -> None:
    day = generated_at[:10]
    lines = [
        f"# Svensk politik och regeringsförhandlingarna — {day}",
        "",
    ]
    if not articles:
        lines += [
            "Inget nytt sedan förra utskicket.",
            "",
            f"_Genererat {generated_at}._",
        ]
        DIGEST_PATH.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.append(
        f"{len(articles)} nya poster sedan förra utskicket "
        f"({skipped['seen']} redan utskickade, {skipped['offtopic']} utanför ämnet)."
    )
    lines.append("")

    headings = {
        "kommentar": "## Analys och kommentar",
        "nyhet": "## Rapportering",
        "officiell": "## Officiella besked",
    }
    for kind, heading in headings.items():
        group = [a for a in articles if a["kind"] == kind]
        if not group:
            continue
        lines += [heading, ""]
        for a in group:
            byline = a["author"] or a["commentator"]
            meta = " · ".join(x for x in [a["source"], a["published"], byline] if x)
            flag = " **[kommentator]**" if a["commentator"] else ""
            if a.get("fetch_error"):
                lock = " _(brödtext ej hämtad — endast ingress)_"
            elif a["paywall"]:
                lock = " _(betalvägg — endast ingress)_"
            else:
                lock = ""
            lines.append(f"### [{a['title']}]({a['url']}){flag}")
            lines.append(f"{meta}{lock}")
            lines.append("")
            lines.append(a["summary"] or a["fulltext"][:600])
            lines.append("")
    lines.append(f"_Genererat {generated_at}._")
    DIGEST_PATH.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    seen = load_seen()
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    age_cutoff = (now - timedelta(days=MAX_AGE_DAYS)).date().isoformat()

    new_articles: list[dict] = []
    skipped = {"seen": 0, "offtopic": 0, "old": 0}
    fetch_errors = 0
    source_status: list[dict] = []

    for source in SOURCES:
        print(f"== {source['name']} ==")
        feed_url, entries = resolve_feed(source)
        if not entries:
            print("  [!] Ingen fungerande URL — hoppar över källan")
            source_status.append({"name": source["name"], "feed": "", "new": 0, "ok": False})
            continue

        added = 0
        for entry in entries[:MAX_PER_SOURCE]:
            url = normalize(entry.get("link", ""))
            if not url:
                continue

            title = clean(entry.get("title", ""))
            summary = strip_html(entry.get("summary", ""))
            published = entry_date(entry)
            tkey = title_key(title)

            if url in seen["urls"] or tkey in seen["titles"]:
                skipped["seen"] += 1
                continue
            if published and published < age_cutoff:
                skipped["old"] += 1
                continue

            matched = relevance(f"{title} {summary}")
            if source["filter"] and not matched:
                skipped["offtopic"] += 1
                continue

            print(f"  Hämtar: {title[:70]} ...", end=" ", flush=True)
            fulltext, author, paywall, fetch_error = fetch_fulltext(url)
            if fulltext and not matched:
                matched = relevance(fulltext)

            author = author or clean(entry.get("author", ""))
            commentator = find_commentator(author, title, summary)

            new_articles.append(
                {
                    "url": url,
                    "title": title,
                    "source": source["name"],
                    "kind": source["kind"],
                    "published": published,
                    "author": author,
                    "commentator": commentator,
                    "summary": summary,
                    "fulltext": fulltext,
                    "paywall": paywall,
                    "fetch_error": fetch_error,
                    "matched_terms": matched,
                    "first_seen": stamp,
                }
            )
            seen["urls"][url] = stamp
            seen["titles"][tkey] = stamp
            added += 1
            fetch_errors += 1 if fetch_error else 0
            if fetch_error:
                print(f"bara ingress (hämtning nekad: {fetch_error[:60]})")
            else:
                print(f"OK ({len(fulltext.split())} ord{', betalvägg' if paywall else ''})")

        print(f"  {added} nya poster")
        source_status.append(
            {"name": source["name"], "feed": feed_url, "new": added, "ok": True}
        )

    new_articles.sort(key=lambda a: (a.get("published", ""), a.get("source", "")), reverse=True)

    LATEST_PATH.write_text(
        json.dumps(
            {
                "fetched_at": stamp,
                "new_count": len(new_articles),
                "skipped": skipped,
                "fetch_errors": fetch_errors,
                "sources": source_status,
                "articles": new_articles,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    SEEN_PATH.write_text(
        json.dumps(prune_seen(seen), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_digest(new_articles, stamp, skipped)

    print(
        f"\nSparade {len(new_articles)} nya poster till {LATEST_PATH}"
        f" ({skipped['seen']} redan utskickade, {skipped['offtopic']} utanför ämnet,"
        f" {skipped['old']} för gamla, {fetch_errors} utan brödtext)"
    )


if __name__ == "__main__":
    main()
