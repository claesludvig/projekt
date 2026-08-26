# omxs30-yfinance

Automatisk datahämtning av OMXS30 (`^OMXS30`) från Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance).

Standard: 15-minutersintervall, senaste månaden (`period="1mo"`, `interval="15m"`).

> Yahoo Finance begränsar hur långt tillbaka intradagsdata går: `15m`-data finns max 60 dagar tillbaka, `1m` bara 7 dagar. En månad ryms alltså gott och väl inom gränsen.

## Installation

```bash
cd omxs30-yfinance
pip install -r requirements.txt
```

## Körning

```bash
python fetch_omxs30.py
```

Detta sparar två filer i `data/`:
- `omxs30_15m_<timestamp>.csv` – tidsstämplad historik över varje körning
- `omxs30_15m_latest.csv` – alltid senaste hämtningen

Valfria flaggor:

```bash
python fetch_omxs30.py --ticker "^OMXS30" --period 1mo --interval 15m
```

## Analys: MA20/MA50 över flera intervall

```bash
python analyze_omxs30.py
```

Hämtar OMXS30 på både `15m` och `1h` (senaste månaden), räknar ut MA20 och MA50 för respektive intervall och plottar allt i `data/omxs30_ma_multi_interval.png`. Priskurvorna ritas ljusgrå i bakgrunden, MA-linjerna i tydliga färger per intervall.

Grafen har två delar:
- **Prispanel** (överst): Close + MA20/MA50 per intervall.
- **Trendstyrke-panel** (nederst): `(MA20 − MA50) / MA50 × 100` per intervall — ett prisoberoende %-mått på trendriktning/styrka, jämförbart rakt av mellan olika tidsintervall. Positivt = uppåttrend, negativt = nedåttrend, nollgenomgång = trendvändning.
- Perioder (>2h) där det snabba och det långsamma intervallet är **oense om trendriktning** skuggas rött i båda panelerna — t.ex. uppåtmomentum på 15m samtidigt som 1h-trenden är på väg ner, en tidig varningssignal snarare än en köpsignal.

Valfria flaggor:

```bash
python analyze_omxs30.py --period 1mo --intervals 15m 1h
```

## Automatisk körning

### Alternativ 1: GitHub Actions (rekommenderas)

Workflowen `.github/workflows/fetch_omxs30.yml` kör `analyze_omxs30.py` automatiskt vardagar 17:00 UTC (efter stängning på Stockholmsbörsen) och laddar upp CSV-filerna samt MA-grafen som en artifact (`omxs30-data`), hämtningsbar under körningen i GitHub Actions-fliken. Går även att triggas manuellt via "Run workflow".

### Alternativ 2: cron (lokalt/server)

```bash
# Kör varje vardag kl 18:00
0 18 * * 1-5 cd /sökväg/till/omxs30-yfinance && /usr/bin/python3 fetch_omxs30.py >> fetch.log 2>&1
```

### Alternativ 3: Task Scheduler (Windows)

Skapa en schemalagd uppgift som kör:
```
python C:\sökväg\till\omxs30-yfinance\fetch_omxs30.py
```

## Nästa steg

Detta är grunden för projektet – nästa steg kan t.ex. vara analys/backtesting av datan, ett dashboard, eller notifieringar vid signaler.
