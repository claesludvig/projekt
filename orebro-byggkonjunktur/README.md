# Byggkonjunkturen i Örebro län: sysselsättning, skatteintäkter och spridningseffekter

Vad nedgången i byggsysselsättningen kostat kommunerna i Örebro län och Region
Örebro län, och vilka spridningseffekter den haft på resten av länsekonomin.

Allt underlag är hämtat från SCB:s statistikdatabas. Eftersom sessionen som tog
fram analysen saknade nätverksåtkomst till `api.scb.se` körs hämtningen i
GitHub Actions (`.github/workflows/orebro_bygg_scb.yml`), som committar tillbaka
uttagen till `data/scb/`. Kör `python3 modell.py` för samtliga tabeller.

---

## Sammanfattning

Byggsysselsättningen i Örebro län föll från **11 141 personer 2023 till 10 644
år 2025 — minus 497 personer, eller 4,5 procent**. Länet följde riket, som föll
4,9 procent. Hypotesen att Örebro skulle ha drabbats hårdare än riket på grund
av sin starka bostadsproduktion 2018–2022 håller inte: nedgången är
riksgenomsnittlig.

Under samma period **steg länets totala sysselsättning**, från 151 483 till
151 742. Arbetskraften absorberades av övriga branscher. Det är avgörande för
svaret på skattefrågan.

Nettoeffekten på kommunernas och regionens skatteintäkter blir därmed
**omkring 29 miljoner kronor om året** — 0,12 procent av länets samlade
skatteintäkter, eller ungefär 45 kommunala årsarbetare. En mekanisk
bruttokalkyl, där varje förlorat byggjobb räknas som förlorad inkomst krona för
krona, ger 104 miljoner. Skillnaden mellan de två talen är hela poängen.

Byggnedgången går inte att utläsa ur länets skatteunderlag. Det gör däremot en
strukturell drift: Örebro läns skatteunderlag har vuxit ungefär en halv
procentenhet långsammare än rikets **varje år sedan 2015**.

## 1. Sysselsättningen

| | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Byggsysselsatta, Örebro län | 10 660 | 10 962 | 11 135 | **11 141** | 10 751 | 10 644 |
| Andel av länets sysselsättning | 7,39 % | 7,49 % | 7,42 % | 7,35 % | 7,10 % | 7,01 % |
| Riket, tusental | 363,6 | 369,5 | 380,5 | **383,4** | 369,0 | 364,7 |

Källa: SCB BAS (AM0210), sysselsatta 15–74 år efter arbetsställets belägenhet.
Den längre RAMS-serien (2008–2021) finns i tabell 1 i modellutskriften och visar
uppgången dessförinnan: från 8 636 personer 2008 till 11 090 år 2021.

Toppen ligger i **2023**, inte 2022. Det är värt att notera för den som daterar
byggkrisen efter bostadsinvesteringarna — sysselsättningen släpar efter
investeringsfallet med ungefär ett år, eftersom pågående projekt färdigställs.

Månadsdatan går till juni 2026 och visar att nedgången planat ut: länet låg på
10 610 i genomsnitt första halvåret 2026, med 10 807 i juni. Botten ligger
bakom oss, men nivån är fortfarande 6,2 procent under toppmånaden 2022M07.

### Kommunvis

| Kommun | 2023 | 2025 | Förändring | |
|---|---|---|---|---|
| Örebro | 6 151 | 5 844 | −307 | −5,0 % |
| Nora | 359 | 291 | −68 | −18,9 % |
| Lindesberg | 785 | 721 | −64 | −8,2 % |
| Degerfors | 195 | 156 | −39 | −20,0 % |
| Karlskoga | 1 160 | 1 129 | −31 | −2,7 % |
| Hällefors | 175 | 152 | −23 | −13,1 % |
| Askersund | 438 | 422 | −16 | −3,7 % |
| Hallsberg | 633 | 621 | −12 | −1,9 % |
| Ljusnarsberg | 98 | 96 | −2 | −2,0 % |
| Laxå | 111 | 122 | +11 | +9,9 % |
| Kumla | 752 | 778 | +26 | +3,5 % |
| Lekeberg | 286 | 312 | +26 | +9,1 % |

