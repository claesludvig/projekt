"""Kontrollerar att varje citat i citat.py finns i Ohlins inlägg och slår upp källan."""
import json, os, re, sys
HÄR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HÄR)
from citat import CITAT

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


if __name__ == '__main__':
    ut, fel = slå_upp()
    for k, v in ut.items():
        print(f"OK  {k:18s} {v['datum']} {v['kammare']:16s} {v['dok_id']}")
    for k in fel:
        print('SAKNAS', k)
    sys.exit(1 if fel else 0)
