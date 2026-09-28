# Väljardatabasen

En databas över politiskt intressanta variabler som visar hur partiernas väljarbaser
har förändrats över tid: vilka grupper som röstar på partierna, hur stora grupperna är
i väljarkåren, var partierna är starka geografiskt och hur utsatthet och otrygghet
fördelar sig mellan grupperna.

Sidan `index.html` börjar med två avsnitt för den som ska fatta beslut:

1. **Läget**: månadsserier (skjutningar, sprängningar, inflation, arbetslöshet, priser på el
   och drivmedel, styrräntan, konkurser, bostadsbyggande, invandring) jämförda med samma
   period i fjol och med seriens egen historik. Byggs om varje måndag; texten sparas i
   `data/lagesbild/senaste.md` och `data/lagesbild/<år>-V<vecka>.md`.
2. **Min valkrets**: riksdagens 29 valkretsar med mandat, valresultat, valdeltagande,
   valdeltagandeklyftan mellan distrikten och ett 40-tal indikatorer mot riket och de andra
   valkretsarna.

3. **Politikens svar**: riksdagens propositioner, betänkanden och voteringar sedan 2014
   (data.riksdagen.se) kopplade till sakfrågorna; hur ofta partierna röstar lika; SOM-institutets
   förslag (andel som tycker att förslaget är bra, 2022 och 2025) bredvid riksdagens beslut i
   samma sak och partiernas röster; förtroende för riksdag, regering och partier. Kopplingen
   görs med ord i rubriken och utskott (`riksdag_katalog.py`).

4. **Områdena**: fördjupning för rättsväsendet, vården, energin, försvaret och integrationen.
   Sverige över tid, jämförelse med Danmark, Finland, Norge, Island och EU-snittet (Eurostat),
   riksdagens senaste beslut, SOM-förslag, myndigheter som utvärderar området och öppet
   redovisade kunskapsluckor (`omraden.py`, `norden.py`).

5. **Genomslag**: följare per parti, partiledare och plattform (Wikidata), omnämnanden i
   redaktionernas nyhetsflöden och i Google Nyheter (samlas in dagligen av
   `.github/workflows/valjare_media.yml`), talartid i riksdagen (anföranden) och Googles
   politiska annonser. Utan API-nycklar; källor och sökmönster i `media_katalog.py`.

Därefter följer väljaranalysen (sammansättning per parti, skiftet sedan 2006, Valu,
kommunsamband, län, valdistrikt, sakfrågor och verklighet, NTU).

**Evidensnivå.** Varje avsnitt är märkt beskrivande, modellskattning eller samband, med
vad det inte kan säga (`metod.py`, tabellen `evidensniva`). Korrelationer har 95-procentiga
intervall.

**Mål i stället för värderingar.** Databasen säger inte om en utveckling är bra eller dålig.
Riktning och målnivå anges bara där riksdagen, lagen, Riksbanken eller ett internationellt
åtagande anger ett mål (`MAL` i `verklighet_katalog.py`).

## Källor

| Källa | Vad | Period |
|---|---|---|
| SCB, Partisympatiundersökningen (PSU) | Partisympati per grupp (ålder, utbildning, inkomst, födelseland, bakgrund, yrke, fack, sektor, boende, region m.m.) med felmarginaler | 1972– (ålder), 2006– (övrigt) |
| SVT:s vallokalsundersökning (Valu) | Partival per väljargrupp på valdagen; tidsserier för kvinnor, män, unga, 65+, LO, företagare | 1991–2026 |
| Valforskningsprogrammet, GU (Svenska väljare) | Sammansättningen av varje partis väljare, rapport 2026:7 | 2018, 2022 |
| SCB, valdeltagande (register) | Röstberättigade och röstande per grupp | 2018, 2022 |
| SCB, valresultat | Riksdagsval per kommun | 1973–2022 |
| Valmyndigheten | Preliminärt riksdagsval 2026 per kommun | 2026 |
| SCB, befolkning/utbildning/inkomst | Utländsk bakgrund, utbildningsnivå, ekonomisk standard, valdeltagande per kommun | 1973– (varierar) |
| Polismyndigheten | Skjutningar (avlidna, skadade) och sprängningar per polisregion och månad | 2017– / 2018– |
| SOM-institutet, Svenska trender | Viktigaste samhällsproblem (öppen fråga) | 1987–2025 |
| Valu | Frågornas betydelse för partivalet, rangordning per parti, bäst politik per område | 1998–2026 |
| SCB, KPI per produktgrupp | El, bensin, diesel, räntekostnader | 1980–2025 |
| SCB, personbilar | Bilar i trafik per kommun | 2015– |
| Valmyndigheten + SCB DeSO | Valdistrikt 2026 med strukturvariabler | 2026 |
| Kolada (RKA) | Verklighetsindikatorer per kommun/region: väntetider i vården, skolresultat, äldreomsorg, anmälda brott, långtidsarbetslöshet, ekonomiskt bistånd, låg ekonomisk standard, skattesats, utsläpp, bostadsbyggande, inkomstskillnader | 2006– |
| SCB (AKU, BNP, bostäder, invandring, medellivslängd, lön) och Riksbanken (styrränta) | Verklighetsindikatorer i riket | varierar |
| Brå, Nationella trygghetsundersökningen | Utsatthet för brott, otrygghet, oro, förtroende per grupp | 2006–2025 |
| Eurostat | Nordisk jämförelse: dödligt våld, poliser, fångar, vårdplatser, väntan på vård, elpriser, förnybart, försvar (COFOG), sysselsättning efter födelseland, asyl | 2000– |
| Riksdagen (data.riksdagen.se) | Propositioner, betänkanden, voteringar per parti och ledamot | 2014– |
| SOM-institutet, Svenska trender | Åsikter om förslag och förtroende för institutioner (senaste värdet per utgåva) | 2022, 2025 |
| Valmyndigheten | Valkretsindelning, mandat och preliminärt resultat per valkrets 2026 | 2022, 2026 |
| SCB (KPIF, AKU per månad, konkurser, påbörjade bostäder, befolkningsförändringar) | Månadsserier till lägesbilden | varierar |

