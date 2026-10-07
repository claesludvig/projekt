#!/usr/bin/env python3
"""Bygger sidan Reservationerna (reservationer.html): vad experter och
ledamöter från byggföretag, fastighetsägare, banker och partier skrev i
reservationer och särskilda yttranden till utredningarna om
bostadsfinansieringen.

Citaten hämtas ordagrant ur källtexten, antingen ur sökdatabasen (OCR-texten
som den ligger i arkivet) eller, för sidor där OCR-texten blandar ihop
spalterna, ur data/layout/<id>.txt.gz (pdftotext -layout på KB:s PDF, en rad
per tryckrad). Uppenbara OCR-fel rättas med en uttrycklig lista per citat och
källtexten visas då under "OCR-text i källan".

    python analys/sarskilda_yttranden.py      # automatisk genomgång, alla SOU till 1992
    python analys/bygg_reservationer.py
"""

import csv
import gzip
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "analys"))
from bygg_branschen import CSS, hamta, lank  # noqa: E402

DB = BASE / "data" / "bostadsarkiv.sqlite"
LAYOUT = BASE / "data" / "layout"
YTTRANDEN = BASE / "data" / "sarskilda_yttranden.jsonl.gz"
UT = Path(__file__).resolve().parent / "reservationer.html"
ARKIVET = "https://claude.ai/artifact/1RQ8ZiGEsz91fNeQ8KT4wc"
BRANSCHEN = "https://claude.ai/artifact/Xw5nbx765D4mFeUeAnD4LP"

_DOK = {r["beteckning"]: r for r in csv.DictReader(open(BASE / "data" / "dokument.csv", encoding="utf-8"))
        if r["relevant"] == "1"}


def layout_text(bet):
    """Layouttexten som en sträng utan sidmarkörer, avstavning hopfogad, och
    en lista med (position, sida) för att hitta sidnumret."""
    r = _DOK[bet]
    t = gzip.open(LAYOUT / f"{r['id']}.txt.gz", "rt", encoding="utf-8").read()
    ut, sidor = [], []
    for del_ in re.split(r"\[PDF-sida (\d+)\]\n", t)[1:]:
        if del_.isdigit():
            sida = int(del_)
            continue
        s = re.sub(r"(\w)-[ \t]*\n\s*(?=[a-zåäö])", r"\1", del_)
        s = re.sub(r"\s+", " ", s).strip()
        sidor.append((sum(len(x) + 1 for x in ut), sida))
        ut.append(s)
    return " ".join(ut), sidor, r


class Citat:
    """Ett citat från fran till och med slut. kalla = "db" (sökdatabasen) eller
    "layout" (layouttexten ur PDF:en)."""

    def __init__(self, bet, fran, slut=None, ratt=(), aktor="", datum="", kalla="db"):
        self.bet, self.fran, self.slut, self.ratt = bet, fran, slut, ratt
        self.aktor, self.datum, self.kalla = aktor, datum, kalla

    def kalltext(self, db):
        if self.kalla == "db":
            did, url, s = hamta(db, self.bet, self.fran, self.slut)
            return s[s.lower().find(self.fran.lower()):], lank(did, url)
        t, sidor, r = layout_text(self.bet)
        i = t.find(self.fran)
        if i < 0:
            raise SystemExit(f"Hittar inte {self.fran!r} i layouttexten för {self.bet}")
        j = t.find(self.slut, i) if self.slut else -1
        if self.slut and j < 0:
            raise SystemExit(f"Hittar inte slutet {self.slut!r} i {self.bet}")
        s = t[i:j + len(self.slut)] if self.slut else t[i:i + 400]
        sida = max(p for pos, p in sidor if pos <= i)
        return s, f"{r['pdf_url']}#page={sida}"

    def html(self, db):
        kall, url = self.kalltext(db)
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
                f'<a href="{url}" target="_blank" rel="noopener">Källan</a>{ocr}</figcaption></figure>')


