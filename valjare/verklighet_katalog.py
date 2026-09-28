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

Katalogen säger inte vilket håll som är "bättre". Det är en politisk bedömning.
Riktning och målnivå anges bara i MAL, och bara där riksdagen, lagen, Riksbanken
eller ett internationellt åtagande som Sverige har anslutit sig till anger ett mål.
Övriga indikatorer visas neutralt.
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
    # fråga, kort namn, Kolada-id (eller sökord om id är okänt), val (regex mot titel)
    ("sjukvard", "Första kontakt i specialiserad vård inom 90 dagar", "N79222", None),
    ("sjukvard", "Operation/åtgärd inom 90 dagar", "N79224", None),
    ("sjukvard", "Telefonsamtal till primärvården besvarade samma dag", "N79179", None),
    ("skola", "Examen/studiebevis inom 4 år (gymnasiet)", "N17457", None),
    ("skola", "Behöriga till yrkesprogram, åk 9", "ehöriga till yrkesprogram",
     r"(?i)elever i åk\.? ?9.*behöriga till yrkesprogram.*hemkommun, andel"),
    ("skola", "Meritvärde åk 9", "eritvärde",
     r"(?i)elever i åk\.? ?9.*genomsnittligt meritvärde.*hemkommun"),
    ("aldre", "Väntetid till särskilt boende (dagar)", "U23401", None),
    ("aldre", "Nöjdhet särskilt boende, helhetssyn (%)", "U23471", None),
    ("lag", "Anmälda brott per 100 000 inv", "N07540", None),
    ("lag", "Anmälda våldsbrott per 100 000 inv", "N07403", None),
    ("jobb", "Arbetslöshet 16–64 år, Arbetsförmedlingen (%)", "rbetslöshet 16-64",
     r"(?i)^arbetslöshet 16-64 år.*andel \(%\) av bef"),
    ("jobb", "Långtidsarbetslösa, andel av arbetslösa (%)", "N03923", None),
    ("egen_ekonomi", "Låg ekonomisk standard (%)", "N66080", None),
    ("valfard", "Ekonomiskt bistånd (% av bef.)", "N31807", None),
    ("invandring", "Utrikes födda (% av bef.)", "trikes födda",
     r"(?i)^invånare.*utrikes födda.*andel|^utrikes födda invånare.*andel"),
    ("skatter", "Total skattesats (%)", "N00900", None),
    ("skatter", "Kommunal skattesats (%)", "ommunal skattesats", r"(?i)^kommunal skattesats"),
    ("klimat", "Växthusgasutsläpp per invånare (ton)", "N00401", None),
    ("klimat", "Växthusgasutsläpp totalt (ton)", "N07702", None),
    ("bostad", "Färdigställda bostäder, nybyggnad, per 1 000 inv", "N07917", None),
    ("pension", "Låg ekonomisk standard 65+ (%)", "N66079", None),
    ("jamstalldhet", "Kvinnors mediannettoinkomst i % av mäns", "N00952", None),
    # --- luckor
    ("skola", "Meritvärde åk 9 (hemkommun, 17 ämnen)", "N15507", None),
    ("jobb", "Arbetslöshet 20–64 år, registerbaserad (BAS, %)", "N02280", None),
    ("invandring", "Arbetslöshet bland utrikes födda 20–64 år (BAS, %)", "N02282", None),
    ("sjukvard", "Barn- och ungdomspsykiatri: första besök inom 90 dagar (%)", "U72552", None),
    ("miljo", "Skyddad natur, andel av landareal (%)", "N85054", None),
    ("miljo", "Ekologiska livsmedel i kommunens verksamhet (%)", "U07514", None),
]

