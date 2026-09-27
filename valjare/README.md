# Väljardatabasen

En databas över politiskt intressanta variabler som visar hur partiernas väljarbaser
har förändrats över tid: vilka grupper som röstar på partierna, hur stora grupperna är
i väljarkåren, var partierna är starka geografiskt och hur utsatthet och otrygghet
fördelar sig mellan grupperna.

Sidan `index.html` visar databasen i diagram (sammansättning per parti mot hela
väljarkåren, skiftet sedan 2006, Valu 1991–2026, kommunsamband 1973–2026, NTU).

## Källor

| Källa | Vad | Period |
|---|---|---|
| SCB, Partisympatiundersökningen (PSU) | Partisympati per grupp (ålder, utbildning, inkomst, födelseland, bakgrund, yrke, fack, sektor, boende, region m.m.) med felmarginaler | 1972– (ålder), 2006– (övrigt) |
| SVT:s vallokalsundersökning (Valu) | Partival per väljargrupp på valdagen; tidsserier för kvinnor, män, unga, 65+, LO, företagare | 1991–2026 |
| Valforskningsprogrammet, GU (Svenska väljare) | Sammansättningen av varje partis väljare, rapport 2026:7 | 2018, 2022 |
| SCB, valdeltagande (register) | Röstberättigade och röstande per grupp | 2018, 2022 |
| SCB, valresultat | Riksdagsval per kommun | 1973–2022 |
| Valmyndigheten | Preliminärt riksdagsval 2026 per kommun | 2026 |
| SCB, befolkning/utbildning/inkomst | Utländsk bakgrund, utbildningsnivå, ekonomisk standard, valdeltagande per kommun | 1973– (varierar) |
| Brå, Nationella trygghetsundersökningen | Utsatthet för brott, otrygghet, oro, förtroende per grupp | 2006–2025 |

## Tabeller i `data/valjare.sqlite` (och `data/csv/`)

- `partistod` – andel av en grupp som röstar på/sympatiserar med ett parti
- `gruppvikt` – gruppens andel av väljarkåren
- `partiprofil` – andel av partiets väljare i varje grupp (`parti = 'ALLA'` = hela väljarkåren)
- `valresultat_kommun`, `kommunindikator`, `kommunsamband`
- `utsatthet`, `partiexponering`
- `valdeltagande_grupp`
- `kalla`, `kontroll`, `varningar`

Exempel:

```sql
-- Andel av varje partis sympatisörer med minst tre års eftergymnasial utbildning, maj 2026
SELECT parti, round(andel, 1) FROM partiprofil
WHERE kalla = 'scb_psu' AND period = '2026M05'
  AND grupp = 'eftergymnasial utbildning 3 år eller mer';
```

## Metod i korthet

PSU redovisar partistöd inom varje grupp men inte gruppernas storlek. Storleken skattas
ur SCB:s felmarginaler (m = 1,96·√(p(1−p)/n) ⇒ n) och kalibreras för ålder,
utbildning, inkomst och födelseland mot registrets röstande 2018 och 2022, eftersom
de oviktade svarsantalen överrepresenterar äldre och högutbildade. Kontrollerna finns i
tabellen `kontroll`. Valu och Valforskningsprogrammet mäter röster, PSU sympati; källornas
gruppindelningar redovisas var för sig.

## Köra

Nätverksåtkomst till SCB, SVT, GU, Brå och Valmyndigheten krävs. Arbetsflödet
`.github/workflows/valjare.yml` gör allt och committar resultatet:

```
pip install -r requirements.txt
python hamta.py          # rådata till data/scb, data/kallor, data/katalog
python bygg_db.py        # data/valjare.sqlite, data/csv, data/webb.json
python bygg_sida.py      # index.html
```

Nya SCB-tabeller läggs till i `kallor.py`. Pdf-originalen sparas inte i git, bara
den extraherade texten i `data/kallor/txt`.
