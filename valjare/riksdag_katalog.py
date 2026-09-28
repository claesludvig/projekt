"""Koppling mellan riksdagens dokument, sakfrågorna och SOM-institutets förslag.

Klassningen är enkel och öppen: rubrikord i propositionens eller betänkandets
titel, och för betänkanden som inte träffas av något ord utskottet som
behandlat ärendet. Ett dokument kan höra till flera frågor. Klassningen kan
missa ärenden och ta med ärenden som bara berör frågan i förbigående, så den
ska läsas som en översikt, inte som en fullständig förteckning.
"""

# fråga -> reguljärt uttryck mot titeln (gemener)
ORD = {
    "lag": r"brott|straff|polis|kriminal|gäng|vapen|fängelse|åklagar|domstol|rättegång|visitation|"
           r"skjut|sprängämne|narkotika|terror|häkte|ungdomsbrott|brottsoffer|våldsbrott",
    "sjukvard": r"hälso- och sjukvård|sjukvård|patient|läkemedel|tandvård|psykiatri|vårdgaranti|vårdplats|"
                r"primärvård|smittskydd|hälsa",
    "aldre": r"äldre|hemtjänst|särskilt boende",
    "skola": r"skol|förskol|gymnasie|lärare|elev|högskol|betyg|vuxenutbildning|utbildning",
    "jobb": r"arbetsmarknad|arbetslös|anställningsskydd|arbetsförmedling|sysselsättning|a-kassa|"
            r"arbetslöshetsförsäkring|arbetsmiljö|arbetstid",
    "ekonomi": r"budgetproposition|ändringsbudget|vårproposition|finansplan|statens budget|riksbank|"
               r"finanspolitisk|budgetlag",
    "egen_ekonomi": r"elstöd|elpriskompensation|högkostnadsskydd|bostadsbidrag|barnbidrag|"
                    r"hushåll|konsument",
    "skatter": r"skatt|avdrag|mervärdesskatt|moms|tull",
    "invandring": r"migration|asyl|uppehållstillstånd|medborgarskap|utlänning|återvändande|utvisning|"
                  r"förvar|familjeåterförening|arbetskraftsinvandring|flykting|integration|etablering",
    "valfard": r"socialtjänst|försörjningsstöd|ekonomiskt bistånd|sjukförsäkring|föräldraförsäkring|"
               r"lss|funktionsnedsättning|socialförsäkring|aktivitetsersättning",
    "bostad": r"bostad|hyres|plan- och bygg|byggande|bostadsrätt|lantmäteri",
    "klimat": r"klimat|utsläpp|koldioxid|reduktionsplikt|växthusgas",
    "miljo": r"miljö|natur|vattenverksamhet|skog|biologisk mångfald|strandskydd|avfall|kemikal|jakt",
    "energi": r"energi|elförsörjning|kärnkraft|kärnteknik|elnät|elmarknad|vindkraft|elpris|effekt",
    "pension": r"pension|bostadstillägg",
    "jamstalldhet": r"jämställd|mäns våld mot kvinnor|våld i nära relation|diskriminering|hedersrelaterat",
    "forsvar": r"försvar|nato|militär|värnplikt|krigsmakt|säkerhetspolitik|beredskap",
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
     r"(?i)migration|asyl|uppehållstillstånd|medborgarskap|återvändande|utvisning|förvar|familjeåterförening|"
     r"arbetskraftsinvandring|utlänningslag"),
    ("sanka_skatt", "skatter", r"(?i)skatterna", r"(?i)^sänka skatterna", "Sänka skatterna",
     r"(?i)sänkt skatt|sänkt inkomstskatt|skattesänkning|sänkning av skatt|jobbskatteavdrag|skattereduktion"),
    ("hoja_skatt", "skatter", r"(?i)skatterna", r"(?i)^höja skatterna", "Höja skatterna",
     r"(?i)höjd skatt|höjning av skatt|skattehöjning|höjd energiskatt"),
    ("minska_forsvar", "forsvar", r"(?i)försvarsutgifterna", r"(?i)^bra förslag", "Minska försvarsutgifterna",
     r"(?i)totalförsvar|försvarsbeslut|nato|försvarsmakt|värnplikt|civilt försvar|militär"),
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
