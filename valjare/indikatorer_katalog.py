"""Bred indikatorkatalog: nyckeltal ur Koladas hela katalog, valda med mönster mot titeln.

Kolada samlar statistik från bland annat Försäkringskassan, Socialstyrelsen, Skolverket,
Arbetsförmedlingen, Brå, SCB och SKR per kommun, region och riket. I stället för att gissa
nyckeltalens id hämtas hela katalogen (data/katalog/kolada_alla_kpi.csv) och varje post nedan väljer
det nyckeltal vars titel matchar mönstret. Finns flera träffar väljs det som redovisas för både
kommuner och riket och har kortast titel (oftast totalen, inte en undergrupp).

(fråga, kort namn, regex mot titeln, regex att utesluta eller None)
"""

KOLADA_BRED = [
    # Socialförsäkringen (Försäkringskassan)
    ("valfard", "Sjukpenningtal (dagar per försäkrad)", r"(?i)^sjukpenningtal", r"(?i)kvinnor|män|\d\d-\d\d år"),
    ("valfard", "Ohälsotal (dagar per försäkrad)", r"(?i)^ohälsotal", r"(?i)kvinnor|män"),
    ("valfard", "Sjuk- och aktivitetsersättning (% av befolkningen)", r"(?i)sjuk- och aktivitetsersättning.*andel",
     r"(?i)kvinnor|män"),
    ("valfard", "Långvarigt ekonomiskt bistånd (% av befolkningen)", r"(?i)långvarigt ekonomiskt bistånd.*andel", None),
    ("valfard", "Barn i ekonomiskt utsatta hushåll (%)", r"(?i)^barn .*ekonomiskt utsatta hushåll", None),
    ("valfard", "Barn i familjer med ekonomiskt bistånd (%)", r"(?i)^barn.*ekonomiskt bistånd.*andel", None),
    ("valfard", "Placerade barn och unga 0–20 år (per 10 000)", r"(?i)placerade barn", None),
    ("valfard", "Personer med insatser enligt LSS (per 1 000 inv)", r"(?i)insatser enligt lss.*inv", None),
    # Jobb och etablering (Arbetsförmedlingen, SCB)
    ("jobb", "Unga 20–24 år som varken arbetar eller studerar (%)", r"(?i)varken arbetar eller studerar", None),
    ("jobb", "Förvärvsarbetande 20–64 år (%)", r"(?i)^förvärvsarbetande invånare 20-64 år", r"(?i)kvinnor|män|utrikes|inrikes"),
    ("jobb", "Öppet arbetslösa och i program 18–24 år (%)", r"(?i)öppet arbetslösa.*18-24 år", None),
    ("invandring", "Nyanlända i arbete eller studier efter etableringsprogrammet (%)",
     r"(?i)(nyanlända|deltagare).*etablering.*(arbete eller studier)", None),
    ("invandring", "Förvärvsarbetande utrikes födda 20–64 år (%)", r"(?i)^förvärvsarbetande.*utrikes födda", r"(?i)kvinnor|män"),
    ("invandring", "Elever i åk 9 med utländsk bakgrund behöriga till gymnasiet (%)",
     r"(?i)elever i åk\.? ?9.*utländsk bakgrund.*behöriga", None),
    # Skola (Skolverket)
    ("skola", "Elever i åk 9 som uppnått kunskapskraven i alla ämnen (%)",
     r"(?i)elever i åk\.? ?9.*(kunskapskraven|betyg) i alla ämnen", r"(?i)kvinnor|män|flickor|pojkar"),
    ("skola", "Lärare med pedagogisk högskoleexamen, grundskola (%)",
     r"(?i)lärare.*pedagogisk högskoleexamen.*grundskol", None),
    ("skola", "Elever i åk 6 med godkänt nationellt prov i matematik (%)", r"(?i)åk\.? ?6.*matematik", None),
    ("skola", "Behöriga till gymnasiet, elever i åk 9 (%)", r"(?i)behöriga till .*gymnasie.*hemkommun",
     r"(?i)yrkesprogram|kvinnor|män|flickor|pojkar"),
    ("skola", "Kostnad grundskola per elev (kr)", r"(?i)^kostnad grundskola.*per elev", None),
    ("skola", "Barn 1–5 år inskrivna i förskola (%)", r"(?i)inskrivna barn.*förskola.*andel", None),
    # Vård och folkhälsa (Socialstyrelsen, SKR)
    ("sjukvard", "Undvikbar slutenvård (per 100 000 inv)", r"(?i)undvikbar slutenvård", None),
    ("sjukvard", "Återinskrivning inom 30 dagar, 65+ (%)", r"(?i)återinskriv", None),
    ("sjukvard", "Förtroende för hälso- och sjukvården (%)", r"(?i)förtroende för (hälso- och )?sjukvården", None),
    ("sjukvard", "Självmord (per 100 000 inv)", r"(?i)^självmord|suicid", None),
    ("sjukvard", "Invånare med bra självskattad hälsa (%)", r"(?i)självskattad.*hälsa", None),
    ("sjukvard", "Nettokostnad hälso- och sjukvård (kr/inv)", r"(?i)nettokostnad hälso- och sjukvård.*kr/inv", None),
    ("sjukvard", "Väntetid till besök i specialiserad psykiatri (%)", r"(?i)psykiatri.*inom.*dagar", r"(?i)barn"),
    # Äldreomsorg
    ("aldre", "Personalkontinuitet i hemtjänsten (antal personal på 14 dagar)",
     r"(?i)antal (olika )?personal.*hemtjänsttagare.*14 dagar", None),
    ("aldre", "Nöjdhet med hemtjänsten, helhetssyn (%)", r"(?i)brukarbedömning hemtjänst äldreomsorg.*helhetssyn", None),
    ("aldre", "Kostnad äldreomsorg per invånare 80+ (kr)", r"(?i)kostnad.*äldreomsorg.*80\+", None),
    ("aldre", "Invånare 80+ i särskilt boende (%)", r"(?i)invånare 80\+ i särskilt boende", None),
    # Lag och ordning, trygghet (Brå, Polisen)
    ("lag", "Anmälda narkotikabrott (per 100 000 inv)", r"(?i)anmälda narkotikabrott", None),
    ("lag", "Anmälda skadegörelsebrott (per 100 000 inv)", r"(?i)anmälda .*skadegörelse", None),
    ("lag", "Anmälda bostadsinbrott (per 100 000 inv)", r"(?i)anmälda .*(inbrott|bostadsinbrott)", None),
    ("lag", "Invånare som känner sig trygga (%)", r"(?i)(känner sig|upplever).*trygg", None),
    # Bostad (Boverket, SCB)
    ("bostad", "Kommunen bedömer att det råder bostadsbrist (ja=1)", r"(?i)bostadsbrist", None),
    ("bostad", "Trångbodda (%)", r"(?i)trångbo", None),
    ("bostad", "Påbörjade bostäder (per 1 000 inv)", r"(?i)påbörjade (lägenheter|bostäder)", None),
    # Kommunernas och regionernas ekonomi
    ("ekonomi", "Kommunens resultat (% av skatt och bidrag)", r"(?i)^resultat före (extraordinära|balanskravs)", None),
    ("ekonomi", "Soliditet inkl. pensionsförpliktelser (%)", r"(?i)soliditet.*inkl.*pension", None),
    ("ekonomi", "Kommunalekonomisk utjämning (kr/inv)", r"(?i)kommunalekonomisk utjämning.*kr/inv", None),
    # Klimat, miljö, energi
    ("klimat", "Elbilar och laddhybrider, andel av nyregistrerade (%)", r"(?i)(elbil|laddbar|miljöbil).*nyregistrerade", None),
    ("klimat", "Andel förnybara drivmedel i kommunens fordon (%)", r"(?i)förnybara drivmedel", None),
    ("miljo", "Hushållsavfall (kg/inv)", r"(?i)hushållsavfall.*kg/inv", None),
    ("miljo", "Insamlat matavfall (%)", r"(?i)matavfall", None),
    ("energi", "Elanvändning per invånare (MWh)", r"(?i)elanvändning.*inv", None),
    # Demokrati och jämställdhet
    ("demokrati", "Valdeltagande i kommunval (%)", r"(?i)valdeltagande.*(kommunval|kommunfullmäktige)", None),
    ("jamstalldhet", "Kvinnor i kommunfullmäktige (%)", r"(?i)kvinnor .*kommunfullmäktige|andel kvinnor.*fullmäktige", None),
    ("jamstalldhet", "Sjukpenningtal, skillnad kvinnor och män", r"(?i)sjukpenningtal.*kvinnor", None),
    # Pension och äldres ekonomi
    ("pension", "Invånare 65+ med garantipension/bostadstillägg (%)", r"(?i)(garantipension|bostadstillägg)", None),
]
