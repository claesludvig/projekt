"""Partiernas genomslag: källor och sökmönster.

Allt hämtas som filer eller flöden, utan API-nycklar:
- Wikidata: entitetsfilen (Special:EntityData/<Q>.json) för varje parti och dess ordförande.
  Egenskapen P8687 (följare i sociala medier) har ett datum (P585) och ett kvalificerande konto
  som anger plattformen.
- Riksdagen: bulkfilerna med anföranden per riksmöte.
- RSS: nyhetsflöden från stora redaktioner och Google Nyheters sökflöde per parti. Flödena visar
  bara de senaste artiklarna, så historiken byggs upp av att de samlas in varje dag.
- Google: öppet CSV-paket med politiska annonser (utgifter per annonsör och vecka). Google och Meta
  slutade visa politiska annonser i EU hösten 2025, så serien är historisk.
"""

# Artikelnamn på Wikipedia (språk:titel); den första som leder till ett objekt används.
PARTI_WIKI = {
    "S": ["sv:Sveriges socialdemokratiska arbetareparti", "en:Swedish Social Democratic Party"],
    "M": ["sv:Moderaterna", "en:Moderate Party"],
    "SD": ["sv:Sverigedemokraterna", "en:Sweden Democrats"],
    "C": ["sv:Centerpartiet", "en:Centre Party (Sweden)"],
    "V": ["sv:Vänsterpartiet", "en:Left Party (Sweden)"],
    "KD": ["sv:Kristdemokraterna (Sverige)", "sv:Kristdemokraterna", "en:Christian Democrats (Sweden)"],
    "L": ["sv:Liberalerna", "en:Liberals (Sweden)"],
    "MP": ["sv:Miljöpartiet de gröna", "en:Green Party (Sweden)"],
}

# Kvalificerare på P8687 -> plattform
PLATTFORM = {
    "P2002": "X", "P6552": "X", "P2003": "Instagram", "P2013": "Facebook", "P7085": "TikTok",
    "P2397": "YouTube", "P11245": "YouTube", "P4033": "Mastodon", "P12361": "Bluesky",
    "P4264": "LinkedIn", "P3789": "Telegram", "P11892": "Threads",
}

# Nyhetsflöden (RSS/Atom). Google Nyheter söks per parti med partinamnet.
FLODEN = [
    ("SVT Nyheter", "https://www.svt.se/nyheter/rss.xml"),
    ("SVT Inrikes", "https://www.svt.se/nyheter/inrikes/rss.xml"),
    ("Sveriges Radio Ekot", "https://api.sr.se/api/rss/program/83"),
    ("DN", "https://www.dn.se/rss/"),
    ("SvD", "https://www.svd.se/feed/articles.rss"),
    ("Aftonbladet", "https://rss.aftonbladet.se/rss2/small/pages/sections/senastenytt/"),
    ("Expressen", "https://feeds.expressen.se/nyheter/"),
]
GOOGLE_NYHETER = "https://news.google.com/rss/search?q=%22{q}%22&hl=sv&gl=SE&ceid=SE:sv"
GOOGLE_SOK = {"S": "Socialdemokraterna", "M": "Moderaterna", "SD": "Sverigedemokraterna",
              "C": "Centerpartiet", "V": "Vänsterpartiet", "KD": "Kristdemokraterna",
              "L": "Liberalerna", "MP": "Miljöpartiet"}

# Omnämnanden i rubrik och ingress. Skiftlägeskänsligt, så att "moderat ökning" inte räknas.
OMNAMNANDE = {
    "S": r"\b[Ss]ocialdemokrat\w*|\(S\)|\bS-(?:ledare\w*|regering\w*|topp\w*|politiker\w*)",
    "M": r"\bModeraterna\w*|\b[Mm]oderatledare\w*|\(M\)|\bM-(?:ledare\w*|topp\w*)",
    "SD": r"\bSverigedemokrat\w*|\bsverigedemokrat\w*|\bSD\b|\(SD\)",
    "C": r"\bCenterpartiet\w*|\b[Cc]enterpartist\w*|\(C\)|\bC-ledare\w*",
    "V": r"\bVänsterpartiet\w*|\b[Vv]änsterpartist\w*|\(V\)|\bV-ledare\w*",
    "KD": r"\bKristdemokrat\w*|\bkristdemokrat\w*|\bKD\b|\(KD\)",
    "L": r"\bLiberalerna\w*|\bliberalledare\w*|\(L\)|\bL-ledare\w*",
    "MP": r"\bMiljöpartiet\w*|\b[Mm]iljöpartist\w*|\bMP\b|\(MP\)",
}

