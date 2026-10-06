# Bostadsarkivet

En sökbar samling av källmaterial om bostadsbyggandet och dess finansiering i Sverige
1939 till i dag: riksdagens kammarprotokoll (per anförande), propositioner,
utskottsbetänkanden, motioner, statliga utredningar (SOU, Ds, kommittédirektiv) och
regeringens remissvar, i fulltext.

## Innehåll (hämtat 2026-10-06)

| Typ | Bedömda | Med i basen |
|---|---|---|
| Kammarprotokoll 1939– | 10 451 protokoll | 29 844 anföranden |
| Propositioner | 3 524 | 1 635 |
| Utskottsbetänkanden och utlåtanden | 4 370 | 1 874 |
| Motioner | 9 714 | 4 790 |
| SOU (KB 1939–1999, riksdagen 1997–) | 6 353 | 1 304 |
| Ds | 304 | 64 |
| Kommittédirektiv | 315 | 142 |
| Remissvar, regeringen.se 2014– | 6 596 | 6 249 |

Sökdatabasen (`bygg_db.py`) blir ca 5,8 GB och ligger inte i git.

**Kapitelfilter** (`kapitel.py`): avsnitten i kapitlet om kreditpolitiken och
bostadsfinansieringen, med år och ämnesord. **Aktörsfilter** (`aktorer.py`):
byggföretag, fastighetsägare, allmännyttan och kooperationen, banker och andra
grupper, med historiska organisationsnamn. Stycken där en aktör redovisas ta ställning
sparas i tabellen `aktorsstycken`.

