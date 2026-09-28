"""Tester av genomslagsdelen med exempeldata i källornas format."""

import sys
from pathlib import Path

import pandas as pd

BAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BAS))

import hamta  # noqa: E402
import media  # noqa: E402

ENTITET = {"id": "Q1", "labels": {"sv": {"value": "Testpartiet"}}, "claims": {
    "P8687": [
        {"rank": "normal", "mainsnak": {"datavalue": {"value": {"amount": "+120000", "unit": "1"}}},
         "qualifiers": {"P585": [{"datavalue": {"value": {"time": "+2024-05-01T00:00:00Z"}}}],
                        "P6552": [{"datavalue": {"value": "12345"}}]}},
        {"rank": "normal", "mainsnak": {"datavalue": {"value": {"amount": "+80000", "unit": "1"}}},
         "qualifiers": {"P585": [{"datavalue": {"value": {"time": "+2025-01-10T00:00:00Z"}}}],
                        "P2003": [{"datavalue": {"value": "testpartiet"}}]}},
        {"rank": "deprecated", "mainsnak": {"datavalue": {"value": {"amount": "+1", "unit": "1"}}},
         "qualifiers": {}}],
    "P488": [
        {"mainsnak": {"datavalue": {"value": {"id": "Q10"}}},
         "qualifiers": {"P580": [{"datavalue": {"value": {"time": "+2015-01-01T00:00:00Z"}}}],
                        "P582": [{"datavalue": {"value": {"time": "+2021-01-01T00:00:00Z"}}}]}},
        {"mainsnak": {"datavalue": {"value": {"id": "Q20"}}},
         "qualifiers": {"P580": [{"datavalue": {"value": {"time": "+2021-02-01T00:00:00Z"}}}]}}]}}

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Sverigedemokraterna kräver nytt besked</title><link>https://a/1</link>
<description>&lt;p&gt;Enligt Moderaterna är det fel.&lt;/p&gt;</description><pubDate>Mon, 21 Sep 2026 08:00:00 +0200</pubDate></item>
<item><title>Moderat ökning av räntan</title><link>https://a/2</link><description>Inget parti här</description>
<pubDate>Tue, 22 Sep 2026 08:00:00 +0200</pubDate></item></channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Vänsterpartiet (V) om skolan</title>
<link href="https://b/1"/><summary>text</summary><published>2026-09-23T10:00:00Z</published></entry></feed>"""


def test_wikidata_foljare_och_ledare():
    f = hamta.wd_foljare(ENTITET)
    assert {(x["plattform"], x["foljare"]) for x in f if x["rang"] != "deprecated"} == {("X", 120000.0), ("Instagram", 80000.0)}
    assert [x["datum"] for x in f if x["plattform"] == "X"] == ["2024-05-01"]
    assert hamta.wd_ordforande(ENTITET) == ["Q20"]


def test_flodestolkning():
    r = hamta.las_flode(RSS)
    assert len(r) == 2 and r[0]["lank"] == "https://a/1" and "<p>" not in r[0]["beskrivning"]
    a = hamta.las_flode(ATOM)
    assert a[0]["lank"] == "https://b/1" and a[0]["publicerad"].startswith("2026-09-23")


def test_omnamnanden(tmp_path):
    rader = [{**x, "flode": "Test", "sokt_parti": None, "hamtad": "2026-09-24T06:00"} for x in hamta.las_flode(RSS)]
    rader += [{**x, "flode": "Test", "sokt_parti": None, "hamtad": "2026-09-24T06:00"} for x in hamta.las_flode(ATOM)]
    rader += [{"titel": "x", "beskrivning": "", "lank": "https://g/1", "publicerad": "Mon, 21 Sep 2026 08:00:00 GMT",
               "kalla_namn": "DN", "flode": "Google Nyheter", "sokt_parti": "SD", "hamtad": "2026-09-24T06:00"}]
    pd.DataFrame(rader).to_csv(tmp_path / "artiklar.csv.gz", index=False)
    om, gn = media.artiklar(tmp_path)
    tot = om.groupby("parti").artiklar.sum()
    assert tot["SD"] == 1 and tot["M"] == 1 and tot["V"] == 1   # "Moderat ökning" räknas inte
    assert gn.set_index("parti").artiklar["SD"] == 1