Tre fjärdedelar av nedgången ligger i Örebro kommun, vilket följer av att
kommunen har 55 procent av länets byggsysselsättning. Relativt sett är det
däremot de små bruksorterna som tar smällen: Nora och Degerfors tappar en
femtedel. Där handlar det om enskilda företag, inte om konjunktur i statistisk
mening — och där är de kommunalekonomiska marginalerna minst.

## 2. Spridningseffekter

SCB publicerar **inga regionala input-output-tabeller**. Den nationella
symmetriska I/O-tabellen måste regionaliseras, exempelvis med Flegg's location
quotient, där varje cell i A-matrisen skalas efter branschvis sysselsättning
eller förädlingsvärde ur regionalräkenskaperna och en storleksparameter som
straffar små regioner.

En upptäckt värd att notera för framtida arbete: **regionalräkenskaperna
särredovisar inte byggverksamhet på länsnivå**. Länstabellen (NR0105ENS2010T03A)
har bara fem aggregat — varuproducenter, tjänsteproducenter, offentligt,
ej branschfördelat, totalt. Full branschindelning finns bara på
riksområdesnivå, där Örebro ingår i Östra Mellansverige. Byggverksamhetens
förädlingsvärde och lönesumma per län går alltså inte att hämta; det måste
skattas. Samma sak med lönesummorna (AM0302): de finns per län utan bransch,
och per bransch utan län.

Att applicera nationella multiplikatorer på ett län överskattar systematiskt.
Byggsektorn köper stål, cement, installation, maskiner och konsulttjänster till
stor del utanför länet, och importinnehållet i kedjan är högt.

| Sysselsättningsmultiplikator, SNI 41–43 | Typ I | Typ II |
|---|---|---|
| Nationell | ~1,50 | ~2,00 |
| **Intraregional, Örebro län** | **1,15–1,40** | **1,35–1,70** |

Med centralvärdena:

- **−497** direkta byggjobb
- **−124** indirekta hos underleverantörer i länet (typ I)
- **−248** indirekta och inducerade (typ II)
- **≈ −745 jobbårsekvivalenter i länet**

Räknat med den nationella typ II-multiplikatorn hade svaret blivit −994, alltså
en överskattning på en tredjedel. Därutöver cirka 250 jobb hos leverantörer
utanför länet — en nationell effekt som inte tillfaller Örebros skattebaser.

Två varningar hör till metoden: typ II-multiplikatorer överskattar
systematiskt, och I/O-ramverket antar fasta insatskoefficienter och ledig
kapacitet. Det senare är rimligt i en nedgång, mindre rimligt i uppgången.

## 3. Skatteunderlaget: brutto mot netto

Årslönen i bygg i länet är beräknad som rikets lönesumma per byggsysselsatt
(455 033 kr, 2024) gånger länets relativa lönenivå (0,912, beräknad som
lönesumma per sysselsatt i länet delat med samma tal för riket) =
**415 105 kronor**.

Men ett förlorat byggjobb är inte ett förlorat skatteunderlag krona för krona:

1. **A-kassa och aktivitetsstöd är kommunalt skattepliktiga**, på ungefär
   55 procent av tidigare lön. Kommunen förlorar differensen, inte hela lönen.
2. **De flesta fick annat arbete.** Detta är inte ett antagande här utan en
   observation: länets totala sysselsättning steg med 259 personer samtidigt
   som byggsysselsättningen föll med 497.

Fördelningen sätts därför till 65 procent nytt arbete i länet (90 procent av
tidigare inkomst), 20 procent arbetslösa (55 procent) och 15 procent som lämnar
länet eller arbetskraften (15 procent). Det innebär att **28 procent** av
bruttolönebortfallet faktiskt lämnar skatteunderlaget.

| mn kr/år | observerad (−4,5 %) | om det fördjupas (−8 %) | hård (−11 %) |
|---|---|---|---|
| Bruttobortfall lönesumma | −306 | −548 | −754 |
| Nettobortfall efter omställning | **−86** | −155 | −213 |

## 4. Skatteintäkter

Skattesatser 2026: kommunerna i länet 21,64 procent (befolkningsviktat; Örebro
21,35, Degerfors högst med 23,00), Region Örebro län 12,30 procent. Summa 33,94
procent, mot rikets 32,38.

