"""Överenskommelser, regeringsförklaringar och partiernas bostadsmotioner.

  avtal        överenskommelser i overenskommelser.txt                  -> data/dok/avtal/
  regdekl      regeringsförklaringar 1994– från regeringen.se           -> data/dok/regdekl/
  motioner     kommitté- och partimotioner till BoU/CU 1990/91–         -> data/dok/mot/
Varje dokument sparas som <id>.json med metadata och text; originalfilen i data/arkiv/raw/ (ej i git).
"""
import argparse, concurrent.futures as cf, json, re, subprocess, sys, time
from pathlib import Path

import requests

from katalog import BOSTAD_RX
from bs4 import BeautifulSoup

ROT = Path(__file__).parent
UT = ROT / "data" / "dok"
RAW = ROT / "data" / "arkiv" / "raw"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/124"
PARTIBOKSTAV = {"S": "s", "M": "m", "C": "c", "FP": "l", "L": "l", "KD": "kd", "KDS": "kd", "V": "v", "VPK": "v",
                "MP": "mp", "SD": "sd", "NYD": "nyd"}


def get(u, **kw):
    for i in range(3):
        try:
            r = S.get(u, timeout=90, **kw)
            if r.status_code == 200: return r
            if r.status_code in (404, 410): return None
        except requests.RequestException:
            pass
        time.sleep(4 * (i + 1))
    return None


def _pdftext(b, namn):
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / f"{namn}.pdf"; f.write_bytes(b)
    return subprocess.run(["pdftotext", "-enc", "UTF-8", str(f), "-"], capture_output=True).stdout.decode("utf8", "replace")


def _htmltext(h, namn):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{namn}.html").write_text(h)
    s = BeautifulSoup(h, "lxml")
    for t in s(["script", "style", "nav", "header", "footer", "form", "aside"]): t.decompose()
    m = s.select_one("main") or s.select_one("article") or s.body
    return "\n\n".join(p.get_text(" ", strip=True) for p in m.select("h1,h2,h3,p,li") if p.get_text(strip=True))


def spara(mapp, d):
    (UT / mapp).mkdir(parents=True, exist_ok=True)
    (UT / mapp / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False))


def avtal():
    for rad in (ROT / "overenskommelser.txt").read_text().splitlines():
        if not rad.strip() or rad.startswith("#"): continue
        id_, ar, partier, slag, titel, url = [x.strip() for x in rad.split("|")]
        r = get(url)
        if not r: print("  saknas:", id_, url); continue
        text = _pdftext(r.content, id_) if r.content.startswith(b"%PDF") else _htmltext(r.text, id_)
        spara("avtal", {"id": id_, "ar": int(ar), "datum": ar, "partier": partier.split(","), "slag": slag,
                        "titel": titel, "url": url, "text": text})
        print("  ", id_, len(text))


def regdekl():
    r = get("https://www.regeringen.se/sitemap.xml")
    urls = sorted(set(re.findall(r"<loc>\s*(https://www\.regeringen\.se/tal/\d{4}/\d\d/regeringsforklaring[^<\s]*)", r.text)))
    print(len(urls), "regeringsförklaringar")
    for u in urls:
        m = re.search(r"/tal/(\d{4})/(\d\d)/", u); id_ = f"regdekl_{m[1]}_{m[2]}"
        if (UT / "regdekl" / f"{id_}.json").exists(): continue
        x = get(u)
        if not x: continue
        s = BeautifulSoup(x.text, "lxml")
        titel = s.h1.get_text(" ", strip=True) if s.h1 else "Regeringsförklaringen"
        spara("regdekl", {"id": id_, "ar": int(m[1]), "datum": f"{m[1]}-{m[2]}", "partier": [], "slag": "regeringsförklaring",
                          "titel": titel, "url": u, "text": _htmltext(x.text, id_)})


def _rm():
    return [f"{a}/{str(a + 1)[2:]}" for a in range(1990, 2026)]


def motioner():
    lista = []
    for rm in _rm():
        for organ in ("alla",):
            for sub in ("Kommittémotion", "Partimotion"):
                sid = 1
                while True:
                    r = get("https://data.riksdagen.se/dokumentlista/", params={"doktyp": "mot", "rm": rm,
                            "subtyp": sub, "utformat": "json", "sz": 200, "p": sid})
                    if not r: break
                    d = r.json()["dokumentlista"]
                    for x in d.get("dokument") or []:
                        org = x.get("organ") or ""
                        if org not in ("BoU", "CU") and not BOSTAD_RX.search((x.get("titel") or "")):
                            continue
                        if org == "CU" and not BOSTAD_RX.search(x.get("titel") or "") and not re.search(r"bygg|plan|hyr|fastighet|bostad|boende|lägenhet", (x.get("titel") or ""), re.I):
                            continue
                        m = re.search(r"\(([A-ZÅÄÖ]+)\)\s*$", x.get("undertitel") or "")
                        lista.append({"id": x["dok_id"], "rm": rm, "datum": (x.get("datum") or "")[:10], "organ": org,
                                      "subtyp": sub, "beteckning": x.get("beteckning"), "titel": x.get("titel"),
                                      "undertitel": x.get("undertitel"), "parti": PARTIBOKSTAV.get(m[1]) if m else None,
                                      "url": f"https://data.riksdagen.se/dokument/{x['dok_id']}.html"})
                    if sid >= int(d.get("@sidor") or 1): break
                    sid += 1
        print(" ", rm, len(lista), flush=True)
    lista = list({x["id"]: x for x in lista}.values())
    (UT / "mot").mkdir(parents=True, exist_ok=True)
    def en(x):
        f = UT / "mot" / f"{x['id']}.json"
        if f.exists(): return
        r = get(f"https://data.riksdagen.se/dokument/{x['id']}.html")
        if r:
            s = BeautifulSoup(r.text, "lxml")
            text = "\n\n".join(p.get_text(" ", strip=True) for p in s.select("h1,h2,h3,p,li") if p.get_text(strip=True))
            spara("mot", {**x, "ar": int(x["rm"][:4]), "partier": [x["parti"]] if x["parti"] else [], "slag": "motion",
                          "text": text})
    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(en, lista))
    print(len(lista), "motioner")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("steg", nargs="*", default=["avtal", "regdekl", "motioner"])
    for s in ap.parse_args().steg:
        print("==", s); globals()[s]()