# SCB-serier i riket. "tabell" är ett tabell-id eller ett regex mot rubriken
# (bland tabeller som hämtats med tema "verklighet"; den med längst tidsserie
# väljs). "val": variabel -> värde (eller lista som summeras). "kvot": variabel,
# täljare, lista för nämnare (andel i procent). "innehall": ContentsCode-regex.
SCB_SERIER = [
    {"fraga": "jobb", "namn": "Arbetslöshet 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"Arbetskraftstillh": "arbetslöshetstal, procent", "TypData": "icke säsongrensad",
             "Alder": "~^totalt 15.74"}, "innehall": r"."},
    {"fraga": "jobb", "namn": "Sysselsättningsgrad 15–74 år (AKU, %)", "tabell": "TAB6514",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "~^totalt 15.74"}, "innehall": r"."},
    {"fraga": "invandring", "namn": "Sysselsättningsgrad utrikes födda 20–64 (AKU, %)", "tabell": "TAB6529",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "totalt 20–64 år", "InrikesUtrikes": "utrikes födda"}, "innehall": r"."},
    {"fraga": "invandring", "namn": "Sysselsättningsgrad inrikes födda 20–64 (AKU, %)", "tabell": "TAB6529",
     "val": {"Arbetskraftstillh": "sysselsättningsgrad, procent", "TypData": "icke säsongrensad",
             "Alder": "totalt 20–64 år", "InrikesUtrikes": "inrikes födda"}, "innehall": r"."},
    {"fraga": "ekonomi", "namn": "BNP, volymförändring (%)", "tabell": "TAB5621",
     "val": {"Anvandningstyp": "BNP till marknadspris"}, "innehall": r"Volymförändring"},
    {"fraga": "bostad", "namn": "Färdigställda lägenheter i nybyggda hus", "tabell": "TAB2538",
     "val": {"Region": "Riket", "Hustyp": ["flerbostadshus", "småhus"]},
     "innehall": r"^Färdigställda lägenheter"},
    {"fraga": "bostad", "namn": "Fastighetsprisindex småhus (1990=100)", "tabell": "TAB1148",
     "val": {"Lan": "Riket"}, "innehall": r"."},
    {"fraga": "invandring", "namn": "Invandringar", "tabell": "TAB1618",
     "val": {"Medbland": "Totalt", "Kon": ["män", "kvinnor"]}, "innehall": r"^Invandringar$"},
    {"fraga": "sjukvard", "namn": "Medellivslängd vid födseln, kvinnor (år)", "tabell": "TAB5241",
     "val": {"Alder": "0 år", "Kon": "kvinnor"}, "innehall": r"."},
    {"fraga": "sjukvard", "namn": "Medellivslängd vid födseln, män (år)", "tabell": "TAB5241",
     "val": {"Alder": "0 år", "Kon": "män"}, "innehall": r"."},
    {"fraga": "jamstalldhet", "namn": "Kvinnors lön i procent av mäns", "tabell": "TAB5124",
     "val": {}, "innehall": r"."},
    {"fraga": "energi", "namn": "Elproduktion, kärnkraft (GWh/mån)", "tabell": "TAB78",
     "val": {"ProdAnv": "kärnkraft (kondens), netto ", "Elomrade": ["SE1", "SE2", "SE3", "SE4"]},
     "innehall": r"."},
    {"fraga": "klimat", "namn": "Växthusgasutsläpp, Sverige (miljoner ton CO2-ekv., exkl. LULUCF)", "tabell": "TAB4698",
     "val": {"Vaxthusgaser": "Totala Växthusgaser (kt CO2-ekv.)",
             "Sektor": "NATIONELL TOTAL (exklusive LULUCF, exklusive internationella transporter)"},
     "innehall": r".", "skala": 0.001},
    {"fraga": "pension", "namn": "Demografisk försörjningskvot, totalt", "tabell": "TAB4642",
     "val": {"Region": "Riket"}, "innehall": r"^Försörjningskvot totalt"},
    {"fraga": "pension", "namn": "Demografisk försörjningskvot, från äldre 65+", "tabell": "TAB4642",
     "val": {"Region": "Riket"}, "innehall": r"från äldre"},
    # Hämtas från och med nästa körning (kallor.SCB_SOK, steg 3)
    {"fraga": "egen_ekonomi", "namn": "Gini-koefficient, disponibel inkomst", "tabell": "TAB1121",
     "val": {"~^Region": "Riket", "~(?i)inkomst": "~(?i)^disponibel inkomst"}, "innehall": r"(?i)gini"},
    {"fraga": "egen_ekonomi", "namn": "Hushållens skuldkvot (% av disponibel inkomst)", "tabell": "TAB4592",
     "val": {"~(?i)sektor": "~(?i)hushåll", "~(?i)indikator": "~(?i)skuldkvot"}, "innehall": r"."},
]

