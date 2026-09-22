# Byggkonjunkturen i Örebro län: sysselsättning, skatteintäkter och spridningseffekter

Estimat av vad nedgången i byggsysselsättningen 2022–2025 rimligen bör ha
kostat kommunerna i Örebro län och Region Örebro län, samt av
spridningseffekterna på resten av länsekonomin.

**Viktig begränsning:** sessionen där detta togs fram hade ingen nätverksåtkomst
till `api.scb.se`, `scb.se`, `regionfakta.com` eller `kolada.se` — egress-policyn
blockerade samtliga. Nivåsiffrorna för Örebro län är därför *kalibrerade
skattningar* byggda på publicerade riksdata och länets strukturandelar, inte
SCB-uttag. `hamta_scb.py` ersätter dem med faktiska värden när det körs i en
miljö med öppen SCB-åtkomst. Allt som inte är verifierat är taggat `ANTAGET` i
`parametrar.py`. Själva slutsatserna hänger på strukturen i beräkningen, inte på
tredje decimalen.

---

## 1. Vad som hänt

Riksbilden är väl belagd. Enligt Byggföretagen föll sysselsättningen i bygg-
och anläggningsbranschen från 328 800 personer 2022 till 312 400 personer 2024,
alltså **−16 400 jobb eller −5,0 procent**. SCB:s bredare BAS-serie låg på
381 644 sysselsatta inom byggverksamhet 2023 och minskade med 4,0 procent under
2024. Serierna skiljer sig i nivå men inte i riktning: nedgången från toppen är
i storleksordningen 5 procent, och koncentrerad till husbyggnad, där över
10 procent av arbetskraften försvunnit.

Örebro län har cirka 2,9 procent av rikets befolkning och en byggandel av
sysselsättningen nära riksgenomsnittet — länet är överrepresenterat i logistik
och tillverkning snarare än i bygg. Det ger en utgångsnivå på **omkring
10 000–10 500 byggsysselsatta 2022**.

Var i intervallet länet hamnar avgörs av *mixen*. Anläggning har hållit emot
(Trafikverkets ramar, kraftnät, försvar), bostäder har kollapsat. Ett län med
hög bostadsandel i byggvolymen faller mer än riket. Örebro hade en ovanligt
stark bostadsproduktion 2018–2022, vilket talar för att nedgången varit något
djupare än riksgenomsnittet. Därför tre scenarier: −5,0 % (följer riket),
−7,5 % (central) och −11,0 % (följer husbyggnadsnedgången).

Ett stödjande observandum: i februari 2025 var 350 personer i Örebro län
inskrivna i Byggnads a-kassa. Och länets folkmängd **minskade** med cirka
18 personer under 2025 — efter ett decennium av tillväxt. Det är den andra
halvan av historien (avsnitt 6).

## 2. Direkt effekt

| Scenario | Nedgång | Direkt, byggjobb |
|---|---|---|
| mild | −5,0 % | −510 |
| **central** | **−7,5 %** | **−765** |
| hård | −11,0 % | −1 122 |

## 3. Spridningseffekter — och varför nationella multiplikatorer inte duger

SCB publicerar **inga regionala input-output-tabeller**. Den nationella
symmetriska I/O-tabellen (NR0117) måste regionaliseras. Standardmetoden är
Flegg's location quotient (FLQ), där varje cell i A-matrisen skalas med en
lokaliseringskvot beräknad på branschvis sysselsättning eller förädlingsvärde ur
regionalräkenskaperna (NR0105), plus en storleksparameter δ som straffar små
regioner extra. Örebro läns BRP-andel på ~2,5 procent ger en kraftig nedskalning.

Att applicera *nationella* multiplikatorer på ett län är det vanligaste felet i
regionala effektstudier. Byggsektorn köper stål, cement, installation, maskiner
och konsulttjänster i stor utsträckning utanför länet, och importinnehållet i
kedjan är högt — precis det din egen promemoria om byggsektorns importberoende
kvantifierar. Varje krona som lämnar länet är en krona som inte multipliceras
i länet.

| Multiplikator (sysselsättning, SNI 41–43) | Typ I | Typ II |
|---|---|---|
| Nationell (hela Sverige) | ~1,50 | ~2,00 |
| **Intraregional, Örebro län** | **1,15–1,40** | **1,35–1,70** |

Med centralvärdena (1,25 / 1,50) i central-scenariot:

- **−765** direkta byggjobb
- **−191** indirekta jobb hos underleverantörer i länet (typ I)
- **−383** indirekta + inducerade (typ II)
- **≈ −1 150 jobbårsekvivalenter totalt i länet**

Därutöver cirka 350–400 jobb hos leverantörer **utanför** länet. Den nationella
effekten av Örebros byggnedgång är alltså större än den regionala — men den
tillfaller inte Örebro läns skattebaser.

