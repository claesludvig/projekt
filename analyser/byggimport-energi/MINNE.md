# MINNE – byggimport & energikänslighet

Kontextfil så att en ny session (eller du själv) kan fortsätta direkt.

## Uppdraget (från Ludvig, 16 nov 2026)
Kartlägga svenska byggsektorns **importandel**, **varifrån** och **vad** som importeras,
och koppla det till **energikänslighet**:
- råolja, bensin och diesel → produktion och transport av byggmaterial
- europeiska gaspriser (TTF) → europeisk produktion av byggmaterial (som Sverige importerar)

Sammanhang: prognosarbete på Prognoscentret. Texten kan senare skrivas om i hans prognosstil
(skill `prognostext-stil`) eller bli bilder i Prognoscentrets mall.

## Bokprojektet (VIKTIGT)
Ludvig skriver en bok: "Bostadspolitiskt bokprojekt (omarbetad)" i Google Drive
(fil-ID 1IgfeXa3ZkZZHIxgN9WLjXwoUtVc7xY6ybtpQKT8EJ68). Utkast på lösa delar: "Utkast på enskilda delar"
(fil-ID 1arMYZF-bCxTO2trxnAGcX-Y348G5l4HOzeF0uC8iBbk).
- Avsnittet om inhemsk producentdel hör till kapitel 4 (byggkostnader), under "Energin och byggkostnaderna",
  som redan säger: energins direkta vikt i BKI är liten (<1/20), energin når byggandet via förädlingskedjan
  (Prognoscentret 2026: ~hälften av kostnaden i stål, >1/4 i betong), Sverige "importerar" krisen via materialpriser.
- Bokens stil: enkel, läsbar prosa. Få siffror. "vi" förekommer. Referera SPARSAMT – inte efter varje påstående; Ludvig vill inte ha källhänvisningar hela tiden.
- LÄXA: när Ludvig ber om språklig bearbetning av sitt utkast, ändra LITE. Behåll hans struktur, stycken och tes.
  Lägg bara till källor och få siffror. Skriv inte om argumentet (v2 var för omfattande och fick kritik).

## Status
- [x] Första genomgång via webbsökning → `RAPPORT.md`
- [x] Datapunkter → `data/datapunkter.csv`, källor → `data/kallor.csv`
- [x] Skript för primärdata → `kod/hamta_data.py` (inte kört, nätverket blockerat)
- [ ] Hämta SCB:s input-output-tabeller (direkt och indirekt importinnehåll, SNI 41–43)
- [ ] Import per KN-kod och land (se `KN_KODER` i skriptet)
- [ ] Eurostat: energikostnadsandelar och produktion C23/C24
- [ ] Bitumenpris och asfaltindex
- [ ] Verifiera TTF-nivån (källorna går isär: ~40 / ~50 / ~93–103 €/MWh)

## Nätverk
Blockerade i molnsessionen: `scb.se`, `api.scb.se`, `statistikdatabasen.scb.se`, `ec.europa.eu`,
`konkurrensverket.se`, `think.ing.com`, `sdmx.oecd.org`, `comtradeapi.un.org`.
De måste läggas till i miljöns tillåtna värdar innan `kod/hamta_data.py` kan köras.

## Resultat från input-output-beräkning (annan session, SCB IO 2023)
Direkt import 12 % av byggets produktionsvärde; inkl. indirekt 24,5 % (20,9 % 2019).
Materialköp 65 % inhemskt / 35 % import. Inhemsk andel: trä 80 %, betong/cement/glas/tegel 73 %, stål 41 %, el och VVS 15–18 %.
Genomslag importpris → inhemskt producentpris inom 3 mån: stål 0,8, elkablar 0,6, färg 0,4, betong/trä/VVS 0,1–0,15.
Slutsats: tunga material prissätts i Sverige på kort sikt → konkurrens och marginaler viktigare än importpriset.
(Metod och kod finns i den andra sessionen, inte i det här paketet.)

## Huvudslutsatser hittills
1. Direkt import ≈ 15–20 % av byggmaterialmarknaden; det fulla importinnehållet är sannolikt högre.
2. Stål är i praktiken helt importerat (armering från Celsa i Mo i Rana). Cement ~15 % import (Lettland).
   Skivor från Norge, Danmark och Tyskland.
3. Oljekanalen: diesel +42,5 % y/y (okt 2026), drivmedel ≈ 1/3 av maskintimmen → anläggning mest utsatt.
   Oljebaserade material: bitumen, plaströr, cellplast, tätskikt.
4. Gaskanalen verkar via importen: svensk tillverkning går mest på el och bio, men glas, tegel, plattor,
   mineralull och stål från kontinenten är gaskänsliga. Energins andel av produktionsvärdet före 2022:
   tegel 16 %, cement 15 %, glas 13 %, plattor 9 %, betongvaror 3 %.

## Omvärldsläget som antas (hösten 2026)
Krig/Iran-konflikt från feb 2026, Hormuz-störningar, vapenvila i maj. Brent i snitt ~96 USD 2026 (69 USD 2025),
~95 USD i mitten av november. TTF ~30 €/MWh före kriget.

## Filer
- `RAPPORT.md` – läsbar sammanställning med källor
- `BOKTEXT_inhemsk_produktion_v3.md` – lätt bearbetad version av Ludvigs utkast (AKTUELL) – INLAGD i bokens Google Doc 17 nov 2026, kap. 4 "Energin och byggkostnaderna", efter stycket "Den indirekta vägen…", före "Det avgörande är ändå…"
- `BOKTEXT_inhemsk_produktion_v2.md` – Ludvigs utkast, omarbetat med IO-siffror och genomslagsskattningar (för omfattande, ej aktuell)
- `BOKTEXT_inhemsk_produktion.md` – bokavsnitt om den inhemska producentdelen (pristak och prisgolv)
- `data/datapunkter.csv` – alla siffror med period, källa och anmärkning
- `data/kallor.csv` – källförteckning
- `kod/hamta_data.py` – hämtning från SCB och Eurostat (tabell-ID:n behöver kontrolleras)
