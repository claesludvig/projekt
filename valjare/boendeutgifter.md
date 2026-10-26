# Boendeutgifter som andel av inkomsten

Hur stor del av den disponibla inkomsten som går till boendet, per inkomstgrupp, ålder,
hushållstyp, upplåtelseform, region och födelseland. Två källor kompletterar varandra:

| Källa | Mått | Grupper | År |
|---|---|---|---|
| SCB, Boendeutgifter (tidigare HEK) | *Boendeutgiftsprocent*: hushållets boendeutgift i procent av disponibel inkomst, median | Upplåtelseform × ålder, hushållstyp, region, lägenhetstyp | 2004–2013, 2015, 2017, 2020, 2021, 2024 |
| Eurostat, EU-SILC (SCB:s ULF/SILC) | Boendekostnadernas andel av disponibel inkomst (median och medel); andel med *hög boendekostnadsbelastning* (över 40 procent) | Inkomstkvintil, fattigdomsstatus, ålder, kön, hushållstyp, upplåtelseform, urbaniseringsgrad, födelseland | 2004–2025, årligen |

Data i `data/boendeutgifter/` (`scb_boendeutgifter.csv`, `eurostat_boendekostnader.csv`),
hämtade med `python boendeutgifter.py`.

**Måtten skiljer sig.** SCB räknar amortering som boendeutgift för ägda bostäder och drar av
bostadsbidrag och skatteeffekter; EU-SILC räknar räntor men inte amortering och drar av
bostadsbidrag från både kostnad och inkomst. SCB:s andel för ägare blir därför högre.
SCB bytte design 2020 med mindre urval; jämför över det året med försiktighet.

## Slutsatser

1. **Inkomsten avgör mest.** Hushåll under fattigdomsgränsen (60 procent av medianinkomsten)
   lägger i median 38 procent av inkomsten på boendet, övriga 17 procent (2025). 42 procent
   av personerna i den lägsta inkomstfemtedelen har boendekostnader över 40 procent av
   inkomsten; i de tre översta femtedelarna är det under 3 procent.
2. **Belastningen har ökat sedan 2022.** Medianandelen steg från 16,0 procent (2020) till
   18,8 (2025), den högsta sedan 2009. Andelen med hög belastning steg från 8,3 till 10,8
   procent; i lägsta femtedelen från 33 till 42 procent. Ökningen kom med räntorna,
   elpriserna och avgiftshöjningarna 2022–2024.
3. **Hyresgäster betalar störst andel, men ägarna har ökat mest.** Median 2024: hyresrätt
   27 procent, bostadsrätt 21, äganderätt 18 (SCB). Hyresgästernas andel är oförändrad sedan
   2015; villaägarnas har stigit 3,5 procentenheter. Bland unga ägare (30–39 år) har andelen
   stigit 5–7 enheter i både villa och bostadsrätt.
4. **Ensamstående och äldre bär tyngst.** Ensamstående kvinnor 65+ i hyresrätt lägger 37
   procent; sammanboende ägare utan barn 15. Ensamboende har fem gånger så ofta hög
   belastning som par (29 mot 6 procent, 2025).
5. **Unga vuxna och nyanlända.** 18–24-åringar har oftare hög belastning (15 procent) än
   befolkningen (11), men skillnaden har krympt sedan 2005 (då 23 procent). Utrikes födda har
   nästan dubbelt så ofta hög belastning som inrikes födda (19 mot 10 procent).
6. **Skuldfria äldre ägare är den nya riskgruppen.** Andelen ägare utan lån med hög
   belastning har fördubblats, från 6–8 procent före 2020 till 14 procent 2024–2025.
   Det är framför allt pensionärer med låg inkomst och stigande drift-, el- och
   avgiftskostnader.

## 1. Inkomst

### Efter fattigdomsstatus (EU-SILC)

| År | Median, under 60 % | Median, över 60 % | Medel, under 60 % | Medel, över 60 % | Medel, samtliga |
|---|---|---|---|---|---|
| 2005 | 43,6 | 18,8 | 52,2 | 21,7 | 24,5 |
| 2010 | 34,9 | 16,0 | 45,1 | 18,5 | 22,3 |
| 2015 | 35,6 | 15,5 | 45,9 | 18,2 | 22,6 |
| 2019 | 34,8 | 14,8 | 44,8 | 17,8 | 22,2 |
| 2022 | 35,9 | 15,1 | 46,3 | 18,0 | 22,2 |
| 2024 | 38,7 | 16,8 | 48,9 | 20,6 | 24,6 |
| 2025 | 38,2 | 17,3 | 47,3 | 20,2 | 24,2 |

