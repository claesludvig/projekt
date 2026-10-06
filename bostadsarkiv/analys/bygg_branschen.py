#!/usr/bin/env python3
"""Bygger sidan Branschen och bostadsfinansieringen (branschen.html).

Citaten hämtas ordagrant ur sökdatabasen (data/bostadsarkiv.sqlite) med
beteckning och ett utmärkande textfragment. Uppenbara OCR-fel rättas med en
uttrycklig lista per citat; källtexten visas då under "OCR-text i källan".

    python analys/bygg_branschen.py
"""

import html
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import text  # noqa: E402

DB = BASE / "data" / "bostadsarkiv.sqlite"
UT = Path(__file__).resolve().parent / "branschen.html"
ARKIVET = "https://claude.ai/artifact/1RQ8ZiGEsz91fNeQ8KT4wc"


def hamta(db, bet, frag, slut=None):
    """Stycket i dokumentet som innehåller frag; valfritt kapat efter slut."""
    for did, url, x in db.execute(
            "SELECT d.id, d.url, v.text FROM avsnitt v JOIN dokument d ON d.id = v.dok_id "
            "WHERE d.beteckning = ? ORDER BY v.nr", (bet,)):
        for st in text.sy_ihop_rader(x).split("\n\n"):
            s = re.sub(r"\s+", " ", st.replace("\xad", "")).strip()
            i = s.lower().find(frag.lower())
            if i >= 0:
                if slut:
                    j = s.find(slut, i)
                    s = s[:j + len(slut)] if j >= 0 else s
                return did, url, s
    raise SystemExit(f"Hittar inte {frag!r} i {bet}")


def lank(did, url):
    if did.startswith("KB-"):
        return url
    return f"https://data.riksdagen.se/dokument/{did}.html"


class Citat:
    def __init__(self, bet, fran, slut=None, ratt=(), datum="", aktor="", skurna=0):
        self.bet, self.fran, self.slut, self.ratt = bet, fran, slut, ratt
        self.datum, self.aktor, self.skurna = datum, aktor, skurna

    def html(self, db):
        did, url, s = hamta(db, self.bet, self.fran, self.slut)
        i = s.lower().find(self.fran.lower())
        kall = s[i:]
        ren = kall
        for a, b in self.ratt:
            if a not in ren:
                raise SystemExit(f"Rättelsen {a!r} finns inte i citatet ur {self.bet}")
            ren = ren.replace(a, b)
        ocr = (f'<details><summary>OCR-text i källan</summary><p>{html.escape(kall)}</p></details>'
               if ren != kall else "")
        return (f'<figure class="q"><blockquote>{html.escape(ren)}</blockquote>'
                f'<figcaption><span>{html.escape(self.aktor)}</span><span>{html.escape(self.bet)}'
                f'{" · " + html.escape(self.datum) if self.datum else ""}</span>'
                f'<a href="{lank(did, url)}" target="_blank" rel="noopener">Källan</a>{ocr}</figcaption></figure>')


# --- Innehåll -------------------------------------------------------------------
# Varje avsnitt: rubrik, id, inledning och en följd av stycken (str) och citat.

