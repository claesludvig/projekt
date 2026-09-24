#!/usr/bin/env python3
"""HTML- och textmall för veckobrevet om vinstförväntningar. Rutinen skriver
bara texten (rapport-JSON); alla siffror, tabeller och grafer kommer ur
vinst.json. Samma formspråk som Marknadspulsen.

    from mall import rendera, rendera_text
    html = rendera(rapport, data)
    text = rendera_text(rapport, data)

rapport = {
  "title": "Rubrik utan avslutande punkt",
  "ingress": "En mening om veckans viktigaste revidering (valfri)",
  "drivkrafter": "Ett stycke om vad som driver revideringarna.",
  "punkter": [{"bold_lead": "Kort etikett", "text": "..."}],   # max 3
  "kallor": [{"namn": "SEB", "titel": "...", "url": "https://..."}]
}
"""

from html import escape

MANADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti",
           "september", "oktober", "november", "december"]

C_TEXT, C_RUBRIK, C_DAMPAD, C_LINJE = "#2d3748", "#1a365d", "#718096", "#e2e8f0"
C_UPP, C_NER = "#276749", "#c53030"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
TD = "padding:5px 2px;font-size:12px;white-space:nowrap;"
TH = f"padding:5px 2px;font-size:10px;color:{C_DAMPAD};font-weight:600;text-align:right;border-bottom:1px solid {C_LINJE};"


def _datum(iso: str) -> str:
    ar, man, dag = (int(x) for x in iso[:10].split("-"))
    return f"{dag} {MANADER[man - 1]} {ar}"


def _kort_datum(iso: str) -> str:
    return f"{int(iso[8:10])}/{int(iso[5:7])}"


def _tal(x: float, dec: int) -> str:
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" if x < 0 else "") + s


def fmt_pct(x, dec: int = 1) -> str:
    if x is None:
        return "–"
    x = round(x, dec)
    if x == 0:
        return "0," + "0" * dec
    return ("+" if x > 0 else "") + _tal(x, dec)


def _farg(x, dec: int = 1) -> str:
    if x is None or round(x, dec) == 0:
        return C_DAMPAD
    return C_UPP if x > 0 else C_NER


def _cell(x, dec: int = 1) -> str:
    return (f'<td style="{TD}text-align:right;color:{_farg(x, dec)};font-variant-numeric:tabular-nums;">'
            f"{fmt_pct(x, dec)}</td>")


def _h2(text: str) -> str:
    return (
        f'<h2 style="color:{C_RUBRIK};font-size:16px;font-weight:700;margin:32px 0 6px 0;padding-bottom:5px;'
        f'border-bottom:1px solid {C_LINJE};text-transform:uppercase;letter-spacing:0.5px;">{escape(text)}</h2>'
    )


def _p(html_text: str, extra: str = "") -> str:
    return f'<p style="color:{C_TEXT};font-size:15px;line-height:1.6;margin:0 0 16px 0;{extra}">{html_text}</p>'


def _liten(text: str, marginal: str = "10px 0 0 0") -> str:
    return f'<div style="font-size:11px;color:{C_DAMPAD};margin:{marginal};line-height:1.5;">{text}</div>'


def _img(url: str, alt: str) -> str:
    return (f'<img src="{escape(url)}" width="520" alt="{escape(alt)}" '
            'style="display:block;width:100%;max-width:520px;height:auto;border:0;margin:6px 0 0 0;">')


def _tabell(huvud: list, rader: list) -> str:
    th = "".join(
        f'<th style="{TH}{"text-align:left;" if i == 0 else ""}">{escape(h)}</th>' for i, h in enumerate(huvud)
    )
    return (
        f'<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;'
        f'font-family:{FONT};"><tr>{th}</tr>'
        + "".join(f'<tr style="border-bottom:1px solid #f0f4f8;">{r}</tr>' for r in rader)
        + "</table>"
    )


def _namncell(text: str, under: str = "") -> str:
    extra = f'<br><span style="color:{C_DAMPAD};font-size:10px;">{escape(under)}</span>' if under else ""
    return f'<td style="{TD}color:{C_TEXT};text-align:left;">{escape(text)}{extra}</td>'


