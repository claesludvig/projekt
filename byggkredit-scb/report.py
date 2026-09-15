#!/usr/bin/env python3
"""Ritar indikatoruppsättningen som små multiplar och skriver en kort
läsanvisning i data/rapport.md.

Varje panel har en egen y-axel med ett enda mått — kreditflöde i kronor,
kvot per lägenhet, räntespread i procentenheter och ett z-poängindex har
ingenting gemensamt att dela axel med, och en dubbelaxel hade bara bjudit in
till att läsa samvariation som inte finns."""

from __future__ import annotations

from pathlib import Path
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"
IN_PATH = DATA / "indikatorer.csv"
FIG_PATH = DATA / "byggkredit.png"
MD_PATH = DATA / "rapport.md"

# Validerad kategoripalett, slot 1-3. Fler än tre serier i samma panel hade
# inte klarat separationskraven för små multiplar, så panelerna hålls till tre.
SERIE_1, SERIE_2, SERIE_3 = "#2a78d6", "#eb6834", "#1baf7a"
# Divergerande par för polaritet kring noll: blått = lättare, rött = stramare.
POS, NEG = "#2a78d6", "#e34948"
TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED = "#0b0b0b", "#52514e", "#8a8983"
GRID, SURFACE = "#e8e7e3", "#fcfcfb"


def _x(index: pd.PeriodIndex) -> pd.DatetimeIndex:
    return index.to_timestamp(how="end")


def _stil(ax: plt.Axes, titel: str, underrad: str) -> None:
    ax.set_title(titel, fontsize=11, color=TEXT_PRIMARY, loc="left", pad=14)
    ax.text(0, 1.02, underrad, transform=ax.transAxes, fontsize=8.5,
            color=TEXT_SECONDARY, va="bottom")
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for kant in ("top", "right"):
        ax.spines[kant].set_visible(False)
    for kant in ("left", "bottom"):
        ax.spines[kant].set_color(GRID)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8, length=0)


def _direktetiketter(ax: plt.Axes, poster: list[tuple[pd.Series, str]]) -> None:
    """Märker ut sista punkten för varje serie direkt i diagrammet. Aqua ligger
    under 3:1 mot ytan, så etiketterna är inte dekoration utan det som gör
    serierna identifierbara utan att man ska behöva skilja på färgerna.

    Serier som konvergerar mot samma nivå — vilket kreditflödena gör i varje
    åtstramning — får annars etiketterna ovanpå varandra. Därför knuffas de isär
    nedifrån och upp med ett minsta avstånd."""
    punkter = [(serie.dropna(), text) for serie, text in poster]
    punkter = [(serie, text) for serie, text in punkter if not serie.empty]
    if not punkter:
        return

    ymin, ymax = ax.get_ylim()
    minsta_avstand = (ymax - ymin) * 0.075
    ordnade = sorted(((serie.iloc[-1], serie.index[-1], text) for serie, text in punkter),
                     key=lambda rad: rad[0])

    placerade: list[float] = []
    for varde, _, _ in ordnade:
        if placerade and varde - placerade[-1] < minsta_avstand:
            varde = placerade[-1] + minsta_avstand
        placerade.append(varde)

    for y, (_, tid, text) in zip(placerade, ordnade):
        ax.annotate(text, xy=(tid.to_timestamp(how="end"), y), xytext=(6, 0),
                    textcoords="offset points", fontsize=8, color=TEXT_SECONDARY,
                    va="center", annotation_clip=False)


def panel_kreditflode(ax: plt.Axes, df: pd.DataFrame) -> bool:
    serier = [("flode_brf", "Bostadsrättsföreningar", SERIE_1),
              ("flode_fastighet_bostader", "Fastighet – bostäder", SERIE_2),
              ("flode_byggverksamhet", "Byggverksamhet", SERIE_3)]
    ritade = [(k, e, f) for k, e, f in serier if k in df and df[k].notna().any()]
    if not ritade:
        return False
    for kolumn, etikett, farg in ritade:
        ax.plot(_x(df.index), df[kolumn], color=farg, linewidth=2, label=etikett)
    ax.axhline(0, color=TEXT_MUTED, linewidth=1)
    _stil(ax, "Kreditflöde per motpart", "12 månaders förändring i utestående belopp, mnkr")
    _direktetiketter(ax, [(df[kolumn], etikett.split(" – ")[0])
                          for kolumn, etikett, _ in ritade])
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_SECONDARY, loc="upper left",
              ncols=1, handlelength=1.6)
    return True


