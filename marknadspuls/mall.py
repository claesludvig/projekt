#!/usr/bin/env python3
"""HTML- och textmall för Marknadspulsen. Rutinen skriver bara texten
(rapport-JSON); alla siffror, tabeller och grafer kommer ur marknadspuls.json
så att formen och datan aldrig glider mellan körningarna.

    from mall import rendera, rendera_text
    html = rendera(rapport, data)
    text = rendera_text(rapport, data)

rapport = {
  "title": "Rubrik utan avslutande punkt",
  "ingress": "En mening om dagens största rörelse (valfri)",
  "drivkrafter": "Ett stycke om vad som driver rörelserna i tabellerna.",
  "punkter": [{"bold_lead": "Kort etikett", "text": "Koppling mellan rörelse och orsak."}],   # max 3
  "kallor": [{"namn": "ING", "titel": "...", "url": "https://..."}]
}
"""

from html import escape

MANADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti",
           "september", "oktober", "november", "december"]

C_TEXT, C_RUBRIK, C_DAMPAD, C_LINJE = "#2d3748", "#1a365d", "#718096", "#e2e8f0"
C_UPP, C_NER = "#276749", "#c53030"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def _datum(iso: str) -> str:
    ar, man, dag = (int(x) for x in iso[:10].split("-"))
    return f"{dag} {MANADER[man - 1]} {ar}"


def _tal(x: float, dec: int) -> str:
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" if x < 0 else "") + s


def fmt_senast(rad: dict) -> str:
    v = rad["senast"]
    if rad["enhet"] == "bp":
        return _tal(v, 2) + " %"
    if abs(v) >= 1000:
        return _tal(v, 0)
    if abs(v) >= 20:
        return _tal(v, 2)
    return _tal(v, 4 if "/" in rad["namn"] else 2)


def fmt_andring(x, enhet: str) -> str:
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


ENHET_ETIKETT = {"pct": "%", "bp": "bp", "pts": "p"}


def _tabell_html(grupp: dict, perioder: list, data_t_o_m: str) -> str:
    th = f"padding:5px 2px;font-size:10px;color:{C_DAMPAD};font-weight:600;text-align:right;border-bottom:1px solid {C_LINJE};"
    enheter = {r["enhet"] for r in grupp["rader"]}
    enhet_txt = "förändring i bp" if enheter == {"bp"} else "förändring i %"
    rader = []
    for r in grupp["rader"]:
        gammal = r["datum"] < data_t_o_m
        namn = escape(r["namn"])
        if r["enhet"] != "pct" and enheter != {r["enhet"]}:
            namn += f' <span style="color:{C_DAMPAD};font-size:10px;">({ENHET_ETIKETT[r["enhet"]]})</span>'
        if gammal:
            namn += f'<br><span style="color:{C_DAMPAD};font-size:10px;">per {int(r["datum"][8:])}/{int(r["datum"][5:7])}</span>'
        celler = [
            f'<td style="padding:5px 2px;font-size:12px;color:{C_TEXT};text-align:left;white-space:nowrap;">{namn}</td>',
            f'<td style="padding:5px 2px;font-size:12px;color:{C_TEXT};text-align:right;white-space:nowrap;">{fmt_senast(r)}</td>',
        ]
        for p in perioder:
            x = r["forandring"].get(p)
            celler.append(
                f'<td style="padding:5px 2px;font-size:12px;text-align:right;white-space:nowrap;'
                f'color:{_farg(x, r["enhet"])};font-variant-numeric:tabular-nums;">{fmt_andring(x, r["enhet"])}</td>'
            )
        rader.append(f'<tr style="border-bottom:1px solid #f0f4f8;">{"".join(celler)}</tr>')
    huvud = (
        f'<th style="{th}text-align:left;">{escape(grupp["grupp"])}</th><th style="{th}">Senast</th>'
        + "".join(f'<th style="{th}">{p}</th>' for p in perioder)
    )
    return (
        f'<div style="font-size:11px;color:{C_DAMPAD};margin:22px 0 2px 0;text-transform:uppercase;letter-spacing:0.5px;">'
        f"{escape(grupp['grupp'])} — {enhet_txt}</div>"
        f'<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;font-family:{FONT};">'
        f"<tr>{huvud}</tr>{''.join(rader)}</table>"
    )


