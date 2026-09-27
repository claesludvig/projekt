"""Källkatalog för väljardatabasen.

Varje post beskriver var en källa finns och hur den ska hämtas. hamta.py läser
bara härifrån, så nya tabeller/rapporter läggs till här.

SCB hämtas via PxWebApi v2 (statistikdatabasen.scb.se/api/v2). Tabeller letas
upp med fritextsökning och filtreras på rubrik, så att koden inte hänger på
SCB:s interna tabell-id:n (TAB1234) som vi inte vet i förväg. Allt som hittas
loggas i data/katalog/scb_katalog.csv.
"""

SCB_API = "https://statistikdatabasen.scb.se/api/v2"

# region: "riket" = bara Riket (kod 00), "kommun" = riket + län + kommuner,
#         "alla" = alla regionvärden. Tabeller utan regionvariabel påverkas inte.
# max_celler: hoppa över tabellen om den blir större (skydd mot jättetabeller).
SCB_SOK = [
    # --- Partisympatiundersökningen (PSU, ME0201): partistöd per grupp, 2 ggr/år
    {"tema": "psu", "sok": "partisympati", "rubrik": r"^Partisympati efter",
     "region": "alla", "max_celler": 400_000},
    {"tema": "psu", "sok": "partisympati", "rubrik": r"^Med partisympati",
     "region": "alla", "max_celler": 400_000},
    {"tema": "psu", "sok": "valresultat om det varit val idag",
     "rubrik": r"(?i)val idag", "region": "alla", "max_celler": 200_000},

    # --- Valdeltagandeundersökningen (ME0105) och registerbaserat deltagande
    {"tema": "valdeltagande", "sok": "valdeltagande riksdagsval",
     "rubrik": r"(?i)valdeltagande", "region": "kommun", "max_celler": 600_000},

    # --- Valresultat (ME0104)
    {"tema": "valresultat", "sok": "riksdagsval valresultat parti",
     "rubrik": r"(?i)riksdagsval.*(parti|valresultat)|valresultat.*riksdag",
     "region": "kommun", "max_celler": 600_000},

    # --- Befolkning (BE0101)
    {"tema": "befolkning", "sok": "folkmängden efter region ålder kön",
     "rubrik": r"(?i)^folkmängden efter region, ålder och kön",
     "region": "riket", "max_celler": 600_000},
    {"tema": "befolkning", "sok": "utländsk bakgrund",
     "rubrik": r"(?i)(utländsk|svensk).*bakgrund", "region": "kommun",
     "max_celler": 600_000},
    {"tema": "befolkning", "sok": "utrikes födda födelseland",
     "rubrik": r"(?i)utrikes födda.*(region|födelseland)", "region": "riket",
     "max_celler": 600_000},

    # --- Utbildning (UF0506)
    {"tema": "utbildning", "sok": "utbildningsnivå befolkning",
     "rubrik": r"(?i)^befolkning.*utbildningsnivå", "region": "kommun",
     "max_celler": 900_000},

    # --- Inkomst (HE0110, HE0103)
    {"tema": "inkomst", "sok": "sammanräknad förvärvsinkomst",
     "rubrik": r"(?i)sammanräknad förvärvsinkomst", "region": "kommun",
     "max_celler": 900_000},
    {"tema": "inkomst", "sok": "disponibel inkomst",
     "rubrik": r"(?i)disponibel inkomst", "region": "kommun",
     "max_celler": 900_000},
    {"tema": "inkomst", "sok": "låg ekonomisk standard",
     "rubrik": r"(?i)ekonomisk standard", "region": "kommun",
     "max_celler": 600_000},

    # --- Arbetsmarknad
    {"tema": "arbete", "sok": "förvärvsarbetande sysselsättningsgrad",
     "rubrik": r"(?i)sysselsättningsgrad|förvärvsarbetande.*region",
     "region": "kommun", "max_celler": 600_000},

    # --- Levnadsförhållanden: utsatthet för brott, trygghet (ULF/SILC, LE0101)
    {"tema": "brott", "sok": "utsatthet för brott",
     "rubrik": r"(?i)brott|våld|hot|stöld|trygghet|säkerhet", "region": "alla",
     "max_celler": 600_000},
    {"tema": "brott", "sok": "trygghet oro",
     "rubrik": r"(?i)trygghet|oro|otrygg", "region": "alla",
     "max_celler": 600_000},
    # --- Priser: KPI per produktgrupp (el, drivmedel m.m.) och elpriser
    {"tema": "priser", "sok": "konsumentprisindex produktgrupp",
     "rubrik": r"(?i)konsumentprisindex.*(produktgrupp|COICOP).*månad", "region": "alla",
     "exkludera": r"(?i)fastställda|kvartal|vikter", "max_celler": 600_000, "max_tabeller": 3},
    {"tema": "priser", "sok": "KPIF",
     "rubrik": r"(?i)KPIF.*månad", "region": "alla", "max_celler": 100_000, "max_tabeller": 2},
    {"tema": "priser", "sok": "elpriser",
     "rubrik": r"(?i)elpris", "region": "alla", "max_celler": 200_000, "max_tabeller": 4},
    # --- Bilinnehav per kommun (drivmedelsexponering)
    {"tema": "bil", "sok": "personbilar folkbokförda personer",
     "rubrik": r"(?i)personbilar.*(folkbokförda|region)", "region": "kommun", "max_celler": 300_000,
     "exkludera": r"(?i)deso|regso"},
    {"tema": "levnad", "sok": "ekonomisk utsatthet",
     "rubrik": r"(?i)ekonomisk utsatthet", "region": "alla",
     "max_celler": 600_000},
]

