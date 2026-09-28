"""Tester av tolkarna och beräkningarna. Körs i CI före bygget, så att en ändrad
källfil eller en trasig tolk stoppar körningen i stället för att ge fel data.

    python -m pytest -q valjare/tests
"""

import io
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BAS))

import hamta  # noqa: E402
import lagesbild  # noqa: E402
import metod  # noqa: E402
import norden  # noqa: E402
import riksdag  # noqa: E402
import tolka  # noqa: E402
import valkrets  # noqa: E402
from verklighet_katalog import mal  # noqa: E402

TXT = BAS / "data" / "kallor" / "txt"
XLSX = BAS / "data" / "kallor" / "xlsx"


def test_konfidensintervall():
    lag, hog = metod.r_ki(0.5, 100)
    assert lag < 0.5 < hog and round(lag, 2) == 0.34 and round(hog, 2) == 0.63
    assert metod.r_ki(0.5, 3) == (None, None)


def test_mal_bara_dar_mal_finns():
    assert mal("Total skattesats (%)")["mal_riktning"] is None
    assert mal("Första kontakt i specialiserad vård inom 90 dagar")["mal_varde"] == 100
    assert mal("Försvarsutgifter, % av BNP (SIPRI)")["mal_varde"] == 2.0


@pytest.mark.skipif(not (TXT / "som_trender_1986_2025.txt").exists(), reason="SOM-texten saknas")
def test_som_asikter():
    d = tolka.som_asikter(TXT / "som_trender_1986_2025.txt", "t")
    assert len(d) > 150
    f = d[d.rubrik.str.contains("färre flyktingar", case=False) & (d.serie == "Bra förslag")]
    assert f.andel.iloc[0] == 53 and f.ar.iloc[0] == 2025
    assert (d.andel.between(0, 100)).all()


@pytest.mark.skipif(not (TXT / "som_trender_1986_2025.txt").exists(), reason="SOM-texten saknas")
def test_som_samhallsproblem():
    d = tolka.som_samhallsproblem(TXT / "som_trender_1986_2025.txt", "t")
    assert d.ar.min() <= 1990 and d.ar.max() >= 2025
    assert (d.andel.between(0, 100)).all()


def test_voteringsfil_utan_rubrikrad():
    rader = """2022/23,UU15,008484EA-7970-4559-BEA7-E2F6454E7571,5,Julia Kronlid,0638497389621,SD,Stockholms län,Frånvarande,sakfrågan,2,kvinna,1980,2023-05-10
2022/23,UU15,008484EA-7970-4559-BEA7-E2F6454E7571,5,Mikael Damberg,014744660015,S,Stockholms län,Ja,sakfrågan,7,man,1971,2023-05-10
2022/23,UU15,008484EA-7970-4559-BEA7-E2F6454E7571,5,Anna Andersson,014744660016,M,Skåne läns västra,Nej,sakfrågan,8,kvinna,1971,2023-05-10"""
    v = pd.read_csv(io.StringIO(rader), dtype=str)
    pp, pl = hamta._rd_aggregera(v, "2022/23")
    assert set(pp.parti) == {"S", "M", "SD"}
    assert pp.set_index("parti").loc["SD", "franvarande"] == 1
    assert pl.namn.str.contains("Kronlid").any()


def test_klassning_av_riksdagsdokument():
    assert "lag" in riksdag.klassa("Skärpta straff för brott i kriminella nätverk")
    assert "invandring" not in riksdag.klassa("Finansiering av kommuners medverkan i frågor om slutförvar")
    assert riksdag.klassa("Ett ärende utan kända ord", "JuU") == ["lag"]


def test_eurostat_tid():
    assert norden._ar_dec("2023") == 2023.5
    assert norden._ar_dec("2023-S2") == 2023.75
    assert abs(norden._ar_dec("2023-Q1") - 2023.125) < 1e-9


def test_jsonstat_glest():
    j = {"id": ["sex", "geo", "time"], "size": [2, 2, 1],
         "dimension": {"sex": {"category": {"index": {"T": 0, "M": 1}}},
                       "geo": {"category": {"index": {"SE": 0, "DK": 1}}},
                       "time": {"category": {"index": {"2024": 0}}}},
         "value": {"0": 1.5, "3": 2.0}}
    d = hamta.jsonstat_till_df(j).dropna(subset=["varde"])
    assert list(zip(d.sex_kod, d.geo_kod, d.varde)) == [("T", "SE", 1.5), ("M", "DK", 2.0)]


def test_lagesbild_antal_och_status():
    idx = pd.period_range("2015-01", "2026-08", freq="M")
    s = pd.Series(30.0, index=idx)
    s[-12:] = 10.0   # tydligt lägre senaste året
    post = {"id": "x", "namn": "Test", "fraga": "lag", "kalla": "t", "typ": "antal", "frekvens": "M",
            "lag": 2, "enhet": "st", "s": s}
    r = lagesbild.analys(post, date(2026, 9, 28))
    assert r["tolv_man"] == 120 and r["tolv_man_fjol"] == 360
    assert r["status"] in ("bevaka", "larm") and "lägsta" in (r["extrem"] or "")
    r2 = lagesbild.analys(post, date(2027, 6, 1))
    assert r2["status"] == "inaktuell"


@pytest.mark.skipif(not list(XLSX.glob("val_radata_2026__preliminar-riksdagsval-utan*.xlsx")),
                    reason="Valmyndighetens fil saknas")
def test_valkretsindelning():
    x = next(XLSX.glob("val_radata_2026__preliminar-riksdagsval-utan*.xlsx"))
    k = valkrets.karta(x)
    assert k.kommunkod.nunique() == 290 and k.valkrets_kod.nunique() == 29
    assert set(k[k.valkrets == "Malmö kommun"].kommun) == {"Malmö"}
    w = valkrets.rostberattigade(x)
    assert 7_000_000 < w.sum() < 8_500_000


def test_valkrets_viktning():
    kar = pd.DataFrame({"kommunkod": ["0001", "0002", "0003"], "valkrets_kod": ["01", "01", "02"]})
    w = pd.Series({"0001": 100.0, "0002": 300.0, "0003": 50.0})
    d = pd.DataFrame({"kommunkod": ["0001", "0002", "0003"], "ar": 2024, "varde": [10.0, 20.0, 5.0]})
    ut = valkrets._vagt(d, kar, w, summa=False).set_index("valkrets_kod").varde
    assert ut["01"] == pytest.approx(17.5) and ut["02"] == 5.0