# --- Innehåll -------------------------------------------------------------------

AVSNITT = [
    ("tidigt", "Systemet byggs upp, 1945–1960", "Kapitlets avsnitt 5", [
        "Bostadssociala utredningens slutbetänkande (SOU 1945:63), som lade grunden för efterkrigssystemet, "
        "har inga reservationer. Striden om formerna kom i stället i bankkommittén 1947. Majoriteten, där "
        "bankdirektörerna satt, föreslog att statens direkta bostadslån skulle ersättas av kreditgarantier "
        "till de privata kreditinstituten. De socialdemokratiska ledamöterna godtog förslaget, men ville inte "
        "stänga dörren för en statlig affärsbank.",
        Citat("SOU 1947:86", "Ett system med statliga kreditgarantier, som kommittén förordar",
              slut="ett dylikt system.", datum="1947",
              aktor="Jonsson, Olof Andersson, Hall och Severin, särskilt yttrande (bankkommittén)"),
        "Bankmannaföreningens ombudsman S. Hallnäs pekade på det som skulle bli frågan i trettio år: om "
        "räntegarantin togs bort måste en högre ränta antingen slå igenom i hyrorna eller bäras av skatterna.",
        Citat("SOU 1947:86", "Ytterst rör denna fråga", slut="bostadsproduktionen.", datum="1947",
              aktor="S. Hallnäs, Svenska bankmannaföreningen, särskilt yttrande"),
        "I hyresregleringskommittén 1952 satt Stockholms fastighetsägareförenings vice verkställande direktör "
        "Hans Wiman. Han avvisade den föreslagna lagen om bostadsanvisning och vände på frågan om "
        "bostadsbristens orsaker.",
        Citat("SOU 1952:37", "Man kan därvid icke bortse ifrån att den allmänna ekonomiska politiken",
              slut="bidragande orsak till bostadsbristen.", datum="1952",
              aktor="Hans Wiman, Stockholms fastighetsägareförening, särskilt yttrande"),
        "Samma år reserverade sig högermannen Cassel och bankdirektören L.-E. Thunholm i 1948 års "
        "bostadsutredning. Betänkandet är inte inskannat i arkivet, men propositionen återger reservationen. "
        "De ville börja avveckla subventionerna direkt, och Näringslivets bostadsbyggnadsdelegation slöt upp "
        "bakom dem i remissen.",
        Citat("Prop. 1953:138", "Mot utredningens förslag rörande storleken av det löpande bidraget",
              slut="tills vidare begränsas till 2 kr. per kvm.", datum="1953",
              aktor="Cassel och Thunholm, reservation, återgiven i propositionen"),
        "I bostadspolitiska utredningen 1956 krävde Leif Cassel (h) och Henning Gustafsson (fp) lika villkor för "
        "alla byggherrar. Den ränta staten subventionerade skulle bara gälla lån som alla företagsformer fick, "
        "och lånen ovanför den gränsen skulle kosta ungefär marknadsränta.",
        Citat("SOU 1956:40", "Statliga lån som lämnas ovanför denna gräns", slut="motsvarande lån.",
              datum="1956", aktor="Leif Cassel (h) och Henning Gustafsson (fp), reservation"),
        "Cassel gick längre i ett eget yttrande. Han trodde inte att stödet hade gett fler bostäder, och han "
        "ville förbereda ett kreditgarantisystem när kapitalmarknaden blev fri.",
        Citat("SOU 1956:40", "Jag finner det sannolikt att ett minst lika stort antal lägenheter",
              slut="lägre", datum="1956", aktor="Leif Cassel (h), särskilt yttrande"),
        Citat("SOU 1956:40", "Emellertid betyder detta ingalunda att kreditgarantisystemet", slut="vidtagas.",
              datum="1956", aktor="Leif Cassel (h), särskilt yttrande"),
    ]),
    ("placering", "Placeringsplikt och paritetslån, 1960–1975", "Kapitlets avsnitt 6", [
        "Kreditmarknadsutredningen bakom placeringskvoterna (SOU 1961:42) och 1967 års "
        "bostadskreditdelegation (SOU 1968:30) har inga reservationer. Det har däremot "
        "bostadspolitiska kommittén, som 1966 föreslog paritetslånen (SOU 1966:44). Där satt "
        "Byggnadsindustriförbundets direktör Gunnar Olofgörs och högerns Bo Turesson. De ville i stället "
        "trappa av räntebidragen efter en plan som var bestämd i förväg. Deras argument är intressant för "
        "kapitlets fråga om räntekänsligheten: hyrorna, menade de, rörde sig knappt med räntan.",
        Citat("SOU 1966:44", "Genom detta alternativ avskärmas visserligen inte", slut="bostadsutredningar.",
              datum="1966",
              aktor="Gunnar Olofgörs (Byggnadsindustriförbundet) och Bo Turesson (h), med instämmande av Sten Källenius"),
        "De varnade också för att omfördelningen av kapitalkostnaderna skulle kräva mer av kapitalmarknaden och "
        "skrämma bort det privata kapitalet från hyreshusen.",
        Citat("SOU 1966:44", "En omfördelning av kapitalkostnaderna av den typ", slut="träda i tillämpning.",
              datum="1966", aktor="Olofgörs och Turesson, reservation"),
        "Turesson reserverade sig också för en gemensam övre lånegräns för alla byggherrar.",
        Citat("SOU 1966:44", "En prioritering av vissa byggherrar minskar", slut="byggnadssektorn.",
              datum="1966", aktor="Bo Turesson (h), med instämmande av Ingvar Petzäll"),
        "Experten Ingvar Petzäll skrev det längsta yttrandet. Näringslivets byggnadsdelegation hänvisade "
        "sedan till det i sitt remissvar (prop. 1967:100). Han ville ersätta statens lån med ett kollektivt "
        "kreditgarantisystem och låta avkastningsvärdet bestämma lånens storlek.",
        Citat("SOU 1966:44", "Om långivningen i stället baseras på husets avkastningsvärde",
              slut="naturlig press på produktionskostnaderna.", datum="1966",
              aktor="Ingvar Petzäll, särskilt yttrande"),
        "Centerns Alvar Andersson och folkpartiets Henning Gustafsson såg också fördelar med kreditgarantier. "
        "De valde ändå paritetslånen.",
        Citat("SOU 1966:44", "Det är nödvändigt att träffa ett val", slut="kreditgarantier och paritetslån.",
              datum="1966", aktor="Alvar Andersson (c) och Henning Gustafsson (fp), särskilt yttrande"),
        Citat("SOU 1966:44", "Våra bedömningar har som framgår", slut="förslaget om paritetslån.",
              datum="1966", aktor="Alvar Andersson (c) och Henning Gustafsson (fp), särskilt yttrande"),
        "Finansdepartementets docent Lars Lindberger ställde sig bakom paritetslånen, men gav dem det namn som "
        "kritikerna senare använde.",
        Citat("SOU 1966:44", "Riktigare vore enligt min uppfattning", slut="villkorlig återbetalningsskyldighet.",
              datum="1966",
              aktor="Lars Lindberger, särskilt yttrande"),
        "Redan 1963 hade Sten Källenius, verkställande direktör i Svenska byggnadsentreprenörföreningen och "
        "högerledamot i andra kammaren, i lokaliseringsutredningen avvisat en statlig lånefond. Kreditprövningen "
        "skulle göras av bankerna.",
        Citat("SOU 1963:58", "En i statlig regi uppbyggd ny apparat", slut="onödig dubblering.", datum="1963",
              aktor="Sten Källenius (SBEF, h), särskilt yttrande"),
    ]),
    ("utjamning", "Utjämningslånen och totalfinansieringen, 1974–1975", "Kapitlets avsnitt 7", [
        "Här finns det som remissvaren i propositionerna inte visar: branschens hållning när paritetslånen "
        "skulle ersättas i mitten av 1970-talet. Boende- och bostadsfinansieringsutredningarna föreslog 1974 "
        "ett utjämningslån där kapitalkostnaden skulle börja lågt och sedan räknas upp varje år. Sten Källenius "
        "och Arne Näverfelt reserverade sig. Näverfelt hade tidigare arbetat på byggentreprenörföreningen.",
        Citat("SOU 1974:17", "Vad gäller det föreslagna finansieringssystemet", slut="kan tillämpas.",
              kalla="layout", datum="1974",
              aktor="Sten Källenius (SBEF) och Arne Näverfelt, reservation"),
        Citat("SOU 1974:17", "På empiriska grunder kan fastslås", slut="under perioden 1955-1973.",
              kalla="layout", datum="1974", aktor="Källenius och Näverfelt, reservation"),
        "Bo Turesson (m) såg samma skuldökning som i paritetslånen under ett nytt namn.",
        Citat("SOU 1974:17", "Förutsättningarna för att de lånen statliga", slut="som paritetslånen gjort.",
              ratt=[("de lånen statliga", "de statliga lånen")], kalla="layout", datum="1974",
              aktor="Bo Turesson (m), reservation"),
        "Hyresgästernas riksförbunds ordförande Erik Svensson stödde utjämningslånet, men varnade för att en "
        "för hög uppräkning skulle äta upp vinsten för hyresgästerna.",
        Citat("SOU 1974:17", "De som realistiska angivna talen", slut="snabbt förloras.",
              ratt=[("De som realistiska angivna talen - 5.0 3,5 % per år", "De som realistiska angivna talen 3,5–5,0 % per år")],
              kalla="layout", datum="1974", aktor="Erik Svensson (Hyresgästernas riksförbund), särskilt yttrande"),
        "I slutbetänkandet räknade Källenius och Näverfelt på systemet i en egen bilaga. Statens förlust skulle "
        "växa så snabbt att systemet inte gick runt.",
        Citat("SOU 1974:32", "De utförda räkneexemplen visar", slut="efter bara några år.", datum="1974",
              ratt=[("utjämningsfaktor på 3 %>", "utjämningsfaktor på 3 %.")],
              aktor="Sten Källenius och Arne Näverfelt, reservation"),
        Citat("SOU 1974:32", "Om en investering på 100 000 kronor finansieras",
              slut="totalsumma av 1 035 000 kronor.", datum="1974", aktor="Bo Turesson (m), reservation"),
        "Ett år senare föreslog utredningarna totalfinansiering, ett enda lån från botten till topp. "
        "Källenius, Näverfelt och Turesson reserverade sig igen. Nu försvarade de den ordning de tidigare hade kritiserat, "
        "och de pekade på räntebidragens starttidpunkt som det som avgjorde boendekostnaden.",
        Citat("SOU 1975:12", "Reservationen motiveras även av", slut="betänkande föreligga.",
              kalla="layout", datum="1975", aktor="Sten Källenius, Arne Näverfelt och Bo Turesson, reservation"),
        Citat("SOU 1975:12", "Från konsumentsynpunkt torde formerna", slut="färdigställande.",
              kalla="layout", datum="1975", aktor="Källenius, Näverfelt och Turesson, reservation"),
        "Folkpartiets Ola Ullsten ställde sig bakom totalfinansieringen men ville behålla bottenlåneinstituten.",
        Citat("SOU 1975:12", "För egen del anser jag", slut="lån under byggnadstiden.",
              kalla="layout", datum="1975", aktor="Ola Ullsten (fp), särskilt yttrande"),
    ]),
]

