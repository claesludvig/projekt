# Svensk politik & regeringsförhandlingar — digest

Automatiserat utskick i samma anda som `ing-think-digest` och
`seb-research-digest`: ett schemalagt jobb hämtar material, skriver JSON till
`data/` och committar. Skillnaden mot de äldre digestarna är att det här
utskicket är **inkrementellt** — varje körning innehåller bara det som inte
redan skickats ut.

## Vad som körs

| | |
|---|---|
| Schema | Ligger i Routinen på claude.ai, inte i workflowet |
| Workflow | `.github/workflows/svensk_politik_digest.yml` — bara hämtning |
| Trigger | `workflow_dispatch`, anropat av Routinen via GitHub API |
| Hemligheter | Inga |
| Commit | Bara när körningen faktiskt hittat något nytt |

## Schemalagd körning: Actions för hämtning, Routine för resten

Samma uppdelning som `chronicle-ingest` använder för poddbevakningen. Analys,
mejl och läget mellan körningar sköts av en schemalagd **Routine** på claude.ai
— inte av `claude-code-action`, inte av Claude API och inte av SMTP. Det tar
bort behovet av API-nycklar och mejlhemligheter i repot helt.

Workflowet `.github/workflows/svensk_politik_digest.yml` gör bara hämtningen,
som behöver en runner med öppet nät. Det triggas via GitHub API av Routinen,
två gånger om dagen, inte av ett eget cron-schema i filen:

```
Routine (claude.ai, schemalagd)
      │
      ├─► triggar svensk_politik_digest.yml via GitHub API, väntar in den
      │        scraper.py   RSS → ämnesfilter → dedup mot seen.json
      │                     → data/latest_articles.json, data/digest.md
      │                     → git commit i det här repot
      │
      ├─► läser data/latest_articles.json och data/sammanfattningar/ via GitHub API
      ├─► skriver den svenska analysen själv (ingen extra hemlighet)
      ├─► renderar med mall.py och mejlar via det kopplade Gmail-kontot
      └─► skriver tillbaka data/rapporter/<datum>.json och
           data/sammanfattningar/<datum>.txt via GitHub API
```

`.claude/skills/politikrapport/` innehåller stilreglerna för rapporten: ton,
JSON-formen, hur rapportering skiljs från kommentar, och att värdet ligger i
jämförelsen med förra utskicket.

### Läget mellan körningar

`data/seen.json` är minnet för vad som redan skickats, `data/sammanfattningar/`
minnet för vad som redan sagts. Båda checkas in — varken en Actions-runner
eller en Routine-session har ett filsystem som består mellan körningar, så allt
som ska överleva måste ligga i git.

### Hemligheter som måste ligga i repot

Inga. Hämtningen läser öppna RSS-flöden, analysen och mejlet sker i Routinen
som autentiserar mot GitHub och Gmail via redan kopplade konton.

## Filer i `data/`

- **`latest_articles.json`** — själva utskicket. Enbart poster som tillkommit
  sedan förra körningen, med `new_count`, `skipped`-statistik och status per
  källa.
- **`digest.md`** — samma innehåll läsbart, grupperat i *Analys och kommentar*,
  *Rapportering* och *Officiella besked*.
- **`rapporter/<datum>.json`** — rubrik, brödtext och punktlista, skriven av
  Routinen. `mall.py` renderar den till mejlets HTML.
- **`sammanfattningar/<datum>.txt`** — 3–5 meningar om läget, kontext åt nästa
  utskick. Utan dem tappar rapporten sin jämförelse mot föregående dag.
- **`seen.json`** — arkivet som gör utskicket inkrementellt. URL:er och
  rubriknycklar för allt som redan skickats, med tidsstämpel. **Filen måste
  vara committad** — utan den börjar nästa körning om från noll och upprepar
  material. Poster äldre än 180 dagar rensas bort.

## Hur dubbletter undviks

Tre spärrar, i den ordningen:

1. **URL** — normaliserad (spårningsparametrar som `utm_*` bortstädade) och
   matchad mot `seen.json`.
2. **Rubriknyckel** — normaliserad rubrikhash. Fångar samma TT-text publicerad
   hos flera avsändare med olika URL.
3. **Ålder** — poster äldre än 10 dagar tas inte med ens om de är osedda, så
   ett flöde som plötsligt börjar leverera arkivmaterial inte spränger utskicket.

## Ämnesfilter

Alla flöden är breda, så varje post prövas mot `sources.py`:

- en träff bland **ämnesorden** (`regeringsbildning`, `talman`, `sondering`,
  `vågmästar` …) räcker, eller
- minst **två olika partier** i rubrik/ingress.

Två fallgropar som filtret är byggt runt:

- **Ämnesorden är stammar, inte fulla ordformer.** Svenskan böjer i bestämd
  form och plural, så `talmansrunda` missar `talmansrundorna` medan `talmansrund`
  fångar båda. Kapa ändelsen när du lägger till ord.
- **Partiträffar räknas per parti, inte per söksträng.** Varianterna överlappar
  som delsträngar — `moderat` ligger inuti `moderaterna` — så räknade man dem
  var för sig skulle ett enda omnämnande av ett parti se ut som två träffar och
  släppa igenom vilken partinotis som helst.

