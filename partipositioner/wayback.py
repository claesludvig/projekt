"""Äldre versioner av partiernas bostadspolitiska sidor och PDF:er ur Internet Archives Wayback Machine.

En kopia per adress och år. Wayback begränsar antalet anrop hårt, så skriptet går långsamt
(ett anrop per 4 s), väntar ut 429-svar och kan avbrytas och startas om.

  data/wayback/index_<domän>.json   CDX-träffar
  data/wayback/<parti>.jsonl        url, år, tidsstämpel, arkivlänk, titel, text
"""
import json, re, subprocess, sys, time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROT = Path(__file__).parent
UT = ROT / "data" / "wayback"
RAW = ROT / "data" / "arkiv" / "raw"
S = requests.Session(); S.headers["User-Agent"] = "partipositioner/1.0 (forskningsarkiv; kontakt via GitHub claesludvig/projekt)"

DOMANER = {
    "s": ["socialdemokraterna.se", "sap.se"], "m": ["moderaterna.se", "moderat.se"], "c": ["centerpartiet.se"],
    "l": ["folkpartiet.se", "liberalerna.se"], "kd": ["kristdemokraterna.se", "kd.se"], "v": ["vansterpartiet.se", "vpk.se"],
    "mp": ["mp.se", "miljopartiet.se"], "sd": ["sverigedemokraterna.se", "sd.se"],
}
FILTER = r".*(bostad|bostader|bostadspolitik|hyr|boende|byggande|amorter|ranteavdrag|fastighetsskatt|allmannytt|valmanifest|partiprogram|handlingsprogram).*"
PAUS = 4.0
_senast = [0.0]


def get(u, **kw):
    for i in range(8):
        vanta = _senast[0] + PAUS - time.time()
        if vanta > 0: time.sleep(vanta)
        _senast[0] = time.time()
        try:
            r = S.get(u, timeout=120, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(60 * (i + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(60 * (i + 1))
    return None


def cdx(domän):
    f = UT / f"index_{domän}.json"
    if f.exists(): return json.loads(f.read_text())
    r = get("https://web.archive.org/cdx/search/cdx", params={
        "url": f"{domän}/*", "output": "json", "fl": "timestamp,original,mimetype,statuscode",
        "filter": ["statuscode:200", f"original:{FILTER}"], "collapse": ["timestamp:4", "urlkey"], "limit": 20000})
    if not r or r.status_code != 200: return None
    rader = r.json()[1:] if r.text.strip() else []
    UT.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(rader))
    return rader


def _text(b, mime, namn):
    if b.startswith(b"%PDF"):
        RAW.mkdir(parents=True, exist_ok=True); p = RAW / f"wb_{namn}.pdf"; p.write_bytes(b)
        return "", subprocess.run(["pdftotext", "-enc", "UTF-8", str(p), "-"], capture_output=True).stdout.decode("utf8", "replace")
    s = BeautifulSoup(b, "lxml")
    titel = s.title.get_text(" ", strip=True) if s.title else ""
    for t in s(["script", "style", "nav", "header", "footer", "form"]): t.decompose()
    return titel, "\n\n".join(p.get_text(" ", strip=True) for p in s.select("h1,h2,h3,p,li,td") if len(p.get_text(strip=True)) > 2)


def parti(k):
    f = UT / f"{k}.jsonl"
    klara = set()
    if f.exists():
        klara = {json.loads(l)["arkiv"] for l in f.read_text().splitlines() if l.strip()}
    for d in DOMANER[k]:
        rader = cdx(d)
        if rader is None: print(f"{k} {d}: Wayback svarar inte", flush=True); return False
        print(f"{k} {d}: {len(rader)} arkiverade versioner", flush=True)
        for ts, orig, mime, _ in rader:
            if not re.search(r"html|pdf", mime): continue
            arkiv = f"https://web.archive.org/web/{ts}id_/{orig}"
            if arkiv in klara: continue
            r = get(arkiv)
            if not r or r.status_code != 200: continue
            titel, text = _text(r.content, mime, f"{k}_{ts}_{abs(hash(orig))}")
            with f.open("a") as ut:
                ut.write(json.dumps({"parti": k, "url": orig, "ar": int(ts[:4]), "tidsstampel": ts,
                                     "arkiv": arkiv.replace("id_/", "/"), "titel": titel, "text": text[:60000]}, ensure_ascii=False) + "\n")
            klara.add(arkiv)
    return True


if __name__ == "__main__":
    UT.mkdir(parents=True, exist_ok=True)
    kvar = sys.argv[1:] or list(DOMANER)
    for runda in range(30):                       # försök igen i upp till ~10 timmar om arkivet inte svarar
        kvar = [k for k in kvar if not parti(k)]
        if not kvar: break
        print(f"väntar 20 min, kvar: {kvar}", flush=True); time.sleep(1200)
