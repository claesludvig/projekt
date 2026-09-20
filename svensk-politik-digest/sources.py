#!/usr/bin/env python3
"""Källor, ämnesfilter och skribentlista för svensk-politik-digesten.

Separerad från scraper.py eftersom det här är den del som behöver justeras
löpande: flöden byter URL, nya kommentatorer tillkommer och ämnesorden ändras
när regeringsbildningen går in i en ny fas.

Varje källa anger flera kandidat-URL:er. Svenska mediehus byter RSS-sökväg
med jämna mellanrum, så scrapern provar dem i ordning och tar den första som
faktiskt ger poster. Då dör inte hela körningen för att ett flöde flyttat.
"""

# kind: "nyhet" = rapportering, "kommentar" = ledare/analys, "officiell" = myndighet
# filter: True = kräver träff i ämnesfiltret, False = allt i flödet är relevant
# paywalled: True = kort brödtext får tolkas som betalvägg. Falskt för öppna
#   avsändare, annars flaggas ett kort riksdagsdokument eller pressmeddelande
#   som betalvägg bara för att det är kort.
SOURCES = [
    # --- Nyhetsrapportering ------------------------------------------------
    {
        "name": "SVT Nyheter",
        "paywalled": False,
        "kind": "nyhet",
        "filter": True,
        "urls": [
            "https://www.svt.se/nyheter/inrikes/rss.xml",
            "https://www.svt.se/nyheter/rss.xml",
            "https://www.svt.se/rss.xml",
        ],
    },
    {
        "name": "Ekot, Sveriges Radio",
        "paywalled": False,
        "kind": "nyhet",
        "filter": True,
        "urls": [
            "https://api.sr.se/api/rss/program/83",
            "https://api.sr.se/api/rss/channel/132",
        ],
    },
    {
        "name": "DN Nyheter",
        "paywalled": True,
        "kind": "nyhet",
        "filter": True,
        "urls": [
            "https://www.dn.se/nyheter/politik/rss/",
            "https://www.dn.se/rss/",
        ],
    },
    # --- Ledare, analys och kommentar --------------------------------------
    {
        "name": "DN Ledare",
        "paywalled": True,
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://www.dn.se/ledare/rss/",
            "https://www.dn.se/ledare/feed/",
        ],
    },
    {
        "name": "SvD Ledare",
        "paywalled": True,
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://www.svd.se/feed/ledare.rss",
            "https://www.svd.se/feed/articles.rss",
        ],
    },
    {
        "name": "Expressen Ledare",
        "paywalled": True,
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://feeds.expressen.se/ledare/",
            "https://feeds.expressen.se/nyheter/",
        ],
    },
    {
        "name": "Aftonbladet Ledare",
        "paywalled": True,
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://rss.aftonbladet.se/rss2/small/pages/sections/ledare/",
            "https://rss.aftonbladet.se/rss2/small/pages/sections/senastenytt/",
        ],
    },
    # --- Officiella källor --------------------------------------------------
    {
        "name": "Regeringen.se",
        "paywalled": False,
        "kind": "officiell",
        # Flödet är allt regeringen publicerar - statsbesök, myndighetsuppdrag,
        # utredningsdirektiv. Utan filter dränker det utskicket, så det prövas
        # mot samma ämnesord som nyhetsflödena.
        "filter": True,
        "urls": [
            "https://www.regeringen.se/Filter/RssFeed?filterType=Taxonomy"
            "&filterByType=FilterablePageBase&rootPageReference=0&displayLocal=true",
            "https://www.regeringen.se/rss/",
        ],
    },
    {
        "name": "Riksdagen",
        "paywalled": False,
        "kind": "officiell",
        "filter": True,
        # www.riksdagen.se/sv/aktuellt/rss/ svarar 404. Öppna data-API:et
        # (data.riksdagen.se) levererar dokumentlistor som RSS via utformat=rss.
        "urls": [
            "https://data.riksdagen.se/dokumentlista/?sok=regeringsbildning"
            "&sort=datum&sortorder=desc&utformat=rss",
            "https://data.riksdagen.se/dokumentlista/?sok=&doktyp=&sort=datum"
            "&sortorder=desc&utformat=rss&a=s",
            "https://www.riksdagen.se/sv/aktuellt/rss/",
        ],
    },
]

