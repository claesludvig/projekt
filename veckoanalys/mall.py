#!/usr/bin/env python3
"""HTML- och textmall för Veckoanalysen (marknadsläget). Rutinen skriver bara
texten som rapport-JSON; formen ligger här så att utseendet aldrig glider.

    from mall import rendera, rendera_text
    html = rendera(rapport)
    text = rendera_text(rapport)

rapport = {
  "etikett": "Veckoanalys · Inför veckan" | "Veckoanalys · Halvvägs",
  "datum": "Söndag 8 november 2026",
  "title": "Rubrik som bär tesen, utan avslutande punkt",
  "dek": "Två meningar som sammanfattar tesen.",
  "sektioner": [{"rubrik": "Kort rubrik", "stycken": ["Stycke ...", "..."]}],   # 4–6 sektioner, sista heter "Bedömning"
  "att_folja": "En mening om veckans viktigaste händelser.",
  "kallor": [{"namn": "SEB", "titel": "...", "url": "https://..."}],
  "underlag": "Valfri rad om dataunderlag och vad som saknades."
}
"""

from html import escape

INK, MUTED, DEK, ACCENT, PAPER, LINE = "#1f2933", "#7b8794", "#52606d", "#9b2c2c", "#f6f3ee", "#e4ddd2"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def rendera(r: dict) -> str:
    d = [
        f'<div style="font-family:{SANS};font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{ACCENT};font-weight:700;margin:0 0 14px 0;">{escape(r.get("etikett", "Veckoanalys · Marknadsläget"))}</div>',
        f'<h1 style="font-family:{SERIF};font-size:30px;line-height:1.2;font-weight:normal;color:{INK};margin:0 0 16px 0;">{escape(r["title"])}</h1>',
        f'<p style="font-family:{SERIF};font-size:18px;line-height:1.5;font-style:italic;color:{DEK};margin:0 0 22px 0;">{escape(r["dek"])}</p>',
        f'<div style="font-family:{SANS};font-size:12px;color:{MUTED};border-top:1px solid {LINE};border-bottom:1px solid {LINE};padding:8px 0;margin:0 0 30px 0;">{escape(r["datum"])}</div>',
    ]
    for i, s in enumerate(r["sektioner"]):
        d.append(f'<h2 style="font-family:{SANS};font-size:13px;letter-spacing:1px;text-transform:uppercase;color:{INK};font-weight:700;margin:{"0" if i == 0 else "34px"} 0 12px 0;">{escape(s["rubrik"])}</h2>')
        for st in s["stycken"]:
            d.append(f'<p style="font-family:{SERIF};font-size:17px;line-height:1.7;color:{INK};margin:0 0 18px 0;">{escape(st)}</p>')
    if r.get("att_folja"):
        d.append(f'<div style="margin:34px 0 0 0;padding:16px 18px;background:{PAPER};border-left:3px solid {ACCENT};font-family:{SERIF};font-size:15px;line-height:1.6;color:{INK};">'
                 f'<span style="font-family:{SANS};font-size:11px;letter-spacing:1px;text-transform:uppercase;color:{ACCENT};font-weight:700;">Att följa</span><br>{escape(r["att_folja"])}</div>')
    fot = []
    if r.get("kallor"):
        fot.append("Källor: " + " · ".join(
            f'<a href="{escape(k["url"])}" style="color:{MUTED};">{escape(k["namn"])}: {escape(k["titel"])}</a>' if k.get("url")
            else f'{escape(k["namn"])}: {escape(k["titel"])}' for k in r["kallor"]))
    if r.get("underlag"):
        fot.append(escape(r["underlag"]))
    if fot:
        d.append(f'<div style="margin-top:30px;padding-top:14px;border-top:1px solid {LINE};font-family:{SANS};font-size:11px;line-height:1.6;color:{MUTED};">' + "<br>".join(fot) + "</div>")
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
            f'<body style="margin:0;padding:0;background:{PAPER};"><div style="background:{PAPER};padding:24px 8px;">'
            f'<div style="max-width:620px;margin:0 auto;background:#ffffff;padding:40px 32px 32px 32px;border-top:4px solid {ACCENT};">'
            + "\n".join(d) + "</div></div></body></html>")


def rendera_text(r: dict) -> str:
    t = [r["title"], r["datum"], "", r["dek"], ""]
    for s in r["sektioner"]:
        t += [s["rubrik"].upper()] + s["stycken"] + [""]
    if r.get("att_folja"):
        t += ["Att följa: " + r["att_folja"], ""]
    if r.get("kallor"):
        t += ["Källor:"] + [f"- {k['namn']}: {k['titel']} {k.get('url', '')}".rstrip() for k in r["kallor"]]
    return "\n\n".join(t) + "\n"


if __name__ == "__main__":
    import json, sys
    from pathlib import Path
    rap = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2] if len(sys.argv) > 2 else "forhandsvisning.html").write_text(rendera(rap), encoding="utf-8")
    print(rendera_text(rap))
