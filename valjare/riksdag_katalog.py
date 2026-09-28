"""Koppling mellan riksdagens dokument, sakfrågorna och SOM-institutets förslag.

Klassningen är enkel och öppen: rubrikord i propositionens eller betänkandets
titel, och för betänkanden som inte träffas av något ord utskottet som
behandlat ärendet. Ett dokument kan höra till flera frågor. Klassningen kan
missa ärenden och ta med ärenden som bara berör frågan i förbigående, så den
ska läsas som en översikt, inte som en fullständig förteckning.

Träffsäkerheten är mätt mot handkodade urval (granskning/klassning_facit*.csv): se
KLASSNING nedan och granskning/KLASSNING.md.
"""

# fråga -> reguljärt uttryck mot titeln (gemener)
ORD = {
    "lag": r"brott|straff|polis|kriminal|gäng|vapen|fängelse|åklagar|domstol|rättegång|rättsprocess|lagföring|"
           r"visitation|husrannsakan|beslag|tvångsmedel|dataavläsning|frivård|kriminalvård|anstalt|explosiv|"
           r"skjut|sprängämne|narkotika|terror|häkte|ungdomsbrott|brottsoffer|våldsbrott|penningtvätt|"
           r"våld i nära relation|insatsgrupp",
    "sjukvard": r"hälso- och sjukvård|sjukvård|patient|läkemedel|tandvård|psykiatri|vårdgaranti|vårdplats|"
                r"primärvård|smittskydd|hälsa|biobank|medicinteknisk|vaccin|apotek",
    "aldre": r"äldreomsorg|äldreboende|äldre personer|hemtjänst|särskilt boende",
    "skola": r"skol|förskol|gymnasie|lärare|elev|högskol|betyg|undervisning|studiestöd|"
             r"utbildning och universitets|universitets",
    "jobb": r"arbetsmarknad|arbetslös|anställningsskydd|arbetsförmedling|sysselsättning|a-kassa|"
            r"arbetslöshetsförsäkring|arbetsmiljö|arbetstid|korttidsarbete|arbetsgivaravgift|arbetsliv|"
            r"arbete ombord|coronaviruset",
    "ekonomi": r"^budgetpropositionen för \d{4}$|vårändringsbudget|höständringsbudget|vårproposition|finansplan|"
               r"statens budget|riksbank|finanspolitisk|budgetlag|samhällsekonomi|statsskuld|coronaviruset|"
               r"eu:s egna medel",
    "egen_ekonomi": r"elstöd|elpriskompensation|högkostnadsskydd|bostadsbidrag|barnbidrag|stöd till hushåll|"
                    r"sänkt skatt på (?:bensin|diesel|drivmedel)|skatt på drivmedel|reduktionsplikt",
    "skatter": r"skatt|avdrag|mervärdesskatt|moms|arbetsgivaravgift|arbetsgivardeklaration|fåmansföretag|"
               r"betaltjänstleverantör",
    "invandring": r"migration|asyl|uppehållstillstånd|medborgarskap|utlänning|återvändande|utvisning|"
                  r"(?<!slut)förvar|familjeåterförening|anhöriginvandring|arbetskraftsinvandring|flykting|"
                  r"integration|etablering|invandr|identitetshandling|kvalificering till socialförsäkring",
    "valfard": r"socialtjänst|försörjningsstöd|ekonomiskt bistånd|sjukförsäkring|föräldraförsäkring|"
               r"\blss\b|funktionsnedsättning|socialförsäkring|aktivitetsersättning|sjukersättning|efterlevande|"
               r"sociala området",
    "bostad": r"bostad|hyres|plan- och bygg|\bbyggande|bygglov|bostadsrätt|lantmäteri",
    "klimat": r"klimat|utsläpp|koldioxid|reduktionsplikt|växthusgas|bonus-malus|förnybartdirektiv|hållbara bränslen",
    "miljo": r"miljö(?!styrning i bonus)|natur|vattenverksamhet|skog|biologisk mångfald|strandskydd|kemikal|"
             r"jakt|vilt\b|ekologisk produktion|artskydd",
    "energi": r"energi|elförsörjning|kärnkraft|kärntekni|elnät|el- och gasnät|gasnät|gaslagring|elmarknad|"
              r"vindkraft|elpris|effektbrist|effektreserv|kapacitetsmekanism|förnybar|extraordinära vinster|"
              r"hållbara bränslen",
    "pension": r"pension(?!at)|bostadstillägg|ålderdom",
    "jamstalldhet": r"jämställd|mäns våld mot kvinnor|våld i nära relation|diskriminering|hedersrelater",
    "forsvar": r"försvar|nato|militär|värnplikt|krigsmakt|säkerhetspolitik|höjd beredskap|civilt försvar|"
               r"cybersäkerhet|säkerhetsintressen|signalspaning|stabiliseringsinsats",
}

# Budgetpropositionens utgiftsområden -> sakfråga (ersätter rubrikorden för dessa dokument)
UTGIFTSOMRADE = {
    2: ["ekonomi"], 3: ["skatter"], 4: ["lag"], 6: ["forsvar"], 8: ["invandring"], 9: ["sjukvard"],
    10: ["valfard"], 11: ["pension"], 12: ["valfard"], 13: ["jamstalldhet", "invandring"], 14: ["jobb"],
    15: ["skola"], 16: ["skola"], 18: ["bostad"], 20: ["klimat", "miljo"], 21: ["energi"], 26: ["ekonomi"],
}