| mn kr/år | observerad | fördjupas | hård |
|---|---|---|---|
| Mekaniskt brutto, kommunerna | −66 | −119 | −163 |
| Mekaniskt brutto, regionen | −38 | −67 | −93 |
| *Mekaniskt brutto, totalt* | *−104* | *−186* | *−256* |
| Realistiskt netto, kommunerna | **−19** | −34 | −46 |
| Realistiskt netto, regionen | **−11** | −19 | −26 |
| **Realistiskt netto, totalt** | **−29** | **−53** | **−72** |

## 5. Utjämningens blinda fläck

Alla tolv kommunerna i länet ligger under garantinivån på 115 procent av
medelskattekraften och är bidragstagare i inkomstutjämningen, med 95 procents
kompensationsgrad.

Hade byggnedgången varit **unik för Örebro län** hade utjämningen kompenserat
cirka 26 av de 29 miljonerna. Kommunerna och regionen hade burit omkring tre
miljoner — ungefär 11 procent.

Men nedgången var **riksgemensam**: länet −4,5 procent, riket −4,9 procent. När
medelskattekraften faller lika mycket som den egna ser utjämningssystemet ingen
relativ försämring. Gapet mot garantinivån krymper proportionellt, bidraget
faller med, och genomslaget blir i praktiken fullt.

Utjämningssystemet försäkrar mot strukturella nivåskillnader mellan kommuner,
inte mot konjunkturell samvariation. Byggkonjunkturrisken i kommunal ekonomi är
därför oförsäkrad — och eftersom byggkonjunkturer nästan alltid är nationella
gäller det generellt, inte bara i det här fallet.

Lägg till eftersläpningen via slutavräkningarna: nedgången 2024–25 landar i
boksluten 2026–27.

## 6. Syns det i skatteunderlaget?

Nej. Örebro läns skatteunderlagstillväxt minus rikets, procentenheter per år:

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| −0,53 | −0,38 | −0,44 | −0,16 | −0,03 | −0,43 | −0,61 | −0,52 | −0,59 | −0,50 | −0,39 | −0,54 |

Snittet är −0,37 före 2022 och −0,51 därefter. Gapet är alltså något större
efter, men 2021 — innan nedgången bet — var större än något år därefter.
Skillnaden ligger inom seriens egen variation.

Det ska den också göra. 497 personer är 0,33 procent av länets sysselsättning,
och bruttoeffekten 0,4 procent av skatteunderlaget — mindre än den strukturella
driften mot riket under ett enskilt år. Den som letar efter byggkrisen i
kommunala bokslut letar på fel ställe.

Vad som däremot finns i datan är den **strukturella driften**: länet har tappat
mot riket varje år sedan 2015, och dess andel av rikets skatteunderlag har
fallit från 2,74 till 2,63 procent på elva år. Mätt mot rikets skatteunderlag
2026 motsvarar det 3,4 miljarder kronor i uteblivet skatteunderlag, eller
1,15 miljarder i årliga skatteintäkter — fyrtio gånger byggnedgångens effekt.

## 7. Vad kalkylen inte fångar

**Befolkningskanalen.** Kommunal ekonomi är i praktiken invånarbaserad — både
skatteunderlaget och utjämningsbidragen. SKR:s marginalintäkt vid
befolkningsförändring ligger kring 65 000 kronor per invånare och år för kommun
och region tillsammans. 1 000 uteblivna invånare är alltså 65 miljoner kronor
per år, mer än dubbelt så mycket som hela den beräknade byggeffekten, och till
skillnad från den bestående. Att länets folkmängd vände nedåt 2025, efter ett
decennium av tillväxt, gör kanalen konkret. Uteblivet bostadsbyggande begränsar
inflyttningen direkt, och det är där byggkonjunkturens kommunalekonomiska
betydelse i huvudsak ligger.

**Engångsintäkterna.** Exploateringsersättningar, markförsäljning och
bygglovsavgifter är volymberoende, slår igenom omedelbart i resultatet och syns
inte i skatteunderlaget alls.

