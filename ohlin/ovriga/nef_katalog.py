"""Förteckning över Nationalekonomiska föreningens sammanträden 1925–1972 där Bertil Ohlin talade.

Läser innehållsförteckningen i varje årgång (kallor/nef/txt), plockar ut sammanträden där Ohlin
står som inledare eller talare och sparar varje sådant sammanträde som egen textfil i nef/.
"""
import json, os, re, unicodedata

HÄR = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(HÄR, 'kallor', 'nef', 'txt')
UT = os.path.join(HÄR, 'nef')
MÅN = 'januari februari mars april maj juni juli augusti september oktober november december'.split()


def fold(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


rMöte = re.compile(r's\w{0,3}m\w{0,4}n\w{0,3}r\w{0,3}d\w{0,2}t\s+den\s+(\d{1,2})\s*([a-zåäö]+)', re.I)
rOhlin = re.compile(r'(?:professor|docent\w*|statsr\w+|herr|fil\.?\s*dr\.?)?\s*(?:b\w{0,2}\.?|bertil)?\s*ohlin', re.I)


# Rättade rubriker och datum där OCR-texten i innehållsförteckningen är för brusig
RÄTTAT = {
    '1930-03-04': 'Vårt jordbruks krisläge', '1930-10-23': 'Handelspolitiskt samarbete i Europa',
    '1932-01-21': 'Några synpunkter på årets budgetförslag', '1932-11-25': 'Offentliga arbeten i depressionstider',
    '1933-11-22': 'Järnvägar och bilar', '1934-09-26': 'Räntenivåns framtid', '1934-11-20': 'Planhushållning',
    '1936-01-23': 'Den nya budgeten', '1936-12-09': 'Arbetslöshetspolitik under högkonjunktur',
    '1937-12-02': 'Nya lagregler angående aktiebolags rätt att utdela vinst?', '1939-01-26': 'Budgetläget',
    '1939-04-25': 'Den ekonomiska politikens möjligheter', '1939-05-16': 'Sveriges ekonomi inför världsläget',
    '1939-10-05': 'Den aktuella pris- och lönepolitikens möjligheter',
    '1941-04-02': 'Vår livsmedelsförsörjning – en blick framåt', '1941-11-25': 'Aktuella arbetsmarknadsproblem',
    '1942-02-12': 'Budgeten och samhällsekonomin', '1942-03-18': 'Bostadsproduktion och hyresmarknad',
    '1943-01-29': 'Budgeten och den ekonomiska politiken', '1943-10-15': 'Vår pris- och lönepolitik efter kriget',
    '1943-12-14': 'Internationell efterkrigsplanering för livsmedelsförsörjningen och jordbruket',
    '1944-01-24': 'Budgeten och penningvärdet', '1953-10-13': 'Convertibility',
    '1956-04-20': 'Näringslivets kapitalförsörjning', '1957-10-24': 'Europeiskt frihandelsområde och nordisk tullunion',
    '1964-01-14': 'Årets statsverksproposition', '1967-01-16': 'Årets statsverksproposition',
    '1968-01-16': 'Årets statsverksproposition', '1968-10-23': 'Investeringar i u-länderna (paneldiskussion)',
    '1969-02-27': 'Nordek – problem och förutsättningar', '1970-04-02': 'Beskattning och kapitalbildning',
    '1970-10-28': 'Inflation och valutaproblem', '1971-01-18': 'Årets statsverksproposition',
    '1971-03-30': 'Långtidsutredningarnas problematik (paneldiskussion)', '1968-04-29': 'Asian Drama',
}
ODATERAT = {(1942, 'budgeten'): '1942-02-12', (1942, 'bostads'): '1942-03-18', (1943, 'internationell'): '1943-12-14'}


def månad(s):
    f = fold(s)
    for i, m in enumerate(MÅN):
        if fold(m)[:3] == f[:3]:
            return i + 1
    return None


def katalog():
    ut = []
    for fn in sorted(os.listdir(TXT)):
        år = int(fn[3:7])
        sidor = open(os.path.join(TXT, fn)).read().split('<<<SIDA ')[1:]
        # innehållsförteckningen: sidorna innan det första sammanträdets text börjar
        toc_slut = next((i for i, s in enumerate(sidor[:15]) if re.search(r'inledde|anf\w*rde', s, re.I)), 8)
        toc = re.sub(r'\s+', ' ', ' '.join(s.split('>>>', 1)[1] for s in sidor[:toc_slut]))
        möten = list(rMöte.finditer(toc))
        for k, m in enumerate(möten):
            del_ = toc[m.start(): möten[k + 1].start() if k + 1 < len(möten) else len(toc)]
            # Bertil Ohlin, inte Nils/Lars Wohlin eller Göran Ohlin
            if not any(not re.search(r'[gc]oran\W*$', fold(del_)[max(0, m2.start() - 8):m2.start()])
                       for m2 in re.finditer(r'\bohlin', fold(del_))):
                continue
            mån = månad(m.group(2))
            ämne = re.search(r'[ÖO]\S*gg\S*\s*:\s*(.+?)\.\s*(?:In\S*d|Anf|F\w*redrag|Panel|$)', del_, re.I)
            inl = re.search(r'Inled\w*(?:\s*f\w*redrag)?\s*(?:av)?(.{0,160}?)(?:\.\s*\.|\d{1,3}\s|Anf)', del_, re.I)
            inledare = inl.group(1).strip(' .·') if inl else ''
            roll = 'inledare' if re.search(r'\bohlin', fold(inledare)) and not re.search(r'[gc]oran', fold(inledare)) else 'talare'
            ut.append({'år': år, 'datum': f'{år}-{mån:02d}-{int(m.group(1)):02d}' if mån else str(år),
                       'ämne': re.sub(r'\s+', ' ', ämne.group(1).replace('- ', '')).strip(' »«>Y').capitalize() if ämne else del_[:160],
                       'roll': roll, 'inledare': inledare[:160], 'toc': del_[:900], 'fil': fn})
    for k in ut:
        if len(k['datum']) == 4:
            for (år, ord_), d in ODATERAT.items():
                if k['år'] == år and ord_ in fold(k['ämne']):
                    k['datum'] = d
        k['ämne'] = RÄTTAT.get(k['datum'], k['ämne'])
    return ut


def slug(s):
    s = fold(s)
    return re.sub(r'[^a-z0-9]+', '-', s)[:50].strip('-')


def sidkarta(sidor):
    """Tryckt sidnummer -> index i PDF:en, utifrån sidnumret överst på varje sida."""
    obs = {}
    for i, s in enumerate(sidor):
        kropp = s.split('>>>', 1)[1].strip().split('\n')[:3]
        for rad in kropp:
            m = re.fullmatch(r"\W*(\d{1,3})\W*", rad.strip())
            if m:
                obs[i] = int(m.group(1))
                break
    # förskjutningen (pdf-index minus tryckt nummer) som flest sidor är överens om, lokalt
    par = sorted(obs.items())
    def pdf(n):
        best = None
        for i, p in par:
            d = i - p
            if best is None or abs(p - n) < abs(best[1] - n):
                best = (d, p)
        return n + best[0] if best else n
    return pdf


def toc_sidor(toc_del):
    return sorted({int(x) for x in re.findall(r'\((\d{1,3})', toc_del)} |
                  {int(x) for x in re.findall(r'\.\s?(\d{1,3})\s', toc_del)})


def dela_ut(K):
    """Sparar texten för varje sammanträde med Ohlin som egen fil."""
    os.makedirs(UT, exist_ok=True)
    per_fil = {}
    for k in K:
        per_fil.setdefault(k['fil'], []).append(k)
    for fn, möten in per_fil.items():
        sidor = open(os.path.join(TXT, fn)).read().split('<<<SIDA ')[1:]
        pdf = sidkarta(sidor)
        for k in möten:
            nr = [n for n in toc_sidor(k['toc']) if n < 400]
            if not nr:
                k['sidor'] = None
                continue
            ohlin_nr = [int(x) for x in re.findall(r'Ohlin\s*\((\d{1,3})(?:[,\s]+(\d{1,3}))?', k['toc']) for x in x if x]
            a = pdf(min(nr))
            b = a + min(60, (max(nr) - min(nr)) + 4)   # sidantalet enligt innehållsförteckningen
            a, b = max(0, a - 1), min(len(sidor), b)
            text = '\n'.join(s.split('>>>', 1)[1] for s in sidor[a:b])
            k['sidor'] = [a + 1, b]
            k['ohlin_sidor_tryckt'] = ohlin_nr
            namn = f"{k['datum']}_{slug(k['ämne'])}.txt"
            k['textfil'] = 'nef/' + namn
            open(os.path.join(UT, namn), 'w').write(
                f"Nationalekonomiska föreningens förhandlingar {k['år']}, sammanträdet {k['datum']}\n"
                f"Ämne: {k['ämne']}\nOhlins roll: {k['roll']}"
                f"{'; Ohlin talar på tryckta s. ' + ', '.join(map(str, ohlin_nr)) if ohlin_nr else ''}\n"
                f"PDF-sidor {a + 1}–{b} i https://www.nationalekonomi.se/wp-content/uploads/2020/09/{fn[:-4]}.pdf\n"
                f"(OCR-text, oredigerad; kan börja eller sluta med en bit av angränsande sammanträde)\n\n{text}")


if __name__ == '__main__':
    K = katalog()
    dela_ut(K)
    json.dump(K, open(os.path.join(HÄR, 'nef_katalog.json'), 'w'), ensure_ascii=False, indent=1)
    for k in K:
        print(k['datum'], k['roll'][:4], '|', k['ämne'][:80])
    print(len(K), 'sammanträden,', sum(k['roll'] == 'inledare' for k in K), 'som inledare')
