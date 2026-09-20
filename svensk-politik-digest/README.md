# Svensk politik & regeringsförhandlingar — digest

Automatiserat utskick i samma anda som `ing-think-digest` och
`seb-research-digest`: ett schemalagt jobb hämtar material, skriver JSON till
`data/` och committar. Skillnaden mot de äldre digestarna är att det här
utskicket är **inkrementellt** — varje körning innehåller bara det som inte
redan skickats ut.

## Vad som körs

| | |
|---|---|
| Schema | 05:00 och 15:00 UTC dagligen (07:00/17:00 svensk sommartid, 08:00/18:00 vintertid) |
| Workflow | `.github/workflows/svensk_politik_digest.yml` |
| Manuell körning | `workflow_dispatch` i Actions |
| Commit | Bara när körningen faktiskt hittat något nytt |

## Filer i `data/`

- **`latest_articles.json`** — själva utskicket. Enbart poster som tillkommit
  sedan förra körningen, med `new_count`, `skipped`-statistik och status per
  källa.
- **`digest.md`** — samma innehåll läsbart, grupperat i *Analys och kommentar*,
  *Rapportering* och *Officiella besked*.
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

Nyhets- och ledarflödena är breda, så varje post prövas mot `sources.py`:

- en träff bland **ämnesorden** (`regeringsbildning`, `talmansrunda`,
  `sonderingsuppdrag`, `vågmästare` …) räcker, eller
- minst **två olika partinamn** i rubrik/ingress.

Träffar sparas i `matched_terms` per post, så det går att se varför något kom
med. Officiella källor (regeringen.se, riksdagen.se) filtreras inte — allt de
publicerar är relevant.

## Kommentatorer

`COMMENTATORS` i `sources.py` är en bevakningslista med namngivna politiska
kommentatorer — Viktor Barth-Kron, Ewa Stenberg, Mats Knutson, Tove Lifvendahl
med flera. Namnet matchas mot författarfält och mot rubrik/ingress (flera
svenska flöden saknar strukturerat författarfält). Träffar får `commentator`
satt och markeras `[kommentator]` i `digest.md`.

Lägg till fler genom att fylla på listan — ingen annan ändring behövs.

## Betalvägg

DN, SvD och Expressen ger sällan fulltext till en oinloggad hämtare. Sådana
poster tas **ändå med**, med rubrik och ingress från RSS och `paywall: true`
satt. Vem som skriver vad, och med vilken vinkel, är halva poängen med
kommentarsbevakningen även när brödtexten saknas.

## Källor som kan flytta

Svenska mediehus byter RSS-sökväg med jämna mellanrum. Varje källa i
`sources.py` har därför flera kandidat-URL:er som provas i ordning — den första
som ger poster vinner. En källa som inte svarar loggas och hoppas över; resten
av körningen fortsätter. Vilken URL som faktiskt användes syns i `sources` i
`latest_articles.json`, så det går att se när en källa tystnat.

TT har inget öppet allmänt nyhetsflöde. TT-materialet kommer in via SVT och
Ekot, som publicerar det vidare.

## Köra lokalt

```bash
pip install -r svensk-politik-digest/requirements.txt
python svensk-politik-digest/scraper.py
```

Vill man se vad en körning skulle ge utan att röra arkivet: kopiera undan
`data/seen.json` först och lägg tillbaka den efteråt.
