# Underlag för oberoende metodgranskning

Det här dokumentet är skrivet för den som ska granska väljardatabasen utifrån, till exempel en
statistiker vid ett universitet eller riksdagens utredningstjänst (RUT) på uppdrag av en ledamot.
Det beskriver vad databasen gör, vilka antaganden varje skattning vilar på, vad som redan är
kontrollerat och vilka frågor granskaren särskilt bör pröva.

Allt kan byggas om från källorna:

```
pip install -r requirements.txt
python hamta.py        # hämtar rådata (kräver nätverk)
python -m pytest -q tests
python bygg_db.py      # databas, CSV, kvalitetskontroll
python bygg_sida.py    # sidan
```

Resultatet av de automatiska kontrollerna står i `data/kvalitet.json` efter varje bygge.

## 1. Vad som är mätt och vad som är skattat

| Avsnitt | Evidensnivå | Bygger på |
|---|---|---|
| Läget | beskrivande | Polisens, SCB:s och Riksbankens månadsserier |
| Min valkrets | beskrivande | kommunvärden viktade till valkrets; vissa värden per län eller polisregion |
| Politikens svar | beskrivande | riksdagens öppna data, SOM:s publicerade värden |
| Områdena | beskrivande | svensk statistik och Eurostat |
| Sammansättning (PSU) | modellskattning | gruppvikter skattade ur felmarginaler, kalibrerade mot register |
| Länen | modellskattning | IPF från nationella PSU-andelar |
| Demografi eller beteende | modellskattning | Shapley-uppdelning av PSU-förändringar |
| Geografin, valdistrikten | samband | korrelationer mellan områden |

Evidensnivån står på sidan vid varje avsnitt (`metod.EVIDENS`).

## 2. Skattningarna och deras antaganden

### 2.1 Gruppvikter i PSU
SCB redovisar partisympati inom grupper men inte gruppernas storlek. Storleken skattas ur
felmarginalen, n = 1,96² · p(1 − p) / m², och kalibreras mot registrets röstande 2018 och 2022
(linjärt däremellan, konstant utanför).

*Antaganden:* felmarginalen är beräknad som för ett obundet slumpmässigt urval; SCB:s vägning och
designeffekt är lika mellan grupper; avrundningen av m (en decimal) ger begränsat fel.
*Kontroll:* PSU:s totala partisiffror återskapas med 0,1–0,3 procentenheters fel. Före kalibrering
är äldre, högutbildade och inrikes födda överrepresenterade (tabellen `kontroll`).
*Fråga till granskaren:* hur stort är felet i skattat n när m är avrundat och p är litet (under 5 %)?
Bör okalibrerade indelningar (yrke, fack, boende) visas alls?

### 2.2 Partiprofiler per län och kommun (IPF)
Startvärdet är PSU:s nationella stöd per grupp gånger antalet röstande i gruppen i länet
(register). Tabellen justeras tills raderna stämmer med registrets röstande och kolumnerna med
länets valresultat.

*Antagande:* gruppernas relativa benägenhet att rösta på ett parti är densamma i hela landet, bara
nivån anpassas. Regionala skillnader inom grupper (t.ex. hur LO-medlemmar röstar i Norrbotten mot i
Skåne) fångas bara delvis. 2026 används 2022 års registersammansättning.
*Kontroll:* på riksnivå återskapas PSU:s profiler med under en procentenhets avvikelse.
*Fråga:* kan antagandet prövas mot Valforskningsprogrammets regionala data eller Valu per region?

### 2.3 Sammansättning och beteende
Förändringen i stöd Σ w·s delas upp i Σ Δw·s̄ + Σ w̄·Δs. Uppdelningen är exakt men beror på vilka
grupper som ingår, och bygger på sympati (PSU), inte röster.

