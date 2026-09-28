"""Skriver KALLOR.md och motioner.csv: förteckning över källmaterialet utanför riksdagens protokoll."""
import csv, json, os, re

HÄR = os.path.dirname(os.path.abspath(__file__))
NEF = json.load(open(os.path.join(HÄR, 'nef_katalog.json')))
MOT = json.load(open(os.path.join(HÄR, 'motioner.json')))

STYRELSE = re.compile(r'författning|grundlag|enkammar|kammare|riksdag|val(?:system|sätt|et|\b)|rösträtt|folkomröstning|'
                      r'partipropaganda|partiernas|förvaltning|regeringsrätt|domstol|justitiekansler|ombudsman|JO-|'
                      r'kommunal|statlig kontroll|ämbetsansvar|besparing|opartisk|rättsuppfattning|organisation', re.I)

PROGRAM = [
    ('fp_p_1934', 'Folkpartiets program 1934', 'Programmet när folkpartiet bildades, före Ohlins tid som ledare.'),
    ('fp_p_1944', 'Folkpartiets program 1944', 'Antaget 11 juni 1944, samma år som Ohlin blev partiledare.'),
    ('fp_p_1962', 'Folkpartiets program 1962', 'Det enda nya principprogrammet under Ohlins tid som ledare.'),
] + [(f'fp_v_{å}', f'Valmanifest {å}', '') for å in (1936, 1940, 1944, 1948, 1952, 1956, 1958, 1960, 1964, 1968, 1970)]


def md_tabell(rader, huvud):
    ut = ['| ' + ' | '.join(huvud) + ' |', '|' + '---|' * len(huvud)]
    ut += ['| ' + ' | '.join(str(c).replace('|', '/') for c in r) + ' |' for r in rader]
    return '\n'.join(ut)


