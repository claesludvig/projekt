"""Bostadsopinionen: SOM-institutets förslagsfrågor om bostäder per grupp.

Hämtar rapporterna "Allmänhetens åsikter om politiska förslag" (2021, 2023, 2024, 2025),
läser gruppfördelningen för bostadsförslagen och skriver
data/bostadsopinion/som_forslag_grupper.csv. Övriga filer i data/bostadsopinion är
handskrivna ur källorna i bostadsopinion.md och ur valjare.sqlite.

Kräver pdftotext (poppler-utils), eftersom pdfplumber blandar spalterna i dessa tabeller.

    python bostadsopinion.py
"""

import csv
import re
import subprocess
import tempfile
from pathlib import Path

import requests

BAS = "https://www.gu.se/sites/default/files/"
RAPPORTER = {
    2021: "2022-08/36.%20Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202021_v2.pdf",
    2023: "2024-04/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202023.pdf",
    2024: "2025-04/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202024.pdf",
    2025: "2026-06/Allm%C3%A4nhetens%20%C3%A5sikter%20om%20politiska%20f%C3%B6rslag%202025.pdf",
}
FORSLAG = [  # (år, tabellnummer, förslag)
    (2021, 5, "Sänka ränteavdraget på bostadslån"),
    (2021, 6, "Införa marknadshyror på bostadsmarknaden"),
    (2023, 17, "Införa marknadshyror på bostadsmarknaden"),
    (2023, 42, "Öka byggandet av billiga bostäder med mycket enkel standard"),
    (2024, 21, "Införa marknadshyror på bostadsmarknaden"),
    (2024, 41, "Förbjud utförsäljning av allmännyttan"),
    (2025, 82, "Återinföra fastighetsskatten"),
]
DIMENSION = {"Kön": "Kön", "Ålder": "Ålder", "Utbildning1": "Utbildning", "Boende-": "Boendeområde",
             "område": "Boendeområde", "Ideologisk": "Ideologi", "orientering2": "Ideologi",
             "Politiskt": "Politiskt intresse", "intresse3": "Politiskt intresse"}
RAD = re.compile(r"^\s*(?:(" + "|".join(DIMENSION) + r")\s+)?(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"
                 r"\s+100\s+([\d ]+?)(?:\s+\d+)?\s*$")
UT = Path(__file__).parent / "data" / "bostadsopinion" / "som_forslag_grupper.csv"


def rapporttext(ar: int, katalog: Path) -> list[str]:
    pdf = katalog / f"som{ar}.pdf"
    pdf.write_bytes(requests.get(BAS + RAPPORTER[ar], timeout=120).content)
    subprocess.run(["pdftotext", "-layout", str(pdf), str(pdf.with_suffix(".txt"))], check=True)
    return pdf.with_suffix(".txt").read_text(encoding="utf-8").splitlines()


def tabell(rader: list[str], nr: int, ar: int) -> list[tuple[str, str, list[int], int]]:
    start = [i for i, r in enumerate(rader) if r.startswith(f"Tabell {nr} ") and "Åsikt" in r][-1]
    ut, dim = [], "Samtliga"
    for r in rader[start + 1:start + 60]:
        if r.startswith("Kommentar"):
            break
        m = RAD.match(r)
        if not m:
            continue
        grupp = m.group(2).strip()
        dim = "Samtliga" if grupp == "Samtliga" else DIMENSION.get(m.group(1), dim)
        if ar == 2025 and grupp == "Varken till vä eller hö":
            grupp += " (4–6)"  # 2025: tre grupper på skalan 0–10, intervallet faller bort i pdf-texten
        ut.append((dim, grupp, [int(m.group(k)) for k in range(3, 8)], int(m.group(8).replace(" ", ""))))
    return ut


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        texter = {ar: rapporttext(ar, Path(tmp)) for ar in RAPPORTER}
    UT.parent.mkdir(parents=True, exist_ok=True)
    with UT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kalla", "ar", "forslag", "dimension", "grupp", "mycket_bra", "ganska_bra", "varken",
                    "ganska_dalig", "mycket_dalig", "andel_bra", "andel_dalig", "netto", "antal"])
        for ar, nr, forslag in FORSLAG:
            for dim, grupp, v, n in tabell(texter[ar], nr, ar):
                bra, dalig = v[0] + v[1], v[3] + v[4]
                w.writerow([f"SOM-institutet, nationella SOM {ar}", ar, forslag, dim, grupp, *v,
                            bra, dalig, bra - dalig, n])


if __name__ == "__main__":
    main()
