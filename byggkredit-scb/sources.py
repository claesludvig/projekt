#!/usr/bin/env python3
"""Deklarativ specifikation av de serier pipelinen bygger på.

Urvalet utgår från en enda observation: *utlåningsstockar per bransch mäter
ägandet av det befintliga beståndet, inte finansieringen av produktionen.*
"Fastighet - bostäder" domineras av beståndsägare, och stocken rör sig av skäl
som inte är ny kredit (amortering, omvärdering, omklassificering). Att läsa den
serien rakt av som "kreditutgivning till byggmarknaden" ger fel svar i just de
lägen man bryr sig om — vändpunkterna.

Pipelinen angriper det i fyra lager, och varje serie nedan är taggad med vilket
lager den tillhör via `role`:

  kredit   Kreditflödet självt, uppdelat på de motparter som faktiskt
           finansierar bostadsproduktion i olika skeden. Bostadsrätts-
           föreningarna är den renaste posten: en förenings permanenta lån
           löser byggnadskreditivet vid inflyttning, så serien är i praktiken
           nyproduktion i bostadsrätt med projekttidens eftersläpning.
  namnare  Fysisk produktionsvolym och byggkostnad. Utan nämnare är ett
           kreditflöde i kronor oläsbart — det enda intressanta är hur mycket
           kredit som går åt per producerad enhet.
  pris     Räntor per bransch. Kreditgivning stramas åt på pris innan den
           stramas åt på volym; prisbenet vänder därför före volymbenet.
  bredd    Antal låntagande företag. Stigande volym med fallande antal
           låntagare är koncentration till starka balansräkningar, alltså en
           åtstramning som volymserien ensam visar som oförändrad.
  enkat    Byggföretagens egen rapportering av finansiella restriktioner
           (KI:s barometer). Enda direkta måttet på kreditutbud, och det
           enda som leder snarare än släpar.

Tabeller och värden matchas på etiketter, inte koder — se pxweb.py. Roten och
titelmönstret nedan är mina bästa gissningar utifrån SCB:s publicerade
tabellnamn; kör `python fetch.py --list <rot>` om ett mönster missar, och
justera mönstret här."""

from __future__ import annotations

from dataclasses import dataclass, field

import pxweb


@dataclass(frozen=True)
class SeriesSpec:
    key: str
    label: str
    role: str
    root: str
    table: str
    picks: tuple[tuple[str, tuple[str, ...]], ...] = ()
    base: str = pxweb.SCB_BASE
    depth: int = 3
    note: str = ""


# Branschetiketterna i KRITA är Riksbankens och SCB:s beräknade bransch, inte
# ren SNI: bolag med SNI "verksamhet vid huvudkontor" flyttas till den bransch
# koncernen faktiskt verkar i. Bostadsrättsföreningar är undantaget — de
# identifieras på juridisk form och är därmed den enda helt rena avgränsningen
# i hela uppsättningen.
# Etiketterna är numrerade och kortare än man tror: "1.2 Fastighet - Bostäder",
# "1.3 Bostadsrättsföreningar", "1.7 Bygg". Det finns alltså ingen
# "Byggverksamhet" att matcha på — bara "Bygg".
#
# Totalen hämtas med, inte för att summeras in i flödena (kategorimönstren i
# indicators.py plockar aldrig upp den) utan för att räntan mot samtliga
# branscher är den referens som visar om just bostadssidan särbehandlas.
KRITA_BRANSCHER = (
    r"[Bb]ostadsr",
    r"[Ff]astighet.*[Bb]ost",
    r"[Ff]astighet.*(kontor|lokal)",
    r"[Bb]ygg\b",
    r"[Tt]otalt, samtliga",
)