### 2.4 Valdistrikt och DeSO
Valdistrikten 2026 läggs över DeSO 2025. Varje distrikt får DeSO-statistik i proportion till
ytandelen. *Antagande:* jämnt fördelad befolkning inom DeSO. Distrikt med under 90 % täckning eller
färre än 100 giltiga röster utesluts. Korrelationernas konfidensintervall är för smala, eftersom
närliggande distrikt liknar varandra (rumslig autokorrelation).
*Fråga:* bör befolkningsviktning via rutnätsstatistik (1 km²) ersätta ytviktningen?

### 2.5 Valkretsar
Kommunvärden viktas med antalet röstberättigade 2026. För indikatorer som bara finns per region får
alla valkretsar i ett delat län (Stockholm, Skåne, Västra Götaland) samma värde; det är markerat.

### 2.6 Lägesbilden
Status sätts när förändringen de senaste tre månaderna avviker mer än 1,5 eller 2
standardavvikelser från seriens förändringar de senaste tio åren, eller när nivån är den högsta
eller lägsta på fem eller tio år. För antal jämförs rullande tolvmånaderssummor.
*Fråga:* ger regeln för många falsklarm för små serier (döda i skjutningar, där enstaka händelser
slår igenom)? Bör en Poissonmodell användas för antal?

### 2.7 Riksdagens beslut och opinionen
Propositioner och betänkanden klassas till sakfrågor med ord i rubriken och, för betänkanden utan
träff, utskottet (`riksdag_katalog.py`). SOM-förslag kopplas till propositioner med reguljära
uttryck. Partiets position i en votering är majoriteten av dess ledamöters röster.
*Kända svagheter:* klassningen både missar och felklassar; budgetpropositionens utgiftsområden
behandlas utan egen votering per förslag; SOM-värdena är bara två punkter (2022, 2025) eftersom
rapporten har diagram, inte tabeller.
*Fråga:* bör klassningen valideras mot ett handkodat urval (t.ex. 200 slumpade propositioner)?

### 2.8 Mål i stället för värderingar
Riktning och målnivå anges bara där lag, riksdagsbeslut, Riksbanken eller internationella åtaganden
anger mål (`verklighet_katalog.MAL`). *Fråga:* är urvalet av mål rimligt och neutralt, och är
målformuleringarna korrekt återgivna?

## 3. Automatiska kontroller

`kontroller.py` körs efter varje bygge:

- **Aktualitet:** månadsserier äldre än källans eftersläpning plus två månader, årsserier utan värde
  de senaste tre åren, riksdagens dokument.
- **Volym:** tabeller som blivit tomma eller krympt mer än 20 % sedan förra körningen (fel).
- **Rimlighet:** 29 valkretsar, 290 kommuner, 349 mandat 2022 och 2026, andelar som summerar till 100,
  voteringar med alla ledamöter, partiprofiler, SOM-förslag, Sverige i de nordiska serierna.

Vid fel öppnar arbetsflödet ett ärende i repot; det stängs när kontrollerna är gröna igen.
Tolkarna testas före bygget (`tests/`), så en ändrad källfil stoppar körningen i stället för att
ge fel data.

## 4. Kända brister som granskaren inte behöver leta efter

- Pdf-tolkningen (Valu, GU, SOM, Polisen) är skör och beror på sidlayout.
- SCB:s tabell-id och Koladas API har ändrats under arbetet; sökningen är robust men inte garanterad.
- Brå:s uppklaringsandel och lagföring, SKR:s väntetider per månad, elpris per elområde och
  Kriminalvårdens beläggning saknas (öppna API saknas eller är inte inkopplade).
- Ingen osäkerhet visas för IPF-skattningarna.
- Licensvillkoren för Valu- och GU-tabellerna är inte avstämda (se `LICENSER.md`).

## 5. Förslag till granskningsuppdrag

1. Pröva gruppviktsskattningen (2.1) mot SCB:s egna gruppstorlekar där sådana finns.
2. Validera IPF (2.2) mot en oberoende regional källa.
3. Handkoda ett urval propositioner och mät träffsäkerheten i klassningen (2.7).
4. Bedöm om framställningen på sidan är neutral mellan partierna.
5. Pröva lägesbildens larmregel (2.6) historiskt: hur ofta hade den larmat 2017–2025, och vid vilka
   händelser?
