"""Tester av tolkarna för myndigheternas Excelfiler och följarfiltret."""

import sys
from pathlib import Path

import pandas as pd

BAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BAS))

import media  # noqa: E402
import myndigheter  # noqa: E402


def test_beviljade_uppehallstillstand(tmp_path):
    (tmp_path / "xlsx").mkdir()
    rader = [["Antal beviljade förstagångs uppehållstillstånd", None, None, None, None],
             ["Uppehållsgrund", "Uppehållsgrund 2", "2024-01", "2024-02", "Totalt"],
             ["Anknytning", "Anhörig till flykting-/asylgrund", "240", "230", "470"],
             [None, "Totalt", "2145", "2210", "4355"],
             ["Skydd", "Konventionsflykting", "..", "204", ".."],
             [None, "Totalt", "1005", "2261", "3266"],
             ["Totalt", "Totalt", "3150", "4471", "7621"]]
    fil = tmp_path / "xlsx" / "migrationsverket__Beviljade_uppeh__llstillst__nd_2024.xlsx"
    pd.DataFrame(rader).to_excel(fil, sheet_name="Månad, första", header=False, index=False)
    d = myndigheter.beviljade_uppehallstillstand(tmp_path)
    assert set(d.grund) == {"Anknytning", "Skydd", "Totalt"}
    assert d[(d.grund == "Skydd") & (d.period == "2024-02")].antal.item() == 2261
    assert len(d) == 6   # detaljrader och årskolumnen räknas inte


def test_gamla_foljarvarden_jamfors_inte(tmp_path):
    pd.DataFrame([
        {"parti": "M", "roll": "parti", "qid": "Q1", "namn": "M", "plattform": "X", "konto": "1",
         "datum": "2018-05-10", "foljare": 90000, "rang": "normal"},
        {"parti": "S", "roll": "parti", "qid": "Q2", "namn": "S", "plattform": "X", "konto": "2",
         "datum": "2025-01-01", "foljare": 110000, "rang": "normal"},
    ]).to_csv(tmp_path / "foljare.csv", index=False)
    alla, nu = media.foljare(tmp_path)
    assert len(alla) == 2 and list(nu.parti) == ["S"]
