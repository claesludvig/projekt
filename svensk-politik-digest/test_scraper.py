#!/usr/bin/env python3
"""Offline-test av politikdigesten. Kräver inget nätverk.

Kör: python svensk-politik-digest/test_scraper.py

Testet stubbar http_get och kör main() två gånger mot en tillfällig datakatalog.
Det som verifieras är det som gått sönder i skarp drift: ämnesfiltret (stammar,
partiräkning), dedupen mellan körningar, åldersgränsen, och skillnaden mellan
betalvägg och hämtningsfel.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scraper  # noqa: E402

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item>
  <title>Talmannen ger Moderaterna sonderingsuppdrag i regeringsbildningen</title>
  <link>https://example.test/artikel/talman?utm_source=rss&amp;id=7</link>
  <description>Efter valet inleds nu en ny talmansrunda.</description>
  <pubDate>Fri, 19 Sep 2026 08:00:00 GMT</pubDate>
</item>
<item>
  <title>Barth-Kron: Talmansrundorna har redan kört fast</title>
  <link>https://example.test/ledare/barth-kron</link>
  <description>Kolumn av Viktor Barth-Kron om läget.</description>
  <pubDate>Fri, 19 Sep 2026 06:00:00 GMT</pubDate>
</item>
<item>
  <title>Partiledarna möts utan JSON-LD på sidan</title>
  <link>https://example.test/artikel/utan-jsonld</link>
  <description>Samtal om regeringsunderlaget.</description>
  <pubDate>Fri, 19 Sep 2026 07:00:00 GMT</pubDate>
</item>
<item>
  <title>Kort officiellt besked om regeringsbildningen</title>
  <link>https://example.test/artikel/kort</link>
  <description>Talmannen meddelar tidplan.</description>
  <pubDate>Fri, 19 Sep 2026 07:30:00 GMT</pubDate>
</item>
<item>
  <title>Tyska kristdemokraterna CDU åker ur delstatsparlamentet</title>
  <link>https://example.test/artikel/tyskland</link>
  <description>Ytterhögerpartiet AfD och vänsterpartiet Die Linke vann de tyska delstatsvalen.</description>
  <pubDate>Fri, 19 Sep 2026 06:30:00 GMT</pubDate>
</item>
<item>
  <title>Moderaterna presenterade en ny skolsatsning</title>
  <link>https://example.test/artikel/skola</link>
  <description>Ett enda parti nämns i en skolnyhet.</description>
  <pubDate>Fri, 19 Sep 2026 05:30:00 GMT</pubDate>
</item>
<item>
  <title>Elpriset faller kraftigt i norra Sverige</title>
  <link>https://example.test/ekonomi/elpris</link>
  <description>Mild väderlek och god tillgång på vattenkraft.</description>
  <pubDate>Fri, 19 Sep 2026 05:00:00 GMT</pubDate>
</item>
<item>
  <title>Gammal text om regeringsbildningen från i våras</title>
  <link>https://example.test/arkiv/gammal</link>
  <description>Regeringsbildningen då och då.</description>
  <pubDate>Mon, 02 Mar 2026 05:00:00 GMT</pubDate>
</item>
</channel></rss>"""

_BODY = (
    "Talmannen har gett Moderaternas partiledare i uppdrag att sondera "
    "förutsättningarna för en ny regering. Sonderingarna redovisas på torsdag. "
    "Socialdemokraterna har meddelat att man inte tänker medverka. Centerpartiet "
    "håller dörren öppen men ställer krav på budgetpolitiken. Parallella samtal "
    "pågår mellan partiledarna om hur mandatfördelningen i utskotten ska lösas "
    "under hösten och vintern, uppger flera källor till redaktionen."
)
FULL = (
    '<html><head><script type="application/ld+json">'
    '{"@type":"NewsArticle","headline":"Talmannen ger uppdrag",'
    f'"articleBody":"{_BODY}","author":{{"name":"Redaktionen"}}}}'
    "</script></head><body></body></html>"
)
# Betalväggsnotisen är kortare än stycketröskeln och syns bara om markörerna
# prövas mot hela artikelbehållaren.
PAYWALLED = (
    "<html><body><article>"
    "<p>Viktor Barth-Kron skriver om regeringsförhandlingarna och läget i riksdagen.</p>"
    "<p>Logga in för att läsa hela texten.</p>"
    "</article></body></html>"
)
HTML_ONLY = "<html><body><article>" + "".join(
    f"<p>Stycke {i}: partiledarna fortsatte på torsdagen sina samtal om "
    f"regeringsunderlaget och mandatfördelningen i utskotten under hösten.</p>"
    for i in range(1, 6)
) + "</article></body></html>"
KORT = (
    "<html><body><article><p>Talmannen meddelar att sonderingarna "
    "redovisas på torsdag klockan tio.</p></article></body></html>"
)
TOM_RSS = '<?xml version="1.0"?><rss version="2.0"><channel><title>tom</title></channel></rss>'