# Tabeller som inte ska hämtas trots att rubriken matchar (skolstatistik,
# barnundersökningar, hushållsutgifter m.m. som dyker upp i fritextsökningen).
SCB_EXKLUDERA = (r"(?i)elever|gymnasie|barn och unga|hemmaboende|studiedeltagande|"
                 r"studiemedel|utgifter för hushåll|EU-sympati|euro-?sympati|nato-sympati|"
                 r"förändring av inkomstgrupp|barns trygghet|boendeutgift|konsumtionsutrymme|"
                 r"ungdomars etablering|nybörjare|medborgare boende utomlands")

# Tabeller som hämtas med känt id. "utelamna": variabler som summeras bort
# (SCB eliminerar dem), för att hålla stora tabeller under cellgränsen.
SCB_TABELLER = [
    # DeSO 2025 (ca 6 000 områden) för koppling till valdistrikt. Samma tabeller
    # som per kommun, men bara DeSO-koder och senaste året. Sparas som <id>_deso.
    *[{"id": t, "tema": "deso", "region": "deso", "senaste": 1, "suffix": "_deso",
       "max_celler": 3_000_000, "not": n} for t, n in [
        ("TAB6571", "DeSO: utländsk/svensk bakgrund och kön"),
        ("TAB6574", "DeSO: ålder och kön"),
        ("TAB6534", "DeSO: utbildningsnivå 25–65 år"),
        ("TAB6685", "DeSO: låg och hög ekonomisk standard"),
        ("TAB6572", "DeSO: födelseregion"),
        ("TAB6253", "DeSO: upplåtelseform"),
        ("TAB6680", "DeSO: arbetsmarknadsstatus")]],
    {"id": "TAB5160", "tema": "priser", "region": "alla", "max_celler": 2_000_000,
     "not": "KPI efter produktgrupp, 1980=100, månad 1980–2025 (el, drivmedel, livsmedel m.m.)"},
    {"id": "TAB3981", "tema": "utbildning", "region": "kommun",
     "utelamna": ["Alder", "Kon"], "max_celler": 600_000,
     "not": "Befolkning 16–74 år efter region och utbildningsnivå 1985–"},
    {"id": "TAB6089", "tema": "brott", "region": "alla", "max_celler": 600_000,
     "not": "ULF/SILC: otrygghet efter indikator, redovisningsgrupp och kön 2008–"},
    {"id": "TAB5864", "tema": "brott", "region": "riket", "max_celler": 600_000,
     "not": "Medborgarundersökningen: syn på trygghet efter region och bakgrund"},
]

# Geodata. "url": direkta kandidater, "sida"+"lank": skrapa länkar,
# "github": (repo, sökvägsmönster) som reserv. Första som går att hämta används.
GEODATA = [
    {"id": "deso_2025",
     "url": ["https://geodata.scb.se/geoserver/stat/wfs?service=WFS&REQUEST=GetFeature&version=1.1.0"
             "&TYPENAMES=stat:DeSO_2025&outputFormat=geopackage"]},
    {"id": "valdistrikt_2026",
     "sida": "https://www.val.se/valresultat-och-statistik/statistik-och-data/radata-val-2026",
     "lank": r"(?i)(valdistrikt|valgeografi|geodata|geografi).*\.(zip|geojson|json|gpkg)",
     "alla": True,   # en fil per län: hämta alla och slå ihop
     "github": [("lama77se/valvaka-2026", r"valdistrikt.*\.geojson$"),
                ("pgronberg/valvaka", r"valdistrikt.*\.(geo|topo)?json$"),
                ("sebdanielsson/election-map-sweden", r"valdistrikt.*2026.*\.(geo)?json$")]},
]

