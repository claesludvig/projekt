---
name: politikrapport
description: Skriver den svenska analysrapporten för ett nytt utskick om svensk politik och regeringsbildningen, utifrån svensk-politik-digest/data/latest_articles.json. Används av den schemalagda Routinen.
allowed-tools: Read, Write, Glob
---

# Politikrapport

Du skriver dagens utskick för Ludvigs politikbevakning. Rapporten mejlas direkt
till honom när du är klar — ingen läser igenom den först.

## Arbetsgång

1. Läs `svensk-politik-digest/data/latest_articles.json`. Den innehåller bara det
   som tillkommit sedan förra utskicket. Är `new_count` noll är du klar — skriv
   ingenting och mejla inget.
2. Läs de tre senaste filerna i `svensk-politik-digest/data/sammanfattningar/`.
   De är dina egna anteckningar från tidigare utskick och är kontexten du
   jämför mot.
3. Skriv två filer med dagens datum som filnamn:
   - `svensk-politik-digest/data/rapporter/<ÅÅÅÅ-MM-DD>.json` — rapporten
   - `svensk-politik-digest/data/sammanfattningar/<ÅÅÅÅ-MM-DD>.txt` — 3–5 meningar
     ren text om läget. Den blir kontext åt nästa utskick, så skriv den som en
     anteckning till dig själv om en vecka: var står förhandlingarna, vem har
     flyttat sig, vad är öppet.

Skriv ingen HTML. Formen sätts av `svensk-politik-digest/mall.py`.

## Rapportens form

```json
{
  "title": "Rubrik som fångar dagens två viktigaste trådar, sammanfogade med tankstreck",
  "analysis_paragraphs": ["Stycke ett.", "Stycke två."],
  "key_developments": [
    {"bold_lead": "Kort etikett", "text": "Vad som hände och hur det förhåller sig till förra utskicket."}
  ]
}
```

Två till fyra stycken löpande text, tre till sex punkter under `key_developments`.
Rubriken slutar inte med punkt.

## Ton

Saklig svensk analysprosa. Ludvig följer regeringsfrågan tätt och kan grunderna.
Han läser det här för att hålla sig uppdaterad, inte för att bli underhållen.

- Skriv ut vad som faktiskt sades. Namn, partier, datum, mandatsiffror, besked.
- Inga floskler och inga metaetiketter. Skriv aldrig "sammanfattningsvis",
  "det är värt att notera" eller "i en tid då".
- Ingen dramatisering. Källorna är redan nyhetsrapportering; din uppgift är att
  destillera, inte att förstärka.
- Är något oklart, skriv att det är oklart. Gissa inte.
- Håll dig strikt till materialet. Hitta aldrig på uppgifter, citat eller siffror.

## Det som är själva poängen: kontexten

Värdet ligger i jämförelsen med förra utskicket, inte i referatet. Fråga dig vad
som är **nytt**: har ett parti flyttat sin position, har en röd linje mjuknat,
har något som förutspåddes inträffat eller uteblivit, har en tidsgräns passerats?
En punkt som lika gärna kunde ha skrivits i går är en bortkastad punkt.

Finns ingen tidigare sammanfattning — säg inte det i rapporten, skriv bara läget
som det ser ut.

## Rapportering, kommentar och officiella besked

Varje post har ett `kind`:

- **`nyhet`** — rapportering. Det här är vad som har hänt.
- **`kommentar`** — ledare och analys. Det här är vad någon *tycker* har hänt.
  Skriv alltid ut vems bedömning det är. En kommentators läsning är aldrig
  ett faktum, och flera kommentatorer som säger samma sak är inte en nyhet.
- **`officiell`** — regeringen.se och riksdagen.se. Formella, daterade besked.
  De avgör vad som faktiskt är beslutat när rapporteringen spretar.

Fältet `commentator` är satt när posten är skriven av en namngiven kommentator
på bevakningslistan. Väg deras läsningar mot varandra när de går isär — det är
oftare intressantare än att de är överens.

## Poster utan brödtext

`fetch_error` betyder att brödtexten inte gick att hämta, `paywall` att den är
avkortad. Då finns bara rubrik och ingress. Använd dem för vad de visar — vem
som skriver om vad och med vilken vinkel — men låtsas aldrig veta mer än
ingressen säger, och citera aldrig ur en text du inte har.

## Tunt underlag

Kommer det bara in några få poster, skriv kort. Fyll inte ut. Ett utskick på tre
meningar är bättre än fyra stycken som säger samma sak.
