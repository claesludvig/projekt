import json,urllib.request,sys,itertools
ages=[str(a) for a in range(18,36)]
def get(tab,region,hs,tid,kon):
    cc={"TAB4364":"0000001D","TAB6689":"000008AI"}[tab]
    body={"selection":[{"variableCode":"Region","valueCodes":[region]},{"variableCode":"Hushallsstallning","valueCodes":hs},
     {"variableCode":"Alder","valueCodes":ages},{"variableCode":"Kon","valueCodes":kon},{"variableCode":"Tid","valueCodes":tid},{"variableCode":"ContentsCode","valueCodes":[cc]}]}
    req=urllib.request.Request(f"https://api.scb.se/OV0104/v2beta/api/v2/tables/{tab}/data?lang=sv&outputFormat=json-stat2",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    d=json.load(urllib.request.urlopen(req))
    ids=d['id'];sz=d['size'];cats=[list(d['dimension'][i]['category']['index']) for i in ids]
    out={}
    for n,combo in enumerate(itertools.product(*cats)):
        v=d['value'][n]
        key=dict(zip(ids,combo));out[(key['Hushallsstallning'],key['Alder'],key['Tid'],key['Kon'])]=v or 0
    return out
allhs=['ABarn','aensf','Aensm','Asamm','Agift','Abild','Aovri']
res={}
for region in ['00','01','12','14']:
    a=get('TAB4364',region,allhs,[str(y) for y in range(2011,2025)],['1','2'])
    b=get('TAB6689',region,allhs,['2025'],['1','2'])
    a.update(b)
    for y in range(2011,2026):
        for ag in ages:
            barn=sum(a[('ABarn',ag,str(y),k)] for k in '12'); tot=sum(a[(h,ag,str(y),k)] for h in allhs for k in '12')
            res[(region,y,ag)]=(barn,tot)
json.dump({f"{k[0]}|{k[1]}|{k[2]}":v for k,v in res.items()},open('scb_barn.json','w'))
for region in ['00','01']:
    print('Region',region)
    print('year  '+' '.join(f"{a:>5}" for a in ages)+'  20-27  25-29 medianLeave')
    for y in range(2011,2026):
        r=[res[(region,y,a)] for a in ages]
        sh=[b/t*100 for b,t in r]
        g=lambda lo,hi: sum(res[(region,y,str(x))][0] for x in range(lo,hi+1))/sum(res[(region,y,str(x))][1] for x in range(lo,hi+1))*100
        med=next((int(a)+0 for a,s in zip(ages,sh) if s<50),None)
        print(y,' '.join(f"{s:5.1f}" for s in sh),f"{g(20,27):6.1f} {g(25,29):6.1f}",med)
