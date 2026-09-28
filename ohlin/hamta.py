"""Hämtar alla kammarprotokoll 1938–1970 där Bertil Ohlin nämns från Riksdagens öppna data.

Listan sparas i data/protokoll.json, råtexten i data/kallor/txt och en rensad radtext
i data/kallor/clean (båda ignoreras av git; de går att hämta på nytt).
"""
import html, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

HÄR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HÄR, 'data')
TXT = os.path.join(DATA, 'kallor', 'txt')
CLEAN = os.path.join(DATA, 'kallor', 'clean')
API = 'https://data.riksdagen.se'


def lista():
    ut, sida = [], 1
    while True:
        u = (f'{API}/dokumentlista/?sok=Ohlin&doktyp=prot&from=1938-01-01&tom=1970-12-31'
             f'&utformat=json&sz=200&sort=datum&sortorder=asc&p={sida}')
        d = json.load(urllib.request.urlopen(u, timeout=120))['dokumentlista']
        ut += [{k: x.get(k) for k in ('dok_id', 'rm', 'datum', 'titel', 'undertitel', 'beteckning')}
               for x in d.get('dokument') or []]
        print(f'sida {sida}/{d["@sidor"]}: {len(ut)} protokoll', flush=True)
        if sida >= int(d['@sidor']):
            return ut
        sida += 1


def ladda(x):
    f = os.path.join(TXT, x['dok_id'] + '.txt')
    if os.path.exists(f) and os.path.getsize(f):
        return 0
    for _ in range(4):
        try:
            b = urllib.request.urlopen(f'{API}/dokument/{x["dok_id"]}.text', timeout=180).read()
            open(f, 'wb').write(b)
            return len(b)
        except Exception as e:
            fel = e
    print('MISSLYCKADES', x['dok_id'], fel)
    return -1


def rensa(fn):
    t = html.unescape(open(os.path.join(TXT, fn), encoding='utf-8', errors='replace').read())
    t = re.sub(r'</p>|<br\s*/?>', '\n', t)
    t = re.sub(r'</span>\s*<span[^>]*class="line[^"]*"[^>]*>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', '', t))
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n\n', t)
    open(os.path.join(CLEAN, fn), 'w').write(t)


if __name__ == '__main__':
    os.makedirs(TXT, exist_ok=True)
    os.makedirs(CLEAN, exist_ok=True)
    L = lista()
    json.dump(L, open(os.path.join(DATA, 'protokoll.json'), 'w'), ensure_ascii=False, indent=0)
    with ThreadPoolExecutor(8) as ex:
        r = list(ex.map(ladda, L))
    print(f'{sum(v for v in r if v > 0) / 1e6:.0f} MB nytt, {sum(v < 0 for v in r)} misslyckade')
    with ProcessPoolExecutor() as ex:
        list(ex.map(rensa, sorted(os.listdir(TXT))))
