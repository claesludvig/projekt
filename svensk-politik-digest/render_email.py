#!/usr/bin/env python3
"""Renderar utskicket till ett mejl i samma formspråk som podd-rapporterna.

Analysen (data/analysis.json) är huvudinnehållet: rubrik, brödtext och
punktlista. Källistan ligger sist - till skillnad från poddrapporten bygger
det här utskicket på många artiklar, och då behöver läsaren kunna gå vidare
till originalen.

Saknas analysen faller mejlet tillbaka på enbart källistan, så ett utskick
alltid går ut även om analyssteget hoppats över.

Kör: python svensk-politik-digest/render_email.py [utfil.html]
Skriver HTML till utfilen och ämnesraden till stdout.
"""

import html
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "latest_articles.json"
ANALYS = Path(__file__).resolve().parent / "data" / "analysis.json"

MARIN = "#1a365d"
BROD = "#2d3748"
DAMPAD = "#718096"
LJUS = "#a0aec0"

RUBRIKER = [
    ("kommentar", "Analys och kommentar"),
    ("nyhet", "Rapportering"),
    ("officiell", "Officiella besked"),
]


def esc(t: str) -> str:
    return html.escape(t or "", quote=True)


def kallista(artiklar: list[dict]) -> list[str]:
    rader = []
    for kind, rubrik in RUBRIKER:
        grupp = [a for a in artiklar if a.get("kind") == kind]
        if not grupp:
            continue
        rader.append(
            f'<h3 style="color:{MARIN};font-size:13px;font-weight:700;margin:22px 0 10px 0;'
            f'letter-spacing:0.5px;text-transform:uppercase">{esc(rubrik)}</h3>'
        )
        for a in grupp:
            meta = " · ".join(
                x for x in [a.get("source"), a.get("published"), a.get("author")] if x
            )
            if a.get("commentator"):
                meta += " · kommentator"
            if a.get("fetch_error"):
                meta += " · endast ingress"
            elif a.get("paywall"):
                meta += " · betalvägg"
            rader.append(
                f'<div style="margin:0 0 12px 0">'
                f'<a href="{esc(a.get("url",""))}" style="color:{MARIN};font-size:14px;'
                f'font-weight:600;text-decoration:none">{esc(a.get("title",""))}</a>'
                f'<div style="color:{LJUS};font-size:12px;margin-top:2px">{esc(meta)}</div>'
                f"</div>"
            )
    return rader


def render(data: dict, analys: dict | None = None) -> tuple[str, str]:
    artiklar = data.get("articles", [])
    dag = data.get("fetched_at", "")[:10]
    antal = data.get("new_count", len(artiklar))

    if analys and analys.get("headline"):
        rubrik = analys["headline"]
    elif artiklar:
        rubrik = "Nytt om regeringsbildningen"
    else:
        rubrik = "Inget nytt sedan förra utskicket"
    amne = f"[politik]: {rubrik}"

    kropp = [
        f'<div style="background-color:#f4f6f8;padding:40px 20px">',
        f'<div style="background-color:#ffffff;max-width:600px;margin:0 auto;'
        f'border-radius:8px;border-top:6px solid {MARIN};overflow:hidden">',
        '<div style="padding:35px 40px">',
        f'<h1 style="color:{MARIN};font-size:22px;font-weight:700;letter-spacing:0.5px;'
        f'margin:0 0 10px 0;text-transform:uppercase">{esc(rubrik)}</h1>',
        f'<div style="color:{DAMPAD};font-size:14px;font-style:italic;margin:0 0 25px 0">'
        f"Analys baserad på {antal} nya poster den {esc(dag)}</div>",
    ]

    if analys:
        for stycke in analys.get("paragraphs", []):
            kropp.append(
                f'<p style="color:{BROD};font-size:15px;line-height:1.6;margin:0 0 20px 0">'
                f"{esc(stycke)}</p>"
            )
        punkter = analys.get("bullets", [])
        if punkter:
            kropp.append(
                f'<h2 style="color:{MARIN};font-size:17px;font-weight:700;margin:30px 0 15px 0;'
                f'padding-bottom:5px;border-bottom:1px solid #e2e8f0;text-transform:uppercase;'
                f'letter-spacing:0.5px">Viktigaste händelserna</h2>'
            )
            kropp.append('<ul style="margin:0 0 20px 0;padding-left:20px">')
            for p in punkter:
                kropp.append(
                    f'<li style="color:{BROD};font-size:15px;line-height:1.6;margin-bottom:12px">'
                    f'<strong style="color:{MARIN}">{esc(p.get("lead",""))}</strong> '
                    f'{esc(p.get("text",""))}</li>'
                )
            kropp.append("</ul>")
    elif artiklar:
        kropp.append(
            f'<p style="color:{BROD};font-size:15px;line-height:1.6;margin:0 0 20px 0">'
            f"Ingen analys genererad för det här utskicket. Nedan ligger materialet "
            f"i sin helhet.</p>"
        )
    else:
        kropp.append(
            f'<p style="color:{BROD};font-size:15px;line-height:1.6;margin:0 0 20px 0">'
            f"Inget nytt har tillkommit sedan förra utskicket.</p>"
        )

    if artiklar:
        kropp.append(
            f'<h2 style="color:{MARIN};font-size:17px;font-weight:700;margin:30px 0 15px 0;'
            f'padding-bottom:5px;border-bottom:1px solid #e2e8f0;text-transform:uppercase;'
            f'letter-spacing:0.5px">Källor</h2>'
        )
        kropp += kallista(artiklar)

    hoppat = data.get("skipped", {})
    kropp += [
        f'<div style="margin-top:40px;border-top:1px solid #f0f4f8;padding-top:15px;'
        f'font-size:12px;color:{LJUS};text-align:center">'
        f'{hoppat.get("seen", 0)} poster var redan utskickade och togs inte med · '
        f"Denna rapport har genererats automatiskt av din personliga nyhetsbevakare."
        f"</div>",
        "</div></div></div>",
    ]
    return amne, "\n".join(kropp)


def las_analys() -> dict | None:
    if not ANALYS.exists():
        return None
    try:
        return json.loads(ANALYS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"kunde inte läsa analysen ({e}) - fortsätter utan", file=sys.stderr)
        return None


def main() -> int:
    if not DATA.exists():
        print("saknar data/latest_articles.json", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    amne, kropp = render(data, las_analys())
    ut = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA.parent / "email.html"
    ut.write_text(kropp, encoding="utf-8")
    print(amne)
    return 0


if __name__ == "__main__":
    sys.exit(main())