def _korr_txt(k: dict) -> str:
    v = k.get("varde")
    return "–" if v is None else ("+" if v > 0 else "") + _tal(v, 2)


def _korr_ord(v) -> str:
    if v is None:
        return "för få observationer"
    a = abs(v)
    styrka = "inget tydligt" if a < 0.2 else "svagt" if a < 0.4 else "måttligt" if a < 0.6 else "starkt"
    if a < 0.2:
        return "inget tydligt samband"
    return f"{styrka} {'positivt' if v > 0 else 'negativt'} samband"


def _h2(text: str) -> str:
    return (
        f'<h2 style="color:{C_RUBRIK};font-size:16px;font-weight:700;margin:32px 0 6px 0;padding-bottom:5px;'
        f'border-bottom:1px solid {C_LINJE};text-transform:uppercase;letter-spacing:0.5px;">{escape(text)}</h2>'
    )


def _p(html_text: str, extra: str = "") -> str:
    return f'<p style="color:{C_TEXT};font-size:15px;line-height:1.6;margin:0 0 16px 0;{extra}">{html_text}</p>'


def rendera(rapport: dict, data: dict) -> str:
    perioder = data["perioder"]
    delar = [
        f'<h1 style="color:{C_RUBRIK};font-size:21px;font-weight:700;letter-spacing:0.5px;margin:0 0 8px 0;text-transform:uppercase;">'
        f"{escape(rapport['title'])}</h1>",
        f'<div style="color:{C_DAMPAD};font-size:14px;font-style:italic;margin:0 0 20px 0;">'
        f"Marknadspulsen — stängningskurser t.o.m. {_datum(data['data_t_o_m'])}</div>",
    ]
    if rapport.get("ingress"):
        delar.append(_p(escape(rapport["ingress"]), "font-weight:600;"))

    delar.append(_h2("Marknadsrörelser"))
    for grupp in data["tabell"]:
        delar.append(_tabell_html(grupp, perioder, data["data_t_o_m"]))
    delar.append(
        f'<div style="font-size:11px;color:{C_DAMPAD};margin:10px 0 0 0;line-height:1.5;">{escape(data["periodforklaring"])}</div>'
    )

    if data["par"]:
        delar.append(_h2("Samband — senaste månaden"))
        for par in data["par"]:
            k1, k3 = par["korrelation"]["1m"], par["korrelation"]["3m"]
            delar.append(
                f'<div style="margin:18px 0 4px 0;font-size:14px;font-weight:700;color:{C_RUBRIK};">'
                f"{escape(par['a'])} mot {escape(par['b'])}</div>"
                f'<div style="font-size:12px;color:{C_DAMPAD};margin:0 0 6px 0;">'
                f"Korrelation 1m: <strong style=\"color:{C_TEXT};\">{_korr_txt(k1)}</strong> ({_korr_ord(k1.get('varde'))})"
                f" · 3m: {_korr_txt(k3)}</div>"
                f'<img src="{escape(par["graf_url"])}" width="520" alt="{escape(par["a"])} mot {escape(par["b"])}, 1 månad" '
                f'style="display:block;width:100%;max-width:520px;height:auto;border:0;">'
            )
        delar.append(
            f'<div style="font-size:11px;color:{C_DAMPAD};margin:10px 0 0 0;line-height:1.5;">{escape(data["korrelationsforklaring"])}</div>'
        )

    if rapport.get("drivkrafter") or rapport.get("punkter"):
        delar.append(_h2("Vad driver marknaden"))
        if rapport.get("drivkrafter"):
            delar.append(_p(escape(rapport["drivkrafter"])))
        if rapport.get("punkter"):
            li = "".join(
                f'<li style="color:{C_TEXT};font-size:15px;line-height:1.6;margin-bottom:10px;">'
                f'<strong style="color:{C_RUBRIK};">{escape(p["bold_lead"])}:</strong> {escape(p["text"])}</li>'
                for p in rapport["punkter"][:3]
            )
            delar.append(f'<ul style="margin:0 0 16px 0;padding-left:20px;">{li}</ul>')

    fot = []
    if rapport.get("kallor"):
        lankar = " · ".join(
            f'<a href="{escape(k["url"])}" style="color:{C_DAMPAD};">{escape(k["namn"])}: {escape(k["titel"])}</a>'
            if k.get("url") else f"{escape(k['namn'])}: {escape(k['titel'])}"
            for k in rapport["kallor"]
        )
        fot.append(f"Källor: {lankar}")
    fot.append("Marknadsdata: Yahoo Finance (yfinance). " + (
        "Saknas: " + escape("; ".join(data["fel"])) + "." if data.get("fel") else ""))
    fot.append("Denna rapport har genererats automatiskt av din personliga nyhetsbevakare.")

    delar.append(
        f'<div style="margin-top:36px;border-top:1px solid #f0f4f8;padding-top:14px;font-size:11px;color:#a0aec0;line-height:1.6;">'
        + "<br>".join(fot)
        + "</div>"
    )

    return (
        '<!DOCTYPE html>\n<html>\n<head>\n  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n'
        f'<body style="background-color:#f4f6f8;font-family:{FONT};margin:0;padding:0;">\n'
        '  <div style="background-color:#f4f6f8;padding:12px 4px;">\n'
        '    <div style="background-color:#ffffff;max-width:600px;margin:0 auto;border-radius:8px;'
        'border-top:6px solid #1a365d;box-shadow:0 4px 12px rgba(0,0,0,0.08);overflow:hidden;">\n'
        '      <div style="padding:24px 14px;">\n'
        + "\n".join(delar)
        + "\n      </div>\n    </div>\n  </div>\n</body>\n</html>\n"
    )


