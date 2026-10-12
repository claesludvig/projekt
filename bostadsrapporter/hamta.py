"""Hittar och laddar ner rapporter och analyser om bostadsmarknaden från aktörerna i katalog.py.

Steg:
  1. sitemaps   alla URL:er per aktör              -> data/sitemaps/<aktör>.txt
  2. sidor      rapportsidor som rör bostäder      -> data/sidor.jsonl (titel, datum, ingress, PDF-länkar)
  3. pdf        rapporterna själva                 -> data/pdf/<aktör>/<id>.pdf (ej i git)
  4. text       pdftotext per sida                 -> data/text/<aktör>/<id>.json.gz

  python hamta.py [steg ...] [--aktor sn,fa]
Extra sidor som inte finns i någon sitemap (t.ex. HSB) läggs i extra_sidor.txt: "<aktör> <url>".
"""
import argparse, concurrent.futures as cf, gzip, hashlib, json, re, subprocess, sys, time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

from katalog import AKTORER, META_SIDA, SLUG, SLUG_BYGG, TERM_RX, WP_ALLA

ROT = Path(__file__).parent
DATA = ROT / "data"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Accept-Language": "sv-SE,sv;q=0.9"}
S = requests.Session(); S.headers.update(H)


def get(u, **kw):
    for i in range(3):
        try:
            r = S.get(u, timeout=60, **kw)
            if r.status_code in (429, 503):
                time.sleep(5 * (i + 1)); continue
            return r
        except requests.RequestException:
            time.sleep(2 * (i + 1))
    return None


# ---------- 1. sitemaps ----------
def _walk(u, seen, out):
    if u in seen: return
    seen.add(u)
    r = get(u)
    if not r or r.status_code != 200: return
    c = r.content
    if c[:2] == b"\x1f\x8b": c = gzip.decompress(c)
    x = c.decode("utf8", "replace")
    locs = [l.replace("&amp;", "&").strip() for l in re.findall(r"<loc>\s*(.*?)\s*</loc>", x, re.S)]
    if "<sitemapindex" in x:
        for l in locs: _walk(l, seen, out)
    else:
        out.extend(locs)


def sitemaps(aktorer):
    (DATA / "sitemaps").mkdir(parents=True, exist_ok=True)
    for k in aktorer:
        sm = AKTORER[k]["sitemap"]
        if not sm: continue
        out = []; _walk(sm, set(), out)
        (DATA / "sitemaps" / f"{k}.txt").write_text("\n".join(sorted(set(out))) + "\n")
        print(f"{k}: {len(set(out))} URL:er")


# ---------- 2. sidor ----------
def kandidater(aktorer):
    ut = []
    for k in aktorer:
        a = AKTORER[k]; f = DATA / "sitemaps" / f"{k}.txt"
        urls = f.read_text().split() if f.exists() else []
        rx = re.compile(a["sida"], re.I)
        for u in urls:
            if not rx.search(u): continue
            if a["slug"] and not SLUG.search(unquote(urlparse(u).path)): continue
            if re.search(r"/(en|english)/|kalender|evenemang|events/|webbinar|/jobb|lediga-tjanster", u): continue
            ut.append((k, u))
        if k in META_SIDA:
            mrx = re.compile(META_SIDA[k], re.I)
            ut += [(k, u) for u in urls if mrx.search(u) and not re.search(r"/(en|english)/", u)]
    extra = ROT / "extra_sidor.txt"
    if extra.exists():
        for rad in extra.read_text().splitlines():
            if rad.strip() and not rad.startswith("#"):
                k, u = rad.split(None, 1)
                if k in aktorer: ut.append((k, u.strip()))
    return list(dict.fromkeys(ut))


DATUM_RX = re.compile(r"(20\d\d|19\d\d)-(\d\d)-(\d\d)")
MANADER = {m: i + 1 for i, m in enumerate(["januari", "februari", "mars", "april", "maj", "juni", "juli",
                                            "augusti", "september", "oktober", "november", "december"])}
SV_DATUM = re.compile(r"\b(\d{1,2}) (" + "|".join(MANADER) + r") (20\d\d)\b", re.I)


