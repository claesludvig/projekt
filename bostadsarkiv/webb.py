#!/usr/bin/env python3
"""Lokal söksida för bostadsarkivet. Kräver bara Python.

    python webb.py            # öppna http://localhost:8765
    python webb.py --port 9000
"""

import argparse
import html
import re
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import sok as sokmodul

DB = sokmodul.DB
TYPNAMN = {"prot": "Protokoll", "sou": "SOU", "ds": "Ds", "dir": "Direktiv", "prop": "Proposition", "bet": "Betänkande", "mot": "Motion"}

CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--mut:#5f6670;--lin:#d9d6cf;--acc:#7a2e3a;--mark:#ffe9a8;--kort:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e6e3dc;--mut:#9aa0a8;--lin:#33363c;
--acc:#e59aa6;--mark:#5a4a12;--kort:#1d2025}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{overflow-wrap:anywhere;margin:0;background:var(--bg);color:var(--fg);
font:16px/1.55 Georgia,'Iowan Old Style',serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.6rem;margin:0 0 4px}h1 a{color:inherit;text-decoration:none}
.sub{color:var(--mut);margin:0 0 20px;font-family:system-ui,sans-serif;font-size:.9rem}
form{display:grid;gap:8px;grid-template-columns:1fr auto;font-family:system-ui,sans-serif}
input,select,button{font:inherit;font-size:.95rem;padding:8px 10px;border:1px solid var(--lin);
border-radius:6px;background:var(--kort);color:var(--fg)}
button{background:var(--acc);color:#fff;border-color:var(--acc);cursor:pointer}
.filter{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px;align-items:center;color:var(--mut);font-size:.85rem}
.filter input[type=number]{width:90px}.filter label{display:flex;gap:4px;align-items:center}
.traff{border-top:1px solid var(--lin);padding:14px 0}
.meta{font-family:system-ui,sans-serif;font-size:.8rem;color:var(--mut)}
.typ{display:inline-block;padding:0 6px;border:1px solid var(--lin);border-radius:4px;margin-right:6px}
.titel{margin:2px 0 4px;font-size:1.02rem}.titel a{color:var(--acc)}
mark{background:var(--mark);color:inherit;padding:0 1px}
.utdrag{margin:0;color:var(--fg)}.antal{font-family:system-ui,sans-serif;color:var(--mut);margin:16px 0 4px}
article p{margin:0 0 .9em}.sida{font-family:system-ui,sans-serif;font-size:.75rem;color:var(--mut);
border-top:1px dashed var(--lin);padding-top:4px;margin-top:18px}
.tips{font-family:system-ui,sans-serif;font-size:.85rem;color:var(--mut);margin-top:24px}
code{font-size:.85em}
"""


def sida(titel, kropp):
    return f"""<!doctype html><html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(titel)}</title>
<style>{CSS}</style></head><body><main>
<h1><a href="/">Bostadsarkivet</a></h1>
<p class="sub">Riksdagens protokoll, propositioner, betänkanden, SOU, Ds och direktiv om bostadsbyggandet 1939–2026</p>
{kropp}</main></body></html>"""


def markera(t, q):
    ord_ = [w.strip('"*').lower() for w in re.findall(r'"[^"]+"|\S+', q)
            if w.upper() not in ("AND", "OR", "NOT")]
    ord_ = [w for w in ord_ if len(w) > 2]
    e = html.escape(t)
    for w in ord_:
        e = re.sub(r"(?i)(" + re.escape(html.escape(w)) + r"\w*)", r"<mark>\1</mark>", e)
    return e


def formular(p):
    v = lambda k: html.escape(p.get(k, ""))
    typer = p.get("typ", "")
    opt = "".join(f'<option value="{k}"{" selected" if typer == k else ""}>{n}</option>'
                  for k, n in [("", "Alla källor")] + list(TYPNAMN.items()))
    sort = p.get("sort", "rang")
    return f"""<form action="/sok">
<input name="q" value="{v('q')}" placeholder='t.ex. räntebidrag*  eller  "allmännyttiga bostadsföretag"' autofocus>
<button>Sök</button>
<div class="filter"><select name="typ">{opt}</select>
<label>från <input type="number" name="fran" value="{v('fran')}" min="1990" max="2030"></label>
<label>till <input type="number" name="till" value="{v('till')}" min="1990" max="2030"></label>
<label>parti <input name="parti" value="{v('parti')}" size="8" placeholder="S M V"></label>
<select name="sort"><option value="rang">Mest relevant</option>
<option value="datum"{" selected" if sort == "datum" else ""}>Äldst först</option></select></div></form>"""


class Hanterare(BaseHTTPRequestHandler):
    def svara(self, kropp, status=200):
        b = kropp.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        db = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
        try:
            if u.path == "/":
                self.svara(sida("Bostadsarkivet", formular(p) + self.oversikt(db)))
            elif u.path == "/sok":
                self.svara(sida(f"{p.get('q', '')} – Bostadsarkivet", formular(p) + self.traffar(db, p)))
            elif u.path.startswith("/anf/"):
                self.svara(self.anforande(db, urllib.parse.unquote(u.path[5:]), p.get("q", "")))
            elif u.path.startswith("/dok/"):
                self.svara(self.dokument(db, urllib.parse.unquote(u.path[5:]), p.get("q", "")))
            else:
                self.svara(sida("Saknas", "<p>Sidan finns inte.</p>"), 404)
        except sqlite3.OperationalError as e:
            self.svara(sida("Fel", formular(p) + f"<p>Frågan gick inte att tolka: {html.escape(str(e))}</p>"), 400)
        finally:
            db.close()

    def oversikt(self, db):
        rader = db.execute("SELECT typ, COUNT(*) n, MIN(ar) a, MAX(ar) b FROM kallor GROUP BY typ").fetchall()
        lista = "".join(f"<li>{TYPNAMN.get(r['typ'], r['typ'])}: {r['n']:,} ({r['a']}–{r['b']})</li>"
                        .replace(",", " ") for r in rader)
        return f"""<p class="antal">Innehåll</p><ul>{lista}</ul>
