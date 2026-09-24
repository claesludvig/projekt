#!/usr/bin/env python3
"""HTML- och textmall för veckobrevet Bygg & fastighet. Rutinen skriver bara
texten (rapport-JSON); alla siffror, tabeller och grafer kommer ur
byggfastighet.json. Samma formspråk som Marknadspulsen och vinstbrevet.

    from mall import rendera, rendera_text
    html = rendera(rapport, data)
    text = rendera_text(rapport, data)

rapport = {
  "title": "Rubrik utan avslutande punkt",
  "ingress": "En mening om veckans viktigaste rörelse (valfri)",
  "drivkrafter": "Ett stycke om vad som driver sektorerna.",
  "punkter": [{"bold_lead": "Kort etikett", "text": "..."}],   # max 3
  "kallor": [{"namn": "SEB", "titel": "...", "url": "https://..."}]
}
"""

from html import escape

MANADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti",
           "september", "oktober", "november", "december"]
KOLUMNER = ["1d", "1v", "2v", "1m", "3m"]

C_TEXT, C_RUBRIK, C_DAMPAD, C_LINJE = "#2d3748", "#1a365d", "#718096", "#e2e8f0"
C_UPP, C_NER = "#276749", "#c53030"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
TD = "padding:5px 2px;font-size:12px;white-space:nowrap;"
TH = f"padding:5px 2px;font-size:10px;color:{C_DAMPAD};font-weight:600;text-align:right;border-bottom:1px solid {C_LINJE};"


def _datum(iso: str) -> str:
    ar, man, dag = (int(x) for x in iso[:10].split("-"))
    return f"{dag} {MANADER[man - 1]} {ar}"


def _kort(iso: str) -> str:
    return f"{int(iso[8:10])}/{int(iso[5:7])}"


def _tal(x: float, dec: int) -> str:
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" if x < 0 else "") + s


def fmt(x, enhet: str = "pct") -> str:
    if x is None:
        return "–"
    x = round(x) if enhet == "bp" else round(x, 1)
    if x == 0:
        return "0" if enhet == "bp" else "0,0"
    return ("+" if x > 0 else "") + _tal(x, 0 if enhet == "bp" else 1)


def _farg(x, enhet: str = "pct") -> str:
    if x is None or (round(x) if enhet == "bp" else round(x, 1)) == 0:
        return C_DAMPAD
    return C_UPP if x > 0 else C_NER


def _cell(x, enhet: str = "pct") -> str:
    return (f'<td style="{TD}text-align:right;color:{_farg(x, enhet)};font-variant-numeric:tabular-nums;">'
            f"{fmt(x, enhet)}</td>")


def _h2(text: str) -> str:
    return (f'<h2 style="color:{C_RUBRIK};font-size:16px;font-weight:700;margin:32px 0 6px 0;padding-bottom:5px;'
            f'border-bottom:1px solid {C_LINJE};text-transform:uppercase;letter-spacing:0.5px;">{escape(text)}</h2>')


def _h3(text: str, marginal: str = "18px 0 0 0") -> str:
    return f'<div style="margin:{marginal};font-size:14px;font-weight:700;color:{C_RUBRIK};">{escape(text)}</div>'


def _p(html_text: str, extra: str = "") -> str:
    return f'<p style="color:{C_TEXT};font-size:15px;line-height:1.6;margin:0 0 16px 0;{extra}">{html_text}</p>'


def _liten(text: str, marginal: str = "10px 0 0 0") -> str:
    return f'<div style="font-size:11px;color:{C_DAMPAD};margin:{marginal};line-height:1.5;">{text}</div>'


def _img(url: str, alt: str) -> str:
    return (f'<img src="{escape(url)}" width="520" alt="{escape(alt)}" '
            'style="display:block;width:100%;max-width:520px;height:auto;border:0;margin:6px 0 0 0;">')


def _tabell(huvud: list, rader: list) -> str:
    th = "".join(f'<th style="{TH}{"text-align:left;" if i == 0 else ""}">{escape(h)}</th>' for i, h in enumerate(huvud))
    return (f'<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;'
            f'font-family:{FONT};"><tr>{th}</tr>'
            + "".join(f'<tr style="border-bottom:1px solid #f0f4f8;">{r}</tr>' for r in rader) + "</table>")


def _namn(text: str, under: str = "") -> str:
    extra = f'<br><span style="color:{C_DAMPAD};font-size:10px;">{escape(under)}</span>' if under else ""
    return f'<td style="{TD}color:{C_TEXT};text-align:left;">{escape(text)}{extra}</td>'


def _grupp(data: dict, namn: str):
    return next((g for g in data["tabell"] if g["grupp"] == namn), None)


def _kurstabell(grupp: dict, data_t_o_m: str) -> str:
    rader = []
    for r in grupp["rader"]:
        under = f"per {_kort(r['datum'])}" if r["datum"] < data_t_o_m else ""
        rader.append(_namn(r["namn"], under) + "".join(_cell(r["forandring"].get(k)) for k in KOLUMNER))
    return _tabell([grupp["grupp"]] + KOLUMNER, rader)


