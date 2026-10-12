"""Medial rapportering om partiernas bostadspolitik.

  sitemaps  månadsvisa artikelsitemaps (Aftonbladet, Expressen, DN, SvD, Omni, Dagens Samhälle):
            artiklar vars adress tyder på bostadspolitik           -> data/media/kandidater.jsonl
  wp        fackpress och Hem & Hyra via WordPress-sök, hel text    -> data/media/wp.jsonl
  gnews     Google Nyheter, senaste månaderna, alla medier          -> data/media/gnews.jsonl
  artiklar  hämtar kandidaterna: rubrik, datum, ingress, text       -> data/media/artiklar.jsonl
Artiklarnas text checkas inte in (upphovsrätt); förteckningen och korta utdrag gör det.
"""
import argparse, concurrent.futures as cf, html, json, re, sys, threading, time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

ROT = Path(__file__).parent
UT = ROT / "data" / "media"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "sv-SE,sv"}
S = requests.Session(); S.headers.update(H)

MEDIER = {
    "ab":   {"namn": "Aftonbladet", "index": "https://www.aftonbladet.se/sitemap.xml"},
    "ex":   {"namn": "Expressen", "index": "https://www.expressen.se/sitemap.xml"},
    "dn":   {"namn": "Dagens Nyheter", "index": "https://www.dn.se/sitemap.xml"},
    "svd":  {"namn": "Svenska Dagbladet", "index": "https://www.svd.se/sitemap.xml"},
    "omni": {"namn": "Omni", "index": "https://omni.se/sitemap.xml"},
    "ds":   {"namn": "Dagens Samhälle", "index": "https://www.dagenssamhalle.se/sitemap.xml"},
    "hh":   {"namn": "Hem & Hyra", "wp": "https://www.hemhyra.se"},
    "ft":   {"namn": "Fastighetstidningen", "wp": "https://fastighetstidningen.se"},
    "bv":   {"namn": "Byggvärlden", "wp": "https://www.byggvarlden.se"},
}

# Adressord som tyder på bostadspolitik (inte bostadsbränder och hyrbilar)
POLITIK = (r"bostadspolitik|bostadsminister|marknadshyr|hyressattning|hyresreglering|presumtionshyr|bruksvarde|"
           r"ranteavdrag|amorteringskrav|bolanetak|fastighetsskatt|fastighetsavgift|flyttskatt|reavinstskatt|"
           r"investeringsstod|allmannytt|bostadsbrist|bostadsbyggande|bostadskris|startlan|bosparande|"
           r"bostadsbidrag|bostadsko|hyresratter|ombildning|utforsaljning.*(allmannytt|hyres)|byggregler|strandskydd|planmonopol")
PARTIORD = (r"regering|socialdemokrat|moderat|centerpart|liberal|folkpart|kristdemokrat|vansterpart|miljopart|"
            r"sverigedemokrat|alliansen|rodgrona|\bsd\b|budget|vallofte|valet|forslag|lofven|reinfeldt|kristersson|"
            r"andersson|akesson|batra|lööf|loof|sjostedt|dadgostar|busch|bostadsminister|tido|januariavtal")
SLUG_RX = re.compile(rf"({POLITIK})|((bostad|bostader|hyr|hyres)[^/]*({PARTIORD}))|(({PARTIORD})[^/]*(bostad|bostader|hyres))", re.I)

WP_SOK = ["bostadspolitik", "marknadshyror", "fri hyressättning", "presumtionshyra", "ränteavdrag", "amorteringskrav",
          "bolånetak", "investeringsstöd", "fastighetsskatt", "fastighetsavgift", "flyttskatt", "bostadsminister",
          "Tidöavtalet", "Januariavtalet", "bostadsbidrag", "allmännyttan", "startlån", "valmanifest", "bostadsbrist"]

_las = defaultdict(lambda: threading.Semaphore(3))


def get(u, **kw):
    with _las[urlparse(u).netloc]:
        for i in range(3):
            try:
                r = S.get(u, timeout=60, **kw)
                if r.status_code in (429, 503): time.sleep(10 * (i + 1)); continue
                return r
            except requests.RequestException:
                time.sleep(3 * (i + 1))
    return None


def _manad(u):
    m = re.search(r"(\d{4})-(\d\d)", u)
    return f"{m[1]}-{m[2]}" if m else None


def sitemaps(medier):
    UT.mkdir(parents=True, exist_ok=True)
    f = UT / "kandidater.jsonl"
    klara = set()
    logg = UT / "sitemaps_klara.txt"
    if logg.exists(): klara = set(logg.read_text().split())
    for k in medier:
        m = MEDIER[k]
        if "index" not in m: continue
        r = get(m["index"])
        if not r: print("index saknas", k); continue
        manader = [l for l in re.findall(r"<loc>\s*([^<\s]+)", r.text) if _manad(l) and "tag" not in l]
        manader = [l for l in manader if l not in klara and "2000" <= _manad(l) <= "2026-12"]
        print(f"{k}: {len(manader)} månadssitemaps")
        def en(l):
            x = get(l)
            if not x or x.status_code != 200: return l, None
            ut = []
            for b in re.findall(r"<url>(.*?)</url>", x.text, re.S):
                loc = re.search(r"<loc>\s*([^<\s]+)", b)
                if not loc or not SLUG_RX.search(loc[1]): continue
                d = re.search(r"<(?:news:publication_date|lastmod)>\s*([^<\s]+)", b)
                t = re.search(r"<news:title>\s*(.*?)\s*</news:title>", b, re.S)
                ut.append({"medium": k, "url": html.unescape(loc[1]), "manad": _manad(l),
                           "datum": d[1][:10] if d else None, "titel": html.unescape(t[1]) if t else None})
            return l, ut
        with cf.ThreadPoolExecutor(3) as ex, f.open("a") as ut, logg.open("a") as lg:
            for i, (l, rader) in enumerate(ex.map(en, manader)):
                if rader is None: continue
                for rad in rader: ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
                lg.write(l + "\n"); lg.flush()
                if i % 50 == 0: print(f"  {k} {i}/{len(manader)}", flush=True)


