#!/usr/bin/env python3
"""Offlinetester av beräkningslogiken.

Hela poängen med pipelinen ligger i omräkningen från stock till normaliserat
flöde, och den går att verifiera utan nätverk. Testerna bygger en syntetisk
uppsättning där vi själva bestämt vad som händer — en period med lätt kredit
följd av en åtstramning — och kontrollerar att indikatorn faktiskt vänder ned
i åtstramningen. Kör: python tests/test_offline.py"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indicators  # noqa: E402
import pxweb  # noqa: E402

START = pd.Period("2018-01", freq="M")
SLUT = pd.Period("2026-06", freq="M")
ATSTRAMNING = pd.Period("2023-01", freq="M")


def _manader() -> pd.PeriodIndex:
    return pd.period_range(START, SLUT, freq="M")


def _rader(serie: str, roll: str, kategori: str, innehall: str,
           varden: dict[pd.Period, float]) -> list[dict]:
    return [{"serie": serie, "roll": roll, "tid": str(tid), "kategori": kategori,
             "innehall": innehall, "varde": varde} for tid, varde in varden.items()]


def syntetisk_data() -> pd.DataFrame:
    """Bygger ett fall med känt facit: fram till 2023 växer kreditstocken 1 %
    per månad, därefter 0,05 %. Byggandet faller samtidigt, men långsammare än
    krediten — alltså en ren utbudsåtstramning."""
    manader = _manader()
    rader: list[dict] = []

    for kategori, start in (("Bostadsrättsföreningar", 400_000.0),
                            ("Fastighet - bostäder", 900_000.0),
                            ("Byggverksamhet", 120_000.0)):
        nivå = start
        volym, ranta, antal = {}, {}, {}
        for m in manader:
            stram = m >= ATSTRAMNING
            nivå *= 1.0005 if stram else 1.01
            volym[m] = nivå
            ranta[m] = 4.6 if stram else 1.8
            antal[m] = 9000 * (0.995 if stram else 1.002) ** (m - START).n
        rader += _rader("krita_volym", "kredit", kategori, "Utestående lånebelopp", volym)
        rader += _rader("krita_ranta", "pris", kategori, "Ränta", ranta)
        rader += _rader("krita_antal", "bredd", kategori, "Antal företag", antal)

    bolan = 3_000_000.0
    bolan_varden = {}
    for m in manader:
        bolan *= 1.001 if m >= ATSTRAMNING else 1.005
        bolan_varden[m] = bolan
    rader += _rader("hushall_bolan", "kredit", "Småhus", "Utlåning", bolan_varden)

    obl = 500_000.0
    obl_varden = {}
    for m in manader:
        obl *= 1.0002 if m >= ATSTRAMNING else 1.006
        obl_varden[m] = obl
    rader += _rader("emitterat", "kredit", "Icke-finansiella företag", "Utestående", obl_varden)

    # Påbörjade lägenheter: bara kvartalsmånader, som i BO-statistiken.
    pab = {m: (4500.0 if m < ATSTRAMNING else 3200.0)
           for m in manader if m.month in (1, 4, 7, 10)}
    rader += _rader("pabörjade", "namnare", "Totalt", "Lägenheter", pab)

    bki = {m: 100.0 * 1.004 ** (m - START).n for m in manader}
    rader += _rader("byggkostnad", "namnare", "Bostadshus", "Index", bki)

    styr = {m: (4.0 if m >= ATSTRAMNING else 0.0) for m in manader}
    rader += _rader("styrranta", "pris", "Totalt", "Reporänta", styr)

    hinder = {m: (28.0 if m >= ATSTRAMNING else 6.0) for m in manader}
    rader += _rader("ki_finansiella_hinder", "enkat", "Byggföretag", "Andel", hinder)

    frame = pd.DataFrame(rader)
    frame["tid"] = frame["tid"].map(lambda v: pd.Period(v, freq="M"))
    return frame


def test_flode_nollstalls_over_tidsseriebrott() -> None:
    stock = pd.Series(range(48), index=pd.period_range("2024-01", periods=48, freq="M"),
                      dtype=float)
    resultat = indicators.flow(stock, periods=12, break_at="2026-02")
    assert pd.isna(resultat[pd.Period("2026-02", freq="M")]), \
        "brottsmånaden ska sakna värde"
    assert pd.isna(resultat[pd.Period("2027-01", freq="M")]), \
        "fönstret som spänner över brottet ska sakna värde ända till brott+12"
    assert not pd.isna(resultat[pd.Period("2027-02", freq="M")]), \
        "första fönstret med båda ändpunkterna efter brottet ska ha värde"
    assert not pd.isna(resultat[pd.Period("2026-01", freq="M")]), \
        "månaden före brottet ska vara opåverkad"


def test_kvartalsomvandling() -> None:
    manadsserie = pd.Series([1.0, 2.0, 3.0, 10.0, 20.0, 30.0],
                            index=pd.period_range("2024-01", periods=6, freq="M"))
    assert list(indicators.to_quarterly(manadsserie, "last")) == [3.0, 30.0]
    assert list(indicators.to_quarterly(manadsserie, "sum")) == [6.0, 60.0]


def test_kvartalsserie_far_ratt_arstakt() -> None:
    """Regressionstest: en serie med bara var tredje månad ifylld måste ändå
    ge tolvmånadersförändring, inte treårsförändring."""
    frame = syntetisk_data()
    pab = indicators.pick(frame, "pabörjade")
    assert pab.index.freqstr == "M"
    spann = (pab.index[-1] - pab.index[0]).n + 1
    assert len(pab) == spann, "indexet ska vara sammanhängande månadsvis"
    assert pab.isna().any(), "mellanliggande månader ska vara NaN, inte borttagna"
    kvartal = indicators.to_quarterly(pab, "sum")
    assert kvartal.loc[pd.Period("2019-01", freq="Q")] == 4500.0


def test_indikatorn_vander_ned_i_atstramningen() -> None:
    resultat = indicators.build(syntetisk_data())
    assert "byggkreditindikator" in resultat.columns
    indikator = resultat["byggkreditindikator"].dropna()
    assert len(indikator) > 8, "för få kvartal beräknades"

    fore = indikator[indikator.index < pd.Period("2023-01", freq="Q")].mean()
    efter = indikator[indikator.index >= pd.Period("2024-01", freq="Q")].mean()
    assert efter < fore, f"indikatorn ska falla vid åtstramning (före {fore:.2f}, efter {efter:.2f})"
    assert efter < 0 < fore, "indexet ska byta tecken kring åtstramningen"


def test_spread_och_normalisering_beraknas() -> None:
    resultat = indicators.build(syntetisk_data())
    for kolumn in ("spread_fastighet_bostader", "kredit_per_pabörjad",
                   "kredit_per_pabörjad_real", "gap_kredit_minus_byggande",
                   "flode_produktionsnara"):
        assert kolumn in resultat.columns, f"{kolumn} saknas"
        assert resultat[kolumn].notna().any(), f"{kolumn} är tom"

    spread = resultat["spread_fastighet_bostader"].dropna()
    # 1,8 % ränta mot 0 % styrränta före, 4,6 mot 4,0 efter: spreaden ska krympa
    # i nivå trots att räntan stigit — precis den sortens motsatta rörelse som
    # gör att räntenivån ensam inte duger som åtstramningsmått.
    assert spread[spread.index < pd.Period("2022-10", freq="Q")].mean() > \
        spread[spread.index >= pd.Period("2023-04", freq="Q")].mean()


def test_gapet_fangar_utbudsatstramning() -> None:
    """Krediten faller kraftigare än byggandet i det syntetiska fallet, så
    gapet ska vara tydligt negativt efter åtstramningen."""
    resultat = indicators.build(syntetisk_data())
    gap = resultat["gap_kredit_minus_byggande"].dropna()
    efter = gap[gap.index >= pd.Period("2023-04", freq="Q")]
    assert efter.mean() < 0, f"gapet skulle vara negativt, blev {efter.mean():.1f}"


def test_flera_matt_i_samma_serie_ger_fel() -> None:
    """Regressionstest för den dyraste sortens bugg: ett ContentsCode-mönster
    som råkar matcha både medel och median, så att de summeras. Resultatet blir
    ungefär dubbelt för stort och ser fullt rimligt ut på en graf."""
    frame = syntetisk_data()
    dubbel = frame[frame["serie"] == "krita_volym"].copy()
    dubbel["innehall"] = "Utestående låntagarbelopp, median, mnkr"
    blandad = pd.concat([frame, dubbel], ignore_index=True)

    try:
        indicators.pick(blandad, "krita_volym", kategori=r"bostadsr")
    except ValueError as exc:
        assert "flera mått" in str(exc)
    else:
        raise AssertionError("pick() ska vägra summera över flera mått")


def test_pick_summerar_daremot_kategorier() -> None:
    """Kategorier ska fortfarande summeras — det är hela poängen med att kunna
    be om flera branscher på en gång."""
    frame = syntetisk_data()
    brf = indicators.pick(frame, "krita_volym", kategori=r"bostadsr")
    fastighet = indicators.pick(frame, "krita_volym", kategori=r"fastighet.*bost")
    bada = indicators.pick(frame, "krita_volym", kategori=r"bostadsr|fastighet.*bost")
    sista = bada.dropna().index[-1]
    assert abs(bada[sista] - (brf[sista] + fastighet[sista])) < 1e-6


def test_jsonstat2_plattas_ut_i_ratt_ordning() -> None:
    """Värdematrisen är radmajor över dimensionerna i 'id'. Fel avkodning ger
    siffror som ser rimliga ut men hör till fel bransch — värt ett eget test."""
    payload = {
        "id": ["Bransch", "Tid"],
        "size": [2, 3],
        "dimension": {
            "Bransch": {"category": {"index": {"A": 0, "B": 1},
                                     "label": {"A": "Bostadsrättsföreningar",
                                               "B": "Byggverksamhet"}}},
            "Tid": {"category": {"index": {"2026M01": 0, "2026M02": 1, "2026M03": 2},
                                 "label": {"2026M01": "2026M01", "2026M02": "2026M02",
                                           "2026M03": "2026M03"}}},
        },
        "value": [1, 2, 3, 10, 20, 30],
    }
    frame = pxweb.jsonstat2_to_frame(payload)
    assert len(frame) == 6
    brf = frame[frame["Bransch"] == "Bostadsrättsföreningar"].set_index("Tid")["value"]
    assert list(brf) == [1, 2, 3]
    bygg = frame[frame["Bransch"] == "Byggverksamhet"].set_index("Tid")["value"]
    assert list(bygg) == [10, 20, 30]


def test_jsonstat2_hanterar_gles_matris() -> None:
    payload = {
        "id": ["Tid"], "size": [3],
        "dimension": {"Tid": {"category": {
            "index": {"2026M01": 0, "2026M02": 1, "2026M03": 2}, "label": {}}}},
        "value": {"0": 5, "2": 7},
    }
    frame = pxweb.jsonstat2_to_frame(payload)
    assert list(frame["value"].fillna(-1)) == [5, -1, 7]


def main() -> int:
    tester = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    misslyckade = 0
    for test in tester:
        try:
            test()
        except AssertionError as exc:
            misslyckade += 1
            print(f"FAIL {test.__name__}: {exc}")
        else:
            print(f"ok   {test.__name__}")
    print(f"\n{len(tester) - misslyckade}/{len(tester)} tester gick igenom")
    return 1 if misslyckade else 0


if __name__ == "__main__":
    raise SystemExit(main())