# Världsbanken (öppet API). Militärutgifterna är SIPRI:s serie.
VARLDSBANKEN = [
    ("forsvar", "Försvarsutgifter, % av BNP (SIPRI)", "MS.MIL.XPND.GD.ZS"),
    ("forsvar", "Försvarsutgifter, % av statens utgifter (SIPRI)", "MS.MIL.XPND.ZS"),
    ("miljo", "Förnybar energi, % av slutlig energianvändning", "EG.FEC.RNEW.ZS"),
    ("miljo", "Luftföroreningar PM2,5, medelexponering (µg/m³)", "EN.ATM.PM25.MC.M3"),
]

RIKSBANKEN = [
    ("egen_ekonomi", "Styrräntan (%)", "SECBREPOEFF"),
]

# Officiella mål. "riktning": åt vilket håll målet pekar. "niva": målnivåer
# (värde, målår eller None, text); den första är den som avståndet räknas mot.
# "kalla": var målet är beslutat. "not": tolkningsförbehåll som visas på sidan.
_VARDGARANTI = "Vårdgarantin, hälso- och sjukvårdslagen (2017:30) 9 kap."
_SYSS = "Den ekonomiska politikens mål om hög och varaktig sysselsättning (budgetpropositionen)"
_KRIM = "Kriminalpolitikens mål: att minska brottsligheten och öka människors trygghet"
_JAMST = "Jämställdhetspolitikens delmål om ekonomisk jämställdhet (prop. 2005/06:155)"
_KLIMAT = "Klimatlagen (2017:720) och klimatmålet: nettonollutsläpp senast 2045"

MAL = {
    "Första kontakt i specialiserad vård inom 90 dagar":
        {"riktning": "hogre", "niva": [(100, None, "alla inom 90 dagar")], "kalla": _VARDGARANTI},
    "Operation/åtgärd inom 90 dagar":
        {"riktning": "hogre", "niva": [(100, None, "alla inom 90 dagar")], "kalla": _VARDGARANTI},
    "Telefonsamtal till primärvården besvarade samma dag":
        {"riktning": "hogre", "niva": [(100, None, "kontakt samma dag")], "kalla": _VARDGARANTI},
    "Barn- och ungdomspsykiatri: första besök inom 90 dagar (%)":
        {"riktning": "hogre", "niva": [(100, None, "alla inom 90 dagar")], "kalla": _VARDGARANTI,
         "not": "Flera regioner har en egen, kortare gräns (30 dagar) för BUP."},
    "Försvarsutgifter, % av BNP (SIPRI)":
        {"riktning": "hogre", "niva": [(2.0, 2024, "Natos riktmärke 2 %"),
                                       (3.5, 2035, "Natos mål från Haag 2025: 3,5 % kärnförsvar")],
         "kalla": "Natoåtagandet (Sverige medlem sedan 2024)",
         "not": "SIPRI räknar försvarsutgifter annorlunda än Nato; nivåerna är inte helt jämförbara."},
    "Offentliga utgifter för försvar, % av BNP (COFOG)":
        {"riktning": "hogre", "niva": [(2.0, 2024, "Natos riktmärke 2 %"),
                                       (3.5, 2035, "Natos mål från Haag 2025: 3,5 % kärnförsvar")],
         "kalla": "Natoåtagandet (Sverige medlem sedan 2024)",
         "not": "COFOG räknar försvarsutgifter annorlunda än Nato; nivåerna är inte helt jämförbara."},
    "Förnybar energi, % av slutlig energianvändning":
        {"riktning": "hogre", "niva": [(65, 2030, "Sveriges bidrag till EU:s förnybartmål"),
                                       (50, 2020, "riksdagens mål 2020")],
         "kalla": "EU:s förnybartdirektiv och Sveriges energi- och klimatplan"},
    "Luftföroreningar PM2,5, medelexponering (µg/m³)":
        {"riktning": "lagre", "niva": [(10, None, "miljömålet Frisk luft, årsmedel")],
         "kalla": "Miljökvalitetsmålet Frisk luft",
         "not": "WHO:s riktvärde från 2021 är 5 µg/m³."},
    "Skyddad natur, andel av landareal (%)":
        {"riktning": "hogre", "niva": [(30, 2030, "30 % skyddat 2030")],
         "kalla": "Kunming–Montreal-ramverket för biologisk mångfald, mål 3",
         "not": "Målet gäller globalt och avser även andra effektiva bevarandeåtgärder."},
    "Växthusgasutsläpp per invånare (ton)": {"riktning": "lagre", "kalla": _KLIMAT},
    "Växthusgasutsläpp totalt (ton)": {"riktning": "lagre", "kalla": _KLIMAT},
    "Växthusgasutsläpp, Sverige (miljoner ton CO2-ekv., exkl. LULUCF)":
        {"riktning": "lagre", "niva": [(0, 2045, "nettonoll 2045")], "kalla": _KLIMAT,
         "not": "Nettonollmålet räknar in upptag i skog och mark och kompletterande åtgärder; "
                "utsläppen här är brutto, utan LULUCF."},
    "Kvinnors mediannettoinkomst i % av mäns":
        {"riktning": "hogre", "niva": [(100, None, "lika inkomster")], "kalla": _JAMST},
    "Kvinnors lön i procent av mäns":
        {"riktning": "hogre", "niva": [(100, None, "lika lön")], "kalla": _JAMST,
         "not": "Skillnaden förklaras till stor del av yrke och sektor; det är inte ett mått på lönediskriminering."},
    "Arbetslöshet 15–74 år (AKU, %)": {"riktning": "lagre", "kalla": _SYSS},
    "Sysselsättningsgrad 15–74 år (AKU, %)": {"riktning": "hogre", "kalla": _SYSS},
    "Arbetslöshet 16–64 år, Arbetsförmedlingen (%)": {"riktning": "lagre", "kalla": _SYSS},
    "Arbetslöshet 20–64 år, registerbaserad (BAS, %)": {"riktning": "lagre", "kalla": _SYSS},
    "Långtidsarbetslösa, andel av arbetslösa (%)": {"riktning": "lagre", "kalla": _SYSS},
    "Skjutningar per år": {"riktning": "lagre", "kalla": _KRIM},
    "Döda i skjutningar per år": {"riktning": "lagre", "kalla": _KRIM},
    "Sprängningar per år": {"riktning": "lagre", "kalla": _KRIM},
    "KPIF, 12-månadersförändring (%)":
        {"riktning": None, "niva": [(2.0, None, "inflationsmålet 2 %")],
         "kalla": "Riksbankens inflationsmål (KPIF)"},
}