def rendera_text(rapport: dict, data: dict) -> str:
    perioder = data["perioder"]
    rader = [rapport["title"], f"Marknadspulsen — stängningskurser t.o.m. {_datum(data['data_t_o_m'])}", ""]
    if rapport.get("ingress"):
        rader += [rapport["ingress"], ""]
    for grupp in data["tabell"]:
        rader.append(f"{grupp['grupp'].upper():<16}{'Senast':>10}" + "".join(f"{p:>7}" for p in perioder))
        for r in grupp["rader"]:
            namn = r["namn"] if r["datum"] >= data["data_t_o_m"] else f"{r['namn']} ({int(r['datum'][8:])}/{int(r['datum'][5:7])})"
            rader.append(
                f"{namn:<16}{fmt_senast(r):>10}"
                + "".join(f"{fmt_andring(r['forandring'].get(p), r['enhet']):>7}" for p in perioder)
            )
        rader.append("")
    rader.append(data["periodforklaring"])
    if data["par"]:
        rader += ["", "SAMBAND — SENASTE MÅNADEN"]
        for par in data["par"]:
            k1, k3 = par["korrelation"]["1m"], par["korrelation"]["3m"]
            rader.append(f"{par['a']} mot {par['b']}: korrelation 1m {_korr_txt(k1)}, 3m {_korr_txt(k3)} — {par['graf_url']}")
    if rapport.get("drivkrafter") or rapport.get("punkter"):
        rader += ["", "VAD DRIVER MARKNADEN"]
        if rapport.get("drivkrafter"):
            rader.append(rapport["drivkrafter"])
        for p in rapport.get("punkter", [])[:3]:
            rader.append(f"- {p['bold_lead']}: {p['text']}")
    if rapport.get("kallor"):
        rader += ["", "Källor:"] + [f"- {k['namn']}: {k['titel']} {k.get('url', '')}".rstrip() for k in rapport["kallor"]]
    if data.get("fel"):
        rader += ["", "Saknas: " + "; ".join(data["fel"])]
    return "\n".join(rader) + "\n"


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Rendera Marknadspulsen till HTML (förhandsvisning).")
    ap.add_argument("rapport")
    ap.add_argument("data", nargs="?", default=str(Path(__file__).parent / "data" / "marknadspuls.json"))
    ap.add_argument("-o", "--ut", default="forhandsvisning.html")
    a = ap.parse_args()
    rap = json.loads(Path(a.rapport).read_text(encoding="utf-8"))
    dat = json.loads(Path(a.data).read_text(encoding="utf-8"))
    Path(a.ut).write_text(rendera(rap, dat), encoding="utf-8")
    print(rendera_text(rap, dat))