AVSNITT = [
    ("tidigt", "Systemet byggs upp, 1945–1960", "Kapitlets avsnitt 5", [
        "Redan när efterkrigssystemet sattes upp tog näringslivets organisationer ställning mot "
        "räntesänkningar. När regeringen 1946 föreslog att räntan på tertiär- och "
        "sekundärlånen i vissa fall skulle sänkas, avvisades det av bland andra Riksbankens fullmäktige, "
        "1945 års bankkommitté, Sparbanksföreningen och Näringslivets bostadsbyggnadsdelegation.",
        Citat("Prop. 1946:279", "Vidkommande först frågan", datum="1946",
              aktor="Remissredovisning", ratt=[("frågan örn", "frågan om"), ("sekund är lån", "sekundärlån")]),
        "Näringslivets bostadsdelegation var enligt en senare utredning tillsatt av bankerna, "
        "industrin, fastighetsägarna, arbetsgivarna och försäkringsbolagen. Den varnade för att det "
        "stora bostadsprogrammet skulle tränga undan industrins investeringar.",
        Citat("SOU 1947:41", "Bland remissinstanserna hade faran", slut="riksförbund).", datum="1947",
              aktor="Näringslivets bostadsdelegation, återgivet i SOU"),
        "Fastighetsägareförbundet var i början inte emot statens stöd i sig. År 1947 avrådde det från "
        "att döma ut stödåtgärderna innan de hunnit verka.",
        Citat("Prop. 1947:235", "Sveriges fastighetsägareförbund anser, att de hittills", datum="1947",
              aktor="Sveriges fastighetsägareförbund"),
        "Från början av 1950-talet ändrades tonen. Förbundet tillstyrkte att tilläggslånen avvecklades "
        "och hyrorna i nya hus fick stiga, och det menade att subventionerna själva bidragit till "
        "bostadsbristen. Byggnadsindustriförbundets intressekontor drog samma slutsats: vägen ur "
        "bostadskrisen gick över efterfrågesidan, inte genom mer stöd.",
        Citat("Prop. 1951:124", "En avveckling av tilläggslånen", datum="1951",
              aktor="Remissredovisning"),
        Citat("Prop. 1951:217", "Av de remissmyndigheter", slut="anledning till bostadsbristen.", datum="1951",
              aktor="Sveriges fastighetsägareförbund"),
        Citat("Prop. 1951:217", "Ihjggförbundets intressekontor", datum="1951",
              aktor="Byggförbundets intressekontor (Svenska byggnadsindustriförbundet)",
              ratt=[("Ihjggförbundets", "Byggförbundets")]),
        "Linjen var principiellt avvecklande men pragmatisk i takten. År 1953 ville förbundet att de "
        "generella subventionerna skulle bort, men gick med på en kort övergång för att nyproduktionen "
        "inte skulle falla.",
        Citat("Prop. 1953:138", "Ehuru Sveriges fastighetsägareförbund", datum="1953",
              aktor="Sveriges fastighetsägareförbund"),
        "Hyresregleringen var i deras ögon kärnan i problemet. Byggentreprenörerna och "
        "byggnadsindustrin sade 1956 att en skälig hyra inte längre gick att bedöma efter tretton års "
        "reglering, och Fastighetsägareförbundet kallade regleringen den primära orsaken till "
        "bostadsbristen.",
        Citat("Prop. 1956:168", "Sålunda anför svenska byggnadsentreprenörföreningen", datum="1956",
              aktor="Svenska byggnadsentreprenörföreningen och Svenska byggnadsindustriförbundet"),
        Citat("Prop. 1956:168", "Sveriges fastighetsägareförbund gör gällande", slut="bostadsmarknaden,",
              datum="1956", aktor="Sveriges fastighetsägareförbund"),
        "Det tydligaste programmet kom i remissvaren över bostadsbyggnadsutredningen 1957. Näringslivets "
        "byggnadsdelegation ville avveckla de generella subventionerna snabbare än utredningen, sätta "
        "räntan efter marknaden, pröva räntegarantin på nytt och ge enskilda byggherrar samma "
        "belåningsgränser som allmännyttiga och kooperativa företag. Byggnadsentreprenörföreningen "
        "lade till att den enskilda sektorn behövde mer kapital.",
        Citat("Prop. 1957:100", "Utöver vad utredningen anfört om de generella", datum="1957",
              aktor="Näringslivets byggnadsdelegation"),
        Citat("Prop. 1957:100", "Näringslivets byggnadsdelegation, som funnit", datum="1957",
              aktor="Näringslivets byggnadsdelegation"),
        Citat("Prop. 1957:100", "Näringslivets byggnadsdelegation anser, att 67", slut="öppna marknaden.",
              datum="1957", aktor="Näringslivets byggnadsdelegation",
              ratt=[("anser, att 67 Kungl. Maj.ts proposition nr 100 är 1957 den", "anser, att den")]),
        Citat("Prop. 1957:100", "Den nu tillämpade differentieringen", slut="för alla företagsformer.",
              datum="1957", aktor="Näringslivets byggnadsdelegation", ratt=[("villighet alt", "villighet att")]),
        Citat("Prop. 1957:100", "Byggnadsentreprenörföreningen, som i övrigt", slut="enskilda företag.",
              datum="1957", aktor="Svenska byggnadsentreprenörföreningen"),
        "Samma hållning syns när den garanterade räntan skulle höjas 1960: både Fastighetsägareförbundet "
        "och Byggnadsentreprenörföreningen tillstyrkte.",
        Citat("Prop. 1960:1", "I tillstyrkande riktning uttalar", slut="centralorganisation (SACO).",
              datum="1960", aktor="Remissredovisning"),
    ]),
    ("placering", "Placeringsplikt och miljonprogram, 1960–1975", "Kapitlets avsnitt 6", [
        "Placeringskvoterna 1962 delade remissinstanserna efter intresse snarare än efter höger och "
        "vänster. HSB, Riksbyggen, SABO och LO tillstyrkte. Bankerna, försäkringsbolagen och "
        "Industriförbundet avstyrkte.",
        Citat("Prop. 1962:52", "Förslaget om placeringskvoter tillstyrkes", slut="bostadsföretag.",
              datum="1962", aktor="Remissredovisning"),
        Citat("Prop. 1962:52", "Lagstiftning om placeringskvoter avstyrkes", datum="1962",
              aktor="Remissredovisning"),
        "Byggföretagen och fastighetsägarna stod inte på någon av listorna. Däremot ville de att "
        "prioriteringen skulle gälla mer, inte mindre: även ombyggnad, sanering och underhåll av äldre "
        "bostadshus borde få prioriterad kredit. Där kreditstyrningen gynnade deras egen verksamhet "
        "invände de alltså inte mot den.",
        Citat("Prop. 1962:52", "Övriga remissinstanser som yttrat sig på ifrågavarande punkt", datum="1962",
              aktor="Remissredovisning",
              ratt=[("En sådan äi ombyggnad", "En sådan är ombyggnad"),
                    ("byggnadsentreprenadföreningen", "byggnadsentreprenörföreningen")]),
        "Kritiken riktades i stället mot lånesystemets konstruktion. När paritetslånen föreslogs 1967, "
        "med låga betalningar i början och stigande skuld, avstyrkte Byggnadsentreprenörföreningen. "
        "Föreningen menade att bara samhällsägda företag kunde bära ett sådant system.",
        Citat("Prop. 1967:100", "SBEF anser att den föreslagna finansieringsmetoden", datum="1967",
              aktor="Svenska byggnadsentreprenörföreningen (SBEF)"),
        "Näringslivets byggnadsdelegation begärde 1970 att paritetslånen skulle avvecklas, bland annat "
        "för att systemet var känsligt för hög ränta och drev på byggkostnaderna. Två år tidigare hade "
        "delegationen sammanfattat sin syn på bostadsbristen i en mening.",
        Citat("Prop. 1968:91", "Näringslivets byggnadsdelegation uttalar", datum="1968",
              aktor="Näringslivets byggnadsdelegation"),
        Citat("Prop. 1970:1", "Näringslivets byggnadsdelegation har gjort framställning", datum="1970",
              aktor="Näringslivets byggnadsdelegation, återgivet av departementschefen",
              ratt=[]),
        "Inför riktlinjebeslutet 1974 riktade delegationen in sig på standarden: om nyproduktionen "
        "byggdes så att de flesta inte kunde betala utan generell subvention, skulle subventionen bli "
        "permanent.",
        Citat("Prop. 1974:150", "NBD anser alt den målsättning", datum="1974",
              aktor="Näringslivets byggnadsdelegation (NBD)",
              ratt=[("anser alt", "anser att"), ("menar all det", "menar att det"),
                    ("försvariigt", "försvarligt"), ("höga, alt fierialet", "höga, att flertalet"),
                    ("belala", "betala"), ("bosläder ulan", "bostäder utan"),
                    ("all bli", "att bli"), ("beträlTande", "beträffande")]),
        "Den kreditpolitiska lagen samma år, som gjorde placeringsplikten och de andra instrumenten "
        "permanenta, mötte motstånd från kreditinstituten och från delegationen. Delegationens "
        "invändning var konstitutionell: regeringen och Riksbanken fick befogenheter utan att villkoren "
        "stod i lagen.",
        Citat("Prop. 1974:168", "Näringslivets byggnadsdelegation menar att principen",
              slut="regeringsformen.", datum="1974", aktor="Näringslivets byggnadsdelegation",
              ratt=[("utomordentiiga", "utomordentliga"), ("tiU samhäUsorgan", "till samhällsorgan"),
                    ("stämraer", "stämmer")]),
    ]),
    ("subvention", "Från kreditstyrning till subventioner, 1975–1985", "Kapitlets avsnitt 7", [
        "När räntebidragen blev det bärande stödet följde branschens organisationer samma linje som "
        "tidigare: stöd skulle vara tillfälligt och neutralt mellan ägarformer. Räntebidrag till "
        "underhåll avvisades av principskäl 1983, och 1985 kallade Byggnadsdelegationen sig principiell "
        "motståndare till bidrag och subventioner, med krav på en ordnad avveckling.",
        Citat("Prop. 1983/84:40", "Fastighetsägareförbundet, Näringslivets byggnadsdelegalion", datum="1983",
              aktor="Remissredovisning",
              ratt=[("byggnadsdelegalion", "byggnadsdelegation"), ("räntebidrag lill", "räntebidrag till"), ("Fasiighetskredit", "Fastighetskredit")]),
        Citat("Prop. 1984/85:120", "Näringslivets byggnadsdelegation säger sig", slut="nya förhållandena.",
              datum="1985", aktor="Näringslivets byggnadsdelegation",
              ratt=[("atl leda", "att leda"), ("atl dessa", "att dessa"),
                    ("anpassa sig lill", "anpassa sig till")]),
        "Samtidigt stödde Fastighetsägareförbundet att statens lån ersattes av garantier på den vanliga "
        "kreditmarknaden, tillsammans med bankerna och försäkringsbolagen.",
        Citat("Prop. 1983/84:90", "Införande av etl garantilånesystem", datum="1983", aktor="Remissredovisning",
              ratt=[("etl", "ett"), ("Spinlab", "Spintab"), ("dessa", "dessa")]),
    ]),
    ("avreglering", "Avregleringen", "Kapitlets avsnitt 8", [
        "När staten 1989 ville ändra villkoren i redan ingångna låneavtal såg Fastighetsägareförbundet "
        "det som ett argument för att lägga hela bostadsfinansieringen på den allmänna kreditmarknaden.",
        Citat("Bet. 1988/89:BoU10", "Föreliggande förslag om ingrepp", datum="1989",
              aktor="Sveriges fastighetsägareförbund, remissyttrande i bilaga till betänkandet"),
        "I den stora omläggningen 1990 gick organisationerna isär i metod men inte i riktning. "
        "Byggnadsdelegationen avstyrkte ett nytt statligt system och ville ha en plan för avveckling. "
        "Fastighetsägareförbundet tillstyrkte en kraftig begränsning av räntebidragen men ville skilja "
        "lån och subventioner åt helt. Byggentreprenörerna kunde godta räntelån om staten garanterade "
        "att fastighetsvärdena räckte till den växande skulden.",
        Citat("Prop. 1990/91:34", "Byggnadsdelegationen avstyrker förslaget", datum="1990",
              aktor="Näringslivets byggnadsdelegation", ratt=[("nyaformer", "nya former"),
                                                               ("awecklingssplan", "avvecklingsplan")]),
        Citat("Prop. 1990/91:34", "Fastighetsägareförbundet tillstyrker huvuddragen", slut="kreditgaranti.",
              datum="1990", aktor="Sveriges fastighetsägareförbund"),
        Citat("Prop. 1990/91:34", "Byggentreprenörerna (Entreprenörföreningen) tillstyrker",
              slut="rimligt skydd.", datum="1990", aktor="Byggentreprenörerna"),
        "Ett yttrande från Fastighetsägareförbundet 1990 knyter tillbaka till kapitlets problem med "
        "räntans tidsprofil: vid hög inflation eller hög realränta måste kapitalkostnaderna kunna "
        "fördelas över tiden, annars faller byggandet. Det var samma problem som paritetslånen och "
        "räntebidragen en gång skulle lösa, nu med marknaden som lösning.",
        Citat("Prop. 1990/91:34", "Under perioder med hög inflation eller hög realränta är det enligt förbundet",
              slut="hållas uppe.", datum="1990", aktor="Sveriges fastighetsägareförbund"),
    ]),
]

