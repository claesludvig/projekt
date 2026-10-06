"""Aktörer i bostadsbyggandet och dess finansiering, med historiska namn.

Varje grupp har ett mönster som matchas mot normaliserad text (gemener,
avstavning ihopslagen). Organisationerna har bytt namn många gånger; alla
kända namn står i samma grupp, t.ex. Svenska byggnadsentreprenörföreningen
(till 1968), Svenska byggnadsindustriförbundet, Byggentreprenörerna, Sveriges
Byggindustrier och Byggföretagen.

BRANSCH anger vilka grupper som räknas som branschaktörer.
"""

import re

GRUPPER = [
    ("bygg", "Byggföretag", [
        r"byggnadsentreprenörfören", r"byggnadsentreprenörsfören", r"byggentreprenörerna",
        r"sveriges byggindustrier", r"byggföretagen", r"byggnadsindustriförbund",
        r"byggnadsindustrins centralorganisation", r"näringslivets byggnadsdelegation",
        r"byggmästarefören", r"byggmästarfören", r"byggherrarna", r"småhusindustri",
        r"trähusindustri", r"trähusfabrikerna", r"monteringsfärdiga hus", r"bostadsgaranti",
        r"byggmaterialindustri", r"byggmaterialproducent", r"skånska cementgjuteriet",
        r"\bskanska\b", r"\bncc\b", r"\bjm\b", r"armerad betong", r"\babv\b",
        r"\bbi\b(?= |,|\))", r"träindustrin", r"svenskt trä\b", r"\bbyggherre\w*fören",
    ]),
    ("fast", "Fastighetsägare", [
        r"fastighetsägareförbund", r"fastighetsägarefören", r"fastighetsägarförbund",
        r"fastighetsägarna", r"sveriges fastighetsägare", r"fastighetsägarnas riksförbund",
        r"fastighetsbranschen", r"\bbyggherrarna\b",
    ]),
    ("allm", "Allmännyttan och kooperationen", [
        r"allmännyttiga bostadsföretag", r"\bsabo\b", r"sveriges allmännytta",
        r"\bhsb\b", r"hyresgästernas sparkasse", r"riksbyggen", r"bostadsrätterna",
        r"kooperativa bostadsfören", r"bostadsföreningars centralfören",
        r"bostadsrättsföreningars centralorganisation", r"\bsbc\b", r"kommunalekonomiska fören",
    ]),
    ("hyr", "Hyresgäster", [
        r"hyresgästernas riksförbund", r"hyresgästföreningen", r"hyresgästförbund",
        r"hyresgästföreningarnas",
    ]),
    ("villa", "Villaägare och småhusägare", [
        r"villaägarnas riksförbund", r"villaägareförbund", r"villaägarförbund",
        r"egnahemsägarnas", r"egnahemsfören",
    ]),
    ("bank", "Banker och bostadsinstitut", [
        r"bankfören", r"sparbanksfören", r"sparbankernas", r"stadshypotek",
        r"bostadskreditinstitut", r"bostadsinstitut", r"svensk fastighetskredit", r"\bspintab\b",
        r"\bsbab\b", r"statens bostadsfinansieringsaktiebolag", r"försäkringsbolags riksförbund",
        r"svensk försäkring", r"bostadskreditkass", r"hypoteksfören", r"landshypotek",
        r"finansbolagens fören", r"fondhandlarefören", r"bankernas", r"föreningsbankerna",
        r"svenska bankers", r"\bswedbank\b", r"\bnordea\b", r"handelsbanken", r"\bseb\b",
    ]),
    ("fack", "Fackliga organisationer", [
        r"landsorganisationen", r"\blo\b", r"tjänstemännens centralorganisation", r"\btco\b",
        r"\bsaco\b", r"byggnadsarbetareförbund", r"svenska byggnadsarbetare",
        r"\bbyggnads\b(?= anser| har| framhåller| menar| föreslår| tillstyrker| avstyrker)",
    ]),
    ("narings", "Arbetsgivare och näringsliv", [
        r"arbetsgivarefören", r"\bsaf\b", r"industriförbund", r"svenskt näringsliv",
        r"handelskammare", r"företagarna", r"företagarnas riksorganisation",
    ]),
    ("kommun", "Kommuner", [
        r"kommunförbund", r"stadsförbund", r"landskommunernas förbund",
        r"sveriges kommuner och regioner", r"sveriges kommuner och landsting", r"\bskr\b", r"\bskl\b",
    ]),
    ("myn", "Myndigheter och Riksbanken", [
        r"bostadsstyrelsen", r"boverket", r"planverket", r"byggnadsstyrelsen", r"riksbanksfullmäktige",
        r"riksbanken", r"konjunkturinstitutet", r"finansinspektionen", r"bankinspektionen",
        r"statskontoret", r"bostadskreditnämnd", r"statens hyresråd", r"länsbostadsnämnd",
        r"riksgäldskontoret", r"konkurrensverket", r"näringsfrihetsombudsmannen",
        r"pris- och kartellnämnd", r"byggforskningsrådet", r"institut för byggnadsforskning",
        r"arbetsmarknadsstyrelsen", r"\bams\b",
    ]),
]

BRANSCH = {"bygg", "fast", "allm", "villa", "bank"}
NAMN = {k: n for k, n, _ in GRUPPER}
_MONSTER = [(k, re.compile("|".join(f"(?:{p})" for p in ps))) for k, _, ps in GRUPPER]
_NAGON = re.compile("|".join(p.pattern for _, p in _MONSTER))

# Ord som visar att ett stycke redovisar en ståndpunkt och inte bara räknar upp
# remissinstanser.
_STALLNING = re.compile(
    r"\banser\b|\bmenar\b|\bframhåller\b|\bföreslår\b|\btillstyrker\b|\bavstyrker\b|\bvänder sig\b|"
    r"\bpåpekar\b|\bunderstryker\b|\bbetonar\b|\bförordar\b|\bmotsätter\b|\bkritiserar\b|"
    r"\bvill\b|\bbegär\b|\bpekar på\b|\bifrågasätter\b|\bvarnar\b|\banför\b|\bhävdar\b|"
    r"\binvänder\b|\bdelar\b|\bgodtar\b|\bmotsätter sig\b|\bhar ingen erinran\b|\binstämmer\b|"
    r"\benligt\b|\bsärskilt yttrande\b|\breservation\b")


def grupper_i(text_lower):
    """Grupper som nämns i en text (gemener)."""
    return [k for k, p in _MONSTER if p.search(text_lower)]


def grupp_for_organisation(namn):
    """Grupp för en remissinstans (namnet på remissvaret)."""
    low = namn.lower()
    g = grupper_i(low)
    if g:
        return g[0]
    if re.search(r"kommun\b|\bstad\b|region\b|landsting", low):
        return "kommun"
    if re.search(r"länsstyrelse|verket\b|myndighet|nämnd\b|domstol|tingsrätt|hovrätt|inspektion|kollegium|"
                 r"ombudsman|rådet\b|institut\b|universitet|högskola|lantmäteri", low):
        return "myn"
    return "ovr"


def stallningstagande(text_lower):
    """Grupper vars ståndpunkt redovisas i stycket. Långa uppräkningar av
    remissinstanser (många grupper, inget ställningsord) räknas inte."""
    if not _STALLNING.search(text_lower) or not _NAGON.search(text_lower):
        return []
    g = grupper_i(text_lower)
    if len(g) >= 5 and len(text_lower) < 120 * len(g):
        return []
    return g