GOOGLE_ANNONSER = "https://storage.googleapis.com/political-csv/google-political-ads-transparency-bundle.zip"
# Annonsörens namn -> parti (lokala partiavdelningar räknas till partiet)
ANNONSOR = {
    "S": r"(?i)socialdemokrat|arbetarepartiet",
    "M": r"(?i)moderata samlingspartiet|moderaterna",
    "SD": r"(?i)sverigedemokrat",
    "C": r"(?i)centerpartiet",
    "V": r"(?i)vänsterpartiet",
    "KD": r"(?i)kristdemokrat",
    "L": r"(?i)liberalerna|folkpartiet liberalerna",
    "MP": r"(?i)miljöpartiet",
}

# Sakfrågor i nyhetstext (gemener, efter att partinamnen tagits bort). Hela ord från ordets början, så att
# "skolval" inte blir skola och "relevant" inte blir elev. Grövre än klassningen av riksdagens ärenden.
SAKORD = {
    "lag": r"\b(?:brott\w*|gäng\w*|skjutning\w*|sprängning\w*|polis\w*|straff\w*|fängelse\w*|kriminal\w*|"
           r"åklagar\w*|mord\w*|trygghet\w*|otrygg\w*)",
    "sjukvard": r"\b(?:sjukvård\w*|vården|vårdkö\w*|väntetid\w*|sjukhus\w*|akuten|vårdcentral\w*|primärvård\w*|"
                r"psykiatri\w*|patient\w*)",
    "aldre": r"\b(?:äldreomsorg\w*|äldreboende\w*|hemtjänst\w*|de äldre)",
    "skola": r"\b(?:skolan|skolor\w*|skolans|grundskol\w*|gymnasi\w*|friskol\w*|lärare\w*|elever\w*|eleven|"
             r"betyg\w*|förskol\w*|läroplan\w*)",
    "jobb": r"\b(?:arbetslös\w*|jobben|jobbskatteavdrag\w*|sysselsättning\w*|a-kassa\w*|arbetsförmedling\w*|varsel\w*)",
    "ekonomi": r"\b(?:ekonomin|budget\w*|inflation\w*|riksbank\w*|styrränt\w*|konjunktur\w*|lågkonjunktur\w*|bnp)\b",
    "egen_ekonomi": r"\b(?:matpris\w*|hushållens|bensinpris\w*|dieselpris\w*|drivmedel\w*|levnadskostnad\w*|"
                    r"hyreshöjning\w*)",
    "invandring": r"\b(?:invandr\w*|migration\w*|asyl\w*|flykting\w*|utvisning\w*|medborgarskap\w*|integration\w*|"
                  r"återvandring\w*)",
    "valfard": r"\b(?:välfärd\w*|försörjningsstöd\w*|bidragstak\w*|fattigdom\w*|socialtjänst\w*)",
    "skatter": r"\b(?:skatt\w*)",
    "klimat": r"\b(?:klimat\w*|utsläpp\w*)",
    "miljo": r"\b(?:miljön|miljöfråg\w*|miljöpolitik\w*|naturskydd\w*|biologisk mångfald)",
    "energi": r"\b(?:kärnkraft\w*|elpris\w*|energi\w*|vindkraft\w*|elnät\w*|elproduktion\w*|reaktor\w*)",
    "bostad": r"\b(?:bostad\w*|bostäder\w*|hyresrätt\w*|bolån\w*|amorter\w*)",
    "pension": r"\b(?:pension\w*)",
    "jamstalldhet": r"\b(?:jämställd\w*|mäns våld|kvinnofrid\w*|feminis\w*)",
    "forsvar": r"\b(?:försvar\w*|nato|militär\w*|värnplikt\w*|totalförsvar\w*)",
}

# Konton som inte finns i Wikidata (kontrollerade 2026-09-28: partiets eller ledarens namn, verifierat konto
# där TikTok visar det). Wikidata är förstahandskällan; de här läggs till.
KONTON_EXTRA = [
    ("S", "parti", "TikTok", "socialdemokraternas"),
    ("SD", "parti", "TikTok", "sverigedemokraterna"),
    ("M", "parti", "TikTok", "moderaterna"),
    ("V", "parti", "TikTok", "vansterpartiet"),
    ("KD", "parti", "TikTok", "kristdemokraterna"),
    ("MP", "parti", "TikTok", "miljopartietdegrona"),
    ("SD", "partiledare", "TikTok", "jimmieakesson"),
    ("M", "partiledare", "TikTok", "ulfkristersson"),
    ("KD", "partiledare", "TikTok", "buschebba"),
    ("V", "partiledare", "TikTok", "nooshidadgostar"),
    ("L", "partiledare", "TikTok", "smohamsson"),
]

# Wikidata-egenskaper med kontonamn per plattform
KONTO_EGENSKAP = {"P2002": "X", "P2003": "Instagram", "P7085": "TikTok", "P2397": "YouTube",
                  "P12361": "Bluesky", "P2013": "Facebook", "P11892": "Threads", "P4033": "Mastodon"}
# Plattformar där följarantalet går att läsa utan inloggning eller betald API-nyckel
MATBARA = ("YouTube", "TikTok", "Bluesky", "Mastodon")

