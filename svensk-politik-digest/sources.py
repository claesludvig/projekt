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
SOURCES = [
    # --- Nyhetsrapportering ------------------------------------------------
    {
        "name": "SVT Nyheter",
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
        "kind": "nyhet",
        "filter": True,
        "urls": [
            "https://api.sr.se/api/rss/program/83",
            "https://api.sr.se/api/rss/channel/132",
        ],
    },
    {
        "name": "DN Nyheter",
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
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://www.dn.se/ledare/rss/",
            "https://www.dn.se/ledare/feed/",
        ],
    },
    {
        "name": "SvD Ledare",
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://www.svd.se/feed/ledare.rss",
            "https://www.svd.se/feed/articles.rss",
        ],
    },
    {
        "name": "Expressen Ledare",
        "kind": "kommentar",
        "filter": True,
        "urls": [
            "https://feeds.expressen.se/ledare/",
            "https://feeds.expressen.se/nyheter/",
        ],
    },
    {
        "name": "Aftonbladet Ledare",
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
        "kind": "officiell",
        "filter": False,
        "urls": [
            "https://www.regeringen.se/rss/",
            "https://www.regeringen.se/Filter/RssFeed?filterType=Taxonomy"
            "&filterByType=FilterablePageBase&rootPageReference=0&displayLocal=true",
        ],
    },
    {
        "name": "Riksdagen",
        "kind": "officiell",
        "filter": False,
        "urls": [
            "https://www.riksdagen.se/sv/aktuellt/rss/",
            "https://www.riksdagen.se/rss/aktuellt/",
        ],
    },
]

# Ett ensamt ämnesord räcker för att artikeln ska tas med. Listan är medvetet
# smal mot regeringsbildningen — bred svensk inrikespolitik fångas i stället
# via partinamnen nedan, som kräver två träffar.
TOPIC_TERMS = [
    "regeringsbildning",
    "regeringsbildande",
    "regeringsförhandling",
    "regeringsunderlag",
    "regeringsfrågan",
    "regeringsalternativ",
    "regeringsmakten",
    "talmansrunda",
    "talmannen",
    "sonderingar",
    "sonderingsuppdrag",
    "statsministeromröstning",
    "statsministerkandidat",
    "blivande statsminister",
    "koalition",
    "koalitionsregering",
    "samarbetsparti",
    "samarbetspartier",
    "stödparti",
    "mandatfördelning",
    "riksdagsval",
    "valresultat",
    "regeringskris",
    "misstroendeförklaring",
    "tidöavtalet",
    "budgetförhandling",
    "statsrådspost",
    "ministerpost",
    "departementsfördelning",
    "partiledarsamtal",
    "vågmästare",
]

# Partinamn: kräver minst två distinkta träffar för att artikeln ska räknas som
# politisk. Förkortningar (S, M, SD) är för brusiga för att matcha på.
PARTY_TERMS = [
    "socialdemokraterna",
    "moderaterna",
    "sverigedemokraterna",
    "centerpartiet",
    "vänsterpartiet",
    "kristdemokraterna",
    "liberalerna",
    "miljöpartiet",
    "socialdemokratiska",
    "moderat",
    "sverigedemokratisk",
]

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
