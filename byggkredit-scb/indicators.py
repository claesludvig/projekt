#!/usr/bin/env python3
"""Räknar om de hämtade serierna till de mått som faktiskt säger något om
kreditutgivningen i byggmarknaden.

Fyra steg, i tur och ordning:

1. Stock -> flöde. Kreditutgivning är ett flöde; utestående belopp är en stock.
   Skillnaden är inte kosmetisk: en stock kan ligga still medan utgivningen
   halveras, eftersom amorteringar och nyutlåning tar ut varandra.
2. Flöde -> flöde per producerad lägenhet, deflaterat med byggkostnadsindex.
   Ett kreditflöde i kronor säger ingenting utan nämnare. Kvoten är i praktiken
   produktionssystemets belåningsgrad.
3. Pris och bredd. Räntespread mot styrräntan och förändring i antal låntagande
   företag. Båda vänder före volymen.
4. Sammanvägning till ett index där positivt = lättare kredit.

Steg 2 är det som gör indikatorn läsbar. Faller kreditflödet snabbare än
byggandet är krediten den bindande restriktionen; faller de i takt är det
efterfrågan på bostäder som är problemet. Volymserien ensam kan inte skilja de
två fallen åt, och det är just den skillnaden en prognos hänger på."""

from __future__ import annotations

from pathlib import Path
import argparse
import re

import pandas as pd

import sources

DATA = Path(__file__).resolve().parent / "data"
TIDY_PATH = DATA / "serier.csv"
OUT_PATH = DATA / "indikatorer.csv"

# Minsta antal delkomponenter för att det sammanvägda indexet ska beräknas.
# Med bara ett ben är det inte ett index utan en omdöpt serie.
MIN_KOMPONENTER = 2
ZSCORE_MINSTA_OBS = 12


