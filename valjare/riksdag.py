"""Politikens svar: riksdagens beslut, partiernas röster och opinionen.

Tabeller:
  riksdag_dokument       propositioner och betänkanden, klassade till sakfrågor
  riksdag_beslut         en rad per votering i sakfrågan: utfall och partiernas röster
  riksdag_aktivitet      antal propositioner, betänkanden och voteringar per sakfråga och riksmöte
  riksdag_samstammighet hur ofta två partier röstar lika, per mandatperiod
  riksdag_parti_fraga    hur ofta partiet röstar med den vinnande sidan, per sakfråga och mandatperiod
  riksdag_ledamot        ledamöter per riksmöte med valkrets och närvaro
  opinion                SOM: senaste värdet för förslag och förtroende (2022 och 2025)
  opinion_beslut         SOM-förslagen och riksdagens beslut i samma sak, med partiernas röster
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

import tolka
from riksdag_katalog import FORTROENDE, OPINION, ORD, UTGIFTSOMRADE, UTSKOTT

PARTIER = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]
VALAR = [2010, 2014, 2018, 2022, 2026]
PARTIKOD = {"FP": "L", "L": "L", "S": "S", "M": "M", "SD": "SD", "C": "C", "V": "V", "KD": "KD", "MP": "MP"}


def _period(rm: str) -> str | None:
    a = int(str(rm)[:4])
    p = max((v for v in VALAR if v <= a), default=None)
    return None if p is None else f"{p}–{p + 4}"


def _utskott(bet: str) -> str | None:
    m = re.match(r"^([A-ZÅÄÖ][A-Za-zåäöÅÄÖ]*?)\d", str(bet))
    return m[1] if m else None


def klassa(titel: str, utskott: str | None = None) -> list[str]:
    t = re.sub(r"\s+", " ", str(titel).lower()).strip()
    if m := re.search(r"utgiftsområde (\d+)", t):
        return list(UTGIFTSOMRADE.get(int(m[1]), []))
    if "ålderspensionssystemet vid sidan av statens budget" in t:
        return ["pension"]
    fr = [f for f, rx in ORD.items() if re.search(rx, t)]
    if not fr and utskott in UTSKOTT:
        fr = [UTSKOTT[utskott]]
    return fr


def _las(mapp: Path, monster: str, **kw) -> pd.DataFrame:
    delar = []
    for f in sorted(mapp.glob(monster)):
        try:
            d = pd.read_csv(f, dtype=str, **kw)
        except (pd.errors.EmptyDataError, ValueError):
            continue
        if len(d):
            delar.append(d)
    return pd.concat(delar, ignore_index=True) if delar else pd.DataFrame()


def dokument(mapp: Path) -> pd.DataFrame:
    d = pd.concat([_las(mapp, "prop_*.csv"), _las(mapp, "bet_*.csv")], ignore_index=True)
    if d.empty:
        return d
    d = d.drop_duplicates("dok_id")
    # Regeringens skrivelser (t.ex. svar på Riksrevisionens rapporter) listas som prop i API:t
    if "subtyp" in d:
        d.loc[(d.doktyp == "prop") & (d.subtyp == "skr"), "doktyp"] = "skr"
    d["utskott"] = np.where(d.doktyp == "bet", d.beteckning.map(_utskott), None)
    d["fragor"] = [",".join(klassa(t, u)) for t, u in zip(d.titel, d.utskott)]
    d["url"] = d.dokument_url_html.fillna("").str.replace(r"^//", "https://", regex=True)
    d["datum"] = d.datum.str[:10]
    return d[["dok_id", "doktyp", "rm", "beteckning", "titel", "undertitel", "organ", "utskott", "datum", "fragor", "url"]]


def _position(r) -> str | None:
    rost = {"ja": r.get("ja", 0), "nej": r.get("nej", 0), "avstår": r.get("avstar", 0)}
    if sum(rost.values()) == 0:
        return None
    return max(rost, key=rost.get)


def voteringar(mapp: Path) -> pd.DataFrame:
    v = _las(mapp, "votering_*.csv.gz")
    if v.empty:
        return v
    for c in ("ja", "nej", "avstar", "franvarande"):
        v[c] = pd.to_numeric(v[c], errors="coerce").fillna(0).astype(int) if c in v else 0
    v["parti"] = v.parti.map(PARTIKOD).fillna("-")
    if "avser" in v:
        v = v[v.avser.fillna("sakfrågan").str.lower().str.startswith("sak")]
    if "votering" in v:
        v = v[v.votering.fillna("huvud").str.lower().str.startswith("huvud")]
    v = v.groupby([c for c in ("rm", "beteckning", "punkt", "votering_id", "datum") if c in v]
                  + ["parti"], dropna=False)[["ja", "nej", "avstar", "franvarande"]].sum().reset_index()
    v["position"] = [_position(r) for r in v.to_dict("records")]
    return v


def beslut(vot: pd.DataFrame, dok: pd.DataFrame) -> pd.DataFrame:
    if vot.empty:
        return pd.DataFrame()
    bet = dok[dok.doktyp == "bet"].set_index(["rm", "beteckning"])
    rader = []
    for (rm, b, p, vid), d in vot.groupby(["rm", "beteckning", "punkt", "votering_id"], dropna=False):
        ja, nej = int(d.ja.sum()), int(d.nej.sum())
        info = bet.loc[(rm, b)] if (rm, b) in bet.index else None
        if isinstance(info, pd.DataFrame):
            info = info.iloc[0]
        pos = {r.parti: r.position for r in d.itertuples() if r.parti in PARTIER}
        rader.append({"rm": rm, "beteckning": b, "punkt": p, "votering_id": vid,
                      "datum": (d.datum.iloc[0] if "datum" in d and isinstance(d.datum.iloc[0], str) else
                                (info.datum if info is not None else None)),
                      "titel": info.titel if info is not None else None,
                      "fragor": info.fragor if info is not None else ",".join(klassa("", _utskott(b))),
                      "ja": ja, "nej": nej, "avstar": int(d.avstar.sum()), "franvarande": int(d.franvarande.sum()),
                      "utfall": "bifall" if ja > nej else "avslag",
                      **{f"p_{k}": pos.get(k) for k in PARTIER}})
    b = pd.DataFrame(rader)
    b["datum"] = b.datum.astype(str).str[:10]
    b["period"] = b.rm.map(_period)
    return b


def aktivitet(dok: pd.DataFrame, bes: pd.DataFrame) -> pd.DataFrame:
    rader = []
    for (rm, typ), d in dok.groupby(["rm", "doktyp"]):
        for fr in d.fragor.str.split(",").explode().dropna():
            if fr:
                rader.append({"rm": rm, "fraga": fr, "typ": typ})
    a = pd.DataFrame(rader)
    if a.empty:
        return a
    a = a.groupby(["rm", "fraga", "typ"]).size().unstack(fill_value=0).reset_index()
    a = a.rename(columns={"prop": "propositioner", "bet": "betankanden", "skr": "skrivelser"})
    if not bes.empty:
        v = bes.assign(fraga=bes.fragor.fillna("").str.split(",")).explode("fraga")
        v = v[v.fraga != ""].groupby(["rm", "fraga"]).size().rename("voteringar").reset_index()
        a = a.merge(v, on=["rm", "fraga"], how="left")
    return a.fillna(0)


def samstammighet(bes: pd.DataFrame) -> pd.DataFrame:
    rader = []
    for per, d in bes.groupby("period"):
        for a in PARTIER:
            for b in PARTIER:
                x = d[[f"p_{a}", f"p_{b}"]].dropna()
                x = x[x.iloc[:, 0].isin(["ja", "nej"]) & x.iloc[:, 1].isin(["ja", "nej"])]
                if len(x):
                    rader.append({"period": per, "parti_a": a, "parti_b": b, "n": len(x),
                                  "andel_lika": 100 * float((x.iloc[:, 0] == x.iloc[:, 1]).mean())})
    return pd.DataFrame(rader)


def parti_fraga(bes: pd.DataFrame) -> pd.DataFrame:
    b = bes.assign(fraga=bes.fragor.fillna("").str.split(",")).explode("fraga")
    b = b[b.fraga != ""]
    rader = []
    for (per, fr), d in b.groupby(["period", "fraga"]):
        vinn = np.where(d.utfall == "bifall", "ja", "nej")
        for p in PARTIER:
            pos = d[f"p_{p}"]
            ok = pos.isin(["ja", "nej"])
            if ok.sum() < 5:
                continue
            rader.append({"period": per, "fraga": fr, "parti": p, "n": int(ok.sum()),
                          "andel_vinnande": 100 * float((pos[ok] == vinn[ok.values]).mean())})
    return pd.DataFrame(rader)


def ledamoter(mapp: Path) -> pd.DataFrame:
    led = _las(mapp, "ledamot_*.csv.gz")
    if led.empty:
        return led
    for c in ("ja", "nej", "avstar", "franvarande"):
        led[c] = pd.to_numeric(led[c], errors="coerce").fillna(0).astype(int) if c in led else 0
    tot = led[["ja", "nej", "avstar", "franvarande"]].sum(axis=1)
    led["voteringar"] = tot
    led["narvaro"] = 100 * (1 - led.franvarande / tot.replace(0, np.nan))
    led["parti"] = led.parti.map(PARTIKOD).fillna(led.parti)
    if "namn" not in led and {"fornamn", "efternamn"} <= set(led.columns):
        led["namn"] = led.fornamn + " " + led.efternamn
    return led


def opinion(kall_dir: Path) -> pd.DataFrame:
    delar = []
    for doc in ("som_trender_1986_2022", "som_trender_1986_2025"):
        f = kall_dir / "txt" / f"{doc}.txt"
        if f.exists():
            delar.append(tolka.som_asikter(f, doc))
    d = pd.concat([x for x in delar if not x.empty], ignore_index=True) if delar else pd.DataFrame()
    return d.drop_duplicates(["ar", "rubrik", "serie"]) if len(d) else d


def opinion_beslut(op: pd.DataFrame, dok: pd.DataFrame, bes: pd.DataFrame, prop_bet: pd.DataFrame,
                   fran_ar: int = 2018) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(förslag: opinion per år) och (förslag: propositioner i samma sak med utfall och röster)."""
    forslag, kopplade = [], []
    props = dok[(dok.doktyp == "prop") & (dok.datum.fillna("") >= f"{fran_ar}-09")]
    for oid, fr, rub, ser, namn, rx in OPINION:
        if not op.empty:
            o = op[op.rubrik.str.contains(rub, regex=True, na=False) & op.serie.str.contains(ser, regex=True, na=False)]
            for r in o.drop_duplicates("ar").itertuples():
                forslag.append({"id": oid, "fraga": fr, "forslag": namn, "ar": r.ar, "andel": r.andel,
                                "serie": r.serie, "rubrik": r.rubrik})
        if not rx:
            continue
        for p in props[props.titel.fillna("").str.contains(rx, regex=True)].itertuples():
            bets = prop_bet[prop_bet.prop_id == p.dok_id] if not prop_bet.empty else pd.DataFrame()
            v = pd.DataFrame()
            for br in bets.itertuples():
                if isinstance(br.bet, str) and not bes.empty:
                    v = pd.concat([v, bes[(bes.rm == br.bet_rm) & (bes.beteckning == br.bet)]])
            rad = {"id": oid, "dok_id": p.dok_id, "rm": p.rm, "beteckning": p.beteckning, "titel": p.titel,
                   "datum": p.datum, "url": p.url,
                   "betankande": ", ".join(f"{b.bet_rm}:{b.bet}" for b in bets.itertuples() if isinstance(b.bet, str)),
                   "voteringar": len(v)}
            if len(v):
                # Den votering där flest röstade emot säger mest om oenigheten
                s = v.sort_values("nej", ascending=False).iloc[0]
                rad.update({"ja": int(s.ja), "nej": int(s.nej), "utfall": s.utfall,
                            **{f"p_{k}": s[f"p_{k}"] for k in PARTIER}})
            kopplade.append(rad)
    return pd.DataFrame(forslag), pd.DataFrame(kopplade)


