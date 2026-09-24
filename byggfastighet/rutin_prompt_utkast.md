# Utkast: prompt för rutinen "Bygg & fastighet" (veckobrev)

Inte skapad som rutin än. Förslag på schema: måndagar 07:30 svensk tid (`30 5 * * 1` UTC under sommartid), efter vinstbrevet. På måndag morgon har Yahoo fredagens stängningskurser för Stockholmsbörsen. På vardagsmorgnar släpar Yahoo ofta en dag.

````text
Dags för veckobrevet om bygg och fastighet. Kör igenom hela kedjan självständigt, på svenska, utan att fråga mig något.

Mailet handlar om hur de svenska BYGG- OCH FASTIGHETSBOLAGEN har rört sig och varför, med de svenska räntorna som den viktigaste förklaringen. Tabellerna och graferna är huvudsaken. Din text är ett kort avsnitt. Alla siffror kommer ur byggfastighet.json: du räknar ingenting själv och hittar aldrig på en siffra.

1. Trigga workflowen `byggfastighet.yml` i claesludvig/projekt på branch `main` (workflow_dispatch). Den tar 2–3 minuter, eftersom Riksbankens API kräver pauser mellan anropen. Trigga samtidigt `seb_research_digest.yml` och `ing_think_digest.yml` på main. Polla var 30:e sekund tills alla är klara, max 15 minuter.

2. Misslyckades `byggfastighet.yml` (conclusion != success): hämta en kort felsammanfattning ur jobbloggen och skicka ETT kort mail via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com med ämnet "[bygg & fastighet]: datahämtningen misslyckades". Avsluta sedan.

3. Hämta från main via GitHub API (get_file_contents):
   - `byggfastighet/data/byggfastighet.json`: `tabell` (index, bolag, räntor), `samband` (korrelation och räntekänslighet mot 5-årsräntan), `prognoser_bygg`, `kommande_rapporter`, `grafer`, `anmarkningar` och `fel`.
   - `seb-research-digest/data/latest_articles.json` och `ing-think-digest/data/latest_articles.json`: använd det som rör Riksbanken, svenska räntor, bostadsmarknaden, byggandet eller fastighetsbolag.

4. Läs datan först. Hur har 2- och 5-årsräntan rört sig, och har fastighetsbolagen följt räntan som räntekänsligheten säger? Går bygg och fastighet åt olika håll? Vilka bolag avviker från sin sektor, och är det bolagsspecifikt? Har byggbolagens vinstprognoser ändrats? Det är utgångspunkten för texten.

5. Skriv rapporten som JSON:
   {
     "title": "Rubrik som fångar veckans viktigaste rörelse, utan avslutande punkt",
     "ingress": "EN mening med den viktigaste siffran ur byggfastighet.json.",
     "drivkrafter": "Ett stycke (3–5 meningar) om vad som driver sektorerna.",
     "punkter": [{"bold_lead": "Kort etikett", "text": "..."}],
     "kallor": [{"namn": "SEB", "titel": "Artikelns titel", "url": "https://..."}]
   }
   Regler:
   - Varje påstående knyts till en siffra i byggfastighet.json. Räntor i bp och heltal, kurser i % med en decimal, samma avrundning som mallen visar.
   - Håll isär fakta och bedömning: "SEB räknar med att …", aldrig en banks prognos som konstaterat faktum. Egen tolkning märks tydligt som tolkning.
   - Rader i tabellen med "per <datum>" släpar en dag: skriv inte om dem som om de gällde den senaste dagen.
   - Står något i `anmarkningar` (misstänkta hopp i en ränteserie): bygg ingen slutsats på den serien.
   - Högst 3 punkter. Saklig prosa, inga floskler, ingen dramatisering.
   - `kallor`: bara det du faktiskt använt.

6. Rendera med mallen i repot. Skriv INTE egen HTML. Hämta `byggfastighet/mall.py` via GitHub API, spara den och byggfastighet.json i en temporär katalog tillsammans med din rapport, och kör:

   import json, sys
   sys.path.insert(0, "<katalogen med mall.py>")
   from mall import rendera, rendera_text
   html = rendera(rapport, data)        # data = byggfastighet.json
   text = rendera_text(rapport, data)

7. Skicka via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com. Ämne: "[bygg & fastighet] v<vecka>: " följt av `title`. htmlBody = html, body = text.

8. Svara kort i chatten (1 mening) att mailet skickats.
````
