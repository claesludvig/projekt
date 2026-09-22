"""
Parametrar för analysen av byggkonjunkturen i Örebro län.

Värden märkta HÄMTAT kommer från SCB:s statistikdatabas via hamta_scb.py och
bearbeta.py, och läses in från data/kalibrering.json. Saknas filen används
reservvärdena nedan, som är de som gällde innan datan fanns.

Värden märkta ANTAGET är modellval som varieras i känslighetsanalysen.
"""

import json
import os

_KAL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "data", "kalibrering.json")
try:
    with open(_KAL, encoding="utf-8") as _f:
        K = json.load(_f)
except FileNotFoundError:
    K = {}

KALIBRERAD = bool(K)

# ---------------------------------------------------------------------------
# 1. Byggsysselsättningen i länet                                     HÄMTAT
# ---------------------------------------------------------------------------

BYGG_LANET = {int(a): v for a, v in K.get("bas_byggsysselsatta_lanet", {}).items()}
BYGG_RIKET = {int(a): v for a, v in K.get("bas_byggsysselsatta_riket", {}).items()}
SYSS_LANET = {int(a): v for a, v in K.get("bas_totalt_lanet", {}).items()}
BYGG_KOMMUNER = K.get("bas_bygg_kommuner", {})
RAMS_LANET = {int(a): v for a, v in
              K.get("rams_byggsysselsatta_lanet_2008_2021", {}).items()}

TOPPAR = int(K["toppar"]) if K.get("toppar") else 2023
SENASTE_AR = int(K["senaste_ar"]) if K.get("senaste_ar") else 2025

# Faktisk förändring från toppåret till senaste år, personer
DIREKT_FORANDRING = K.get("direkt_forandring_personer", -497)
NEDGANG_LANET = K.get("nedgang_lanet_fran_topp", -0.045)
NEDGANG_RIKET = K.get("nedgang_riket_fran_topp", -0.049)
LANETS_ANDEL_AV_RIKET = K.get("lanets_andel_av_rikets_bygg", 0.0292)

# ---------------------------------------------------------------------------
# 2. Inkomster                                                        HÄMTAT
# ---------------------------------------------------------------------------

_lon = K.get("lonesumma_per_byggsysselsatt_riket_senaste", {})
ARSLON_BYGG_RIKET = _lon.get("varde", 455_033)
RELATIV_LONENIVA = K.get("lanets_relativa_lonenniva", 0.912)

ARSLON_BYGG_LAN = ARSLON_BYGG_RIKET * RELATIV_LONENIVA   # ~415 000 kr
ARSLON_OVRIGT_LAN = K.get("snittlon_per_sysselsatt_lanet", 400_599)

# ---------------------------------------------------------------------------
# 3. Skattesatser, skatteunderlag                                     HÄMTAT
# ---------------------------------------------------------------------------

_su = K.get("skatteunderlag_lanet", {})
SKATTEUNDERLAG_LANET = _su.get("varde", 75.3e9)
SKATTEUNDERLAG_AR = _su.get("ar", "2026")

_sats = K.get("skattesats_kommun_lanet", {})
SKATTESATS_KOMMUN_LAN = _sats.get("varde", 21.60) / 100
_satsr = K.get("skattesats_region_lanet", {})
SKATTESATS_REGION = _satsr.get("varde", 12.30) / 100
_tot = K.get("skattesats_lanet", {})
SKATTESATS_TOTAL = (_tot.get("varde") or 33.90) / 100

# ---------------------------------------------------------------------------
# 4. Multiplikatorer                                                  ANTAGET
# ---------------------------------------------------------------------------
# Nationella sysselsättningsmultiplikatorer för SNI 41-43 ur SCB:s symmetriska
# I/O-tabeller. De regionala är nedskalade för interregionalt läckage
# (FLQ-regionalisering). SCB publicerar inga regionala I/O-tabeller.

MULT_NATIONELL_TYP1 = 1.50
MULT_NATIONELL_TYP2 = 2.00
MULT_REGIONAL_TYP1 = {"lag": 1.15, "central": 1.25, "hog": 1.40}
MULT_REGIONAL_TYP2 = {"lag": 1.35, "central": 1.50, "hog": 1.70}

# ---------------------------------------------------------------------------
# 5. Omställning                                                      ANTAGET
# ---------------------------------------------------------------------------
# Kalibrerat mot den observerade utvecklingen: länets TOTALA sysselsättning
# steg under samma period som byggsysselsättningen föll, vilket innebär att
# de frigjorda resurserna i allt väsentligt absorberades av länets övriga
# arbetsmarknad. Andelen som återfår arbete i länet är därför satt högt.

OMSTALLNING = {
    "nytt_arbete_i_lanet": (0.65, 0.90),
    "arbetslos": (0.20, 0.55),
    "lamnar_lanet_eller_arbetskraften": (0.15, 0.15),
}

# Alternativ som varieras i känsligheten: hur stor andel av bruttolöne-
# bortfallet som faktiskt lämnar skatteunderlaget.
NETTOANDEL_ALTERNATIV = {"lag": 0.20, "central": None, "hog": 0.50, "mekanisk": 1.00}

# ---------------------------------------------------------------------------
# 6. Utjämning och referensvärden
# ---------------------------------------------------------------------------

KOMPENSATIONSGRAD = 0.95            # prop. 2003/04:155
LANSVIS_SKATTESATS_KOMMUN = 0.2030  # ANTAGET  rikssnitt 2003, skatteväxlingsjusterat
LANSVIS_SKATTESATS_REGION = 0.1140  # ANTAGET

BEFOLKNING_LAN = 308_362            # Region Örebro län, 2025
MARGINALINTAKT_PER_INVANARE = 65_000  # SKR, marginalintäkter vid befolkningsförändring

# Scenarier för hur djup nedgången blir, mätt från toppåret.
SCENARIER_NEDGANG = {
    "observerad": NEDGANG_LANET,
    "fortsatt": -0.080,
    "hard": -0.110,
}
