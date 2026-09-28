"""Bred indikatorkatalog: nyckeltal ur Koladas hela katalog, valda med mönster mot titeln.

Kolada samlar statistik från bland annat Försäkringskassan, Socialstyrelsen, Skolverket,
Arbetsförmedlingen, Brå, SCB och SKR per kommun, region och riket. I stället för att gissa
nyckeltalens id hämtas hela katalogen (data/katalog/kolada_alla_kpi.csv) och varje post nedan väljer
det nyckeltal vars titel matchar mönstret. Finns flera träffar väljs det som redovisas för både
kommuner och riket och har kortast titel (oftast totalen, inte en undergrupp).

(fråga, kort namn, regex mot titeln eller "id:<nyckeltal>", regex att utesluta eller None)

Mönster som gav fel eller ingen träff (se data/katalog/kolada_bred_val.csv) är ersatta med exakta id
ur katalogen; namnet beskriver då vad nyckeltalet faktiskt mäter.
"""

KOLADA_BRED = [
    # Socialförsäkringen (Försäkringskassan)
    ("valfard", "Sjukpenningtal (dagar per försäkrad)", r"(?i)^sjukpenningtal", r"(?i)kvinnor|män|\d\d-\d\d år"),
    ("valfard", "Ohälsotal (dagar per försäkrad)", r"(?i)^ohälsotal", r"(?i)kvinnor|män"),
    ("valfard", "Barn 0–19 år med förälder med sjuk- eller aktivitetsersättning (%)", "id:N02903", None),
    ("valfard", "Vuxna med långvarigt ekonomiskt bistånd (% av befolkningen)", "id:N31816", None),
    ("valfard", "Barn och unga 0–19 år med låg ekonomisk standard (%)", "id:N66077", None),
    ("valfard", "Barn i familjer med ekonomiskt bistånd (%)", r"(?i)^barn.*ekonomiskt bistånd.*andel", None),
    ("valfard", "Barn och unga 0–20 år placerade i HVB eller familjehem (per 1 000)", "id:N33818", None),
    ("valfard", "Invånare 0–22 år med insatser enligt LSS (per 10 000)", "id:N28891", None),
    # Jobb och etablering (Arbetsförmedlingen, SCB)
    ("jobb", "Unga 16–24 år som varken arbetar eller studerar (%)", "id:N02797", None),
    ("jobb", "Sysselsättningsgrad 20–64 år (%)", "id:N02267", None),
    ("jobb", "Öppet arbetslösa 18–24 år, av befolkningen (%)", "id:N03939", None),
    ("invandring", "Nyanlända i arbete eller studier 90 dagar efter etableringsuppdraget (%)", "id:N00973", None),
    ("invandring", "Förvärvsarbetande flyktingar och anhöriga 20–64 år (%)", "id:N00700", None),
    ("invandring", "Sysselsättningsgrad 20–64 år, utrikes födda (%)", "id:N02268", None),
    ("invandring", "Sysselsättningsgrad 20–64 år, inrikes födda (%)", "id:N02269", None),
    # Skola (Skolverket)
    ("skola", "Elever i åk 9 som uppnått betygskriterierna i alla ämnen (%)", "id:N15508", None),
    ("skola", "Lärare med pedagogisk högskoleexamen, grundskola (%)",
     r"(?i)lärare.*pedagogisk högskoleexamen.*grundskol", None),
    ("skola", "Elever i åk 6, betygspoäng i matematik (genomsnitt)", "id:N15509", None),
    ("skola", "Kostnad grundskola F–9 per elev (kr)", "id:N15027", None),
    ("skola", "Barn 1–5 år inskrivna i förskola (%)", "id:N11800", None),
    # Vård och folkhälsa (Socialstyrelsen, SKR)
    ("sjukvard", "Rimlig väntetid till sjukhusvård, enligt invånarna (%)", "id:U70448", None),
    ("sjukvard", "Återinskrivning inom 30 dagar, 65+ (%)", r"(?i)återinskriv", None),
    ("sjukvard", "Förtroende för hälso- och sjukvården (%)", r"(?i)förtroende för (hälso- och )?sjukvården", None),
    ("sjukvard", "Självmord 25 år+, femårsmedelvärde (per 100 000 inv)", "id:N61603", None),
    ("sjukvard", "Invånare med bra självskattat hälsotillstånd (%)", "id:U01405", None),
    ("sjukvard", "Nettokostnad hälso- och sjukvård (kr/inv)", r"(?i)nettokostnad hälso- och sjukvård.*kr/inv", None),
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
    ("lag", "Otrygga vid utevistelse sen kväll i eget område, NTU (%)", "id:N07609", None),
    # Bostad (Boverket, SCB)
    ("bostad", "Bostadsmarknadsläget enligt kommunen (0=underskott, 1=balans, 2=överskott)", "id:U30446", None),
    ("bostad", "Trångbodda i flerbostadshus, norm 2 (%)", "id:N07907", None),
    # Kommunernas och regionernas ekonomi
    ("ekonomi", "Kommunens resultat före extraordinära poster (kr/inv)", "id:N03107", None),
    ("ekonomi", "Soliditet inkl. pensionsförpliktelser (%)", r"(?i)soliditet.*inkl.*pension", None),
    ("ekonomi", "Kommunalekonomisk utjämning (kr/inv)", "id:N00005", None),
    # Klimat, miljö, energi
    ("klimat", "Elbilar, andel av personbilarna i trafik (%)", "id:N07945", None),
        ("miljo", "Insamlat mat- och restavfall (kg/inv)", "id:U07482", None),
    ("miljo", "Insamlat matavfall (%)", r"(?i)matavfall", None),
    ("energi", "Slutanvändning av el (MWh/inv)", "id:N45906", None),
    # Demokrati och jämställdhet
    ("demokrati", "Valdeltagande i minst ett av de allmänna valen (%)", "id:N05400", None),
    ("jamstalldhet", "Kvinnor i kommunfullmäktige (%)", r"(?i)kvinnor .*kommunfullmäktige|andel kvinnor.*fullmäktige", None),
    # Pension och äldres ekonomi (garantipension och bostadstillägg finns inte i Kolada)
]
