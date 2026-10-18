# Sellpy-sök och annonsbevakning

Sellpy söker via Algolia med en publik söknyckel som ligger i deras egen frontend. Samma
index går att fråga direkt, och då kommer man åt all strukturerad metadata — även sådant
sajten inte låter en filtrera på, som **mått i cm** (midja, innerben, längd, bredd, klackhöjd),
material, mönster, midjehöjd och publiceringsdatum.

## Söksida — `index.html`

Öppna `sellpy/index.html` (eller https://ckhold.se/sellpy/). Fritext, sortering, pris,
datum, kryssfilter med antal per värde (flerval inom ett filter) och måttintervall.
Sökningen ligger i adressfältet, så den går att bokmärka. **Spara som bevakning** ger en
JSON-rad att klistra in i `bevakningar.json`.

## Kommandorad — `sellpy.py` (bara standardbiblioteket)

```sh
python sellpy.py sok "501" --marke "Levi Strauss & Co" --kon Man --matt waistInCm=80-86 --max-pris 300
python sellpy.py sok --kategori "Man > Kläder > Byxor & Jeans > Jeans" --midjehojd Hög --sortera billigast
python sellpy.py sok "ullkappa" --material Ull --skick Nytt --skick "Mycket bra" --dagar 3 --json
python sellpy.py facetter "kånken"     # vilka värden (märken, storlekar, mått…) finns att filtrera på
python sellpy.py bevaka                # kör alla bevakningar
```

Filter: `--marke --typ --storlek --skick --farg --material --monster --kon --kategori
--langd --midjehojd --stil` (upprepa för ELLER), `--min-pris --max-pris` (kr),
`--matt NAMN=MIN-MAX` (cm; `waistInCm`, `innerLegLengthInCm`, `lengthInCm`, `widthInCm`,
`heightInCm`, `heelHeightInCm`), `--dagar N`, `--sortera nyast|relevans|billigast|dyrast`.
Storlekar heter som i Sellpys data, t.ex. `PANTS-INCH-32`, `MEN-INT-M`, `SHOES-EU-43` —
`facetter` visar vilka som finns.

## Bevakning — `bevakningar.json`

En lista sökningar med samma nycklar som filtren ovan (`fraga`, `marke`, `matt`, `max_pris`
…) plus `namn`, och valfritt `"aktiv": false`. GitHub Actions (`sellpy_bevakning.yml`) kör
dem varannan timme. Nya annonser och prissänkningar på redan sedda skrivs till
`data/nya.md`/`data/nya.json`, och vid nyheter skapas ett **GitHub-issue** — så notisen
kommer via mejl eller GitHub-appen. Första körningen för en ny bevakning registrerar bara
befintliga annonser. Sedda annonser glöms efter 30 dagar utan träff.
