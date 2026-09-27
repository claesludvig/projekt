"""Verklighetsindikatorer per sakfråga.

Varje sakfråga som väljarna rangordnar (Valu: "Vilken betydelse har följande
frågor för ditt val av parti", SOM: "viktigaste samhällsproblem") kopplas till
ett eller flera mått på hur det faktiskt har utvecklats.

- KOLADA: nyckeltal per kommun, region och riket (api.kolada.se). "sok" är en
  fritextsökning på titeln, "valj" ett reguljärt uttryck som väljer rätt
  nyckeltal bland träffarna. Alla träffar loggas i data/katalog/kolada_katalog.csv.
- SCB: tabeller i riket via samma sökmekanism som i kallor.py (tema "verklighet"),
  tolkade i verklighet.py med SCB_SERIER.
- RIKSBANKEN: serier i SWEA-API:t.

"battre": "hogre" / "lagre" / None anger åt vilket håll utvecklingen är bättre
för medborgarna (None = neutralt, t.ex. invandring).
"""

FRAGOR = [
    # (id, Valu-fråga, SOM-kategori)
    ("sjukvard", "Sjukvården", "Sjukvård"),
    ("skola", "Skola och utbildning", "Skola/utbildning"),
    ("aldre", "Äldreomsorgen", "Äldrefrågor"),
    ("lag", "Lag och ordning", "Lag och ordning"),
    ("jobb", "Sysselsättning", "Arbetsmarknad"),
    ("ekonomi", "Svenska ekonomin", "Ekonomi"),
    ("egen_ekonomi", "Din egen ekonomi", "Ekonomi"),
    ("invandring", "Flyktingar/invandring", "Integration/immigration"),
    ("valfard", "Sociala välfärden", "Sociala frågor/problem"),
    ("skatter", "Skatterna", "Skatter"),
    ("miljo", "Miljön", "Miljö/energi"),
    ("klimat", "Klimatfrågan", "Miljö/energi"),
    ("energi", "Energi och kärnkraft", "Miljö/energi"),
    ("bostad", "Bostadsfrågan", "Bostäder/byggnadsfrågor"),
    ("pension", "Pensionerna", "Äldrefrågor"),
    ("jamstalldhet", "Jämställdheten mellan kvinnor och män", None),
    ("forsvar", "Försvarsfrågan", "Utrikes-/försvarspolitik"),
]

KOLADA = [
    # fråga, kort namn, sökord, val (regex mot titel), bättre
    ("sjukvard", "Besök i specialiserad vård inom 90 dagar", "specialiserad vård inom 90 dagar",
     r"(?i)besök.*specialiserad vård inom 90 dagar.*andel", "hogre"),
    ("sjukvard", "Operation/åtgärd inom 90 dagar", "åtgärd inom 90 dagar",
     r"(?i)(operation|åtgärd).*inom 90 dagar.*andel", "hogre"),
    ("sjukvard", "Kontakt med primärvården samma dag", "primärvården samma dag",
     r"(?i)kontakt med primärvården samma dag", "hogre"),
    ("skola", "Behöriga till yrkesprogram, åk 9", "behöriga till ett yrkesprogram",
     r"(?i)elever i åk\.? ?9.*behöriga till (ett )?yrkesprogram.*hemkommun.*andel", "hogre"),
    ("skola", "Meritvärde åk 9", "genomsnittligt meritvärde",
     r"(?i)elever i åk\.? ?9.*genomsnittligt meritvärde.*hemkommun", "hogre"),
    ("skola", "Gymnasieexamen inom 4 år", "examen inom 4 år",
     r"(?i)gymnasieelever med examen inom 4 år.*hemkommun.*andel", "hogre"),
    ("aldre", "Väntetid till särskilt boende (dagar)", "väntetid i antal dagar från ansökningsdatum",
     r"(?i)väntetid i antal dagar från ansökningsdatum till erbjudet inflyttningsdatum till särskilt boende", "lagre"),
    ("aldre", "Nöjdhet särskilt boende, helhetssyn", "särskilt boende äldreomsorg - helhetssyn",
     r"(?i)brukarbedömning särskilt boende äldreomsorg - helhetssyn", "hogre"),
    ("lag", "Anmälda brott per 100 000 inv", "anmälda brott totalt",
     r"(?i)^anmälda brott totalt, antal/100 000 inv", "lagre"),
    ("lag", "Anmälda våldsbrott per 100 000 inv", "anmälda våldsbrott",
     r"(?i)^anmälda våldsbrott, antal/100 000 inv", "lagre"),
    ("jobb", "Arbetslöshet 16–64 år", "arbetslöshet 16-64",
     r"(?i)^arbetslöshet 16-64 år, andel \(%\) av befolkningen", "lagre"),
    ("jobb", "Förvärvsarbetande 20–64 år", "förvärvsarbetande invånare 20-64",
     r"(?i)^förvärvsarbetande invånare 20-64 år, andel", "hogre"),
    ("jobb", "Långtidsarbetslöshet 25–64 år", "långtidsarbetslöshet",
     r"(?i)^långtidsarbetslöshet 25-64 år, andel", "lagre"),
    ("egen_ekonomi", "Medianinkomst (disponibel) per k.e.", "disponibel inkomst",
     r"(?i)disponibel inkomst.*median.*(kr|tkr)", "hogre"),
    ("valfard", "Ekonomiskt bistånd", "erhållit ekonomiskt bistånd",
     r"(?i)invånare som någon gång under året erhållit ekonomiskt bistånd, andel", "lagre"),
    ("invandring", "Utrikes födda", "födda utomlands",
     r"(?i)^invånare (som är )?födda utomlands, andel", None),
    ("invandring", "Nyanlända mottagna", "nyanlända",
     r"(?i)mottagna nyanlända.*antal", None),
    ("invandring", "Förvärvsarbetande utrikes födda 20–64", "förvärvsarbetande utrikes födda",
     r"(?i)förvärvsarbetande.*utrikes födda.*20-64.*andel", "hogre"),
    ("skatter", "Kommunal skattesats", "kommunal skattesats",
     r"(?i)^kommunal skattesats", "lagre"),
    ("skatter", "Total skattesats", "total skattesats",
     r"(?i)^total skattesats", "lagre"),
    ("klimat", "Växthusgasutsläpp per invånare", "växthusgaser",
     r"(?i)utsläpp till luft av växthusgaser, totalt, ton co2-ekv/inv", "lagre"),
    ("bostad", "Färdigställda bostäder per 1 000 inv", "färdigställda bostäder",
     r"(?i)färdigställda bostäder.*nybyggda hus.*antal/1000", "hogre"),
    ("pension", "Låg ekonomisk standard 65+", "låg ekonomisk standard",
     r"(?i)invånare 65\+ år med låg ekonomisk standard|invånare 65 år och äldre.*låg ekonomisk", "lagre"),
    ("jamstalldhet", "Kvinnors inkomst i procent av mäns", "kvinnors",
     r"(?i)kvinnors (medianinkomst|nettoinkomst|sammanräknade förvärvsinkomst).*(i förhållande|i procent|/).*män", "hogre"),
]

