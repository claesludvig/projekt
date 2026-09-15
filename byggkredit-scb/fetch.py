#!/usr/bin/env python3
"""Hämtar serierna i sources.py och skriver dem i långt format till
data/serier.csv, plus en granskningslogg i data/resolution.json.

Loggen är inte en biprodukt utan poängen: eftersom tabeller och värden väljs
på etiketter måste man kunna se exakt vilken tabell och vilka värden en serie
faktiskt landade i innan man använder siffrorna i en prognos. Kör alltid
--dry-run först efter att SCB lagt om en tabell."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import argparse
import json
import re
import sys

import pandas as pd

import pxweb
import riksbank
import sources

DATA = Path(__file__).resolve().parent / "data"
RAW = DATA / "raw"
TIDY_PATH = DATA / "serier.csv"
RESOLUTION_PATH = DATA / "resolution.json"

CONTENTS_CODES = {"contentscode", "tabellinnehåll", "tabellinnehall"}


def parse_period(value: str) -> pd.Period | None:
    """SCB blandar 2026M02, 2026K1 och 2026 i tidsvariabeln. Normaliserar till
    månadsperiod — kvartal och år placeras på sin första månad så att allt kan
    ligga i samma tabell, och resamplas explicit i indicators.py."""
    value = str(value).strip()
    if m := re.fullmatch(r"(\d{4})M(\d{2})", value):
        return pd.Period(f"{m.group(1)}-{m.group(2)}", freq="M")
    if m := re.fullmatch(r"(\d{4})K(\d)", value):
        return pd.Period(f"{m.group(1)}-{(int(m.group(2)) - 1) * 3 + 1:02d}", freq="M")
    if m := re.fullmatch(r"(\d{4})", value):
        return pd.Period(f"{m.group(1)}-01", freq="M")
    try:
        return pd.Period(pd.Timestamp(value), freq="M")
    except Exception:
        return None


def build_selection(client: pxweb.PxWebClient, spec: sources.SeriesSpec, meta: dict
                    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Översätter spec.picks till konkreta värdekoder, och bestämmer vad som
    ska hända med de variabler specen inte nämner."""
    selections: dict[str, list[str]] = {}
    labels: dict[str, list[str]] = {}
    for var_pattern, value_patterns in spec.picks:
        code, values, texts = client.match_values(meta, var_pattern, list(value_patterns))
        selections[code] = values
        labels[code] = texts

    time_code = client.time_variable(meta)["code"]
    for var in meta["variables"]:
        if var["code"] in selections or var["code"] == time_code:
            continue
        if var.get("elimination"):
            # Variabeln kan utelämnas, vilket ger SCB:s eget totalvärde. Det är
            # det vi vill ha för t.ex. storleksklass — summan över alla klasser.
            continue
        # Icke-eliminerbar variabel måste anges. Finns ett totalvärde tar vi
        # det; annars alla. Skillnaden är inte kosmetisk — hämtar man både
        # "Totalt" och de enskilda storleksklasserna summerar indicators.py
        # ihop dem till ungefär det dubbla, och felet syns inte på en graf som
        # ändå saknar absolut referens.
        total = _totalvarde(var)
        if total is not None:
            kod, etikett = total
            selections[var["code"]] = [kod]
            labels[var["code"]] = [etikett]
        else:
            selections[var["code"]] = list(var["values"])
            labels[var["code"]] = list(var["valueTexts"])
    return selections, labels


def _totalvarde(var: dict) -> tuple[str, str] | None:
    """Hittar variabelns eget totalvärde, om det finns. SCB stavar det olika
    mellan produkter ('Totalt', 'Samtliga', 'Alla MFI', '1. Totalt, samtliga
    branscher'), så matchningen är medvetet generös."""
    # Måttdimensionen undantas. Ett "totalvärde" bland måtten finns inte —
    # där betyder ordet något helt annat, och den generösa matchningen valde
    # "Räntekostnad samtliga utestående, procent" som om det vore en summa.
    if var["code"].lower() in CONTENTS_CODES:
        return None

    par = list(zip(var["values"], var["valueTexts"]))
    # Exakt etikett först. Utan det vann "byggmästeri-varor totalt" över det
    # riktiga totalvärdet bara för att det också innehåller ordet "totalt".
    exakta = [(kod, text) for kod, text in par
              if text.strip().lower() in {"total", "totalt", "samtliga", "alla"}]
    if len(exakta) == 1:
        return exakta[0]

    rx = re.compile(r"\b(totalt?|samtliga|alla)\b", re.IGNORECASE)
    traffar = [(kod, text) for kod, text in par if rx.search(text)]
    # Flera lösa träffar betyder att mönstret fångat något annat än ett
    # totalvärde; då är det säkrare att hämta allt och låta granskningsloggen
    # visa det, så att pick():s skyddsräcke får smälla i stället.
    return traffar[0] if len(traffar) == 1 else None


