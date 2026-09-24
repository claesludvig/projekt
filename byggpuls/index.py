"""Byggpulsen: ett eget ledande index för svenskt byggande.

Indexet väger ihop månadsserier som rör sig före byggstatistiken
(platsannonser, konkurser, räntor, byggbolagens aktier). Varje serie:

1. görs om till en årsförändring (``transform``),
2. vänds så att högre alltid betyder starkare byggande (``tecken``),
3. standardiseras (z-värde: avvikelse från sitt eget snitt i standardavvikelser).

Vikterna tas fram med principalkomponentanalys: den första komponenten är den
rörelse som serierna har gemensamt, och laddningarna blir vikter. Ingen vikt
sätts för hand. Indexet mäts i standardavvikelser: 0 = normalt läge, +1 =
ovanligt starkt, −1 = ovanligt svagt.

``efterhandstest`` räknar om indexet som det hade sett ut vid varje
tidpunkt, med bara den data som då var publicerad, och jämför med SCB:s
påbörjade lägenheter kvartalen efteråt. Det är det ärliga måttet på om
indexet leder byggandet; korrelationen i hela urvalet blir alltid för bra.
"""

import numpy as np
import pandas as pd

MIN_OBS = 36  # månader med alla komponenter innan vikter skattas


def transformera(s: pd.Series, typ: str) -> pd.Series:
    if typ == "yoy":
        return (s / s.shift(12) - 1) * 100
    if typ == "yoy_3m":
        m = s.rolling(3).mean()
        return (m / m.shift(12) - 1) * 100
    if typ == "diff12":
        return s - s.shift(12)
    raise ValueError(f"okänd transform: {typ}")


def signaler(ra: pd.DataFrame, komponenter: list) -> pd.DataFrame:
    """Transformerade och teckenvända serier, en kolumn per komponent."""
    ut = {}
    for k in komponenter:
        if k["id"] in ra and ra[k["id"]].notna().sum() > 12:
            ut[k["id"]] = transformera(ra[k["id"]].astype(float), k["transform"]) * k["tecken"]
    return pd.DataFrame(ut).replace([np.inf, -np.inf], np.nan)


def pca_vikter(z: pd.DataFrame) -> pd.Series | None:
    """Laddningar på första principalkomponenten, skalade så att
    absolutbeloppen summerar till 1 och vända så att summan är positiv."""
    hel = z.dropna()
    if len(hel) < MIN_OBS or z.shape[1] < 2:
        return None
    egenv, egenvek = np.linalg.eigh(np.corrcoef(hel.values, rowvar=False))
    v = egenvek[:, np.argmax(egenv)]
    if v.sum() < 0:
        v = -v
    return pd.Series(v / np.abs(v).sum(), index=z.columns)


def lika_vikter(z: pd.DataFrame) -> pd.Series:
    return pd.Series(1 / z.shape[1], index=z.columns)


def standardisera(x: pd.DataFrame) -> pd.DataFrame:
    return (x - x.mean()) / x.std()


def vag_ihop(z: pd.DataFrame, vikter: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Index = viktat snitt av de komponenter som finns just den månaden.
    Saknas en komponent i slutet (den publiceras senare) fördelas dess vikt
    på de andra, som i vanliga nowcast-modeller. Returnerar index och varje
    komponents bidrag (bidragen summerar till indexet)."""
    w = z.notna().mul(vikter, axis=1)
    summa = w.abs().sum(axis=1).replace(0, np.nan)
    bidrag = z.mul(vikter, axis=1).div(summa, axis=0)
    # minst hälften av komponenterna måste finnas för att indexet ska räknas
    rakna = z.notna().sum(axis=1) >= max(2, (z.shape[1] + 1) // 2)
    index = bidrag.sum(axis=1, min_count=1).where(rakna)
    return index, bidrag.where(rakna, axis=0)


def bygg_index(ra: pd.DataFrame, komponenter: list, metod: str = "pca") -> dict | None:
    x = signaler(ra, komponenter)
    if x.shape[1] < 2:
        return None
    z = standardisera(x)
    vikter = pca_vikter(z) if metod == "pca" else lika_vikter(z)
    if vikter is None:
        vikter, metod = lika_vikter(z), "lika"
    index, bidrag = vag_ihop(z, vikter)
    return {"index": index.dropna(), "bidrag": bidrag, "z": z, "vikter": vikter, "metod": metod}


def _publicerat(ra: pd.DataFrame, t: pd.Timestamp, fordrojning: dict) -> pd.DataFrame:
    """Det som fanns publicerat i slutet av månad t: serie med fördröjning
    k månader har bara värden t.o.m. månad t−k."""
    ut = ra[ra.index <= t].copy()
    for kol, k in fordrojning.items():
        if kol in ut and k:
            ut.loc[ut.index > t - pd.DateOffset(months=k), kol] = np.nan
    return ut


def realtidsindex(ra: pd.DataFrame, komponenter: list, metod: str = "pca") -> pd.Series:
    """Indexets värde för varje månad t, räknat med data publicerad vid t.
    Vikter och standardisering skattas om varje månad på data t.o.m. t."""
    fordrojning = {k["id"]: k.get("fordrojning_man", 0) for k in komponenter}
    ut = {}
    for t in ra.index:
        r = bygg_index(_publicerat(ra, t, fordrojning), komponenter, metod)
        if r is None or r["metod"] != metod:
            continue
        # senaste månad med ett indexvärde, högst en månad bakåt
        senast = r["index"][r["index"].index >= t - pd.DateOffset(months=1)]
        if len(senast):
            ut[t] = float(senast.iloc[-1])
    return pd.Series(ut, dtype=float)


def mal_arsforandring(kvartal: pd.Series) -> pd.Series:
    """Årsförändring i % av rullande fyrakvartalssumma (jämnar ut säsong och brus)."""
    s4 = kvartal.rolling(4).sum()
    return ((s4 / s4.shift(4) - 1) * 100).dropna()


def ledkorrelation(index_man: pd.Series, mal_kv: pd.Series, max_kvartal: int = 4) -> list:
    """Korrelation mellan indexet i ett kvartal (värdet i kvartalets sista
    månad) och målets årsförändring k kvartal senare."""
    idx = index_man.groupby(index_man.index.to_period("Q")).last()
    mal = mal_kv.copy()
    mal.index = mal.index.to_period("Q")
    ut = []
    for k in range(max_kvartal + 1):
        df = pd.concat([idx, mal.shift(-k)], axis=1, keys=["i", "m"]).dropna()
        ut.append({"ledtid_kvartal": k, "n": len(df),
                   "korrelation": None if len(df) < 8 else round(float(df["i"].corr(df["m"])), 2)})
    return ut
