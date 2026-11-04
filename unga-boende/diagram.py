import json,csv,sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
S=sys.argv[1]; OUT=sys.argv[2]
def load(f):
    d=json.load(open(f));ids=d['id'];sz=d['size']
    cats=[sorted(d['dimension'][i]['category']['index'].items(),key=lambda x:x[1]) for i in ids]
    out={}
    for k,v in d['value'].items():
        k=int(k);idx=[]
        for s in reversed(sz): idx.append(k%s);k//=s
        idx=idx[::-1];key={ids[j]:cats[j][idx[j]][0] for j in range(len(ids))}
        out.setdefault(key['geo'],{})[int(key['time'])]=v
    return out
E={'Medelålder när man flyttar hemifrån':load(f'{S}/dl/age.json'),
   'Andel 25–29 år som bor hos föräldrar, %':load(f'{S}/dl/ilc_lvps08_sex_T_age_Y25-29.json'),
   'Andel 18–34 år som bor hos föräldrar, %':load(f'{S}/dl/ilc_lvps08_sex_T_age_Y18-34.json'),
   'Boendekostnad >40 % av inkomst, 25–29 år, %':load(f'{S}/dl/ilc_lvho07a_sex_T_age_Y25-29_rskpovth_TOTAL.json'),
   'Trångboddhet, 25–29 år, %':load(f'{S}/dl/ilc_lvho05a_sex_T_age_Y25-29_rskpovth_TOTAL.json')}
geos=['SE','DK','FI','DE','NL','FR','ES','IT','PL','EU27_2020']
r={tuple(k.split('|')):v for k,v in json.load(open(f'{S}/scb_barn.json')).items()}
sh=lambda reg,y,lo,hi: sum(r[(reg,str(y),str(a))][0] for a in range(lo,hi+1))/sum(r[(reg,str(y),str(a))][1] for a in range(lo,hi+1))*100
regn={'00':'Riket','01':'Stockholms län','12':'Skåne län','14':'Västra Götalands län'}
with open(f'{OUT}/eurostat.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['indikator','land','år','värde'])
    for n,dd in E.items():
        for g in geos:
            for y,v in sorted(dd.get(g,{}).items()): w.writerow([n,g,y,v])
with open(f'{OUT}/scb_hemmaboende_per_alder.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['region','år','ålder','bor_hos_foraldrar','totalt','andel_%'])
    for (reg,y,a),(b,t) in sorted(r.items()): w.writerow([regn[reg],y,a,b,t,round(b/t*100,2)])
# chart
C=['#2a78d6','#eb6834','#1baf7a','#eda100']; ink='#0b0b0b'; mut='#52514e'
plt.rcParams.update({'font.size':10,'axes.edgecolor':'#c9c8c3','axes.labelcolor':mut,'xtick.color':mut,'ytick.color':mut,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':'#ecebe7','grid.linewidth':0.8})
fig,ax=plt.subplots(2,2,figsize=(12,8.5),facecolor='#fcfcfb')
for a in ax.flat: a.set_facecolor('#fcfcfb')
yrs=range(2011,2026)
a=ax[0,0]
for i,(lo,hi,lab) in enumerate([(25,29,'25–29 år'),(28,30,'28–30 år'),(30,35,'30–35 år')]):
    for reg,ls in [('00','-'),('01','--')]:
        a.plot(yrs,[sh(reg,y,lo,hi) for y in yrs],ls,color=C[i],lw=2,label=f'{lab}, {regn[reg]}')
a.set_title('Sverige (SCB-register): andel folkbokförda hos föräldrar',loc='left',color=ink,fontsize=11)
a.legend(fontsize=8,frameon=False,ncol=2); a.set_ylabel('%')
a=ax[0,1]
for i,(reg) in enumerate(['00','01']):
    for y,al in [(2011,0.45),(2025,1)]:
        a.plot(range(18,36),[r[(reg,str(y),str(x))][0]/r[(reg,str(y),str(x))][1]*100 for x in range(18,36)],color=C[i],lw=2,alpha=al,label=f'{regn[reg]} {y}')
a.set_title('Andel hos föräldrar per ålder, 2011 vs 2025',loc='left',color=ink,fontsize=11)
a.set_xlabel('ålder'); a.set_ylabel('%'); a.legend(fontsize=8,frameon=False)
a.set_xlim(24,35); a.set_ylim(0,30)
a=ax[1,0]; d=E['Andel 25–29 år som bor hos föräldrar, %']
for i,g in enumerate(['SE','DK','FI','NL']):
    yy=sorted(d[g]); a.plot(yy,[d[g][y] for y in yy],color=C[i],lw=2,label=g)
a.set_title('Eurostat EU-SILC: andel 25–29 år hos föräldrar, Norden + NL',loc='left',color=ink,fontsize=11)
a.legend(fontsize=8,frameon=False); a.set_ylabel('%')
a=ax[1,1]; d=E['Medelålder när man flyttar hemifrån']
for i,g in enumerate(['SE','EU27_2020','ES','IT'][:4]):
    yy=sorted(d[g]); a.plot(yy,[d[g][y] for y in yy],color=C[i],lw=2,label=g.replace('EU27_2020','EU27'))
a.set_title('Eurostat: uppskattad medelålder vid utflytt',loc='left',color=ink,fontsize=11)
a.axvline(2020.5,color=mut,lw=0.8,ls=':'); a.text(2020.7,19,'SE metodbyte\n2021',fontsize=7.5,color=mut)
a.legend(fontsize=8,frameon=False); a.set_ylabel('år')
fig.text(0.01,0.005,'Källor: SCB TAB4364/TAB6689 (registerbaserad hushållsstatistik, hushållsställning "barn"), Eurostat yth_demo_030, ilc_lvps08. Register mäter folkbokföring, inte faktiskt boende.',fontsize=7.5,color=mut)
fig.tight_layout(rect=(0,0.02,1,1)); fig.savefig(f'{OUT}/unga_boende.png',dpi=150)