def _nyckeltal(data: dict) -> list:
    """Meningar med indexets nyckeltal, gemensamma för HTML och text."""
    idx, ar = data["index"], data["ar"]
    ut = []
    b = idx.get("bredd_1m") or {}
    if b:
        tot = b["hojda"] + b["sankta"] + b["oforandrade"]
        ut.append(f"Senaste månaden har {b['hojda']} av {tot} bolag fått höjd vinstprognos för {ar['+1y']} "
                  f"och {b['sankta']} sänkt.")
    a = idx.get("analytikerrevideringar_30d") or {}
    if a and (a.get("upp") or a.get("ner")):
        ut.append(f"Enskilda analytiker har höjt {a['upp']} gånger och sänkt {a['ner']} gånger.")
    if idx.get("tillvaxt_nasta_ar") is not None:
        ut.append(f"Väntad vinsttillväxt {ar['+1y']} mot {ar['0y']}: {fmt_pct(idx['tillvaxt_nasta_ar'])} %.")
    if None not in (idx.get("kurs_3m"), idx.get("eps_nasta_ar_3m"), idx.get("vardering_3m")):
        ut.append(f"Senaste 90 dagarna: OMXS30 {fmt_pct(idx['kurs_3m'])} %, vinstprognosen för {ar['+1y']} "
                  f"{fmt_pct(idx['eps_nasta_ar_3m'])} %, alltså värdering (P/E) {fmt_pct(idx['vardering_3m'])} %.")
    return ut


