# Arbetsläge (överlämning mellan sessioner)

Uppdaterad 2026-09-28 ca 19:00 svensk tid. Läs detta först i en ny session.

## Var projektet står

- Gren: `claude/voter-database-demographics-r9y5la`. Slås automatiskt ihop med `main` efter varje
  lyckad CI-körning (`.github/scripts/valjare_sla_ihop.sh`). Schemat körs från main: daglig
  insamling av nyhetsflöden och följare (`valjare_media.yml`), lägesbild måndagar, allt i juni/december.
- Nätet är stängt i Claude-miljön. All hämtning sker i GitHub Actions (`valjare.yml`, körs vid push
  till grenen). Lokalt: `python bygg_db.py && python bygg_sida.py` på data som finns i repot.
- Publicerad sida (artefakt): https://claude.ai/artifact/Ln94HX5BQ9SiwfNvmw1HM5 – republicera med
  `python bygg_sida.py --utan-ram <scratchpad>/valjarbaserna.html` och Artifact-verktyget med `url`.
  Senaste publicerade version (8) är en mellanversion UTAN voteringar, Norden, genomslag och nya
  Kolada-nyckeltal.
- Sidans avsnitt: 1 Läget, 2 Min valkrets, 3 Politikens svar, 4 Områdena, 5 Genomslag, 6–15
  väljaranalys, Om databasen (kvalitetskontroll, källornas villkor). Innehållsförteckning + sidospalt.

## Session 2026-09-28 kväll (gren `ccr-5a0ec028-8z8hi6`, utgår från main 033bd26)

Granskat: riksdagsdatan ser rimlig ut (8 289 beslut 2014–2026, alla med votering; M, KD, L röstar
lika i 99,9–100 % 2022–2026, SD med dem i 87 %). Opinion_beslut: 28 av 100 förslag saknar votering.
Google-annonser: 0 rader (troligen korrekt, politiska annonser stoppade i EU hösten 2025).

Gjort:
- Hämtfel: Wikidata provar alla artiklar tills ett svenskt objekt hittas (KD), Omni-flödet borttaget
  (404), Eurostat släpper filter för dimensioner som inte finns och försöker igen (vantan: `quant_inc`,
  elpris_hush utan `product`). `fangar` (crim_pris_pop) ger fortfarande 0 rader – ej åtgärdat.
- Följare: värden mer än tre år äldre än det senaste jämförs inte (M 2018, S- och MP-ledare 2021).
- Kolada: katalogen stöder `"id:<nyckeltal>"`; 26 poster har exakta id, felvalen (U33779, U01414,
  U31809, U07488) är borttagna, namnen beskriver vad nyckeltalen mäter. Namn uppdateras vid omhämtning.
- SCB: nya serier försörjningskvot (TAB4642) och växthusgaser totalt (TAB4698); Gini (TAB1121) och
  hushållens skuldkvot (TAB4592) är inlagda men hämtas först vid nästa körning (två varningar tills dess).
  Sökmönstren i `kallor.py` för Gini, skuldkvot, trångboddhet och hyror är skärpta.
- `myndigheter.py`: Migrationsverkets beviljade uppehållstillstånd per månad och grund 2021–2026, i
  lägesbilden (ut_totalt, ut_skydd, ut_anknytning, ut_arbete, ut_studier). Asylansökningar per månad
  finns bara för 2026 (statistiken pausad), FK-filen slutar 2022 – ingen av dem används.
- `omraden.py`: nya indikatorer i rättsväsende, vård, energi och integration; luckor uppdaterade.

## CI-körning 36450527136 (klar 18:59 svensk tid)

Lyckad, inga fel i kvalitetskontrollen. Gini (TAB1121) fungerar, 2011–2024. Skuldkvoten valde fel rad
(SCB kallar den "Låneskulder i procent av disponibel inkomst") – rättat i efterföljande commit.
Eurostat `vantan` och `fangar` ger 0 rader utan felmeddelande; hämtningen loggar nu vilka koder som
finns för SE (se `fel` i `data/katalog/hamtlogg.json` efter nästa körning).

## Genomslag, utbyggt (kväll 28/9)

Nya källor i `hamta.py` (körs i `alla` och `vecka`, inte i den dagliga mediekörningen):
- `hamta_wikipedia_visningar`: sidvisningar per månad på svenska Wikipedia sedan 2015 för partiernas och
  partiledarnas artiklar (titlarna sparas nu i `wikidata_objekt.csv`, kolumn `svwiki`).
  → `data/media/wikipedia_visningar.csv`, tabell `media_wikipedia`.