# Dokument (PDF) som laddas ned och textextraheras. Text sparas sida för sida
# i data/kallor/txt så att tabellerna kan tolkas och verifieras.
DOKUMENT = [
    # SVT:s vallokalsundersökning (Valu). Innehåller tabeller över partival per
    # väljargrupp (kön, ålder, yrke, ursprung m.m.), ofta med jämförelseår.
    {"id": "valu_rd_2014_2018", "typ": "valu",
     "url": "https://omoss.svt.se/download/18.2b162e85172e510106a44061/1595419616898/valuresultat_riksdagsval_pk_2018_vagda_0912.pdf"},
    {"id": "valu_rd_2014_2022", "typ": "valu",
     "url": "https://omoss.svt.se/download/18.69f812fb18327382298d3e8a/1663746207468/valu_riksdagsval_2022_viktat_0921_V3.pdf"},
    {"id": "valu_rd_2026_seminarium", "typ": "valu",
     "url": "https://omoss.svt.se/download/18.c7d6c981a0a583535d1535/1789484134179/Valu%202026%20seminarium%20260915.pdf"},
    {"id": "valu_ep_2024", "typ": "valu",
     "url": "https://omoss.svt.se/download/18.273015e218fe7d3833535561/1718110247331/ValuResultat_EUval_2024.pdf"},
    # Valforskningsprogrammet (Svenska väljare), Göteborgs universitet
    {"id": "gu_valu_1991_2022", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2023-01/R23_2.pdf"},
    {"id": "gu_konsskillnader_1921_2022", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2023-11/2023_9.pdf"},
    {"id": "gu_hur_rostar_folk_2022", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2022-06/2022_7_Hur_rostar_folk_1.pdf"},
    {"id": "gu_lyssna_pa_valjarna_2018", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2020-03/Holmberg,%20Na%CC%88sman,%20Oscarsson%20&%20Gudmundson%20-%20Lyssna%20pa%CC%8A%20va%CC%88ljarna%20-%20SVT%20VALU-%20Val%202018,%20EU%20Val%202019%20(2020).pdf"},
    {"id": "gu_faktablad_F2023_12", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2023-03/F2023_12.pdf"},
    # SOM-institutet: långa tidsserier, bl.a. viktigaste samhällsproblem 1987–
    {"id": "som_trender_1986_2025", "typ": "som",
     "url": "https://www.gu.se/sites/default/files/2026-03/Svenska%20trender%201986-2025.pdf"},
    {"id": "som_trender_1986_2022", "typ": "som",
     "url": "https://www.gu.se/sites/default/files/2023-04/1.%20Svenska%20trender%201986-2022.pdf"},
    {"id": "gu_vansterpartiet_2025", "typ": "svenska_valjare",
     "url": "https://www.gu.se/sites/default/files/2025-09/R2025_8_V%C3%A4nsterpartiet.pdf"},
]

# Webbsidor som skrapas efter länkar till fler dokument (pdf/xlsx).
# Matchande länkar laddas ned som DOKUMENT (pdf) eller EXCEL (xlsx).
LANKSIDOR = [
    {"id": "gu_faktablad_2023", "typ": "svenska_valjare",
     "url": "https://www.gu.se/valforskningsprogrammet/resultat-och-publikationer/faktablad/faktablad-2023",
     "lank": r"\.pdf", "max": 40},
    {"id": "gu_rapporter", "typ": "svenska_valjare",
     "url": "https://www.gu.se/valforskningsprogrammet/resultat-och-publikationer/rapporter",
     "lank": r"\.pdf", "max": 40},
    {"id": "svt_valu_2026", "typ": "valu",
     "url": "https://omoss.svt.se/arkiv/nyhetsarkiv/2026-09-15-svts-vallokalsundersokning---valu-2026.html",
     "lank": r"\.(pdf|xlsx?)", "max": 10},
    {"id": "bra_ntu_utsatthet", "typ": "bra_ntu",
     "url": "https://bra.se/statistik/statistik-fran-enkatundersokningar/nationella-trygghetsundersokningen/utsatthet-for-brott",
     "lank": r"\.xlsx?", "max": 10},
    {"id": "bra_ntu", "typ": "bra_ntu",
     "url": "https://bra.se/statistik/statistik-fran-enkatundersokningar/nationella-trygghetsundersokningen",
     "lank": r"\.xlsx?", "max": 10},
    # Polisen: skjutningar och sprängningar per polisregion och månad, en pdf per år
    {"id": "polisen", "typ": "polisen",
     "url": "https://polisen.se/om-polisen/polisens-arbete/sprangningar-och-skjutningar/",
     "folj": r"(?i)sprangningar-och-skjutningar/|skjutningar|sprangningar|statistik",
     "lank": r"(?i)(skjutningar|sprangningar|explosion|detonation).*\.pdf", "max": 40, "alltid": True},
    {"id": "bra_sprangningar", "typ": "bra",
     "url": "https://bra.se/nyheter/arkiv/2026-03-04-statistik-om-sprangningar",
     "lank": r"(?i)\.(xlsx?|pdf)", "max": 6},
    {"id": "val_radata_2026", "typ": "valmyndigheten",
     "url": "https://www.val.se/valresultat-och-statistik/statistik-och-data/radata-val-2026",
     "lank": r"(?i)(slutlig|riksdag).*\.(xlsx|csv|zip)", "max": 6},
]
