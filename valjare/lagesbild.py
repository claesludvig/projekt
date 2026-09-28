"""Lägesbild: vad har hänt de senaste månaderna?

Varje vecka läses de månads- och kvartalsserier som finns (Polisen, SCB,
Riksbanken) och jämförs med samma period förra året och med seriens egen
historik. Resultatet är en signal att titta närmare på, inte en förklaring.

Status per serie:
  larm       ovanligt stor förändring (|z| >= 2 mot de senaste tio årens
             förändringar) eller högsta/lägsta nivån på minst tio år
  bevaka     |z| >= 1,5 eller högsta/lägsta på minst fem år
  normal     inget av ovanstående
  inaktuell  senaste värdet är äldre än källans normala eftersläpning + 2 månader

För antal (skjutningar, konkurser) jämförs rullande tolvmånaderssummor och de
tre senaste månaderna mot samma månader året innan, så att säsongen tas bort.
För nivåer (inflation, arbetslöshet) jämförs värdet med tre och tolv månader
tidigare.

Tabeller: lagesbild (en rad per serie), lagesbild_serie (serierna).
Filer: data/lagesbild/senaste.md och data/lagesbild/<år>-V<vecka>.md.
"""

import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from fragor import KPI_GRUPPER
from verklighet_katalog import mal

TOTALT = r"(?i)^(totalt|samtliga|hela|riket|män och kvinnor|båda|totala|summa)"


def _valj(df: pd.DataFrame, val: dict, innehall: str | None = None) -> pd.Series | None:
    """Väljer ut en tidsserie ur en SCB-tabell. val: regex mot variabelnamn -> regex mot värde.
    Variabler som inte anges får ett totalvärde eller sitt enda värde."""
    if df is None or df.empty:
        return None
    cc = list(dict.fromkeys(df.ContentsCode))
    c = next((x for x in cc if innehall and re.search(innehall, x)), cc[0] if not innehall else None)
    if c is None:
        return None
    df = df[df.ContentsCode == c]
    for d in [c for c in df.columns if not c.endswith("_kod") and c not in ("tabell", "Tid", "ContentsCode", "varde")]:
        varden = list(dict.fromkeys(df[d].astype(str)))
        monster = next((v for k, v in val.items() if re.search(k, d)), None)
        v = next((x for x in varden if monster and re.search(monster, x)), None)
        if v is None and monster is None:
            v = next((x for x in varden if re.search(TOTALT, x.strip())), varden[0] if len(varden) == 1 else None)
        if v is None:
            return None
        df = df[df[d].astype(str) == v]
    s = df.groupby("Tid").varde.sum()
    try:
        s.index = pd.PeriodIndex([t.replace("M", "-").replace("K", "Q") if "K" in t else t.replace("M", "-")
                                  for t in s.index], freq="Q" if "K" in s.index[0] else "M")
    except (ValueError, IndexError):
        return None
    return s.sort_index().dropna()


def _yoy(s: pd.Series) -> pd.Series:
    return (100 * (s / s.shift(12) - 1)).dropna()


def _katalog_tab(katalog: pd.DataFrame, rubrik: str) -> list[str]:
    k = katalog[katalog.rubrik.astype(str).str.contains(rubrik, regex=True, na=False)]
    return list(k["id"])


