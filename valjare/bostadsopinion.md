# Bostadsopinionen: vad väljarna tycker och hur viktigt de tycker att det är

Sammanställning ur Valforskningsprogrammet (Svenska väljare/Valundersökningen), SOM-institutet
(nationellt, Göteborg, Västsverige) och SVT:s Valu, kompletterad med intressentbeställda
mätningar där forskningsdata saknas. Siffrorna finns i `data/bostadsopinion/`:

| Fil | Innehåll |
|---|---|
| `tidsserier.csv` | Aggregerade serier: hur viktig bostadsfrågan är (1979–2025) och åsikter om förslag |
| `som_forslag_grupper.csv` | SOM: sju bostadsförslag per kön, ålder, utbildning, boendeområde, ideologi och politiskt intresse (byggs av `bostadsopinion.py`) |
| `partier.csv` | Per parti: marknadshyror (2018, 2022), bostadsfrågans vikt och rang (2018, 2022) |
| `psu_partisympati_boendeform.csv` | SCB PSU: partisympati i villa, bostadsrätt och hyresrätt, maj 2006–2026, med felmarginaler |

## Slutsatser

1. **Bostadsfrågan är en av de minst prioriterade frågorna nationellt, och har blivit det
   alltmer.** I SOM:s öppna fråga om viktiga samhällsproblem nämner 1 procent bostäder
   2022–2025, lägst av 17 områden alla fyra åren. Toppen var 7 procent 1988 och 2015.
   I Valundersökningen har bostäder inte nämnts av mer än 2 procent som viktig fråga för
   partivalet sedan 1994.
2. **Lokalt är frågan betydligt viktigare.** I Göteborg nämner 10–18 procent bostadsfrågor
   som stadens viktigaste problem (14 procent 2025, upp från 10). I Västra Götaland var
   bostäder den fjärde viktigaste kommunala frågan 2016 (18 procent) men har fallit till 7.
3. **Motståndet mot marknadshyror är stort men har krympt.** Andelen som tycker att det är
   ett dåligt förslag föll från 53 till 35 procent 2021–2024, andelen positiva steg från 15
   till 24. Inget parti har en majoritet för förslaget bland sina väljare, och ingen
   demografisk grupp i SOM är positiv.
4. **Ideologi skiljer mer än demografi.** Kön, utbildning och boendeort ger skillnader på
   några procentenheter; vänster–höger ger skillnader på 25–45 procentenheter
   (marknadshyror, allmännyttan, fastighetsskatt). Undantaget är ränteavdraget, där
   ideologin nästan inte skiljer.
5. **Ägt boende har ett starkt skydd i opinionen.** Att återinföra fastighetsskatten får
   14 procent stöd (2025), bland de lägsta av SOM:s förslag det året. Däremot hade ett
   sänkt ränteavdrag fler för än emot 2021 (34 mot 29 procent).
6. **Allmännyttan och billiga bostäder har brett stöd.** 50 procent vill förbjuda
   utförsäljning av allmännyttan (14 procent emot, 2024), 64 procent vill bygga fler
   billiga bostäder med enkel standard (13 procent emot, 2023).
7. **De unga är mest osäkra.** 16–29-åringarna svarar oftare "varken bra eller dåligt" på
   nästan alla bostadsförslag (53 procent om marknadshyror och 59 procent om allmännyttan
   2024). Det gäller även förslag som riktar sig till dem: billiga enkla bostäder får
   51 procent stöd bland unga mot 75 bland 65+.

## 1. Hur viktig är bostadsfrågan?

### Riket, öppna frågor

| År | SOM: viktigt samhällsproblem | Valundersökningen: viktig för partivalet |
|---|---|---|
| 1979 | – | 5 |
| 1982 | – | 2 |
| 1985 | – | 2 |
| 1988 | 7 | 4 |
| 1991 | 5 | 5 |
| 1994 | 1 | 1 |
| 1998 | 1 | 0 |
| 2002 | 3 | 2 |
| 2006 | 2 | 1 |
| 2010 | 2 | 1 |
| 2014 | 3 | 1 |
| 2015 | 7 | – |
| 2018 | 4 | 2 |
| 2022 | 1 | 1 |
| 2025 | 1 | – |

