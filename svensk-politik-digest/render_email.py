#!/usr/bin/env python3
"""Renderar latest_articles.json till ett mejl.

Används både av workflowets mejlsteg och för manuella utskick, så att
formatet bara finns på ett ställe.

Kör: python svensk-politik-digest/render_email.py [utfil.html]
Skriver HTML till utfilen (standard: data/email.html) och ämnesraden till
stdout, så ett anropande skal kan plocka upp den.
"""

import html
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "latest_articles.json"

RUBRIKER = [
    ("kommentar", "Analys och kommentar"),
    ("nyhet", "Rapportering"),
    ("officiell", "Officiella besked"),
]

# Inline-stilar: e-postklienter plockar bort <style>-block.
BRODTEXT = "font-family:Georgia,'Times New Roman',serif;color:#1a1a1a;"
DAMPAD = "color:#6b6b6b;font-size:13px;"


def esc(t: str) -> str:
    return html.escape(t or "", quote=True)


def markering(a: dict) -> str:
    """Kort notis om varför brödtexten saknas - eller att det är en kommentator."""
    delar = []
    if a.get("commentator"):
        delar.append(
            '<span style="background:#fff3cd;color:#664d03;font-size:11px;'
            'padding:2px 6px;border-radius:3px;">KOMMENTATOR</span>'
        )
    if a.get("fetch_error"):
        delar.append(f'<span style="{DAMPAD}">brödtext ej hämtad</span>')
    elif a.get("paywall"):
        delar.append(f'<span style="{DAMPAD}">betalvägg</span>')
    return " ".join(delar)


def render(data: dict) -> tuple[str, str]:
    artiklar = data.get("articles", [])
    dag = data.get("fetched_at", "")[:10]
    antal = data.get("new_count", len(artiklar))
    amne = f"Svensk politik & regeringsförhandlingarna – {dag} ({antal} nya)"

    rader = [
        f'<div style="{BRODTEXT}max-width:640px;margin:0 auto;padding:24px 16px;">',
        '<h1 style="font-size:22px;margin:0 0 4px;">Svensk politik och '
        "regeringsförhandlingarna</h1>",
        f'<p style="{DAMPAD}margin:0 0 20px;">{esc(dag)} · {antal} nya poster sedan '
        f'förra utskicket · {data.get("skipped", {}).get("seen", 0)} redan utskickade, '
        f'{data.get("skipped", {}).get("offtopic", 0)} utanför ämnet</p>',
    ]

    if not artiklar:
        rader.append('<p style="font-size:16px;">Inget nytt sedan förra utskicket.</p>')

    for kind, rubrik in RUBRIKER:
        grupp = [a for a in artiklar if a.get("kind") == kind]
        if not grupp:
            continue
        rader.append(
            f'<h2 style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;'
            f'color:#6b6b6b;border-bottom:1px solid #e0e0e0;padding-bottom:6px;'
            f'margin:28px 0 16px;">{esc(rubrik)}</h2>'
        )
        for a in grupp:
            meta = " · ".join(
                x for x in [a.get("source"), a.get("published"), a.get("author")] if x
            )
            flagg = markering(a)
            ingress = a.get("summary") or " ".join(a.get("fulltext", "").split()[:60])
            rader += [
                '<div style="margin:0 0 22px;">',
                f'<a href="{esc(a.get("url", ""))}" style="font-size:17px;'
                f'font-weight:bold;color:#0b3d91;text-decoration:none;">'
                f'{esc(a.get("title", ""))}</a>',
                f'<div style="{DAMPAD}margin:4px 0 6px;">{esc(meta)}'
                + (f" &nbsp;{flagg}" if flagg else "")
                + "</div>",
                f'<div style="font-size:15px;line-height:1.5;">{esc(ingress)}</div>',
                "</div>",
            ]

    rader.append(
        f'<p style="{DAMPAD}border-top:1px solid #e0e0e0;padding-top:12px;'
        f'margin-top:28px;">Genererat {esc(data.get("fetched_at", "")[:19])} · '
        "svensk-politik-digest</p></div>"
    )
    return amne, "\n".join(rader)


def main() -> int:
    if not DATA.exists():
        print("saknar data/latest_articles.json", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    amne, kropp = render(data)
    ut = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA.parent / "email.html"
    ut.write_text(kropp, encoding="utf-8")
    print(amne)
    return 0


if __name__ == "__main__":
    sys.exit(main())
