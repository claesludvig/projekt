# Prompt för rutinen "Marknadspulsen" (v3, med OMXS30-bolagen och tradingläge)

I drift på rutinen `trig_01JfhbGz51QENm6vawia7qXC` (vardagar `0 6 * * 1-5` UTC). Ändra här och i rutinen samtidigt så att de inte glider isär. Originalet från före v2 finns i [`original/`](original/rutin_fx_rantor_backup_2026-09-23.md).

````text
Dags för Marknadspulsen. Kör igenom hela kedjan självständigt, på svenska, utan att fråga mig något.

Mailet handlar om MARKNADSRÖRELSER och om var det finns TRADINGLÄGEN i OMXS30-bolagen med högst en veckas innehav. Tabellerna och graferna är huvudsaken; din text är två korta avsnitt: vad som driver rörelserna, och vad tradingläget säger. Alla siffror kommer ur marknadspuls.json — du räknar ingenting själv och hittar aldrig på en siffra.

1. Trigga workflowen `marknadspuls.yml` i claesludvig/projekt på branch `main` (workflow_dispatch). Trigga samtidigt `ing_think_digest.yml` och `seb_research_digest.yml` på main. Polla var 30:e sekund tills alla tre är klara, max 10 minuter.

2. Misslyckades `marknadspuls.yml` (conclusion != success): hämta en kort felsammanfattning ur jobbloggen och skicka ETT kort mail via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com med ämnet "[marknadspuls]: datahämtningen misslyckades". Avsluta sedan — utan data finns inget mail att skicka. Misslyckas ING eller SEB: fortsätt med de källor som finns och nämn det i `kallor`.

3. Hämta från main via GitHub API (get_file_contents):
   - `marknadspuls/data/marknadspuls.json` — tabellerna (`tabell`), korrelationerna och grafernas URL:er (`par`), OMXS30-bolagen och tradingläget (`aktier`: `index`, `rorelser`, `kandidater`, `uttanjda`, `undvik`, `handelser`, `signalkontroll`, `uppfoljning`, `bolag`), och `fel` (instrument som saknas). `aktier` kan vara null om bolagskurserna inte gick att hämta; skriv då inget tradingavsnitt.
   - `ing-think-digest/data/latest_articles.json` och `seb-research-digest/data/latest_articles.json`. För SEB: finns samma innehåll som engelsk "Nordic Alert" och svensk "Morning Alert", använd den svenska. Hoppa över bildbaserade rapporter med <50 ord text.
   - Sök i Gmail (search_threads) efter "Slok OR Sløk OR Yardeni" och hämta de 1–2 senaste från agm@apollo.com (Torsten Sløk) och yardeni-research@ghost.io (Ed Yardeni) med get_thread, messageFormat PLAIN_TEXT. Yardeni är ofta delvis betalspärrad — använd den fria inledningen.

4. Läs tabellerna först. Vilka är de största och mest avvikande rörelserna — över 1d, men också där 1v/2v/1m visar en trend eller ett trendbrott? Vilka par har korrelationer som skiljer sig mellan 1m och 3m (ett samband som bryts eller uppstår)? Det är utgångspunkten för texten, inte vad källorna råkar skriva om. Rader märkta "per <datum>" släpar en dag hos Yahoo (vanligt för europeiska index på morgonen) — skriv inte om dem som om de gällde senaste dagen.

   Läs sedan `aktier`: hur ligger OMXS30 mot sina medelvärden och hur bred är rörelsen (`index`)? Vilka bolag sticker ut (`rorelser`)? Vilka är kandidaterna och varför (`skal`)? Vilka händelser i `handelser` träffar kandidaterna under veckan (t.ex. Riksbanken för bankerna)? Vad säger `signalkontroll` om att urvalet faktiskt fungerar, och hur gick förra veckans kandidater (`uppfoljning`)?

5. Skriv rapporten som JSON:
   {
     "title": "Rubrik som fångar dagens huvudrörelse, utan avslutande punkt",
     "ingress": "EN mening om den viktigaste rörelsen, med siffra ur tabellen.",
     "drivkrafter": "Ett stycke (3–5 meningar) om vad som driver rörelserna.",
     "punkter": [{"bold_lead": "Kort etikett", "text": "..."}],
     "kallor": [{"namn": "ING", "titel": "Artikelns titel", "url": "https://..."}],
     "trading": {
       "text": "Ett stycke (2–4 meningar) om tradingläget.",
       "punkter": [{"bold_lead": "Kort etikett", "text": "..."}]
     }
   }
   Regler:
   - Varje påstående i `drivkrafter` och `punkter` knyts till en konkret rörelse i tabellen, t.ex. "Brent −5,7 % på en vecka: Iran signalerade att Hormuzsundet kan öppnas (SEB)". Rörelse först, förklaring sedan, källa i parentes.
   - Högst 3 punkter. Hellre färre än utfyllnad.
   - Skriv bara siffror som står i marknadspuls.json eller i källtexterna. Tabellens siffror skrivs med samma avrundning som mallen visar (en decimal för %, heltal för bp). Kontrollera varje siffra i texten mot JSON-filen innan du renderar.
   - Håll isär bedömning och fakta: "ING bedömer att …", aldrig en banks prognos som konstaterat faktum.
   - Saklig prosa, inga floskler ("sammanfattningsvis", "det är värt att notera", "i en värld där"), ingen dramatisering.
   - Säger källorna inget om en stor rörelse, säg det hellre än att gissa en förklaring.
   - `trading`: bara om `aktier` finns. Högst 2 punkter. Nämn bara bolag som står i `kandidater`, `uttanjda` eller `undvik`, och bara siffror som står där. Lägg aldrig till egna kandidater, kursmål eller stoppnivåer. Skriv aldrig "köp" eller "sälj"; skriv "kandidat" och "undvik". Knyt kandidaterna till marknadsrörelserna när det går (t.ex. bankerna och räntorna, verkstad och oljan) och märk det som tolkning. Träffas en kandidat av en händelse i `handelser` under veckan: säg det. Är |t| under 2 för rekylsignalen i `signalkontroll`, eller går IC 26 v och IC 8 v åt olika håll, skriv i en mening att urvalets grund inte är säkerställd just nu. Finns `uppfoljning`: ange utfallet mot index i en bisats, även när det är dåligt. Är `kandidater` tom, skriv det i stället för att leta upp andra bolag.
   - `kallor`: de artiklar och mail du faktiskt använt. Har Sløk/Yardeni inget nytt sedan i går, skriv det som en post med titel "inget nytt".

6. Rendera med mallen i repot — skriv INTE egen HTML. Hämta `marknadspuls/mall.py` via GitHub API, spara den och marknadspuls.json i en temporär katalog tillsammans med din rapport, och kör:

   import json, sys
   sys.path.insert(0, "<katalogen med mall.py>")
   from mall import rendera, rendera_text
   html = rendera(rapport, data)        # data = marknadspuls.json
   text = rendera_text(rapport, data)

7. Skicka via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com. Ämne: "[marknadspuls] <ÅÅÅÅ-MM-DD>: " följt av `title`. htmlBody = html, body = text.

8. Svara kort i chatten (1 mening) att mailet skickats.
````
