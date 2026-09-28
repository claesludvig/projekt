"""Hämtar källmaterial om och av Bertil Ohlin som inte är riksdagens protokoll.

    python3 hamta.py partiprogram   # folkpartiets program och valmanifest 1934–1970 (SND)
    python3 hamta.py nef            # Nationalekonomiska föreningens förhandlingar 1925–1972
    python3 hamta.py texter         # SOU 1934:12 och rapporten till Nationernas förbund 1931
    python3 hamta_motioner.py       # riksdagsmotioner som Ohlin skrivit under
    python3 nef_katalog.py          # sammanträden där Ohlin talade, utskurna till nef/

Stora PDF:er och råtext hamnar i kallor/ (ignoreras av git).
"""
import html, os, re, sys, urllib.request

HÄR = os.path.dirname(os.path.abspath(__file__))
KÄLLOR = os.path.join(HÄR, 'kallor')


def get(url, fil):
    if os.path.exists(fil) and os.path.getsize(fil):
        return
    os.makedirs(os.path.dirname(fil), exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(fil, 'wb') as f:
        f.write(r.read())


PARTIPROGRAM = ['p/1934', 'p/1944', 'p/1962'] + [f'v/{å}' for å in
                (1936, 1940, 1944, 1948, 1952, 1956, 1958, 1960, 1964, 1968, 1970)]


def partiprogram():
    for k in PARTIPROGRAM:
        namn = 'fp_' + k.replace('/', '_')
        for fmt in ('txt', 'pdf'):
            get(f'https://snd.se/sv/vivill/file/fp/{k}/{fmt}', os.path.join(HÄR, 'partiprogram', f'{namn}.{fmt}'))


def nef():
    import pymupdf  # pip install pymupdf
    for år in range(1925, 1973):
        pdf = os.path.join(KÄLLOR, 'nef', 'pdf', f'nf-{år}.pdf')
        get(f'https://www.nationalekonomi.se/wp-content/uploads/2020/09/nf-{år}.pdf', pdf)
        txt = os.path.join(KÄLLOR, 'nef', 'txt', f'nf-{år}.txt')
        if not os.path.exists(txt):
            os.makedirs(os.path.dirname(txt), exist_ok=True)
            d = pymupdf.open(pdf)
            open(txt, 'w').write(''.join(f'\n<<<SIDA {i + 1}>>>\n' + p.get_text() for i, p in enumerate(d)))


def texter():
    ut = os.path.join(HÄR, 'texter')
    os.makedirs(ut, exist_ok=True)
    get('https://weburn.kb.se/sou/204/urn-nbn-se-kb-digark-2039038.pdf', os.path.join(KÄLLOR, 'sou', 'SOU_1934_12.pdf'))
    sida = urllib.request.urlopen('https://lagen.nu/sou/1934:12', timeout=300).read().decode('utf-8')
    t = re.sub(r'(?s)<script.*?</script>|<style.*?</style>|<nav.*?</nav>', '', sida)
    t = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'</(p|div|h\d|li|tr)>', '\n', t)))
    t = re.sub(r'\n\s*\n+', '\n\n', re.sub(r'[ \t]+', ' ', t))
    open(os.path.join(ut, 'SOU_1934_12_Ohlin_penningpolitik.txt'), 'w').write(
        'Bertil Ohlin: Penningpolitik, offentliga arbeten, subventioner och tullar som medel mot arbetslöshet. '
        'Bidrag till expansionens teori.\nSOU 1934:12 (Arbetslöshetsutredningens betänkande II, bilagor, band 4). '
        'Text från lagen.nu (OCR), original: https://weburn.kb.se/sou/204/urn-nbn-se-kb-digark-2039038.pdf\n\n'
        + t[t.find('SOU 1934:12'):])
    lon = urllib.request.urlopen('https://archive.org/download/TheCauseAndPhasesOfTheWorldEconomicDepression/'
                                 'Ohlin1931-TheCauseAndPhasesOfTheWorldEconomicDepression_djvu.txt', timeout=300)
    open(os.path.join(ut, 'Nationernas_forbund_1931_Ohlin_world_economic_depression.txt'), 'w').write(
        'Bertil Ohlin: The Course and Phases of the World Economic Depression. Report presented to the Assembly of '
        'the League of Nations. Genève: League of Nations, 1931.\nText: Internet Archive (OCR), '
        'https://archive.org/details/TheCauseAndPhasesOfTheWorldEconomicDepression\n\n' + lon.read().decode('utf-8'))


if __name__ == '__main__':
    for steg in sys.argv[1:] or ['partiprogram', 'nef', 'texter']:
        globals()[steg]()
