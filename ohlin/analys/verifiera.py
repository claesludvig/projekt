"""Kontrollerar att varje citat i citat.py finns i Ohlins inlägg och slår upp källan."""
import json, os, re, sys
HÄR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HÄR)
from citat import CITAT, ÖVRIGA, RÅTEXT
import unicodedata

# Uppenbara OCR-fel i protokolltexten som citaten rättar
RÄTTNINGAR = [(r'\börn\b', 'om'), (r'\beu\b', 'en'), (r'\bbär\b', 'har'), (r'\blia\b', 'ha'), (r'\boell\b', 'och'),
              (r'\bnian\b', 'man'), (r'\bvöre\b', 'vore'), (r'\bbada\b', 'båda'), (r'\bat\b', 'åt'), (r'\bpa\b', 'på'),
              (r'\.dfe\b', 'de'), (r'\barn\b', 'om'), (r'\bstol-ar\b', 'stolar'), (r'\bjlå\b', 'så'),
              (r'arbetsoch', 'arbets- och'), (r're presenterar', 'representerar'), (r'\bsaller\b', 'gäller'),
              (r'\bjäg\b', 'jag'), (r'\^', '')]


def norm(s):
    s = s.lower()
    for a, b in RÄTTNINGAR:
        s = re.sub(a, b, s)
    s = re.sub(r'[»«"”“\'’`^_■•~]', '', s)
    s = re.sub(r'[—–-]+', '-', s)
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'[^\wåäöéü\-.,;:!?()]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def slå_upp():
    R = json.load(open(os.path.join(HÄR, '..', 'data', 'inlagg.json')))
    N = [(r, norm(r['text'])) for r in R]
    ut, fel = {}, []
    for k, c in CITAT.items():
        n = norm(c)
        träff = [r for r, t in N if n in t]
        if not träff:
            fel.append(k)
            continue
        r = träff[0]
        ut[k] = {'text': c, 'datum': r['datum'], 'kammare': r['kammare'].split(' - ')[0], 'dok_id': r['dok_id'],
                 'id': r['id'], 'arende': r['arende'][:120], 'typ': r['typ']}
    return ut, fel


def ordform(s):
    """Gemener utan diakritiska tecken; skräptecken inne i ord tas bort, avstavningar slås ihop."""
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'-\s*\n\s*', '', s)
    s = re.sub(r'[^a-z\s]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def samma_ord(a, b):
    """OCR-tolerant ordjämförelse: samma begynnelsebokstav, nästan samma längd och stavning."""
    from rapidfuzz import fuzz
    return a == b or (a[:1] == b[:1] and abs(len(a) - len(b)) <= 2 and fuzz.ratio(a, b) >= 80)


def ordtäckning(citat, källa):
    """Andel av citatets ord som återfinns i samma ordning i källans bästa matchande avsnitt."""
    from rapidfuzz import fuzz
    al = fuzz.partial_ratio_alignment(citat, källa)
    fönster = källa[max(0, al.dest_start - 40): al.dest_end + 40].split()
    j, träff, ord_ = 0, 0, citat.split()
    for w in ord_:
        for k in range(j, min(len(fönster), j + (4 if träff else len(fönster)))):
            if samma_ord(w, fönster[k]):
                träff, j = träff + 1, k + 1
                break
    return al.score, träff / len(ord_)


def bara_bokstäver(s):
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if c.isalpha() and not unicodedata.combining(c))


def rättelser(rå, citat, max_bokstäver=3):
    """Skillnaderna i bokstavsföljd mellan OCR-råtext och rättat citat. Varje skillnad får omfatta
    högst tre bokstäver, så att hela ord inte kan bytas, läggas till eller strykas."""
    from difflib import SequenceMatcher
    a, b = bara_bokstäver(rå), bara_bokstäver(citat)
    diff = [(a[i1:i2], b[j1:j2]) for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if op != 'equal']
    return diff, all(len(x) <= max_bokstäver and len(y) <= max_bokstäver for x, y in diff)


def slå_upp_övriga():
    """Citat ur ohlin/ovriga. Utan OCR-råtext måste citatet finnas ordagrant i källan (bortsett från
    skiljetecken, versaler och diakritiska tecken). Med OCR-råtext (RÅTEXT) måste råtexten finnas
    exakt i källan och citatet får bara skilja sig från den genom små rättelser inom ord."""
    ut, fel = {}, []
    for k, ((fil, källa, datum, url), text) in ÖVRIGA.items():
        src = open(os.path.join(HÄR, '..', 'ovriga', fil)).read()
        post = {'text': text, 'källa': källa, 'datum': datum, 'url': url, 'fil': fil}
        if k in RÅTEXT:
            rå = RÅTEXT[k]
            if rå not in re.sub(r'\s+', ' ', src):
                fel.append((k, 'råtexten finns inte i källan'))
                continue
            diff, ok = rättelser(rå, text)
            if not ok:
                fel.append((k, f'för stora ändringar: {[d for d in diff if max(map(len, d)) > 3]}'))
                continue
            post.update(rå=rå, rättelser=len(diff))
        elif bara_bokstäver(text) not in bara_bokstäver(src):
            fel.append((k, 'finns inte ordagrant i källan'))
            continue
        ut[k] = post
    return ut, fel


if __name__ == '__main__':
    ut, fel = slå_upp()
    for k, v in ut.items():
        print(f"OK  {k:18s} {v['datum']} {v['kammare']:16s} {v['dok_id']}")
    for k in fel:
        print('SAKNAS', k)
    ö, föl = slå_upp_övriga()
    for k, v in ö.items():
        print(f"OK  {k:18s} {'OCR, ' + str(v['rättelser']) + ' rättelser' if 'rå' in v else 'ordagrant':18s} {v['källa'][:60]}")
    for k, orsak in föl:
        print('FEL', k, orsak)
    sys.exit(1 if fel or föl else 0)