Två varningar som hör till metoden: typ II-multiplikatorer överskattar
systematiskt (Miller & Blair), och hela I/O-ramverket antar fasta
insatskoefficienter och ledig kapacitet. Det senare är rimligt i en nedgång,
mindre rimligt vid en uppgång med kompetensbrist.

## 4. Skatteunderlaget: brutto mot netto

Här går de flesta branschkalkyler fel. Ett förlorat byggjobb är **inte** ett
förlorat skatteunderlag krona för krona, av två skäl:

1. **A-kassa och aktivitetsstöd är kommunalt skattepliktiga.** Ersättningen
   ligger på omkring 55 procent av tidigare lön. Kommunen förlorar
   differensen, inte hela lönen.
2. **De flesta får annat arbete.** Örebro läns arbetsmarknad är bred;
   byggarbetare rör sig till industri, logistik och installation.

Fördelningsantagande: 45 procent nytt arbete i länet (90 % av tidigare inkomst),
35 procent arbetslösa (55 %), 20 procent lämnar länet eller arbetskraften (15 %).
Det ger att **cirka 37 procent** av bruttolönebortfallet faktiskt lämnar
skatteunderlaget.

| mn kr/år | mild | central | hård |
|---|---|---|---|
| Bruttobortfall lönesumma | −337 | **−505** | −741 |
| Nettobortfall efter omställning | −125 | **−188** | −276 |

## 5. Skatteintäkter — och utjämningens blinda fläck

Skattesatser: kommunerna i länet 21,6 procent befolkningsviktat (Örebro kommun
21,35), Region Örebro län 12,30 procent. Summa 33,9 procent.

| mn kr/år | mild | central | hård |
|---|---|---|---|
| Mekaniskt brutto, kommunerna | −73 | −109 | −160 |
| Mekaniskt brutto, regionen | −41 | −62 | −91 |
| *Mekaniskt brutto, totalt* | *−114* | *−171* | *−251* |
| Realistiskt netto, kommunerna | −27 | **−41** | −60 |
| Realistiskt netto, regionen | −15 | **−23** | −34 |
| **Realistiskt netto, totalt** | **−43** | **−64** | **−94** |

**Den viktigaste poängen i hela analysen** gäller inkomstutjämningen. Systemet
garanterar varje kommun 115 procent av medelskattekraften i riket, med 95
procents kompensationsgrad och en länsvis skattesats. Alla tolv kommunerna i
Örebro län ligger under garantinivån och är bidragstagare.

Det betyder att utjämningen försäkrar mot **idiosynkratiska** chocker: om
byggnedgången hade varit unik för Örebro län hade cirka 57 av 64 miljoner
kompenserats, och kommunerna och regionen hade burit ungefär 7 miljoner —
runt 11 procent.

Men byggnedgången var **riksgemensam**. När medelskattekraften faller lika
mycket som den egna skattekraften ser utjämningssystemet ingen relativ
försämring. Gapet mot garantinivån krymper proportionellt, bidraget faller med,
och genomslaget blir i praktiken fullt. Örebro läns kommuner bär alltså hela
beloppet — och det gäller oavsett hur lågt de ligger i skattekraft.

Sensmoralen: den kommunalekonomiska risken i en byggkonjunktur är *helt
oförsäkrad* när konjunkturen är nationell, vilket den nästan alltid är.
Utjämningssystemet är byggt för strukturella nivåskillnader, inte för
konjunkturell samvariation.

Lägg till att skatteunderlaget slår igenom med eftersläpning via
slutavräkningarna — nedgången 2023–24 landar i boksluten 2025–26.

## 6. Vad lönesummekalkylen missar

Fyra kanaler ligger utanför beräkningen, och tre av dem är sannolikt större än
den som beräknats:

**Befolkningskanalen, störst av alla.** Kommunal ekonomi är i praktiken
invånarbaserad — både skatteunderlaget och utjämningsbidragen. SKR:s
marginalintäkt vid befolkningsförändring ligger kring 65 000 kr per invånare och
år för kommun och region tillsammans. Uteblivet bostadsbyggande begränsar
inflyttningen direkt. Om bostadskrisen kostat länet 1 000 invånare i utebliven
tillväxt är det **65 miljoner kronor per år** — lika mycket som hela den direkta
och indirekta sysselsättningseffekten, och till skillnad från den är den
bestående. Att länets folkmängd faktiskt vände nedåt 2025 gör kanalen konkret,
inte hypotetisk.

**Engångsintäkterna.** Exploateringsersättningar, markförsäljning och
bygglovsavgifter är volymberoende och slår igenom omedelbart i kommunernas
resultat. De syns inte i skatteunderlaget alls.

**Fastighetsavgiften ger ingenting.** Nybyggda bostäder färdigställda från 2012
har 15 års befrielse från kommunal fastighetsavgift. Byggandets
kommunalekonomiska värde ligger alltså i inflyttningen, inte i fastigheten.

