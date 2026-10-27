#!/usr/bin/env python3
"""OMXS30-bolagen i Marknadspulsen: hur bolagen rör sig och var det finns
tradinglägen med högst en veckas innehavstid.

Bolagslistan och analytikernas vinstprognoser kommer från vinstförväntningarna
(vinstforvantningar/bolag.json och data/vinst.json), så att de två breven
alltid utgår från samma bolag. Kurserna hämtas från Yahoo Finance, justerade
för split och utdelning, så att en utdelning inte ser ut som ett kursfall.

Urvalet bygger på det som har gått att belägga på veckohorisont i den här
bolagsmängden: förra veckans förlorare har i snitt gått bättre veckan efter
(kortsiktig rekyl), medan en jämn trend inte har gett något försprång. Därför
letar urvalet efter kursfall i bolag där analytikerna höjer prognoserna, utan
rapport under innehavsveckan. Signalkontrollen räknas om vid varje körning så
att brevet visar om sambandet fortfarande håller.

    from aktier import berakna_aktier
    sektion = berakna_aktier(t_o_m)   # dict till marknadspuls.json["aktier"]
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent
BOLAG_FIL = REPO_DIR / "vinstforvantningar" / "bolag.json"
VINST_FIL = REPO_DIR / "vinstforvantningar" / "data" / "vinst.json"
HANDELSER_FIL = BASE_DIR / "handelser.json"
HISTORIK_FIL = BASE_DIR / "data" / "kandidater_historik.csv"
INDEX_TICKER = "^OMX"

HISTORIK_AR = 2
INNEHAV_DAGAR = 5            # handelsdagar
HANDELSER_FRAMAT = 7         # kalenderdagar framåt för rapporter och makrohändelser
FONSTER_VECKOR = 120         # handelsdagar som 5-dagarsfördelningen räknas på
MAX_KANDIDATER = 5
REVIDERING_BRUS = 0.5        # % på en månad; mindre är brus (samma gräns som vinstbrevet)
RAPPORTFALL_GRANS = -8.0     # % mot index på rapportdagen: fallet är bolagsnyhet, inte rekyl
NYLIG_RAPPORT_DAGAR = 10
UTTANJD_Z = 2.0


# ── Hämtning ──────────────────────────────────────────────────────────────────

def _bolag() -> list[dict]:
    return json.loads(BOLAG_FIL.read_text(encoding="utf-8"))["bolag"]


def _vinst() -> dict:
    if not VINST_FIL.exists():
        return {}
    return json.loads(VINST_FIL.read_text(encoding="utf-8"))


def hamta_kurser(tickers: list[str], t_o_m: date) -> pd.DataFrame:
    """Dagliga stängningskurser (datum × ticker) t.o.m. t_o_m."""
    import yfinance as yf

    raw = yf.download(tickers, period=f"{HISTORIK_AR}y", interval="1d", auto_adjust=True,
                      progress=False, threads=True)
    if raw is None or raw.empty:
        return pd.DataFrame()
    kurser = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    kurser.index = pd.to_datetime(kurser.index.date)
    kurser = kurser[~kurser.index.duplicated(keep="last")].sort_index()
    return kurser[kurser.index <= pd.Timestamp(t_o_m)].dropna(axis=1, how="all")


# ── Mått per bolag ────────────────────────────────────────────────────────────

def _trend(logpris: pd.Series) -> tuple[float, float]:
    """Lutning (i % per år) och R² för en linje genom logaritmerade kurser."""
    y = logpris.dropna().values
    if len(y) < 20:
        return np.nan, np.nan
    x = np.arange(len(y))
    lutning, konst = np.polyfit(x, y, 1)
    rest = y - (konst + lutning * x)
    r2 = 1 - (rest ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return (np.exp(lutning * 252) - 1) * 100, r2


def _rsi(s: pd.Series, n: int = 14) -> float:
    d = s.diff().dropna()
    upp = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    ned = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    return 100.0 if ned == 0 else 100 - 100 / (1 + upp / ned)


def _pct(nu, da):
    return (nu / da - 1) * 100


def _r(x, dec=2):
    return None if x is None or pd.isna(x) else round(float(x), dec)


def matt_per_bolag(kurser: pd.DataFrame, bolag: list[dict], vinst: dict, t_o_m: date) -> list[dict]:
    idx = kurser[INDEX_TICKER].dropna()
    r_idx = idx.pct_change()
    prognoser = {b["ticker"]: b for b in vinst.get("bolag", [])}
    rader = []
    for b in bolag:
        t = b["ticker"]
        if t not in kurser:
            continue
        s = kurser[t].dropna()
        if len(s) < 130:
            continue
        r = s.pct_change()
        gem = pd.concat([r, r_idx], axis=1).dropna().iloc[-250:]
        beta = gem.iloc[:, 0].cov(gem.iloc[:, 1]) / gem.iloc[:, 1].var()
        senast = s.iloc[-1]
        vecka = s.pct_change(INNEHAV_DAGAR).iloc[-FONSTER_VECKOR:] * 100
        # Avkastning utöver det index förklarar (β × index), senaste veckan
        idx_5d = _pct(idx.iloc[-1], idx.iloc[-1 - INNEHAV_DAGAR])
        res_5d = _pct(senast, s.iloc[-1 - INNEHAV_DAGAR]) - beta * idx_5d
        logp = np.log(s)
        trend60, r2_60 = _trend(logp.iloc[-60:])
        alfa60, r2_alfa = _trend((logp - beta * np.log(idx.reindex(s.index).ffill())).iloc[-60:])
        p5 = vecka.quantile(0.05)

        prog = prognoser.get(t, {})
        nasta = prog.get("+1y", {})
        rapport = prog.get("nasta_rapport")
        rapport_reaktion = None
        if rapport:
            rd = pd.Timestamp(rapport)
            if pd.Timestamp(t_o_m) - pd.Timedelta(days=NYLIG_RAPPORT_DAGAR) <= rd <= pd.Timestamp(t_o_m):
                i = s.index.searchsorted(rd)
                if 0 < i < len(s):
                    dag = _pct(s.iloc[i], s.iloc[i - 1])
                    idx_dag = _pct(idx.asof(s.index[i]), idx.asof(s.index[i - 1]))
                    rapport_reaktion = dag - beta * idx_dag
        dagar_till_rapport = None
        if rapport:
            dagar_till_rapport = (date.fromisoformat(rapport) - t_o_m).days

        rader.append({
            "namn": b["namn"], "ticker": t, "datum": s.index[-1].date().isoformat(),
            "senast": _r(senast),
            "1d": _r(_pct(senast, s.iloc[-2])), "1v": _r(_pct(senast, s.iloc[-1 - INNEHAV_DAGAR])),
            "1m": _r(_pct(senast, s.asof(s.index[-1] - pd.Timedelta(days=30)))),
            "res_1v": _r(res_5d),
            "vs_ma50": _r(_pct(senast, s.iloc[-50:].mean())),
            "rsi14": _r(_rsi(s.iloc[-120:]), 0),
            "z60": _r((senast - s.iloc[-60:].mean()) / s.iloc[-60:].std(ddof=0)),
            "beta": _r(beta),
            "vol20": _r(r.iloc[-20:].std() * np.sqrt(252) * 100, 1),
            "trend60": _r(trend60, 1), "r2_60": _r(r2_60),
            "alfa60": _r(alfa60, 1), "r2_alfa60": _r(r2_alfa),
            "andel_uppveckor": _r((vecka > 0).mean() * 100, 0),
            "spridning_5d": _r(vecka.std()),
            "p5_5d": _r(p5),
            "stopp": _r(senast * (1 + p5 / 100)),
            "prognos_1m": nasta.get("revidering", {}).get("1m"),
            "prognos_1v": nasta.get("revidering", {}).get("1v"),
            "analytiker_upp_30d": nasta.get("upp_30d"),
            "analytiker_ner_30d": nasta.get("ner_30d"),
            "rapport": rapport,
            "dagar_till_rapport": dagar_till_rapport,
            "rapport_reaktion": _r(rapport_reaktion, 1),
        })
    return rader


# ── Urval ─────────────────────────────────────────────────────────────────────

def _svensk(text: str) -> str:
    """Decimalkomma och typografiskt minustecken, som i mallens tabeller."""
    return re.sub(r"-(?=\d)", "−", re.sub(r"(?<=\d)\.(?=\d)", ",", text))


def _rapport_i_veckan(r: dict) -> bool:
    d = r["dagar_till_rapport"]
    return d is not None and 0 < d <= HANDELSER_FRAMAT


def valj(rader: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """(kandidater, uttänjda, undvik). Varje post får en lista skäl."""
    kandidater, uttanjda, undvik = [], [], []
    for r in rader:
        rev, upp, ner = r["prognos_1m"], r["analytiker_upp_30d"] or 0, r["analytiker_ner_30d"] or 0
        skal_undvik = []
        if rev is not None and rev <= -1.0:
            skal_undvik.append(f"prognosen för nästa år sänkt {abs(rev):.1f} % på en månad")
        if ner >= 3 and ner >= 2 * upp:
            skal_undvik.append(f"{ner:.0f} ned/{upp:.0f} upp bland analytikerna på 30 dagar")
        if r["rapport_reaktion"] is not None and r["rapport_reaktion"] <= RAPPORTFALL_GRANS:
            skal_undvik.append(f"föll {abs(r['rapport_reaktion']):.1f} % mot index på rapporten")
        if (r["trend60"] or 0) < 0 and (r["r2_60"] or 0) >= 0.6:
            skal_undvik.append(f"stabil nedåttrend (R² {r['r2_60']:.2f}, {r['trend60']:.0f} % i årstakt)")
        if skal_undvik:
            undvik.append({**r, "skal": [_svensk(x) for x in skal_undvik]})
            continue
        if (r["z60"] or 0) >= UTTANJD_Z or (r["rsi14"] or 0) >= 70:
            uttanjda.append({**r, "skal": [_svensk(f"z60 {r['z60']:+.2f}, RSI {r['rsi14']:.0f}")]})
            continue
        if (rev is None or rev < REVIDERING_BRUS or upp < 2 or upp <= ner or _rapport_i_veckan(r)
                or r["1v"] is None or r["1v"] >= 0 or (r["z60"] or 0) > 1):
            continue
        kandidater.append(dict(r))

    if kandidater:
        df = pd.DataFrame(kandidater)
        # Lika vikt: prognoshöjning, fall utöver index, andel uppveckor, låg spridning
        poang = (df["prognos_1m"].rank() + (-df["res_1v"]).rank()
                 + df["andel_uppveckor"].rank() + (-df["spridning_5d"]).rank())
        df["poang"] = poang / (4 * len(df))
        df = df.sort_values("poang", ascending=False).head(MAX_KANDIDATER)
        # Relativ positionsstorlek: omvänt mot veckospridningen, största = 1,0
        inv = 1 / df["spridning_5d"]
        df["vikt"] = (inv / inv.max()).round(2)
        kandidater = []
        for r in df.to_dict("records"):
            skal = [f"prognosen för nästa år +{r['prognos_1m']:.1f} % på en månad "
                    f"({r['analytiker_upp_30d']:.0f} upp/{r['analytiker_ner_30d']:.0f} ned bland analytikerna)",
                    f"{r['res_1v']:+.1f} % mot index senaste veckan",
                    f"uppgång {r['andel_uppveckor']:.0f} % av veckorna, spridning ±{r['spridning_5d']:.1f} %"]
            if r["rapport_reaktion"] is not None:
                skal.append(f"rapportdagen {r['rapport_reaktion']:+.1f} % mot index")
            r["poang"] = round(float(r["poang"]), 2)
            r["skal"] = [_svensk(x) for x in skal]
            kandidater.append(r)
    uttanjda.sort(key=lambda r: -(r["z60"] or 0))
    return kandidater, uttanjda, undvik


# ── Signalkontroll ────────────────────────────────────────────────────────────

def signalkontroll(kurser: pd.DataFrame, bolag: list[dict]) -> list[dict]:
    """Rangkorrelation (IC) mellan signalen och nästa veckas avkastning, mätt varje
    vecka utan överlapp över senaste året. Negativt IC för veckans avkastning =
    förlorarna har gått bättre veckan efter (rekyl)."""
    tick = [b["ticker"] for b in bolag if b["ticker"] in kurser]
    logp = np.log(kurser[tick])
    framat = logp.shift(-INNEHAV_DAGAR) - logp
    signaler = {
        "Förra veckans avkastning (rekyl)": logp - logp.shift(INNEHAV_DAGAR),
        "Trend 60 dagar (momentum)": logp - logp.shift(60),
        "Låg volatilitet 20 dagar": -logp.diff().rolling(20).std(),
    }
    datum = logp.index[-252 - INNEHAV_DAGAR:-INNEHAV_DAGAR:INNEHAV_DAGAR]
    ut = []
    for namn, s in signaler.items():
        ic = pd.Series([s.loc[d].rank().corr(framat.loc[d].rank()) for d in datum]).dropna()
        if len(ic) < 8:
            continue
        ut.append({
            "signal": namn,
            "ic": _r(ic.mean(), 3),
            "t": _r(ic.mean() / ic.std() * np.sqrt(len(ic))),
            "ic_26v": _r(ic.iloc[-26:].mean(), 3),
            "ic_8v": _r(ic.iloc[-8:].mean(), 3),
            "veckor": int(len(ic)),
        })
    return ut


# ── Index och rörelser ────────────────────────────────────────────────────────

def indexlage(kurser: pd.DataFrame, rader: list[dict]) -> dict:
    s = kurser[INDEX_TICKER].dropna()
    senast = s.iloc[-1]
    vol20 = s.pct_change().iloc[-20:].std() * np.sqrt(252) * 100
    tr, r2 = _trend(np.log(s.iloc[-60:]))
    sista = [r for r in rader if r["datum"] == s.index[-1].date().isoformat()]
    return {
        "datum": s.index[-1].date().isoformat(),
        "senast": _r(senast),
        "vs_ma20": _r(_pct(senast, s.iloc[-20:].mean())),
        "vs_ma50": _r(_pct(senast, s.iloc[-50:].mean())),
        "vs_ma200": _r(_pct(senast, s.iloc[-200:].mean())),
        "rsi14": _r(_rsi(s.iloc[-120:]), 0),
        "z60": _r((senast - s.iloc[-60:].mean()) / s.iloc[-60:].std(ddof=0)),
        "trend60": _r(tr, 1), "r2_60": _r(r2),
        "vol20": _r(vol20, 1),
        "normal_veckorörelse": _r(vol20 / np.sqrt(52), 1),
        "bredd_upp_1d": sum(1 for r in sista if (r["1d"] or 0) > 0),
        "bredd_over_ma50": sum(1 for r in rader if (r["vs_ma50"] or 0) > 0),
        "antal_bolag": len(rader),
    }


def rorelser(rader: list[dict], n: int = 3) -> dict:
    ut = {}
    for p in ("1d", "1v"):
        sort = sorted((r for r in rader if r[p] is not None), key=lambda r: r[p])
        ut[p] = {"basta": [{"namn": r["namn"], "andring": r[p]} for r in reversed(sort[-n:])],
                 "samsta": [{"namn": r["namn"], "andring": r[p]} for r in sort[:n]]}
    return ut


# ── Händelser och uppföljning ─────────────────────────────────────────────────

def handelser(rader: list[dict], t_o_m: date) -> list[dict]:
    slut = t_o_m + timedelta(days=HANDELSER_FRAMAT + 1)
    ut = [{"datum": r["rapport"], "handelse": f"{r['namn']} rapporterar", "typ": "rapport"}
          for r in rader if r["rapport"] and t_o_m < date.fromisoformat(r["rapport"]) <= slut]
    if HANDELSER_FIL.exists():
        for h in json.loads(HANDELSER_FIL.read_text(encoding="utf-8"))["handelser"]:
            if t_o_m < date.fromisoformat(h["datum"]) <= slut:
                ut.append({"datum": h["datum"], "handelse": h["handelse"], "typ": "makro"})
    return sorted(ut, key=lambda h: h["datum"])


def uppfoljning(kurser: pd.DataFrame, kandidater: list[dict], t_o_m: date) -> dict | None:
    """Sparar dagens kandidater och räknar utfallet för kandidaterna från en
    vecka sedan (köp vid stängning den dagen, sälj vid senaste stängning)."""
    nya = pd.DataFrame([{"datum": t_o_m.isoformat(), "ticker": r["ticker"], "namn": r["namn"],
                         "kurs": r["senast"], "index": float(kurser[INDEX_TICKER].dropna().iloc[-1])}
                        for r in kandidater], columns=["datum", "ticker", "namn", "kurs", "index"])
    hist = pd.read_csv(HISTORIK_FIL) if HISTORIK_FIL.exists() else nya.iloc[0:0]
    hist = pd.concat([hist[hist["datum"] != t_o_m.isoformat()], nya], ignore_index=True)
    hist = hist[pd.to_datetime(hist["datum"]) >= pd.Timestamp(t_o_m) - pd.Timedelta(days=400)]
    HISTORIK_FIL.parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(HISTORIK_FIL, index=False)

    idx = kurser[INDEX_TICKER].dropna()
    if len(idx) <= INNEHAV_DAGAR:
        return None
    start = idx.index[-1 - INNEHAV_DAGAR].date().isoformat()
    tidigare = hist[hist["datum"] <= start]
    if tidigare.empty:
        return None
    dag = tidigare["datum"].max()
    grupp = tidigare[tidigare["datum"] == dag]
    idx_avk = _pct(idx.iloc[-1], grupp["index"].iloc[0])
    poster = []
    for g in grupp.itertuples():
        if g.ticker in kurser and pd.notna(kurser[g.ticker].iloc[-1]):
            avk = _pct(kurser[g.ticker].dropna().iloc[-1], g.kurs)
            poster.append({"namn": g.namn, "avkastning": _r(avk, 1), "mot_index": _r(avk - idx_avk, 1)})
    if not poster:
        return None
    return {"fran": dag, "index": _r(idx_avk, 1), "bolag": poster,
            "snitt": _r(np.mean([p["avkastning"] for p in poster]), 1),
            "snitt_mot_index": _r(np.mean([p["mot_index"] for p in poster]), 1)}


# ── Ingång ────────────────────────────────────────────────────────────────────

def berakna_aktier(t_o_m: date) -> tuple[dict | None, list[str]]:
    """Returnerar (sektion till marknadspuls.json, fel-lista). Sektionen är None
    om kurserna inte gick att hämta; resten av brevet ska då gå ut ändå."""
    fel = []
    bolag = _bolag()
    vinst = _vinst()
    if not vinst:
        fel.append("Vinstprognoser saknas (vinstforvantningar/data/vinst.json)")
    kurser = hamta_kurser([b["ticker"] for b in bolag] + [INDEX_TICKER], t_o_m)
    if kurser.empty or INDEX_TICKER not in kurser:
        return None, fel + ["OMXS30-bolagen: ingen kursdata från Yahoo"]
    saknas = [b["namn"] for b in bolag if b["ticker"] not in kurser]
    if saknas:
        fel.append("OMXS30-bolagen saknar kurser: " + ", ".join(saknas))

    rader = matt_per_bolag(kurser, bolag, vinst, t_o_m)
    gamla = [r["namn"] for r in rader if r["datum"] < kurser[INDEX_TICKER].dropna().index[-1].date().isoformat()]
    if gamla:
        fel.append("Kurs från tidigare dag för: " + ", ".join(gamla))
    kandidater, uttanjda, undvik = valj(rader)
    return {
        "data_t_o_m": kurser.index[-1].date().isoformat(),
        "prognoser_per": vinst.get("datum"),
        "index": indexlage(kurser, rader),
        "rorelser": rorelser(rader),
        "kandidater": kandidater,
        "uttanjda": uttanjda,
        "undvik": undvik,
        "handelser": handelser(rader, t_o_m),
        "signalkontroll": signalkontroll(kurser, bolag),
        "uppfoljning": uppfoljning(kurser, kandidater, t_o_m),
        "bolag": rader,
        "metod": (
            "Kurser från Yahoo Finance, justerade för split och utdelning. Kandidaterna är bolag där "
            "analytikerna höjt prognosen för nästa år minst 0,5 % den senaste månaden (fler höjningar än "
            "sänkningar), som fallit senaste veckan, inte är uttänjda (z60 högst +1) och inte rapporterar "
            "inom 7 dagar. De rangordnas med lika vikt på prognoshöjning, fall mot index (β × OMXS30), "
            "andel uppveckor och låg veckospridning, mätt på 120 handelsdagar. Stopp = 5:e percentilen "
            "av bolagets 5-dagarsavkastning. Vikt = omvänt mot veckospridningen, största = 1,0. "
            "Signalkontroll: rangkorrelation (IC) mellan signalen och nästa veckas avkastning, en mätning "
            "per vecka senaste året; |t| under 2 = inte säkerställt. Negativt IC för förra veckans "
            "avkastning betyder att förlorarna gått bättre veckan efter. Inte investeringsrådgivning."
        ),
    }, fel


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Räkna OMXS30-avsnittet separat (test).")
    ap.add_argument("--t-o-m", default=(date.today() - timedelta(days=1)).isoformat())
    a = ap.parse_args()
    sektion, fel = berakna_aktier(date.fromisoformat(a.t_o_m))
    print(json.dumps({k: v for k, v in (sektion or {}).items() if k != "bolag"}, ensure_ascii=False, indent=2))
    print("Fel:", fel)