def rendera(rapport: dict, data: dict) -> str:
    ar, idx, perioder = data["ar"], data["index"], data["perioder"]
    delar = [
        f'<h1 style="color:{C_RUBRIK};font-size:21px;font-weight:700;letter-spacing:0.5px;margin:0 0 8px 0;text-transform:uppercase;">'
        f"{escape(rapport['title'])}</h1>",
        f'<div style="color:{C_DAMPAD};font-size:14px;font-style:italic;margin:0 0 20px 0;">'
        f"Vinstförväntningar OMXS30 — vecka {data['vecka']}, analytikerkonsensus per {_datum(data['datum'])}</div>",
    ]
    if rapport.get("ingress"):
        delar.append(_p(escape(rapport["ingress"]), "font-weight:600;"))

    delar.append(_h2("Indexet"))
    rader = []
    for h in ("0y", "+1y"):
        rader.append(_namncell(f"Vinstprognos {ar[h]}") + "".join(_cell(idx["revidering"][h].get(p), 2) for p in perioder))
    delar.append(_liten("Ändrad vinstprognos, börsvärdesviktad, %", "14px 0 2px 0"))
    delar.append(_tabell(["OMXS30"] + perioder, rader))
    nyckel = _nyckeltal(data)
    if nyckel:
        delar.append(f'<p style="color:{C_TEXT};font-size:14px;line-height:1.6;margin:12px 0 0 0;">{escape(" ".join(nyckel))}</p>')
    if data["grafer"].get("vinst_mot_kurs"):
        delar.append(f'<div style="margin:18px 0 0 0;font-size:14px;font-weight:700;color:{C_RUBRIK};">Vinstprognos mot kurs, 90 dagar</div>')
        delar.append(_img(data["grafer"]["vinst_mot_kurs"], "Vinstprognos mot OMXS30-kursen, 90 dagar"))
        delar.append(_liten("Kursen över prognosen = högre värdering. Prognospunkterna är Yahoos konsensus i dag och 7, 30, 60 och 90 dagar sedan."))

    delar.append(_h2("Bolagen"))
    if data["grafer"].get("revideringar_1m"):
        delar.append(f'<div style="margin:12px 0 0 0;font-size:14px;font-weight:700;color:{C_RUBRIK};">'
                     f"Ändrad vinstprognos {ar['+1y']}, senaste månaden</div>")
        delar.append(_img(data["grafer"]["revideringar_1m"], f"Ändrad vinstprognos {ar['+1y']} per bolag, senaste månaden"))
    rader = []
    for r in data["bolag"]:
        under = f"rapport {_kort_datum(r['nasta_rapport'])}" if r["nasta_rapport"] in {k["datum"] for k in data["kommande_rapporter"]} else ""
        rader.append(
            _namncell(r["namn"], under)
            + "".join(_cell(r[h]["revidering"].get(p)) for h in ("0y", "+1y") for p in ("1v", "1m", "3m"))
        )
    delar.append(_liten(f"Ändrad vinstprognos i %. Vänster: {ar['0y']}, höger: {ar['+1y']}. Sorterat på {ar['+1y']}, 1m.", "18px 0 2px 0"))
    delar.append(_tabell(["Bolag", f"{ar['0y'][2:]} 1v", "1m", "3m", f"{ar['+1y'][2:]} 1v", "1m", "3m"], rader))

    if data["kommande_rapporter"]:
        delar.append(_h2("Rapporter kommande tre veckor"))
        delar.append(_p(escape(", ".join(f"{k['namn']} {_kort_datum(k['datum'])}" for k in data["kommande_rapporter"])),
                        "font-size:14px;"))

    if rapport.get("drivkrafter") or rapport.get("punkter"):
        delar.append(_h2("Vad driver prognoserna"))
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
        fot.append("Källor: " + " · ".join(
            f'<a href="{escape(k["url"])}" style="color:{C_DAMPAD};">{escape(k["namn"])}: {escape(k["titel"])}</a>'
            if k.get("url") else f"{escape(k['namn'])}: {escape(k['titel'])}"
            for k in rapport["kallor"]
        ))
    fot.append(escape(data["metod"]))
    if data.get("fel"):
        fot.append("Saknas: " + escape("; ".join(data["fel"])) + ".")
    fot.append("Denna rapport har genererats automatiskt av din personliga nyhetsbevakare.")
    delar.append(
        f'<div style="margin-top:36px;border-top:1px solid #f0f4f8;padding-top:14px;font-size:11px;color:#a0aec0;line-height:1.6;">'
        + "<br>".join(fot) + "</div>"
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
    ar, idx, perioder = data["ar"], data["index"], data["perioder"]
    ut = [rapport["title"], f"Vinstförväntningar OMXS30 — vecka {data['vecka']}, analytikerkonsensus per {_datum(data['datum'])}", ""]
    if rapport.get("ingress"):
        ut += [rapport["ingress"], ""]
    ut.append("INDEXET — ändrad vinstprognos, börsvärdesviktad, %")
    ut.append(f"{'':<22}" + "".join(f"{p:>7}" for p in perioder))
    for h in ("0y", "+1y"):
        ut.append(f"{'Vinstprognos ' + ar[h]:<22}" + "".join(f"{fmt_pct(idx['revidering'][h].get(p), 2):>7}" for p in perioder))
    ut += [""] + _nyckeltal(data)
    if data["grafer"].get("vinst_mot_kurs"):
        ut.append(f"Graf, vinstprognos mot kurs: {data['grafer']['vinst_mot_kurs']}")
    ut += ["", f"BOLAGEN — ändrad vinstprognos i %, {ar['0y']} | {ar['+1y']}"]
    ut.append(f"{'':<15}" + "".join(f"{p:>6}" for p in ("1v", "1m", "3m")) + " |" + "".join(f"{p:>6}" for p in ("1v", "1m", "3m")))
    for r in data["bolag"]:
        ut.append(
            f"{r['namn']:<15}" + "".join(f"{fmt_pct(r['0y']['revidering'].get(p)):>6}" for p in ("1v", "1m", "3m"))
            + " |" + "".join(f"{fmt_pct(r['+1y']['revidering'].get(p)):>6}" for p in ("1v", "1m", "3m"))
        )
    if data["kommande_rapporter"]:
        ut += ["", "RAPPORTER KOMMANDE TRE VECKOR", ", ".join(f"{k['namn']} {_kort_datum(k['datum'])}" for k in data["kommande_rapporter"])]
    if rapport.get("drivkrafter") or rapport.get("punkter"):
        ut += ["", "VAD DRIVER PROGNOSERNA"]
        if rapport.get("drivkrafter"):
            ut.append(rapport["drivkrafter"])
        ut += [f"- {p['bold_lead']}: {p['text']}" for p in rapport.get("punkter", [])[:3]]
    if rapport.get("kallor"):
        ut += ["", "Källor:"] + [f"- {k['namn']}: {k['titel']} {k.get('url', '')}".rstrip() for k in rapport["kallor"]]
    ut += ["", data["metod"]]
    if data.get("fel"):
        ut.append("Saknas: " + "; ".join(data["fel"]))
    return "\n".join(ut) + "\n"
