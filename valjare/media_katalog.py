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
    "KD": ["sv:Kristdemokraterna", "sv:Kristdemokraterna (Sverige)", "en:Christian Democrats (Sweden)"],
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
    ("Omni", "https://omni.se/rss"),
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
