# Bostadsarkivet

En sökbar samling av källmaterial om bostadsbyggandet i Sverige 1990 till i dag:
riksdagens kammarprotokoll (per anförande), propositioner, utskottsbetänkanden och
statliga utredningar (SOU, Ds och kommittédirektiv) i fulltext.

## Källor

| Källa | Vad | Period | Hur |
|---|---|---|---|
| Riksdagen, data.riksdagen.se | Kammarprotokoll | 1990– | Alla protokoll hämtas och delas upp i anföranden; anföranden om bostadsbyggandet sparas |
| Riksdagen, data.riksdagen.se | SOU | 1997– | Kandidater via riksdagens sökmotor (`katalog.SOKFRAGOR`), fulltexten bedöms |
| Riksdagen, data.riksdagen.se | Ds, kommittédirektiv | 1990– | Som SOU |
| Riksdagen, data.riksdagen.se | Propositioner, utskottsbetänkanden | 1990– | Som SOU. Äldre dokument utan titel i listan får första rubriken i texten som titel |
| Kungliga biblioteket, sou.kb.se | SOU (inskannade, OCR) | 1990–1999 | Alla SOU som riksdagen saknar hämtas som PDF och bedöms; sidnumren (PDF-sida) sparas |

KB:s OCR-text från 1990-talet innehåller läsfel. Citera alltid från originalet
(länkarna till riksdagen.se och KB:s PDF finns vid varje träff).

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

## Använda

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
python hamta.py protokoll --om       # gör om (t.ex. efter ändrad ordlista)
```

`.github/workflows/bostadsarkiv.yml` hämtar nytt material den 3:e varje månad från
förra årets början och committar `data/`. Schemalagda körningar går bara från
standardgrenen.

Ändrar du ordlistan eller reglerna i `katalog.py` påverkar det bara nya hämtningar. Kör
med `--om` för att bedöma om det som redan hämtats.

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