def _datum(soup, html, url):
    for sel, attr in [("meta[property='article:published_time']", "content"), ("meta[name='date']", "content"),
                      ("meta[name='publishdate']", "content"), ("meta[name='DC.date']", "content"),
                      ("meta[itemprop='datePublished']", "content"), ("time[datetime]", "datetime")]:
        t = soup.select_one(sel)
        if t and t.get(attr) and DATUM_RX.search(t[attr]):
            return "-".join(DATUM_RX.search(t[attr]).groups())
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d\d-\d\d)', html)
    if m: return m[1]
    txt = soup.get_text(" ", strip=True)[:6000]
    m = SV_DATUM.search(txt)
    if m: return f"{m[3]}-{MANADER[m[2].lower()]:02d}-{int(m[1]):02d}"
    m = re.search(r"/(20\d\d)/(\d\d)/", url)
    if m: return f"{m[1]}-{m[2]}-01"
    m = re.search(r"/(20\d\d)/", url)
    if m: return f"{m[1]}-01-01"
    return None


def _pdflankar(soup, bas):
    ut = []
    for a in soup.select("a[href]"):
        h = a["href"].strip()
        if not re.search(r"\.pdf($|\?)", h, re.I) and "bilder_och_dokument/rapporter" not in h: continue
        u = urljoin(bas, h)
        if not urlparse(u).scheme.startswith("http"): continue
        ut.append({"url": u, "text": a.get_text(" ", strip=True)[:200]})
    return list({p["url"]: p for p in ut}.values())


def _sida(k, u):
    try:
        return _sida_(k, u)
    except Exception as e:
        print("  fel", u, e, file=sys.stderr); return None


def _sida_(k, u):
    if re.search(r"\.pdf($|\?)", u, re.I):
        namn = unquote(Path(urlparse(u).path).stem).replace("-", " ").replace("_", " ")
        return {"aktor": k, "url": u, "titel": namn, "datum": None, "ingress": "", "pdf": [{"url": u, "text": namn}],
                "traffar": 0, "titeltraff": bool(SLUG.search(u))}
    r = get(u)
    if not r or r.status_code != 200 or "html" not in r.headers.get("content-type", ""): return None
    html = r.text; soup = BeautifulSoup(html, "lxml")
    og = soup.select_one("meta[property='og:title']")
    titel = (og.get("content") if og else None) or (soup.h1.get_text(" ", strip=True) if soup.h1 else "") or (soup.title.string if soup.title else None) or u
    titel = re.sub(r"\s*[|–-]\s*(Svenskt Näringsliv|Fastighetsägarna|HSB|Hyresgästföreningen|Stockholms Handelskammare|Byggföretagen|Sveriges Allmännytta|Riksbyggen|Timbro|Boverket|Svenska Bankföreningen|Finance Sweden)\s*$", "", titel.strip())
    d = soup.select_one("meta[property='og:description']") or soup.select_one("meta[name='description']")
    for t in soup(["script", "style", "nav", "header", "footer", "form"]): t.decompose()
    main = soup.select_one("main") or soup.body or soup
    text = main.get_text(" ", strip=True)
    return {"aktor": k, "url": u, "titel": titel, "datum": _datum(BeautifulSoup(html, "lxml"), html, u),
            "ingress": ((d.get("content") if d else "") or "")[:600], "pdf": _pdflankar(main, u),
            "traffar": len(TERM_RX.findall(text)), "titeltraff": bool(SLUG.search(titel + " " + u)),
            "brodtext": text[:20000]}


def sidor(aktorer):
    kand = kandidater(aktorer)
    print(f"{len(kand)} kandidatsidor")
    f = DATA / "sidor.jsonl"
    gamla = {}
    if f.exists():
        for rad in f.read_text().splitlines():
            try:
                r = json.loads(rad); gamla[r["url"]] = r
            except json.JSONDecodeError:
                pass
    nya = [(k, u) for k, u in kand if u not in gamla]
    with cf.ThreadPoolExecutor(16) as ex, f.open("a") as ut:
        for i, r in enumerate(ex.map(lambda x: _sida(*x), nya)):
            if r:
                gamla[r["url"]] = r; ut.write(json.dumps(r, ensure_ascii=False) + "\n"); ut.flush()
            if i % 200 == 0: print(f"  {i}/{len(nya)}", flush=True)
    f.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in gamla.values()))
    print(f"{len(gamla)} sidor sparade")


