"""Aktörer, var deras rapporter ligger och vad som räknas som bostadsrelevant."""
import re

AKTORER = {
    "sn":  {"namn": "Svenskt Näringsliv", "js": True, "sitemap": "https://www.svensktnaringsliv.se/sitemapindex.xml",
            "sida": r"svensktnaringsliv\.se/(sakomraden|fragor|regioner|material|bilder_och_dokument|amne)/", "slug": True},
    "fa":  {"namn": "Fastighetsägarna", "js": True, "sitemap": "https://www.fastighetsagarna.se/sitemap.xml",
            "sida": r"fastighetsagarna\.se/(aktuellt/rapporter/|fakta/|aktuellt/nyheter/.*(rapport|analys|undersokning|prognos|kvartal|hyresgastenkat|bostadsbrist))", "slug": False},
    "hsb": {"namn": "HSB", "sitemap": None, "sida": r"hsb\.se/", "slug": False},
    "hgf": {"namn": "Hyresgästföreningen", "sitemap": "https://www.hyresgastforeningen.se/sitemap.xml",
            "sida": r"hyresgastforeningen\.se/(bostadsfakta/(rapporter|fakta)/|globalassets/bostadsfakta/.*\.pdf$)", "slug": False},
    "shk": {"namn": "Stockholms Handelskammare", "sitemap": "https://stockholmshandelskammare.se/sitemap.xml",
            "wp": True, "sida": r"stockholmshandelskammare\.se/(rapporter/[^/]+/$|nyheter/.*(rapport|analys))", "slug": True},
    "bf":  {"namn": "Byggföretagen", "sitemap": "https://byggforetagen.se/sitemap.xml",
            "wp": True, "sida": r"byggforetagen\.se/(20\d\d/\d\d/.*(rapport|analys|prognos|konjunktur|bostad|byggande|hyres|byggkostnad)|statistik/|bostadsmarknad|byggkonjunktur|konjunktur)", "slug": False},
    "sa":  {"namn": "Sveriges Allmännytta", "pdfvard": ["d1vpjw3v2d2tlw.cloudfront.net"], "sitemap": "https://www.sverigesallmannytta.se/sitemap.xml",
            "wp": True, "sida": r"sverigesallmannytta\.se/", "slug": True},
    "rb":  {"namn": "Riksbyggen", "sitemap": "https://www.riksbyggen.se/sitemap.xml",
            "sida": r"riksbyggen\.se/om-riksbyggen/(bostadspolitik/|pressrum/20\d\d/\d+)", "slug": False},
    "tim": {"namn": "Timbro", "sitemap": "https://timbro.se/sitemap_index.xml",
            "wp": True, "sida": r"timbro\.se/(publikation|rapporter)/", "slug": True},
    "bov": {"namn": "Boverket", "sitemap": "https://www.boverket.se/sitemap.xml",
            "sida": r"boverket\.se/sv/(om-boverket/publikationer/20(0[5-9]|1\d|2\d)/|samhallsplanering/bostadsmarknad/)", "slug": True},
    "fs":  {"namn": "Svenska Bankföreningen", "sitemap": "https://www.financesweden.se/sitemap.xml",
            "sida": r"financesweden\.se/(fakta-och-rapporter/|bankfokus/.*bostad)", "slug": True},
}

# Sidor som hämtas bara för att ge PDF:er i mediebiblioteket titel, datum och ingress
META_SIDA = {
    "tim": r"timbro\.se/publikation/",
    "shk": r"stockholmshandelskammare\.se/(rapporter/[^/]+/$|nyheter/)",
    "sa":  r"sverigesallmannytta\.se/",
    "bf":  r"byggforetagen\.se/(20\d\d/\d\d/|statistik/|bostadsmarknad)",
}

# Ord i URL:en som tyder på att sidan handlar om bostäder (för sajter där allt annat också ligger)
SLUG = re.compile(r"bostad|bostader|hyr|bygg|boende|bopris|bolan|amorter|skuld|trangbodd|nyproduktion|"
                  r"plan|allmannytt|bostadsratt|flytt|rorlighet|stadsutveckl|fastighetsskatt|rantea|markanvisn|"
                  r"hemlos|lagenhet|smahus|egnahem|kredit|hushall|tomtratt|renover|miljonprogram|segregat|student|"
                  r"tillvaxt.*stad|storstad|stockholm.*(vaxer|vaxt)|housing", re.I)

