"""Bygger analys/staten.html: Ohlin om staten, partiet och det politiska arbetet.

Texten nedan är en tolkning av Ohlins inlägg i riksdagen 1938–1970. Alla citat hämtas från
citat.py och kontrolleras mot inläggen (verifiera.py) innan sidan skrivs.
"""
import html, os, sys

HÄR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HÄR)
from verifiera import slå_upp, slå_upp_övriga

REGISTER = 'https://claude.ai/artifact/J6zjBRdJh6y2WUpLWBxmEB'
MÅN = ['januari', 'februari', 'mars', 'april', 'maj', 'juni', 'juli', 'augusti', 'september', 'oktober',
       'november', 'december']

HÅLLPUNKTER = [
    ('Makten ska vara spridd.',
     'Decentralisering är hans grundtanke. Den gäller både statens och de enskilda storföretagens makt. '
     'Argumentet är dubbelt: ett decentraliserat system är effektivare, och det ger människorna större oberoende.'),
    ('Staten ska vara stark på få områden.',
     'Konjunkturpolitik, social trygghet, utbildning och ett stadigt penningvärde är statens uppgifter. '
     'Detaljstyrning av näringslivet är det inte. Frågan är inte om man ska planera, utan vem som ska göra det. '
     'Redan 1934 kallar han den statliga ramen för "ramhushållning".'),
    ('Organisationssamhället är det nya styrelseproblemet.',
     'Från 1942 och framåt återkommer han till risken att uppgörelser mellan regeringen och de stora '
     'organisationerna gör riksdagen till en instans som bara godkänner i efterhand, en "tredje kammare".'),
    ('Institutionerna bestämmer vilka majoriteter som kan regera.',
     'Tvåkammarsystemet lät en äldre opinion styra över den aktuella. Enkammarriksdagen, ett rättvisare '
     'valsystem och beslutande folkomröstningar är för honom villkor för en fungerande parlamentarism.'),
    ('Oppositionen har ett eget arbete att göra.',
     'Den ska granska, lägga fram alternativ och göra praktiskt nytta i utskotten. Han avvisar tanken att låta '
     'regeringen misslyckas och kräver att oppositionen får tillgång till utredningar och experter.'),
    ('Hållbara reformer kräver samling.',
     'En reform som bärs av en bred uppgörelse står kvar. En reform som drivs igenom efter hård strid kan rivas upp. '
     'Samling förutsätter att alla parter ger efter, och annars lovar han motstånd.'),
    ('Förändring har ekonomiska och psykologiska villkor.',
     'Tillväxten finansierar reformerna. Inflation leder till regleringar, och regleringar leder till byråkrati. '
     'Åtgärder ska sättas in i tid och vara tillräckliga, och den som vill behålla ett system med enskilt initiativ '
     'måste respektera det systemets drivkrafter.'),
]

