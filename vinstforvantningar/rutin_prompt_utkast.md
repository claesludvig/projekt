# Utkast: prompt för rutinen "Vinstförväntningar OMXS30" (veckobrev)

Inte skapad som rutin än. Förslag på schema: måndagar 07:00 svensk tid (`0 5 * * 1` UTC under sommartid). Samma upplägg som Marknadspulsen: workflowet räknar allt, rutinen skriver bara texten.

````text
Dags för veckobrevet om vinstförväntningar. Kör igenom hela kedjan självständigt, på svenska, utan att fråga mig något.

Mailet handlar om hur ANALYTIKERNAS VINSTPROGNOSER för OMXS30-bolagen har ändrats. Tabellerna och graferna är huvudsaken. Din text är ett kort avsnitt som förklarar revideringarna. Alla siffror kommer ur vinst.json: du räknar ingenting själv och hittar aldrig på en siffra.

1. Trigga workflowen `vinstforvantningar.yml` i claesludvig/projekt på branch `main` (workflow_dispatch). Trigga samtidigt `seb_research_digest.yml` och `ing_think_digest.yml` på main. Polla var 30:e sekund tills alla är klara, max 15 minuter.

2. Misslyckades `vinstforvantningar.yml` (conclusion != success): hämta en kort felsammanfattning ur jobbloggen och skicka ETT kort mail via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com med ämnet "[vinstförväntningar]: datahämtningen misslyckades". Avsluta sedan.

3. Hämta från main via GitHub API (get_file_contents):
   - `vinstforvantningar/data/vinst.json`: indexets revideringar (`index`), bolagen (`bolag`, sorterade på nästa års prognos 1m), `storsta_hojningar`, `storsta_sankningar`, `kommande_rapporter`, `grafer` och `fel`.
   - `seb-research-digest/data/latest_articles.json` och `ing-think-digest/data/latest_articles.json`: använd bara det som rör bolagsvinster, konjunktur, räntor eller valutor som påverkar svenska bolag.
   - Sök i Gmail (search_threads) efter "from:yardeni-research@ghost.io OR from:agm@apollo.com newer_than:7d" och läs (get_thread, PLAIN_TEXT) de mail som handlar om vinster, vinstprognoser eller "forward earnings". Yardeni är ofta delvis betalspärrad: använd den fria inledningen. Hans siffror gäller USA och ska alltid anges som amerikanska.

4. Läs datan först. Vilka bolag och sektorer drar upp respektive ned indexets prognos? Är revideringarna breda (många bolag) eller smala (några stora)? Stämmer kursutvecklingen med prognoserna, eller har värderingen (P/E) gått åt ett annat håll? Vilka bolag rapporterar snart? Det är utgångspunkten för texten, inte vad källorna råkar skriva om.

5. Skriv rapporten som JSON:
   {
     "title": "Rubrik som fångar veckans viktigaste revidering, utan avslutande punkt",
     "ingress": "EN mening med den viktigaste siffran ur vinst.json.",
     "drivkrafter": "Ett stycke (3–5 meningar) om vad som driver revideringarna.",
     "punkter": [{"bold_lead": "Kort etikett", "text": "..."}],
     "kallor": [{"namn": "SEB", "titel": "Artikelns titel", "url": "https://..."}]
   }
   Regler:
   - Varje påstående knyts till en siffra i vinst.json, t.ex. "Swedbank +3,7 % på en månad för 2027".
   - Säger källorna inget om varför ett bolags prognos har ändrats, skriv det. Egen tolkning (t.ex. att bankernas höjningar hänger ihop med högre räntor) märks tydligt som tolkning och inte som fakta.
   - Högst 3 punkter. En av dem ska handla om kommande rapporter om `kommande_rapporter` inte är tom.
   - Revideringar under ±0,5 % på en månad är brus. Lyft dem inte som nyheter.
   - Saklig prosa, inga floskler, ingen dramatisering. Siffror med samma avrundning som mallen visar (en decimal).
   - `kallor`: bara det du faktiskt använt.

6. Rendera med mallen i repot. Skriv INTE egen HTML. Hämta `vinstforvantningar/mall.py` via GitHub API, spara den och vinst.json i en temporär katalog tillsammans med din rapport, och kör:

   import json, sys
   sys.path.insert(0, "<katalogen med mall.py>")
   from mall import rendera, rendera_text
   html = rendera(rapport, data)        # data = vinst.json
   text = rendera_text(rapport, data)

7. Skicka via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com. Ämne: "[vinstförväntningar] v<vecka>: " följt av `title`. htmlBody = html, body = text.

8. Svara kort i chatten (1 mening) att mailet skickats.
````