SAMMANFATTNING = [
    ("Marknaden skulle bestämma.",
     "Från 1950-talet till 1990 är linjen densamma: generella subventioner och reglerade hyror skulle "
     "avvecklas, räntan och hyran sättas av marknaden. Det gäller Fastighetsägareförbundet, "
     "byggentreprenörerna och Näringslivets byggnadsdelegation."),
    ("Avveckling, men i takt med byggandet.",
     "Kraven på avveckling kom nästan alltid med en övergång. Ingen av organisationerna ville att "
     "nyproduktionen skulle falla, och 1953 accepterade Fastighetsägareförbundet fortsatta subventioner "
     "för en tid av just det skälet."),
    ("Lika villkor för enskilda.",
     "Ett genomgående krav var att enskilda byggherrar skulle få samma belåningsgränser och villkor som "
     "allmännyttiga och kooperativa företag. Skillnaden beskrevs 1957 som en diskriminering som höll "
     "privat kapital borta."),
    ("Kreditstyrningen var bankernas strid.",
     "Placeringskvoterna 1962 avstyrktes av bankerna, försäkringsbolagen och industrin, inte av "
     "byggföretagen och fastighetsägarna. De senare ville tvärtom att även ombyggnad och sanering skulle "
     "få prioriterad kredit."),
    ("Kritiken gällde lånens konstruktion.",
     "Paritetslånen 1967–1970 ansågs passa bara samhällsägda företag och vara sårbara för hög ränta. "
     "Byggentreprenörerna varnade för monopolisering."),
    ("1990 var målet nått, men inte problemet.",
     "Vid avregleringen tillstyrkte organisationerna att räntebidragen begränsades. Fastighetsägareförbundet "
     "påpekade samtidigt att kapitalkostnaderna vid hög inflation eller realränta måste kunna fördelas "
     "över tiden för att byggandet ska hållas uppe."),
]