class FakeResp:
    """Efterliknar ett httpx-svar: bytes till feedparser, avkodad text till bs4."""

    def __init__(self, text: str):
        self.text = text
        self.content = text.encode("utf-8")


def fake_get(url: str):
    if url.startswith("https://www.svt.se/nyheter/inrikes"):
        return FakeResp(RSS)
    if "/ledare/barth-kron" in url:
        return FakeResp(PAYWALLED)
    if "/artikel/utan-jsonld" in url:
        return FakeResp(HTML_ONLY)
    if "/artikel/kort" in url:
        return FakeResp(KORT)
    if "/artikel/talman" in url:
        return FakeResp(FULL)
    if url.startswith("https://example.test"):
        raise RuntimeError("otillgänglig")
    return FakeResp(TOM_RSS)  # övriga riktiga flöden: tomma i testet


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="politikdigest-test-"))
    scraper.OUTPUT_DIR = tmp
    scraper.SEEN_PATH = tmp / "seen.json"
    scraper.LATEST_PATH = tmp / "latest_articles.json"
    scraper.DIGEST_PATH = tmp / "digest.md"
    scraper.http_get = fake_get

    try:
        scraper.main()
        first = json.loads(scraper.LATEST_PATH.read_text(encoding="utf-8"))
        digest_forst = scraper.DIGEST_PATH.read_text(encoding="utf-8")
        scraper.main()
        second = json.loads(scraper.LATEST_PATH.read_text(encoding="utf-8"))
        digest_andra = scraper.DIGEST_PATH.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    def hitta(delrubrik: str) -> dict | None:
        return next((a for a in first["articles"] if delrubrik in a["title"]), None)

    bk = hitta("Barth-Kron")
    talman = hitta("Talmannen ger")
    nojson = hitta("utan JSON-LD")
    kort = hitta("Kort officiellt")
    rubriker = " | ".join(a["title"] for a in first["articles"])

    kontroller = [
        ("fyra relevanta poster togs med", first["new_count"] == 4),
        ("ett ensamt partinamn räcker inte", "skolsatsning" not in rubriker),
        ("ämnesfrämmande post filtrerades bort", "Elpriset" not in rubriker),
        ("utländsk politik på svenska filtrerades bort", "CDU" not in rubriker),
        ("för gammal post togs bort", first["skipped"]["old"] >= 1),
        ("böjd form fångas av stammen (talmansrundorna)", bk is not None),
        ("andra körningen gav inget nytt", second["new_count"] == 0),
        ("andra körningen kände igen allt", second["skipped"]["seen"] >= 4),
        ("kommentator identifierad utan författarfält",
         bk is not None and bk["commentator"] == "Viktor Barth-Kron"),
        ("betalvägg flaggad trots kort notis",
         bk is not None and bk["paywall"] is True),
        ("fulltext ur JSON-LD",
         talman is not None and len(talman["fulltext"].split()) > 50),
        ("öppen artikel inte betalväggsflaggad",
         talman is not None and talman["paywall"] is False),
        ("ämnesord sparade för spårbarhet",
         talman is not None and "sondering" in talman["matched_terms"]),
        ("url normaliserad, utm bort och id kvar",
         talman is not None and talman["url"] == "https://example.test/artikel/talman?id=7"),
        ("html-fallback när JSON-LD saknas",
         nojson is not None and len(nojson["fulltext"].split()) > 50),
        ("kort text från öppen avsändare är inte betalvägg",
         kort is not None and kort["paywall"] is False
         and len(kort["fulltext"].split()) < 60),
        ("digest.md listar posterna", "Talmannen ger" in digest_forst),
        ("digest.md rapporterar tomt utskick",
         "Inget nytt sedan förra utskicket" in digest_andra),
    ]

    ok = True
    for text, villkor in kontroller:
        ok = ok and villkor
        print(f"  [{'OK ' if villkor else 'FEL'}] {text}")
    print("\nRESULTAT:", "ALLA KONTROLLER OK" if ok else "MISSLYCKADES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