# SCB-serier i riket. "tabell" är ett tabell-id eller ett regex mot rubriken
# (bland tabeller som hämtats med tema "verklighet"; den med längst tidsserie
# väljs). "val": variabel -> värde (eller lista som summeras). "kvot": variabel,
# täljare, lista för nämnare (andel i procent). "innehall": ContentsCode-regex.
SCB_SERIER = [
    {"fraga": "jobb", "namn": "Arbetslöshet 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"~(?i)typ": "~(?i)^original|^icke|ej säsong", "~(?i)alder|ålder": "~15-74|15–74"},
     "innehall": r"(?i)1000|tusental|antal",
     "kvot": ("~(?i)arbetskraft", r"(?i)^arbetslösa", [r"(?i)^arbetslösa", r"(?i)^sysselsatta"]), "battre": "lagre"},
    {"fraga": "jobb", "namn": "Sysselsättningsgrad 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"~(?i)typ": "~(?i)^original|^icke|ej säsong", "~(?i)alder|ålder": "~15-74|15–74"},
     "innehall": r"(?i)1000|tusental|antal",
     "kvot": ("~(?i)arbetskraft", r"(?i)^sysselsatta", [r"(?i)^(totalt|befolkning)"]), "battre": "hogre"},
    {"fraga": "invandring", "namn": "Sysselsättningsgrad utrikes födda 15–74 (AKU, %)", "tabell": "TAB6529",
     "val": {"~(?i)typ": "~(?i)^original|^icke|ej säsong", "~(?i)alder|ålder": "~15-74|15–74",
     "~(?i)fodd|född|inrikes": "~(?i)^utrikes"},
     "innehall": r"(?i)1000|tusental|antal",
     "kvot": ("~(?i)arbetskraft", r"(?i)^sysselsatta", [r"(?i)^(totalt|befolkning)"]), "battre": "hogre"},
    {"fraga": "ekonomi", "namn": "BNP, volymförändring (%)", "tabell": "TAB5621",
     "val": {"Anvandningstyp": "BNP till marknadspris"}, "innehall": r"Volymförändring", "battre": "hogre"},
    {"fraga": "bostad", "namn": "Färdigställda lägenheter i nybyggda hus", "tabell": "TAB2538",
     "val": {"Region": "Riket", "Hustyp": ["flerbostadshus", "småhus"]},
     "innehall": r"^Färdigställda lägenheter", "battre": "hogre"},
    {"fraga": "bostad", "namn": "Fastighetsprisindex småhus (1990=100)", "tabell": "TAB1148",
     "val": {"Lan": "Riket"}, "innehall": r".", "battre": None},
    {"fraga": "invandring", "namn": "Invandringar", "tabell": "TAB1618",
     "val": {"Medbland": "Totalt", "Kon": ["män", "kvinnor"]}, "innehall": r"^Invandringar$", "battre": None},
    {"fraga": "klimat", "namn": "Växthusgasutsläpp (tusen ton CO2-ekv)",
     "tabell": r"(?i)växthusgas.*(sektor|totalt|nationella)", "val": {}, "innehall": r".", "battre": "lagre"},
    {"fraga": "sjukvard", "namn": "Medellivslängd vid födseln", "tabell": r"(?i)medellivslängd",
     "val": {}, "innehall": r".", "battre": "hogre"},
    {"fraga": "jamstalldhet", "namn": "Kvinnors lön i procent av mäns", "tabell": r"(?i)kvinnors lön i procent av mäns",
     "val": {}, "innehall": r"(?i)kvinnors lön i procent", "battre": "hogre"},
    {"fraga": "energi", "namn": "Elproduktion, kärnkraft (GWh/mån)", "tabell": "TAB78",
     "val": {"ProdAnv": "kärnkraft (kondens), netto ", "Elomrade": ["SE1", "SE2", "SE3", "SE4"]},
     "innehall": r".", "battre": None},
]

RIKSBANKEN = [
    ("egen_ekonomi", "Styrräntan (%)", "SECBREPOEFF", None),
]