Procent av disponibel inkomst. "Under 60 %" = hushåll med inkomst under 60 procent av
medianinkomsten (EU:s risk för fattigdom).

### Hög boendekostnadsbelastning efter inkomstkvintil (EU-SILC)

Andel personer i hushåll där boendekostnaderna är över 40 procent av den disponibla inkomsten.

| År | Kvintil 1 (lägst) | 2 | 3 | 4 | 5 (högst) | Samtliga |
|---|---|---|---|---|---|---|
| 2005 | 36,2 | 6,9 | 2,4 | 0,9 | 0,1 | 9,2 |
| 2010 | 33,5 | 5,1 | 0,5 | 0,1 | 0,2 | 7,8 |
| 2015 | 34,6 | 7,2 | 1,5 | 0,1 | 0,1 | 8,7 |
| 2019 | 37,6 | 7,8 | 1,0 | 0,4 | 0,1 | 9,4 |
| 2020 | 32,9 | 7,3 | 0,7 | 0,3 | 0,2 | 8,3 |
| 2022 | 37,6 | 6,8 | 0,7 | 0,4 | 0,1 | 9,1 |
| 2024 | 40,7 | 9,9 | 2,5 | 0,4 | 0,0 | 10,6 |
| 2025 | 41,7 | 9,1 | 2,8 | 0,7 | 0,1 | 10,8 |

Problemet finns nästan bara i de två nedersta femtedelarna. 2022–2025 spred det sig något
uppåt: i tredje femtedelen gick andelen från under 1 till nästan 3 procent.

### Boendeutgift i kronor efter inkomstkvartil (SCB)

SCB redovisar inte boendeutgiftsprocent per inkomstgrupp, bara utgiften i kronor (medel,
tkr per år, kvartil av disponibel inkomst per konsumtionsenhet):

| Kvartil | 2020 | 2021 | 2024 | Förändring 2020–2024 |
|---|---|---|---|---|
| Första (lägst) | 67 | 77 | 90 | +34 % |
| Andra | 82 | 90 | 102 | +25 % |
| Tredje | 92 | 97 | 125 | +35 % |
| Fjärde (högst) | 116 | 119 | 143 | +23 % |

Höginkomsthushållen betalar 1,6 gånger mer i kronor, men inkomsten är flera gånger högre,
så andelen blir lägre. I lägsta kvartilen ökade ägarnas utgift mest (äganderätt 65 → 106 tkr).

## 2. Ålder

### Boendeutgiftsprocent efter hushållsföreståndarens ålder och upplåtelseform (SCB, median)

| Ålder | Hyresrätt 2015 | Hyresrätt 2024 | Bostadsrätt 2015 | Bostadsrätt 2024 | Äganderätt 2015 | Äganderätt 2024 | Samtliga 2015 | Samtliga 2024 |
|---|---|---|---|---|---|---|---|---|
| 18–29 | 26,4 | 26,6 | 20,8 | 26,7 | 20,0 | – | 24,7 | 26,6 |
| 30–39 | 25,4 | 25,3 | 18,8 | 23,9 | 18,6 | 25,3 | 21,4 | 25,2 |
| 40–49 | 25,5 | 26,9 | 18,8 | 19,5 | 14,4 | 18,5 | 18,6 | 21,2 |
| 50–59 | 25,3 | 24,1 | 17,5 | 17,3 | 14,0 | 15,2 | 18,4 | 18,2 |
| 60–64 | 23,8 | 26,2 | 18,4 | 16,4 | 12,0 | 15,3 | 16,7 | 21,2 |
| 65–69 | 28,7 | 30,1 | 18,4 | 17,2 | 13,7 | 14,7 | 18,6 | 19,8 |
| 70–79 | 38,3 | 34,4 | 25,2 | 22,5 | 15,3 | 17,3 | 23,7 | 24,4 |
| 80+ | 39,0 | 33,1 | 31,7 | 24,7 | 16,1 | 18,8 | 32,7 | 24,9 |
| Alla | 28,2 | 27,3 | 20,5 | 21,1 | 14,6 | 18,1 | 20,8 | 22,6 |

Felmarginalen för en åldersgrupp (samtliga) är ±1–3 procentenheter 2024.

- **U-format:** andelen är högst bland de yngsta och de äldsta, lägst vid 50–59 år.
- **Unga ägare har fått det mycket dyrare:** 30–39-åringar i äganderätt gick från 18,6 till
  25,3 procent och i bostadsrätt från 18,8 till 23,9. Bland hyresgäster i samma ålder är
  andelen oförändrad.
