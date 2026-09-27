#!/usr/bin/env python3
"""Väljardatabasen, steg 3: bygg index.html av sida.html och data/webb.json.

    python bygg_sida.py                 # index.html (fristående sida)
    python bygg_sida.py --utan-ram UT   # samma innehåll utan <html>/<head>-ram
"""

import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--utan-ram", metavar="FIL")
    a = p.parse_args()
    data = json.loads((BASE_DIR / "data" / "webb.json").read_text(encoding="utf-8"))
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    innehall = (BASE_DIR / "sida.html").read_text(encoding="utf-8").replace("/*DATA*/null", js)
    if a.utan_ram:
        Path(a.utan_ram).write_text(innehall, encoding="utf-8")
        return
    sida = ('<!doctype html>\n<html lang="sv">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + innehall.replace("<main>", "</head>\n<body>\n<main>", 1) + "\n</body>\n</html>\n")
    (BASE_DIR / "index.html").write_text(sida, encoding="utf-8")


if __name__ == "__main__":
    main()