Träffar sparas i `matched_terms` per post, så det går att se varför något kom
med.

Även de officiella källorna filtreras. Regeringen.se publicerar allt från
statsbesök till myndighetsuppdrag; utan filter dränkte det utskicket i material
som inte rör regeringsbildningen.

## Kommentatorer

`COMMENTATORS` i `sources.py` är en bevakningslista med namngivna politiska
kommentatorer — Viktor Barth-Kron, Ewa Stenberg, Mats Knutson, Tove Lifvendahl
med flera. Namnet matchas mot författarfält och mot rubrik/ingress (flera
svenska flöden saknar strukturerat författarfält). Träffar får `commentator`
satt och markeras `[kommentator]` i `digest.md`.

Lägg till fler genom att fylla på listan — ingen annan ändring behövs.

## Betalvägg och hämtningsfel

DN, SvD och Expressen ger sällan fulltext till en oinloggad hämtare. Sådana
poster tas **ändå med**, med rubrik och ingress från RSS och `paywall: true`
satt. Vem som skriver vad, och med vilken vinkel, är halva poängen med
kommentarsbevakningen även när brödtexten saknas.

De två fallen hålls isär i utdatan:

| Fält | Betyder |
|---|---|
| `paywall: true` | Texten hämtades men är avkortad — inloggning krävs |
| `fetch_error: "..."` | Vi kom inte fram alls; felet sparas ordagrant |

Blandades de ihop skulle ett trasigt flöde se ut som en betalvägg och felet
aldrig upptäckas. Antalet poster utan brödtext summeras i `fetch_errors`.

Hämtningen är byggd runt tre saker som skarpa körningar avslöjade:

- **Delad klient med cookies.** DN släppte igenom de tre första artiklarna och
  svarade `406 Not Acceptable` på resten när varje anrop gjordes fristående.
  En återanvänd `httpx.Client` behåller cookies och anslutning.
- **Paus per värd** (`HOST_DELAY`, 1,5 s) så vi inte stryps.
- **Andra försök vid avvisning**, och för `www.`-värdar ett försök utan
  prefixet.

Sidor avkodas via `r.text` (httpx följer serverns `Content-Type`) i stället för
råa bytes. BeautifulSoup gissar annars kodningen och gissar fel när sidan saknar
charset-deklaration — då blir å, ä och ö sönderkodade och både
betalväggsmarkörerna och ämnesfiltret slutar matcha.

### Kända begränsningar

Uppmätt i skarp drift, inte gissat:

| Källa | Läge |
|---|---|
| SVT, Expressen, regeringen.se | Fulltext, stabilt |
| DN | Flödet fungerar, men ~7 av 10 artikelhämtningar ger `406`. DN stryper datacenter-IP:n; längre pauser och cookies testades utan mätbar effekt. Posterna kommer med som rubrik + ingress + skribent |
| DN Ledare | Flödet svarar oregelbundet — uppe i en körning, `406` i nästa |
| Sveriges Radio | Artikelsidor svarar `403`. RSS-ingressen används |
| Riksdagen | Dokumentlistan fungerar; en del av dess länkar pekar på sidor som svarar `404` |

Det som går förlorat är brödtexten, inte posten. Rubrik, ingress, skribent,
kommentatorsmarkering och datum kommer med i samtliga fall.

## Tester

```bash
python svensk-politik-digest/test_scraper.py
```

Kör helt utan nätverk. Täcker ämnesfiltret (stammar, partiräkning),
dedupen mellan två körningar, åldersgränsen och skillnaden mellan betalvägg
och hämtningsfel.

## Källor som kan flytta

Svenska mediehus byter RSS-sökväg med jämna mellanrum. Varje källa i
`sources.py` har därför flera kandidat-URL:er som provas i ordning — den första
som ger poster vinner. En källa som inte svarar loggas och hoppas över; resten
av körningen fortsätter. Vilken URL som faktiskt användes syns i `sources` i
`latest_articles.json`, så det går att se när en källa tystnat.

TT har inget öppet allmänt nyhetsflöde. TT-materialet kommer in via SVT och
Ekot, som publicerar det vidare.

Riksdagen saknar RSS på `www.riksdagen.se` (svarar 404). I stället används
öppna data-API:et `data.riksdagen.se/dokumentlista` med `utformat=rss`.

## Köra lokalt

```bash
pip install -r svensk-politik-digest/requirements.txt
python svensk-politik-digest/scraper.py
```

Vill man se vad en körning skulle ge utan att röra arkivet: kopiera undan
`data/seen.json` först och lägg tillbaka den efteråt.

Och rendera ett färdigt utskick till HTML:

```python
import json, sys; sys.path.insert(0, "svensk-politik-digest")
from mall import rendera
print(rendera(
    json.load(open("svensk-politik-digest/data/rapporter/2026-09-20.json", encoding="utf-8")),
    json.load(open("svensk-politik-digest/data/latest_articles.json", encoding="utf-8")),
))
```
