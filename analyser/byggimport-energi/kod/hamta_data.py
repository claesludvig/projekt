"""Hämtar primärdata för analysen av byggsektorns import och energikänslighet.

Kräver att följande värdar är tillåtna i nätverket:
  api.scb.se, ec.europa.eu
Kör:  python3 kod/hamta_data.py   (sparar i data/raw/)

OBS: Tabell-ID:n för SCB nedan är utgångspunkter och behöver
kontrolleras i SCB:s API-browser innan skarp körning.
"""
import json
import pathlib
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# KN/HS-koder att följa i importstatistiken
KN_KODER = {
    "7214": "Armeringsstång (stång av järn/olegerat stål)",
    "7216": "Profiler/balkar av stål",
    "2523": "Cement och klinker",
    "6809": "Gipsskivor",
    "6806": "Mineralull",
    "6907": "Keramiska plattor",
    "7005": "Planglas (floatglas)",
    "7008": "Isolerglas",
    "2713": "Petroleumbitumen",
    "2715": "Bitumenblandningar",
    "3917": "Plaströr",
    "4410": "Spånskivor",
    "4411": "Fiberskivor/MDF",
}

# Eurostat-dataset (JSON-stat via dissemination API)
EUROSTAT = {
    # TTF-nära: gaspris för icke-hushåll
    "nrg_pc_203": {"geo": "SE", "unit": "KWH"},
    # Producentpriser industri, C23 icke-metalliska mineral, C24 stål
    "sts_inppd_m": {"geo": "EU27_2020", "nace_r2": "C23", "indic_bt": "PRC_PRR"},
    # Produktionsvolym industri
    "sts_inpr_m": {"geo": "EU27_2020", "nace_r2": "C23", "indic_bt": "PRD"},
    # Input-output, importmatris (FIGARO/naio)
    "naio_10_cp1610": {"geo": "SE", "prd_use": "CPA_F"},
}

SCB_BAS = "https://api.scb.se/OV0104/v1/doris/sv/ssd"
SCB_TABELLER = {
    # Byggkostnadsindex per varugrupp (kontrollera ID)
    "bki": "PR/PR0502/PR0502A/BKIFLERBOST",
    # Utrikeshandel per KN8 och land (kontrollera ID)
    "import_kn": "HA/HA0201/HA0201B/ImpExpKNMan",
    # Input-output, importerade insatsvaror (kontrollera ID)
    "io_import": "NR/NR0102/NR0102Y/NR0102IOimp",
}


def hamta(url, fil, data=None):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        (RAW / fil).write_bytes(r.read())
    print("sparad:", fil)


def eurostat():
    for ds, filt in EUROSTAT.items():
        q = "&".join(f"{k}={v}" for k, v in filt.items())
        url = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}?{q}"
        try:
            hamta(url, f"eurostat_{ds}.json")
        except Exception as e:  # noqa: BLE001
            print("misslyckades", ds, e)


def scb():
    for namn, tab in SCB_TABELLER.items():
        url = f"{SCB_BAS}/{tab}"
        try:
            # GET ger metadata; bygg sedan fråga med rätt variabler
            hamta(url, f"scb_{namn}_meta.json")
        except Exception as e:  # noqa: BLE001
            print("misslyckades", namn, e)


if __name__ == "__main__":
    (RAW / "kn_koder.json").write_text(json.dumps(KN_KODER, ensure_ascii=False, indent=2))
    eurostat()
    scb()
