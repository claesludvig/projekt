# Byggkredit — kreditutgivningen i byggmarknaden

Pipeline som bygger en läsbar bild av kreditutgivningen mot bostadsproduktion
ur SCB:s och Konjunkturinstitutets öppna statistik.

## Problemet den löser

Den naiva ansatsen är att slå upp MFI:s utlåning till branschen *Fastighet –
bostäder* i KRITA och läsa den som kreditutgivning till byggandet. Det ger fel
svar, av tre skäl som alla slår åt samma håll:

1. **Stock är inte flöde.** Utestående belopp kan ligga still medan utgivningen
   halveras, eftersom amortering och nyutlåning tar ut varandra. Vändpunkterna
   — det enda man egentligen bryr sig om i en prognos — syns inte i stocken.
2. **Branschen mäter ägande, inte produktion.** *Fastighet – bostäder*
   domineras av beståndsägare. Krediten till en befintlig hyresfastighet som
   byter ägare hamnar i samma serie som krediten till ett nytt projekt.
3. **Kronor utan nämnare är oläsbart.** Ett fallande kreditflöde kan lika gärna
   betyda att det byggs mindre som att det är svårare att låna. Det är olika
   prognoser.

Byggnadskreditiv — det som faktiskt finansierar själva produktionen —
publiceras inte separat någonstans. Ingen konstruktion kommer runt det. Det
pipelinen gör är att ringa in storheten från flera håll samtidigt och vara
explicit med vad varje ben kan och inte kan visa.

## Metoden

Fem lager, som var och en motsvarar en `role` i `sources.py`:

| Lager | Vad | Varför |
|---|---|---|
| `kredit` | Flöden till BRF, fastighet–bostäder, byggverksamhet, hushållens bolån och obligationsmarknaden | BRF är den renaste posten: föreningens permanenta lån löser byggnadskreditivet vid inflyttning, så serien är nyproduktion i bostadsrätt med projekttidens eftersläpning |
| `namnare` | Påbörjade lägenheter och byggkostnadsindex | Gör kreditflödet till en kvot per producerad enhet — i praktiken produktionssystemets belåningsgrad |
| `pris` | Utlåningsränta per bransch mot styrräntan | Kreditgivning stramas åt på pris innan den stramas åt på volym |
| `bredd` | Antal låntagande företag | Volym upp och antal låntagare ned är koncentration till starka balansräkningar, alltså en åtstramning som volymserien döljer |
| `enkat` | KI:s barometer, finansiella restriktioner som främsta hinder | Enda direkta måttet på kreditutbud, och det enda benet som leder de övriga |

Det avgörande steget är nämnaren. **Faller kreditflödet snabbare än byggandet
är krediten den bindande restriktionen; faller de i takt är det efterfrågan på
bostäder.** Den skillnaden går inte att se i volymserien, och det är den en
prognos hänger på. Måttet heter `gap_kredit_minus_byggande` och är
kreditflödets årstakt minus byggandets, i procentenheter.

Lagren vägs till sist ihop till `byggkreditindikator`, ett z-poängindex där
positivt betyder lättare kreditvillkor än normalt under perioden.

## Användning

```bash
pip install -r requirements.txt

python fetch.py --dry-run     # visa vilka tabeller och värden specarna landar i
python fetch.py --since 2015  # hämta -> data/serier.csv
python indicators.py          # räkna om    -> data/indikatorer.csv
python report.py              # rita        -> data/byggkredit.png, data/rapport.md

python tests/test_offline.py  # verifierar beräkningslogiken utan nätverk
```

Kör `--dry-run` först. Pipelinen väljer tabeller och värden på **etiketter, inte
koder**, eftersom SCB byter koder oftare än namn — KRITA gick från SNI 2007 till
SNI 2025 i februari 2026 och bytte då ut samtliga branschkoder men behöll
"Bostadsrättsföreningar" och "Fastighet - bostäder". Priset för den
robustheten är att en matchning kan landa fel utan att något kraschar, och
därför loggas varje upplösning till `data/resolution.json`. Läs den innan du
använder siffrorna.

Missar ett mönster:

```bash
python fetch.py --list FM/FM0002        # visa tabellerna under en rot
python fetch.py --only krita_volym      # kör om en enskild serie
```

och justera titel- eller värdemönstret i `sources.py`.

## Läsa resultatet

- `gap_kredit_minus_byggande` **negativt** → åtstramning utöver konjunkturen.
- `spread_*` stigande → åtstramning som ännu inte syns i volymen.
- `bredd_antal_lantagare_yoy` fallande medan flödet står still → kreditgivningen
  koncentreras, marginella låntagare stängs ute.
- `byggkreditindikator` kräver fullt komponentset. `byggkreditindikator_prel`
  tar vad som finns vid seriens kant och ska läsas som preliminär: KRITA släpar
  medan KI:s barometer är färsk, så ett medelvärde över ett krympande
  komponentset hoppar i nivå av rena mätskäl.

## Förbehåll

- **KRITA publiceras som stock.** Flödena här är differenser och innehåller
  omvärderingar och omklassificeringar som SCB inte rensar bort. Hushållsserien
  i finansmarknadsstatistiken publiceras även som transaktioner och är därmed
  ett renare flödesmått — den asymmetrin går inte att bygga bort.
- **Branschen i KRITA är beräknad bransch, inte ren SNI.** Bolag med SNI
  "verksamhet vid huvudkontor" flyttas till koncernens faktiska bransch.
  Bostadsrättsföreningar är den enda helt rena avgränsningen, eftersom de
  identifieras på juridisk form.
- **Byggnadskreditiv saknas.** Produktionens finansiering syns först när
  föreningens permanenta lån läggs upp, alltså med projekttidens eftersläpning.
- **Ändamål mäts inte för hushåll, säkerhet mäts.** Blancolån som finansierar
  bostadsköp saknas helt i bolåneserien.
- **Utländska direktlån och kreditfonder fångas dåligt.** MFI-aggregatet täcker
  svenska monetära finansinstitut; obligationsbenet fångar en del av resten,
  men inte allt.
- **Tidsseriebrott vid SNI 2025 (2026-02).** Det finns ingen överlappsperiod att
  länka på, så flöden vars fönster spänner över brottet sätts till saknat värde
  i stället för att redovisa en omklassificering som kreditgivning.

## Källor

- SCB, Kreditdatabas KRITA (FM0002) — utlåning till icke-finansiella företag
  efter bransch och storleksklass
- SCB, Finansmarknadsstatistik (FM5001) — utlåning till hushåll efter säkerhet
- SCB, Emitterade värdepapper — räntebärande värdepapper efter emittentsektor
- SCB, Boende/byggande (BO) — påbörjade bostadslägenheter
- SCB, Priser (PR) — byggkostnadsindex för bostadshus
- Konjunkturinstitutet, Konjunkturbarometern — byggföretagens hinder

Kompletterande källor som pipelinen inte läser men som hör till bilden:
Finansinspektionens bolåneundersökning (belåningsgrader och skuldkvoter på nya
lån, stickprov på låntagarnivå) och Riksbankens företagsundersökning.
