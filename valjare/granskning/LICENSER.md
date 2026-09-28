# Källornas villkor och vad som behöver stämmas av

Samma uppgifter finns i `licenser.py` och på sidan under "Om databasen". Sammanställningen är inte
en juridisk bedömning; villkoren ska bekräftas mot utgivarens aktuella text innan sidan sprids.

| Källa | Status | Vad som behöver göras |
|---|---|---|
| SCB, Kolada, riksdagen, Valmyndigheten, Eurostat, Världsbanken, Riksbanken, Polisen, Brå | Öppna data | Ange källan; bekräfta villkoren via länkarna i `licenser.py` |
| SVT:s vallokalsundersökning (Valu) | Stäm av före spridning | Begär tillstånd att återpublicera tabellerna per väljargrupp 1991–2026 (utkast: `brev_svt_valu.md`) |
| Valforskningsprogrammet, GU | Stäm av före spridning | Begär tillstånd för tabellerna över partiernas väljare (utkast: `brev_valforskningsprogrammet.md`) |
| SOM-institutet, GU | Citat med källhänvisning | Informera och stäm av om sidan sprids brett (utkast: `brev_som_institutet.md`) |

Tills avstämningen är klar bör sidan hållas i en intern krets. Om tillstånd inte ges kan
tabellerna tas bort ur `bygg_db.webb()` utan att resten av databasen påverkas; den interna
SQLite-filen kan då ligga kvar för egen analys.
