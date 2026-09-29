"""Partiernas ställningstaganden per område, ur deras egna program inför riksdagsvalet 2026.

Källor: partiernas valmanifest och valplattformar 2026 (för S de vallöften som presenterats och de politiska
riktlinjer kongressen beslutade 2025). Texterna hämtas som dokument (kallor.DOKUMENT, typ "partiprogram") och
sparas i data/kallor/txt/prog_*.txt. Citat får också hämtas ur partiernas egna politiksidor (POLITIK_AO nedan).

Varje fråga är ett konkret förslag som flera partier tar ställning till. Svaret är
  "ja"      programmet driver förslaget
  "nej"     programmet vänder sig mot förslaget
  "delvis"  programmet går en bit på vägen eller med villkor
och bygger alltid på ett ordagrant citat ur partiets program. tests/test_partier.py kontrollerar att varje citat
finns i partiets texter. Saknas partiet för en fråga ger texterna inget besked: det betyder inte att partiet saknar
åsikt, bara att valmanifestet och politiksidorna inte tar upp saken.

Frågorna och tolkningen av citaten är gjorda för hand och kan ifrågasättas; citatet visas alltid bredvid svaret.
"""

# Parti -> dokument (id i kallor.DOKUMENT) som citaten får hämtas ur
PROGRAM = {
    "S": ["prog_s_valloften_2026", "prog_s_riktlinjer_2025"],
    "M": ["prog_m_2026"],
    "SD": ["prog_sd_2026"],
    "C": ["prog_c_2026"],
    "V": ["prog_v_2026"],
    "KD": ["prog_kd_2026"],
    "L": [f"prog_l_2026_{i}" for i in range(1, 9)],
    "MP": ["prog_mp_2026"],
}
PROGRAM_NAMN = {
    "S": "Vallöften 2026 och Politiska riktlinjer 2025", "M": "Valmanifest 2026 – För ett rättvisare Sverige",
    "SD": "Valplattform 2026 – Hemma i Sverige", "C": "Valmanifest 2026 – Sverige kan mer",
    "V": "Valplattform 2026", "KD": "Valmanifest 2026 – Tro på Sverige", "L": "Valmanifest 2026",
    "MP": "Valmanifest 2026 – Sverige vinner på grön politik",
}

# Partiernas samlade politik ("Politik A–Ö" på respektive webbplats): parti -> (listsida eller sitemap,
# mönster för ämnessidorna). Hämtas av hamta.hamta_politik_ao() till data/kallor/politik/<parti>.json.
POLITIK_AO = {
    "V": ("https://www.vansterpartiet.se/var-politik/politik-a-o/",
          r"vansterpartiet\.se/var-politik/politik-a-o/[A-Za-z0-9%_.-]+/?$"),
    "S": ("https://www.socialdemokraterna.se/rest-api/sitemapXml",
          r"socialdemokraterna\.se/var-politik/a-till-o/[A-Za-z0-9%_.-]+$"),
    "MP": ("https://www.mp.se/politik/", r"mp\.se/politik/[A-Za-z0-9%_.-]+/?$"),
    "C": ("https://www.centerpartiet.se/var-politik/politik-a-o",
          r"centerpartiets-politik-a-o/[A-Za-z0-9%_.-]+(/[A-Za-z0-9%_.-]+)?/?$"),
    "L": ("https://www.liberalerna.se/politik-a-o", r"liberalerna\.se/politik/[A-Za-z0-9%_.-]+/?$"),
    "KD": ("https://kristdemokraterna.se/var-politik/politik-a-till-o", r"/var-politik/politik-a-till-o/[A-Za-z0-9%_.-]+/?$"),
    "M": ("https://moderaterna.se/var-politik/", r"moderaterna\.se/var-politik/[A-Za-z0-9%_.-]+/?$"),
    "SD": ("https://www.sd.se/a-o-matters-sitemap.xml", r"sd\.se/a-till-o/[A-Za-z0-9%_.-]+/?$"),
}
# Sekunder mellan anropen per parti (SD:s robots.txt begär 10)
POLITIK_PAUS = {"SD": 10}