CSS = """
:root{--ground:#F4F5F2;--surface:#FFFFFF;--ink:#1B2029;--muted:#5C6470;--rule:#D8DBD4;--accent:#23508F;
--doc:#6B5A2E;--serif:"Newsreader",Georgia,"Times New Roman",serif;--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--ground:#111418;--surface:#181C22;
--ink:#E4E6E9;--muted:#98A0AB;--rule:#2B3139;--accent:#8DB2EA;--doc:#D2BC86}}
:root[data-theme="dark"]{color-scheme:dark;--ground:#111418;--surface:#181C22;--ink:#E4E6E9;--muted:#98A0AB;--rule:#2B3139;
--accent:#8DB2EA;--doc:#D2BC86}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font:17.5px/1.62 var(--serif);padding-inline:16px;padding-block:36px 72px}
.wrap{max-width:1080px;margin:0 auto;display:grid;grid-template-columns:minmax(0,680px) 220px;gap:56px;justify-content:space-between}
@media (max-width:980px){.wrap{grid-template-columns:minmax(0,1fr)}nav.toc{display:none}}
main{display:flex;flex-direction:column;gap:44px;min-width:0}
header{display:flex;flex-direction:column;gap:12px}
.eyebrow{font:500 12px/1.4 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font:600 clamp(34px,5.4vw,52px)/1.05 var(--serif);margin:0;text-wrap:balance;letter-spacing:-.01em}
.lede{font-size:20px;line-height:1.5;margin:0}
.meta{font:14px/1.55 var(--sans);color:var(--muted);margin:0}
.meta a,footer a,nav.toc a,p a{color:var(--accent)}
h2{font:600 28px/1.2 var(--serif);margin:0 0 4px;text-wrap:balance}
.kap{font:500 12px/1.4 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--doc)}
section{display:flex;flex-direction:column;gap:16px;scroll-margin-top:20px}
section p{margin:0;max-width:66ch}
.summary{background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:22px 24px;display:flex;flex-direction:column;gap:12px}
.summary h2{font-size:22px}
.summary ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px}
.summary li{font-size:16.5px;line-height:1.55}
.summary li strong{font-family:var(--sans);font-size:15px;font-weight:600;margin-right:4px}
figure.q{margin:4px 0 6px;display:flex;flex-direction:column;gap:8px;padding-left:28px;position:relative;max-width:64ch}
figure.q::before{content:"»";position:absolute;left:0;top:-4px;font:600 30px/1 var(--serif);color:var(--accent)}
blockquote{margin:0;font:400 18px/1.55 var(--serif)}
figcaption{display:flex;flex-wrap:wrap;gap:4px 14px;font:13px/1.4 var(--sans);color:var(--muted);font-variant-numeric:tabular-nums}
figcaption a{color:var(--accent)}
details{flex-basis:100%;font:13px/1.5 var(--sans);color:var(--muted)}
details summary{cursor:pointer;color:var(--accent);width:max-content}
details p{margin:6px 0 0;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;overflow-wrap:anywhere}
dl.org{margin:0;display:grid;grid-template-columns:minmax(0,1fr);gap:10px;font-size:16px}
dl.org dt{font:600 15px/1.4 var(--sans)}
dl.org dd{margin:2px 0 0;line-height:1.5}
nav.toc{position:sticky;top:calc(env(safe-area-inset-top,0px) + 24px);align-self:start;display:flex;flex-direction:column;gap:8px;font:14px/1.4 var(--sans);padding-top:6px}
nav.toc span{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500;margin-bottom:4px}
nav.toc a{text-decoration:none}
nav.toc a:hover,nav.toc a:focus-visible{text-decoration:underline}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:2px}
footer{font:14px/1.6 var(--sans);color:var(--muted);border-top:1px solid var(--rule);padding-top:20px;display:flex;flex-direction:column;gap:8px;max-width:66ch}
"""


