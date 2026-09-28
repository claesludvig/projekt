"""Plockar ut Bertil Ohlins egna inlägg ur de hämtade kammarprotokollen.

Ett inlägg börjar på en rad som inleds med talarangivelsen "Herr OHLIN (fp):", "Herr Ohlin:"
e.d. och slutar när nästa talare får ordet, ett nytt § börjar eller överläggningen avslutas.
Texten är riksdagens OCR-tolkning av de tryckta protokollen och innehåller läsfel.
Resultat: data/inlagg.json (med fulltext) och data/inlagg.csv (utan fulltext).
"""
import re,json,os,csv
from concurrent.futures import ProcessPoolExecutor
HÄR=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HÄR,'data'); CLEAN=os.path.join(DATA,'kallor','clean')
L={x['dok_id']:x for x in json.load(open(os.path.join(DATA,'protokoll.json')))}
DAYS=r'(?:Måndagen|Tisdagen|Onsdagen|Torsdagen|Fredagen|Lördagen|Söndagen)'
MON='januari februari mars april maj juni juli augusti september oktober november december'.split()
rDate=re.compile(DAYS+r' den (\d{1,2}) ('+'|'.join(MON)+r') (\d{4})')
rFurn=re.compile(r'^(?:\d+|Nr \d+\.?|(?:Första|Andra) kammarens protokoll.*|'+DAYS+r' den \d.*\d{4}.{0,12})$')
TITLES=r'(?:Herr|Hans excellens|Chefen för \w+,? (?:herr|lierr|hem) statsrådet|Fru|Fröken|Hans excellens|Hennes excellens|Statsrådet|Talmannen|Herr talmannen|Förste vice talmannen|Andre vice talmannen|Tredje vice talmannen|Chefen för)'
rSpk=re.compile(r'^'+TITLES+r'\s[^:.!?]{0,130}?(?::|yttrade:|anförde:)')
rForts=re.compile(r'\((?:F|f)orts\.?\)\.?$')
rOhlin=re.compile(r'^Herr (?:OHLIN|Ohlin)\b')
rSec=re.compile(r'^§ ?(\d+)\.?$')
rPunkt=re.compile(r'^Punkt(?:en|erna) [\d—–-]+')
rEnd=re.compile(r'^(?:§ ?\d+\.?$|Överläggningen (?:var|förklarades)|Efter slutad överläggning|Punkt(?:en|erna) [\d—–-]+\.?$|Propositioner? (?:gavs|gåvos|framställdes)|Vad utskottet (?:i punkten )?hemställt bifölls|Kammaren (?:biföll|beslöt))')
def join(ls):
    s=''
    for l in ls:
        if s.endswith('-') and l[:1].islower(): s=s[:-1]+l
        else: s=(s+' '+l) if s else l
    return re.sub(r'\s+',' ',s).strip()
def proc(fn):
    did=fn[:-4]; meta=L[did]
    raw=[l.strip() for l in open(os.path.join(CLEAN,fn)).read().split('\n')]
    raw=[l for l in raw if l]
    # skip header/css: start at first line that looks like body (after 'div.sida' css block ends)
    hdr_date=next((l for l in raw[:20] if re.match(r'^\d{4}-\d\d-\d\d',l)),'')[:10]
    date=None; sec='';sect=[];punkt='';out=[];cur=None
    i=0
    while i<len(raw):
        l=raw[i]
        m=rDate.search(l)
        if m and rFurn.match(l):
            date=f"{m.group(3)}-{MON.index(m.group(2))+1:02d}-{int(m.group(1)):02d}"; i+=1; continue
        if rFurn.match(l) or rForts.search(l): i+=1; continue
        l3=join(raw[i:i+3])
        if cur is not None and (rSpk.match(l3) or rEnd.match(l)) and len(cur['lines'])>1:
            out.append(cur); cur=None
        if rSec.match(l):
            sec=l; sect=raw[i+1:i+4]; punkt=''
        elif rPunkt.match(l):
            punkt=join(raw[i:i+2])
        if cur is None and rSpk.match(l3) and rOhlin.match(l):
            cur={'lines':[l],'date':date or hdr_date,'sec':sec,'topic':join(sect),'punkt':punkt}
        elif cur is not None:
            cur['lines'].append(l)
            if len(cur['lines'])>3000: out.append(cur); cur=None
        i+=1
    if cur: out.append(cur)
    y=int(meta['rm'][:4])
    res=[]
    for k,c in enumerate(out):
        t=join(c['lines']); head=t[:120]
        typ='kort genmäle' if re.search(r'genmäle|replik',head[:60],re.I) else 'anförande'
        res.append({'dok_id':did,'n':k+1,'rm':meta['rm'],'kammare':meta['undertitel'],'datum':(c['date'] if c['date'] and abs(int(c['date'][:4])-y)<=1 else hdr_date),'paragraf':c['sec'],
            'arende':c['topic'][:300],'punkt':c['punkt'][:200],'typ':typ,'ord':len(t.split()),'text':t,
            'url':f"https://data.riksdagen.se/dokument/{did}.html"})
    return res