def bygg(data_dir: Path, kall_dir: Path) -> dict[str, pd.DataFrame]:
    mapp = data_dir / "riksdagen"
    op = opinion(kall_dir)
    ut = {"opinion": op}
    if not mapp.exists():
        return ut
    dok = dokument(mapp)
    if dok.empty:
        return ut
    vot = voteringar(mapp)
    bes = beslut(vot, dok)
    pb = _las(mapp, "prop_bet.csv")
    of, ob = opinion_beslut(op, dok, bes, pb)
    ut.update({"riksdag_dokument": dok, "riksdag_beslut": bes, "riksdag_aktivitet": aktivitet(dok, bes),
               "riksdag_samstammighet": samstammighet(bes) if len(bes) else pd.DataFrame(),
               "riksdag_parti_fraga": parti_fraga(bes) if len(bes) else pd.DataFrame(),
               "riksdag_ledamot": ledamoter(mapp), "opinion_forslag": of, "opinion_beslut": ob})
    return ut


def fortroende(op: pd.DataFrame) -> pd.DataFrame:
    if op.empty:
        return op
    return op[op.rubrik.str.contains("(?i)förtroende för samhällsinstitutioner", na=False)
              & op.serie.str.contains(FORTROENDE, regex=True, na=False)]


def utvardera(facit: pd.DataFrame) -> pd.DataFrame:
    """Träffsäkerhet mot handkodat facit: precision, täckning och F1 per sakfråga.

    facit: dok_id, titel, facit ("fraga;fraga" eller tomt). Klassningen görs på titeln."""
    rader = []
    gissat = [set(klassa(t)) for t in facit.titel]
    ratt = [set(x for x in str(f).split(";") if x and x != "nan") for f in facit.facit]
    for fr in sorted(set().union(*ratt, *gissat)):
        tp = sum(fr in g and fr in r for g, r in zip(gissat, ratt))
        fp = sum(fr in g and fr not in r for g, r in zip(gissat, ratt))
        fn = sum(fr not in g and fr in r for g, r in zip(gissat, ratt))
        p_ = tp / (tp + fp) if tp + fp else None
        r_ = tp / (tp + fn) if tp + fn else None
        rader.append({"fraga": fr, "ratt": tp, "felaktigt_tillagd": fp, "missad": fn, "precision": p_,
                      "tackning": r_, "f1": 2 * p_ * r_ / (p_ + r_) if p_ and r_ else 0.0})
    tp = sum(len(g & r) for g, r in zip(gissat, ratt))
    fp = sum(len(g - r) for g, r in zip(gissat, ratt))
    fn = sum(len(r - g) for g, r in zip(gissat, ratt))
    rader.append({"fraga": "TOTALT", "ratt": tp, "felaktigt_tillagd": fp, "missad": fn,
                  "precision": tp / (tp + fp) if tp + fp else None, "tackning": tp / (tp + fn) if tp + fn else None,
                  "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
                  "exakt": sum(g == r for g, r in zip(gissat, ratt)) / len(ratt)})
    return pd.DataFrame(rader)
