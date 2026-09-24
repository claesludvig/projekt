# Byggpulsen

Ett eget ledande index för svenskt byggande, räknat på serier som rör sig
före den officiella byggstatistiken. Tanken är att inte vänta på SCB:s
kvartalssiffror utan väga ihop det som syns tidigare.

## Komponenter

| Komponent | Källa | Signal | Riktning |
|---|---|---|---|
| Platsannonser, byggets andel | JobTech (Arbetsförmedlingen), historiska annonser: bygg och anläggning / alla yrken | årsförändring, 3 mån snitt | större andel = starkare |
| Bygglov för nya lägenheter | SCB (TAB2534), kvartal | årsförändring | fler bygglov = starkare |
| Statsobligation 5 år | Riksbanken (SWEA) | förändring mot för ett år sedan, procentenheter | högre ränta = svagare |
| Byggbolagens aktier | Yahoo Finance, bolagen i `byggfastighet/bolag.json`, likaviktade | årsförändring | uppgång = starkare |

Målserie för efterhandstestet: påbörjade lägenheter i nybyggda hus (SCB,
kvartal), årsförändring av rullande fyra kvartal.

Komponenter läggs till i `kallor.json` (och en hämtare i `hamta.py`).

## Egen data

Varje körning sparar dagens antal **aktiva** platsannonser (bygg och alla
yrken) i `data/annonser_dag.csv`. Serien finns inte publicerad någon annanstans
och blir längre för varje körning; ju oftare workflowet körs, desto tätare
serie.

## Metod

1. Varje serie görs om till en årsförändring och vänds så att högre alltid
   betyder starkare byggande.
2. Serierna standardiseras (z-värden).
3. Vikterna är laddningarna på första principalkomponenten, alltså den
   rörelse serierna har gemensamt. Ingen vikt är satt för hand.
   Som jämförelse räknas också ett likaviktat index.
4. Indexet mäts i standardavvikelser: 0 = normalt läge, +1 = ovanligt starkt,
   −1 = ovanligt svagt. En komponent som publiceras senare (bygglov, kvartal)
   behåller sitt senaste värde tills nästa värde normalt kommer; saknas den
   längre fördelas dess vikt på de övriga.

Andelen i stället för antalet annonser: Platsbankens totala volym svänger
kraftigt av skäl som inte är konjunktur (−46 % till +95 % på ett år), och de
senaste månaderna är ofullständiga i historik-API:t. Andelen bygg påverkas
inte av någotdera.

Konkurser i byggindustrin var tänkta som komponent men finns inte i SCB:s
API. Bolagsverkets och Tillväxtanalys data är nästa kandidat.

### Efterhandstest

Korrelationen i hela urvalet blir alltid för bra, eftersom vikterna har sett
hela historiken. `efterhandstest.realtid_pca` räknar därför om indexet för
varje månad med bara den data som då var publicerad, med vikter och
standardisering skattade på data fram till dess. Korrelationen mot
påbörjade lägenheter 0–4 kvartal senare visar om indexet faktiskt leder.

### Resultat (körning 24 september 2026)

Korrelation mellan Byggpulsen och årsförändringen i påbörjade lägenheter
k kvartal senare, realtidsversionen från juni 2020:

| Ledtid | 0 kv | 1 kv | 2 kv | 3 kv | 4 kv |
|---|---|---|---|---|---|
| Byggpulsen (PCA-vikter), realtid | 0,53 | 0,72 | **0,79** | 0,77 | 0,68 |
| Likaviktat, realtid | 0,29 | 0,49 | 0,63 | 0,71 | 0,72 |

Indexet leder alltså byggstarterna med ungefär två kvartal. Indexet fångade
raset 2022 och vändningen 2024 i förväg. Urvalet är litet (drygt 20 kvartal
i realtidstestet), så siffrorna är en indikation och inte ett bevis.

## Filer

- `hamta.py`: hämtar, räknar, ritar, skriver `data/byggpuls.json`.
  `--utan-hamtning` räknar om från sparade serier.
- `index.py`: indexmatematiken (transformer, PCA, realtidstest).
- `data/serier.csv`: månadsserierna (rådata), `data/mal.csv`: målserien.
- `data/scb_tabeller.txt`: SCB-tabeller som söktes fram och urvalet som användes.
- `data/grafer/<datum>/`: indexet mot påbörjade lägenheter och senaste månadens bidrag.

## Förbehåll

- Byggaktierna är dagens bolag bakåt i tiden (överlevnadsbias) och likaviktade.
- Platsannonserna påverkas av hur stor del av marknaden Platsbanken täcker,
  som kan ändras över tid.
- Knappt tio års månadsdata räcker till en grov validering, inte till en
  finjusterad prognosmodell.