def main():
    db = sqlite3.connect(DB)
    n_citat = 0
    delar = []
    for sid, rubrik, kap, innehall in AVSNITT:
        kropp = []
        for x in innehall:
            if isinstance(x, Citat):
                kropp.append(x.html(db))
                n_citat += 1
            else:
                kropp.append(f"<p>{html.escape(x)}</p>")
        delar.append(f'<section id="{sid}"><span class="kap">{kap}</span><h2>{rubrik}</h2>{"".join(kropp)}</section>')
    summ = "".join(f"<li><strong>{html.escape(a)}</strong>{html.escape(b)}</li>" for a, b in SAMMANFATTNING)
    toc = "".join(f'<a href="#{sid}">{rubrik}</a>' for sid, rubrik, _, _ in AVSNITT)
    sida = f"""<meta charset="utf-8">
<title>Branschen och bostadsfinansieringen</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<style>{CSS}</style>
<div class="wrap"><main>
<header>
<span class="eyebrow">Remissvar i riksdagstrycket 1946–1990</span>
<h1>Branschen och bostadsfinansieringen</h1>
<p class="lede">Vad byggföretagen och fastighetsägarna tyckte om lånen, räntorna, regleringarna och subventionerna som styrde bostadsbyggandet efter kriget, i deras egna remissvar.</p>
<p class="meta">Källan är propositionernas och betänkandenas redovisning av remissvaren, där departementet återger vad varje organisation anfört. Originalyttrandena finns i Riksarkivet och är inte digitaliserade. Genomgången bygger på 880 stycken i riksdagstrycket och utredningarna 1945–1992 där byggföretagens eller fastighetsägarnas organisationer tar ställning, sorterade efter kapitlets avsnitt. Alla {n_citat} citat är hämtade ordagrant ur källtexten; där OCR-fel rättats visas den ursprungliga texten. Hela materialet går att söka i <a href="{ARKIVET}" target="_blank" rel="noopener">Bostadsarkivet</a> med aktörsfiltret.</p>
</header>
<section class="summary" id="sammanfattning"><h2>Sex hållpunkter</h2><ul>{summ}</ul></section>
<section id="aktorer"><h2>Vem som talade för branschen</h2>
<dl class="org">
<dt>Sveriges fastighetsägareförbund</dt><dd>De enskilda fastighetsägarnas riksorganisation, i dag Fastighetsägarna. Remissinstans i nästan varje hyres- och finansieringsfråga.</dd>
<dt>Svenska byggnadsentreprenörföreningen (SBEF)</dt><dd>Byggentreprenörernas organisation, senare Byggentreprenörerna, Sveriges Byggindustrier och i dag Byggföretagen.</dd>
<dt>Svenska byggnadsindustriförbundet</dt><dd>Byggindustrins arbetsgivarorganisation, med ett intressekontor som yttrade sig i bostadsfrågor.</dd>
<dt>Näringslivets byggnadsdelegation (NBD)</dt><dd>Näringslivets gemensamma organ i bygg- och bostadsfrågor. Fastighetsägareförbundet och Bankföreningen ställde sig ibland bakom dess yttranden. Den ska därför läsas som näringslivets samlade röst, inte bara byggföretagens.</dd>
</dl></section>
{''.join(delar)}
<section id="luckor"><h2>Vad materialet inte visar</h2>
<p>Redovisningen i propositionerna är departementets sammanfattning och kan vara förkortad. Ett yttrande som saknas i en remissredovisning behöver inte betyda att organisationen inte yttrade sig. Det tydligaste exemplet är räntebidragssystemets införande i mitten av 1970-talet, där byggföretagens och fastighetsägarnas egna synpunkter knappt syns i trycket. För dem behövs originalyttrandena i Riksarkivet, eller organisationernas egna arkiv och tidskrifter.</p>
<p>Utredningarnas egna texter, till exempel SOU 1945:63, SOU 1956:40, SOU 1975:12 och SOU 1981:104, innehåller ibland särskilda yttranden från experter som organisationerna utsett. De finns i arkivet men är inte genomgångna här.</p>
</section>
<footer><span>Källor: propositioner, utskottsbetänkanden och statliga utredningar via <a href="https://data.riksdagen.se" target="_blank" rel="noopener">Riksdagens öppna data</a> och <a href="https://sou.kb.se" target="_blank" rel="noopener">Kungliga bibliotekets digitaliserade SOU</a>. Sammanställt ur <a href="{ARKIVET}" target="_blank" rel="noopener">Bostadsarkivet</a>.</span></footer>
</main>
<nav class="toc" aria-label="Innehåll"><span>Innehåll</span><a href="#sammanfattning">Sex hållpunkter</a><a href="#aktorer">Vem som talade</a>{toc}<a href="#luckor">Vad materialet inte visar</a></nav>
</div>
"""
    UT.write_text(sida, encoding="utf-8")
    print(f"{UT}: {n_citat} citat, {len(sida) // 1000} kB")


if __name__ == "__main__":
    main()
