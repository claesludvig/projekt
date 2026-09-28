"""Sakfördjupning per område: Sverige över tid, Norden, beslut, opinion och kunskapsläge.

Varje område samlar indikatorer som redan finns i databasen (verklighet,
lägesbild), jämförbara serier för de nordiska länderna från Eurostat,
riksdagens beslut och SOM-förslag i samma frågor, myndigheter som utvärderar
området och de kunskapsluckor som öppna data inte täcker.

EUROSTAT: (id, dataset, filter, namn, enhet). Filtren låser alla dimensioner
utom land och tid; dimensioner som inte anges får sitt totalvärde. Serierna
hämtas för LANDER och EU-snittet (hamta.py) och tolkas i bygg_db.py.
"""

LANDER = {"SE": "Sverige", "DK": "Danmark", "FI": "Finland", "NO": "Norge", "IS": "Island",
          "EU27_2020": "EU-snitt"}

EUROSTAT = [
    # Rättsväsende
    ("mord", "crim_off_cat", {"iccs": "ICCS0101", "unit": "P_HTHAB"}, "Dödligt våld per 100 000 inv", "per 100 000"),
    ("polis", "crim_just_job", {"isco08": "OC5412", "unit": "P_HTHAB", "sex": "T"},
     "Poliser per 100 000 inv", "per 100 000"),
    ("fangar", "crim_pris_cap", {"indic_cr": "PRIS_ACT_CAP", "unit": "P_HTHAB"}, "Intagna i fängelse per 100 000 inv", "per 100 000"),
    ("ordning_bnp", "gov_10a_exp", {"cofog99": "GF03", "na_item": "TE", "sector": "S13", "unit": "PC_GDP"},
     "Offentliga utgifter för ordning och säkerhet, % av BNP", "% av BNP"),
    # Vård
    ("vardplatser", "hlth_rs_bds1", {"facility": "HBEDT", "unit": "P_HTHAB"},
     "Vårdplatser på sjukhus per 100 000 inv", "per 100 000"),
    ("vantan", "hlth_silc_08", {"reason": "WLIST", "quant_inc": "TOTAL", "sex": "T", "age": "Y_GE16", "unit": "PC"},
     "Avstått från vård på grund av väntetid (%, 16+)", "%"),
    ("halsa_bnp", "gov_10a_exp", {"cofog99": "GF07", "na_item": "TE", "sector": "S13", "unit": "PC_GDP"},
     "Offentliga utgifter för hälso- och sjukvård, % av BNP", "% av BNP"),
    ("livslangd", "demo_mlexpec", {"sex": "T", "age": "Y_LT1", "unit": "YR"}, "Medellivslängd vid födseln (år)", "år"),
    # Energi
    ("elpris_hush", "nrg_pc_204", {"nrg_cons": "KWH2500-4999", "unit": "KWH", "tax": "I_TAX",
                                   "currency": "EUR"}, "Elpris för hushåll, inkl. skatter (euro/kWh)", "euro/kWh"),
    ("fornybart", "nrg_ind_ren", {"nrg_bal": "REN", "unit": "PC"}, "Förnybar energi, % av slutlig användning", "%"),
    ("importberoende", "nrg_ind_id", {"siec": "TOTAL", "unit": "PC"}, "Energiimportberoende (%)", "%"),
    # Försvar
    ("forsvar_bnp", "gov_10a_exp", {"cofog99": "GF02", "na_item": "TE", "sector": "S13", "unit": "PC_GDP"},
     "Offentliga utgifter för försvar, % av BNP (COFOG)", "% av BNP"),
    # Integration
    ("syss_utrikes", "lfsa_ergacob", {"sex": "T", "age": "Y20-64", "c_birth": "FOR", "unit": "PC"},
     "Sysselsättningsgrad 20–64, utrikes födda (%)", "%"),
    ("syss_inrikes", "lfsa_ergacob", {"sex": "T", "age": "Y20-64", "c_birth": "NAT", "unit": "PC"},
     "Sysselsättningsgrad 20–64, inrikes födda (%)", "%"),
    ("asyl", "migr_asyappctza", {"citizen": "EXT_EU27_2020", "applicant": "FRST", "sex": "T", "age": "TOTAL", "unit": "PER"},
     "Förstagångsansökningar om asyl", "antal"),
    ("befolkning", "demo_gind", {"indic_de": "JAN"}, "Folkmängd 1 januari", "personer"),
    ("arbetsloshet", "une_rt_a", {"age": "Y15-74", "sex": "T", "unit": "PC_ACT"}, "Arbetslöshet 15–74 (%)", "%"),
]