SAMMANFATTNING = [
    ("Samma få namn återkommer.",
     "Under trettio år var det i stort sett Leif Cassel, Bo Turesson, Sten Källenius, Gunnar Olofgörs, Ingvar Petzäll "
     "och Arne Näverfelt som reserverade sig för byggföretagens och näringslivets linje. De satt både som "
     "riksdagsmän och som organisationsföreträdare."),
    ("Kreditgarantier i stället för statslån.",
     "Från bankkommittén 1947 till Petzäll 1966 var alternativet till statens direkta lån detsamma: "
     "statliga garantier för lån som de privata instituten gav, med marknadsränta och lika villkor för alla byggherrar."),
    ("Hyrorna ansågs okänsliga för räntan.",
     "Olofgörs och Turesson skrev 1966 att hyrorna i en balanserad marknad knappt påverkades av kortsiktiga "
     "ränteförändringar. Det gjorde avskärmningen mot räntan onödig."),
    ("Paritetslånen och utjämningslånen sågs som dold skuld.",
     "Lindberger kallade 1966 paritetslånen subventioner med villkorlig återbetalningsskyldighet. År 1974 räknade "
     "Källenius, Näverfelt och Turesson fram att utjämningslånet aldrig skulle gå runt."),
    ("1975 försvarade branschen den ordning den kritiserat.",
     "Mot totalfinansieringen ville reservanterna behålla den finansieringsordning som fanns och vänta på "
     "kapitalmarknadsutredningen. Det som avgjorde var när räntebidragen började."),
]