def serier(scb, katalog: pd.DataFrame, pol: pd.DataFrame, kpi: pd.DataFrame, data_dir: Path) -> list[dict]:
    """Alla serier som går att bygga. Varje post: id, namn, fraga, kalla, typ, frekvens, lag (månader), s."""
    ut = []

    def lagg(id_, namn, fraga, kalla, typ, s, lag, enhet=""):
        if s is not None and len(s) >= 24:
            ut.append({"id": id_, "namn": namn, "fraga": fraga, "kalla": kalla, "typ": typ,
                       "frekvens": s.index.freqstr[0], "lag": lag, "enhet": enhet, "s": s})

    # Polisen
    if pol is not None and not pol.empty:
        tot = pol[pol.polisregion == "Totalt"]
        for (typ, matt), id_, namn in ((("skjutningar", "skjutningar"), "skjutningar", "Skjutningar"),
                                       (("skjutningar", "avlidna"), "skjutningar_doda", "Döda i skjutningar"),
                                       (("sprängningar", "detonationer"), "sprangningar", "Sprängningar (detonationer)")):
            d = tot[(tot.typ == typ) & (tot.matt == matt)].groupby(["ar", "manad"]).antal.sum()
            if len(d):
                s = pd.Series(d.values, index=pd.PeriodIndex(
                    [pd.Period(year=int(a), month=int(m), freq="M") for a, m in d.index])).sort_index()
                lagg(id_, namn, "lag", "Polismyndigheten", "antal", s.astype(float), 2, "st")

    # Inflation (KPIF) mot Riksbankens mål
    for tab in ["TAB6590"] + _katalog_tab(katalog, r"(?i)^Konsumentprisindex med fast ränta \(KPIF\), \d{4}=100"):
        df = scb(tab)
        s = _valj(df, {}, r"(?i)12-mån")
        if s is None:
            s = _valj(df, {}, None)
            s = _yoy(s) if s is not None else None
        if s is not None and len(s) > 24:
            lagg("kpif", "KPIF, 12-månadersförändring (%)", "ekonomi", f"SCB {tab}", "niva", s, 1, "%")
            break

    # Arbetslöshet (AKU, säsongrensad)
    for tab in ["TAB6387"]:
        s = _valj(scb(tab), {r"(?i)arbetskraft": r"(?i)arbetslöshetstal", r"(?i)typ": r"(?i)^säsongrensad$",
                             r"(?i)ålder|alder": r"(?i)^totalt 15.74"}, None)
        lagg("aku", "Arbetslöshet 15–74 år, säsongrensad (AKU, %)", "jobb", f"SCB {tab}", "niva", s, 1, "%")

    # Priser på el och drivmedel: KPI per produktgrupp t.o.m. 2025, därefter KPIF per COICOP
    ny = scb("TAB6602")
    for namn, monster in KPI_GRUPPER:
        # Räntekostnader fanns bara i KPI-tabellen som upphörde 2025; styrräntan visas i stället
        if namn in ("El, lägenhet", "Räntekostnader"):
            continue
        gammal = kpi[kpi.serie == namn] if kpi is not None and not kpi.empty else pd.DataFrame()
        s = None
        if len(gammal):
            s = pd.Series(gammal.forandring_12m.values, index=pd.PeriodIndex(
                [pd.Period(year=int(a), month=int(m), freq="M") for a, m in zip(gammal.ar, gammal.manad)])).dropna()
        if ny is not None and namn != "Räntekostnader":
            coicop = {"El": r"(?i)^[\d.]*\s*el(ektricitet|ström)?\b(?!.*(gas|värme))",
                      "Bensin": r"(?i)bensin", "Diesel": r"(?i)diesel"}[namn]
            s2 = _valj(ny, {r"(?i)varu|tjänst|grupp": coicop}, None)
            if s2 is not None:
                s2 = _yoy(s2)
                s = s2 if s is None else pd.concat([s[s.index < s2.index.min()], s2]) \
                    if s2.index.min() > s.index.min() else s2.combine_first(s)
        if s is not None:
            s = s[s.index.year >= 2000]
            lagg(f"pris_{namn.lower()}", f"{namn}, prisförändring 12 mån (%)",
                 "energi" if namn == "El" else "egen_ekonomi", "SCB KPI/KPIF", "niva", s, 1, "%")

    # Styrräntan
    f = data_dir / "riksbanken" / "SECBREPOEFF.csv"
    if f.exists():
        d = pd.read_csv(f)
        dc = next((c for c in d.columns if "date" in c.lower()), None)
        vc = next((c for c in d.columns if "value" in c.lower()), None)
        if dc and vc:
            m = d.groupby(pd.to_datetime(d[dc]).dt.to_period("M"))[vc].mean()
            lagg("styrranta", "Styrräntan (%)", "egen_ekonomi", "Riksbanken", "niva", m, 0, "%")

    # Konkurser, påbörjade bostäder, invandring (SCB, hittas via sökning)
    for rubrik, id_, namn, fraga, val, inneh, lag in (
            (r"(?i)konkurs.*månad", "konkurser", "Konkurser", "ekonomi", {}, r"(?i)konkurs|antal", 2),
            (r"(?i)påbörjade.*lägenheter.*kvartal", "paborjade", "Påbörjade lägenheter i nybyggda hus", "bostad",
             {r"(?i)hustyp": TOTALT, r"(?i)region": r"(?i)riket"}, r"(?i)påbörjade|lägenheter", 4),
            (r"(?i)befolkningsförändringar.*månad", "invandringar", "Invandringar", "invandring",
             {r"(?i)förändring|händelse": r"(?i)^invandring"}, None, 2)):
        for tab in _katalog_tab(katalog[katalog.tema == "manad"], rubrik):
            s = _valj(scb(tab), val, inneh)
            if s is not None and len(s) >= 24:
                lagg(id_, namn, fraga, f"SCB {tab}", "antal", s, lag, "st")
                break
    return ut


