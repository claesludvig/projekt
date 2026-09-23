# Arbetsutkast: Marknadspulsen v2, med data först

Status: **utkast, inget är byggt och ingenting körs.** Den gamla rutinen (`trig_01TkoGSFWagxXtcuG6x5EbtH`) kör vidare oförändrad. Den ordagranna kopian ligger i [`original/`](original/rutin_fx_rantor_backup_2026-09-23.md).

## Vad som ändras

| | Idag (v1) | Ny (v2) |
|---|---|---|
| Fokus | Nyhetsbrev: text om ING/SEB/Sløk | **Marknadsrörelser**: tabeller och grafer först, text sist |
| Marknadsdata | 5 amerikanska ETF-proxyer (EWD, EWG …) via Twelve Data, bara dag % + trendstyrka | Riktiga index, räntor, valutor och råvaror via yfinance, **1d / 2d / 3d / 1v / 2v / 1m** |
| Grafer | Inga | **Linjediagram per tillgångspar, 1 månad**: t.ex. olja mot OMXS30 |
| Text | 1–2 stycken + 4–6 punkter | **Ett kort avsnitt** "Vad driver marknaden": 1 stycke + max 3 punkter |
| Siffror | Modellen räknar själv ur API-svaret | Räknas i Python (GitHub Actions); modellen skriver bara om dem |
| HTML | Inklistrad i prompten | Mall i repot (`marknadspuls/mall.py`), samma upplägg som politikbevakningen |

## Mailets layout (utkast)

```
MARKNADSPULSEN — 2026-09-24                        (rubrik = dagens huvudrörelse)

1. AKTIER             Senast    1d     2d     3d     1v     2v     1m
   OMXS30             3 318   +0,4%  +0,9%  ...
   DAX                ...
   Euro Stoxx 50
   S&P 500
   Nasdaq 100
   VIX (nivå, punkter)

2. RÄNTOR (förändring i bp)
   US 2Y / US 10Y / (SE 10Y, DE 10Y — se öppna frågor)

3. VALUTOR (%)
   EUR/USD, USD/SEK, EUR/SEK, EUR/NOK

4. RÅVAROR (%)
   Brent, guld, koppar

5. SAMBAND — 1 MÅNAD (linjediagram, båda serierna indexerade till 100)
   [graf] OMXS30 mot Brent             korrelation 1m: −0,42  (3m: −0,10)
   [graf] OMXS30 mot US 10Y
   [graf] EUR/USD mot US 10Y
   [graf] USD/SEK mot OMXS30

6. VAD DRIVER MARKNADEN (kort)
   1 stycke + max 3 punkter ur ING, SEB, Sløk/Yardeni. Varje påstående
   kopplas till en rörelse i tabellerna ovan, t.ex. "Brent −4 % på en vecka:
   Hormuz-beskedet (SEB)".

   Källor · genererad automatiskt
```

Cellerna färgas grönt/rött efter tecken. Räntor visas i baspunkter och inte i procent, samma logik som `correlation_analysis.py` redan använder för `^TNX`.

## Instrument (första förslag)

Kontrollera varje ticker i den första testkörningen på Actions. Från den här sandlådan går det inte att nå Yahoo.

| Grupp | Namn | yfinance-ticker | Anmärkning |
|---|---|---|---|
| Aktier | OMXS30 | `^OMX` (fallback: 1h-proxy ur `market.db`) | `^OMXS30` gav bara en rad på `1d`, se `correlation_analysis.py` |
| | DAX | `^GDAXI` | |
| | Euro Stoxx 50 | `^STOXX50E` | |
| | S&P 500 | `^GSPC` | |
| | Nasdaq 100 | `^NDX` | |
| | VIX | `^VIX` | nivå + förändring i punkter |
| Räntor | US 10Y | `^TNX` | ×10 = bp |
| | US 2Y | `2YY=F` eller `^IRX` (3M) | osäker, testas |
| Valutor | EUR/USD | `EURUSD=X` | |
| | USD/SEK | `SEK=X` / `USDSEK=X` | |
| | EUR/SEK | `EURSEK=X` | |
| | EUR/NOK | `EURNOK=X` | |
| Råvaror | Brent | `BZ=F` | redan i `market.db` |
| | Guld | `GC=F` | |
| | Koppar | `HG=F` | |

## Beräkningar

- **Perioder:** 1d, 2d, 3d = 1, 2 och 3 handelsdagar bakåt. 1v, 2v, 1m = senaste stängning på eller före datum −7, −14 och −30 kalenderdagar. Kalenderdagar gör perioderna jämförbara mellan marknader med olika helgdagar.
- **Förändring:** % för priser, bp för räntor, punkter för VIX.
- **Korrelation:** Pearson på dagliga förändringar (inte på nivåer, eftersom två trendande serier alltid ser korrelerade ut) över senaste månaden (~21 handelsdagar). 3 månader visas bredvid som referens, så att man ser om sambandet har ändrats.
- **Graf:** båda serierna indexerade till 100 i periodens början och ritade på samma axel. Räntan visas som nivå på en högeraxel eftersom den inte går att indexera på ett meningsfullt sätt.

## Arkitektur

```
Rutin (08:00 vardagar)
 ├─ triggar marknadspuls.yml        ← NYTT: yfinance → tabell-JSON + PNG-grafer
 ├─ triggar ing_think_digest.yml    (som idag)
 ├─ triggar seb_research_digest.yml (som idag)
 ├─ läser Sløk/Yardeni i Gmail      (som idag)
 ├─ skriver bara avsnitt 6, som JSON (ingen siffra hittas på, allt kommer ur marknadspuls.json)
 ├─ renderar med marknadspuls/mall.py
 └─ skickar via Gmail
```

Nya filer:
- `marknadspuls/hamta.py`: hämtar alla instrument (inkrementellt i `market.db`, som idag), räknar tabellen och korrelationerna och skriver `data/marknadspuls.json` och `data/graf_*.png`.
- `marknadspuls/mall.py`: `rendera(rapport, data)` → HTML + textversion.
- `.github/workflows/marknadspuls.yml`

Twelve Data behövs inte längre. Det ger färre API-gränser och index i stället för ETF-proxyer.

## Beslut

- **Räntor:** amerikanska räcker (3M, 2Y, 10Y, 30Y).
- **Par i graferna:** OMXS30–Brent, OMXS30–US 10Y, EUR/USD–US 10Y, USD/SEK–OMXS30.
- **Grafer i mejlet:** repot är publikt, så PNG:erna committas under `data/grafer/<datum>/` och länkas via `raw.githubusercontent.com`. En katalog per dag gör att gamla mejl behåller sina bilder. Kataloger äldre än 30 dagar rensas.
- **Parallellkörning mot v1:** avgörs senare.

## Status

- [x] `hamta.py`: data, tabell, korrelationer och grafer (testad lokalt på syntetisk data)
- [x] `mall.py`: HTML + text (kontrollerad på 375 px mobilbredd)
- [x] `.github/workflows/marknadspuls.yml`: har tillfälligt en push-trigger på utvecklingsbranchen för test
- [x] `rutin_prompt_utkast.md`
- [ ] Första körningen mot riktig Yahoo-data: vilka tickers fungerar?
- [ ] Merga till main (ta bort push-triggern först) och skapa eller byt rutin