<p class="tips">Sökningen gäller hela texten. Flera ord måste alla finnas. <code>"…"</code> söker fras,
<code>*</code> söker ordbörjan (<code>bostadsbygg*</code>), <code>OR</code> och <code>NOT</code> fungerar.
Protokollen är uppdelade per anförande, utredningarna i avsnitt om ett par sidor.</p>"""

    def traffar(self, db, p):
        q = p.get("q", "").strip()
        if not q:
            return ""
        typ = [p["typ"]] if p.get("typ") else None
        parti = p.get("parti", "").split() or None
        heltal = lambda k: int(p[k]) if p.get(k, "").isdigit() else None
        rader = sokmodul.sok(db, q, typ, heltal("fran"), heltal("till"), parti, p.get("sort", "rang"), 200)
        ut = [f'<p class="antal">{len(rader)}{"+" if len(rader) == 200 else ""} träffar</p>']
        for r in rader:
            lank = (f"/anf/{r['ref']}" if r["typ"] == "prot" else f"/dok/{r['ref']}") + "?q=" + urllib.parse.quote(q)
            utdrag = html.escape(r["utdrag"]).replace("[", "<mark>").replace("]", "</mark>")
            ut.append(f"""<div class="traff"><div class="meta"><span class="typ">{TYPNAMN.get(r['typ'], r['typ'])}</span>
{html.escape(r['datum'] or '')} · {html.escape(r['kalla'] or '')}</div>
<div class="titel"><a href="{lank}">{html.escape(r['titel'] or '')}</a></div>
<p class="utdrag">{utdrag}</p></div>""")
        return "".join(ut)

    def anforande(self, db, aid, q):
        a = db.execute("SELECT * FROM anforanden WHERE id = ?", (aid,)).fetchone()
        if not a:
            return sida("Saknas", "<p>Anförandet finns inte.</p>")
        stycken = "".join(f"<p>{markera(s, q)}</p>" for s in a["text"].split("\n\n"))
        grannar = db.execute("""SELECT id, anf_nr, talare, parti FROM anforanden
                                WHERE prot_id = ? AND rubrik = ? ORDER BY anf_nr""",
                             (a["prot_id"], a["rubrik"])).fetchall()
        debatt = " · ".join(
            (f"<b>{g['anf_nr']} {html.escape(g['talare'])}</b>" if g["id"] == aid else
             f'<a href="/anf/{g["id"]}?q={urllib.parse.quote(q)}">{g["anf_nr"]} {html.escape(g["talare"])}</a>')
            + (f" ({g['parti']})" if g["parti"] else "") for g in grannar)
        titel = f"{a['talare']} ({a['parti']})" if a["parti"] else a["talare"]
        return sida(titel, f"""<div class="meta">Prot. {a['rm']}:{a['prot_nr']}, anf. {a['anf_nr']} ·
{a['datum']}{' · replik' if a['replik'] else ''} · <a href="{a['url']}">riksdagen.se</a></div>
<h2 class="titel">{html.escape(titel)}</h2><div class="meta">{html.escape(a['rubrik'])}</div>
<p class="meta">Debatten: {debatt}</p><article>{stycken}</article>""")

    def dokument(self, db, ref, q):
        if ref.isdigit():
            v = db.execute("SELECT dok_id, nr FROM avsnitt WHERE id = ?", (int(ref),)).fetchone()
            dok_id, fokus = (v["dok_id"], v["nr"]) if v else (None, None)
        else:
            dok_id, fokus = ref, None
        d = db.execute("SELECT * FROM dokument WHERE id = ?", (dok_id,)).fetchone()
        if not d:
            return sida("Saknas", "<p>Dokumentet finns inte.</p>")
        delar, senaste = [], None
        for v in db.execute("SELECT nr, sida, rubrik, text FROM avsnitt WHERE dok_id = ? ORDER BY nr", (dok_id,)):
            if v["sida"] and v["sida"] != senaste:
                delar.append(f'<div class="sida">PDF-sida {v["sida"]}</div>')
                senaste = v["sida"]
            ankare = ' id="fokus"' if v["nr"] == fokus else ""
            delar.append(f"<section{ankare}>" + "".join(f"<p>{markera(s, q)}</p>" for s in v["text"].split("\n\n"))
                         + "</section>")
        hopp = '<script>document.getElementById("fokus")?.scrollIntoView()</script>' if fokus else ""
        pdf = f' · <a href="{d["pdf_url"]}">PDF</a>' if d["pdf_url"] else ""
        return sida(d["beteckning"], f"""<div class="meta">{html.escape(d['beteckning'])} · {d['datum']} ·
{'KB' if d['kalla'] == 'kb' else 'riksdagen.se'}: <a href="{d['url']}">källa</a>{pdf} ·
relevans {d['grad']} ({d['karna']} kärnträffar)</div>
<h2 class="titel">{html.escape(d['titel'])}</h2><article>{''.join(delar)}</article>{hopp}""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    print(f"Bostadsarkivet: http://localhost:{a.port}")
    ThreadingHTTPServer(("127.0.0.1", a.port), Hanterare).serve_forever()


if __name__ == "__main__":
    main()