def panel_linje(ax: plt.Axes, df: pd.DataFrame, kolumn: str, titel: str,
                underrad: str, farg: str = SERIE_1, nolllinje: bool = False) -> bool:
    if kolumn not in df or not df[kolumn].notna().any():
        return False
    ax.plot(_x(df.index), df[kolumn], color=farg, linewidth=2)
    if nolllinje:
        ax.axhline(0, color=TEXT_MUTED, linewidth=1)
    _stil(ax, titel, underrad)
    return True


def panel_divergerande(ax: plt.Axes, df: pd.DataFrame, kolumn: str, titel: str,
                       underrad: str) -> bool:
    """Polaritet kring noll ritas som fält i det divergerande paret — riktningen
    är hela budskapet, och ett fält läses snabbare än en linje man måste jämföra
    mot en axel."""
    if kolumn not in df or not df[kolumn].notna().any():
        return False
    serie = df[kolumn]
    x = _x(df.index)
    ax.fill_between(x, 0, serie, where=serie >= 0, color=POS, alpha=0.85,
                    interpolate=True, linewidth=0)
    ax.fill_between(x, 0, serie, where=serie < 0, color=NEG, alpha=0.85,
                    interpolate=True, linewidth=0)
    ax.axhline(0, color=TEXT_MUTED, linewidth=1)
    _stil(ax, titel, underrad)
    return True


def rita(df: pd.DataFrame, path: Path) -> None:
    paneler = [
        lambda ax: panel_kreditflode(ax, df),
        lambda ax: panel_linje(ax, df, "kredit_per_pabörjad_real",
                               "Kredit per påbörjad lägenhet",
                               "Produktionsnära kreditflöde / påbörjade, deflaterat med BKI"),
        lambda ax: panel_divergerande(ax, df, "gap_kredit_minus_byggande",
                                      "Utbud eller efterfrågan?",
                                      "Kreditflödets årstakt minus byggandets, "
                                      "procentenheter · negativt = åtstramning"),
        lambda ax: panel_linje(ax, df, "spread_fastighet_bostader",
                               "Räntespread mot styrräntan",
                               "Utlåningsränta fastighet – bostäder, procentenheter",
                               farg=SERIE_2),
        lambda ax: panel_linje(ax, df, "bredd_antal_lantagare_yoy",
                               "Kreditgivningens bredd",
                               "Antal låntagande företag, årlig förändring i procent",
                               farg=SERIE_3, nolllinje=True),
        lambda ax: panel_divergerande(ax, df, "byggkreditindikator",
                                      "Byggkreditindikator",
                                      "Sammanvägt z-index, fullt komponentset · "
                                      "positivt = lättare kreditvillkor"),
    ]

    fig, axes = plt.subplots(3, 2, figsize=(13, 12), facecolor=SURFACE)
    fig.subplots_adjust(hspace=0.6, wspace=0.26, top=0.855, bottom=0.05,
                        left=0.07, right=0.92)
    plattade = list(axes.flat)
    for ax in plattade:
        ax.set_facecolor(SURFACE)

    anvanda = 0
    for rita_panel in paneler:
        if rita_panel(plattade[anvanda]):
            anvanda += 1
    for ax in plattade[anvanda:]:
        ax.set_visible(False)

    fig.suptitle("Kreditutgivning i byggmarknaden", x=0.07, y=0.968, ha="left",
                 fontsize=16, color=TEXT_PRIMARY, weight="bold")
    fig.text(0.07, 0.941, "Källa: SCB (KRITA, finansmarknadsstatistik, BO, PR) "
                          "och Konjunkturinstitutet. Egen bearbetning.",
             ha="left", fontsize=9, color=TEXT_SECONDARY)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def _senaste(df: pd.DataFrame, kolumn: str) -> tuple[str, float] | None:
    if kolumn not in df:
        return None
    ren = df[kolumn].dropna()
    if ren.empty:
        return None
    return str(ren.index[-1]), float(ren.iloc[-1])


