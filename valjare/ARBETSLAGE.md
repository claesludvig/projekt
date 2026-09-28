# Arbetsläge (överlämning mellan sessioner)

Uppdaterad 2026-09-28 ca 15:00 svensk tid. Läs detta först i en ny session.

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

## Senaste CI-körning (36417262971, klar 14:43 svensk tid)

Lyckad: hämtning, tester, bygge, commit, sammanslagning med main. Kvalitet: 111 av 114 ok, inga fel
(varningar: förnybart slutar 2021, återinskrivning slutar 2022, en Valu-rad). Datan är committad på
grenen men INTE granskad eller publicerad än. En ny körning (för 3caaa94, Kolada-cache) kan ha
startat efter den.

## Nästa steg (i ordning)

1. `git pull` och granska riktig data:
   - `data/riksdagen`: votering_*, ledamot_*, anforande_*, prop_bet.csv; tabellerna riksdag_beslut,
     riksdag_samstammighet (M, KD, L, SD bör rösta lika ofta 2022–2026), opinion_beslut.
   - `data/eurostat` och tabellen `norden`; `data/media` (foljare.csv, artiklar.csv.gz,
     google_annonser_*.csv); fel i `data/katalog/hamtlogg.json`.
2. Rätta Kolada-urvalet i `indikatorer_katalog.py` mot `data/katalog/kolada_alla_kpi.csv`
   (se `data/katalog/kolada_bred_val.csv`). Felval: "känner sig trygga" → U33779 (HVB, fel),
   "självskattad hälsa" → U01414 (tandhälsa, fel), "långvarigt bistånd" → U31809 (barn; välj N31816
   för vuxna). 19 poster utan träff: sjuk- och aktivitetsersättning, barn i ekonomiskt utsatta hushåll,
   placerade barn, förvärvsarbetande 20–64, nyanlända/etablering, utrikes födda förvärvsarbetande,
   kunskapskrav alla ämnen, behöriga gymnasiet, kostnad grundskola, förskola, undvikbar slutenvård,
   psykiatri väntetid, bostadsbrist, påbörjade bostäder, utjämning, elbilar, hushållsavfall,
   elanvändning, garantipension. Byt till exakta id (mönstret stöder bara regex i dag – lägg till
   stöd för id eller skriv `^exakt titel$`).
3. Lägg in de nya SCB-tabellerna (Gini, försörjningskvot, vistelsetid, trångboddhet, elpriser,
   skulder, hyror; se `data/katalog/scb_katalog.csv`) som serier i `verklighet_katalog.SCB_SERIER`.
4. Läs txt-översikterna för myndighetsfilerna i `data/kallor/txt` (fk_statistik, migrationsverket,
   arbetsformedlingen, bra_kriminalstatistik, kriminalvarden) och bygg tolkare för asyl per månad,
   uppklaringsandel/lagföring, beläggning, sjukfrånvaro.
5. Uppdatera `omraden.py` så att områdena använder de nya indikatorerna och stryk luckor som fyllts.
6. Bygg lokalt, `python -m pytest -q tests`, pusha, publicera artefakten och skicka länken.

## Att tänka på

- Användaren vill ha svar på svenska och tider i svensk tid (UTC+2).
- Kolada hämtar nu bara de tre senaste åren för redan sparade nyckeltal (snabbare körningar).
- Varje gren har egen kö (`valjare-${{ github.ref }}`); en ny push ersätter bara en väntande körning.
- En schemalagd påminnelse (trigger `trig_01BqJCxYfMhscGj6iT6py9sK`, "Kolla riksdagsdatan i CI")
  är bunden till den gamla sessionen och kan tas bort.
- Utkast till förfrågningar om återpublicering (SVT, SOM, Valforskningsprogrammet) finns i
  `granskning/`; de har inte skickats.