# Tolkningsförbehåll för indikatorer utan mål.
NOTER = {
    "Anmälda brott per 100 000 inv": "Fler anmälningar kan betyda fler brott eller att fler brott anmäls.",
    "Anmälda våldsbrott per 100 000 inv": "Fler anmälningar kan betyda fler brott eller att fler brott anmäls.",
    "Meritvärde åk 9": "Stigande meritvärden kan spegla betygsinflation.",
    "Meritvärde åk 9 (hemkommun, 17 ämnen)": "Stigande meritvärden kan spegla betygsinflation.",
    "Färdigställda bostäder, nybyggnad, per 1 000 inv": "Boverket beräknar byggbehovet; det finns inget beslutat mål.",
    "Demografisk försörjningskvot, totalt": "Antal yngre (0–19) och äldre (65+) per 100 personer i åldern "
                                             "20–64. Säger inget om hur många som faktiskt arbetar.",
    "Gini-koefficient, disponibel inkomst": "0 = alla har lika inkomst, 1 = en person har allt.",
    "Total skattesats (%)": "Skattenivån är en politisk avvägning mot välfärdens omfattning.",
    "Kommunal skattesats (%)": "Skattenivån är en politisk avvägning mot välfärdens omfattning.",
}


def mal(indikator: str) -> dict:
    """Mål och förbehåll för en indikator, som kolumner (tomma om mål saknas)."""
    m = MAL.get(indikator, {})
    niva = m.get("niva") or [(None, None, None)]
    return {"mal_riktning": m.get("riktning"), "mal_varde": niva[0][0], "mal_ar": niva[0][1],
            "mal_text": niva[0][2], "mal_kalla": m.get("kalla"),
            "mal_ovriga": "; ".join(f"{t} ({v}{'' if a is None else f', {a}'})" for v, a, t in niva[1:]) or None,
            "not": m.get("not") or NOTER.get(indikator)}
