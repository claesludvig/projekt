#!/usr/bin/env python3
"""Generisk klient mot PxWeb-API:er (SCB:s statistikdatabas och Konjunktur-
institutets barometer använder samma API-dialekt).

Klienten är avsiktligt *upptäcktsdriven* snarare än hårdkodad: i stället för
att peka ut tabell-ID och värdekoder direkt går den ned genom tabellträdet
och matchar tabeller och variabelvärden på sina svenska etiketter med
reguljära uttryck. Skälet är att SCB byter koder oftare än etiketter — KRITA
gick t.ex. över från SNI 2007 till SNI 2025 i februari 2026, vilket bytte ut
värdekoderna för bransch men behöll namnen ("Bostadsrättsföreningar",
"Fastighet - bostäder"). En hårdkodad pipeline hade tystnat vid varje sådan
omläggning; den här rapporterar i stället vad den matchade så att man kan
granska kopplingen innan man litar på siffrorna."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Sequence
import json
import re
import sys
import time

import pandas as pd
import requests

SCB_BASE = "https://api.scb.se/OV0104/v1/doris/sv/ssd"
KONJ_BASE = "https://statistik.konj.se/PxWeb/api/v1/sv/KonjBar"

# SCB tillåter 30 anrop per 10 sekunder och adress. Vi håller oss med god
# marginal under det — pipelinen gör ändå bara någon handfull anrop per körning.
MIN_INTERVAL_S = 0.5
MAX_RETRIES = 4

# PxWeb v1 avvisar svar över ~150 000 celler. Tidsdimensionen är den enda som
# växer obegränsat, så den är också den vi delar upp på när ett uttag blir för
# stort.
CELL_LIMIT = 100_000

# Markörer för serier som inte uppdateras längre. SCB skriver det i
# tabelltiteln, KI lägger dem i undermappar med "hist" i namnet.
NEDLAGD = re.compile(r"uppdateras ej|hist", re.IGNORECASE)


class PxWebError(RuntimeError):
    pass


@dataclass
class Node:
    """En nod i tabellträdet: antingen en nivå ('l') eller en tabell ('t')."""

    id: str
    type: str
    text: str
    path: str

    @property
    def is_table(self) -> bool:
        return self.type == "t"


@dataclass
class Resolution:
    """Vad en sökning faktiskt landade i. Loggas till data/resolution.json så
    att kopplingen mellan efterfrågad serie och hämtad tabell går att granska
    i efterhand — det är den enda rimliga kvalitetskontrollen när urvalet görs
    på etiketter."""

    table_path: str
    table_title: str
    selections: dict[str, list[str]] = field(default_factory=dict)
    selection_labels: dict[str, list[str]] = field(default_factory=dict)


class PxWebClient:
    def __init__(self, base_url: str = SCB_BASE, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "byggkredit-scb/1.0"})
        self._last_call = 0.0
        self._nav_cache: dict[str, list[Node]] = {}

    # ---------- lågnivå ----------

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)
        self._last_call = time.monotonic()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.strip('/')}" if path else self.base_url
        for attempt in range(MAX_RETRIES):
            self._throttle()
            resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if resp.status_code == 429:
                # Backoff vid takgräns. SCB skickar sällan Retry-After, så vi
                # dubblar väntetiden själva.
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                raise PxWebError(f"{method} {url} gav {resp.status_code}: {resp.text[:300]}")
            return resp.json()
        raise PxWebError(f"{method} {url} takgränsades {MAX_RETRIES} gånger i rad")

    # ---------- navigering ----------

    def navigate(self, path: str = "") -> list[Node]:
        if path not in self._nav_cache:
            payload = self._request("GET", path)
            self._nav_cache[path] = [
                Node(id=n["id"], type=n["type"], text=n["text"],
                     path=f"{path}/{n['id']}".strip("/"))
                for n in payload
            ]
        return self._nav_cache[path]

    def walk_tables(self, root: str, max_depth: int = 3) -> Iterator[Node]:
        """Går igenom tabellträdet under `root` och lämnar ut varje tabell.
        Djupbegränsningen finns för att inte råka traversera halva SSD om en
        rot anges för brett."""
        if max_depth < 0:
            return
        try:
            noder = self.navigate(root)
        except PxWebError as exc:
            # SSD innehåller nivåer som ligger kvar i navigationen men svarar
            # 400 (t.ex. BO/BO0303/BO0303Z). En sådan död gren ska inte ta ned
            # hela sökningen — då blir varje serie under samma rot omöjlig att
            # hitta, vilket är precis vad som hände innan.
            print(f"[hoppar över] {root}: {exc}", file=sys.stderr)
            return
        for node in noder:
            if node.is_table:
                yield node
            else:
                yield from self.walk_tables(node.path, max_depth - 1)

    def find_table(self, root: str, title_pattern: str, max_depth: int = 3) -> Node:
        """Hittar den tabell under `root` vars titel matchar mönstret. Kastar
        om noll eller flera matchar — tvetydighet ska åtgärdas genom ett
        skarpare mönster i sources.py, inte genom att pipelinen gissar."""
        rx = re.compile(title_pattern, re.IGNORECASE)
        hits = [t for t in self.walk_tables(root, max_depth) if rx.search(t.text)]
        # Nedlagda serier ligger kvar bredvid sina efterföljare och matchar
        # samma mönster. Finns en levande variant är det alltid den man vill ha.
        # Både titel och sökväg prövas. SCB skriver "(uppdateras ej)" i titeln,
        # men KI lägger sina avslutade serier i undermappar — zftgkhist,
        # zftgmhist — medan titeln ser fullt aktuell ut.
        levande = [t for t in hits
                   if not NEDLAGD.search(t.text) and not NEDLAGD.search(t.path)]
        if levande:
            hits = levande
        if not hits:
            available = [t.text for t in self.walk_tables(root, max_depth)]
            raise PxWebError(
                f"Ingen tabell under '{root}' matchar {title_pattern!r}.\n"
                f"Tillgängliga: " + "\n  ".join(available[:40])
            )
        if len(hits) > 1:
            raise PxWebError(
                f"Flera tabeller under '{root}' matchar {title_pattern!r}: "
                + ", ".join(f"{h.path} ({h.text})" for h in hits)
            )
        return hits[0]

    # ---------- metadata och urval ----------

    def metadata(self, table_path: str) -> dict:
        return self._request("GET", table_path)

    @staticmethod
    def match_values(meta: dict, var_pattern: str, value_patterns: Sequence[str]
                     ) -> tuple[str, list[str], list[str]]:
        """Översätter ('bransch', ['Bostadsrättsförening']) till den variabelkod
        och de värdekoder tabellen faktiskt använder. Returnerar (variabelkod,
        värdekoder, värdeetiketter)."""
        var_rx = re.compile(var_pattern, re.IGNORECASE)
        candidates = [v for v in meta["variables"]
                      if var_rx.search(v["text"]) or var_rx.search(v["code"])]
        if not candidates:
            names = ", ".join(f"{v['code']} ({v['text']})" for v in meta["variables"])
            raise PxWebError(f"Ingen variabel matchar {var_pattern!r}. Fanns: {names}")
        var = candidates[0]

        codes: list[str] = []
        labels: list[str] = []
        for pattern in value_patterns:
            rx = re.compile(pattern, re.IGNORECASE)
            found = [(c, t) for c, t in zip(var["values"], var["valueTexts"]) if rx.search(t)]
            if not found:
                raise PxWebError(
                    f"Inget värde i '{var['text']}' matchar {pattern!r}. "
                    f"Fanns: {', '.join(var['valueTexts'][:40])}"
                )
            for code, text in found:
                if code not in codes:
                    codes.append(code)
                    labels.append(text)
        return var["code"], codes, labels

    @staticmethod
    def time_variable(meta: dict) -> dict:
        for v in meta["variables"]:
            if v.get("time"):
                return v
        # Äldre tabeller saknar time-flaggan; falla tillbaka på kodnamnet.
        for v in meta["variables"]:
            if v["code"].lower() in {"tid", "time"}:
                return v
        raise PxWebError("Tabellen saknar tidsvariabel")

    # ---------- uttag ----------

    def fetch(self, table_path: str, selections: dict[str, list[str]],
              time_codes: list[str] | None = None) -> pd.DataFrame:
        """Hämtar ett uttag och returnerar det i långt format. Delar upp på tid
        om urvalet spränger cellgränsen."""
        meta = self.metadata(table_path)
        tvar = self.time_variable(meta)
        times = time_codes if time_codes is not None else list(tvar["values"])

        per_period = max(1, _product(len(v) for v in selections.values()))
        chunk = max(1, CELL_LIMIT // per_period)
        frames = []
        for start in range(0, len(times), chunk):
            frames.append(self._fetch_chunk(table_path, meta, selections,
                                            tvar["code"], times[start:start + chunk]))
        return pd.concat(frames, ignore_index=True).drop_duplicates()

    def _fetch_chunk(self, table_path: str, meta: dict, selections: dict[str, list[str]],
                     time_code: str, times: list[str]) -> pd.DataFrame:
        query = [{"code": code, "selection": {"filter": "item", "values": values}}
                 for code, values in selections.items()]
        query.append({"code": time_code, "selection": {"filter": "item", "values": times}})
        body = {"query": query, "response": {"format": "json-stat2"}}
        payload = self._request("POST", table_path, data=json.dumps(body).encode("utf-8"),
                                headers={"Content-Type": "application/json"})
        return jsonstat2_to_frame(payload)


def _product(values: Iterator[int]) -> int:
    total = 1
    for v in values:
        total *= v
    return total


def jsonstat2_to_frame(payload: dict) -> pd.DataFrame:
    """Plattar ut ett JSON-stat2-svar till långt format med en kolumn per
    dimension plus 'value'. Värdematrisen är radmajor över dimensionerna i
    payload['id'], och kan komma antingen som lista eller som gles dict."""
    dim_ids: list[str] = payload["id"]
    sizes: list[int] = payload["size"]
    raw = payload["value"]

    # Etiketter per dimension, ordnade efter kategoriindex.
    axes: list[list[str]] = []
    for dim_id in dim_ids:
        category = payload["dimension"][dim_id]["category"]
        index = category["index"]
        if isinstance(index, dict):
            ordered = sorted(index, key=lambda k: index[k])
        else:
            ordered = list(index)
        labels = category.get("label", {})
        axes.append([labels.get(code, code) for code in ordered])

    total = _product(iter(sizes))
    if isinstance(raw, dict):
        values: list[Any] = [None] * total
        for position, value in raw.items():
            values[int(position)] = value
    else:
        values = list(raw)
    if len(values) != total:
        raise PxWebError(f"JSON-stat2: {len(values)} värden men {total} celler förväntades")

    # Radmajor: sista dimensionen varierar snabbast.
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    columns = {dim_ids[d]: [axes[d][(i // strides[d]) % sizes[d]] for i in range(total)]
               for d in range(len(dim_ids))}
    columns["value"] = values
    frame = pd.DataFrame(columns)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame
