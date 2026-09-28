"""Hämtar riksdagsmotioner 1938–1970 som nämner Ohlin och sparar dem som Ohlin själv undertecknat."""
import html, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

HÄR = os.path.dirname(os.path.abspath(__file__))
KÄLLA = os.path.join(HÄR, 'kallor', 'motioner', 'txt')
UT = os.path.join(HÄR, 'motioner')
API = 'https://data.riksdagen.se'


def lista():
    ut, p = [], 1
    while True:
        u = (f'{API}/dokumentlista/?sok=Ohlin&doktyp=mot&from=1938-01-01&tom=1970-12-31&utformat=json'
             f'&sz=200&sort=datum&sortorder=asc&p={p}')
        d = json.load(urllib.request.urlopen(u, timeout=120))['dokumentlista']
        ut += [{k: x.get(k) for k in ('dok_id', 'rm', 'datum', 'titel', 'undertitel', 'beteckning')}
               for x in d.get('dokument') or []]
        if p >= int(d['@sidor']):  # noqa
            return ut
        p += 1


def ladda(x):
    f = os.path.join(KÄLLA, x['dok_id'] + '.txt')
    if not (os.path.exists(f) and os.path.getsize(f)):
        b = urllib.request.urlopen(f'{API}/dokument/{x["dok_id"]}.text', timeout=180).read().decode('utf-8', 'replace')
        t = html.unescape(b)
        t = re.sub(r'</p>|<br\s*/?>|</span>\s*<span[^>]*class="line[^"]*"[^>]*>', '\n', t)
        t = html.unescape(re.sub(r'<[^>]+>', '', t))
        t = re.sub(r'[ \t]+', ' ', t)
        t = re.sub(r'(?s)^.*?\}\s*(?=\S)', '', t, count=1) if 'Internet Explorer' in t[:3000] else t
        open(f, 'w').write(re.sub(r'\n\s*\n+', '\n', t))
    return x


def ohlins(t):
    """Sant om Ohlin är motionär: nämnd som förslagsställare i rubriken eller som undertecknare."""
    huvud = re.sub(r'\s+', ' ', t[:3000])
    if re.search(r'\b[Aa]v herr (?:Bertil )?Ohlin\b', huvud):
        return 'förslagsställare'
    slut = re.sub(r'\s+', ' ', t[-2500:])
    if re.search(r'\bBertil Ohlin\b|\bB\. Ohlin\b', slut):
        return 'undertecknare'
    return None


if __name__ == '__main__':
    os.makedirs(KÄLLA, exist_ok=True)
    L = lista()
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(ladda, L))
    ut = []
    for x in L:
        t = open(os.path.join(KÄLLA, x['dok_id'] + '.txt')).read()
        roll = ohlins(t)
        if roll:
            huvud = re.sub(r'\s+', ' ', t[:5000])
            huvud = re.sub(r'Kungl\. ?Maj\W{0,3}t', 'Kungl Maj:t', huvud).replace('m. fl.', 'm fl').replace(' m. m.', ' m m')
            m = (re.search(r'Av herr (?:Bertil )?Ohlin[^,]*,\s*(.{8,260}?)\.(?:\s|$)', huvud)
                 or re.search(r'Av (?:herr|herrar|fru|fröken)[^,]{0,120},\s*(.{8,260}?)\.(?:\s|$)', huvud))
            ut.append({**x, 'roll': roll, 'rubrik': m.group(1).strip() if m else '',
                       'url': f'{API}/dokument/{x["dok_id"]}.html'})
    json.dump(ut, open(os.path.join(HÄR, 'motioner.json'), 'w'), ensure_ascii=False, indent=1)
    os.makedirs(UT, exist_ok=True)
    for x in ut:
        open(os.path.join(UT, x['dok_id'] + '.txt'), 'w').write(open(os.path.join(KÄLLA, x['dok_id'] + '.txt')).read())
    print(len(L), 'motioner hämtade,', len(ut), 'med Ohlin som motionär')
