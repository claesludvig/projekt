# OMXS30-kommentarer

Två frågor, två skript:

1. **Vilka kommenterar OMXS30 dagligen?** → `discover.py`
2. **Vad säger de?** → `collect.py`

Resultatet visas i `omxs30-kommentarer.html` i repots rot (länkad från sidomenyn i `index.html`).

## Så mäts "dagligen"

`discover.py` frågar Google News RSS på ett antal OMXS30-fraser (definierade i
`sources.json` under `sokfrasor_google_news`). Varje träff har en utgivare och ett
datum. Skriptet räknar **distinkta publiceringsdagar per utgivare** och delar med
antalet börsdagar i mätfönstret:

| andel av börsdagar | kadens |
|---|---|
| ≥ 0,60 | daglig |
| ≥ 0,35 | nästan daglig |
| ≥ 0,12 | veckovis |
| < 0,12 | sporadisk |

Det är alltså mätt på faktisk publicering, inte på vad utgivarna påstår att de gör.
Träffarna ackumuleras i `data/kommentatorer_historik.json` (rullande 180 dagar), så
bilden blir skarpare för varje körning. En enstaka körning på 30 dagar räcker för att
skilja de dagliga från de sporadiska; en månads dagliga körningar ger en stabil ranking.

Börsdagar approximeras som vardagar – röda dagar räknas alltså med, vilket drar ner
andelen någon procentenhet. Det påverkar rangordningen marginellt.

## Så hämtas texterna

`sources.json` innehåller ett register över kända kommentatorer (Placera/Direkt, DI,
EFN, Nordnetbloggen, Börskollen, Swedbank Aktiellt, tekniskanalys.org, Investtech,
Aktiespararna, Daytrading.se och r/aktiemarknaden). Varje källa har **flera
kandidat-URL:er** eftersom svenska mediesajter flyttar sina flöden.

- `check_sources.py` provar alla kandidater och skriver `data/sources_status.json`
  med vilken URL som faktiskt fungerar.
- `collect.py` använder i första hand en redan bekräftad URL, faller annars tillbaka
  på att prova kandidaterna, och sist på att skrapa listningssidan.

Varje post relevanspoängsätts (`common.RELEVANS_TERMER`) – "OMXS30" väger 5, 
"storbolagsindex" 4, "Stockholmsbörsen" 3, "börsen" 1. Poster under `--min-relevans`
(default 3) sorteras bort, så vanliga bolagsnyheter inte följer med.

## Tonläget

`common.tonlage()` är ett rakt lexikon (`POSITIVA`/`NEGATIVA` i `common.py`) som räknar
ord. Det är en grovsortering för att snabbt hitta dagar där tonen svänger – inte en
sentimentmodell. Justera listorna när du ser vad som faktiskt återkommer i texterna.

## Köra lokalt

```bash
pip install -r omxs30-kommentarer/requirements.txt
cd omxs30-kommentarer

python check_sources.py              # vilka flöden lever?
python discover.py --dagar 30        # vilka kommenterar, hur ofta?
python collect.py --dagar 3          # vad sägs just nu?
```

Nyttiga flaggor för `collect.py`: `--max-per-kalla`, `--min-relevans`,
`--utan-fulltext` (bara rubriker och ingresser, går mycket fortare).

## GitHub Actions

`.github/workflows/omxs30_kommentarer.yml` kör vardagar 17:30 UTC och kan startas
manuellt med valet `check`, `discover`, `collect` eller `allt`.

Notera att GitHub bara exponerar `workflow_dispatch` för workflows som finns på
default-branchen – kör en `check` manuellt så snart den här grenen är mergad, och
rensa bort de kandidat-URL:er som rapporteras döda.

## Datafiler

| Fil | Innehåll |
|---|---|
| `data/kommentatorer.json` | Rankade utgivare med kadens och exempelrubriker |
| `data/kommentatorer_historik.json` | Ackumulerade träffar, rullande 180 dagar |
| `data/latest_commentary.json` | Hämtade texter med relevans och ton |
| `data/dagsvy.json` | Per dag: antal, tonfördelning, återkommande teman |
| `data/sources_status.json` | Vilka kandidat-URL:er som fungerar |

## Att bygga vidare på

- `dagsvy.json` har en dagsnyckel som matchar `omxs30-yfinance/data/` – att lägga
  tonläget bredvid faktisk indexutveckling är nästa naturliga steg.
- `latest_commentary.json` innehåller fulltext, alltså tillräckligt för att köra en
  riktig sammanfattning eller sentimentmodell i stället för lexikonet.
- `sokfrasor_google_news` styr vad discovery letar efter – lägg till fraser för att
  hitta kommentatorer som inte skriver ordet OMXS30 rakt ut.