def _sedan(r: pd.Series, hog: bool) -> int | None:
    """Första år bakåt då serien senast var lika hög (låg) som nu; None om aldrig."""
    x = r.iloc[-1]
    tidigare = r.iloc[:-1]
    over = tidigare[tidigare >= x] if hog else tidigare[tidigare <= x]
    return int(over.index[-1].year) if len(over) else None


def analys(post: dict, idag: date) -> dict:
    s, typ = post["s"], post["typ"]
    q = post["frekvens"] == "Q"
    n12, n3 = (4, 1) if q else (12, 3)
    sen = s.index[-1]
    rad = {k: post[k] for k in ("id", "namn", "fraga", "kalla", "typ", "enhet")}
    rad.update({"period": str(sen), "varde": float(s.iloc[-1])})
    if typ == "antal":
        r12 = s.rolling(n12).sum().dropna()
        k3 = s.rolling(n3).sum()
        forandr = (100 * (k3 / k3.shift(n12) - 1)).replace([np.inf, -np.inf], np.nan).dropna()
        rad.update({"tolv_man": float(r12.iloc[-1]),
                    "tolv_man_fjol": float(r12.iloc[-1 - n12]) if len(r12) > n12 else None,
                    "jmf_fjol": float(forandr.iloc[-1]) if len(forandr) else None,
                    "jmf_text": "senaste " + ("kvartalet" if q else "tre månaderna") + " mot samma period i fjol, %"})
        niva = r12
    else:
        d3, d12 = s.diff(n3).dropna(), s.diff(n12).dropna()
        forandr = d3
        rad.update({"tolv_man": None, "tolv_man_fjol": float(s.iloc[-1 - n12]) if len(s) > n12 else None,
                    "jmf_fjol": float(d12.iloc[-1]) if len(d12) else None,
                    "jmf_text": "mot samma månad i fjol, procentenheter"})
        niva = s
    hist = forandr[forandr.index.year >= sen.year - 10].iloc[:-1]
    z = None
    if len(hist) >= 24 and hist.std() > 0 and len(forandr):
        z = float((forandr.iloc[-1] - hist.mean()) / hist.std())
    hog, lag_ = _sedan(niva, True), _sedan(niva, False)
    start = niva.index[0].year
    ar_hog = (sen.year - hog) if hog else (sen.year - start)
    ar_lag = (sen.year - lag_) if lag_ else (sen.year - start)
    extrem, extrem_ar = None, 0
    if ar_hog >= 5 and ar_hog >= ar_lag:
        extrem, extrem_ar = ("högsta" + (f" sedan {hog}" if hog else f" i serien (från {start})")), ar_hog
    elif ar_lag >= 5:
        extrem, extrem_ar = ("lägsta" + (f" sedan {lag_}" if lag_ else f" i serien (från {start})")), ar_lag
    manader_sedan = (idag.year - sen.year) * 12 + idag.month - (sen.end_time.month if q else sen.month)
    status = "normal"
    if z is not None and abs(z) >= 1.5 or extrem_ar >= 5:
        status = "bevaka"
    if z is not None and abs(z) >= 2 or extrem_ar >= 10:
        status = "larm"
    if manader_sedan > post["lag"] + 2:
        status = "inaktuell"
    m = mal(post["namn"])
    rad.update({"z": z, "extrem": extrem, "manader_sedan": manader_sedan, "status": status,
                "mal_varde": m["mal_varde"], "mal_text": m["mal_text"], "mal_kalla": m["mal_kalla"]})
    rad["text"] = _text(rad)
    return rad