def _rantetabell(grupp: dict) -> str:
    rader = [
        _namn(r["namn"]) + f'<td style="{TD}text-align:right;color:{C_TEXT};">{_tal(r["senast"], 2)} %</td>'
        + "".join(_cell(r["forandring"].get(k), "bp") for k in KOLUMNER)
        for r in grupp["rader"]
    ]
    return _tabell(["Ränta", "Senast"] + KOLUMNER, rader)


def _korr(v) -> str:
    return "–" if v is None else ("+" if v > 0 else "") + _tal(v, 2)


def _sambandsmening(namn: str, s: dict) -> str:
    k = s["korrelation"]
    txt = f"Korrelation mot {s['mot']}: 1m {_korr(k.get('1m'))}, 3m {_korr(k.get('3m'))}."
    if s.get("per_10bp_3m") is not None:
        txt += (f" Räntekänslighet: {namn.lower()}sindex har i snitt rört sig {fmt(s['per_10bp_3m'])} % "
                f"per 10 bp högre ränta senaste 3 månaderna.")
    return txt


def rendera(rapport: dict, data: dict) -> str:
    ar, g = data["ar"], data["grafer"]
    d = [
        f'<h1 style="color:{C_RUBRIK};font-size:21px;font-weight:700;letter-spacing:0.5px;margin:0 0 8px 0;text-transform:uppercase;">'
        f"{escape(rapport['title'])}</h1>",
        f'<div style="color:{C_DAMPAD};font-size:14px;font-style:italic;margin:0 0 20px 0;">'
        f"Bygg &amp; fastighet — vecka {data['vecka']}, stängningskurser t.o.m. {_datum(data['data_t_o_m'])}</div>",
    ]
    if rapport.get("ingress"):
        d.append(_p(escape(rapport["ingress"]), "font-weight:600;"))

    d.append(_h2("Sektorerna"))
    if _grupp(data, "Index"):
        d.append(_liten("Förändring i %", "14px 0 2px 0"))
        d.append(_kurstabell(_grupp(data, "Index"), data["data_t_o_m"]))
    if g.get("relativ_3m"):
        d.append(_h3("Fastighet och bygg mot OMXS30, 3 månader"))
        d.append(_img(g["relativ_3m"], "Fastighets- och byggindex mot OMXS30, 3 månader"))

    d.append(_h2("Räntorna"))
    if _grupp(data, "Räntor"):
        d.append(_liten("Svenska räntor, förändring i baspunkter", "14px 0 2px 0"))
        d.append(_rantetabell(_grupp(data, "Räntor")))
    for sektor in ("Fastighet", "Bygg"):
        s = data["samband"].get(sektor)
        nyckel = f"{sektor.lower()}_mot_ranta"
        if g.get(nyckel):
            d.append(_h3(f"{sektor}sindex mot {s['mot'] if s else 'räntan'}, 3 månader"))
            d.append(_img(g[nyckel], f"{sektor}sindex mot räntan, 3 månader"))
        if s:
            d.append(_liten(escape(_sambandsmening(sektor, s)), "6px 0 0 0"))
    d.append(_liten("Räntan ritas på en inverterad högeraxel: stigande ränta nedåt. Går linjerna ihop följer aktierna räntan på det väntade sättet."))

    for sektor in ("Fastighet", "Bygg"):
        grupp = _grupp(data, sektor)
        if grupp:
            d.append(_h2(f"{sektor}sbolagen"))
            d.append(_liten("Förändring i %, sorterat på 1m", "14px 0 2px 0"))
            d.append(_kurstabell(grupp, data["data_t_o_m"]))

    if data["prognoser_bygg"]:
        d.append(_h2("Vinstprognoser, byggbolagen"))
        rader = [
            _namn(r["namn"], f"rapport {_kort(r['nasta_rapport'])}" if r["nasta_rapport"] in {k["datum"] for k in data["kommande_rapporter"]} else "")
            + "".join(_cell(r[h]["revidering"].get(p)) for h in ("0y", "+1y") for p in ("1m", "3m"))
            + _cell(r.get("tillvaxt_nasta_ar"))
            for r in data["prognoser_bygg"]
        ]
        d.append(_liten(f"Ändrad vinstprognos (analytikerkonsensus) i %, och väntad vinsttillväxt {ar['+1y']} mot {ar['0y']}", "14px 0 2px 0"))
        d.append(_tabell(["Bolag", f"{ar['0y'][2:]} 1m", "3m", f"{ar['+1y'][2:]} 1m", "3m", "Tillväxt"], rader))

    if data["kommande_rapporter"]:
        d.append(_h3("Rapporter kommande tre veckor", "16px 0 4px 0"))
        d.append(_p(escape(", ".join(f"{k['namn']} {_kort(k['datum'])}" for k in data["kommande_rapporter"])), "font-size:14px;"))

    if rapport.get("drivkrafter") or rapport.get("punkter"):
        d.append(_h2("Vad driver sektorerna"))
        if rapport.get("drivkrafter"):
            d.append(_p(escape(rapport["drivkrafter"])))
        if rapport.get("punkter"):
            li = "".join(f'<li style="color:{C_TEXT};font-size:15px;line-height:1.6;margin-bottom:10px;">'
                         f'<strong style="color:{C_RUBRIK};">{escape(p["bold_lead"])}:</strong> {escape(p["text"])}</li>'
                         for p in rapport["punkter"][:3])
            d.append(f'<ul style="margin:0 0 16px 0;padding-left:20px;">{li}</ul>')

    fot = []
    if rapport.get("kallor"):
        fot.append("Källor: " + " · ".join(
            f'<a href="{escape(k["url"])}" style="color:{C_DAMPAD};">{escape(k["namn"])}: {escape(k["titel"])}</a>'
            if k.get("url") else f"{escape(k['namn'])}: {escape(k['titel'])}" for k in rapport["kallor"]))
    fot.append(escape(data["metod"]))
    if data.get("fel"):
        fot.append("Saknas: " + escape("; ".join(data["fel"])) + ".")
    fot.append("Denna rapport har genererats automatiskt av din personliga nyhetsbevakare.")
    d.append(f'<div style="margin-top:36px;border-top:1px solid #f0f4f8;padding-top:14px;font-size:11px;color:#a0aec0;line-height:1.6;">'
             + "<br>".join(fot) + "</div>")

    return ('<!DOCTYPE html>\n<html>\n<head>\n  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n'
            f'<body style="background-color:#f4f6f8;font-family:{FONT};margin:0;padding:0;">\n'
            '  <div style="background-color:#f4f6f8;padding:12px 4px;">\n'
            '    <div style="background-color:#ffffff;max-width:600px;margin:0 auto;border-radius:8px;'
            'border-top:6px solid #1a365d;box-shadow:0 4px 12px rgba(0,0,0,0.08);overflow:hidden;">\n'
            '      <div style="padding:24px 14px;">\n' + "\n".join(d)
            + "\n      </div>\n    </div>\n  </div>\n</body>\n</html>\n")


