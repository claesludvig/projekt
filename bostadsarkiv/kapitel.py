"""Kapitlet om kreditpolitiken och bostadsfinansieringen: avsnitt som filter.

En källa hör till ett avsnitt om den ligger inom avsnittets år och texten
träffar något av avsnittets mönster (gemener, sammansättningar träffas).
En källa kan höra till flera avsnitt. Avsnitt 9 (avslutningen) har inget eget
filter; den knyter ihop avsnitt 2 och 8.

Ändra fritt; kör sedan python bygg_webb.py och publicera sidan igen.
"""

AVSNITT = [
    {
        "nr": 1, "namn": "Kreditpolitikens återkomst", "fran": 2008, "till": 2026,
        "mönster": r"kreditpolitik|kreditgaranti|statliga lån|gröna lån|riksbank|styrränt|"
                   r"amorteringskrav|bolånetak|finansinspektion|makrotillsyn|europeiska centralbanken|"
                   r"bank of england|räntehöjning|ränteuppgång|stigande räntor",
    },
    {
        "nr": 2, "namn": "Bostadsbyggandets räntekänslighet", "fran": 1939, "till": 2026,
        "mönster": r"räntekänslig|räntenivå|räntehöjning|räntesänkning|ränteläge|ränteutveckling|"
                   r"räntekostnad|kapitalkostnad|höga räntor|låga räntor|högre räntor|lägre räntor|"
                   r"ränteskydd|räntefri|realränt",
    },
    {
        "nr": 3, "namn": "Kreditpolitik under efterkrigstiden", "fran": 1945, "till": 1985,
        "mönster": r"kreditpolitik|kreditreglering|kreditransonering|lågräntepolitik|räntereglering|"
                   r"penningpolitik|riksbanksfullmäktige|riksbanken|kreditrestriktion|utlåningstak|"
                   r"kreditmarknad|bankernas utlåning",
    },
    {
        "nr": 4, "namn": "Rötterna 1939–1944", "fran": 1939, "till": 1944,
        "mönster": r"räntegaranti|garantiränt|hyresreglering|hyresstopp|hyreskontroll|tertiärlån|"
                   r"sekundärlån|statliga lån|bostadslån|bostadsbyggnadslån|ohlin|bostadsbygg|"
                   r"bostadsproduktion|byggnadsverksamhet",
    },
    {
        "nr": 5, "namn": "Systemet byggs upp, 1945–1960", "fran": 1945, "till": 1960,
        "mönster": r"bostadssociala utredningen|tertiärlån|sekundärlån|räntegaranti|garantiränt|"
                   r"byggnadsreglering|byggnadstillstånd|igångsättningstillstånd|byggnadskvot|startkvot|"
                   r"allmännytt|kooperativ|hsb|riksbyggen|statliga (?:bostads)?lån|lånebestämmelse|"
                   r"kreditpolitik|lågräntepolitik|räntepolitik|bostadsstyrelsen",
    },
    {
        "nr": 6, "namn": "Placeringsplikt och miljonprogram, 1960–1975", "fran": 1960, "till": 1975,
        "mönster": r"placeringsplikt|placeringskvot|placeringskrav|likviditetskvot|prioriterade sektor|"
                   r"ap-fond|allmänna pensionsfond|pensionsfonden|\batp\b|miljonprogram|en miljon (?:nya |)"
                   r"(?:bostäder|lägenheter)|bostadsobligation|bostadsinstitut|kreditinstitut|"
                   r"bostadsbyggnadsprogram|bostadsbyggnadsutredningen",
    },
    {
        "nr": 7, "namn": "Från kreditstyrning till subventioner, 1975–1985", "fran": 1975, "till": 1985,
        "mönster": r"räntebidrag|räntesubvention|garantiränt|inflation|nominell|placeringskrav|"
                   r"placeringsplikt|grå marknad|gråa marknad|grå kreditmarknad|penningmarknad|"
                   r"bankcertifikat|statsskuldväxl|bostadsfinansiering",
    },
    {
        "nr": 8, "namn": "Avregleringen", "fran": 1983, "till": 1996,
        "mönster": r"avreglering|utlåningstak|kreditexpansion|bankkris|finanskris|fastighetskris|"
                   r"räntebidrag|nya bostadsfinansieringssystem|bostadsfinansiering|"
                   r"placeringsplikt|kreditmarknad|räntegaranti",
    },
]
