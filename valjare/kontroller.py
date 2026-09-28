"""Automatiska kvalitetskontroller efter varje bygge.

Tre slags kontroller:
  aktualitet  har källan kommit med nya siffror inom normal eftersläpning?
  volym       har någon tabell krympt kraftigt eller blivit tom sedan förra körningen?
  rimlighet   stämmer summor och kända storheter (349 mandat, 100 procent, 29 valkretsar)?

Status per kontroll: ok, varning, fel. Körningens status är den värsta. Vid fel
öppnar arbetsflödet ett ärende i GitHub (se .github/workflows/valjare.yml).

Filer: data/kvalitet.json, data/kvalitet.md, data/katalog/radantal.json (jämförelsebas).
"""

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ORDNING = {"ok": 0, "varning": 1, "fel": 2}
KRYMPNING = 0.2       # mer än 20 procent färre rader än förra körningen = fel
ARSSERIE_LAG = 3      # årsserie utan värde de senaste tre åren = varning


def _k(grupp, id_, beskrivning, status, detalj="", varde=None):
    return {"grupp": grupp, "id": id_, "beskrivning": beskrivning, "status": status,
            "detalj": detalj, "varde": None if varde is None else float(varde)}


def aktualitet(t: dict, idag: date) -> list[dict]:
    ut = []
    lb = t.get("lagesbild", pd.DataFrame())
    for r in lb.itertuples() if len(lb) else []:
        ut.append(_k("aktualitet", f"lage_{r.id}", f"Månadsserie: {r.namn}",
                     "varning" if r.status == "inaktuell" else "ok",
                     f"senaste {r.period}, {r.manader_sedan} månader sedan", r.manader_sedan))
    v = t.get("verklighet", pd.DataFrame())
    if len(v):
        r = v[v.niva == "riket"].groupby("indikator").ar_dec.max()
        for ind, a in r.items():
            ar = int(np.floor(a))
            ut.append(_k("aktualitet", f"verk_{ind}", f"Årsserie: {ind}",
                         "varning" if ar < idag.year - ARSSERIE_LAG else "ok", f"senaste år {ar}", ar))
    n = t.get("norden", pd.DataFrame())
    if len(n):
        for sid, d in n[n.geo == "SE"].groupby("id"):
            ar = int(np.floor(d.ar_dec.max()))
            ut.append(_k("aktualitet", f"norden_{sid}", f"Eurostat: {d.namn.iloc[0]}",
                         "varning" if ar < idag.year - ARSSERIE_LAG else "ok", f"senaste år för Sverige {ar}", ar))
    om = t.get("media_omnamnanden", pd.DataFrame())
    gn = t.get("media_google_nyheter", pd.DataFrame())
    if len(gn):
        dagar = (pd.Timestamp(idag) - pd.to_datetime(gn.dag).max()).days
        ut.append(_k("aktualitet", "nyhetsfloden", "Nyhetsflödena (Google Nyheter)",
                     "varning" if dagar > 7 else "ok", f"senaste artikel för {dagar} dagar sedan", dagar))
    if len(om):
        n = int(om.drop_duplicates(["vecka", "flode"]).totalt.sum())
        ut.append(_k("aktualitet", "redaktionsfloden", "Redaktionernas nyhetsflöden", "ok" if n > 0 else "varning",
                     f"{n} artiklar i {om.flode.nunique()} flöden", n))
    fl = t.get("media_foljare_nu", pd.DataFrame())
    ut.append(_k("aktualitet", "wikidata_foljare", "Följarantal från Wikidata", "ok" if len(fl) else "varning",
                 f"{len(fl)} konton med följarantal" if len(fl) else "inga följarantal hämtade", len(fl)))
    dok = t.get("riksdag_dokument", pd.DataFrame())
    if len(dok):
        sista = pd.to_datetime(dok.datum, errors="coerce").max()
        dagar = (pd.Timestamp(idag) - sista).days
        riksmote = idag.month not in (7, 8)
        ut.append(_k("aktualitet", "riksdag_dokument", "Riksdagens dokument", "varning" if riksmote and dagar > 45 else "ok",
                     f"senaste dokument {sista.date()}, {dagar} dagar sedan", dagar))
    return ut


def volym(t: dict, bas: dict) -> list[dict]:
    ut = []
    for namn, df in t.items():
        n = len(df)
        forra = bas.get(namn)
        if forra is None:
            continue
        if forra > 0 and n == 0:
            ut.append(_k("volym", f"rader_{namn}", f"Tabell {namn}", "fel", f"tom, förra körningen {forra} rader", n))
        elif forra > 0 and n < (1 - KRYMPNING) * forra:
            ut.append(_k("volym", f"rader_{namn}", f"Tabell {namn}", "fel",
                         f"{n} rader mot {forra} förra körningen ({100 * (n / forra - 1):.0f} %)", n))
        else:
            ut.append(_k("volym", f"rader_{namn}", f"Tabell {namn}", "ok", f"{n} rader (förra {forra})", n))
    return ut


