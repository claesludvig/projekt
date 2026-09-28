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

## Nästa steg

1. Kör CI (push till `claude/voter-database-demographics-r9y5la` eller manuellt) så att Kolada-
   nyckeltalen med nya id och SCB-tabellerna TAB1121/TAB4592 hämtas. Kontrollera att varningarna
   för Gini och skuldkvot försvinner.
2. Eurostat `fangar`: hitta rätt dataset/filter (0 rader).
3. Brå (uppklaring, lagföring) och Kriminalvården (beläggning) saknas fortfarande i `data/kallor`.
4. Publicera artefakten efter CI-körningen.

## Att tänka på

- Användaren vill ha svar på svenska och tider i svensk tid (UTC+2).
- Kolada hämtar nu bara de tre senaste åren för redan sparade nyckeltal (snabbare körningar).
- Varje gren har egen kö (`valjare-${{ github.ref }}`); en ny push ersätter bara en väntande körning.
- En schemalagd påminnelse (trigger `trig_01BqJCxYfMhscGj6iT6py9sK`, "Kolla riksdagsdatan i CI")
  är bunden till den gamla sessionen och kan tas bort.
- Utkast till förfrågningar om återpublicering (SVT, SOM, Valforskningsprogrammet) finns i
  `granskning/`; de har inte skickats.