def _text(h):
    return re.sub(r"\s+", " ", BeautifulSoup(h or "", "lxml").get_text(" ")).strip()


def wp(medier):
    UT.mkdir(parents=True, exist_ok=True)
    sett = {}
    for k in medier:
        m = MEDIER[k]
        if "wp" not in m: continue
        for q in WP_SOK:
            for sid in range(1, 30):
                r = get(f"{m['wp']}/wp-json/wp/v2/posts", params={"search": q, "per_page": 100, "page": sid,
                                                                  "_fields": "id,date,link,title,excerpt,content"})
                if not r or r.status_code != 200: break
                rader = r.json()
                if not rader: break
                for p in rader:
                    sett[p["link"]] = {"medium": k, "url": p["link"], "datum": p["date"][:10], "titel": _text(p["title"]["rendered"]),
                                       "ingress": _text(p["excerpt"]["rendered"])[:600], "text": _text(p["content"]["rendered"]),
                                       "sokord": q}
                if sid >= int(r.headers.get("x-wp-totalpages", 1)): break
            print(f"  {k} {q}: totalt {sum(1 for v in sett.values() if v['medium'] == k)}", flush=True)
    (UT / "wp.jsonl").write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in sett.values()))
    print(f"{len(sett)} artiklar från fackpressen")


def gnews(_):
    from katalog import PARTIER
    UT.mkdir(parents=True, exist_ok=True)
    fragor = ["bostadspolitik", "marknadshyror", "ränteavdrag", "amorteringskrav", "bostadsbyggande", "hyresrätter", "fastighetsskatt"]
    sett = {}
    for p in ["Socialdemokraterna", "Moderaterna", "Sverigedemokraterna", "Centerpartiet", "Liberalerna",
              "Kristdemokraterna", "Vänsterpartiet", "Miljöpartiet", "regeringen"]:
        for f in fragor:
            r = get(f"https://news.google.com/rss/search?q={quote(p + ' ' + f)}&hl=sv&gl=SE&ceid=SE:sv")
            if not r: continue
            for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
                t = re.search(r"<title>(.*?)</title>", it, re.S); l = re.search(r"<link>(.*?)</link>", it)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it); s = re.search(r"<source url=\"([^\"]*)\">(.*?)</source>", it)
                if not (t and l): continue
                sett[l[1]] = {"medium": "gnews", "kalla": html.unescape(s[2]) if s else "", "url": l[1],
                              "datum": time.strftime("%Y-%m-%d", time.strptime(d[1][5:16], "%d %b %Y")) if d else None,
                              "titel": html.unescape(t[1]), "sokord": f"{p} {f}"}
            time.sleep(1)
    (UT / "gnews.jsonl").write_text("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in sett.values()))
    print(f"{len(sett)} rubriker från Google Nyheter")


def _artikel(rad):
    r = get(rad["url"])
    if not r or r.status_code != 200 or "html" not in r.headers.get("content-type", ""): return None
    s = BeautifulSoup(r.text, "lxml")
    meta = lambda *n: next((t.get("content") for x in n for t in [s.select_one(x)] if t and t.get("content")), None)
    titel = meta("meta[property='og:title']") or (s.h1.get_text(" ", strip=True) if s.h1 else rad.get("titel"))
    datum = meta("meta[property='article:published_time']", "meta[name='publish-date']", "meta[itemprop='datePublished']")
    if not datum:
        m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)', r.text); datum = m[1] if m else None
    ingress = meta("meta[property='og:description']", "meta[name='description']") or ""
    for t in s(["script", "style", "nav", "header", "footer", "aside", "form", "figure"]): t.decompose()
    kropp = s.select_one("article") or s.select_one("main") or s.body
    stycken = [p.get_text(" ", strip=True) for p in (kropp.select("p") if kropp else [])]
    text = "\n\n".join(p for p in stycken if len(p) > 40)
    return {**rad, "titel": titel, "datum": (datum or rad.get("datum") or rad.get("manad") or "")[:10],
            "ingress": ingress[:800], "text": text[:40000]}


def artiklar(medier):
    f = UT / "artiklar.jsonl"
    klara = set()
    if f.exists():
        for l in f.read_text().splitlines():
            try: klara.add(json.loads(l)["url"])
            except Exception: pass
    kand = {}
    for l in (UT / "kandidater.jsonl").read_text().splitlines():
        r = json.loads(l)
        if r["medium"] in medier and r["url"] not in klara: kand[r["url"]] = r
    print(f"{len(kand)} artiklar att hämta")
    with cf.ThreadPoolExecutor(12) as ex, f.open("a") as ut:
        for i, a in enumerate(ex.map(_artikel, kand.values())):
            if a: ut.write(json.dumps(a, ensure_ascii=False) + "\n"); ut.flush()
            if i % 500 == 0: print(f"  {i}/{len(kand)}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("steg", nargs="*", default=["sitemaps", "wp", "gnews", "artiklar"])
    ap.add_argument("--medier", default=",".join(MEDIER))
    a = ap.parse_args()
    for st in a.steg:
        print("==", st); globals()[st](a.medier.split(","))