Procent av samtliga som nämner frågan (högst tre svar). SOM har årliga värden 1987–2025 i
`tidsserier.csv`. Toppen 2015–2016 sammanföll med flyktingmottagandet och debatten om
bostadsbristen; nedgången efter 2018 med att lag och ordning, energi och ekonomi tog över.

### Riket, slutna frågor (Valu)

- 34 procent (2014) och 32 procent (2018) sa att bostadsfrågan hade *mycket stor betydelse*
  för partivalet, plats 14–15 av 19. SVT ställde inte frågan 2022 och 2026.
- 2018 var frågan relativt sett viktigast för V-väljare (plats 8 av 19) och minst viktig för
  C- och M-väljare (plats 16).
- Valundersökningen 2022: 6,0 procent av V-väljarna nämnde bostäder som viktig fråga, mot
  1,2 procent av alla. V var också det enda parti som väljarna uppfattade att det drev
  bostadsfrågan (4,8 procent nämnde det, övriga partier under 0,3).

### Regionalt (SOM)

| År | Göteborg: viktigaste problem i staden | Västra Götaland: viktigaste kommunala fråga |
|---|---|---|
| 2012 | – | 10 |
| 2014 | – | 11 |
| 2015 | – | 15 |
| 2016 | 18 | 18 |
| 2018 | 14 | 14 |
| 2020 | 12 | 10 |
| 2022 | 11 | 9 |
| 2023 | 10 | 7 |
| 2024 | 10 | 7 |
| 2025 | 14 | – |

## 2. Marknadshyror

### Över tid

| År | Källa | Bra förslag | Dåligt förslag | Netto |
|---|---|---|---|---|
| 2018 | Novus/Hyresgästföreningen | – | ca 70 | – |
| 2021 | SOM | 15 | 53 | −38 |
| 2022 | Valundersökningen ("på nya hyresrätter") | 20 | – | – |
| 2023 | SOM | 19 | 48 | −29 |
| 2024 | SOM | 24 | 35 | −11 |
| 2026 | Indikator/Hyresgästföreningen | 7 | 69 | −62 |

