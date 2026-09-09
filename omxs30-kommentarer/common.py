#!/usr/bin/env python3
"""Delade hjälpfunktioner för OMXS30-kommentarsmodulen."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCES_PATH = BASE_DIR / "sources.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}

# Termer som gör en text relevant för OMXS30. Vikten avgör träffpoängen.
RELEVANS_TERMER = {
    r"\bomxs\s?30\b": 5,
    r"\bomx\s?s30\b": 5,
    r"\bstorbolagsindex\b": 4,
    r"\bstockholmsbörsen\b": 3,
    r"\bstockholmsborsen\b": 3,
    r"\bnasdaq stockholm\b": 2,
    r"\bbörsen\b": 1,
    r"\bborsen\b": 1,
    r"\bindexet\b": 1,
    r"\bstockholm 30\b": 4,
}

# Enkelt tonlexikon. Heuristik, inte en modell - använd som grovsortering.
POSITIVA = [
    "uppgång", "stiger", "rusar", "lyfter", "optimism", "återhämtning", "styrka",
    "köpläge", "bryter upp", "motståndet passerat", "riskaptit", "rally", "plusvecka",
    "positiv", "stark", "medvind",
]
NEGATIVA = [
    "nedgång", "faller", "rasar", "tappar", "oro", "pessimism", "svaghet",
    "säljtryck", "bryter ned", "stödet brutet", "riskaversion", "korrektion",
    "minusvecka", "negativ", "svag", "motvind", "vinsthemtagning", "vinsthemtagningar",
]


def normalisera(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def utan_accenter(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c)
    ).lower()


def relevanspoang(*texter: str) -> int:
    """Poängsätter hur mycket en text handlar om OMXS30/Stockholmsbörsen."""
    blob = " ".join(t or "" for t in texter).lower()
    blob_flat = utan_accenter(blob)
    poang = 0
    for monster, vikt in RELEVANS_TERMER.items():
        if re.search(monster, blob) or re.search(monster, blob_flat):
            poang += vikt
    return poang


def tonlage(text: str) -> dict:
    """Grov lexikonbaserad ton. Returnerar antal träffar och en etikett."""
    blob = (text or "").lower()
    plus = sum(blob.count(ord_) for ord_ in POSITIVA)
    minus = sum(blob.count(ord_) for ord_ in NEGATIVA)
    if plus == minus:
        etikett = "neutral"
    elif plus > minus:
        etikett = "positiv"
    else:
        etikett = "negativ"
    return {"positiva_traffar": plus, "negativa_traffar": minus, "etikett": etikett}


def hamta(url: str, timeout: float = 25.0) -> httpx.Response | None:
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:  # noqa: BLE001 - vi vill logga och gå vidare
        print(f"    [!] {url}: {e}")
        return None


def ser_ut_som_flode(text: str) -> bool:
    huvud = (text or "")[:2000].lower()
    return "<rss" in huvud or "<feed" in huvud or "<rdf" in huvud


def las_kallor() -> dict:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def skriv_json(namn: str, data: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sokvag = DATA_DIR / namn
    sokvag.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return sokvag


def nu_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parsa_datum(varde) -> str:
    """Plockar ut YYYY-MM-DD ur ett feedparser-datum eller en strang."""
    if not varde:
        return ""
    if isinstance(varde, str):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", varde)
        if m:
            return m.group(0)
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(varde).date().isoformat()
        except Exception:  # noqa: BLE001
            return ""
    try:
        return date(varde.tm_year, varde.tm_mon, varde.tm_mday).isoformat()
    except Exception:  # noqa: BLE001
        return ""


def borsdagar(fran: date, till: date) -> list[str]:
    """Vardagar i intervallet (helgdagar hanteras inte - grov approximation)."""
    dagar = []
    d = fran
    while d <= till:
        if d.weekday() < 5:
            dagar.append(d.isoformat())
        d += timedelta(days=1)
    return dagar