Sammanställningen *Branschen och bostadsfinansieringen* (`analys/bygg_branschen.py`,
https://claude.ai/artifact/Xw5nbx765D4mFeUeAnD4LP) visar vad byggföretagen och
fastighetsägarna anförde i remissvaren 1946–1990.

## Källor

| Källa | Vad | Period | Hur |
|---|---|---|---|
| Riksdagen, data.riksdagen.se | Kammarprotokoll | 1939– | Alla protokoll hämtas och delas upp i anföranden; anföranden om bostadsbyggandet sparas |
| Riksdagen, data.riksdagen.se | SOU | 1997– | Kandidater via riksdagens sökmotor (`katalog.SOKFRAGOR`), fulltexten bedöms |
| Riksdagen, data.riksdagen.se | Ds, kommittédirektiv | 1990– | Som SOU |
| Riksdagen, data.riksdagen.se | Propositioner, utskottsbetänkanden, motioner | 1939– | Som SOU. Äldre dokument utan titel i listan får första rubriken i texten som titel |
| Kungliga biblioteket, sou.kb.se | SOU (inskannade, OCR) | 1939–1999 | Alla SOU som riksdagen saknar hämtas som PDF och bedöms; sidnumren (PDF-sida) sparas |

Den OCR-tolkade texten före 2000-talet innehåller läsfel. Citera alltid från originalet
(länkarna till riksdagen.se och KB:s PDF finns vid varje träff).

| Regeringskansliet, regeringen.se | Remissvar (en PDF per instans) | 2014– | `hamta_remisser.py`: alla remisser inom Bostäder och samhällsplanering och bostadsrelaterade inom Finansmarknad |

## Vad räknas som bostadsbyggande

`katalog.py` har två ordlistor:

- **Kärntermer**, t.ex. *bostadsbyggande*, *bostadsproduktion*, *byggande av bostäder*,
  *bostadsförsörjning*, *bostadsbrist*, *nyproduktion av bostäder*, *räntebidrag*,
  *statliga bostadslån*, *investeringsstöd till hyresbostäder*, *byggkostnader*.
- **Breda termer** för bostads- och plansektorn, t.ex. *bostadspolitik*,
  *bostadsmarknad*, *hyresrätt*, *allmännyttan*, *plan- och bygglagen*, *detaljplan*,
  *bygglov*, *markanvisning*, *byggsektorn*, *bruksvärde*.

Urvalet görs så här:

- **Ett anförande** tas med om det har minst en kärnträff, eller minst tre breda träffar
  i två kategorier, eller om ärendets rubrik handlar om bostäder. I det sista fallet tas
  hela debatten med.
- **Ett dokument** (SOU, Ds, direktiv, proposition, betänkande) tas med om titeln träffar någon term, eller om den
  har minst fem kärnträffar, eller minst två kärnträffar och minst tre per 10 000 ord.

Varje källa får en relevansgrad (*hög*, *medel* eller *låg*) efter hur tätt kärntermerna
förekommer. Även de utredningar som inte togs med finns i `data/dokument.csv`, med antal
träffar per term, så att urvalet går att granska och ändra.

## Filer

- `data/protokoll.csv`: alla genomgångna protokoll med antal anföranden och antal relevanta
- `data/anforanden/<riksmöte>.jsonl.gz`: relevanta anföranden med talare, parti, datum,
  ärende, träffar och text
- `data/dokument.csv`: alla bedömda dokument med metadata, träffar och om de tagits med
- `data/text/<sou|ds|dir|prop|bet>/<id>.txt.gz`: fulltexten för de dokument som tagits med
- `data/hamtlogg.json`: antal och fel per körning
- `data/bostadsarkiv.sqlite`: sökdatabasen. Den byggs lokalt och ligger inte i git.

## Söksidan

Den publicerade söksidan **Bostadsarkivet** (https://claude.ai/artifact/1RQ8ZiGEsz91fNeQ8KT4wc)
är byggd som "Ohlin i kammaren": diagram per år, filter för källtyp, parti, period och
relevans, och sökning direkt i webbläsaren. Anförandena finns med i sin helhet. För
propositioner, betänkanden och utredningar visas de stycken som nämner bostadsbyggandet
(högst 30 per dokument). Sidan är `webb/index.html`, och datafilerna byggs med:

```sh
python bygg_db.py && python bygg_webb.py   # skriver webb/data/*.json (ca 65 MB, ej i git)
```

## Använda lokalt

```sh
pip install -r requirements.txt     # bara requests; pdftotext (poppler-utils) behövs för KB
python bygg_db.py                   # bygg sökdatabasen (ett par minuter)
python webb.py                      # söksida på http://localhost:8765
python sok.py 'räntebidrag*' --fran 1990 --till 1995
python sok.py '"bygga fler bostäder"' --typ prot --parti S M --datum
python sok.py 'investeringsstöd* hyres*' -n 0 --csv utdrag.csv
python sok.py --oversikt
```

Sökningen använder SQLite FTS5. Flera ord måste alla finnas, `"…"` söker en fras,
`*` söker en ordbörjan (`bostadsbygg*`), och `OR` och `NOT` fungerar. Databasen går också
att öppna direkt i SQLite, DB Browser for SQLite eller pandas. Vyn `kallor` listar alla
källor.

## Uppdatera

```sh
python hamta.py alla                 # allt som saknas, 1990 till i dag
python hamta.py protokoll --fran 2026
python hamta.py riksdagsdok --typ sou ds dir prop bet --fran 2025
python hamta.py kb                   # SOU 1990–1999 från KB
python hamta.py omvardera            # bedöm sparad text igen efter skärpt ordlista
python hamta.py protokoll --om       # hämta och bedöm om allt (efter lättad ordlista)
```

`.github/workflows/bostadsarkiv.yml` hämtar nytt material den 3:e varje månad från
förra årets början och committar `data/`. Schemalagda körningar går bara från
standardgrenen.

Ändrar du ordlistan eller reglerna i `katalog.py` påverkar det bara nya hämtningar. Har
du skärpt dem räcker `hamta.py omvardera`, som bedömer den sparade texten igen och tar
bort det som inte längre uppfyller reglerna. Har du lättat dem måste texten hämtas om med
`--om`, eftersom det som tidigare bedömdes som irrelevant aldrig sparades.

## Begränsningar

- Riksdagens sökmotor avgör vilka SOU, Ds och direktiv som bedöms. Ett dokument som
  aldrig nämner någon av sökfrågorna hittas inte. Protokollen och KB:s SOU gås däremot
  igenom i sin helhet.
- Protokollen från 1990-talet är inskannade. Talare och parti läses ur rubriken
  "Anf. 12 NAMN (parti)". Sidhuvuden tas bort men enstaka OCR-fel finns kvar.
- Motioner ingår inte. Lägg till `mot` i `--typ` och i `beteckning()` i `hamta.py` för
  att ta med dem.
- Budgetpropositionerna och finansutskottets betänkanden kommer med eftersom de
  behandlar bostadsanslagen, men de är långa. Relevansgraden (träffar per 10 000 ord)
  hjälper till att sortera fram de dokument som handlar om bostäder i första hand.
