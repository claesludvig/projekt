# Arbetsläge – Bostadsarkivet (överlämning mellan sessioner)

Uppdaterad 2026-10-07. Läs detta först i en ny session.

## Vem och varför

Ludvig skriver ett bokkapitel om kreditpolitiken och bostadsfinansieringen i Sverige efter
kriget (arbetstitel "Kreditpolitik under efterkrigstiden", utkast som artefakt:
https://claude.ai/artifact/Xdj4MqqKTX1XAbM2b4kka3; inledningskapitel:
https://claude.ai/artifact/E7N5ny3Sr9cUcHQBSH7Rm4). Bostadsarkivet är källbasen för det.
Förebild för formen: "Ohlin i kammaren" (https://claude.ai/artifact/J6zjBRdJh6y2WUpLWBxmEB)
och "Ohlin om staten och politiken" (https://claude.ai/artifact/WCoHNsqEGTwHNyYeYgKpWB).

Kapitlets planerade struktur (avsnitt 5–9 ska skrivas, målet ca 10 000 ord):
1 Kreditpolitikens återkomst · 2 Bostadsbyggandets räntekänslighet · 3 Kreditpolitik under
efterkrigstiden · 4 Rötterna 1939–1942 · 5 Systemet byggs upp 1945–1960 · 6 Placeringsplikt och
miljonprogram 1960–1975 · 7 Från kreditstyrning till subventioner 1975–1985 · 8 Avregleringen ·
9 Avslutning. Viktiga källor: Englund (1993), Jonung (1993, 2025), Kock (1961, 1962),
SOU 1945:63, SOU 1956:40, SOU 1975:12, SOU 1981:104, SOU 1982:52, prop. 1967:100.
Avsnitten med år och ämnesord finns i `kapitel.py`.

## Var allt finns

- Gren: `claude/serene-shannon-7xw533` i `claesludvig/projekt` (inget PR skapat).
- Kod och data: `bostadsarkiv/`. Läs `README.md` för källor, regler och kommandon.
- Publicerade sidor (privata, delas via sidans dela-meny):
  - Söksidan **Bostadsarkivet**: https://claude.ai/artifact/1RQ8ZiGEsz91fNeQ8KT4wc
    (källa `webb/index.html`, data `webb/data/*.json` som byggs med `bygg_webb.py`, ej i git).
  - Sammanställningen **Branschen och bostadsfinansieringen**:
    https://claude.ai/artifact/Xw5nbx765D4mFeUeAnD4LP (byggs med `analys/bygg_branschen.py`,
    31 citat hämtade ordagrant ur databasen, OCR-rättelser listade per citat).
  - **Reservationerna i utredningarna**: https://claude.ai/artifact/8T2Vi9Npz1GqLnymEZa9kh
    (byggs med `analys/bygg_reservationer.py`, 24 citat; automatisk lista över alla
    reservationer/särskilda yttranden i SOU t.o.m. 1992 i `data/sarskilda_yttranden.jsonl.gz`
    från `analys/sarskilda_yttranden.py`; layouttext ur KB:s PDF för tvåspaltiga sidor i `data/layout/`).

## Innehåll (hämtat 2026-10-06)

Protokoll 1939–2026: 10 451 genomgångna, 29 844 relevanta anföranden. Propositioner 1 635,
betänkanden/utlåtanden 1 874, motioner 4 790, SOU 1 304 (KB:s inskannade 1939–1999 +
riksdagen 1997–), Ds 64, direktiv 142, remissvar (regeringen.se 2014–) 6 249.
Texter i git: `data/text/<typ>/*.txt.gz` (~770 MB), anföranden `data/anforanden/*.jsonl.gz`.

## Bygga om i en ny session (containern är tom utöver git)

```sh
cd bostadsarkiv
pip install -r requirements.txt          # requests; pdftotext finns i miljön
python bygg_db.py                        # ~20 min, data/bostadsarkiv.sqlite ~5,8 GB (ej i git)
python bygg_webb.py                      # ~15 min, webb/data/*.json ~155 MB (ej i git)
python sok.py 'placeringskvot*' --typ prop --fran 1960 --till 1975
```

Nätet är öppet härifrån (data.riksdagen.se, sou.kb.se/weburn.kb.se, regeringen.se fungerar).
Hämtning: `python hamta.py alla` (inkrementell), `python hamta_remisser.py`,
`python hamta.py omvardera` efter skärpt ordlista.

Publicera söksidan: max 64 MB per publicering och 256 MB per version, så datan går upp i
omgångar till samma `url` med `root: bostadsarkiv/webb` och `files: {"data/x.json": "data/x.json"}`.
U+FFFD i texten stoppar publiceringen (rensas nu i `bygg_webb.py`).

## Tolkning och kända fallgropar

- Protokollformat: "Anf. N NAMN (parti):" från ca 1980; utan kolon 1994/95–2002/03;
  "Herr LUNDBERG (s):" / "Herr statsrådet Möller:" före 1980; `<pre>`-block 1996–2003.
  Äldre protokoll har bara året i riksdagens lista – datum läses ur texten ("Onsdagen den 25 maj").
  Tvåkammarriksdagen: kammare (FK/AK) i fältet `kammare`.
- Äldre tryck är OCR med en rad per stycke; `text.sy_ihop_rader` syr ihop innan analys.
- Aktörer (`aktorer.py`): bara organisationsnamn räknas ("fastighetsägarna" i allmänhet räknas
  inte). Grupper: bygg, fast, allm, hyr, villa, bank, fack, narings, kommun, myn.
  Tabell `aktorsstycken` i databasen = stycken där aktören redovisas ta ställning.
- Remisser före 2014 finns inte digitalt hos regeringen; originalyttrandena ligger i
  Riksarkivet. Propositionernas remissredovisning är departementets sammanfattning.
- Kapitelmärkningen och relevansgraden är automatiska (ordlistor) – grov sortering.

## Fynd hittills (detaljer och citat på branschsidan)

Byggföretagen (SBEF, Byggnadsindustriförbundet), Fastighetsägareförbundet och Näringslivets
byggnadsdelegation (NBD) drev 1950–1990 samma linje: avveckla generella subventioner och
hyresreglering, marknadsränta, lika belåningsvillkor för enskilda byggherrar, men i takt med
byggandet. Placeringskvoterna 1962 avstyrktes av banker, försäkringsbolag och industri – inte
av byggföretag/fastighetsägare, som i stället ville utvidga prioriteringen till ombyggnad och
sanering (prop. 1962:52). SBEF avstyrkte paritetslånen 1967 ("monopolisering"); NBD begärde
deras avveckling 1970. Vid 1990 års omläggning (prop. 1990/91:34) tillstyrkte förbundet
begränsade räntebidrag men påpekade behovet av att fördela kapitalkostnader över tiden vid hög
inflation/realränta. Lucka: branschens hållning när räntebidragen infördes mitten av 1970-talet.

## Särskilda yttranden (klart 2026-10-07)

Automatisk genomgång: 834 SOU t.o.m. 1992 → 355 reservationer/särskilda yttranden i 140 SOU,
113 rör finansieringen eller ett kapitelavsnitt. Handläst: SOU 1947:86, 1952:37, 1956:40, 1963:58,
1966:44, 1974:17, 1974:32, 1975:12 (+ reservationen i 1948 års bostadsutredning via prop. 1953:138).
Inga reservationer: SOU 1945:63, 1961:42, 1968:30, 1982:52; SOU 1981:104 = ensamutredare.
Huvudfynd: Källenius (SBEF, h), Näverfelt (ex-SBEF) och Turesson (h/m) reserverade sig mot
utjämningslånen 1974 ("rävsaxen") och mot totalfinansieringen 1975 – fyller luckan om branschens
hållning i mitten av 1970-talet. Olofgörs/Turesson 1966: hyrorna "relativt okänslig[a] för
kortsiktiga ränteförändringar" (relevant för avsnitt 2). Verifierade roller: Wiman = vice vd
Stockholms fastighetsägareförening; Hallnäs = ombudsman Bankmannaföreningen; Erik Svensson = ordf.
Hyresgästernas riksförbund; Näverfelt = SBEF 1964; Lindberger = docent finansdep.
Oklart: Petzäll (NBD hänvisade till honom), Skarstedt (direktör Hälsingborg; SABO m.fl. stödde hans yttrande).
Spaltblandad OCR (går ej att citera utan sidbild): SOU 1973:50, delar av 1974:17, 1975:51.
Fallgrop: 1966:44 anger Källenius som instämmande, prop. 1967:100 anger Petzäll.

## Nästa uppgift

Om Ludvig vill: kapitelutkastets avsnitt 5–9 med arkivet som källbas (remissvar på branschsidan,
reservationer på reservationssidan). Möjligt tillägg: läsa sidbilderna för SOU 1973:50 och 1975:51.
