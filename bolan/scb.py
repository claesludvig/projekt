"""Minimal hämtare mot SCB PxWebApi v2 -> långt pandas-format."""
import time
import pandas as pd
import requests

API = "https://statistikdatabasen.scb.se/api/v2"


def hamta(tabell: str, urval: dict[str, str], lang: str = "sv") -> pd.DataFrame:
    """urval: {dimension: 'kod1,kod2' eller '*'}. Returnerar en rad per cell."""
    params = {f"valueCodes[{k}]": v for k, v in urval.items()}
    params.update(lang=lang, outputFormat="json-stat2")
    for forsok in range(4):
        r = requests.get(f"{API}/tables/{tabell}/data", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(2 ** forsok * 2)
            continue
        r.raise_for_status()
        break
    js = r.json()
    dims = js["id"]
    koder = [list(js["dimension"][d]["category"]["index"]) for d in dims]
    idx = pd.MultiIndex.from_product(koder, names=dims)
    df = pd.DataFrame({"varde": js["value"]}, index=idx).reset_index()
    time.sleep(0.4)
    return df


def tid_till_datum(s: pd.Series) -> pd.Series:
    s = s.astype(str)
    if s.str.contains("M").all():
        return pd.PeriodIndex(s.str.replace("M", "-"), freq="M").to_timestamp(how="end").normalize()
    if s.str.contains("K").all():
        return pd.PeriodIndex(s.str.replace("K", "Q"), freq="Q").to_timestamp(how="end").normalize()
    return pd.to_datetime(s)