TEMAN={
 'Ekonomisk politik':r'inflation|penningvärde|prisstegring|konjunktur|sysselsättning|arbetslöshet|räntepolitik|kreditpolitik|finanspolitik|budgetpolitik|överbalanser',
 'Skatter':r'skatt|beskattning',
 'Bostäder':r'bostad|bostäder|hyresreglering|hyror|egnahem',
 'Pensioner och ATP':r'pension|\batp\b|tjänstepension',
 'Socialpolitik':r'socialförsäkring|sjukförsäkring|barnbidrag|socialpolitik|socialvård|folkpension',
 'Arbetsmarknad och löner':r'arbetsmarknad|lönepolitik|löneökning|fackförening|landsorganisation|strejk',
 'Jordbruk':r'jordbruk|jordbrukar|bönder|lantbruk',
 'Handel och näringsliv':r'tullar|frihandel|näringsliv|företagare|företagsamhet|handelspolitik|export',
 'Europa och internationellt':r'förenta nationerna|europeisk|europarådet|efta|sexstat|marshall|internationell',
 'Utrikespolitik och neutralitet':r'utrikespolitik|neutralitet|alliansfri|atlantpakt|nato|stormakt',
 'Försvar':r'försvar|krigsmakt|flygvapn|beredskap',
 'Utbildning och forskning':r'skola|skolväsen|universitet|utbildning|forskning|gymnasi',
 'Författning och demokrati':r'författning|grundlag|tvåkammar|enkammar|valsystem|valsätt|demokrati|tryckfrihet',
 'Regeringsfrågan':r'samlingsregering|koalition|regeringsfråga|regeringsskifte|regeringsbildning|borgerlig samverkan',
}
TEMAN_RE={k:re.compile(v,re.I) for k,v in TEMAN.items()}
def teman(t):
    n=len(t.split())
    return [k for k,r in TEMAN_RE.items() if len(r.findall(t))>=max(2,n//700)]

if __name__=='__main__':
    with ProcessPoolExecutor() as ex: R=[r for rs in ex.map(proc,sorted(os.listdir(CLEAN))) for r in rs]
    R.sort(key=lambda r:(r['datum'] or '',r['dok_id'],r['n']))
    for i,r in enumerate(R):
        r['id']=i+1; r['teman']=teman(r['text'])
    json.dump(R,open(os.path.join(DATA,'inlagg.json'),'w'),ensure_ascii=False)
    kol=['id','datum','kammare','rm','dok_id','typ','ord','teman','arende','punkt','url','inledning']
    with open(os.path.join(DATA,'inlagg.csv'),'w',newline='') as f:
        w=csv.DictWriter(f,kol); w.writeheader()
        for r in R: w.writerow({**{k:r.get(k) for k in kol},'teman':'; '.join(r['teman']),'inledning':' '.join(r['text'].split()[:60])})
    import collections
    print(len(R),'inlägg,',sum(r['ord'] for r in R),'ord')
    print(collections.Counter(r['typ'] for r in R))
    print(collections.Counter(t for r in R for t in r['teman']).most_common())