def rimlighet(t: dict) -> list[dict]:
    ut = []

    def lagg(id_, beskr, ok, detalj, varde=None, niva="fel"):
        ut.append(_k("rimlighet", id_, beskr, "ok" if ok else niva, detalj, varde))

    vk = t.get("valkrets", pd.DataFrame())
    if len(vk):
        lagg("valkretsar_29", "29 valkretsar", len(vk) == 29, f"{len(vk)} valkretsar", len(vk))
        for ar in (2022, 2026):
            col = f"mandat_{ar}"
            if col in vk:
                s = vk[col].sum()
                lagg(f"mandat_{ar}", f"Mandaten {ar} summerar till 349", s == 349, f"summa {s:.0f}", s)
    km = t.get("valkrets_kommun", pd.DataFrame())
    if len(km):
        lagg("kommuner_290", "290 kommuner i valkretsindelningen", km.kommunkod.nunique() == 290,
             f"{km.kommunkod.nunique()} kommuner", km.kommunkod.nunique())
    res = t.get("valresultat_valkrets", pd.DataFrame())
    if len(res):
        s = res[res.parti != "valdeltagande"].groupby(["ar", "valkrets_kod"]).andel.sum()
        avv = float((s - 100).abs().max())
        lagg("valkrets_andelar_100", "Partiernas andelar per valkrets summerar till 100", avv < 0.5,
             f"största avvikelse {avv:.2f} procentenheter", avv)
    prof = t.get("partiprofil", pd.DataFrame())
    if len(prof) and {"parti", "dimension", "andel"} <= set(prof.columns):
        tid = "period" if "period" in prof else "ar"
        s = prof.groupby(["kalla", tid, "parti", "dimension"]).andel.sum()
        s = s[s > 0]
        andel_ok = float(((s - 100).abs() < 2).mean())
        lagg("profil_100", "Partiprofilerna summerar till 100 inom varje indelning", andel_ok > 0.9,
             f"{100 * andel_ok:.0f} % av profilerna inom ±2 procentenheter", 100 * andel_ok, niva="varning")
    bes = t.get("riksdag_beslut", pd.DataFrame())
    if len(bes):
        tot = bes.ja + bes.nej + bes.avstar + bes.franvarande
        andel_ok = float(tot.between(340, 349).mean())
        lagg("voteringar_349", "Varje votering räknar alla 349 ledamöter", andel_ok > 0.95,
             f"{100 * andel_ok:.1f} % av {len(bes)} voteringar har 340–349 röster inklusive frånvaro", 100 * andel_ok)
    ss = t.get("riksdag_samstammighet", pd.DataFrame())
    if len(ss):
        d = ss[ss.parti_a == ss.parti_b].andel_lika
        lagg("samstammighet_diagonal", "Ett parti röstar alltid som sig självt", bool((d == 100).all()),
             f"diagonalen {d.min():.0f}–{d.max():.0f} %")
    of = t.get("opinion_forslag", pd.DataFrame())
    if len(of):
        per_ar = of.groupby("ar").id.nunique()
        lagg("som_forslag", "SOM-förslagen hittas i rapporterna", per_ar.max() >= 10,
             ", ".join(f"{a}: {n}" for a, n in per_ar.items()), per_ar.max(), niva="varning")
    n = t.get("norden", pd.DataFrame())
    if len(n):
        saknar = sorted(set(n.id) - set(n[n.geo == "SE"].id))
        lagg("norden_sverige", "Sverige finns i alla nordiska serier", not saknar,
             "saknas i: " + ", ".join(saknar) if saknar else f"{n.id.nunique()} serier", niva="varning")
    lb = t.get("lagesbild", pd.DataFrame())
    lagg("lagesbild_serier", "Lägesbilden har minst sex månadsserier", len(lb) >= 6, f"{len(lb)} serier", len(lb),
         niva="varning")
    return ut


def kor(t: dict, data_dir: Path, varningar: list[str], idag: date | None = None) -> pd.DataFrame:
    idag = idag or date.today()
    basfil = data_dir / "katalog" / "radantal.json"
    bas = json.loads(basfil.read_text()) if basfil.exists() else {}
    rader = aktualitet(t, idag) + volym(t, bas) + rimlighet(t)
    rader += [_k("tolkning", f"varning_{i}", "Varning vid tolkning", "varning", v) for i, v in enumerate(varningar)]
    k = pd.DataFrame(rader)
    status = max(k.status, key=ORDNING.get) if len(k) else "ok"
    (data_dir / "kvalitet.json").write_text(json.dumps(
        {"skapad": idag.isoformat(), "status": status, "antal": k.status.value_counts().to_dict(),
         "kontroller": k.replace({np.nan: None}).to_dict("records")}, ensure_ascii=False, indent=1), encoding="utf-8")
    (data_dir / "kvalitet.md").write_text(rapport(k, status, idag), encoding="utf-8")
    # Ny jämförelsebas, men inte om tabeller har krympt (då ska nästa körning jämföra med det friska läget)
    if status != "fel":
        basfil.parent.mkdir(parents=True, exist_ok=True)
        basfil.write_text(json.dumps({n: len(df) for n, df in t.items()}, indent=1), encoding="utf-8")
    return k


def rapport(k: pd.DataFrame, status: str, idag: date) -> str:
    rubrik = {"ok": "Alla kontroller är gröna", "varning": "Varningar", "fel": "Fel som behöver åtgärdas"}[status]
    rader = [f"## Väljardatabasen: kvalitetskontroll {idag.isoformat()}", "", f"**{rubrik}.**", ""]
    for st in ("fel", "varning"):
        d = k[k.status == st]
        if len(d):
            rader += [f"### {st.capitalize()} ({len(d)})", ""] + \
                     [f"- **{r.beskrivning}** ({r.grupp}): {r.detalj}" for r in d.itertuples()] + [""]
    rader.append(f"{int((k.status == 'ok').sum())} av {len(k)} kontroller är ok.")
    return "\n".join(rader)
