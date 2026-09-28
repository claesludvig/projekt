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


def test_sakfragor_i_samma_artikel(tmp_path):
    pd.DataFrame([
        {"titel": "Moderaterna vill skärpa straffen för gängbrott", "beskrivning": "", "lank": "a", "hamtad": "2026-09-28T10:00"},
        {"titel": "Moderaterna om skolan", "beskrivning": "Nya betyg", "lank": "b", "hamtad": "2026-09-28T11:00"},
        {"titel": "Vädret", "beskrivning": "Regn", "lank": "c", "hamtad": "2026-09-28T12:00"},
    ]).to_csv(tmp_path / "artiklar.csv.gz", index=False)
    s = media.sakfragor(tmp_path).set_index(["parti", "fraga"])
    assert s.loc[("M", "lag"), "andel"] == 50 and s.loc[("M", "skola"), "artiklar"] == 1
    assert set(s.index.get_level_values("parti")) == {"M"}


def test_riksdagsaktivitet_per_ledamot(tmp_path):
    pd.DataFrame([{"rm": "2024/25", "typ": t, "parti": "V", "antal": n} for t, n in (("mot", 200), ("ip", 50), ("fr", 250))]) \
        .to_csv(tmp_path / "aktivitet.csv", index=False)
    led = pd.DataFrame({"rm": ["2024/25"] * 25, "parti": ["V"] * 25, "voteringar": [100] * 25})
    d = media.rd_aktivitet(tmp_path, led)
    assert d.per_ledamot.item() == 20


def test_partinamn_raknas_inte_som_sakfraga(tmp_path):
    pd.DataFrame([{"titel": "Miljöpartiet byter talesperson", "beskrivning": "", "lank": "a", "hamtad": "2026-09-28"}]) \
        .to_csv(tmp_path / "artiklar.csv.gz", index=False)
    s = media.sakfragor(tmp_path)
    assert s.artiklar.sum() == 0


def test_som_fortroende_ur_layouttext(tmp_path):
    (tmp_path / "txt").mkdir()
    (tmp_path / "txt" / "som_fortroendetrender.txt").write_text(
        "     Tabell 32d Andel mycket/ganska stort förtroende för radio och tv, efter bakgrundsfaktorer 1986–2024 (procent, eta)\n"
        "                            2023   2024\n"
        "          S amtliga          5 8    5 6\n"
        "          Socialdemokraterna 71     67\n"
        "          Kristdemokraterna  (47)   39\n"
        "          Sverigedemokraterna 33    32\n"
        "          eta               0.31   0.31\n", encoding="utf-8")
    d = media.som_fortroende(tmp_path).set_index(["grupp", "ar"])
    assert d.loc[("ALLA", 2024), "andel"] == 56 and d.loc[("SD", 2023), "andel"] == 33
    assert bool(d.loc[("KD", 2023), "fa_svar"]) and not bool(d.loc[("KD", 2024), "fa_svar"])