AVSNITT = [
    ('makt', 'Spridd makt som grundtanke', [
        ('p', 'Den tanke som bär hela Ohlins politiska argumentation är att beslutsmakt ska vara spridd. Han formulerar den '
              'som handelsminister i samlingsregeringen i januari 1945, i en debatt med Gunnar Myrdal, och återkommer till '
              'den i nästan samma ord i den allmänpolitiska debatten i oktober 1970, strax innan tvåkammarriksdagen upphörde.'),
        ('q', 'decentral1945'),
        ('p', 'Argumentet har två delar som han håller ihop. Den ena gäller effektivitet: staten kan inte sköta allt, och en '
              'central förvaltning har begränsad kapacitet. Den andra gäller frihet: makt som samlas hos de styrande och '
              'förvaltningen hamnar hos ett fåtal, även när den sägs utövas för folkets räkning.'),
        ('q', 'tjänstemän1945'),
        ('q', 'fåtal1953'),
        ('p', 'I samma anförande 1953 räknar han upp vad som faktiskt har gjort människor friare: stigande levnadsstandard, '
              'demokratin och fackföreningarna. Det sista är värt att notera. Ohlin ser starka fackliga organisationer som en '
              'del av det liberala samhället, inte som ett hot mot det. År 1970 sammanfattar han skiljelinjen mot '
              'socialdemokratin som en fråga om maktkoncentration, och han riktar kritiken mot både statlig och enskild makt.'),
        ('q', 'central1970'),
        ('q', 'kapital1970'),
        ('p', 'Samma tanke står i partiets program. Programmet 1944 antogs samma sommar som Ohlin blev partiledare. Programmet 1962, det enda nya principprogrammet under hans tid, skriver in maktkritiken mot både staten och de enskilda kapitalägarna. Programmen är kollektiva texter och inte hans egna formuleringar. De visar vad partiet under hans ledning ställde sig bakom.'),
        ('q', 'behärskat1944'),
        ('q', 'makt1962'),
    ]),
    ('staten', 'Statens uppgifter och gränser', [
        ('p', 'Ohlin är ingen anhängare av en svag stat. Han var en av de ekonomer som redan före 1932 förordade en aktiv '
              'konjunkturpolitik, och han påpekar själv att han fått "lida åtskillig smälek" för att han sympatiserat med '
              'planhushållning. Hans poäng är en annan: staten ska koncentrera sig på det som bara den kan göra.'),
        ('q', 'planera1943'),
        ('q', 'händerna1945'),
        ('p', 'Resonemanget är äldre än riksdagsåren. I Nationalekonomiska föreningens debatt om planhushållning i november 1934, med Eli Heckscher och Gunnar Myrdal, avvisar han själva motsättningen mellan plan och marknad. Han gör frågan till ett organisationsproblem som får olika svar på olika områden.'),
        ('q', 'planhush1934'),
        ('q', 'organisation1934'),
        ('p', 'I samma inlägg delar han in statens ingrepp i fyra slag: egen affärsverksamhet som posten, kontroll som yrkesinspektion och monopollagstiftning, konjunkturpolitik och det han kallar <em>ramhushållning</em>. Den sista typen beskriver han med tydlig sympati. Staten drar upp ramar genom lagstiftning, och inom dem sköter sig företagen själva. Han tar jordbrukspolitiken som exempel.'),
        ('q', 'ramhush1934'),
        ('p', 'I interpellationen efter valet 1952, en av hans mest samlade programtexter i riksdagen, formulerar han principen '
              'som en regel för regeringen: den som försöker göra allt sköter också sina kärnuppgifter sämre.'),
        ('q', 'begränsning1952'),
        ('p', 'Planering och prognoser får en tydlig roll men en begränsad funktion. Planen ska ange ramar och villkor, inte '
              'styra enskilda beslut. Skälet är att framtiden är osäker. En plan som låses fast i regleringar blir ett hinder '
              'den dag utvecklingen tar en annan väg. Han påpekar också att politiker väljs för andra egenskaper än '
              'dem som krävs för att bedöma en bransch.'),
        ('q', 'rörlighet1948'),
        ('q', 'ramar1970'),
        ('q', 'ramar1970b'),
        ('q', 'politiker1970'),
        ('p', 'Programmet 1962 gör samma avvägning till en regel för statlig företagsamhet.'),
        ('q', 'affär1962'),
        ('p', 'Byråkratikritiken är inte riktad mot tjänstemännen utan mot systemet. Ett regleringssystem blir byråkratiskt av '
              'sin egen logik. Mot den enskilda myndighetsutövningen ställer han rättssäkerheten. På 1950-talet driver '
              'folkpartiet kravet att regeringens och myndigheternas beslut ska kunna prövas i domstol.'),
        ('q', 'byråkrati1946'),
        ('q', 'individ1960'),
        ('q', 'medel1960'),
        ('p', 'Motionerna visar hur rättssäkerhetskravet skulle genomföras. Från 1954 och framåt lägger folkpartiet med Ohlin som första namn fram en serie motioner om domstolsprövning av förvaltningsbeslut, om ett opartiskt förfarande i myndigheterna och om grundlagsskydd för medborgerliga fri- och rättigheter. Argumentet är att förvaltningen har vuxit ifrån de kontrollformer som fanns.'),
        ('q', 'rättsstat1954'),
        ('q', 'åklagare1954'),
        ('q', 'grundlag1958'),
        ('p', 'Samma hållning gäller förhållandet mellan stat och kommun. Programmet 1944 vill undvika en långtgående centralisering av förvaltningen. En motion 1953 föreslår att statens kontroll över kommunerna ska ske i efterhand och gälla maktmissbruk, inte styra kommunerna i förväg.'),
        ('q', 'centralisering1944'),
        ('q', 'kommun1953'),
    ]),
    ('organisationer', 'Riksdagen och organisationerna', [
        ('p', 'En fråga som går igen i trettio år är hur riksdagens ställning påverkas av att regeringen förhandlar direkt '
              'med näringslivets och arbetsmarknadens organisationer. Under kriget 1942 ställer han frågan själv. Då '
              'bedömer han farhågorna som ogrundade, eftersom riksdagen har lagt fast riktlinjerna och regeringen '
              'väljer vilka den förhandlar med.'),
        ('q', 'tredje1942'),
        ('p', 'Partiprogrammet 1944 anger grundhållningen. Organisationerna är en del av demokratin men får inte tvinga enskilda eller dela upp politiken efter intressen.'),
        ('q', 'org1944'),
        ('p', 'Efter kriget blir han mer oroad. År 1950 kallar han förhållandet mellan regeringen, riksdagen och '
              'organisationerna för "det stora problemet" i landets styrelse och begär en utredning om riksdagens '
              'inflytande i "organisationssamhället". År 1951 menar han att fackföreningarna inte i längden kan bära '
              'ansvaret för att hålla nere lönerna åt staten. År 1955 kritiserar han att jordbrukspolitiken avgörs '
              'genom en kompromiss mellan organisationerna som regeringen sedan lägger fram för riksdagen.'),
        ('q', 'org1950'),
        ('q', 'fack1951'),
        ('q', 'korporativ1955'),
        ('p', 'Kritiken gäller också hur det ser ut för oppositionen. Regeringen har sina fasta kanaler till näringslivet, '
              'som Harpsundsöverläggningarna och det näringspolitiska rådet. Oppositionen har inga sådana.'),
        ('q', 'harpsund1968'),
        ('p', 'Programmet 1962 innehåller partiets svar. Det avvisar korporativt styre uttryckligen. I stället för slutna överläggningar mellan regeringen och organisationerna föreslår det ett öppet ekonomiskt-socialt råd där också riksdagen finns med.'),
        ('q', 'korporativt1962'),
        ('q', 'råd1962'),
    ]),
    ('forfattning', 'Parlamentarism, kammare och valsystem', [
        ('p', 'Ohlins författningspolitik utgår från en konkret iakttagelse. Från och med valet 1952 fick socialdemokraterna '
              'färre röster än de tre borgerliga partierna tillsammans men behöll ändå makten, eftersom första kammaren '
              'speglade äldre val. Han behandlar det som ett demokratiproblem och pekar på att '
              'formerna för demokratins arbete i stort sett har stått stilla.'),
        ('q', 'arbetsformer1952'),
        ('q', 'enkammare1957'),
        ('p', 'Enkammarmotionen 1953, som Ohlin skrev under och som hade Georg von Friesen som första namn, beskriver problemet med tvåkammarsystemet i siffror.'),
        ('q', 'enkammar1953'),
        ('p', 'Folkpartiets riksdagsgrupp motionerade om en enkammarriksdag 1953. När reformen beslutas i maj 1968 kallar '
              'Ohlin den en milstolpe för både demokratin och liberalismen. Han säger också rakt ut att den långa '
              'utredningen fungerade som en broms.'),
        ('q', 'demokrati1968'),
        ('q', 'tolv1968'),
        ('q', 'konservativt1968'),
        ('q', 'svunnen1968'),
        ('p', 'Valsystemet ska ge en rättvis fördelning av mandaten utan att partierna behöver valkarteller. Det ska också '
              'göra det möjligt att rösta efter övertygelse. Han vill komplettera den representativa demokratin med '
              'beslutande folkomröstningar i vissa frågor. Samtidigt betonar han att inga regler ersätter viljan att '
              'kompromissa.'),
        ('q', 'samförstånd1952'),
        ('q', 'extrema1962'),
        ('p', 'Folkomröstningen återkommer i motioner 1948 och 1953, båda med Ohlin som första namn. Motiveringen är både demokratisk och praktisk. Folket ska få ett direkt ansvar, och regering och riksdag ska tvingas ta mer hänsyn till olika gruppers synpunkter. I programmet 1962 blir folkomröstningen ett minoritetsskydd. Riksdagen ska också få egna tjänstemän och därmed bli mindre beroende av regeringens förvaltning.'),
        ('q', 'folkomr1948'),
        ('q', 'folkomr1953'),
        ('q', 'minoritet1962'),
        ('q', 'tjänstemannakår1962'),
    ]),
    ('opposition', 'Regering, opposition och samling', [
        ('p', 'Ohlin ledde folkpartiet i 23 år, de flesta av dem som oppositionens största parti, och hans syn på oppositionens roll är genomtänkt. '
              'Oppositionen ska granska och kritisera, men det ger inte regeringen rätt att behandla sina förslag som '
              'färdiga. Han pekar på en asymmetri: regeringen har förvaltningen och utredningsväsendet till sitt '
              'förfogande, medan oppositionen bara undantagsvis kan ta fram detaljerade förslag.'),
        ('q', 'kritik1948'),
        ('q', 'heliga1948'),
        ('q', 'apparat1948'),
        ('q', 'danmark1957'),
        ('p', 'Hans viktigaste tanke här gäller hur länge en reform står sig. Efter folkomröstningen om pensionerna och '
              'regeringskrisen hösten 1957 formulerar han den så här:'),
        ('q', 'grundmurad1957'),
        ('q', 'diktera1957'),
        ('q', 'huvudfråga1957'),
        ('p', 'Samling är dock inte detsamma som eftergivenhet. Han kräver att förhandlingar förs på riktigt, där parterna '
              'närmar sig varandra i stället för att den ena bestämmer sig först. Om den andra sidan vägrar lovar han '
              'motstånd. År 1962 avvisar han uttryckligen tanken att oppositionen tjänar på att regeringen misslyckas.'),
        ('q', 'tredjeregel1957'),
        ('q', 'bundit1970'),
        ('q', 'motstånd1952'),
        ('q', 'katastrof1962'),
        ('q', 'tvåsätt1962'),
        ('q', 'debatt1962'),
        ('p', 'Redan som statsråd i samlingsregeringen 1945 försvarar han rätten att föra en principiell debatt även inifrån '
              'regeringen. En långvarig samling får inte kväva meningsbrytningen.'),
        ('q', 'yttrandefrihet1945'),
    ]),
    ('partiet', 'Folkpartiet och den sociala liberalismen', [
        ('p', 'Ohlin beskriver folkpartiet som ett vänsterparti i frihetsfrågorna, mer konsekvent än socialdemokratin, '
              'som han menar har fastnat i klasstänkande. Det är en medveten markering mot bilden av ett borgerligt block. '
              'Han definierar liberalismen utifrån individen och inte utifrån klass.'),
        ('q', 'vänster1948'),
        ('q', 'klass1948'),
        ('q', 'liberal1946'),
        ('p', 'Valmanifesten och programmen talar samma språk. År 1948 gäller det "kommissionsväldet", 1956 "förmyndarskap". År 1962 formuleras skiljelinjen som personligt ansvar mot yttre tvång.'),
        ('q', 'kommission1948'),
        ('q', 'förmyndar1956'),
        ('q', 'kommando1962'),
        ('p', 'Mot socialdemokratin talar han om en gradskillnad i synen på samhällets inflytande som blir så stor att den '
              'i praktiken blir en artskillnad. Fördelningspolitiken har en klassisk socialliberal formel, som han '
              'upprepar från 1943 och framåt.'),
        ('q', 'grad1949'),
        ('q', 'jämn1946'),
        ('p', 'Partiets särart beskriver han som en fråga om idéer snarare än intressen. Han konstaterar att partiet saknar '
              'stöd av mäktiga fackliga organisationer och gör idéerna till partiets bas. På 1960-talet blir '
              'samarbetet med centerpartiet hans svar på regeringsfrågan. En borgerlig regering skulle få sin tyngdpunkt '
              'i mitten.'),
        ('q', 'idéer1960'),
        ('q', 'fackstöd1960'),
        ('q', 'bisak1960'),
        ('q', 'reformvänligt1955'),
        ('q', 'mitten1966'),
    ]),
    ('forandring', 'Förutsättningar för politiskt driven förändring', [
        ('p', 'Jag har inte hittat något inlägg där Ohlin samlat vad som krävs för att en politisk förändring ska lyckas. '
              'Villkoren går ändå att läsa ut ur hans inlägg, och de är förvånansvärt stabila över tiden.'),
        ('h', 'Tillväxten är reformernas finansiering'),
        ('p', 'Sociala reformer blir möjliga när produktionen växer. Det är därför han ser tillväxtpolitik och '
              'socialpolitik som samma sak och avvisar att de skulle stå mot varandra.'),
        ('q', 'standard1952'),
        ('q', 'dynamik1970'),
        ('p', 'Programmen bygger in samma tanke. År 1944 är det den enskildes egen ansträngning som ska föras samman med samhällets åtgärder. År 1962 är det tillväxten som gör reformer och skattesänkningar möjliga samtidigt.'),
        ('q', 'fattigdom1944'),
        ('q', 'tillväxt1962'),
        ('h', 'Den som behåller ett system får respektera dess drivkrafter'),
        ('p', 'Mot Myrdal 1945 formulerar han det som ett val. Den som vill ha kvar ett system byggt på enskilt initiativ kan '
              'inte stegvis ta bort dess drivkrafter utan att ersätta dem med något annat.'),
        ('q', 'stolar1945'),
        ('q', 'respektera1945'),
        ('h', 'Balans före reglering'),
        ('p', 'Inflation och överhettning leder till regleringar, och regleringar leder till byråkrati. Därför är '
              'makroekonomisk balans för honom en förutsättning för ett liberalt samhälle och inte bara ett '
              'konjunkturpolitiskt mål.'),
        ('q', 'balans1948'),
        ('h', 'I tid, tillräckligt och med hänsyn till förtroendet'),
        ('p', 'Efter valet 1948 sammanfattar han sina krav på den ekonomiska politiken i fyra led. Det sista är det mest '
              'Ohlinska: politiken måste ta hänsyn till hur människor och företag reagerar, deras förtroende och deras '
              'vilja att spara och investera.'),
        ('q', 'itid1948'),
        ('h', 'Tydliga regler och försiktighet med löften'),
        ('p', 'Mot finansminister Wigforss i Nationalekonomiska föreningen 1946 kräver han enkla och fasta regler för budgeten. Utan dem kan nästan varje utgift kallas en investering. Han varnar också för att binda sig för utgifter innan man vet hur inkomsterna utvecklas.'),
        ('q', 'kritstreck1946'),
        ('q', 'binder1946'),
        ('h', 'Gradvis anpassning'),
        ('p', 'Redan 1934 beskriver han institutionell förändring som en fortlöpande anpassning till nya förutsättningar, som storföretag, teknik och befolkning, och inte som ett systemskifte.'),
        ('q', 'anpassning1934'),
        ('h', 'Mandat och opinion'),
        ('p', 'En genomgripande förändring kräver ett mandat som har prövats i val. Han läser också valresultat som '
              'tendenser över flera val, inte bara som mandatsiffror i ett enskilt val.'),
        ('q', 'mandat1948'),
        ('q', 'huvudsak1945'),
        ('q', 'tendenser1952'),
        ('h', 'Kritik och opposition som förändringskraft'),
        ('p', 'Förändringen kommer ofta från oppositionen. Han beskriver ett återkommande mönster: förslaget röstas ned '
              'några år och antas sedan i något ändrad form. Opinionens tryck har en funktion i sig.'),
        ('q', 'klagomål1948'),
        ('q', 'mönster1970'),
    ]),
    ('analys', 'Analyserna bakom', [
        ('p', 'Ohlin argumenterar som nationalekonom, och det märks i hur han bygger sina resonemang. Fyra analytiska '
              'grepp återkommer.'),
        ('p', '<strong>Makroekonomi från Stockholmsskolan.</strong> Han hänvisar till att hans generation av ekonomer '
              'redan före 1932 var överens om en aktiv konjunkturpolitik. Striden gäller för honom inte om staten ska stabilisera '
              'ekonomin, bara med vilka medel och hur mycket den ska styra i detalj.'),
        ('q', 'ekonomer1932'),
        ('p', '<strong>Prisbildningen som samordning.</strong> Priserna ska styra produktionen. Det gör att den centrala '
              'planeringen alltid möter en informations- och kapacitetsgräns.'),
        ('q', 'prisbildning1946'),
        ('p', '<strong>Storleksordningar.</strong> Han räknar gärna. År 1945 visar han att en fullständig konfiskation av '
              'inkomster över 10 000 kronor skulle ge omkring 200 miljoner kronor mot en nationalinkomst på 15–17 '
              'miljarder. Slutsatsen är att tillväxten betyder mer än omfördelningen för de breda gruppernas standard. '
              'Samma resonemang använder han 1970 om utbildningen.'),
        ('q', 'storlek1945'),
        ('q', 'utbildning1970'),
        ('p', '<strong>Valstatistik och institutioner.</strong> Han behandlar röstsiffror som tidsserier och kopplar dem '
              'till hur mandaten fördelas. Den analysen ligger bakom kravet på enkammarriksdag och nytt valsystem. Han '
              'försvarar dessutom ekonomernas rätt att delta i politiken som medborgare och inte bara som experter.'),
        ('q', 'eunucker1945'),
        ('p', 'Tio år tidigare formulerar han samma sak som en kunskapsteoretisk poäng. Ekonomiska råd bygger alltid på en politisk målsättning, och det bör sägas öppet.'),
        ('q', 'målsättning1934'),
    ]),
]