SOM-serien är jämförbar mellan åren (samma formulering). Förskjutningen 2021–2024 kommer
mest från att de negativa blivit neutrala (32 → 41 procent "varken bra eller dåligt"),
inte från att många blivit positiva. Indikators formulering ("ett system där hyresvärden
ensidigt får bestämma hyran") är laddad och beställd av en part i frågan; den kan inte
jämföras med SOM.

### Per grupp (SOM, andel bra / dåligt förslag)

| Grupp | 2021 | 2023 | 2024 |
|---|---|---|---|
| Samtliga | 15 / 53 | 19 / 48 | 24 / 35 |
| Kvinnor | 12 / 56 | 17 / 50 | 22 / 35 |
| Män | 16 / 52 | 21 / 45 | 26 / 36 |
| 16–29 år | 13 / 49 | 18 / 37 | 14 / 33 |
| 30–49 år | 14 / 51 | 20 / 49 | 27 / 36 |
| 50–64 år | 15 / 59 | 19 / 49 | 26 / 34 |
| 65+ år | 14 / 54 | 18 / 49 | 23 / 38 |
| Låg utbildning | 13 / 56 | 16 / 45 | 20 / 32 |
| Hög utbildning | 15 / 53 | 22 / 53 | 26 / 40 |
| Ren landsbygd | 14 / 39 | 17 / 40 | 27 / 29 |
| Stad/större tätort | 14 / 55 | 19 / 50 | 23 / 36 |
| Stockholm/Göteborg/Malmö | 15 / 61 | 24 / 53 | 25 / 42 |
| Klart till vänster | 4 / 86 | 8 / 75 | 14 / 65 |
| Varken vänster eller höger | 14 / 48 | 19 / 40 | 22 / 28 |
| Klart till höger | 27 / 37 | 30 / 38 | 38 / 22 |

- Storstäderna är mest polariserade: flest "mycket dåligt" (39 procent 2021) men också
  något fler positiva. Landsbygden är mest neutral, där berörs få av frågan.
- "Klart till höger" blev 2024 den enda gruppen med fler positiva än negativa (38 mot 22).
- Bland unga steg inte stödet 2024 (14 procent) – i stället ökade de neutrala.

### Per parti

| Parti | Novus 2018: bra idé | Valundersökningen 2022: bra förslag |
|---|---|---|
| V | 1 | 5 |
| S | 3 | 11 |
| MP | 7 | 8 |
| SD | 22 | 24 |
| KD | 24 | 24 |
| C | 24 | 24 |
| M | 28 | 32 |
| L | 34 | 32 |
| Samtliga | – | 20 |

Ordningen mellan partierna är densamma i två olika undersökningar fyra år isär. SD-väljarna
ligger på borgerlig nivå trots att partiet i riksdagen har varit emot marknadshyror.

### Per boendeform (Indikator för Hyresgästföreningen)

- 2024: bostadsrättsägare 10 procent bra / 69 procent nej; hyresgäster 6 / 77.
  Högst stöd bland C- och M-väljare (17 procent). SD-väljarna oftast osäkra (22 procent
  vet ej). Län: Uppsala 16 procent för, Västmanland 2 procent, Västerbotten 82 procent emot.
- 2026: ägare mer positiva än hyresgäster, men under 10 procent i alla boendeformer; högst
  stöd bland män i storstäder med hög inkomst och ägt boende.

SOM och Valundersökningen redovisar inte åsikterna per boendeform; det kräver mikrodata
(se avsnitt 6).

## 3. Ägt boende: ränteavdrag och fastighetsskatt

**Sänka ränteavdraget på bostadslån (SOM 2021):** 34 procent bra, 29 dåligt, 37 neutrala.

- Unga mest positiva (40 / 12), 50–64 år minst (30 / 36).
- Både "klart till vänster" (41 / 19) och mitten (40 / 23) är positiva; bara höger är
  negativ ("klart till höger" 30 / 44). Gradienten är svag jämfört med andra bostadsfrågor.
- Bolånetagare är negativa: 62 procent emot, 26 för (Demoskop för Bostadsrätterna 2021).

**Återinföra fastighetsskatten (SOM 2025):** 14 procent bra, 54 dåligt.

| Grupp | Bra | Dåligt |
|---|---|---|
| 16–29 år | 11 | 36 |
| 30–49 år | 20 | 43 |
| 50–64 år | 8 | 64 |
| 65+ år | 13 | 64 |
| Låg utbildning | 9 | 60 |
| Hög utbildning | 18 | 52 |
| Ren landsbygd | 10 | 61 |
| Storstad | 17 | 48 |
| Vänster (0–3) | 25 | 37 |
| Höger (7–10) | 7 | 70 |

Motståndet är störst bland 50–64-åringar, som oftast äger sin bostad och har störst
värdeökning. Även till vänster är fler emot än för. Bolånetagare: 73 procent emot
(Demoskop 2021).

## 4. Allmännyttan och byggande

**Förbjud utförsäljning av allmännyttan (SOM 2024):** 50 procent bra, 14 dåligt.
Klart till vänster 77 / 6, klart till höger 32 / 28 – även högergruppen är svagt positiv.
65+ 57 procent, 16–29 år 27 procent (59 procent neutrala). Storstäderna 56 procent.

**Göteborg – ta bort möjligheten att ombilda kommunala hyresrätter till bostadsrätter:**
41 (2023), 38 (2024), 37 procent bra (2025).

**Öka byggandet av billiga bostäder med mycket enkel standard (SOM 2023):** 64 procent bra,
13 dåligt. Inga ideologiska skillnader (61–64 procent i alla grupper), men stora efter ålder
(16–29: 51, 65+: 75) och utbildning (låg: 72, hög: 55).

**Göteborg – förtäta befintliga bostadsområden:** 30–36 procent bra 2017–2020. Bygga bostäder
på Heden: 29 (2016) → 23 procent (2021).

## 5. Boendeform som skiljelinje i partivalet (SCB PSU, maj)

| Parti | Hyresrätt 2006 | Hyresrätt 2026 | Bostadsrätt 2006 | Bostadsrätt 2026 | Villa 2006 | Villa 2026 |
|---|---|---|---|---|---|---|
| S | 48,4 | 33,0 | 39,8 | 36,6 | 37,9 | 32,9 |
| V | 9,1 | 16,7 | 5,5 | 7,7 | 4,5 | 5,0 |
| M | 20,1 | 13,3 | 31,1 | 17,9 | 30,2 | 20,6 |
| SD | – | 18,9 | – | 11,2 | – | 20,8 |
| MP | 5,7 | 6,6 | 6,4 | 8,6 | 4,0 | 5,2 |
| C | 3,7 | 3,9 | 3,3 | 8,4 | 7,9 | 6,8 |

- V har nästan fördubblats bland hyresgäster och är där tre gånger så stort som bland
  villaägare.
- S tappade 15 procentenheter bland hyresgäster 2006–2026; 2026 är S lika stort i hyresrätt
  som i villa. Värdet för maj 2026 är ett enskilt mättillfälle (felmarginaler i filen).
- SD är svagast i bostadsrätt (11 procent) och lika starkt i hyresrätt och villa (19–21).
- Bostadsrättsägarna har gått från M till S, MP och C.

Detta är partisympati, inte åsikter om bostäder; det visar vilka väljargrupper som bär
partiernas bostadspolitik.

## 6. Begränsningar och nästa steg

- **Grupperna är små.** SOM:s grupper har 140–800 svarande; för en grupp med 200 svarande är
  felmarginalen ±5–7 procentenheter. Förändringar på 3–4 enheter i en grupp är inte säkra.
- **Mätningarna är få.** SOM har ställt marknadshyrefrågan tre gånger (2021, 2023, 2024),
  de övriga bostadsförslagen en gång var. Någon lång serie om bostadsåsikter finns inte i
  de publicerade rapporterna; de långa serierna gäller bara frågans vikt.
- **Valu har slutat fråga om bostäder** efter 2018.
- **Intressentbeställda mätningar** (Hyresgästföreningen, Bostadsrätterna) redovisas för
  att de bryter ned per boendeform, men formuleringarna gynnar beställaren.
- **Finare nedbrytningar** (t.ex. hyresgäster under 35 i storstad, eller åsikt per parti i
  SOM) kräver mikrodata. SOM-undersökningarna och Valundersökningarna finns hos Svensk
  nationell datatjänst (SND) och innehåller boendeform, ålder, inkomst, ort och partival.

## Källor

- SOM-institutet, *Allmänhetens åsikter om politiska förslag* [2021](https://www.gu.se/sites/default/files/2022-08/36.%20Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202021_v2.pdf),
  [2023](https://www.gu.se/sites/default/files/2024-04/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202023.pdf),
  [2024](https://www.gu.se/sites/default/files/2025-04/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202024.pdf),
  [2025](https://www.gu.se/sites/default/files/2026-06/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202025.pdf)
- SOM-institutet, [Svenska trender 1986–2025](https://www.gu.se/sites/default/files/2026-03/Svenska%20trender%201986-2025.pdf),
  [Göteborgstrender 2016–2025](https://www.gu.se/sites/default/files/2026-05/G%C3%B6teborgstrender%202016-2025_0.pdf),
  [Västsvenska trender 1998–2024](https://www.gu.se/sites/default/files/2025-11/V%C3%A4stsvenska%20trender%201998-2024.pdf)
- Valforskningsprogrammet, [Swedish Voting Behavior 1956–2022, rapport 2026:4](https://www.gu.se/sites/default/files/2026-04/R2026_4_SVB.pdf), tabell 3;
  partirapporterna 2025:4–2025:11 och Vänsterpartiets väljare 2025 (Valundersökningen 2022, tabellerna A5, A12, A14)
- SVT/Valu, Riksdagsvalen 2014–2018 (i `data/kallor/txt/valu_rd_2014_2018.txt`)
- SCB, Partisympatiundersökningen, tabell TAB3251 (boendeform)
- Hem & Hyra, [Majoritet mot marknadshyror i ny undersökning](https://www.hemhyra.se/nyheter/majoritet-mot-marknadshyror-ny-undersokning/) (Novus, aug 2018)
- Hyresgästföreningen, [Ny undersökning: överväldigande majoritet emot marknadshyror](https://via.tt.se/pressmeddelande/3485676/ny-undersokning-overvaldigande-majoritet-av-svenskarna-emot-marknadshyror?publisherId=3236613&lang=sv) (Indikator, 2024),
  [Sju av tio svenskar säger nej till marknadshyror](https://via.tt.se/pressmeddelande/4329542/sju-av-tio-svenskar-sager-nej-till-marknadshyror?publisherId=3236613&lang=sv) (Indikator, 2026)
- Bostadsrätterna, [Ökad rörlighet – till vilket pris?](https://www.bostadsratterna.se/nyheter/artiklar/2021/oekad-rorlighet-till-vilket-pris) (Demoskop, 2021)
