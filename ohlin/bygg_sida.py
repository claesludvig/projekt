"""Skriver data/inlagg-webb.json, det kompakta dataformat som index.html läser in."""
import json, os, re

HÄR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HÄR, 'data')
R = json.load(open(os.path.join(DATA, 'inlagg.json')))
TEMAN = sorted({t for r in R for t in r['teman']})


def ärende(r):
    a = re.sub(r'\s+', ' ', r['arende'] or '').strip()
    a = re.split(r' (?:Herr|Fru|Hans excellens|Chefen för|Ordet lämnades|Under denna punkt|Föredrogs|Föredrogos|Fortsattes|Avlämnades|Kungl\. Maj:t hade) ', a)[0] or a
    a = re.sub(r'\s*\((?:F|f)orts\.?\)\.?', '', a).strip()
    if r['punkt'] and not a.lower().startswith('punkt'):
        a = f"{a} – {r['punkt']}" if a else r['punkt']
    return a[:180]


ut = {'teman': TEMAN, 'inlagg': [{
    'id': r['id'], 'd': r['datum'], 'k': 'FK' if r['kammare'].startswith('Första') else 'AK',
    't': 'g' if r['typ'] == 'kort genmäle' else 'a', 'o': r['ord'], 'a': ärende(r),
    'te': [TEMAN.index(t) for t in r['teman']], 'p': r['dok_id'], 'x': r['text']} for r in R]}
json.dump(ut, open(os.path.join(DATA, 'inlagg-webb.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(R), 'inlägg,', os.path.getsize(os.path.join(DATA, 'inlagg-webb.json')) // 1000, 'kB')
