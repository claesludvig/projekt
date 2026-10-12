# Partiernas bostadspolitik

Riksdagspartiernas positioner i bostadspolitiken och hur de flyttats över tid: partiprogram,
valmanifest, sakpolitiska överenskommelser, regeringsförklaringar, partiernas egna bostadsmotioner,
partiernas webbplatser och medial rapportering, uppdelat på bostadspolitiska frågor och valperioder.
Kompletterar Bostadsarkivet (riksdagens protokoll och tryck 1939–) och Bostadsrapporterna
(intresseorganisationernas rapporter).

Sökgränssnitt: https://claude.ai/artifact/GZGP68B8YzayoEZw1yUV3X (privat).

## Källor

| Källa | Skript | Omfång |
|---|---|---|
| SND, *Svenska partiprogram och valmanifest* (Vivill), CC BY 4.0 | `vivill.py` | 349 dokument 1887–2026: valmanifest, parti-, princip-, idé- och handlingsprogram för S, M, C, FP/L, KD, V, MP, SD, NyD, Alliansen och De rödgröna. Text och PDF |
| Överenskommelser (`overenskommelser.txt`) | `dokument.py avtal` | Decemberöverenskommelsen, Januariavtalet med L:s faktapromemoria, Tidöavtalet, regeringens bokslut över Tidöavtalet |
| Regeringsförklaringar | `dokument.py regdekl` | 1994–2025 från regeringen.se och riksdagens protokoll (2016 och sept. 2021 saknas) |
| Partiernas bostadsmotioner | `dokument.py motioner` | Kommitté- och partimotioner till bostads- och civilutskottet, och motioner om bostäder i andra utskott, 2000/01– |
| Partiernas webbplatser i dag | `partisajter.py` | Sidor och PDF:er om bostäder från S, M, C, L, KD, MP och SD (V spärrar automatisk hämtning) |
| Partiernas webbplatser förr | `wayback.py` | Arkivkopior per år ur Internet Archive. **Wayback Machine svarade inte under insamlingen**; skriptet går långsamt och kan köras igen |
| Medier | `media.py` | Aftonbladet, Expressen, DN, SvD och Omni via månadssitemaps (adresser om bostadspolitik), Hem & Hyra, Fastighetstidningen och Byggvärlden via WordPress-sök, Google Nyheter för de senaste månaderna |

## Frågor

`FRAGOR` i `katalog.py`: hyressättning och marknadshyror, allmännyttan, statligt stöd till byggande,
bostadsbeskattning, bolån och kreditregler, planering och byggregler, bostadsbidrag och sociala
bostäder, byggandets omfattning, renovering, upplåtelseformer, segregation. Ett stycke märks med en
fråga när det innehåller frågans ord. Märkningen visar vad partiet tar upp, inte vad det tycker.

**Fokus** (tabellen `fokus` och matrisen i gränssnittet): promille av orden i partiets valmanifest
och program som står i stycken om frågan. Ett mått på hur viktig frågan är för partiet vid varje val.

## Databasen

- `data/partipositioner_publik.sqlite.gz` – i git. Allt utom medieartiklarnas brödtext (bara rubrik).
- `data/partipositioner.sqlite` – lokalt, med medietexterna. Byggs av `python bygg.py`.

Tabeller: `dokument` (slag, partier, år, titel, länkar, frågor, hela texten), `stycke` (stycken om
bostäder med frågor och nämnda partier), `stycke_fts` (FTS5), `fokus`, `parti`, `fraga`.

```sql
-- Hur har partierna formulerat sig om marknadshyror i sina valmanifest?
SELECT d.ar, d.partier, s.text
FROM stycke_fts JOIN stycke s ON s.rowid = stycke_fts.rowid JOIN dokument d ON d.id = s.dok
WHERE stycke_fts MATCH 'marknadshyr*' AND d.slag = 'valmanifest' ORDER BY d.ar;

-- Hur stor plats har hyresfrågan fått i varje partis valmanifest?
SELECT parti, ar, hyra FROM fokus WHERE slag = 'valmanifest' AND ar >= 1990 ORDER BY parti, ar;
```

## Körning

```bash
python vivill.py
python dokument.py               # avtal, regdekl, motioner
python partisajter.py
python media.py                  # sitemaps, wp, gnews, artiklar
python wayback.py                # långsamt; försöker igen om arkivet inte svarar
python bygg.py
```

## Begränsningar

- Riksdagsmotionerna före 2000 är inte märkta som parti- eller kommittémotioner i riksdagens API och
  ingår inte här. De finns i Bostadsarkivet.
- Moderaternas valmanifest 2006 och 2014 finns som Alliansens gemensamma.
- Medieurvalet bygger på ord i artiklarnas adresser och missar artiklar med andra rubriker. Artiklar
  bakom betalvägg (DN, SvD) har ofta bara rubrik och ingress. Medietexterna checkas inte in.
- Vänsterpartiets webbplats spärrar automatiska hämtningar. V:s positioner finns i valmanifest,
  program och motioner.