def bygg():
    with open(os.path.join(HÄR, 'motioner.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['riksmöte', 'nr', 'kammare', 'Ohlins roll', 'rubrik', 'dok_id', 'url'])
        for m in MOT:
            w.writerow([m['rm'], m['beteckning'], m['undertitel'], m['roll'], m['rubrik'], m['dok_id'], m['url']])

    förslag = [m for m in MOT if m['roll'] == 'förslagsställare']
    styr = [m for m in MOT if STYRELSE.search(m['rubrik'] or '')]
    delar = [f"""# Källmaterial utanför riksdagens protokoll

Material av och om Bertil Ohlin som kompletterar protokollen i registret *Ohlin i kammaren*.
Allt nedan är hämtat från öppna källor. Texterna är OCR-tolkade och har inte korrekturlästs.

Ohlin dog 1979, och hans böcker och artiklar är upphovsrättsligt skyddade till och med 2049.
Här finns därför bara offentligt tryck och material som utgivaren själv lagt ut fritt.
Annat som finns digitalt är listat under *Bara länkar*.

## 1. Folkpartiets program och valmanifest 1934–1970

Från Svensk nationell datatjänsts samling av partiprogram och valmanifest (Vivill), <https://snd.se/sv/vivill/party/fp>.
Text och PDF finns i `partiprogram/`.

{md_tabell([(f'`{f}`', t, b) for f, t, b in PROGRAM], ['Fil', 'Dokument', 'Kommentar'])}

Valmanifestet 1964 innehåller bara omkring 190 ord i SND:s textversion. Se PDF:en.

## 2. Nationalekonomiska föreningens förhandlingar

Föreningen har lagt ut sina förhandlingar 1877–1972 som PDF, <https://www.nationalekonomi.se>.
Alla årgångar 1925–1972 har genomsökts via innehållsförteckningarna. Bertil Ohlin talade vid
**{len(NEF)} sammanträden** 1930–1969 och inledde {sum(k['roll'] == 'inledare' for k in NEF)} av dem.
Varje sammanträde finns som egen textfil i `nef/`. Diskussionerna återges i sin helhet, så
motdebattörernas inlägg finns med.

Innehållsförteckningarna nämner också Nils Wohlin, Lars Wohlin och nationalekonomen Göran Ohlin.
Deras sammanträden är bortsorterade. Sammanträden där Ohlin yttrade sig utan att stå i
innehållsförteckningen kan saknas.

{md_tabell([(k['datum'], k['ämne'], k['roll'], f"`{k['textfil']}`",
             f"[PDF s. {k['sidor'][0]}–{k['sidor'][1]}](https://www.nationalekonomi.se/wp-content/uploads/2020/09/{k['fil'][:-4]}.pdf)")
            for k in NEF], ['Datum', 'Ämne', 'Ohlins roll', 'Text', 'Original'])}

## 3. Riksdagsmotioner 1938–1970

Motionerna är riksdagstryck men inte protokoll. De visar vilka förslag Ohlin själv drev.
Av 876 motioner som nämner Ohlin har han skrivit under **{len(MOT)}**. I {len(förslag)} av dem står
han först, "Av herr Ohlin …", och i {len(MOT) - len(förslag)} är han en av flera undertecknare.
Alla finns i `motioner.csv` och som text i `motioner/`.

Motioner om författning, val, förvaltning, rättssäkerhet och kommunal självstyrelse ({len(styr)} st.):

{md_tabell([(m['rm'], m['beteckning'], 'AK' if m['undertitel'].startswith('Andra') else 'FK', m['roll'],
             m['rubrik'][:150], f"[{m['dok_id']}]({m['url']})") for m in styr],
           ['År', 'Nr', 'Kammare', 'Ohlins roll', 'Rubrik', 'Text'])}

## 4. Offentligt tryck och internationella rapporter

| Fil | Verk | Källa |
|---|---|---|
| `texter/SOU_1934_12_Ohlin_penningpolitik.txt` | Ohlin, *Penningpolitik, offentliga arbeten, subventioner och tullar som medel mot arbetslöshet* (SOU 1934:12). Hans bidrag till Arbetslöshetsutredningen, omkring 80 000 ord. | [KB, PDF](https://weburn.kb.se/sou/204/urn-nbn-se-kb-digark-2039038.pdf), text via [lagen.nu](https://lagen.nu/sou/1934:12) |
| `texter/Nationernas_forbund_1931_Ohlin_world_economic_depression.txt` | Ohlin, *The Course and Phases of the World Economic Depression* (Nationernas förbund, 1931). | [Internet Archive](https://archive.org/details/TheCauseAndPhasesOfTheWorldEconomicDepression) |

## 5. Bara länkar

Följande material är digitaliserat men antingen skyddat, bara tillgängligt som ljud eller video,
eller spärrat för automatisk hämtning härifrån.

**Ohlins egna texter och framträdanden**
- Nobelföreläsningen 1977 och en självbiografisk text: [nobelprize.org](https://www.nobelprize.org/prizes/economic-sciences/1977/ohlin/lecture/), [biografi](https://www.nobelprize.org/prizes/economic-sciences/1977/ohlin/biographical/). Också på [Svenska tal](https://www.svenskatal.se/tal/bertil-ohlin-nobelprisforelasning-1977).
- *Bertil Ohlin – folkpartiledare i 23 år*: tre radioprogram från 1975 där han berättar om partiledartiden för Arvid Lagercrantz. [Sveriges Radio, Radiofynd](https://www.sverigesradio.se/artikel/910013).
- *Bertil Ohlin minns*: [SVT Öppet arkiv](https://www.oppetarkiv.se/video/2486205/bertil-ohlin-minns). Partiledarintervjuer och slutdebatt 1966 finns i [Kommunalval 1966](https://www.svtplay.se/kommunalval-1966).
- *The Problem of Employment Stabilization* (1949): skannad i Digital Library of India på [Internet Archive](https://archive.org/details/in.ernet.dli.2015.90494). Upphovsrätten är oklar, så boken är inte kopierad hit.
- *Interregional and International Trade* (1933, 1967): utlån på [Internet Archive](https://archive.org/details/interregionalint0000ohli).
- *Fri eller dirigerad ekonomi* (1936) och memoarerna (*Ung man blir politiker*, *Bertil Ohlins memoarer 1940–1951*) finns inte fritt digitalt. Se [Libris](https://libris.kb.se).

**Om Ohlin**
- Svenskt biografiskt lexikon: [Bertil G Ohlin](https://sok.riksarkivet.se/sbl/Presentation.aspx?id=7663).
- Riksarkivet: Ohlins personarkiv, omkring 220 volymer, via [NAD](https://sok.riksarkivet.se/nad). Det är inte digitaliserat.
- Hans Brems, *Bertil Ohlin's Contributions to Economic Theory* (1986): [Internet Archive](https://archive.org/details/bertilohlinscont1305brem).
- Mats Lundahl, *Nationalekonomen Bertil Ohlin*: [Svensk Tidskrift](https://www.svensktidskrift.se/mats-lundahl-nationalekonomen-bertil-ohlin/).
- Johan Hakelius, *Bertil Ohlin och välfärdsstaten* (Timbro 1994): [PDF](https://timbro.se/smedjan/usa-ar-ett-politiskt-disneyland/attachment/294/).
- Liberal Debatt 2013: [Ohlins "alternativ" skapade borgerligheten](https://www.liberaldebatt.se/2013/12/ohlins-%E2%80%9Dalternativ%E2%80%9D-skapade-borgerligheten/) och [Vad ska vi med Ohlin till?](https://www.liberaldebatt.se/2013/12/vad-ska-vi-med-ohlin-till/).
- Uppsatser: [Vad är Liberalernas liberalism?](https://www.diva-portal.org/smash/get/diva2:1576661/FULLTEXT01.pdf) (DiVA), [The Young Ohlin on the Theory of Interregional and International Trade](https://www.diva-portal.org/smash/get/diva2:328550/FULLTEXT01.pdf).
- Tidningar: [tidningar.kb.se](https://tidningar.kb.se) är sökbart, men material från Ohlins tid kan i regel bara läsas i sin helhet på KB och vissa bibliotek.
"""]
    open(os.path.join(HÄR, 'KALLOR.md'), 'w').write('\n'.join(delar))
    print('KALLOR.md:', len(NEF), 'sammanträden,', len(MOT), 'motioner,', len(styr), 'om styrelseskicket')


if __name__ == '__main__':
    bygg()
