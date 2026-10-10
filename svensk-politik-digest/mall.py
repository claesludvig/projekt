"""
Renderar ett utskick till HTML.

Layouten är lyft ur chronicle-ingests mall.py så att mejlen ser likadana ut som
poddrapporterna. Claude skriver bara innehållet som JSON; formen bestäms här,
vilket gör att den inte kan glida från dag till dag.

Skillnaden mot poddmallen är källistan sist. En poddrapport bygger på ett
avsnitt, det här utskicket på många artiklar, och då behöver läsaren kunna gå
vidare till originalen.
"""

import html as _html
from datetime import datetime
from typing import Any, Dict, List

MARIN = "#1a365d"
BROD = "#2d3748"
DAMPAD = "#718096"
LJUS = "#a0aec0"

AVDELNINGAR = [
    ("kommentar", "Analys och kommentar"),
    ("nyhet", "Rapportering"),
    ("officiell", "Officiella besked"),
]


def _text(v: Any) -> str:
    """Escapar innehåll från modellen så att ett bindestreck eller & inte bryter mailen."""
    return _html.escape(str(v or "").strip())


def _kallor(artiklar: List[Dict[str, Any]]) -> str:
    block = []
    for kind, rubrik in AVDELNINGAR:
        grupp = [a for a in artiklar if a.get("kind") == kind]
        if not grupp:
            continue
        block.append(
            f"<h3 style='color: {MARIN}; font-size: 13px; font-weight: 700; "
            f"margin: 22px 0 10px 0; letter-spacing: 0.5px; text-transform: uppercase;'>"
            f"{_text(rubrik)}</h3>"
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
            block.append(
                f"<div style='margin: 0 0 12px 0;'>"
                f"<a href='{_text(a.get('url'))}' style='color: {MARIN}; font-size: 14px; "
                f"font-weight: 600; text-decoration: none;'>{_text(a.get('title'))}</a>"
                f"<div style='color: {LJUS}; font-size: 12px; margin-top: 2px;'>{_text(meta)}</div>"
                f"</div>"
            )
    return "".join(block)


def rendera(data: Dict[str, Any], utskick: Dict[str, Any]) -> str:
    """data = rapporten Claude skrivit, utskick = latest_articles.json."""
    rubrik = _text(data.get("title")) or "Nytt om regeringsbildningen"
    artiklar = utskick.get("articles", [])
    antal = utskick.get("new_count", len(artiklar))
    dag = (utskick.get("fetched_at") or "")[:10] or datetime.now().strftime("%Y-%m-%d")

    stycken = "".join(
        f"<p style='color: {BROD}; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;'>"
        f"{_text(p)}</p>"
        for p in data.get("analysis_paragraphs", [])
        if str(p).strip()
    )

    punkter = "".join(
        f"<li style='color: {BROD}; font-size: 15px; line-height: 1.6; margin-bottom: 12px;'>"
        f"<strong style='color: {MARIN};'>{_text(b.get('bold_lead'))}:</strong> {_text(b.get('text'))}"
        f"</li>"
        for b in data.get("key_developments", [])
        if str(b.get("text", "")).strip()
    )

    hoppat = utskick.get("skipped", {}).get("seen", 0)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body style="background-color: #f4f6f8; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0;">
  <div style="background-color: #f4f6f8; padding: 40px 20px;">
    <div style="background-color: #ffffff; max-width: 600px; margin: 0 auto; border-radius: 8px; border-top: 6px solid {MARIN}; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); overflow: hidden;">
      <div style="padding: 35px 40px;">
        <h1 style="color: {MARIN}; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; margin: 0 0 10px 0; text-transform: uppercase;">
          {rubrik}
        </h1>
        <div style="color: {DAMPAD}; font-size: 14px; font-style: italic; margin: 0 0 25px 0;">
          Analys baserad på {antal} nya poster den {_text(dag)}
        </div>

        {stycken}

        <h2 style="color: {MARIN}; font-size: 17px; font-weight: 700; margin: 30px 0 15px 0; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">
          Viktigaste händelserna
        </h2>
        <ul style="margin: 0 0 20px 0; padding-left: 20px;">
          {punkter}
        </ul>

        <h2 style="color: {MARIN}; font-size: 17px; font-weight: 700; margin: 30px 0 15px 0; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">
          Källor
        </h2>
        {_kallor(artiklar)}

        <div style="margin-top: 40px; border-top: 1px solid #f0f4f8; padding-top: 15px; font-size: 12px; color: {LJUS}; text-align: center;">
          {hoppat} poster var redan utskickade och togs inte med · Denna rapport har genererats automatiskt av din personliga nyhetsbevakare.
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""