FASER = [
    ('1930–1937', 'Ekonomen i debatten',
     'Som professor skriver han Arbetslöshetsutredningens bidrag om penningpolitik och offentliga arbeten (SOU 1934:12). '
     'I Nationalekonomiska föreningen avvisar han 1934 motsättningen mellan plan och marknad och formulerar tanken om '
     'ramhushållning.'),
    ('1938–1944', 'Första kammaren, krigsåren',
     'Ohlin kommer in i första kammaren 1938. Han är pragmatisk i krisekonomin och accepterar regeringens förhandlingar med '
     'organisationerna 1942, men frågar vem som ska planera. Han blir folkpartiets ordförande 1944.'),
    ('1944–1945', 'Handelsminister i samlingsregeringen',
     'Som statsråd använder han remissdebatten 1945 till en principiell uppgörelse med Myrdal om decentralisering och '
     'statens gränser. Han försvarar statsrådens rätt att debattera principfrågor även i en samlingsregering.'),
    ('1945–1948', 'Planhushållningsstriden',
     'Socialiseringen och arbetarrörelsens 27-punktsprogram står i centrum. Han kritiserar byråkratiseringen. Efter valet '
     '1948, då folkpartiet växer kraftigt, hävdar han att socialiseringen saknar folkligt mandat och att politiken måste gå '
     'efter socialliberala linjer.'),
    ('1949–1958', 'Organisationssamhället och parlamentarismen',
     'Han tar upp organisationernas makt och kräver enkammarriksdag, rättvist valsystem och beslutande folkomröstningar. '
     'Motionerna om domstolsprövning och rättssäkerhet i förvaltningen kommer 1954–1960. '
     'Han ställer frågan om strid eller samling kring pensionerna och folkomröstningen 1957.'),
    ('1959–1967', 'Mittensamverkan',
     'Han utvecklar sin syn på oppositionens roll, med kompromisser i utskotten men utan katastrofteori. Han betonar '
     'idéer före intressen och rättssäkerhet. Partiprogrammet 1962 avvisar korporativt styre och föreslår ett öppet '
     'ekonomiskt-socialt råd. Samarbetet med centerpartiet ska göra mitten till en regeringsbas. '
     'Han avgår som partiledare 1967.'),
    ('1968–1970', 'Enkammarreformen och avskedet',
     'Enkammarreformen beslutas 1968. I den allmänpolitiska debatten i oktober 1970 sammanfattar han skiljelinjen som '
     'maktkoncentration mot decentralisering, med närdemokratin som nästa steg.'),
]