# Områden att bläddra i partiernas samlade politik: (id, namn, mönster mot ämnessidans rubrik). En sida kan höra
# till flera områden. Sidor vars rubrik inte matchar något mönster placeras efter vilka mönster som oftast
# förekommer i texten. De sju första id:na är desamma som i STANDPUNKTER, så att förslagstabellen hamnar rätt.
POLITIK_OMRADEN = [
    ("rattsvasende", "Lag, rätt och trygghet",
     r"brott|polis|rättsväs|lag och rätt|rättsstat|kriminal|straff|gäng|trygghet|våld|fängelse|narkotik|vittne|terror|"
     r"domstol|nämndem|skjutvapen|bedrägeri|hedersrelat|sexualbrott|ungdomsbrott|visitation|avlyssning|kameraöverv"),
    ("vard", "Vård och omsorg",
     r"vård|sjukhus|hälsa|psykisk|tandvård|läkemedel|omsorg|assistans|\blss\b|antibiotika|andts|alkohol|tobak|abort|"
     r"cancer|dödshjälp|hjälpmedel|ungdomsmottagning|spelreklam|missbruk|beroende|suicid|sjukskötersk|läkare|ambulans|förlossning|spel om pengar"),
    ("skola", "Skola och utbildning",
     r"skol|utbildning|förskol|lärare|betyg|högskol|universitet|forskning|studie|folkbild|bildning|\bsfi\b|elev|"
     r"läsande|nationella prov|läxhjälp|yrkeshögskol|komvux|fritids"),
    ("ekonomi", "Ekonomi och skatter",
     r"skatt|ekonomi|budget|\brut\b|\brot\b|statsfinans|inflation|ränta|finanspolit|bank|konsument|matpris|"
     r"hushållens|skuld|tull|privatekonomi|avdrag|\bemu\b|euron"),
    ("energi", "Energi", r"energi|kärnkraft|\bel(?:en|pris|nät|försörjning|produktion|system)?\b|vindkraft|vattenkraft|solkraft|elpris|uran"),
    ("integration", "Migration och integration",
     r"migration|integration|asyl|invandr|medborgarskap|utvis|anhörig|segregation|återvandr|flykting|"
     r"utanförskap|frontex|tiggeri|nyanlän|svenska för|uppehållstillstånd|arbetskraftsinvandr"),
    ("forsvar", "Försvar och säkerhet",
     r"försvar|nato|säkerhetspolit|beredskap|\bplikt|värnplikt|civilplikt|krisberedskap|totalförsvar|hemvärn|cyber"),
    ("jobb", "Jobb och arbetsmarknad",
     r"jobb|arbetsmarknad|arbetslös|a-kassa|arbetsrätt|löne|anställ|arbetsförmedl|arbetsmiljö|arbetstid|"
     r"kompetensförsörj|sysselsättning|arbetsliv|visstid|lärling"),
    ("trygghetssystem", "Pension, familj och trygghetssystem",
     r"pension|sjukförsäkr|socialförsäkr|bidrag|försörjningsstöd|föräldra|barnbidrag|familj|trygghetssystem|senior|"
     r"äldre|barn|grundlön|fattigdom|socialtjänst|socialpolit|välfärd|adoption|äktenskap|ensamhet|anhörig"),
    ("bostad", "Bostad och samhällsbyggnad",
     r"bostad|hyr|boende|byggande|samhällsbygg|plan- och bygg|amortering|hemlös|stadsplan|allmännytt"),
    ("klimat", "Klimat och miljö",
     r"klimat|miljö|natur|biologisk|\bhav|östersjö|vatten|djur|kemikal|strandskydd|avfall|cirkulär|plast|"
     r"utsläpp|nollutsläpp|hållbar|förorening|allemansrätt|nationalpark"),
    ("landsbygd", "Landsbygd, jordbruk och skog",
     r"landsbygd|jordbruk|skog|jakt|fiske|livsmedel|\bmat\b|mat och|bonde|lantbruk|vilt|varg|rovdjur|åker|"
     r"gröna näring|riksintress|skarv|säl\b|glesbygd|betes|rennäring|frikommun|regional utveckl"),
    ("transport", "Infrastruktur och transporter",
     r"infrastruktur|transport|trafik|järnväg|\bväg|bilen|bilism|drivmedel|bensin|diesel|flyg|kollektivtrafik|"
     r"bredband|posten|tåg|cykel|sjöfart|hamnar|elbil|laddinfra"),
    ("utrikes", "EU och omvärlden",
     r"\beu\b|europa|utrikes|bistånd|ukraina|ryssland|israel|palestin|gaza|mellanöstern|mänskliga rättigheter|"
     r"frihandel|handelspolit|\bfn\b|förenta nationerna|kina|usa|folkrätt|nedrustning|vapenexport|norden|nordiskt"),
    ("demokrati", "Demokrati, jämställdhet och rättigheter",
     r"demokrati|jämställd|diskrimin|hbtq|rasism|antisemit|främlingsfient|yttrandefrihet|religion|minoritet|samer|"
     r"funktionsrätt|funktionsnedsätt|grundlag|kvinno|mäns våld|\bval\b|valsystem|integritet|offentlighet|"
     r"transperson|\bhbt|kvotering|demonstrationsfrihet|äganderätt|subsidiaritet|samhällsgemenskap|feminism|\bkön|trossamfund|islamism|extremism|monarki"),
    ("naringsliv", "Företag, digitalisering och teknik",
     r"företag|näringsliv|digital|\bai\b|artificiell|innovation|teknik|konkurrens|entreprenör|regelförenkl|"
     r"industri|besöksnäring|turism|export|upphandling|\bit\b|tech|startup"),
    ("kultur", "Kultur, medier och idrott",
     r"kultur|medie|media|idrott|public service|bibliotek|konst|film|musik|spel\b|föreningsliv|civilsamhälle|"
     r"folkrörelse|kulturarv|språk\b|svenska språket|press"),
]