def rendera_text(rapport: dict, data: dict) -> str:
    ar = data["ar"]
    ut = [rapport["title"], f"Bygg & fastighet — vecka {data['vecka']}, stängningskurser t.o.m. {_datum(data['data_t_o_m'])}", ""]
    if rapport.get("ingress"):
        ut += [rapport["ingress"], ""]
    for grupp in data["tabell"]:
        bp = grupp["grupp"] == "Räntor"
        ut.append(f"{grupp['grupp'].upper() + (' (bp)' if bp else ' (%)'):<19}" + (f"{'Senast':>8}" if bp else "")
                  + "".join(f"{k:>7}" for k in KOLUMNER))
        for r in grupp["rader"]:
            namn = r["namn"] if r["datum"] >= data["data_t_o_m"] or bp else f"{r['namn']} ({_kort(r['datum'])})"
            ut.append(f"{namn:<19}" + (f"{_tal(r['senast'], 2) + ' %':>8}" if bp else "")
                      + "".join(f"{fmt(r['forandring'].get(k), 'bp' if bp else 'pct'):>7}" for k in KOLUMNER))
        ut.append("")
    for sektor, s in data["samband"].items():
        ut.append(f"{sektor}: " + _sambandsmening(sektor, s))
    for nyckel, url in data["grafer"].items():
        ut.append(f"Graf {nyckel}: {url}")
    if data["prognoser_bygg"]:
        ut += ["", f"VINSTPROGNOSER BYGG — ändring % ({ar['0y']} 1m/3m | {ar['+1y']} 1m/3m | tillväxt)"]
        for r in data["prognoser_bygg"]:
            ut.append(f"{r['namn']:<12}" + "".join(f"{fmt(r[h]['revidering'].get(p)):>7}" for h in ("0y", "+1y") for p in ("1m", "3m"))
                      + f"{fmt(r.get('tillvaxt_nasta_ar')):>8}")
    if data["kommande_rapporter"]:
        ut += ["", "Rapporter kommande tre veckor: " + ", ".join(f"{k['namn']} {_kort(k['datum'])}" for k in data["kommande_rapporter"])]
    if rapport.get("drivkrafter") or rapport.get("punkter"):
        ut += ["", "VAD DRIVER SEKTORERNA"]
        if rapport.get("drivkrafter"):
            ut.append(rapport["drivkrafter"])
        ut += [f"- {p['bold_lead']}: {p['text']}" for p in rapport.get("punkter", [])[:3]]
    if rapport.get("kallor"):
        ut += ["", "Källor:"] + [f"- {k['namn']}: {k['titel']} {k.get('url', '')}".rstrip() for k in rapport["kallor"]]
    ut += ["", data["metod"]]
    if data.get("fel"):
        ut.append("Saknas: " + "; ".join(data["fel"]))
    return "\n".join(ut) + "\n"