def datum(d):
    y, m, dd = d.split('-')
    return f'{int(dd)} {MÅN[int(m) - 1]} {y}'


def datum_fritt(d):
    return datum(d) if len(d) == 10 else d


def citat(k, C):
    c = C[k]
    if 'källa' in c:
        rå = (f'<details><summary>OCR-text i källan</summary><p>{html.escape(c["rå"])}</p></details>'
              if 'rå' in c else '')
        return (f'<figure class="q ovr"><blockquote>{html.escape(c["text"])}</blockquote>'
                f'<figcaption><span>{html.escape(c["källa"])} · {datum_fritt(c["datum"])}</span>'
                f'<a href="{c["url"]}" target="_blank" rel="noopener">Källan</a>{rå}</figcaption></figure>')
    typ = {'kort genmäle': ' · kort genmäle', 'som statsråd': ' · som handelsminister'}.get(c['typ'], '')
    return (f'<figure class="q"><blockquote>{html.escape(c["text"])}</blockquote>'
            f'<figcaption><span>{datum(c["datum"])} · {c["kammare"].lower()}{typ}</span>'
            f'<a href="https://data.riksdagen.se/dokument/{c["dok_id"]}.html" target="_blank" rel="noopener">'
            f'Protokollet</a></figcaption></figure>')