- **De äldsta har fått det något bättre:** 80+ har sjunkit från 32,7 till 24,9 procent.
  Tabellerna säger inte varför.

### Hög belastning och median efter ålder (EU-SILC)

| År | Median <18 | Median 18–64 | Median 65+ | Över 40 %: 18–24 | 25–29 | 18–64 | 65+ |
|---|---|---|---|---|---|---|---|
| 2005 | 18,6 | 18,9 | 24,7 | 22,6 | 12,7 | 8,8 | 16,7 |
| 2010 | 16,2 | 16,4 | 21,8 | 19,5 | 14,7 | 8,2 | 9,9 |
| 2015 | 15,4 | 16,2 | 20,8 | 18,1 | 12,8 | 8,9 | 11,5 |
| 2019 | 14,7 | 15,7 | 20,7 | 16,9 | 11,9 | 9,4 | 12,2 |
| 2022 | 14,6 | 16,0 | 21,0 | 16,9 | 14,9 | 9,4 | 13,6 |
| 2025 | 16,8 | 18,3 | 22,0 | 15,4 | 14,7 | 10,9 | 15,2 |

Kön: kvinnor 11,0 och män 10,6 procent med hög belastning 2025; skillnaden finns främst bland
ensamstående äldre (se nedan).

## 3. Hushållstyp

### SCB, median 2024 (2015 inom parentes)

| Hushållstyp | Hyresrätt | Bostadsrätt | Äganderätt | Samtliga |
|---|---|---|---|---|
| Ensamstående kvinna 18–64 utan barn | 30,6 (31,3) | 24,6 (22,6) | – | 29,5 (27,4) |
| Ensamstående man 18–64 utan barn | 28,2 (28,3) | 24,5 (20,1) | 20,3 (21,2) | 26,0 (25,0) |
| Ensamstående kvinna 65+ | 36,5 (41,1) | 28,1 (32,5) | 25,6 (23,3) | 32,9 (36,2) |
| Ensamstående man 65+ | 34,2 (36,0) | 24,2 (24,5) | 24,0 (19,2) | 28,2 (28,2) |
| Ensamstående med barn | 30,2 (33,1) | 27,3 (24,8) | 22,8 (20,1) | 27,8 (28,6) |
| Sammanboende utan barn 18–64 | 19,5 (17,5) | 16,5 (15,0) | 14,8 (12,6) | 17,0 (14,8) |
| Sammanboende utan barn 65+ | 22,8 (25,2) | 13,8 (16,2) | 14,4 (13,0) | 15,8 (15,1) |
| Sammanboende med barn | 19,4 (21,8) | 20,1 (17,5) | 19,7 (15,4) | 19,7 (17,2) |

### Hög belastning efter hushållstyp (EU-SILC, procent över 40 %)

| Hushållstyp | 2005 | 2015 | 2022 | 2025 |
|---|---|---|---|---|
| Ensamboende kvinna | 30,9 | 27,0 | 26,6 | 30,7 |
| Ensamboende man | 25,9 | 25,1 | 23,7 | 27,8 |
| Ensamboende 65+ | 33,0 | 25,8 | 28,1 | 32,5 |
| Ensamstående med barn | 15,3 | 12,6 | 8,0 | 14,7 |
| Två vuxna utan barn | 4,0 | 4,0 | 5,3 | 5,8 |
| Två vuxna med barn | 2,8 | 3,0 | 2,6 | 3,4 |

Ensamstående föräldrar har lägre belastning än ensamboende tack vare bostadsbidrag och
barnbidrag, men deras andel nästan fördubblades 2022–2025.

## 4. Upplåtelseform och region

### Upplåtelseform över tid (SCB, median)

| År | Hyresrätt | Bostadsrätt | Äganderätt | Samtliga |
|---|---|---|---|---|
| 2004 | 28,9 | 23,9 | 19,5 | 24,4 |
| 2008 | 27,3 | 21,2 | 16,8 | 21,7 |
| 2013 | 27,9 | 19,5 | 15,7 | 20,8 |
| 2015 | 28,2 | 20,5 | 14,6 | 20,8 |
| 2017 | 28,2 | 20,2 | 15,8 | 21,0 |
| 2020 | 26,8 | 20,5 | 16,4 | 21,5 |
| 2021 | 27,1 | 18,8 | 16,2 | 20,5 |
| 2024 | 27,3 | 21,1 | 18,1 | 22,6 |

2004–2013 är HEK och inte helt jämförbart med 2015–.

