# sellpy-bevakning

Bevakar Sellpy efter plagg som matchar ett filter och säger till när något nytt
dyker upp.

Sellpys sidor är en JavaScript-app. Filtren och träfflistorna renderas i
webbläsaren och finns inte i sidkällan, så varken `curl` eller en vanlig
HTML-parser ser produkterna. Skriptet kör därför en riktig Chromium via
Playwright.

## Installation

```
pip install -r requirements.txt
playwright install chromium
```

Har du redan en Chromium, peka på den med `--chromium <sökväg>` eller
miljövariabeln `SELLPY_CHROMIUM` i stället för att ladda ner en till.

## Användning

Bygg filtret i Sellpys eget gränssnitt, kopiera adressen ur webbläsaren och
skicka in den med `--url`. Då slipper skriptet gissa hur Sellpy kodar filter i
adressen, vilket är det enda som brukar gå sönder.

```
python sellpy_bevakning.py \
  --url "https://www.sellpy.se/..." \
  --marke Uniqlo --storlek M --maxpris 50 \
  --uteslut hoodie huvtröja luvtröja --enfargat
```

Utan `--url` gissar skriptet `sellpy.se/store/brand/<märke>`.

Alla villkor prövas dessutom om i Python på det som faktiskt hämtades, så
träfflistan stämmer även om Sellpys egna filter tolkade adressen annorlunda.

### Löpande bevakning

```
python sellpy_bevakning.py --url "..." --intervall 30 \
  --kommando "notify-send 'Sellpy' '{antal} nya: {första}'"
```

Kör om var 30:e minut. Plagg som setts förut ligger i `data/sedda.json`, så bara
verkligt nya träffar märks `NY` och utlöser `--kommando` (`{antal}` och
`{första}` byts ut). Radera filen för att nollställa.

## Hur produkterna hittas

Sellpys CSS-klasser är genererade och byts vid varje release, så skriptet läser
inte DOM:en. I stället lyssnar det på sidans JSON-svar och letar igenom dem
efter objekt som *ser ut* som produkter: något prisfält plus något namn- eller
märkesfält. Nyckelnamnen står överst i `sellpy_bevakning.py` och är gissningar —
de täcker de vanliga stavningarna, men Sellpy kan förstås använda andra.

Går något fel, kör med `--inspect`. Då sparas alla JSON-svar i `data/inspekt/`
och det första produktliknande objektet skrivs ut, så att nyckellistorna kan
rättas mot verkligheten.

## Att hålla ögonen på

- **Priser.** Sellpy kan rapportera pris i kronor eller i ören. Skriptet gissar
  på fördelningen och skriver ut vad det kom fram till. Blir det fel, tvinga med
  `--prisenhet kr` eller `--prisenhet ore`.
- **Mönster.** `--enfargat` fäller bara det som är *bevisat* mönstrat. Plagg
  utan mönsterdata visas som `okänt` och följer med — hellre det än att tyst
  dölja en träff. Kolla bilden innan du köper.
- **Storlek.** `M` matchar även `Medium` och fält som listar flera storlekar
  (`S, M`). Storlekar utanför XS–XL jämförs rakt av.
- Skriptet blockerar bilder och typsnitt och pausar mellan scroll-varven, så det
  belastar Sellpy ungefär som en vanlig besökare. Dra inte ner `--paus` i onödan.

## Status

Logiken är testad mot syntetiska svar och webbläsardelen mot en lokal attrapp
med samma form (XHR-laddad lista, cookie-ruta, infinite scroll). Den är ännu
**inte** körd mot sellpy.se — nyckelnamn och adressform kan behöva rättas vid
första riktiga körningen. `--inspect` finns just för det.
