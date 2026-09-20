#!/usr/bin/env python3
"""Skriver en analytisk sammanfattning av utskicket med Claude.

Utan det här steget är utskicket en länklista. Det som efterfrågas är
sammanfattningar och analyser: en syntetiserad rubrik, sammanhängande
brödtext som väver ihop rapportering med kommentatorernas läsningar, och en
punktlista över det viktigaste.

Läser data/latest_articles.json och skriver data/analysis.json.
Kräver ANTHROPIC_API_KEY. Saknas den hoppar steget över analysen och
utskicket faller tillbaka på ren lista - hämtningen ska inte fälla på en
nyckel som inte hunnit sättas.
"""

import json
import os
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "latest_articles.json"
UT = Path(__file__).resolve().parent / "data" / "analysis.json"

MODELL = "claude-opus-5"

SYSTEM = """Du är politisk analytiker och skriver ett dagligt utskick på svenska \
om svensk politik och regeringsbildningen, till en läsare som följer frågan tätt \
och redan kan grunderna.

Du får dagens nya artiklar: nyhetsrapportering, ledare och kommentarer samt \
officiella besked. Skriv en analys av materialet.

Krav:
- Skriv på svenska, i sakprosa. Inga punktlistor i brödtexten.
- Håll dig strikt till det som står i materialet. Hitta aldrig på uppgifter, \
namn, siffror eller citat. Har du inte täckning för något, skriv det inte.
- Var konkret. Namnge partier, personer och besked. Undvik svepande formuleringar.
- Väv ihop rapportering med kommentatorernas läsningar, och var tydlig med vad \
som är rapporterat och vad som är någons bedömning. Skriv ut vem som tycker vad.
- Vissa poster har bara ingress för att brödtexten låg bakom betalvägg. Använd \
dem för vad de visar - vem som skriver om vad och med vilken vinkel - men \
låtsas inte veta mer än ingressen säger.
- Är materialet tunt: skriv kort. Fyll inte ut.

Format:
- headline: en rubrik som fångar dagens två viktigaste trådar, sammanfogade med \
tankstreck. Ingen avslutande punkt.
- paragraphs: två till fyra stycken analytisk brödtext. Första stycket tar det \
tyngsta skeendet, följande stycken det som rör sig därnäst.
- bullets: tre till sex punkter över det viktigaste. lead är en fetad ingång på \
några ord som slutar med kolon, text är en till två meningar som utvecklar."""

SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "paragraphs": {"type": "array", "items": {"type": "string"}},
        "bullets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"lead": {"type": "string"}, "text": {"type": "string"}},
                "required": ["lead", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headline", "paragraphs", "bullets"],
    "additionalProperties": False,
}


def bygg_underlag(artiklar: list[dict]) -> str:
    """Materialet som analysen får bygga på, i den ordning det ska läsas."""
    ordning = {"nyhet": 0, "officiell": 1, "kommentar": 2}
    etikett = {
        "nyhet": "RAPPORTERING",
        "officiell": "OFFICIELLT BESKED",
        "kommentar": "LEDARE/KOMMENTAR",
    }
    delar = []
    for a in sorted(artiklar, key=lambda x: ordning.get(x.get("kind"), 9)):
        rader = [
            f"--- {etikett.get(a.get('kind'), 'ÖVRIGT')} ---",
            f"Rubrik: {a.get('title','')}",
            f"Avsändare: {a.get('source','')}",
            f"Datum: {a.get('published','')}",
        ]
        if a.get("author"):
            rader.append(f"Skribent: {a['author']}")
        if a.get("commentator"):
            rader.append(f"Namngiven kommentator: {a['commentator']}")
        if a.get("summary"):
            rader.append(f"Ingress: {a['summary']}")
        if a.get("fetch_error"):
            rader.append("Brödtext: kunde inte hämtas - bara ingressen ovan finns.")
        elif a.get("paywall"):
            rader.append("Brödtext: avkortad av betalvägg.")
        if a.get("fulltext"):
            rader.append(f"Text: {a['fulltext']}")
        delar.append("\n".join(rader))
    return "\n\n".join(delar)


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("ANTHROPIC_API_KEY saknas - hoppar över analysen.")
        return 0
    if not DATA.exists():
        print("saknar data/latest_articles.json", file=sys.stderr)
        return 1

    data = json.loads(DATA.read_text(encoding="utf-8"))
    artiklar = data.get("articles", [])
    if not artiklar:
        print("Inga nya poster - ingen analys att skriva.")
        return 0

    import anthropic

    klient = anthropic.Anthropic()
    underlag = bygg_underlag(artiklar)
    print(f"Analyserar {len(artiklar)} poster ({len(underlag.split())} ord underlag) ...")

    svar = klient.messages.create(
        model=MODELL,
        max_tokens=16000,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Datum: {data.get('fetched_at','')[:10]}. "
                    f"{len(artiklar)} nya poster sedan förra utskicket.\n\n{underlag}"
                ),
            }
        ],
    )

    if svar.stop_reason == "refusal":
        print(f"Modellen avböjde: {getattr(svar, 'stop_details', None)}", file=sys.stderr)
        return 0

    text = next(b.text for b in svar.content if b.type == "text")
    analys = json.loads(text)
    analys["model"] = svar.model
    analys["based_on"] = len(artiklar)

    UT.write_text(json.dumps(analys, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Skrev analys: {analys['headline']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
