# Bostadsrapporterna

Rapporter, analyser, prognoser och remissvar om bostadsmarknaden och bostadsbyggandet från
intresseorganisationer, tankesmedjor och myndigheter, nedladdade och sökbara i fulltext sida för
sida. Byggd på samma sätt som Bostadsarkivet (riksdagens protokoll och tryck): ladda ner,
läs ut texten, klassa relevans och teman, lägg i en sökbar databas och ett sökgränssnitt.

## Aktörer

| Kod | Aktör | Var rapporterna hittas |
|---|---|---|
| `sn` | Svenskt Näringsliv | sitemap (sakområden, frågor, regioner) + webbsök; sidorna renderas i Chromium |
| `fa` | Fastighetsägarna | `/aktuellt/rapporter/`, `/fakta/`, rapportnyheter; renderas i Chromium |
| `hsb` | HSB | nyhetsarkivet per år och kategorin Undersökningar och rapporter |
| `hgf` | Hyresgästföreningen | `/bostadsfakta/rapporter/` och `/globalassets/bostadsfakta/` |
| `shk` | Stockholms Handelskammare | hela PDF-biblioteket (WordPress) + rapportsidor |
| `bf` | Byggföretagen | PDF-biblioteket (WordPress) + nyheter om rapporter, prognoser och statistik |
| `sa` | Sveriges Allmännytta | hela PDF-biblioteket (WordPress) |
| `rb` | Riksbyggen | bostadspolitik och pressrummet |
| `tim` | Timbro | publikationer och PDF-biblioteket (WordPress) |
| `bov` | Boverket | publikationer 2005– och bostadsmarknadssidorna |
| `fs` | Svenska Bankföreningen | Fakta och rapporter (bl.a. Bolånemarknaden i Sverige) |

Aktörer, sökvägar och ordlistor finns i `katalog.py`. Fler aktörer läggs till där; sidor som inte
finns i någon sitemap läggs i `extra_sidor.txt`.

## Körning

```bash
pip install -r requirements.txt          # pdftotext/pdfinfo (poppler-utils) och, för fa/sn, Node + Playwright
python hamta.py                          # sitemaps, sidor, pdf, text
python hamta.py wp rendera pdf text      # mediebibliotek, JS-sajter, nedladdning, textutläsning
python bygg.py                           # databas, CSV och sökgränssnittets data
```

Allt är inkrementellt: redan hämtade sidor, PDF:er och texter hämtas inte igen.

## Urval och klassning

- En PDF kommer med om den länkas från en sida som rör bostäder (ord i adress eller rubrik, eller
  minst tre fackord i texten) eller ligger i ett mediebibliotek med bostadsord i namnet.
- Därefter räknas ett 40-tal fackord i hela texten (`TERMER` i `katalog.py`). Under fyra träffar
  tas rapporten bort. **Relevans**: hög = minst 40 träffar och minst 3 per 1 000 ord, eller
  bostadsord i rubriken och minst 15 träffar; medel = minst 12 träffar; annars låg.
- **Teman** (byggande, hyressättning, bolån, skatter, planering, rörlighet, priser, allmännyttan,
  Stockholm/regional tillväxt, renovering) sätts efter ord i texten.
- **Slag**: remissvar och yttranden, prognoser/index/enkäter, övrigt rapporter och analyser.
- Samma rapport i flera versioner (läs- och tryckversion, uppslag) tas med en gång (ordlikhet > 85 %).
- Datum är rapportsidans publiceringsdatum, annars PDF:ens tillkomstdatum.

## Databasen

`data/bostadsrapporter.sqlite.gz` (packa upp med `gunzip -k`). Tabeller:

- `dokument` – en rad per rapport: aktör, titel, datum, år, slag, relevans, träffar, sidor, teman, länkar
- `sida` – texten per PDF-sida
- `sida_fts` – fulltextindex (SQLite FTS5) över `sida`
- `aktor`, `tema` – kodlistor

```sql
-- Var skriver aktörerna om presumtionshyra, nyast först?
SELECT d.datum, a.namn, d.titel, s.sidnr, snippet(sida_fts, 0, '[', ']', ' … ', 12)
FROM sida_fts JOIN sida s ON s.rowid = sida_fts.rowid
JOIN dokument d USING (id) JOIN aktor a USING (aktor)
WHERE sida_fts MATCH 'presumtionshyr*'
ORDER BY d.datum DESC;

-- Antal rapporter per aktör och år om bolån och skulder
SELECT aktor, ar, count(*) FROM dokument WHERE teman LIKE '%fin%' GROUP BY 1, 2;
```

Förteckningen finns även som `data/csv/dokument.csv`, texten per rapport i
`data/text/<aktör>/<id>.json.gz` och PDF-adresserna i `data/pdf_lista.json`. PDF:erna själva
checkas inte in (flera GB); `python hamta.py pdf` laddar ner dem igen.

## Sökgränssnittet

`webb/index.html` med `webb/data/` (byggs av `bygg.py`). Publicerat som artefakt (https://claude.ai/artifact/2S84sd1ptt74bCJHxYH8BR, privat); söker i hela
texten i webbläsaren, med träffar per sida och länk direkt till sidan i PDF:en.

## Begränsningar

- Texten är maskinutläst. Tabeller, flerspaltig layout och avstavning kan bli fel; inskannade
  PDF:er utan textlager kommer inte med.
- Urvalet bygger på webbplatsernas nuvarande struktur. Äldre rapporter som tagits bort från
  sajterna saknas, och HSB:s och Svenskt Näringslivs arkiv är bara delvis åtkomliga utan sökfunktion.
- HSB:s robots.txt ber sökrobotar att inte indexera PDF:er. Här hämtas ett tjugotal enskilda
  rapporter för eget bruk; publicera inte texten vidare.