# Striktare variant för byggbranschens egna sajter, där "bygg" står överallt
SLUG_BYGG = re.compile(SLUG.pattern.replace("|bygg|", "|byggande|byggkostnad|byggprognos|byggkonjunktur|"
                                            "bostadsbygg|byggstart|konjunktur|prognos|marknad|"), re.I)
# Aktörer där alla PDF:er i mediebiblioteket hämtas och textfiltret får avgöra
WP_ALLA = {"shk", "sa"}

# Termer som räknas för relevans i texten
TERMER = [
    "bostadsbyggande", "bostadsbyggandet", "bostadsmarknad", "bostadsbrist", "bostadsförsörjning", "bostadspolitik",
    "hyresmarknad", "hyressättning", "bruksvärde", "presumtionshyr", "marknadshyr", "hyresreglering", "hyresrätt",
    "bostadsrätt", "småhus", "flerbostadshus", "nyproduktion", "påbörjade bostäder", "färdigställda bostäder",
    "byggkostnad", "produktionskostnad", "markpris", "detaljplan", "planprocess", "markanvisning",
    "bolån", "amorteringskrav", "bolånetak", "skuldkvot", "ränteavdrag", "fastighetsavgift", "fastighetsskatt",
    "flyttskatt", "reavinstskatt", "investeringsstöd", "allmännytt", "trångboddhet", "rörlighet på bostadsmarknaden",
    "bostadspris", "huspris", "bostadsbidrag", "bostadskö", "andrahandsuthyrning", "tomträtt", "boendekostnad",
]
TERM_RX = re.compile("|".join(re.escape(t) for t in TERMER), re.I)

# Teman för filtrering i gränssnittet; en källa kan ha flera
TEMAN = {
    "bygg":   ("Bostadsbyggande och byggkostnader", r"bostadsbyggande|påbörjade|färdigställ|nyproduktion|byggkostnad|produktionskostnad|byggprognos|byggkonjunktur|byggande"),
    "hyra":   ("Hyresmarknad och hyressättning", r"hyressättning|bruksvärde|presumtionshyr|marknadshyr|hyresreglering|hyresförhandling|hyresnivå|hyreshöjning|andrahand"),
    "fin":    ("Bolån, skulder och finansiering", r"bolån|amortering|skuldkvot|belåningsgrad|räntekostnad|bostadskredit|kreditrestriktion|bolånetak|skuldsättning"),
    "skatt":  ("Skatter och subventioner", r"ränteavdrag|fastighetsavgift|fastighetsskatt|flyttskatt|reavinstskatt|uppskov|investeringsstöd|bostadsbidrag|subvention|rot-avdrag"),
    "plan":   ("Planering, mark och regler", r"detaljplan|planprocess|plan- och bygglag|markanvisning|strandskydd|riksintresse|bygglov|överklagan|tomträtt|markpris"),
    "rorl":   ("Rörlighet, trångboddhet och bostadsbrist", r"rörlighet|trångbodd|bostadsbrist|bostadskö|inlåsning|flyttkedj|hemlöshet|unga vuxna|förstagångsköpare"),
    "pris":   ("Bostadspriser och marknadsläge", r"bostadspris|huspris|prisutveckling|bostadsrättspris|bopris|prisfall|kvadratmeterpris"),
    "allm":   ("Allmännyttan och bostadsförsörjning", r"allmännytt|kommunala bostadsbolag|bostadsförsörjning|social bostadspolitik|sociala bostäder|utförsäljning"),
    "region": ("Stockholm och regional tillväxt", r"stockholm|storstad|regionförstoring|pendling|kompetensförsörjning|arbetskraft"),
    "ren":    ("Renovering och energi", r"renovering|miljonprogram|energieffektiv|energiprestanda|upprustning|EPBD"),
}
