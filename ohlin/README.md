# Ohlin i kammaren

Ett sökbart register över Bertil Ohlins inlägg i riksdagens första och andra kammare
1938–1970, hämtade ur riksdagens digitaliserade protokoll ([data.riksdagen.se](https://data.riksdagen.se)).

- **1 890 inlägg**: 1 124 anföranden och 766 korta genmälen, sammanlagt cirka 1,9 miljoner ord.
- Inläggen kommer ur **513 protokoll**. Totalt har 1 351 protokoll som nämner Ohlin genomsökts.
- Ohlin satt i första kammaren 1938–1944 och i andra kammaren 1945–1970.

## Så körs det

```
python3 hamta.py        # listar och laddar ner protokollen (ca 1,7 GB i data/kallor, ignoreras av git)
python3 extrahera.py    # plockar ut Ohlins inlägg -> data/inlagg.json, data/inlagg.csv
python3 bygg_sida.py    # skriver data/inlagg-webb.json som index.html läser in
python3 -m http.server  # öppna sedan http://localhost:8000/index.html
```

`hamta.py` kräver att miljön når `data.riksdagen.se`.

## Metod och begränsningar

- Riksdagens API ger alla protokoll där ordet "Ohlin" förekommer. Ett inlägg räknas från talarraden
  ("Herr OHLIN (fp):", "Herr Ohlin: Herr talman!" och liknande) till nästa talarrad, en ny
  paragraf eller en rad som avslutar överläggningen.
- Texten är riksdagens OCR-tolkning av de tryckta protokollen. Den innehåller läsfel, och
  talarrader som har lästs fel kan göra att ett inlägg missas eller blir för långt. Citera
  därför från originalet, som länkas vid varje inlägg.
- Ärenderubriken är den närmast föregående paragrafen i protokollet och är ungefärlig.
- Temana sätts med nyckelord (`TEMAN` i `extrahera.py`) och är bara en grov sortering.
- `data/inlagg.csv` har en rad per inlägg med metadata och de första 60 orden. Den passar för
  kalkylblad. Fulltexten finns i `data/inlagg.json`.