def _tal(x, d=1):
    if x is None or pd.isna(x):
        return "–"
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


MANAD = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september",
         "oktober", "november", "december"]


def _pertext(p: str) -> str:
    if "Q" in p:
        return f"kvartal {p[-1]} {p[:4]}"
    return f"{MANAD[int(p[5:7]) - 1]} {p[:4]}"


def _text(r: dict) -> str:
    d = 0 if r["typ"] == "antal" else 1
    tecken = lambda x: ("+" if x > 0 else "") + _tal(x, 0 if r["typ"] == "antal" else 1)  # noqa: E731
    per = _pertext(r["period"])
    if r["typ"] == "antal":
        m = [f"{per.capitalize()}: {_tal(r['varde'], 0)}."]
        if r["tolv_man"] is not None:
            m.append(f"Senaste tolv månaderna: {_tal(r['tolv_man'], 0)}"
                     + (f" (året innan {_tal(r['tolv_man_fjol'], 0)})." if r["tolv_man_fjol"] else "."))
        if r["jmf_fjol"] is not None:
            m.append(f"De tre senaste månaderna: {tecken(r['jmf_fjol'])} % mot samma månader i fjol.")
        if r["extrem"]:
            m.append(f"Tolvmånaderssumman är den {r['extrem']}.")
    else:
        m = [f"{per.capitalize()}: {_tal(r['varde'], d)} {r['enhet']}".rstrip() + "."]
        if r["jmf_fjol"] is not None:
            m.append(f"{tecken(r['jmf_fjol'])} procentenheter mot ett år tidigare.")
        if r["extrem"]:
            m.append(f"Nivån är den {r['extrem']}.")
    if r["mal_varde"] is not None:
        m.append(f"Mål: {_tal(r['mal_varde'])} ({r['mal_kalla']}).")
    if r["status"] == "inaktuell":
        m.append(f"Senaste värdet är {r['manader_sedan']} månader gammalt.")
    return " ".join(m)


STATUS_ORDNING = {"larm": 0, "bevaka": 1, "normal": 2, "inaktuell": 3}
STATUS_TEXT = {"larm": "Ovanlig utveckling", "bevaka": "Värd att bevaka", "normal": "Inom det vanliga",
               "inaktuell": "Inaktuell källa"}


def rapport(lb: pd.DataFrame, idag: date) -> str:
    v = idag.isocalendar()
    rader = [f"# Lägesbild vecka {v.week} {v.year}", "",
             f"Skapad {idag.isoformat()} ur Polisens, SCB:s och Riksbankens senaste siffror. "
             "Statusen jämför den senaste förändringen med seriens egen historik; den säger inte varför "
             "något har hänt och inte om det är bra eller dåligt.", ""]
    for st in STATUS_ORDNING:
        d = lb[lb.status == st]
        if d.empty:
            continue
        rader += [f"## {STATUS_TEXT[st]}", ""]
        rader += [f"- **{r.namn}**: {r.text} _Källa: {r.kalla}._" for r in d.itertuples()]
        rader.append("")
    return "\n".join(rader)


def bygg(scb, katalog, pol, kpi, data_dir: Path, idag: date | None = None):
    idag = idag or date.today()
    poster = serier(scb, katalog, pol, kpi, data_dir)
    if not poster:
        return pd.DataFrame(), pd.DataFrame(), ""
    lb = pd.DataFrame([analys(p, idag) for p in poster])
    lb["ordning"] = lb.status.map(STATUS_ORDNING)
    lb = lb.sort_values(["ordning", "fraga"]).drop(columns="ordning").reset_index(drop=True)
    ser = pd.concat([pd.DataFrame({"id": p["id"], "period": p["s"].index.astype(str), "varde": p["s"].values})
                     for p in poster], ignore_index=True)
    text = rapport(lb, idag)
    ut = data_dir / "lagesbild"
    ut.mkdir(parents=True, exist_ok=True)
    v = idag.isocalendar()
    (ut / "senaste.md").write_text(text, encoding="utf-8")
    (ut / f"{v.year}-V{v.week:02d}.md").write_text(text, encoding="utf-8")
    return lb, ser, text