def tidy(frame: pd.DataFrame, spec: sources.SeriesSpec, time_code: str) -> pd.DataFrame:
    """Vänder ett uttag till (serie, tid, kategori, innehall, varde)."""
    contents_col = next((c for c in frame.columns if c.lower() in CONTENTS_CODES), None)
    category_cols = [c for c in frame.columns
                     if c not in {time_code, "value", contents_col}]

    out = pd.DataFrame({
        "serie": spec.key,
        "roll": spec.role,
        "tid": frame[time_code].map(parse_period),
        "kategori": (frame[category_cols].astype(str).agg(" | ".join, axis=1)
                     if category_cols else "Totalt"),
        "innehall": frame[contents_col] if contents_col else spec.label,
        "varde": frame["value"],
    })
    return out.dropna(subset=["tid"]).sort_values(["kategori", "tid"])


def resolve_and_fetch(spec: sources.SeriesSpec, since: int | None, dry_run: bool
                      ) -> tuple[pxweb.Resolution, pd.DataFrame | None]:
    client = pxweb.PxWebClient(spec.base)
    node = client.find_table(spec.root, spec.table, spec.depth)
    meta = client.metadata(node.path)
    selections, labels = build_selection(client, spec, meta)
    resolution = pxweb.Resolution(table_path=node.path, table_title=node.text,
                                  selections=selections, selection_labels=labels)
    if dry_run:
        return resolution, None

    tvar = client.time_variable(meta)
    times = list(tvar["values"])
    if since is not None:
        times = [t for t in times if (p := parse_period(t)) is not None and p.year >= since]
    frame = client.fetch(node.path, selections, times)
    return resolution, tidy(frame, spec, tvar["code"])


def cmd_list(root: str, base: str, depth: int) -> None:
    client = pxweb.PxWebClient(base)
    for table in client.walk_tables(root, depth):
        print(f"{table.path}\n    {table.text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="Kommaseparerade serienycklar att hämta")
    parser.add_argument("--since", type=int, default=2015, help="Första år att hämta")
    parser.add_argument("--dry-run", action="store_true",
                        help="Lös ut tabeller och värden utan att hämta data")
    parser.add_argument("--list", metavar="ROT",
                        help="Lista tabeller under en rot, t.ex. FM/FM0002")
    parser.add_argument("--base", default=pxweb.SCB_BASE, help="API-bas för --list")
    parser.add_argument("--depth", type=int, default=3, help="Djup för --list")
    args = parser.parse_args()

    if args.list is not None:
        cmd_list(args.list, args.base, args.depth)
        return

    wanted = set(args.only.split(",")) if args.only else None
    specs = [s for s in sources.SPECS if wanted is None or s.key in wanted]
    if not specs:
        parser.error(f"Ingen serie matchar --only {args.only}")

    RAW.mkdir(parents=True, exist_ok=True)
    resolutions: dict[str, dict] = {}
    frames: list[pd.DataFrame] = []
    failures: list[str] = []

    for spec in specs:
        try:
            resolution, frame = resolve_and_fetch(spec, args.since, args.dry_run)
        except Exception as exc:
            # En serie som inte går att lösa ut ska inte stoppa de andra —
            # hellre en partiell uppsättning med tydlig avvikelselista än
            # ingenting alls.
            failures.append(f"{spec.key}: {exc}")
            print(f"[MISS] {spec.key}: {exc}", file=sys.stderr)
            continue

        resolutions[spec.key] = {"label": spec.label, "roll": spec.role,
                                 "note": spec.note, **asdict(resolution)}
        print(f"[OK]   {spec.key} -> {resolution.table_path} ({resolution.table_title})")
        for code, texts in resolution.selection_labels.items():
            print(f"         {code}: {', '.join(texts[:6])}"
                  + (" ..." if len(texts) > 6 else ""))
        if frame is not None:
            frame.to_csv(RAW / f"{spec.key}.csv", index=False)
            frames.append(frame)

    # Styrräntan ligger utanför SSD och hämtas från Riksbanken. Den behandlas
    # som vilken serie som helst i utdatan, men får falla utan att stoppa
    # körningen — indicators.py räknar en relativ ränta mot KRITA:s egen total
    # när den absoluta spreaden saknas.
    if (wanted is None or "styrranta" in wanted) and not args.dry_run:
        try:
            swea = riksbank.som_tidig_tabell(args.since)
        except Exception as exc:
            failures.append(f"styrranta: {exc}")
            print(f"[MISS] styrranta (Riksbanken): {exc}", file=sys.stderr)
        else:
            swea.to_csv(RAW / "styrranta.csv", index=False)
            frames.append(swea)
            print(f"[OK]   styrranta -> Riksbanken SWEA ({len(swea)} månader)")

    RESOLUTION_PATH.write_text(json.dumps(resolutions, ensure_ascii=False, indent=2))
    if frames:
        tidy_all = pd.concat(frames, ignore_index=True)
        tidy_all.to_csv(TIDY_PATH, index=False)
        print(f"\nSkrev {len(tidy_all)} rader till {TIDY_PATH}")
    print(f"Granskningslogg: {RESOLUTION_PATH}")
    if failures:
        print(f"\n{len(failures)} serie(r) kunde inte lösas ut — justera mönstret i "
              f"sources.py, eller kör --list på roten för att se vad som finns.")


if __name__ == "__main__":
    main()
