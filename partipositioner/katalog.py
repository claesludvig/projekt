"""Partier, källor och bostadspolitiska frågor för partipositionsdatabasen."""
import re

# Riksdagspartier med föregångare. Koden är SND Vivills, "kod" är dagens förkortning.
PARTIER = {
    "s":   {"kod": "S",  "namn": "Socialdemokraterna", "vivill": ["s"]},
    "m":   {"kod": "M",  "namn": "Moderaterna", "vivill": ["m"]},          # Högerpartiet före 1969
    "c":   {"kod": "C",  "namn": "Centerpartiet", "vivill": ["c"]},        # Bondeförbundet före 1957
    "l":   {"kod": "L",  "namn": "Liberalerna", "vivill": ["fp", "l"]},    # Folkpartiet före 2015
    "kd":  {"kod": "KD", "namn": "Kristdemokraterna", "vivill": ["kd"]},
    "v":   {"kod": "V",  "namn": "Vänsterpartiet", "vivill": ["v"]},
    "mp":  {"kod": "MP", "namn": "Miljöpartiet", "vivill": ["mp"]},
    "sd":  {"kod": "SD", "namn": "Sverigedemokraterna", "vivill": ["sd"]},
    "nyd": {"kod": "NyD", "namn": "Ny demokrati", "vivill": ["nd"]},
    "all": {"kod": "Alliansen", "namn": "Alliansen (M, C, FP/L, KD)", "vivill": ["all"]},
    "rg":  {"kod": "Rödgröna", "namn": "De rödgröna (S, V, MP)", "vivill": ["rg"]},
}

# Namn och förkortningar i löptext (medier, överenskommelser)
PARTI_RX = {
    "s":  r"\bsocialdemokrat\w*|\(s\)|\bS-|\bS:s\b",
    "m":  r"\bmoderat\w*|\(m\)|\bM:s\b",
    "c":  r"\bcenterpartiet\w*|\bcenterpartist\w*|\(c\)|\bC:s\b",
    "l":  r"\bliberalerna\w*|\bfolkpartiet\w*|\(l\)|\(fp\)|\bL:s\b",
    "kd": r"\bkristdemokrat\w*|\(kd\)|\bKD:s\b",
    "v":  r"\bvänsterpartiet\w*|\(v\)|\bV:s\b",
    "mp": r"\bmiljöpartiet\w*|\(mp\)|\bMP:s\b",
    "sd": r"\bsverigedemokrat\w*|\(sd\)|\bSD:s\b",
}

# Bostadspolitiska sakfrågor. Varje fråga får sina stycken ur varje dokument, så att partiernas
# formuleringar kan läggas bredvid varandra år för år.
FRAGOR = {
    "hyra":    ("Hyressättning och marknadshyror", r"marknadshyr|bruksvärde|presumtionshyr|hyressättning|hyresreglering|fri hyressättning|hyresförhandling|hyreskontroll"),
    "allm":    ("Allmännyttan och utförsäljningar", r"allmännytt|kommunala bostadsbolag|kommunala bostadsföretag|utförsälj|ombildning"),
    "stod":    ("Statligt stöd till byggande", r"investeringsstöd|investeringsbidrag|räntebidrag|byggsubvention|statliga lån|statligt stöd till (bostads|hyres)|räntegaranti|kreditgaranti|byggbonus|bostadsbyggnadsstöd"),
    "skatt":   ("Bostadsbeskattning", r"fastighetsskatt|fastighetsavgift|ränteavdrag|flyttskatt|reavinstskatt|uppskov|schablonintäkt|kommunal fastighetsavgift|bostadsmoms"),
    "kredit":  ("Bolån, amortering och kreditregler", r"amorteringskrav|bolånetak|skuldkvot|kreditrestriktion|bolån|startlån|bosparande|ungdomssparande|kontantinsats"),
    "plan":    ("Planering, mark och byggregler", r"detaljplan|planmonopol|plan- och bygglag|byggregler|strandskydd|överklagande|markanvisning|bygglov|riksintresse|kommunala särkrav"),
    "bidrag":  ("Bostadsbidrag och sociala bostäder", r"bostadsbidrag|bostadstillägg|sociala bostäder|social bostadspolitik|hemlös|bostadsgaranti|bostadsförsörjning"),
    "bygg":    ("Bostadsbyggandets omfattning", r"bostadsbyggande|bygga (fler|mer|\d)|nya bostäder|bostadsbrist|byggtakt|miljonprogram|bostäder per år|nyproduktion"),
    "ren":     ("Renovering och upprustning", r"renovering|upprustning|ROT-avdrag|ROT|energieffektiviser|miljonprogramsområden|renoveringsstöd"),
    "agande":  ("Ägande och upplåtelseformer", r"äganderätt|ägarlägenhet|bostadsrätt|hyresrätt|egnahem|småhus|kooperativ hyresrätt|upplåtelseform"),
    "segr":    ("Segregation och utsatta områden", r"segregation|utsatta områden|socioekonomiskt|blandade upplåtelseformer|trångbodd|andrahandsuthyrning|svarthandel med kontrakt"),
}
FRAGA_RX = {k: re.compile(rx, re.I) for k, (_, rx) in FRAGOR.items()}
BOSTAD_RX = re.compile(r"bostad|bostäder|hyr|boende|bygg|lägenhet|fastighet|bolån|amorter|egnahem|småhus|stadsplan|bosätt", re.I)