**Fastighetsavgiften ger ingenting.** Nybyggda bostäder färdigställda från 2012
har 15 års befrielse från kommunal fastighetsavgift. Byggandets värde för
kommunen ligger i inflyttningen, inte i fastigheten.

**Staten bär merparten.** Arbetsgivaravgifter, moms på byggvolymen, bolagsskatt
och a-kassa är statliga. Kommunsektorns andel av det samlade
offentligfinansiella bortfallet är sannolikt under en tredjedel.

## 8. Känslighet

Nettobortfallet på 29 miljoner varierar mellan 21 och 52 miljoner för rimliga
parametervärden. Den enskilt mest avgörande parametern är
omställningsantagandet: sätts återinkomsten till noll blir svaret 104 miljoner,
tre och en halv gånger så mycket. Multiplikatorvalet spelar mindre roll — hela
spannet 1,35 till 1,70 ger 27 till 33 miljoner. Att felaktigt använda den
nationella typ II-multiplikatorn ger 39 miljoner.

Med andra ord: i en regional effektstudie av det här slaget ligger osäkerheten
inte i input/output-analysen utan i vad som händer med människorna efteråt.

---

## Köra själv

```bash
python3 hamta_scb.py sok      # kartlägger statistikdatabasens träd
python3 hamta_scb.py hamta    # hämtar de fjorton serierna till data/scb/
python3 bearbeta.py           # skriver data/kalibrering.json
python3 modell.py --csv       # tabeller + data/resultat.csv
```

Hämtningen kräver åtkomst till `api.scb.se`. Workflowet
`.github/workflows/orebro_bygg_scb.yml` kör hela kedjan och committar
resultatet; det triggas av ändringar i `hamta_scb.py` eller `bearbeta.py` och
kan startas manuellt.

### Datakällor

| Serie | Tabell |
|---|---|
| Byggsysselsättning per kommun och bransch, 2020– | BAS, `AM/AM0210/AM0210B/ArbStDoNArNN` |
| Samma, månadsvis till 2026M06 | `AM/AM0210/AM0210B/ArbStDoNMNN` |
| Byggsysselsättning 2008–2021 | RAMS, `AM/AM0207/AM0207K/DagSNI07KonK` m.fl. |
| BRP, sysselsatta, löner per län | `NR/NR0105/NR0105A/NR0105ENS2010T03A` |
| Samma per riksområde, full branschindelning | `NR0105ENS2010T04A` |
| Fasta bruttoinvesteringar per region och bransch | `NR0105ENS2010T05A` |
| Lönesummor per län | `AM/AM0302/AM0302A/LSUMLan` |
| Lönesummor per bransch, riket | `AM/AM0302/AM0302A/LSUMSNI07` |
| Skatteunderlag och skattekraft per kommun | `OE/OE0101/SkatteKraft` |
| Skattesatser per kommun, 2000– | `OE/OE0101/Kommunalskatter2000` |
| Kommunalekonomisk utjämning | `OE/OE0115/OE0115A/KomEkUtj` |

Multiplikatorerna och omställningsantagandena är modellval och ligger i
`parametrar.py`, märkta `ANTAGET`. Övriga värden läses från
`data/kalibrering.json` och är märkta `HÄMTAT`.

### Övriga källor

- [Prop. 2003/04:155, Ändringar i det kommunala utjämningssystemet](https://lagen.nu/prop/2003/04:155)
- [SKR, Marginalintäkter vid befolkningsförändring](https://skr.se/download/18.14fb7b721997a8f53f23b01d/1758788101139/Marginalint%C3%A4kter-vid-befolkningsf%C3%B6r%C3%A4ndring.pdf)
- [Riksrevisionen 2019:29, Det kommunala utjämningssystemet](https://www.riksdagen.se/sv/dokument-och-lagar/dokument/riksrevisionens-granskningsrapport/det-kommunala-utjamningssystemet-behov-av-mer_h7b529/html/)
- [Byggföretagen, Sysselsättning inom byggverksamhet](https://byggforetagen.se/statistik/antal-ans/)
- [Region Örebro län, Befolkning i Örebro län 2025](https://www.regionorebrolan.se/sv/aktuellt/befolkning-i-orebro-lan-2025/)