- `hamta_gdelt`: GDELT DOC 2.0, svenskspråkiga artiklar som nämner partinamnet per dag sedan 2017 och deras
  ton (6 s mellan frågorna). → `data/media/gdelt.csv.gz`, tabell `media_gdelt` (andel per månad, vägd ton).
- `hamta_riksdag_aktivitet`: motioner, interpellationer och skriftliga frågor per parti och riksmöte
  (dokumentlistans `@traffar` med partifilter; L summerar L och FP). Loggar fel om partifiltret verkar
  ignoreras. → `data/riksdagen/aktivitet.csv`, tabell `media_rd_aktivitet`.
- `media.sakfragor`: sakfrågor i samma artikel som partiet, med egen ordlista `media_katalog.SAKORD`
  (partinamnen tas bort först). Tabell `media_sakfragor`. Underlaget är litet tills RSS-insamlingen pågått.

Sidan (avsnitt 5): Wikipedia-intresse (parti/partiledare, antal/andel), nyhetsandel och ton från GDELT,
sakfrågetabell och aktivitetstabell. Webbnyckeln heter `rd_partiaktivitet` (`rd_aktivitet` är upptagen av
propositionerna per fråga). Provat i Chromium med exempeldata: inga JS-fel, fungerar i 390 px.

## Följare, medieanvändning och forskning (kväll 28/9)

- Följarvärden från Wikidata var från 2018–2023 och är borttagna från sidan: bara värden från det senaste
  året visas (`media.AKTUELL_DAGAR`). Wikidata används nu för att hitta kontona (`data/media/konton.csv`).
- `hamta_foljare_matt` (körs dagligen i `--steg media`) mäter följare direkt: YouTube (kanalsidan, avrundat),
  TikTok (profilsidans JSON, med verifieringsflagga), Bluesky (öppet API), Mastodon (öppet API).
  → `data/media/foljare_matt.csv`, en rad per konto och dag. TikTok-konton som saknas i Wikidata står i
  `media_katalog.KONTON_EXTRA` (kontrollerade 28/9; L:s partikonto och S-ledarens hittades inte).
  Instagram, Facebook, Threads och X kräver inloggning eller betald åtkomst och mäts inte.
- Wikidata: etiketten `mul` används som reserv (Ulf Kristersson saknar sv-etikett).
- `media_katalog.MEDIEBAROMETERN` (Nordicom 2025, ur seminariebilderna 5 maj 2026),
  `POLITIKNYHETER_ALDER` (SOM/Mediemyndigheten 2025) och `FORSKNING` (RJ P21-0158, Ekman & Widholm 2024 x2)
  visas i avsnitt 5 ("Var finns publiken?" och "Forskningen").
- Nätet fungerar nu från Claude-miljön för de flesta källor (riksdagen, Wikidata, TikTok, YouTube, Bluesky,
  Nordicom), men inte DiVA, och Wikimedia och GDELT svarade 429 härifrån.

## Nästa steg

1. Mediebarometerns fullständiga rapport (DiVA diva2:2056759, FULLTEXT05.pdf) har räckvidd per plattform och
   ålder; lägg in den i `kallor.DOKUMENT` och tolka den i CI, där DiVA går att nå.
2. SOM: förtroende för medier efter partisympati skulle koppla medieanvändningen till partierna.
3. GDELT: körning 39 gav 0 rader (HTTP 429 och tomma svar för `sourcelang:swedish`). Hämtningen väntar nu
   20–140 s och försöker igen. Ger nästa körning fortfarande inget: byt till GDELT:s ngram-data eller stryk källan.
   Wikipedia (2 059 månadsvärden) och Eurostat `vantan` (WLIST) och `fangar` (crim_pris_cap) fungerar.

## Att tänka på

- Användaren vill ha svar på svenska och tider i svensk tid (UTC+2).
- Kolada hämtar nu bara de tre senaste åren för redan sparade nyckeltal (snabbare körningar).
- Varje gren har egen kö (`valjare-${{ github.ref }}`); en ny push ersätter bara en väntande körning.
- En schemalagd påminnelse (trigger `trig_01BqJCxYfMhscGj6iT6py9sK`, "Kolla riksdagsdatan i CI")
  är bunden till den gamla sessionen och kan tas bort.
- Utkast till förfrågningar om återpublicering (SVT, SOM, Valforskningsprogrammet) finns i
  `granskning/`; de har inte skickats.