# Ett ensamt ämnesord räcker för att artikeln ska tas med. Listan är medvetet
# smal mot regeringsbildningen - bred svensk inrikespolitik fångas i stället
# via partinamnen nedan, som kräver två träffar.
#
# Orden är STAMMAR, inte fulla ordformer, eftersom svenska böjer i bestämd form
# och plural: "talmansrunda" matchar inte "talmansrundorna", men "talmansrund"
# matchar båda. Lägg till nya ord i samma form - kapa ändelsen.
TOPIC_TERMS = [
    "regeringsbildning",      # -en
    "regeringsbildande",
    "regeringsförhandling",   # -ar, -arna
    "regeringsunderlag",      # -et
    "regeringsfråg",          # -an, -orna
    "regeringsalternativ",
    "regeringsmakt",          # -en
    "regeringskris",          # -en
    "regeringsskifte",        # -t
    "regeringsombildning",    # -en
    "övergångsregering",      # -en
    "expeditionsministär",    # -en
    "talman",                 # talmannen, talmansrunda, talmansrundorna
    "sondering",              # -ar, -arna, sonderingsuppdrag
    "statsminister",          # -n, -posten, -kandidat, -omröstning
    "statsrådspost",          # -en, -er
    "statsrådsberedning",     # -en
    "ministerpost",           # -en, -er
    "departementsfördelning", # -en
    "koalition",              # -en, -er, koalitionsregering
    "samarbetspart",          # -i, -ier, -ierna
    "stödparti",              # -er, -erna
    "partiledar",             # partiledare, -na, -samtal, -debatt
    "mandatfördelning",       # -en
    "riksdagsval",            # -et
    "valresultat",            # -et
    "misstroendeförklaring",  # -en
    "budgetförhandling",      # -ar, -arna
    "vågmästar",              # vågmästare, -rollen
    "tidöavtal",              # -et
]

# Partinamn: kräver minst två olika *partier* för att artikeln ska räknas som
# politisk. Varianterna grupperas per parti eftersom de överlappar som
# delsträngar - "moderat" ligger inuti "moderaterna", och räknades de var för
# sig skulle ett enda omnämnande av ett parti se ut som två träffar och släppa
# igenom vilken partinotis som helst. Förkortningar (S, M, SD) är för brusiga
# för att matcha på.
PARTIES = {
    "Socialdemokraterna": ["socialdemokraterna", "socialdemokratiska", "socialdemokratisk"],
    "Moderaterna": ["moderaterna", "moderat"],
    "Sverigedemokraterna": ["sverigedemokraterna", "sverigedemokratisk"],
    "Centerpartiet": ["centerpartiet", "centerpartist"],
    "Vänsterpartiet": ["vänsterpartiet", "vänsterpartist"],
    "Kristdemokraterna": ["kristdemokraterna", "kristdemokrat"],
    "Liberalerna": ["liberalerna"],
    "Miljöpartiet": ["miljöpartiet", "miljöpartist"],
}

# Namngivna politiska kommentatorer. Träffar markeras i utskicket så att analys
# går att skilja från ren rapportering. Matchas mot författarfält och mot
# titel/ingress, eftersom flera flöden saknar strukturerat författarfält.
COMMENTATORS = [
    "Viktor Barth-Kron",
    "Ewa Stenberg",
    "Amanda Sokolnicki",
    "Erik Helmerson",
    "Susanne Nyström",
    "Peter Wolodarski",
    "Tove Lifvendahl",
    "Per Gudmundson",
    "Göran Eriksson",
    "Anna Dahlberg",
    "Patrik Kronqvist",
    "K-G Bergström",
    "Lena Mellin",
    "Anders Lindberg",
    "Mats Knutson",
    "Elisabeth Marmorstein",
    "Fredrik Furtenbach",
    "Tomas Ramberg",
    "Jenny Sanner Roosqvist",
]

# Indikatorer på att brödtexten är avkortad av betalvägg.
PAYWALL_MARKERS = [
    "logga in för att läsa",
    "prenumerera för att läsa",
    "denna artikel är för prenumeranter",
    "endast för prenumeranter",
    "fortsätt läsa med",
    "testa dn",
    "köp digital prenumeration",
]