## Tabeller i `data/valjare.sqlite` (och `data/csv/`)

- `partistod` – andel av en grupp som röstar på/sympatiserar med ett parti
- `gruppvikt` – gruppens andel av väljarkåren
- `partiprofil` – andel av partiets väljare i varje grupp (`parti = 'ALLA'` = hela väljarkåren)
- `valresultat_kommun`, `kommunindikator`, `kommunsamband`
- `utsatthet`, `partiexponering`
- `valdeltagande_grupp`, `valdeltagande_region`
- `valresultat_lan`, `lansindikator`, `utsatthet_lan`, `partiprofil_region` (IPF-skattning per län/kommun)
- `dekomposition` (sammansättning mot beteende)
- `valdistrikt_2026`, `valdistrikt_tiondel`, `valdistrikt_samband`
- `polisen_manad`, `kpi_manad`, `fraga_betydelse`, `fraga_rang_parti`, `bast_politik`, `som_samhallsproblem`
- `test_bilar`, `test_skjutningar`
- `verklighet`, `verklighet_forandring`, `verklighet_kommun` (indikatorer per sakfråga; katalogen i `verklighet_katalog.py`)
- `valkrets`, `valkrets_kommun`, `valresultat_valkrets`, `valkrets_indikator`, `valkrets_oversikt`
- `lagesbild`, `lagesbild_serie`
- `riksdag_dokument`, `riksdag_beslut`, `riksdag_aktivitet`, `riksdag_samstammighet`,
  `riksdag_parti_fraga`, `riksdag_ledamot`, `opinion`, `opinion_forslag`, `opinion_beslut`
- `norden`
- `media_foljare`, `media_foljare_nu`, `media_omnamnanden`, `media_google_nyheter`,
  `media_talartid`, `media_annonser`
- `evidensniva`
- `kalla`, `kontroll`, `varningar`

Exempel:

```sql
-- Andel av varje partis sympatisörer med minst tre års eftergymnasial utbildning, maj 2026
SELECT parti, round(andel, 1) FROM partiprofil
WHERE kalla = 'scb_psu' AND period = '2026M05'
  AND grupp = 'eftergymnasial utbildning 3 år eller mer';
```

## Metod i korthet

PSU redovisar partistöd inom varje grupp men inte gruppernas storlek. Storleken skattas
ur SCB:s felmarginaler (m = 1,96·√(p(1−p)/n) ⇒ n) och kalibreras för ålder,
utbildning, inkomst och födelseland mot registrets röstande 2018 och 2022, eftersom
de oviktade svarsantalen överrepresenterar äldre och högutbildade. Kontrollerna finns i
tabellen `kontroll`. Valu och Valforskningsprogrammet mäter röster, PSU sympati; källornas
gruppindelningar redovisas var för sig.

## Kvalitet, granskning och villkor

- `kontroller.py` körs efter varje bygge: aktualitet (har källan kommit med nya siffror),
  volym (har någon tabell krympt mer än 20 %) och rimlighet (349 mandat, 29 valkretsar, 290
  kommuner, andelar som summerar till 100, voteringar med alla ledamöter). Resultatet står i
  `data/kvalitet.json` och `data/kvalitet.md`, tabellen `kvalitet` och på sidan. Vid fel öppnar
  arbetsflödet ett ärende i repot, som stängs när kontrollerna är gröna igen.
- `tests/` testar tolkarna och beräkningarna före bygget (`python -m pytest -q tests`).
- `granskning/METODGRANSKNING.md` är underlag för en oberoende granskning, med antaganden,
  kontroller, kända brister och konkreta granskningsfrågor.
- `licenser.py` och `granskning/LICENSER.md` anger villkoren per källa. Tabellerna från Valu och
  Valforskningsprogrammet bör stämmas av innan sidan sprids; utkast till förfrågningar finns i
  `granskning/`.

## Köra

Nätverksåtkomst till SCB, SVT, GU, Brå och Valmyndigheten krävs. Arbetsflödet
`.github/workflows/valjare.yml` gör allt och committar resultatet:

```
pip install -r requirements.txt
python hamta.py          # rådata till data/scb, data/kallor, data/katalog
python hamta.py --steg vecka   # bara månadsserierna till lägesbilden
python bygg_db.py        # data/valjare.sqlite, data/csv, data/webb.json
python bygg_sida.py      # index.html
```

Nya SCB-tabeller läggs till i `kallor.py`. Nya verklighetsindikatorer läggs till i
`verklighet_katalog.py` (Kolada-id eller sökord, SCB-tabell och variabelval, fråga och
och eventuellt ett officiellt mål i `MAL`). Pdf-originalen sparas inte i git, bara
den extraherade texten i `data/kallor/txt`.