# ---------- 2c. rendera ----------
def rendera(aktorer):
    """Sajter som bygger sidan med JavaScript: rendera i Chromium (rendera.js, kräver Node och Playwright)."""
    js = [k for k in aktorer if AKTORER[k].get("js")]
    urls = [(k, u) for k, u in kandidater(js) if not re.search(r"\.pdf($|\?)", u, re.I)]
    lista = DATA / "rendera_urls.txt"
    lista.write_text("\n".join(u for _, u in urls) + "\n")
    akt = dict((u, k) for k, u in urls)
    npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    o = subprocess.run(["node", str(ROT / "rendera.js"), str(lista)], capture_output=True, text=True,
                       env={**__import__("os").environ, "NODE_PATH": npm}).stdout
    with (DATA / "renderade.jsonl").open("w") as ut:
        for rad in o.splitlines():
            r = json.loads(rad); u = r["url"]
            titel = (r.get("h1") or r.get("titel") or u).strip()
            soup = BeautifulSoup("", "lxml")
            m = SV_DATUM.search(r["text"][:4000]) or None
            datum = f"{m[3]}-{MANADER[m[2].lower()]:02d}-{int(m[1]):02d}" if m else _datum(soup, "", u)
            ut.write(json.dumps({"aktor": akt[u], "url": u, "titel": titel, "datum": datum, "ingress": (r.get("desc") or "")[:600],
                                 "pdf": list({_norm(p["url"]): p for p in r["pdf"]}.values()),
                                 "traffar": len(TERM_RX.findall(r["text"])), "titeltraff": bool(SLUG.search(titel + " " + u)),
                                 "brodtext": r["text"][:20000]}, ensure_ascii=False) + "\n")
    print(f"{len(o.splitlines())} sidor renderade av {len(urls)}")


# ---------- 2b. wp ----------
def wp(aktorer):
    """WordPress-sajter: alla PDF:er i mediebiblioteket, med titel och uppladdningsdatum."""
    with (DATA / "wp.jsonl").open("w") as ut:
        for k in aktorer:
            a = AKTORER[k]
            if not a.get("wp"): continue
            bas = "https://" + urlparse(a["sitemap"]).netloc
            n = 0
            for sid in range(1, 100):
                r = get(f"{bas}/wp-json/wp/v2/media", params={"mime_type": "application/pdf", "per_page": 100, "page": sid})
                if not r or r.status_code != 200: break
                rader = r.json()
                if not rader: break
                for m in rader:
                    u = m.get("source_url"); titel = BeautifulSoup((m.get("title") or {}).get("rendered", ""), "lxml").get_text()
                    if not u: continue
                    ut.write(json.dumps({"aktor": k, "url": u, "titel": titel, "datum": (m.get("date") or "")[:10] or None,
                                         "ingress": "", "pdf": [{"url": u, "text": titel}], "traffar": 0,
                                         "titeltraff": bool(SLUG.search(titel + " " + unquote(u))), "wp": True},
                                        ensure_ascii=False) + "\n")
                    n += 1
                if sid >= int(r.headers.get("x-wp-totalpages", 1)): break
            print(f"{k}: {n} PDF:er i mediebiblioteket")


# ---------- 3. pdf ----------
def pid(u):
    return hashlib.sha1(u.encode()).hexdigest()[:12]


def _norm(u):
    return unquote(u).split("?")[0].replace("http://", "https://").replace("://www.", "://").lower()