def statistik():
    rader = [json.loads(x) for x in gzip.open(YTTRANDEN, "rt", encoding="utf-8")]
    fin = [r for r in rader if r["karntraffar"] >= 2 or r["kapitel"]]
    return len(rader), len({r["sou"] for r in rader}), len(fin), len({r["sou"] for r in fin})


def main():
    db = sqlite3.connect(DB)
    n_citat, delar = 0, []
    for sid, rubrik, kap, innehall in AVSNITT:
        kropp = []
        for x in innehall:
            if isinstance(x, Citat):
                kropp.append(x.html(db))
                n_citat += 1
            else:
                kropp.append(f"<p>{html.escape(x)}</p>")
        delar.append(f'<section id="{sid}"><span class="kap">{kap}</span><h2>{rubrik}</h2>{"".join(kropp)}</section>')
    n, n_sou, n_fin, n_fin_sou = statistik()
    summ = "".join(f"<li><strong>{html.escape(a)}</strong>{html.escape(b)}</li>" for a, b in SAMMANFATTNING)
    toc = "".join(f'<a href="#{sid}">{rubrik}</a>' for sid, rubrik, _, _ in AVSNITT)
    sida = f"""<meta charset="utf-8">
<title>Reservationerna i utredningarna</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,600&display=swap">
<style>{CSS}</style>
<div class="wrap"><main>
<header>
<span class="eyebrow">Statens offentliga utredningar 1947–1975</span>
<h1>Reservationerna i utredningarna</h1>
<p class="lede">Vad byggföretagens, fastighetsägarnas och bankernas företrädare, och de borgerliga ledamöterna, skrev när de inte delade majoritetens förslag om bostadsfinansieringen.</p>
<p class="meta">Reservationer och särskilda yttranden trycktes i betänkandet och är därför bevarade i sin helhet, till skillnad från remissvaren. Alla {n_sou} utredningar till och med 1992 i arkivet med reservationer eller särskilda yttranden har gåtts igenom automatiskt. Det gav {n} yttranden, varav {n_fin} i {n_fin_sou} utredningar rör finansieringen eller något av kapitlets avsnitt. Utredningarna bakom de stora besluten är lästa för hand. Alla {n_citat} citat är ordagranna. Där OCR-fel rättats visas den ursprungliga texten. Länken går till sidan i KB:s inskannade original. Sidan kompletterar <a href="{BRANSCHEN}" target="_blank" rel="noopener">Branschen och bostadsfinansieringen</a>, som bygger på remissvaren.</p>
</header>
<section class="summary" id="sammanfattning"><h2>Fem hållpunkter</h2><ul>{summ}</ul></section>
<section id="personer"><h2>Reservanterna</h2>
<dl class="org">
<dt>Leif Cassel</dt><dd>Högerledamot i andra kammaren. Reserverade sig 1953 tillsammans med bankdirektören L.-E. Thunholm, och 1956.</dd>
<dt>Hans Wiman</dt><dd>Vice verkställande direktör i Stockholms fastighetsägareförening, ledamot av hyresregleringskommittén.</dd>
<dt>S. Hallnäs</dt><dd>Ombudsman i Svenska bankmannaföreningen, ledamot av 1945 års bankkommitté.</dd>
<dt>Sten Källenius</dt><dd>Verkställande direktör i Svenska byggnadsentreprenörföreningen (SBEF) och högerledamot i andra kammaren. Satt i utredningarna 1963–1975.</dd>
<dt>Gunnar Olofgörs</dt><dd>Direktör i Svenska byggnadsindustriförbundet.</dd>
<dt>Bo Turesson</dt><dd>Riksdagsledamot för högern och moderaterna. Satt i bostadsutredningarna 1964–1975.</dd>
<dt>Ingvar Petzäll</dt><dd>Expert i bostadspolitiska kommittén 1966. Näringslivets byggnadsdelegation hänvisade till hans yttrande i sitt remissvar. Hans egen tillhörighet anges inte i trycket.</dd>
<dt>Arne Näverfelt</dt><dd>Utredare på Svenska byggnadsentreprenörföreningen på 1960-talet, direktör när han satt i bostadsfinansieringsutredningen 1974–1975.</dd>
<dt>Erik Svensson, Ola Ullsten, Alvar Andersson, Henning Gustafsson, Lars Lindberger</dt><dd>Ordförande i Hyresgästernas riksförbund, folkpartist, centerpartist, folkpartist, och docent i finansdepartementet. De finns med som motbild.</dd>
</dl></section>
{''.join(delar)}
<section id="luckor"><h2>Vad som saknas</h2>
<p>SOU 1945:63 har inga reservationer. Kreditmarknadsutredningen 1961 (SOU 1961:42), bostadskreditdelegationen 1968 (SOU 1968:30) och 1982 års kreditpolitiska betänkande (SOU 1982:52) har inte heller några, i den mån den inskannade texten visar det. SOU 1981:104 skrevs av en ensam utredare. Betänkandet från 1948 års bostadsutredning finns inte i arkivet, så reservationen 1953 är citerad ur propositionen.</p>
<p>Några betänkanden är tryckta i två spalter, och OCR-texten blandar ihop dem. Det gäller till exempel SOU 1973:50, med ett yttrande av Källenius om provisoriska lån för hyresförluster, och delar av SOU 1974:17 och SOU 1975:51. De har inte gått att citera och behöver läsas i originalet. Den automatiska listan med alla {n} yttranden finns i <code>data/sarskilda_yttranden.jsonl.gz</code>. Den har namn, sida, kapitelavsnitt och en gissning om aktörsgrupp, och gissningen behöver alltid kontrolleras.</p>
</section>
<footer><span>Källor: statliga utredningar via <a href="https://sou.kb.se" target="_blank" rel="noopener">Kungliga bibliotekets digitaliserade SOU</a> och propositioner via <a href="https://data.riksdagen.se" target="_blank" rel="noopener">Riksdagens öppna data</a>. Sammanställt ur <a href="{ARKIVET}" target="_blank" rel="noopener">Bostadsarkivet</a>.</span></footer>
</main>
<nav class="toc" aria-label="Innehåll"><span>Innehåll</span><a href="#sammanfattning">Fem hållpunkter</a><a href="#personer">Reservanterna</a>{toc}<a href="#luckor">Vad som saknas</a></nav>
</div>
"""
    UT.write_text(sida, encoding="utf-8")
    print(f"{UT}: {n_citat} citat, {len(sida) // 1000} kB")


if __name__ == "__main__":
    main()