# (område, rubrik, [frågor]); fråga: (id, förslag, {parti: (svar, citat)})
STANDPUNKTER = [
    ("rattsvasende", "Rättsväsendet", [
        ("barn_fangelse", "Sänkt straffbarhetsålder, så att barn under 15 år kan dömas för de grövsta brotten", {
            "KD": ("ja", "I och med det eskalerande problemet med mycket unga gärningsmän inom gängmiljön har regeringen beslutat att tillfällig sänka straffbarhetsåldern till 14 år."),
            "M": ("ja", "sänker straffbarhetsåldern till 14 år för de allra grövsta brotten, såsom mord och mordplaner"),
            "S": ("delvis", "Socialdemokraterna avvisar generella sänkningar av straffbarhetsåldern, men en tillfällig "
                            "sänkning vid allvarliga brott kan prövas och utvärderas."),
            "C": ("nej", "Nej till sänkt straffmyndighetsålder. Att låsa in 13- och 14-åringar i fängelse stoppar inte "
                         "rekryteringen till gängen."),
            "MP": ("nej", "Inte sätta barn i fängelse"),
        }),
        ("fler_poliser", "Fler poliser och mer lokal polisnärvaro", {
            "V": ("ja", "Vi vill stärka polisen, socialtjänsten, elevhälsan och fritidsverksamheten"),
            "M": ("ja", "Fortsätta öka antalet poliser"),
            "SD": ("ja", "Vi fortsätter att öka antalet poliser genom ökade resurser och mer attraktiv polisutbildning."),
            "C": ("ja", "Stärk polisens närvaro i de delar av landet där den idag är alldeles för svag."),
            "L": ("ja", "Vi vill se en statlig storsatsning på synliga poliser i hela Sverige som både förebygger och "
                        "ingriper mot brott"),
            "S": ("ja", "Det ska finnas poliser lokalt närvarande med rimliga inställelsetider i alla Sveriges kommuner."),
            "KD": ("ja", "En rättsstat måste tydligt agera mot brott med en närvarande och effektiv polismakt"),
            "MP": ("ja", "Stärka polisens lokala närvaro och förutsättningar att jobba förebyggande mot både "
                         "relationsvåld och ungdomskriminalitet"),
        }),
        ("utvisa_kriminella", "Utvisa fler kriminella som inte är svenska medborgare", {
            "SD": ("ja", "Illegala och kriminella invandrare ska utvisas."),
            "L": ("ja", "utvisa fler gängkriminella utan svenskt medborgarskap"),
            "KD": ("ja", "men som utvisar kriminella som inte hör hemma här"),
            "M": ("ja", "Införa automatisk utvisning av personer med utländskt medborgarskap som begår våld i nära "
                        "relation eller sexualbrott"),
            "C": ("ja", "Kriminella och de som saknar uppehållsrätt ska lämna Sverige snabbare"),
        }),
    ]),
    ("vard", "Vården", [
        ("stat_vard", "Staten tar över ansvaret för sjukvården från regionerna", {
            "SD": ("ja", "Sverigedemokraterna vill på sikt se ett statligt helhetsansvar för hälso- och sjukvården."),
            "V": ("delvis", "Det är statens ansvar att avsätta de resurser som krävs för att garantera en jämlik och jämställd sjukvård i hela landet"),
            "KD": ("ja", "Gör vården till ett nationellt ansvar och avveckla därefter dagens 21 olika regioner."),
            "L": ("delvis", "Men då behöver staten styra sjukvården mycket tydligare så att köerna kortas och sjukvården "
                            "blir mer jämlik i hela landet."),
        }),
        ("tandvard", "Billigare tandvård med högkostnadsskydd för fler", {
            "M": ("delvis", "Vi skjuter till stora medel samtidigt som vi gör en omprioritering från yngre, med mindre behov, till äldre med större behov."),
            "SD": ("ja", "det högkostnadsskydd som sedan årsskiftet gäller äldre ska omfatta alla medborgare"),
            "S": ("ja", "Socialdemokraterna går till val på billigare tandvård för alla vuxna"),
            "MP": ("ja", "tandvården ska finansieras enligt samma principer som annan hälso- och sjukvård"),
            "L": ("ja", "Vi vill stegvis göra förbättra tandvårdsförsäkringen så att kostnaderna blir rimligare"),
            "KD": ("delvis", "Patienter som är yngre än 67 år med stora tandvårdsbehov bör också omfattas av det nya "
                             "högkostnadsskyddet"),
            "C": ("delvis", "Tandvårdsstödet ska riktas mer till äldre, sjuka och personer med funktionsnedsättning."),
        }),
        ("vardgaranti", "Skärpt vårdgaranti för kortare väntetider", {
            "M": ("ja", "Skärpa vårdgarantin så att första besöket respektive operation eller annan behandling inom "
                        "specialistvården ges inom loppet av 30 dagar i stället för som i dag 90 dagar"),
            "KD": ("ja", "Vårdgarantin, som ger dig rätt till vård i rimlig tid, ska skärpas och efterlevas."),
            "S": ("ja", "Vi vill stärka tillgängligheten och vårdgarantin så att alla får den vård de behöver"),
        }),
    ]),
    ("skola", "Skolan", [
        ("vinst_skola", "Stoppa vinstuttag ur skolan", {
            "SD": ("nej", "Sverigedemokraterna anser därför att det avgörande inte är vem som äger skolan, utan hur den fungerar och vilka resultat den levererar."),
            "KD": ("nej", "Att förbjuda vinstdrivande företag skulle innebära att utbudet av alternativ minskade, vilket vore en inskränkning i medborgarens valmöjligheter."),
            "V": ("ja", "Privatiseringar och marknadsexperiment har dränerat skolan, vården och omsorgen."),
            "L": ("ja", "Därför vill vi fasa ut vinstintresset ur skolan."),
            "MP": ("ja", "Avskaffa marknadsskolan och stoppa vinsterna"),
            "S": ("ja", "Fristående huvudmän ska inte få flytta skolans resurser från kommunen eller ha lägre "
                        "lärartäthet i syfte att göra vinst."),
            "C": ("delvis", "Det ska inte gå en krona till vinst om välfärdsföretag inte håller kvaliteten och uppfyller "
                            "de krav som ställs."),
            "M": ("nej", "Slå vakt om föräldrars rätt att välja skola och se till att seriösa friskolor inte stängs av "
                         "politiska skäl"),
        }),
        ("statlig_skola", "Staten tar över huvudansvaret för skolan", {
            "MP": ("delvis", "Staten behöver ta ett större ansvar för likvärdigheten genom starkare finansiering och resurser efter behov."),
            "V": ("delvis", "Staten ska ta ett långsiktigt och ökat finansieringsansvar för hela välfärdssektorn."),
            "L": ("ja", "Därför vill vi att staten tar över ansvaret för skolan från kommunerna."),
            "S": ("delvis", "Staten ska därför ta ett ökat ansvar för skolans finansiering för att stärka skolans "
                            "kvalitet och likvärdighet"),
        }),
        ("skarmar", "Färre skärmar och fler böcker för de yngre eleverna", {
            "S": ("ja", "Böcker och utbildning ska få en tydligare plats i skolan och daglig läsning ska införas för de yngre barnen."),
            "M": ("ja", "Fasa ut skärmar i låg- och mellanstadiet"),
            "KD": ("ja", "utdelning av individuella bärbara datorer och ipads ska helt upphöra i låg- och mellanstadiet"),
            "L": ("ja", "I förskolan och lågstadiet ska läsplattor och personliga elevdatorer tas bort."),
        }),
    ]),
    ("ekonomi", "Jobb, skatter och ekonomi", [
        ("skatt_arbete", "Sänkt skatt på arbete", {
            "M": ("ja", "Sänka skatten för alla med låga och medelhöga inkomster"),
            "C": ("ja", "Sänk inkomstskatten särskilt för de med låga inkomster."),
            "L": ("ja", "Därför vill vi kraftigt sänka den statliga inkomstskatten på högre inkomster, med målet att "
                        "halvera den."),
            "KD": ("ja", "Pengar i plånboken är en del av välfärden – sänk skatten för landets hushåll."),
            "SD": ("ja", "Vi fortsätter att minska skattebördan för både människor och näringsliv."),
            "S": ("delvis", "Under nästa mandatperiod kommer Socialdemokraterna inte att höja skatten för folk med "
                            "vanliga löner"),
        }),
        ("skatt_rika", "Höjd skatt för de mest förmögna och på kapital", {
            "KD": ("nej", "Det var en godtycklig och omoralisk skatt som drev stora mängder kapital ut ur landet. Den ska inte återinföras i någon form."),
            "V": ("ja", "De med högst inkomst och stora förmögenheter behöver bidra med mer skatt till välfärden."),
            "S": ("ja", "De allra mest förmögna ska bidra mer."),
            "MP": ("ja", "Minska de ekonomiska klyftorna genom att beskatta de superrika och stärka välfärds- och "
                         "trygghetssystemen"),
            "M": ("nej", "Finansiera nya reformer utan att höja skattetrycket"),
        }),
        ("bidragskrav", "Hårdare krav för att få bidrag", {
            "V": ("nej", "När man kallar sjuka och arbetslösa för fuskare gör regeringen det lättare att motivera en politik som monterar ner och försvagar våra socialförsäkringar."),
            "M": ("ja", "Säkerställa att bidragstaket fullt ut träder i kraft"),
            "SD": ("ja", "Vi fortsätter att dra åt bidragskranen."),
            "S": ("ja", "För personer med försörjningsstöd vill vi se krav på aktivitetsplikt."),
            "L": ("ja", "Kvaliteten i SFI behöver höjas, och närvaro ska vara ett krav för att få bidrag."),
            "C": ("delvis", "Om man inte deltar i svenskundervisning, ställer sig till arbetsmarknadens förfogande, "
                            "eller ser till att ens barn kommer till skolan, ska det påverka nivån på bidrag och "
                            "ersättningar."),
        }),
    ]),
    ("energi", "Energi och klimat", [
        ("karnkraft", "Bygga ny kärnkraft", {
            "SD": ("ja", "På lång sikt görs det genom utbyggnad av kärnkraft."),
            "M": ("ja", "Se till att ny kärnkraft kommer på plats så snart som möjligt genom att finansiera upp till "
                        "5 000 MW"),
            "KD": ("ja", "Fullfölj byggandet av nya kärnkraftverk."),
            "L": ("ja", "Därför behöver vi mer kärnkraft som levererar stora mängder el dygnet runt, oavsett väder."),
            "S": ("ja", "Det förutsätter mer el från vatten, vind, sol, kärnkraft och bioenergi."),
            "C": ("delvis", "Vi vill ha en teknikneutral energiöverenskommelse som gör det enklare att bygga ny "
                            "elproduktion utan att förnybara energislag missgynnas."),
            "MP": ("nej", "Ny kärnkraft är inte lösningen"),
        }),
        ("vindkraft", "Bygga ut vindkraften", {
            "SD": ("nej", "De olika kraftslagen har olika fördelar och nackdelar vilket politiken måste erkänna och därför motsätter vi oss statliga stöd till vindkraft."),
            "V": ("ja", "Likaså finns det stora behov av en utbyggnad av förnybar elproduktion, elnät och lagring"),
            "MP": ("ja", "Investera i förnybar energi som sol och vind"),
            "C": ("ja", "Peka ut områden för havsbaserad vindkraft och auktionera ut rättigheterna att bygga vindparker "
                        "där."),
            "L": ("ja", "Samtidigt ska vi satsa på mer solkraft och vindkraft, som går snabbt att bygga ut, och "
                        "förenkla tillståndsprocessen för havsbaserad vindkraft."),
            "S": ("ja", "Kommunala beslut om vindkraft behöver fastslås tidigt i processen och det krävs lokala "
                        "incitament för ökad acceptans."),
            "M": ("delvis", "Att den som påverkas av vindkraft i närmiljön ska ha rätt till kompensation och inflytande "
                            "vid byggnation av nya anläggningar"),
            "KD": ("delvis", "Säkra att lokalsamhällen får del av den ekonomiska vinningen vid etablering av exempelvis "
                             "vindkraftsparker"),
        }),
        ("drivmedel", "Lägre priser på bensin och diesel (sänkt skatt, mindre reduktionsplikt)", {
            "S": ("delvis", "S vill se till att du har råd att köra till jobb och aktiviteter även när världsmarknadspriserna på bensin och diesel stiger."),
            "L": ("delvis", "Reduktionsplikten och systemet med utsläppsrätter ska därför utformas så att de inte driver upp drivmedelspriserna mer än nödvändigt."),
            "KD": ("ja", "Reduktionsplikt samt höga drivmedelsskatter på dem som inte har andra alternativ än bilen leder enbart till omfördelning av pengar från landsbygdsbor till staten"),
            "SD": ("ja", "Vi fortsätter att hålla nere bränslepriserna genom sänkt skatt och minskad reduktionsplikt."),
            "M": ("delvis", "Vi har sänkt skatten på drivmedel så att föräldrar har råd att åka till jobbet eller skjutsa "
                            "barnen till träningen. Vi är beredda att göra så igen ifall det krävs."),
            "MP": ("nej", "Bli kvitt beroendet av fossila bränslen genom att göra de hållbara alternativen billigare och "
                          "bättre och det fossila dyrare"),
        }),
    ]),
    ("integration", "Migration och integration", [
        ("stram_asyl", "Asylpolitik på EU:s miniminivå", {
            "MP": ("nej", "Värna asylrätten och ta emot minst 5 000 kvotflyktingar per år."),
            "KD": ("delvis", "Kristdemokraterna vill därför ha en fortsatt stram migrationspolitik med målsättningen att den ska ligga på nordiska nivåer."),
            "V": ("nej", "Vårt svar är en human politik som värnar asylrätten"),
            "SD": ("ja", "Asyllagstiftningen ska vara på EU:s miniminivå"),
            "M": ("ja", "Att asylinvandringen till Sverige ska vara restriktiv och den asylrelaterade migrationspolitiken "
                        "i enlighet med EU:s miniminivå"),
            "S": ("ja", "behöver Sverige under överskådlig tid ha en migrationspolitik i enlighet med EU:s miniminivåer"),
            "L": ("ja", "behöver Sverige och EU föra en stram asylpolitik"),
        }),
        ("stoppa_utvisningar", "Låta den som arbetar och sköter sig stanna (stoppa så kallade kompetensutvisningar)", {
            "KD": ("ja", "Det är angeläget att stoppa kompetensutvisningarna av utländsk arbetskraft."),
            "M": ("delvis", "De som arbetar kan ansöka om ett arbetstillstånd och regeringen tittar nu på möjligheten att före detta spårbytare som uppfyller lönekravet ska kunna ansöka om arbetstillstånd inifrån Sverige."),
            "V": ("ja", "Men Sverige blir inte tryggare av att människor som lever sina liv här rycks upp och utvisas."),
            "C": ("ja", "Den som arbetar, betalar skatt och bygger sitt liv i Sverige ska inte utvisas på grund av "
                        "orimliga regelmissar eller långsam byråkrati."),
            "MP": ("ja", "Stoppa orimliga utvisningar: Människor som byggt upp sina liv i Sverige ska få stanna."),
            "L": ("ja", "den som jobbar och sköter sig ska inte utvisas för bagateller"),
        }),
        ("medborgarskap", "Hårdare krav för svenskt medborgarskap", {
            "SD": ("ja", "Vi fortsätter höja kraven för svenskt medborgarskap."),
            "M": ("ja", "Införa hedersscreening för nyanlända och en värderingsscreening för att beviljas svenskt "
                        "medborgarskap"),
            "KD": ("ja", "Inför krav på godkända språk- och samhällsorienteringsprov som villkor för medborgarskap."),
            "L": ("ja", "Tack vare Liberalerna införs nu språktest och medborgarskapsprov"),
            "S": ("ja", "Språkkrav ska i huvudsak krävas för svenskt medborgarskap."),
        }),
    ]),
    ("forsvar", "Försvaret", [
        ("forsvarsanslag", "Höja försvarsanslagen mot Natos mål på 5 procent av BNP", {
            "M": ("ja", "vi ställer oss bakom det högre Nato-målet på minst 3,5 procent av BNP på militära utgifter, vilket Sverige ska nå redan 2030."),
            "L": ("ja", "Höjningen till 5 procent av BNP ska genomföras"),
            "C": ("ja", "Upprustningen måste fullföljas upp till fem procent av BNP"),
            "S": ("ja", "Det kommer kräva ökade försvarsanslag."),
            "SD": ("ja", "Upprustningen av Försvarsmakten är välbehövlig, men tar stora ekonomiska resurser i anspråk."),
        }),
        ("ukraina", "Fortsatt militärt och civilt stöd till Ukraina", {
            "KD": ("ja", "Detta innebär ett fortsatt omfattande militärt, ekonomiskt och humanitärt stöd i syfte att kunna hantera en oviss och osäker framtid."),
            "V": ("ja", "Vi har agerat för Ukrainas självklara rätt att försvara sig mot Rysslands anfallskrig"),
            "SD": ("ja", "Stödet till Ukraina och motståndet mot den ryska imperialismen är Sveriges viktigaste "
                         "utrikespolitiska fråga"),
            "M": ("ja", "Att stödet till Ukraina ska vara Sveriges viktigaste utrikespolitiska prioritering"),
            "L": ("ja", "Sverige och EU ska fortsätta trappa upp sitt bistånd till Ukraina med vapen och ekonomiskt "
                        "stöd ända till den siste ryske soldaten har lämnat."),
            "S": ("ja", "Särskilt viktigt är att vi står fast vid vårt militära och civila stöd till Ukraina så länge "
                        "det behövs"),
            "MP": ("ja", "Vi måste stötta Ukraina i kampen för frihet och demokrati"),
            "C": ("ja", "Sverige ska stå upp för Ukraina, för demokratin och för det europeiska samarbete som behövs "
                        "när världen blir farligare."),
        }),
        ("plikt", "Värnplikt eller civilplikt för fler", {
            "MP": ("ja", "civilplikten bör byggas ut som ett komplement till värnplikten"),
            "L": ("ja", "Försvaret av Sverige ska bygga på både frivillighet och plikt."),
            "KD": ("ja", "Allmän försvarsutbildning ska gälla alla unga – antingen militär utbildning eller "
                         "civilförsvarsutbildning."),
            "M": ("ja", "Fortsätta utveckla civilplikten inom fler områden så att den blir ett naturligt komplement "
                        "till värnplikten"),
            "S": ("ja", "bredda civilplikten till att gälla fler områden och personer än idag"),
            "C": ("ja", "Utöka civilplikten."),
        }),
    ]),
]