# Utskott -> fråga, för betänkanden som inga rubrikord träffar
UTSKOTT = {
    "JuU": "lag", "FöU": "forsvar", "SoU": "sjukvard", "UbU": "skola", "AU": "jobb", "FiU": "ekonomi",
    "SkU": "skatter", "CU": "bostad", "NU": "energi", "MJU": "miljo", "SfU": "valfard",
}

# SOM-förslag som ställs mot riksdagens beslut.
# (id, fråga, rubrik (regex), serie (regex), kort namn, regex mot propositionernas titel)
# Serien är andelen "bra förslag" (eller "satsa mer"), utom där serien själv är förslaget.
OPINION = [
    ("farre_flyktingar", "invandring", r"(?i)färre flyktingar", r"(?i)^bra förslag", "Ta emot färre flyktingar",
     r"(?i)migration|asyl|uppehållstillstånd|medborgarskap|återvändande|utvisning|(?<!slut)förvar|familjeåterförening|"
     r"arbetskraftsinvandring|utlänningslag"),
    ("sanka_skatt", "skatter", r"(?i)skatterna", r"(?i)^sänka skatterna", "Sänka skatterna",
     r"(?i)sänkt skatt|sänkt inkomstskatt|skattesänkning|sänkning av skatt|jobbskatteavdrag|skattereduktion"),
    ("hoja_skatt", "skatter", r"(?i)skatterna", r"(?i)^höja skatterna", "Höja skatterna",
     r"(?i)höjd skatt|höjning av skatt|skattehöjning|höjd energiskatt"),
    ("minska_forsvar", "forsvar", r"(?i)försvarsutgifterna", r"(?i)^bra förslag", "Minska försvarsutgifterna",
     r"(?i)totalförsvaret \d{4}|försvarsbeslut|utgiftsområde 6|medlemskap i nato|natomedlemskap|"
     r"anslutning till nordatlantiska|försvarsanslag|ändringsbudget.*rikets militära försvar"),
    ("minska_bistand", "ekonomi", r"(?i)biståndet", r"(?i)^bra förslag", "Minska biståndet",
     r"(?i)bistånd|utvecklingssamarbete"),
    ("minska_offentlig", "ekonomi", r"(?i)offentliga sektorn", r"(?i)^bra förslag", "Minska den offentliga sektorn",
     None),
    ("sex_timmar", "jobb", r"(?i)sex timmars", r"(?i)^bra förslag", "Införa sex timmars arbetsdag",
     r"(?i)arbetstid"),
    ("vinstforbud", "skola", r"(?i)privatisering", r"(?i)^vinstutdelning ska inte",
     "Vinstutdelning ska inte tillåtas i skattefinansierad vård, skola och omsorg",
     r"(?i)fristående skol|friskol|skolpeng|enskilda huvudmän|vinst"),
    ("koldioxidskatt", "klimat", r"(?i)miljö och jämställdhet", r"(?i)koldioxidskatt", "Höja koldioxidskatten på bensin",
     r"(?i)koldioxidskatt|energiskatt på bensin|skatt på bensin|skatt på diesel|drivmedel|reduktionsplikt"),
    ("karnkraft", "energi", r"(?i)energikällor", r"(?i)^kärnkraft", "Satsa mer på kärnkraft",
     r"(?i)kärnkraft|kärnteknik"),
    ("vindkraft", "energi", r"(?i)energikällor", r"(?i)^vindkraft", "Satsa mer på vindkraft",
     r"(?i)vindkraft|havsbaserad"),
    ("glesbygd", "valfard", r"(?i)miljö och jämställdhet", r"(?i)glesbygd", "Öka det ekonomiska stödet till glesbygden",
     r"(?i)landsbygd|glesbygd"),
    ("statlig_sjukvard", "sjukvard", r"(?i)förstatligande", r"(?i)sjukvården", "Låta staten överta ansvaret för sjukvården",
     r"(?i)statligt huvudmannaskap|förstatligande|huvudmannaskap för hälso"),
    ("statlig_skola", "skola", r"(?i)förstatligande", r"(?i)skolan", "Låta staten överta ansvaret för skolan",
     r"(?i)statligt huvudmannaskap|förstatligande|huvudmannaskap för skola"),
]

# Förtroende (SOM) som visas bredvid riksdagens beslut
FORTROENDE = r"(?i)^(?:riksdagen|regeringen|de politiska partierna|kommunstyrelserna)$"

# Träffsäkerhet mot ett orört, handkodat urval av 100 propositioner 2018/19–2025/26
# (granskning/klassning_facit_test.csv), mätt innan reglerna rättades efter det urvalet.
KLASSNING = {"urval": 100, "precision": 0.84, "tackning": 0.83, "f1": 0.83, "exakt": 0.77,
             "fore": {"precision": 0.76, "tackning": 0.67, "f1": 0.71, "exakt": 0.65}}
