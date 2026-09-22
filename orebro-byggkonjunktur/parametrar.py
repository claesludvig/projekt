"""
Parametrar och antaganden for analysen av byggkonjunkturen i Orebro lan.

Varje parameter har en status:
  HAMTAD   - hamtas fran SCB via hamta_scb.py och skrivs over vid korning
  ANKARE   - publicerad siffra fran namngiven kalla
  ANTAGET  - kalibrerat antagande, varieras i kansligheten

Alla belopp i loepande priser om inget annat anges.
"""

# ---------------------------------------------------------------------------
# 1. Struktur: Orebro lan
# ---------------------------------------------------------------------------

BEFOLKNING_LAN = 308_362          # ANKARE  Region Orebro lan, 2025
BEFOLKNINGSANDEL_RIKET = 0.0290   # ANKARE  308 362 / ~10,6 mn

# Lanets andel av rikets byggsysselsattning. Byggandelen av sysselsattningen i
# Orebro lan ligger nara riksgenomsnittet; lanet ar overrepresenterat i logistik
# och tillverkning snarare an i bygg.
ANDEL_AV_RIKETS_BYGGSYSSELSATTNING = 0.0275   # ANTAGET (HAMTAD ersatter)

# ---------------------------------------------------------------------------
# 2. Byggsysselsattning, riket (SNI 41-43)
# ---------------------------------------------------------------------------
# Serierna skiljer sig kraftigt at beroende pa definition:
#   SCB BAS/RAMS "sysselsatta inom byggverksamhet"   ~382 000 (2023)
#   Byggforetagen "bygg- och anlaggningsbranschen"   328 800 (2022) -> 312 400 (2024)
# Nedgangen 2022->2024 ar ~5 procent i bada serierna. Modellen arbetar med
# NIVA x FORANDRING, dar forandringen ar det robusta.

RIKET_BYGG_2022 = 371_000         # ANTAGET  niva i RAMS/NR-definition
RIKET_FORANDRING_2022_2025 = -0.050   # ANKARE  Byggforetagen: 328,8 -> 312,4 tkr (2022-2024)

# Lansspecifikt avvik fran riksnedgangen. Bostadsbyggandet foll betydligt mer an
# anlaggning; lan med hog bostadsandel i byggvolymen foll darfor mer an riket.
SCENARIER_NEDGANG = {
    "mild":    -0.050,   # lanet foljer riket
    "central": -0.075,   # lanet nagot varre an riket (hogre bostadsandel)
    "hard":    -0.110,   # lanet foljer husbyggnadsnedgangen (~-10 % nationellt)
}

# ---------------------------------------------------------------------------
# 3. Inkomster
# ---------------------------------------------------------------------------

ARSLON_BYGG_LAN = 450_000         # ANTAGET  beskattningsbar forvarvsinkomst per
                                  # sysselsatt i bygg, Orebro lan, 2025 ars niva
                                  # (~37,5 tkr/man; inkl. egenforetagare som drar ned)
ARSLON_OVRIGT_LAN = 420_000       # ANTAGET  snitt i de indirekt/inducerat berorda jobben

# ---------------------------------------------------------------------------
# 4. Multiplikatorer (input/output)
# ---------------------------------------------------------------------------
# Nationella sysselsattningsmultiplikatorer for SNI 41-43 ur SCB:s symmetriska
# I/O-tabeller. Regionala varden ar nationella varden nedskalade for
# interregionalt lackage (FLQ-regionalisering, se README avsnitt 4).

MULT_NATIONELL_TYP1 = 1.50        # ANTAGET  direkt + indirekt, hela Sverige
MULT_NATIONELL_TYP2 = 2.00        # ANTAGET  + inducerat

MULT_REGIONAL_TYP1 = {            # ANTAGET  intraregionalt, Orebro lan
    "lag": 1.15, "central": 1.25, "hog": 1.40,
}
MULT_REGIONAL_TYP2 = {
    "lag": 1.35, "central": 1.50, "hog": 1.70,
}

# ---------------------------------------------------------------------------
# 5. Motverkande inkomster (vad som faktiskt forsvinner ur skatteunderlaget)
# ---------------------------------------------------------------------------
# En forlorad byggtjanst ar inte ett forlorat skatteunderlag krona for krona.
# Omstallningsutfallet avgor. Andelarna summerar till 1.

OMSTALLNING = {
    # andel av de berorda, kvarvarande andel av tidigare inkomst
    "nytt_arbete_i_lanet": (0.45, 0.90),   # ANTAGET  nagot lagre lon i nytt jobb
    "arbetslos":           (0.35, 0.55),   # ANTAGET  a-kassa/aktivitetsstod, skattepliktigt
    "lamnar_lanet_eller_arbetskraften": (0.20, 0.15),  # ANTAGET
}

# ---------------------------------------------------------------------------
# 6. Skattesatser och utjamning
# ---------------------------------------------------------------------------

SKATTESATS_KOMMUN_LAN = 0.2160    # ANKARE/ANTAGET  befolkningsviktat lansgenomsnitt
                                  # (Orebro kommun 21,35 %; mindre kommuner hogre)
SKATTESATS_REGION = 0.1230        # ANKARE  Region Orebro lan, 2026

# Inkomstutjamning: bidrag = kompensationsgrad x lansvis skattesats x
# (garantiniva x medelskattekraft - egen skattekraft) x invanare.
KOMPENSATIONSGRAD = 0.95          # ANKARE  prop. 2003/04:155
LANSVIS_SKATTESATS_KOMMUN = 0.2030  # ANTAGET  rikssnitt 2003 justerat for skattevaxling
LANSVIS_SKATTESATS_REGION = 0.1140  # ANTAGET

# ---------------------------------------------------------------------------
# 7. Referensvarden for proportioner
# ---------------------------------------------------------------------------

SKATTEUNDERLAG_PER_INV_LAN = 233_000   # ANTAGET  ~95 % av riksgenomsnittet
MARGINALINTAKT_PER_INVANARE = 65_000   # ANKARE   SKR, marginalintakter vid
                                       # befolkningsforandring (kommun + region)