# Beräknade serier: (id, namn, enhet, funktion av serierna)
BERAKNADE = [
    ("asyl_per_100k", "Förstagångsansökningar om asyl per 100 000 inv", "per 100 000",
     lambda s: 1e5 * s["asyl"] / s["befolkning"]),
    ("syss_gap", "Sysselsättningsgap inrikes minus utrikes födda (e.)", "procentenheter",
     lambda s: s["syss_inrikes"] - s["syss_utrikes"]),
]

OMRADEN = [
    {"id": "rattsvasende", "namn": "Rättsväsendet", "fragor": ["lag"],
     "intro": "Grovt våld, rättsväsendets kapacitet och tryggheten. Polisens och Brås siffror för Sverige, "
              "Eurostats för jämförelsen med Norden.",
     "sverige": ["Skjutningar per år", "Döda i skjutningar per år", "Sprängningar per år",
                 "Anmälda brott per 100 000 inv", "Anmälda våldsbrott per 100 000 inv",
                 "Otrygga vid utevistelse sen kväll i eget område, NTU (%)"],
     "lage": ["skjutningar", "sprangningar"],
     "norden": ["mord", "polis", "fangar", "ordning_bnp"],
     "myndigheter": [("Brottsförebyggande rådet (Brå)", "https://bra.se", "kriminalstatistik, NTU, utvärderingar"),
                     ("Polismyndigheten", "https://polisen.se", "skjutningar och sprängningar, lägesbilder"),
                     ("Kriminalvården", "https://www.kriminalvarden.se", "beläggning och platser"),
                     ("Riksrevisionen", "https://www.riksrevisionen.se", "granskningar av rättsväsendet")],
     "luckor": ["Uppklaringsandel och lagföring (Brå) finns inte i öppet API och ingår inte ännu.",
                "Kriminalvårdens beläggningsgrad och platsbrist saknas.",
                "Dödligt våld jämförs mellan länder med olika registrering; nivåskillnader ska tolkas försiktigt."]},
    {"id": "vard", "namn": "Vården", "fragor": ["sjukvard", "aldre"],
     "intro": "Tillgänglighet (vårdgarantin), kapacitet och resultat. Kolada för regioner och riket, "
              "Eurostat för Norden.",
     "sverige": ["Första kontakt i specialiserad vård inom 90 dagar", "Operation/åtgärd inom 90 dagar",
                 "Telefonsamtal till primärvården besvarade samma dag",
                 "Barn- och ungdomspsykiatri: första besök inom 90 dagar (%)",
                 "Rimlig väntetid till sjukhusvård, enligt invånarna (%)",
                 "Invånare med bra självskattat hälsotillstånd (%)",
                 "Medellivslängd vid födseln, kvinnor (år)", "Medellivslängd vid födseln, män (år)"],
     "lage": [],
     "norden": ["vardplatser", "vantan", "halsa_bnp", "livslangd"],
     "myndigheter": [("Myndigheten för vård- och omsorgsanalys", "https://www.vardanalys.se", "utvärderingar av vården"),
                     ("Socialstyrelsen", "https://www.socialstyrelsen.se", "statistik och öppna jämförelser"),
                     ("Sveriges Kommuner och Regioner, Väntetider i vården", "https://www.vantetider.se",
                      "väntetider per region och månad")],
     "luckor": ["Väntetider per månad (SKR) och vårdplatser per region ingår inte ännu.",
                "Personalbrist och bemanning saknas.",
                "Äldreomsorgens kvalitet mäts bara med väntetid och nöjdhet."]},
    {"id": "energi", "namn": "Energin", "fragor": ["energi", "klimat"],
     "intro": "Priser för hushållen, elproduktion och klimatmålen. SCB och Kolada för Sverige, Eurostat för Norden.",
     "sverige": ["Elpris egnahem (KPI, 1980=100)", "Elproduktion, kärnkraft (GWh/mån)",
                 "Växthusgasutsläpp, Sverige (miljoner ton CO2-ekv., exkl. LULUCF)",
                 "Växthusgasutsläpp per invånare (ton)", "Förnybar energi, % av slutlig energianvändning",
                 "Slutanvändning av el (MWh/inv)"],
     "lage": ["pris_el"],
     "norden": ["elpris_hush", "fornybart", "importberoende"],
     "myndigheter": [("Energimyndigheten", "https://www.energimyndigheten.se", "energistatistik och prognoser"),
                     ("Energimarknadsinspektionen", "https://ei.se", "elpriser och elmarknaden"),
                     ("Svenska kraftnät", "https://www.svk.se", "effektbalans och elnät"),
                     ("Klimatpolitiska rådet", "https://www.klimatpolitiskaradet.se", "årlig granskning mot klimatmålen")],
     "luckor": ["Elpris per elområde och timme ingår inte; KPI och Eurostat visar hushållens genomsnitt.",
                "Effektbalans och risk för effektbrist saknas.",
                "Etappmålet för 2030 (utsläpp utanför EU:s handelssystem) är inte beräknat; 2045 visas som nettonoll."]},
    {"id": "forsvar", "namn": "Försvaret", "fragor": ["forsvar"],
     "intro": "Resurser till försvaret mot Natoåtagandet. SIPRI (via Världsbanken) och Eurostat (COFOG).",
     "sverige": ["Försvarsutgifter, % av BNP (SIPRI)", "Försvarsutgifter, % av statens utgifter (SIPRI)"],
     "lage": [],
     "norden": ["forsvar_bnp"],
     "myndigheter": [("Totalförsvarets forskningsinstitut (FOI)", "https://www.foi.se", "analyser av försvarsekonomi"),
                     ("Försvarsmakten", "https://www.forsvarsmakten.se", "budgetunderlag och årsredovisning"),
                     ("Riksrevisionen", "https://www.riksrevisionen.se", "granskningar av försvarets materielförsörjning")],
     "luckor": ["Personal, värnpliktiga och materielleveranser saknas; bara pengar mäts.",
                "Det civila försvaret (beredskapslager, skyddsrum, kommunernas förmåga) ingår inte.",
                "COFOG och SIPRI räknar olika; ingen av dem följer exakt Natos definition."]},
    {"id": "integration", "namn": "Integrationen", "fragor": ["invandring", "jobb"],
     "intro": "Invandring och etablering på arbetsmarknaden. SCB, Kolada och Migrationsverket för Sverige, "
              "Eurostat för Norden.",
     "sverige": ["Invandringar", "Sysselsättningsgrad utrikes födda 20–64 (AKU, %)",
                 "Sysselsättningsgrad inrikes födda 20–64 (AKU, %)",
                 "Arbetslöshet bland utrikes födda 20–64 år (BAS, %)", "Utrikes födda (% av bef.)",
                 "Förvärvsarbetande flyktingar och anhöriga 20–64 år (%)",
                 "Nyanlända i arbete eller studier 90 dagar efter etableringsuppdraget (%)"],
     "lage": ["invandringar", "ut_totalt", "ut_skydd", "ut_anknytning", "ut_arbete", "ut_studier"],
     "norden": ["asyl_per_100k", "syss_utrikes", "syss_gap", "arbetsloshet"],
     "myndigheter": [("Institutet för arbetsmarknads- och utbildningspolitisk utvärdering (IFAU)", "https://www.ifau.se",
                      "effektutvärderingar av etableringsinsatser"),
                     ("Migrationsverket", "https://www.migrationsverket.se", "asyl, uppehållstillstånd, handläggningstider"),
                     ("Arbetsförmedlingen", "https://arbetsformedlingen.se", "etableringsprogrammet")],
     "luckor": ["Återvändande och handläggningstider saknas.",
                "Etablering efter vistelsetid (hur det går efter 2, 5, 10 år) ingår inte.",
                "Boendesegregation och utsatta områden saknas."]},
]
