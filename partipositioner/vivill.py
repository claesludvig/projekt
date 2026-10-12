"""Partiprogram och valmanifest ur SND:s samling "Svenska partiprogram och valmanifest" (Vivill), CC BY 4.0.

  data/vivill/lista.json            ett dokument per rad: parti, slag, år, titel, källa
  data/vivill/text/<p>_<t>_<år>.txt texten
  data/vivill/pdf/...               PDF-kopian (ej i git)
"""
import concurrent.futures as cf, json, re, sys, time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from katalog import PARTIER

ROT = Path(__file__).parent
UT = ROT / "data" / "vivill"
BAS = "https://snd.se"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (partipositioner; forskning)"


def get(u):
    for i in range(4):
        try:
            r = S.get(u, timeout=90)
            if r.status_code == 200: return r
            if r.status_code == 404: return None
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    return None


def lista():
    ut = []
    for k, p in PARTIER.items():
        for v in p["vivill"]:
            r = get(f"{BAS}/sv/vivill/party/{v}")
            if not r: print("saknas", v); continue
            for a in BeautifulSoup(r.text, "lxml").select("a.vivill-list--document__document"):
                m = re.search(r"/vivill/party/([^/]+)/([^/]+)/(\d{4})", a["href"])
                if not m or m[1] != v: continue
                txt = a.select_one(".vivill-list--document__document__title").get_text("\n", strip=True)
                typ = re.search(r"Type:\s*\n?(.+)", txt); kalla = a.select_one(".source")
                ut.append({"id": f"{v}_{m[2]}_{m[3]}", "parti": k, "vivill": v, "slag": m[2], "ar": int(m[3]),
                           "titel": a.select_one("h5").get_text(" ", strip=True),
                           "slagnamn": typ[1].strip() if typ else m[2], "kalla": kalla.get_text(" ", strip=True) if kalla else "",
                           "url": f"{BAS}/sv/vivill/party/{v}/{m[2]}/{m[3]}",
                           "pdf": f"{BAS}/sv/vivill/file/{v}/{m[2]}/{m[3]}/pdf"})
    ut = list({d["id"]: d for d in ut}.values())
    UT.mkdir(parents=True, exist_ok=True)
    (UT / "lista.json").write_text(json.dumps(ut, ensure_ascii=False, indent=1))
    print(f"{len(ut)} dokument")
    return ut


def hamta(docs):
    (UT / "text").mkdir(exist_ok=True); (UT / "pdf").mkdir(exist_ok=True)
    def ett(d):
        t = UT / "text" / f"{d['id']}.txt"; p = UT / "pdf" / f"{d['id']}.pdf"
        if not t.exists():
            r = get(f"{BAS}/en/vivill/file/{d['vivill']}/{d['slag']}/{d['ar']}/txt")
            if r: t.write_text(r.content.decode("utf-8-sig", "replace"))
        if not p.exists():
            r = get(d["pdf"])
            if r and r.content.startswith(b"%PDF"): p.write_bytes(r.content)
        return t.exists(), p.exists()
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(ett, docs))
    print("text:", sum(a for a, _ in res), "pdf:", sum(b for _, b in res), "av", len(docs))


if __name__ == "__main__":
    hamta(lista())