def valda_pdf(aktorer):
    """Rapporter = PDF:er länkade från bostadsrelevanta sidor. Samma PDF från flera sidor räknas en gång."""
    ut = {}
    rader = (DATA / "sidor.jsonl").read_text().splitlines()
    if (DATA / "wp.jsonl").exists(): rader += (DATA / "wp.jsonl").read_text().splitlines()
    alla = {}
    if (DATA / "renderade.jsonl").exists(): rader += (DATA / "renderade.jsonl").read_text().splitlines()
    for rad in rader:
        try:
            r = json.loads(rad)
        except json.JSONDecodeError:
            continue
        alla[r["url"] + ("#wp" if r.get("wp") else "")] = r      # renderade sidor läses sist och ersätter
    alla = list(alla.values())
    lankad = {}
    for s in alla:
        if s.get("wp"): continue
        for p in s["pdf"]:
            lankad.setdefault(_norm(p["url"]), s)
    for s in alla:
        if s.get("wp") and _norm(s["url"]) in lankad:
            m = lankad[_norm(s["url"])]
            s = {**s, "sida_meta": m["url"], "sidtitel_meta": m["titel"], "datum_meta": m["datum"], "ingress": m["ingress"]}
        if s["aktor"] not in aktorer: continue
        if s.get("wp"):
            namn = s["titel"] + " " + unquote(Path(urlparse(s["url"]).path).name)
            rx = SLUG_BYGG if s["aktor"] == "bf" else SLUG
            if s["aktor"] not in WP_ALLA and not rx.search(namn): continue
        elif not (s["titeltraff"] or s["traffar"] >= 3): continue
        egen = re.sub(r"^www\.", "", urlparse(AKTORER[s["aktor"]]["sitemap"] or s["url"]).netloc)
        for p in s["pdf"]:
            vard = urlparse(p["url"]).netloc
            if not s.get("wp") and not vard.endswith(egen) and vard not in AKTORER[s["aktor"]].get("pdfvard", []): continue    # andras rapporter som aktören länkar till
            if re.search(r"(fullmakt|blankett|ansokan|avtal|stadgar|policy|integritet|logo|cookie|arsredovisning|"
                         r"arsberattelse|bolagsstyrning|hallbarhetsredovisning|faktura|anmalan|mall)", p["url"], re.I):
                continue
            if s.get("sida_meta"):
                ut.setdefault(_norm(p["url"]), {"aktor": s["aktor"], "pdf": p["url"], "lanktext": s["titel"], "sida": s["sida_meta"],
                                         "sidtitel": s["sidtitel_meta"], "datum": s["datum_meta"] or s["datum"],
                                         "ingress": s["ingress"]})
            else:
                ut.setdefault(_norm(p["url"]), {"aktor": s["aktor"], "pdf": p["url"], "lanktext": p["text"], "sida": s["url"],
                                         "sidtitel": s["titel"], "datum": s["datum"], "ingress": s["ingress"],
                                         "wp": s.get("wp", False)})
    return list(ut.values())


def pdf(aktorer):
    rapp = valda_pdf(aktorer)
    print(f"{len(rapp)} PDF:er att hämta")
    def ett(r):
        mal = DATA / "pdf" / r["aktor"] / f"{pid(r['pdf'])}.pdf"
        if mal.exists(): return "fanns"
        mal.parent.mkdir(parents=True, exist_ok=True)
        x = get(r["pdf"])
        if not x or x.status_code != 200 or not x.content.startswith(b"%PDF"): return "fel"
        mal.write_bytes(x.content); return "ny"
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(ett, rapp))
    print({k: res.count(k) for k in set(res)})
    (DATA / "pdf_lista.json").write_text(json.dumps(rapp, ensure_ascii=False, indent=0))


# ---------- 4. text ----------
def _pdfinfo(f):
    try:
        o = subprocess.run(["pdfinfo", str(f)], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return {}
    return dict(re.findall(r"^([^:]+):\s*(.*)$", o, re.M))


def text(aktorer):
    rapp = [r for r in json.loads((DATA / "pdf_lista.json").read_text()) if r["aktor"] in aktorer]
    def ett(r):
        f = DATA / "pdf" / r["aktor"] / f"{pid(r['pdf'])}.pdf"
        mal = DATA / "text" / r["aktor"] / f"{pid(r['pdf'])}.json.gz"
        if not f.exists(): return None
        if mal.exists(): return "fanns"
        info = _pdfinfo(f)
        try:
            o = subprocess.run(["pdftotext", "-enc", "UTF-8", str(f), "-"], capture_output=True, timeout=300).stdout.decode("utf8", "replace")
        except subprocess.TimeoutExpired:
            return "fel"
        sidor_ = o.split("\f")
        mal.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(mal, "wt", encoding="utf8") as g:
            json.dump({"pdf": r["pdf"], "info": {k: info.get(k) for k in ("Title", "Author", "CreationDate", "Pages")},
                       "sidor": sidor_}, g, ensure_ascii=False)
        return "ny"
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(ett, rapp))
    print({k: res.count(k) for k in set(res)})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("steg", nargs="*", default=["sitemaps", "sidor", "pdf", "text"])
    ap.add_argument("--aktor", default=",".join(AKTORER))
    a = ap.parse_args()
    akt = a.aktor.split(",")
    for s in a.steg:
        print(f"== {s}"); globals()[s](akt)