SPECS: list[SeriesSpec] = [
    # ---------- lager 1: kreditflödet ----------
    SeriesSpec(
        key="krita_volym",
        label="MFI:s utlåning till icke-finansiella företag, utestående belopp per bransch",
        role="kredit",
        root="FM/FM0002",
        table=r"utlåning till icke-finansiella företag.*bransch",
        picks=(
            (r"bransch", KRITA_BRANSCHER),
            # Ankrat mönster. "[Uu]testående" ensamt matchade fem mått, bland
            # dem både medel- och medianräntan — vars etiketter innehåller
            # ordet "utestående" — som sedan summerades till nonsens.
            (r"^(ContentsCode|Tabellinnehåll)$", (r"^Utestående lånebelopp",)),
        ),
        note="Stock, månad. Differentieras till flöde i indicators.py. Innehåller "
             "omvärderingar och omklassificeringar som SCB inte rensar bort — till "
             "skillnad från hushållsserien, som publiceras även som transaktioner.",
    ),
    SeriesSpec(
        key="hushall_bolan",
        label="MFI:s utlåning till hushåll med bostad som säkerhet",
        role="kredit",
        root="FM/FM5001",
        table=r"Utestående avtal efter MFI, motpart och säkerhet",
        picks=(
            (r"motpart", (r"[Hh]ushåll",)),
            (r"säkerhet", (r"[Ss]måhus", r"[Bb]ostadsrätt", r"[Ää]garlägenhet")),
            # Totalen över institut heter bara "MFI" och fångas därför inte av
            # den generiska totalvärdesmatchningen. Utan det här picket hämtas
            # totalen tillsammans med banker, bostadsinstitut och finansbolag,
            # och summeras till ungefär det dubbla.
            (r"^MFI$", (r"^MFI$",)),
        ),
        note="Efterfrågesidan. OBS att SCB inte samlar in lånets ändamål utan "
             "approximerar med panten — blancolån som finansierar bostadsköp "
             "saknas därför helt i serien.",
    ),
    SeriesSpec(
        key="emitterat",
        label="Emitterade räntebärande värdepapper, icke-finansiella företag",
        role="kredit",
        root="FM",
        table=r"Utestående och emitterat belopp under månaden samt räntekostnader",
        picks=(
            (r"sektor|emittent", (r"[Ii]cke-finansiell",)),
            # Utan explicit mått valdes "Räntekostnad samtliga utestående,
            # procent" — en procentsats som differentierades som vore den ett
            # kreditflöde och gav 0,1 i stället för miljarder.
            (r"^(ContentsCode|Tabellinnehåll)$", (r"[Uu]testående belopp",)),
        ),
        note="Fastighetsbolagen är tungt överrepresenterade på den svenska "
             "företagsobligationsmarknaden. Utan det här benet underskattas "
             "kreditflödet till sektorn kraftigt från mitten av 2010-talet.",
    ),

    # ---------- lager 2: nämnare ----------
    SeriesSpec(
        key="pabörjade",
        label="Påbörjade bostadslägenheter",
        role="namnare",
        root="BO",
        table=r"[Pp]åbörja.*lägenhet",
        note="Fysisk produktionsvolym. Nyckeln till att skilja kreditutbud från "
             "byggefterfrågan: faller krediten snabbare än byggandet är krediten "
             "den bindande restriktionen, faller de i takt är det efterfrågan.",
    ),
    SeriesSpec(
        key="byggkostnad",
        label="Byggkostnadsindex för bostadshus",
        role="namnare",
        root="PR",
        table=r"[Bb]yggkostnadsindex.*bostadshus",
        note="Deflator för kredit per lägenhet. Utan den går stigande "
             "kostnadsläge inte att skilja från stigande belåningsgrad.",
    ),

    # ---------- lager 3: pris ----------
    # Styrräntan finns inte i SSD — SCB publicerar den inte, den är Riksbankens.
    # Den hämtas i stället från SWEA (se riksbank.py). Utöver den absoluta
    # spreaden beräknar indicators.py en relativ ränta mot KRITA:s egen total,
    # som fungerar även när SWEA inte svarar.
    SeriesSpec(
        key="krita_ranta",
        label="Utlåningsränta till icke-finansiella företag per bransch",
        role="pris",
        root="FM/FM0002",
        table=r"utlåning till icke-finansiella företag.*bransch",
        picks=(
            (r"bransch", KRITA_BRANSCHER),
            # Medel, inte median. Utan ankaret plockades båda och adderades.
            (r"^(ContentsCode|Tabellinnehåll)$", (r"^Ränta, medel",)),
        ),
        note="Ställs mot styrräntan i indicators.py. Spreaden är det snabbaste "
             "måttet på åtstramning som finns i offentlig statistik.",
    ),
    # ---------- lager 4: bredd ----------
    SeriesSpec(
        key="krita_antal",
        label="Antal låntagande företag per bransch",
        role="bredd",
        root="FM/FM0002",
        table=r"utlåning till icke-finansiella företag.*bransch",
        picks=(
            (r"bransch", KRITA_BRANSCHER),
            (r"^(ContentsCode|Tabellinnehåll)$", (r"[Aa]ntal",)),
        ),
        note="Volym upp och antal låntagare ned = koncentration till starka "
             "balansräkningar. Det är en åtstramning som volymserien döljer.",
    ),

    # ---------- lager 5: enkät ----------
    SeriesSpec(
        key="ki_finansiella_hinder",
        label="Byggföretag: finansiella restriktioner som främsta hinder",
        role="enkat",
        base=pxweb.KONJ_BASE,
        root="",
        table=r"[Hh]inder.*[Bb]ygg|[Bb]ygg.*hinder",
        depth=4,
        note="Konjunkturinstitutet, inte SCB. Enda direkta måttet på kreditutbud "
             "i byggsektorn och det enda benet som leder de övriga.",
    ),
]

# Tidsseriebrott, serienyckel -> första månad som inte är jämförbar bakåt.
#
# Tom med flit. Övergången till SNI 2025 i februari 2026 antogs först bryta
# KRITA-serien, men det stämmer inte för den publicerade tabellen: branschen
# där är Riksbankens och SCB:s *beräknade* bransch, och den mappningen
# underhålls över SNI-bytet. Månadsförändringarna i februari 2026 (0,4-0,9 %
# beroende på bransch) ligger helt inom det normala bruset, och etiketterna är
# desamma genom hela serien 2019M07-. Antagandet kostade sex månaders färska
# observationer i flödesberäkningen — just de som en prognos behöver mest.
#
# Mekanismen är kvar för den dag ett verkligt brott inträffar. Lägg då in
# nyckeln här och kontrollera först att nivåhoppet syns i data.
BREAKS: dict[str, str] = {}


def by_key(key: str) -> SeriesSpec:
    for spec in SPECS:
        if spec.key == key:
            return spec
    raise KeyError(key)