def bygg():
    C, fel = slå_upp()
    Ö, föl = slå_upp_övriga()
    if fel or föl:
        sys.exit(f'Citat som inte går att kontrollera: {fel + föl}')
    antal_prot = len(C)
    C.update(Ö)
    delar = []
    for aid, rubrik, innehåll in AVSNITT:
        kropp = []
        for typ, v in innehåll:
            if typ == 'p':
                kropp.append(f'<p>{v}</p>')
            elif typ == 'h':
                kropp.append(f'<h3>{html.escape(v)}</h3>')
            else:
                kropp.append(citat(v, C))
        delar.append(f'<section id="{aid}"><h2>{html.escape(rubrik)}</h2>{"".join(kropp)}</section>')
    hp = ''.join(f'<li><strong>{html.escape(a)}</strong> {html.escape(b)}</li>' for a, b in HÅLLPUNKTER)
    faser = ''.join(f'<li><span class="yr">{a}</span><div><b>{html.escape(b)}</b><p>{html.escape(c)}</p></div></li>'
                    for a, b, c in FASER)
    toc = ''.join(f'<a href="#{aid}">{html.escape(r)}</a>' for aid, r, _ in AVSNITT)
    sida = open(os.path.join(HÄR, 'mall.html')).read()
    sida = (sida.replace('{{HALLPUNKTER}}', hp).replace('{{FASER}}', faser).replace('{{AVSNITT}}', ''.join(delar))
            .replace('{{TOC}}', toc).replace('{{REGISTER}}', REGISTER).replace('{{ANTAL}}', str(len(C))).replace('{{ANTAL_PROT}}', str(antal_prot))
            .replace('{{ANTAL_OVR}}', str(len(Ö))))
    open(os.path.join(HÄR, 'staten.html'), 'w').write(sida)
    print(f'staten.html: {len(C)} kontrollerade citat ({antal_prot} ur protokollen, {len(Ö)} ur övriga källor)')


if __name__ == '__main__':
    bygg()
