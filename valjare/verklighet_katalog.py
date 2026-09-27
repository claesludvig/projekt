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
    # fråga, kort namn, Kolada-id (eller sökord om id är okänt), val (regex mot titel), bättre
    ("sjukvard", "Första kontakt i specialiserad vård inom 90 dagar", "N79222", None, "hogre"),
    ("sjukvard", "Operation/åtgärd inom 90 dagar", "N79224", None, "hogre"),
    ("sjukvard", "Telefonsamtal till primärvården besvarade samma dag", "N79179", None, "hogre"),
    ("skola", "Examen/studiebevis inom 4 år (gymnasiet)", "N17457", None, "hogre"),
    ("skola", "Behöriga till yrkesprogram, åk 9", "ehöriga till yrkesprogram",
     r"(?i)elever i åk\.? ?9.*behöriga till yrkesprogram.*hemkommun, andel", "hogre"),
    ("skola", "Meritvärde åk 9", "eritvärde",
     r"(?i)elever i åk\.? ?9.*genomsnittligt meritvärde.*hemkommun", "hogre"),
    ("aldre", "Väntetid till särskilt boende (dagar)", "U23401", None, "lagre"),
    ("aldre", "Nöjdhet särskilt boende, helhetssyn (%)", "U23471", None, "hogre"),
    ("lag", "Anmälda brott per 100 000 inv", "N07540", None, "lagre"),
    ("lag", "Anmälda våldsbrott per 100 000 inv", "N07403", None, "lagre"),
    ("jobb", "Arbetslöshet 16–64 år, Arbetsförmedlingen (%)", "rbetslöshet 16-64",
     r"(?i)^arbetslöshet 16-64 år.*andel \(%\) av bef", "lagre"),
    ("jobb", "Långtidsarbetslösa, andel av arbetslösa (%)", "N03923", None, "lagre"),
    ("egen_ekonomi", "Låg ekonomisk standard (%)", "N66080", None, "lagre"),
    ("valfard", "Ekonomiskt bistånd (% av bef.)", "N31807", None, "lagre"),
    ("invandring", "Utrikes födda (% av bef.)", "trikes födda",
     r"(?i)^invånare.*utrikes födda.*andel|^utrikes födda invånare.*andel", None),
    ("skatter", "Total skattesats (%)", "N00900", None, "lagre"),
    ("skatter", "Kommunal skattesats (%)", "ommunal skattesats", r"(?i)^kommunal skattesats", "lagre"),
    ("klimat", "Växthusgasutsläpp per invånare (ton)", "N00401", None, "lagre"),
    ("klimat", "Växthusgasutsläpp totalt (ton)", "N07702", None, "lagre"),
    ("bostad", "Färdigställda bostäder, nybyggnad, per 1 000 inv", "N07917", None, "hogre"),
    ("pension", "Låg ekonomisk standard 65+ (%)", "N66079", None, "lagre"),
    ("jamstalldhet", "Kvinnors mediannettoinkomst i % av mäns", "N00952", None, "hogre"),
]

# SCB-serier i riket. "tabell" är ett tabell-id eller ett regex mot rubriken
# (bland tabeller som hämtats med tema "verklighet"; den med längst tidsserie
# väljs). "val": variabel -> värde (eller lista som summeras). "kvot": variabel,
# täljare, lista för nämnare (andel i procent). "innehall": ContentsCode-regex.
SCB_SERIER = [
    {"fraga": "jobb", "namn": "Arbetslöshet 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"Arbetskraftstillh": "arbetslöshetstal, procent", "TypData": "icke säsongrensad",
             "Alder": "~^totalt 15.74"}, "innehall": r".", "battre": "lagre"},
    {"fraga": "jobb", "namn": "Sysselsättningsgrad 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "~^totalt 15.74"}, "innehall": r".", "battre": "hogre"},
    {"fraga": "invandring", "namn": "Sysselsättningsgrad utrikes födda 20–64 (AKU, %)", "tabell": "TAB6529",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "totalt 20–64 år", "InrikesUtrikes": "utrikes födda"}, "innehall": r".", "battre": "hogre"},
    {"fraga": "invandring", "namn": "Sysselsättningsgrad inrikes födda 20–64 (AKU, %)", "tabell": "TAB6529",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "totalt 20–64 år", "InrikesUtrikes": "inrikes födda"}, "innehall": r".", "battre": "hogre"},
    {"fraga": "ekonomi", "namn": "BNP, volymförändring (%)", "tabell": "TAB5621",
     "val": {"Anvandningstyp": "BNP till marknadspris"}, "innehall": r"Volymförändring", "battre": "hogre"},
    {"fraga": "bostad", "namn": "Färdigställda lägenheter i nybyggda hus", "tabell": "TAB2538",
     "val": {"Region": "Riket", "Hustyp": ["flerbostadshus", "småhus"]},
     "innehall": r"^Färdigställda lägenheter", "battre": "hogre"},
    {"fraga": "bostad", "namn": "Fastighetsprisindex småhus (1990=100)", "tabell": "TAB1148",
     "val": {"Lan": "Riket"}, "innehall": r".", "battre": None},
    {"fraga": "invandring", "namn": "Invandringar", "tabell": "TAB1618",
     "val": {"Medbland": "Totalt", "Kon": ["män", "kvinnor"]}, "innehall": r"^Invandringar$", "battre": None},
    {"fraga": "sjukvard", "namn": "Medellivslängd vid födseln, kvinnor (år)", "tabell": "TAB5241",
     "val": {"Alder": "0 år", "Kon": "kvinnor"}, "innehall": r".", "battre": "hogre"},
    {"fraga": "sjukvard", "namn": "Medellivslängd vid födseln, män (år)", "tabell": "TAB5241",
     "val": {"Alder": "0 år", "Kon": "män"}, "innehall": r".", "battre": "hogre"},
    {"fraga": "jamstalldhet", "namn": "Kvinnors lön i procent av mäns", "tabell": "TAB5124",
     "val": {}, "innehall": r".", "battre": "hogre"},
    {"fraga": "energi", "namn": "Elproduktion, kärnkraft (GWh/mån)", "tabell": "TAB78",
     "val": {"ProdAnv": "kärnkraft (kondens), netto ", "Elomrade": ["SE1", "SE2", "SE3", "SE4"]},
     "innehall": r".", "battre": None},
]

RIKSBANKEN = [
    ("egen_ekonomi", "Styrräntan (%)", "SECBREPOEFF", None),
]
