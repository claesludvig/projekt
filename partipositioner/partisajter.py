"""Partiernas egna sidor och program om bostadspolitik, hämtade från deras webbplatser i dag
(en arkivkopia per hämtning). Tidigare versioner hämtas ur Wayback Machine med wayback.py.

  data/partisajter/<parti>.jsonl   en rad per sida eller PDF: url, titel, datum, text
"""
import concurrent.futures as cf, gzip, json, re, subprocess, sys, time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROT = Path(__file__).parent
UT = ROT / "data" / "partisajter"
RAW = ROT / "data" / "arkiv" / "raw"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/124"

SAJTER = {
    "s":  ["https://www.socialdemokraterna.se/rest-api/sitemapXml"],
    "m":  ["https://moderaterna.se/sitemap_index.xml"],
    "c":  ["https://www.centerpartiet.se/sitemapindex.xml"],
    "l":  ["https://www.liberalerna.se/sitemap_index.xml"],
    "kd": ["kryp:https://kristdemokraterna.se/var-politik"],
    "v":  [],   # vansterpartiet.se spärrar automatiska hämtningar (Cloudflare); V:s texter kommer från Vivill och motionerna
    "mp": ["https://www.mp.se/sitemap.xml"],
    "sd": ["https://sd.se/sitemap.xml", "https://sd.se/sitemap_index.xml", "https://sd.se/wp-sitemap.xml"],
}
SLUG = re.compile(r"bostad|bostader|hyr|hyres|boende|bygga|byggande|amorter|bolan|ranteavdrag|fastighetsskatt|"
                  r"fastighetsavgift|allmannytt|flyttskatt|egnahem|agarlagenhet|bosparande|startlan|hemlos|trangbodd", re.I)
LOKAL = re.compile(r"moderaterna\.se/(?!sitemap)[a-z]+/|/(lokalt|kommun|region|distrikt|forening|kalender|evenemang|jobb)/", re.I)


def get(u):
    for i in range(3):
        try:
            r = S.get(u, timeout=60)
            if r.status_code == 200: return r
            if r.status_code in (403, 404, 410): return None
        except requests.RequestException:
            pass
        time.sleep(3 * (i + 1))
    return None


def _walk(u, seen, out, djup=0):
    if u in seen or djup > 3: return
    seen.add(u); r = get(u)
    if not r: return
    c = r.content
    if c[:2] == b"\x1f\x8b": c = gzip.decompress(c)
    x = c.decode("utf8", "replace")
    locs = [l.replace("&amp;", "&") for l in re.findall(r"<loc>\s*([^<\s]+)", x)]
    if "<sitemapindex" in x:
        for l in locs:
            if not LOKAL.search(l): _walk(l, seen, out, djup + 1)
    else:
        out += locs


def _text_html(h):
    s = BeautifulSoup(h, "lxml")
    og = s.select_one("meta[property='og:title']"); titel = og.get("content") if og else (s.h1.get_text(" ", strip=True) if s.h1 else "")
    d = s.select_one("meta[property='article:published_time']") or s.select_one("meta[property='article:modified_time']")
    datum = d.get("content", "")[:10] if d else None
    if not datum:
        m = re.search(r'"date(?:Published|Modified)"\s*:\s*"(\d{4}-\d\d-\d\d)', h); datum = m[1] if m else None
    pdfer = [urljoin("https://x", a["href"]) for a in s.select("a[href$='.pdf'], a[href*='.pdf?']")]
    for t in s(["script", "style", "nav", "header", "footer", "form", "aside"]): t.decompose()
    m = s.select_one("main") or s.select_one("article") or s.body
    text = "\n\n".join(p.get_text(" ", strip=True) for p in (m.select("h1,h2,h3,p,li") if m else []) if p.get_text(strip=True))
    return titel, datum, text, pdfer


def _kryp(start, djup=2):
    """För sajter utan sitemap: följ länkar inom politiksidorna."""
    bas = urlparse(start).netloc; sett, nu, ut = set(), [start], []
    for _ in range(djup):
        nya = []
        for u in nu:
            if u in sett: continue
            sett.add(u); r = get(u)
            if not r: continue
            for a in BeautifulSoup(r.text, "lxml").select("a[href]"):
                h = urljoin(u, a["href"]).split("#")[0]
                if urlparse(h).netloc == bas and "/var-politik" in h: nya.append(h); ut.append(h)
        nu = nya
    return ut


def parti(k):
    urls = []
    for sm in SAJTER[k]:
        if sm.startswith("kryp:"): urls += _kryp(sm[5:])
        else: _walk(sm, set(), urls)
        if urls: break
    urls = sorted({u for u in urls if SLUG.search(u) and not LOKAL.search(u)})
    print(f"{k}: {len(urls)} sidor", flush=True)
    idag = date.today().isoformat(); ut = []
    def en(u):
        r = get(u)
        if not r: return []
        if r.content.startswith(b"%PDF"):
            RAW.mkdir(parents=True, exist_ok=True); f = RAW / f"{k}_{abs(hash(u))}.pdf"; f.write_bytes(r.content)
            t = subprocess.run(["pdftotext", "-enc", "UTF-8", str(f), "-"], capture_output=True).stdout.decode("utf8", "replace")
            return [{"parti": k, "url": u, "titel": Path(urlparse(u).path).stem.replace("-", " "), "datum": None, "hamtad": idag, "text": t}]
        titel, datum, text, pdfer = _text_html(r.text)
        rader = [{"parti": k, "url": u, "titel": titel, "datum": datum, "hamtad": idag, "text": text}]
        for p in pdfer[:5]:
            p = urljoin(u, p)
            if SLUG.search(p) or re.search(r"program|manifest|plattform|rapport", p, re.I):
                x = get(p)
                if x and x.content.startswith(b"%PDF"):
                    RAW.mkdir(parents=True, exist_ok=True); f = RAW / f"{k}_{abs(hash(p))}.pdf"; f.write_bytes(x.content)
                    t = subprocess.run(["pdftotext", "-enc", "UTF-8", str(f), "-"], capture_output=True).stdout.decode("utf8", "replace")
                    rader.append({"parti": k, "url": p, "titel": Path(urlparse(p).path).stem.replace("-", " "), "datum": datum,
                                  "hamtad": idag, "text": t, "fran_sida": u})
        return rader
    with cf.ThreadPoolExecutor(4) as ex:
        for r in ex.map(en, urls): ut += r
    UT.mkdir(parents=True, exist_ok=True)
    (UT / f"{k}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in ut))
    print(f"{k}: {len(ut)} sparade", flush=True)


if __name__ == "__main__":
    for k in (sys.argv[1:] or SAJTER):
        parti(k)