### Hög belastning efter upplåtelseform (EU-SILC)

| År | Ägare med lån | Ägare utan lån | Hyresgäst (marknadsmässig hyra) |
|---|---|---|---|
| 2005 | 3,0 | 7,7 | 20,5 |
| 2010 | 3,6 | 7,2 | 15,9 |
| 2015 | 3,0 | 6,2 | 18,7 |
| 2019 | 2,7 | 7,9 | 19,8 |
| 2022 | 2,8 | 10,2 | 17,7 |
| 2024 | 4,7 | 14,0 | 17,9 |
| 2025 | 4,6 | 14,0 | 18,4 |

### Region (SCB, median 2024)

| Region | Hyresrätt | Bostadsrätt | Äganderätt | Samtliga |
|---|---|---|---|---|
| Stor-Stockholm | 27,7 | 20,6 | 17,5 | 22,4 |
| Stor-Göteborg | 27,2 | 20,1 | 18,3 | 23,7 |
| Kommuner > 75 000 inv. | 27,1 | 21,7 | 18,0 | 22,7 |
| Kommuner < 75 000 inv. | 27,4 | 21,8 | 18,2 | 22,2 |

Inom samma upplåtelseform är andelen nästan lika i hela landet; högre inkomster i
storstäderna väger upp högre kostnader. Skillnaden syns i stället i urbaniseringsgrad
(EU-SILC, median 2025): städer 20,9, mindre tätorter 17,7, landsbygd 17,3 procent.
Hög belastning: städer 13,1, tätorter 9,7, landsbygd 8,0 procent.

### Lägenhetsstorlek (SCB, median 2024)

Hyresrätt: 1 rum 27,7, 2 rum 29,9, 3 rum 25,3, 4 rum 24,4 procent. De små lägenheterna har
störst andel eftersom de bebos av ensamhushåll med en inkomst.

## 5. Födelseland (EU-SILC, 18 år och äldre, procent över 40 %)

| År | Inrikes födda | Utrikes födda | Födda i annat EU-land | Födda utanför EU |
|---|---|---|---|---|
| 2005 | 9,5 | 17,5 | 16,2 | 18,5 |
| 2010 | 7,8 | 12,1 | 13,8 | 11,1 |
| 2015 | 8,1 | 15,0 | 15,6 | 14,7 |
| 2019 | 8,2 | 17,5 | 17,0 | 17,6 |
| 2022 | 8,6 | 16,2 | 17,4 | 15,8 |
| 2025 | 10,0 | 18,7 | 19,1 | 18,6 |

## 6. Upplevd börda (EU-SILC)

Andel som upplever boendekostnaden som en *tung* börda: 13 procent 2005, 7 procent 2015,
10 procent 2023. Bland hushåll under fattigdomsgränsen 22 procent 2023 (18 procent 2015).
Frågan ställs inte varje år; senaste värdet är 2023.

## Begränsningar

- SCB:s grupper bygger på ett urval; efter 2020 är urvalet mindre och felmarginalerna för
  ålder × upplåtelseform 2–5 procentenheter. Celler med "–" är för osäkra för att redovisas.
- SCB redovisar inte boendeutgiftsprocent per inkomstgrupp; EU-SILC gör det bara som andel
  med hög belastning. Mediankvoten per kvintil kräver mikrodata (SCB:s HEK eller EU-SILC
  via Eurostat).
- Boendeutgiften omfattar inte hushåll i andrahand, studentbostäder och seniorboenden (SCB).
- Inkomstgrupperna i EU-SILC avser personer, i SCB hushåll.

## Källor

- SCB, [Statistikdatabasen](https://www.statistikdatabasen.scb.se/), ämnet Hushållens ekonomi: TAB4557,
  TAB4377, TAB1178, TAB1179, TAB1182, TAB4551 (Boendeutgifter 2015–2024) och TAB830 (HEK 2004–2013), hämtade via
  `https://statistikdatabasen.scb.se/api/v2/tables/`
- Eurostat, EU-SILC: [ilc_mded01](https://ec.europa.eu/eurostat/databrowser/view/ilc_mded01/default/table),
  [ilc_lvho08a](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho08a/default/table),
  [ilc_lvho08b](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho08b/default/table),
  [ilc_lvho07a](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07a/default/table)–[ilc_lvho07e](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho07e/default/table),
  [ilc_lvho26](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho26/default/table),
  [ilc_lvho28](https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho28/default/table),
  [ilc_mded04](https://ec.europa.eu/eurostat/databrowser/view/ilc_mded04/default/table)