**Kostnadssidan och staten.** Kommunerna får ökade kostnader för försörjningsstöd
och arbetsmarknadsinsatser. Samtidigt bärs merparten av den offentligfinansiella
förlusten av staten: arbetsgivaravgifter, moms på byggvolymen, bolagsskatt från
konkursade byggbolag och a-kassan. Kommunsektorns andel av det totala
offentligfinansiella bortfallet är sannolikt under en tredjedel.

## 7. Proportioner

Länets samlade kommunala och regionala skatteintäkter ligger kring 24 miljarder
kronor. Nettobortfallet i central-scenariot, 64 miljoner, motsvarar:

- **0,26 procent** av skatteintäkterna (mekaniskt brutto: 0,70 procent)
- ungefär **98 kommunala årsarbetare**
- ungefär vad 1 000 uteblivna invånare kostar

Slutsatsen är alltså dubbel, och båda halvorna behöver sägas: byggnedgången är
en **reell men inte dominerande** post i kommunernas ekonomi — den förklarar
inte de budgetunderskott som diskuteras i länet — men den är **helt oförsäkrad**
via utjämningen, och dess största kommunalekonomiska effekt går via
befolkningsutvecklingen snarare än via byggjobben i sig.

## 8. Känslighet

Nettobortfallet i central-scenariot, 64 mn kr, varierar mellan **43 och 86 mn kr**
för rimliga värden på multiplikator, genomsnittslön och länets byggandel. Den
enskilt mest avgörande parametern är omställningsantagandet: sätts återinkomsten
till noll — vilket är vad rena branschkalkyler implicit gör — blir svaret
171 mn kr, nästan tre gånger så högt. Att använda den nationella
typ II-multiplikatorn regionalt ger 84 mn kr, alltså 32 procents överskattning.

Fullständig känslighetstabell: `python3 modell.py`.

---

## Så här verifierar du siffrorna

```bash
python3 modell.py --csv      # kör modellen, skriver data/resultat.csv
python3 hamta_scb.py allt    # letar upp rätt tabell-id i SCB:s API
python3 hamta_scb.py meta <id>
python3 hamta_scb.py data <id> --valuecodes Region=18 --out data/syss.csv
```

Serier som behövs för att ersätta antagandena:

| Parameter | SCB-källa |
|---|---|
| Byggsysselsatta i Örebro län, nivå och utveckling | NR0105 regionalräkenskaper, sysselsatta per län och bransch |
| Genomsnittlig årslön i bygg i länet | NR0105 lönesummor per län och bransch |
| Location quotients till FLQ | NR0105 BRP/förädlingsvärde per län och bransch |
| Längre serie, kommunnedbruten | RAMS/BAS förvärvsarbetande dagbefolkning |
| Faktiskt skatteunderlag att relatera till | Kommunalt skatteunderlag per kommun |
| A-matris och importmatris | NR0117 input-output-tabeller (ofta xlsx, inte API) |

Det som mest sannolikt flyttar resultatet är länets faktiska byggandel och den
faktiska nedgången — alltså scenariovalet i tabell 1, inte
multiplikatorantagandena.

## Källor

- [Byggföretagen, Sysselsättning inom byggverksamhet](https://byggforetagen.se/statistik/antal-ans/)
- [Byggkonjunkturen #1 2025, Byggföretagen](https://byggforetagen.se/app/uploads/2025/04/Byggkonjunkturen.pdf)
- [SCB, Sysselsättningen minskar mest i byggbranschen](https://www.scb.se/hitta-statistik/temaomraden/sveriges-ekonomi/fordjupningsartiklar_Sveriges_ekonomi/sysselsattningen-minskar-mest-i-byggbranschen/)
- [SCB, Regionalräkenskaper](https://www.scb.se/hitta-statistik/statistik-efter-amne/nationalrakenskaper/nationalrakenskaper/regionalrakenskaper/)
- [SCB statistikdatabasen, NR0105A](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__NR__NR0105__NR0105A/)
- [Region Örebro län, Befolkning i Örebro län 2025](https://www.regionorebrolan.se/sv/aktuellt/befolkning-i-orebro-lan-2025/)
- [Prop. 2003/04:155, Ändringar i det kommunala utjämningssystemet](https://lagen.nu/prop/2003/04:155)
- [SKR, Marginalintäkter vid befolkningsförändring](https://skr.se/download/18.14fb7b721997a8f53f23b01d/1758788101139/Marginalint%C3%A4kter-vid-befolkningsf%C3%B6r%C3%A4ndring.pdf)
- [Riksrevisionen 2019:29, Det kommunala utjämningssystemet](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/riksrevisionens-granskningsrapport/det-kommunala-utjamningssystemet-behov-av-mer_h7b529/html/)
- [Regionfakta, Kommunal skatt 2025, Örebro län](https://www.regionfakta.com/globalassets/upload/regional-ekonomi_1800/r18n_1800.pdf)