def load(path: Path = TIDY_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["tid"] = frame["tid"].map(lambda v: pd.Period(v, freq="M"))
    return frame


def pick(frame: pd.DataFrame, serie: str, kategori: str | None = None,
         innehall: str | None = None) -> pd.Series:
    """Plockar ut en enskild tidsserie ur den långa tabellen. Kategori och
    innehåll matchas som reguljära uttryck mot etiketterna."""
    sub = frame[frame["serie"] == serie]
    if kategori:
        sub = sub[sub["kategori"].str.contains(kategori, case=False, regex=True, na=False)]
    if innehall:
        sub = sub[sub["innehall"].str.contains(innehall, case=False, regex=True, na=False)]
    if sub.empty:
        return pd.Series(dtype=float, index=pd.PeriodIndex([], freq="M"))
    # Flera kategorier som matchar summeras — det är det man vill när man ber
    # om t.ex. "alla bostadsrelaterade fastighetsbranscher".
    series = sub.groupby("tid")["varde"].sum().sort_index()
    series.index = pd.PeriodIndex(series.index, freq="M")
    # Luckor fylls med NaN så att diff(12) alltid jämför med rätt månad —
    # kvartalsserier har bara var tredje månad ifylld, och en diff på den
    # komprimerade indexeringen hade jämfört tre år bakåt i stället för ett.
    full = pd.period_range(series.index.min(), series.index.max(), freq="M")
    return series.reindex(full)


def flow(stock: pd.Series, periods: int = 12, break_at: str | None = None) -> pd.Series:
    """Rullande flöde ur en stock. Observationer vars fönster spänner över ett
    tidsseriebrott sätts till NaN — en förändring över brottet mäter
    omklassificeringen, inte kreditgivningen."""
    out = stock.diff(periods)
    if break_at:
        brott = pd.Period(break_at, freq="M")
        out[(out.index >= brott) & (out.index < brott + periods)] = float("nan")
    return out


def to_quarterly(series: pd.Series, how: str = "last") -> pd.Series:
    """Månad -> kvartal. Stockar och räntor tas som kvartalets sista värde,
    flöden och antal summeras."""
    if series.empty:
        return series
    grouped = series.groupby(series.index.asfreq("Q"))
    result = {"last": grouped.last, "mean": grouped.mean, "sum": grouped.sum}[how]()
    result.index = pd.PeriodIndex(result.index, freq="Q")
    return result


def deflate(nominal: pd.Series, index: pd.Series) -> pd.Series:
    """Deflaterar med byggkostnadsindex. Utan det går stigande kostnadsläge
    inte att skilja från stigande belåning per lägenhet."""
    aligned = index.reindex(nominal.index).ffill()
    return nominal / (aligned / 100.0)


def zscore(series: pd.Series) -> pd.Series:
    clean = series.dropna()
    if len(clean) < ZSCORE_MINSTA_OBS or clean.std(ddof=0) == 0:
        return pd.Series(float("nan"), index=series.index)
    return (series - clean.mean()) / clean.std(ddof=0)


def build(frame: pd.DataFrame) -> pd.DataFrame:
    out: dict[str, pd.Series] = {}

    # --- steg 1: kreditflöden per motpart ---
    brf_stock = pick(frame, "krita_volym", kategori=r"bostadsr")
    fast_bost_stock = pick(frame, "krita_volym", kategori=r"fastighet.*bost")
    bygg_stock = pick(frame, "krita_volym", kategori=r"bygg")
    bolan_stock = pick(frame, "hushall_bolan")
    obligationer = pick(frame, "emitterat")

    brott = sources.BREAKS.get("krita_volym")
    flows = {
        "flode_brf": flow(brf_stock, break_at=brott),
        "flode_fastighet_bostader": flow(fast_bost_stock, break_at=brott),
        "flode_byggverksamhet": flow(bygg_stock, break_at=brott),
        "flode_hushall_bolan": flow(bolan_stock),
        "flode_obligationer": flow(obligationer),
    }
    for name, series in flows.items():
        out[name] = to_quarterly(series, "last")

    # Produktionsnära kredit: föreningarnas permanenta lån plus bostads-
    # fastighetsbolagens upplåning. Entreprenörernas lån hålls utanför — de är
    # rörelsekapital och rör sig med orderstocken, inte med finansieringen av
    # nya projekt.
    produktionsnara = flows["flode_brf"].add(flows["flode_fastighet_bostader"],
                                             fill_value=0.0)
    produktionsnara[flows["flode_brf"].isna() & flows["flode_fastighet_bostader"].isna()] = float("nan")
    out["flode_produktionsnara"] = to_quarterly(produktionsnara, "last")

    # --- steg 2: normalisering mot fysisk produktion ---
    pabörjade = to_quarterly(pick(frame, "pabörjade"), "sum")
    bki = to_quarterly(pick(frame, "byggkostnad"), "mean")
    if not pabörjade.empty:
        kvot = out["flode_produktionsnara"] / pabörjade.reindex(out["flode_produktionsnara"].index)
        out["kredit_per_pabörjad"] = kvot
        if not bki.empty:
            out["kredit_per_pabörjad_real"] = deflate(kvot, bki)

        # Utbud eller efterfrågan? Gapet mellan kreditflödets och byggandets
        # årstakt. Negativt gap = krediten drar sig undan snabbare än
        # produktionen faller, dvs. åtstramning utöver konjunkturen.
        kredit_yoy = out["flode_produktionsnara"].pct_change(4) * 100
        bygg_yoy = pabörjade.pct_change(4) * 100
        out["gap_kredit_minus_byggande"] = kredit_yoy - bygg_yoy.reindex(kredit_yoy.index)

    # --- steg 3: pris och bredd ---
    styrranta = to_quarterly(pick(frame, "styrranta"), "last")
    for etikett, monster in (("brf", r"bostadsr"), ("fastighet_bostader", r"fastighet.*bost")):
        ranta = to_quarterly(pick(frame, "krita_ranta", kategori=monster), "last")
        out[f"ranta_{etikett}"] = ranta
        if not styrranta.empty and not ranta.empty:
            out[f"spread_{etikett}"] = ranta - styrranta.reindex(ranta.index).ffill()

    antal = pick(frame, "krita_antal", kategori=r"fastighet.*bost|bostadsr")
    if not antal.empty:
        out["bredd_antal_lantagare_yoy"] = to_quarterly(
            antal.pct_change(12) * 100, "last")

    # --- steg 4: sammanvägning ---
    hinder = to_quarterly(pick(frame, "ki_finansiella_hinder"), "mean")
    if not hinder.empty:
        out["ki_finansiella_hinder"] = hinder

    result = pd.DataFrame(out).sort_index()

    # Alla komponenter orienteras så att positivt = lättare kreditvillkor.
    komponenter = {
        "kredit_per_pabörjad_real": 1,
        "gap_kredit_minus_byggande": 1,
        "spread_fastighet_bostader": -1,
        "bredd_antal_lantagare_yoy": 1,
        "ki_finansiella_hinder": -1,
    }
    z = pd.DataFrame({
        namn: zscore(result[namn]) * tecken
        for namn, tecken in komponenter.items() if namn in result
    })
    if not z.empty:
        antal = z.notna().sum(axis=1)
        result["antal_komponenter"] = antal
        # Två varianter, av ett skäl som bara syns när man kör serien skarpt:
        # KRITA släpar ett par månader medan KI:s barometer är färsk, så vid
        # seriens kant faller komponenter bort. Ett medelvärde över ett
        # krympande komponentset hoppar då i nivå av rena mätskäl. Huvudserien
        # kräver därför fullt komponentset; kantserien tar vad som finns och
        # ska läsas som preliminär.
        fullt = int(antal.max())
        result["byggkreditindikator"] = z.mean(axis=1).where(antal >= fullt)
        result["byggkreditindikator_prel"] = z.mean(axis=1).where(
            antal >= MIN_KOMPONENTER)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=TIDY_PATH)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"{args.input} saknas — kör fetch.py först")

    result = build(load(args.input))
    result.to_csv(args.output)
    print(result.tail(12).to_string())
    print(f"\nSkrev {len(result)} kvartal till {args.output}")
    saknas = [c for c in ("byggkreditindikator", "kredit_per_pabörjad_real")
              if c not in result.columns]
    if saknas:
        print(f"Kunde inte beräkna: {', '.join(saknas)} — kontrollera "
              f"data/resolution.json för vilka källserier som saknas.")


if __name__ == "__main__":
    main()
