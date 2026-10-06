"""Bostadsarkivet: vad som räknas som material om bostadsbyggandet.

Alla träffar räknas på normaliserad text (gemener, avstavningar vid
radbrytning ihopslagna, blanksteg hopslagna). Mönstren är reguljära uttryck
utan ordgräns i början, så att sammansättningar träffas
("hyresbostadsbyggandet", "småhusproduktionen").

KARNA: termer som nästan alltid handlar om att bygga bostäder eller om
villkoren för det. BRED: bostads- och plansektorn i stort. En text bedöms
som relevant enligt reglerna längst ned; poängen sparas för varje text så
att urvalet kan skärpas i efterhand utan omhämtning.
"""

KARNA = {
    "bostadsbyggande": r"bostadsbygg",
    "bostadsproduktion": r"bostadsproduktion|lägenhetsproduktion|småhusproduktion",
    "byggande av bostäder": r"byggande av (?:nya |fler |hyres|små|billiga |)(?:bostäder|lägenheter|hus)",
    "bygga bostäder": r"bygg(?:a|er|s|ts|des|t) (?:fler |nya |billiga |många |mer |)(?:bostäder|lägenheter|hyresrätter|hyresbostäder)",
    "bostadsförsörjning": r"bostadsförsörjning",
    "bostadsbrist": r"bostadsbrist|bostadsunderskott|brist på bostäder",
    "nyproduktion av bostäder": r"(?:nyproduktion|nybyggnation)(?:en)? av (?:nya |)(?:bostäder|lägenheter|hyresrätter|bostadsrätter|småhus)|bostadsnyproduktion|nybyggda (?:bostäder|lägenheter|hyresrätter)",
    "påbörjade/färdigställda bostäder": r"(?:påbörjade|färdigställda|igångsatta) (?:bostäder|lägenheter|småhus)",
    "bostadsinvesteringar": r"bostadsinvestering|investeringar i bostäder",
    "räntebidrag": r"räntebidrag|räntesubvention",
    "statliga bostadslån": r"bostadslån|statliga lån till bostäder|bostadskredit|bostadsfinansiering",
    "investeringsstöd till bostäder": r"investeringsstöd(?:et)? (?:till|för) (?:hyres|bostäder|bostads|små)|investeringsbidrag(?:et)? (?:till|för) (?:hyres|bostäder|bostads)",
    "byggkostnader": r"byggkostnad|produktionskostnader(?:na)? för bostäder",
    "byggsubventioner": r"bostadssubvention|byggsubvention|produktionsstöd",
}

BRED = {
    "bostadspolitik": r"bostadspolitik",
    "nyproduktion": r"nyproduktion|nybyggnation",
    "bostadsmarknad": r"bostadsmarknad",
    "bostadssektorn": r"bostadssektor|bostadsfråg|bostadsområde",
    "hyresrätt": r"hyresrätt|hyresbostäder|hyreslägenhet|hyreshus",
    "bostadsrätt/ägande": r"bostadsrätt|egnahem|äganderätt till bostad",
    "flerbostadshus/småhus": r"flerbostadshus|småhus",
    "allmännyttan": r"allmännytt|bostadsbolag|bostadsföretag",
    "plan- och bygglagen": r"plan- och bygglag|\bpbl\b|bygglov|detaljplan|översiktsplan|planprocess|planmonopol",
    "mark": r"markanvisning|markpris|byggbar mark|markpolitik",
    "byggsektorn": r"byggsektor|byggbransch|byggindustri|byggföretag|byggherr|byggmaterial",
    "byggregler": r"byggregl|byggnorm|boverkets byggregler|tillgänglighetskrav",
    "hyressättning": r"bruksvärde|presumtionshyr|hyressättning|hyresreglering|marknadshyr",
    "bostadsbidrag/boendekostnad": r"bostadsbidrag|bostadstillägg|bostadskostnad|boendekostnad",
    "studentbostäder": r"studentbostäder|ungdomsbostäder|seniorbostäder|trygghetsboende",
    "trångboddhet": r"trångbodd|hemlöshet|bostadslös",
    "boverket": r"boverket|bostadsstyrelsen|statens bostadskreditnämnd|bostadsdepartement|bostadsminister|bostadsutskott",
}

# Frågor till riksdagens sökmotor (data.riksdagen.se) för att hitta kandidater
# bland SOU, Ds och kommittédirektiv. Protokollen hämtas alla, utan sökning.
# Sökmotorn böjer orden själv (bostadsbyggande = bostadsbyggandet).
SOKFRAGOR = [
    "bostadsbyggande",
    "bostadsproduktion",
    "bostadsförsörjning",
    "bostadsbrist",
    "nyproduktion bostäder",
    "byggkostnader",
    "räntebidrag",
    "investeringsstöd hyresbostäder",
    "bostadspolitik",
    "bostadsmarknaden",
    "plan- och bygglagen",
    "allmännyttiga bostadsföretag",
]

# Dokumenttyper som hämtas från riksdagen och vad de heter.
DOKTYPER = {
    "prot": "Riksdagens protokoll",
    "sou": "Statens offentliga utredningar",
    "ds": "Departementsserien",
    "dir": "Kommittédirektiv",
}

FRAN_AR = 1990

# --- Urvalsregler ------------------------------------------------------------
# Ett anförande är relevant om det har minst en kärnträff, eller minst tre
# breda träffar i två olika kategorier, eller om ärendets rubrik (t.ex.
# "3 § Svar på interpellation om bostadsbyggandet") träffar någon term; då tas
# hela debatten med.
ANF_MIN_KARNA = 1
ANF_MIN_BRED = 3
ANF_MIN_BRED_KATEGORIER = 2

# Ett dokument (SOU, Ds, direktiv) är relevant om titeln träffar någon term,
# eller om det har minst DOK_MIN_KARNA kärnträffar, eller minst två
# kärnträffar som är minst DOK_MIN_TATHET per 10 000 ord (fångar korta texter).
DOK_MIN_KARNA = 5
DOK_MIN_TATHET = 3.0

# Relevansgrad för sorteringen: kärnträffar per 10 000 ord.
GRAD_HOG = 15.0
GRAD_MEDEL = 3.0