# Medieanvändning i befolkningen (Nordicom, Mediebarometern 2025). Siffrorna är avskrivna ur Nordicoms
# seminariebilder 5 maj 2026 (samma undersökning som rapporten) och kontrollerade mot dem.
MEDIEBAROMETERN = {
    "ar": 2025, "n": 6004, "alder": "9–85 år",
    "kalla": "Nordicom, Mediebarometern 2025 (Falk, 2026), seminariet 5 maj 2026",
    "url": "https://www.nordicom.gu.se/sv/publikationer/mediebarometern-2025",
    # (medium, daglig räckvidd %, förändring mot 2024 i procentenheter)
    "rackvidd": [("Rörlig bild (tv, strömmat, YouTube)", 95, -1), ("Sociala medier", 84, 0),
                 ("Radio och podcast", 76, -2), ("Inspelad musik", 64, 1), ("Dagstidning", 60, -6),
                 ("Bok", 49, -2)],
    # "Mediedieter" en vanlig dag, befolkningen 9–79 år (procent)
    "dieter": {"kategorier": ["Nyheter + underhållning + sociala medier", "Underhållning + sociala medier, inga nyheter",
                              "Nyheter + underhållning", "Enbart nyheter", "Enbart underhållning", "Inga medier"],
               "1997": [0, 0, 33, 55, 6, 7], "2025": [74, 18, 6, 1, 1, 0]},
    "nyheter_dag": {"Hela befolkningen": (88, 81), "Unga vuxna": (76, 63)},   # 1997, 2025
}

# Nyhetsvanor om politik efter ålder (SOM-institutet, Andersson 2025, s. 30): andel som minst tre dagar i veckan
# tar del av nyheter om politik, 2024
POLITIKNYHETER_ALDER = {"kalla": "Andersson, U. (2025). Svenska nyhetsvanor 2005–2024. Mediemyndigheten/SOM-institutet",
                        "url": "https://mediemyndigheten.se/rapporter-och-analyser/svenska-nyhetsvanor/",
                        "v": [("16–29 år", 40), ("30–49 år", 59), ("50–64 år", 69), ("65 år–", 72)]}

# Forskning om partiernas egen nyhetsproduktion och den hybrida politiska kommunikationen
FORSKNING = [
    {"titel": "Den politiska kommunikationens hybridisering: Politiserade nyhetsformat och journalistikens gränser",
     "vem": "Andreas Widholm (projektledare) och Mattias Ekman, Stockholms universitet",
     "typ": "Forskningsprojekt, Riksbankens Jubileumsfond P21-0158 (2 906 000 kr)",
     "url": "https://www.rj.se/bidrag/2021/den-politiska-kommunikationens-hybridisering-politiserade-nyhetsformat-och-journalistikens-granser/",
     "fynd": ["Partierna producerade egna nyhetsformat i valrörelsen 2022: Socialdemokraternas Morgon-Tidningen "
              "(AiP Media), Sverigedemokraternas Youtubekanal Riks, Miljöpartiets nyhetstalkshow Tjugotjugotvå och "
              "Moderaternas lokala initiativ.",
              "Formaten spreds främst via Facebook, Instagram, TikTok och YouTube, inte via egna nyhetssajter.",
              "Partierna var olika öppna med vem som stod bakom innehållet; Riks beskrevs som konservativ "
              "nyhetsproduktion utan partibeteckning.",
              "Sverigedemokraterna var betydligt mer effektiva än andra partier i att skapa engagemang i sociala "
              "medier, med både organisk spridning och riktade kampanjer."]},
    {"titel": "Parasitic news: Adoption and adaption of journalistic conventions in hybrid political communication",
     "vem": "Ekman, M. & Widholm, A. (2024)", "typ": "Journalism: Theory, Practice & Criticism",
     "url": "https://doi.org/10.1177/14648849221136940",
     "fynd": ["Begreppet parasitiska nyheter: partier och politiker lånar journalistikens former för att nå väljare "
              "när nyhetsinstitutionerna inte längre är självklara mellanhänder.",
              "Analysramen har fem dimensioner: ideologisk öppenhet, alternativitet, nyhetsgenrer, individuell "
              "eller kollektiv medieproduktion och sociala mediers möjligheter. Formen används från höger till vänster."]},
    {"titel": "Political communication as television news: Party-produced news of the Sweden Democrats during the "
              "2022 election campaign",
     "vem": "Ekman, M. & Widholm, A. (2024)", "typ": "Nordicom Review 45(s1), 66–91",
     "url": "https://doi.org/10.2478/nor-2024-0008",
     "fynd": ["Alla videor som Riks publicerade de fyra sista veckorna före valet 2022 blandar beskrivande, tolkande "
              "och upprörda genrer och ramar in valrörelsens viktigaste frågor till partiets fördel.",
              "Riks döljer kopplingen till partiet och är det mest utvecklade exemplet på parasitiska nyheter i Sverige."]},
]
