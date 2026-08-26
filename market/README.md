# market — trendläge per tidsintervall

Svarar på en fråga: **pekar de korta och långa tidsintervallen åt samma håll?**
En uppgång på 15 minuter inuti en fallande timtrend är en rekyl, inte en vändning,
och de två får olika ord.

```
OMXS30    15m ▲ +0.42 %  |  1h ▲ +1.10 %  |  1d ▲ +3.20 %   → Samstämmig upp
USD/SEK   15m ▲ +5.01 %  |  1h → +1.16 %  |  1d ▼ −4.46 %   → Rekyl upp i nedtrend
```

## Kom igång

```bash
pip install yfinance pandas matplotlib

python3 -m market.cli --out out/market.png              # live från Yahoo
python3 -m market.cli --provider synthetic --no-chart   # demo utan nätverk
python3 -m market.tests.test_trend                      # 12 tester
```

## Hur riktningen bestäms

Per tidsintervall gäller tre mått, men de väger inte lika:

**`momentum` är en grind, inte en röst.** Rörelsen över de senaste 20 staplarna
delas med vad intervallets egen brusnivå skulle producera över samma sträcka.
Skalningen är hela poängen: 0,2 % på en kvart är en verklig rörelse, samma
0,2 % på en dagsstapel är ingenting. Under `z_threshold` (1,3 σ) är svaret
neutralt oavsett vad annat säger.

**De två EMA-avläsningarna** — snabb mot långsam EMA, och lutningen på den
långsamma — får bara bekräfta eller lägga in veto. Båda måste säga emot grinden
för att stoppa den.

Att hålla EMA:erna underordnade är avsiktligt. De är nära dubbletter av varandra,
och som likvärdiga röster blev resultatet att paret rutinmässigt röstade ner den
enda volatilitetsmedvetna signalen: 12 av 30 rena slumpvandringar fick starkt
trendbesked. Med grinden ligger andelen på ~21 %, vilket är ungefär vad man ska
förvänta sig — en slumpvandring *trendar* faktiskt ibland, och en klassificerare
som påstår noll falska utslag ljuger.

**`strength` (1–3)** graderas efter hur långt förbi grinden rörelsen nådde
(1,3 σ / 2 σ / 3 σ) — inte efter hur många indikatorer som höll med. Det
mättes: när grinden väl öppnar håller EMA:erna med i praktiskt taget 100 % av
fallen, så en räkning av dem hade rapporterat en konstant förklädd till skala.

## Samstämmighet

Riktningarna jämförs kortast först. Neutrala intervall räknas inte — ett platt
mellansteg bryter inte en i övrigt entydig bild.

| Utfall | Betydelse |
|---|---|
| `Samstämmig upp` / `ner` | Alla aktiva intervall pekar åt samma håll |
| `Rekyl upp i nedtrend` | Kort sikt upp, längre sikt fortsatt ner |
| `Rekyl ner i upptrend` | Kort sikt ner, längre sikt fortsatt upp |
| `Blandad bild` | Intervallen säger emot varandra utan mönster |
| `Riktningslöst` | Inget intervall klarade grinden |

## Datakällor

| Provider | Användning |
|---|---|
| `yfinance` | Live från Yahoo Finance |
| `csv` | Spelar upp tidigare sparade serier — för maskiner utan Yahoo-åtkomst |
| `synthetic` | Genererade banor för tester och demo. **Aldrig marknadsdata.** |

Kör `--record snapshots/` där Yahoo går att nå, och `--provider csv` där det inte
gör det:

```bash
python3 -m market.cli --record snapshots/        # på en maskin med åtkomst
python3 -m market.cli --provider csv --csv-dir snapshots/
```

## Anpassa bevakningslistan

Symbolerna i `config.py` är Yahoo-tickers: `^OMX` (OMXS30), `^GSPC`, `^IXIC`,
`^TNX` (10-årsränta), `BZ=F` (Brent), `SEK=X` (USD/SEK). Lägg till egna med
`--symbols`, eller redigera `DEFAULT_WATCHLIST`.

Yahoo begränsar intradagshistorik: 15-minutersdata når ~60 dagar bakåt,
1-minutersdata ~7. Därför har varje tidsintervall sin egen `period` i
`config.py`.

## Begränsningar

- Trendklassificering beskriver vad som *har* hänt. Den förutsäger ingenting.
- Ett instrument som saknar tillräckligt med staplar rapporteras som
  otillgängligt i `unavailable` — det tystas inte bort.
- Yahoo-data är fördröjd för många instrument och bör inte användas för
  handelsbeslut som kräver realtid.
