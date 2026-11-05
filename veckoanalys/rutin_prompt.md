# Rutin: Veckoanalys av marknadsläget

Körs söndag och onsdag 11.35 svensk tid (`CRON_TZ=Europe/Stockholm 35 11 * * 0,3`). Söndagen sammanfattar förra veckan och tar sikte på veckan som kommer. Onsdagen stämmer av läget halvvägs. Mallen ligger i [`mall.py`](mall.py).

````text
Dags för veckoanalysen av marknadsläget. Kör igenom hela kedjan självständigt, på svenska, utan att fråga mig något.

Avgör först vilken utgåva det är utifrån dagens veckodag (svensk tid):
- SÖNDAG = "Inför veckan". Förklara vad som hände förra veckan och varför, och ta sedan sikte på veckan som kommer: vilka händelser, data och rapporter som kan ändra bilden.
- ONSDAG = "Halvvägs". Stäm av veckan hittills mot söndagens bild: vad som har bekräftats, vad som har ändrats och vad som återstår fram till fredag.
Annan veckodag (manuell körning): välj den utgåva som ligger närmast.

1. Hämta underlag. Repot är claesludvig/projekt. Läs med GitHub API (get_file_contents) från branch `main`, utom mallen (se steg 5):
   - `marknadspuls/data/marknadspuls.json`: senaste marknadsrörelser och korrelationer.
   - `vinstforvantningar/data/vinst.json`: revideringar av vinstprognoser för OMXS30, bredd, värdering (kurs mot prognos) och `kommande_rapporter`.
   - `seb-research-digest/data/latest_articles.json` och `ing-think-digest/data/latest_articles.json`. För SEB: använd den svenska Morning Alert om samma innehåll finns på engelska.
   - Gmail (search_threads + get_thread, PLAIN_TEXT), senaste 7 dagarna (onsdag: sedan söndagen): "subject:marknadspuls", "subject:podd", "subject:politik", samt "from:yardeni-research@ghost.io OR from:agm@apollo.com". Yardeni är ofta betalspärrad: använd den fria inledningen.
   - Onsdag: läs också söndagens "[veckoanalys]"-mail (from:ludvig.uggla@gmail.com subject:veckoanalys), så att du kan ställa veckan mot den bilden.
   - Webben (WebSearch) för det som underlaget saknar: veckans kalender (centralbanker, KPI/KPIF, BNP, jobbdata), svenska bolagsrapporter de närmaste dagarna och utfall som publicerats sedan underlaget hämtades.
   - Om något saknas eller inte går att hämta, fortsätt med det som finns och skriv det i `underlag`.

2. Hitta tesen innan du skriver. Vad är den viktigaste spänningen i läget just nu, alltså det som skiljer sig från hur marknaden eller den gängse tolkningen ser på saken? Exempel på bra teser: två marknader läser samma nyhet olika; en risk flyttar från en kanal till en annan; vinstbilden och kursutvecklingen går åt olika håll. En analys som bara återger veckans rörelser har misslyckats. Onsdag: tesen ska säga något nytt jämfört med söndagens utgåva, inte samma tes med nya siffror.

3. Skriv i Ludvigs prognosstil:
   - Sammanhängande, resonerande prosa. Inga punktlistor, ingen fetstil och inga siffertabeller i texten.
   - Långa meningar med bisatser, varvade med korta meningar som fäller avgörandet. Stycken på 4–6 meningar.
   - Opersonlig och analytisk ton: inget "jag" eller "vi". Bedömningen ska framgå av hur argumenten vägs.
   - Graderat sannolikhetsspråk ("det mest sannolika är", "talar för", "riskerar att"). En bedömning ska ha en riktning även när den är osäker.
   - Förklara kausala kedjor: varför aktörer beter sig som de gör. Läs marknadsbeteende som evidens om förväntningar.
   - Historiska analogier bara när de bär ett argument om mekanism.
   - Få siffror, 2–4 per sektion, och bara när de bär ett argument. Skriv tal med ord där det går ("närmare en femtedel"). Använd bara siffror som står i underlaget.
   - Ange källan i prosan ("enligt SEB", "Apollos Torsten Sløk pekar på"). Håll isär bedömning och fakta: en banks prognos är en bedömning, aldrig ett konstaterat faktum.
   - Svensk Stockholmsbörs, kronan och Riksbanken ska alltid ha en egen sektion. Ta med vinstförväntningarna när vinst.json har något nytt att säga.
   - Sista sektionen heter "Bedömning". Den ska hålla isär vad som står fast och vad som har blivit osäkrare.
   - Inga floskler ("sammanfattningsvis", "det är värt att notera") och ingen dramatisering.

4. Skriv rapporten som JSON:
   {
     "etikett": "Veckoanalys · Inför veckan" eller "Veckoanalys · Halvvägs",
     "datum": "Söndag 8 november 2026",
     "title": "Rubrik som bär tesen, utan avslutande punkt",
     "dek": "Två meningar som sammanfattar tesen.",
     "sektioner": [{"rubrik": "Kort, påståendebärande rubrik", "stycken": ["...", "..."]}],
     "att_folja": "En mening om de viktigaste händelserna framåt, med datum.",
     "kallor": [{"namn": "SEB", "titel": "Artikelns titel", "url": "https://..."}],
     "underlag": "Underlag även från ... Saknades: ..."
   }
   4–6 sektioner med 1–2 stycken var. Söndag: börja med förra veckan och låt de sista sektionerna före "Bedömning" handla om veckan som kommer.

5. Rendera med mallen. Skriv INTE egen HTML. Hämta `veckoanalys/mall.py` med get_file_contents från `main`. Finns den inte där, använd branch `claude/zealous-bardeen-682fzm`. Spara den i en temporär katalog och kör:

   import json, sys
   sys.path.insert(0, "<katalogen med mall.py>")
   from mall import rendera, rendera_text
   html = rendera(rapport)
   text = rendera_text(rapport)

6. Skicka via Gmail (send_message, inte draft) till ludvig.uggla@gmail.com. Ämne: "[veckoanalys] " följt av `title`. htmlBody = html, body = text.

7. Svara kort i chatten (1 mening) att mailet skickats.
````
