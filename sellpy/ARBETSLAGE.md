# Sellpy – arbetsläge och Ludvigs preferenser

Läs den här filen först när Ludvig vill fortsätta leta kläder på Sellpy. Verktyget
(`sellpy.py`, `index.html`) beskrivs i `README.md`.

## Hur sökningen görs (det som fungerade)

1. **Hämta brett via Algolia** med `sellpy.algolia(...)` och facetFilters – flera fritextfrågor
   (t.ex. "flanell", "borstad", "ull") och slå ihop på `objectID`, eftersom fritexten är luddig.
2. **Poängsätt på `keywords`, `metadata.*` och `materials`** (Sellpys AI-taggning). Plus för rätt
   tyg/stil, minus för det han inte vill ha (listor nedan), justera för skick och pris.
3. **Granska alltid bilderna** innan något rekommenderas: ladda `images[0]`, gör ett kontaktark
   med helbild + närbild på krage/tyg (PIL), och titta. Taggarna ljuger ofta – button down,
   glans, lockfickor, färgton (tan vs benvit) syns bara på bild.
4. Svara med **fullständiga länkar** `https://www.sellpy.se/item/<id>`, pris, storlek, skick,
   och några egna toppval. Säg ärligt när det inte finns tillräckligt.

Fallgropar: "ull" är en delsträng av "bomull" (matcha med ordgräns); "text" träffar
"texturerad"; `metadata.brand` kan saknas; färgen `Beige` spänner från benvit till tan.

## Nyttiga fält

- Snabb leverans = `storageSite:J` (Sverige). `--snabb` i CLI, kryssruta på söksidan.
  Allt i ordern måste vara märkt snabb leverans för att det ska gälla. Inte garanterat "idag".
- Pris: `price_SE.amount` i öre. Alltid `price_SE.amount>0` (annars ej till salu).
- Storlekar: `MEN-INT-M`, `MEN-INT-L`, `MEN-INT-M/L` osv. Typer: `metadata.type`
  (Skjorta, Buttondown-skjorta, Flanellskjorta, Överskjorta, Kofta, Kavaj, Tröja, Pikétröja,
  Farfarströja, Långärmad t-shirt …). Tyg: `metadata.fabric` (Flanell, Manchester, Finstickad …).

## Ludvigs stil och krav (hösten 2026)

**Helhet:** höstigt, 1920-talsinspirerat, nedskalat, enfärgat. Ska passa till hans **bruna
byxor i flanell/bomull**. Gärna under kavaj. Billigt (riktmärke ≤ 50–60 kr, koftor/kavajer ≤ 90)
och gärna **snabb leverans**.

**Storlek:** Uniqlo och These Glory Days krymper → **bara L**. Övriga märken M eller L.

**Skjortor:**
- Mjukt, varmt, stabilt tyg: flanell, borstad bomull, moleskin, ull, kraftig twill.
- **Inte:** oxford (för styvt/kallt), linne/sommartyg, poplin, glansiga kostymskjortor,
  strykfritt, slim fit, kortärmat, rutigt/randigt.
- **Vanlig nedvikt krage** – inte bandkrage/mandarin. Helst **inte button down**
  (accepterade det undantagsvis för These Glory Days).
- **Ska gå under kavaj:** inga överskjortor/skjortjackor, inga lockfickor eller epåletter.
- **Manchester: skippa** (ville först ha det, valde sedan bort).
- Vita/ljusa: "har tillräckligt med vita nu". Andra färger som funkar: grått, marinblått,
  skogsgrönt, oliv, vinrött.

**Tröjor m.m.:**
- Tjockare långärmade t-shirts, stickade tröjor (ull/merino/lammull), koftor.
- **Farfarströja måste ha krage** → långärmad stickad piké med knappslå.
- Koftor gärna **kavajliknande**: sjalkrage, reverskrage, fickor, armbågslappar, mjuka
  jersey-/stickade kavajer.
- **Inga kamelfärgade tröjor.** Inga loggor/tryck, inget sportigt, ingen dragkedja/huva.

## Tidigare favoriter (kan vara sålda)

- Skjortor, snabb leverans: These Glory Days ljusgrå borstad flanell, L, 60 kr (`RIk1UIzBMF`);
  S.C.W koksgrå flanell vanlig krage, L, 35 kr (`EcH7kODsAW`).
- Piké med krage: Abrams koksgrå 100 % ull, L, 55 kr (`aCvdRzSjWC`); GANT vinröd merino (`A0k3QkeZXt`).
- Koftor: Dobber sjalkrage ull/bomull, L, 50 kr (`x33Tspfy7c`); !Solid armbågslappar (`F9JRKhAe3U`).