def skriv_rapport(df: pd.DataFrame, path: Path) -> None:
    rader = ["# Kreditutgivning i byggmarknaden", "",
             "Automatiskt genererad sammanfattning. Läs tillsammans med "
             "`data/resolution.json`, som visar vilka tabeller siffrorna kommer ur.",
             "", "## Senaste observation", "",
             "| Mått | Period | Värde |", "|---|---|---|"]

    etiketter = {
        "flode_brf": "Kreditflöde, bostadsrättsföreningar (12 mån)",
        "flode_fastighet_bostader": "Kreditflöde, fastighet – bostäder (12 mån)",
        "flode_byggverksamhet": "Kreditflöde, byggverksamhet (12 mån)",
        "flode_hushall_bolan": "Kreditflöde, hushållens bolån (12 mån)",
        "flode_obligationer": "Kreditflöde, obligationer (12 mån)",
        "kredit_per_pabörjad_real": "Kredit per påbörjad lägenhet, real",
        "gap_kredit_minus_byggande": "Gap kredit minus byggande (p.e.)",
        "spread_fastighet_bostader": "Räntespread, fastighet – bostäder (p.e.)",
        "bredd_antal_lantagare_yoy": "Antal låntagare, årstakt (%)",
        "byggkreditindikator": "Byggkreditindikator (z)",
    }
    for kolumn, etikett in etiketter.items():
        if (senaste := _senaste(df, kolumn)) is not None:
            period, varde = senaste
            # Formatera talet för sig: ett .replace() på hela raden hade
            # ätit kommatecknen i etiketterna också.
            tal = f"{varde:,.1f}".replace(",", "\u00a0")
            rader.append(f"| {etikett} | {period} | {tal} |")

    rader += ["", "## Läsanvisning", ""]
    if (indikator := _senaste(df, "byggkreditindikator")) is not None:
        period, varde = indikator
        riktning = "lättare" if varde > 0 else "stramare"
        rader.append(f"Byggkreditindikatorn står i {varde:.2f} standardavvikelser "
                     f"({period}), alltså {riktning} kreditvillkor än normalt under "
                     f"perioden.")
    if (gap := _senaste(df, "gap_kredit_minus_byggande")) is not None:
        period, varde = gap
        if varde < 0:
            rader.append(f"Gapet mot byggandet är {varde:.1f} procentenheter: krediten "
                         f"drar sig undan snabbare än produktionen faller. Det talar "
                         f"för att finansieringen, inte bostadsefterfrågan, är den "
                         f"bindande restriktionen.")
        else:
            rader.append(f"Gapet mot byggandet är {varde:+.1f} procentenheter: krediten "
                         f"håller emot bättre än produktionen. Restriktionen ligger då "
                         f"på efterfrågesidan, inte i finansieringen.")

    rader += ["", "## Förbehåll", "",
              "- KRITA publiceras som stock. Flödena nedan är differenser och "
              "innehåller därför omvärderingar och omklassificeringar som SCB inte "
              "rensar bort.",
              "- Branschindelningen i KRITA är beräknad bransch, inte ren SNI. Bara "
              "bostadsrättsföreningarna är rent avgränsade (juridisk form).",
              "- Byggnadskreditiv redovisas inte separat. Nyproduktionens "
              "finansiering syns först när föreningens permanenta lån läggs upp.",
              "- Tidsseriebrott vid SNI 2025 (februari 2026) — flöden över brottet "
              "sätts till saknat värde.", ""]
    path.write_text("\n".join(rader), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=IN_PATH)
    parser.add_argument("--fig", type=Path, default=FIG_PATH)
    parser.add_argument("--markdown", type=Path, default=MD_PATH)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"{args.input} saknas — kör indicators.py först")

    df = pd.read_csv(args.input, index_col=0)
    df.index = pd.PeriodIndex(df.index, freq="Q")
    rita(df, args.fig)
    skriv_rapport(df, args.markdown)
    print(f"Skrev {args.fig} och {args.markdown}")


if __name__ == "__main__":
    main()
