# Hur träffsäker är kopplingen mellan riksdagens dokument och sakfrågorna?

Propositioner klassas till sakfrågor med ord i rubriken (`riksdag_katalog.ORD`), och
budgetpropositionens utgiftsområden med en fast tabell (`UTGIFTSOMRADE`). Klassningen avgör vilka
beslut som visas under varje sakfråga och vilka som ställs mot SOM-förslagen, så den har prövats
mot handkodade urval.

## Metod

1. **Utvecklingsurval:** 200 slumpvis dragna propositioner 2018/19–2025/26 (utan regeringens
   skrivelser), kodade för hand efter vilken sakfråga de i sak handlar om
   (`klassning_facit.csv`). 59 av dem hör inte till någon av sakfrågorna (finansmarknad,
   transporter, kultur m.m.) och ska inte klassas.
2. Reglerna justerades mot felen i utvecklingsurvalet: budgetpropositionens utgiftsområden fick en
   egen tabell, för breda ord snävades in ("byggande" träffade "förebyggande", "utbildning"
   träffade "polisutbildning") och saknade ord lades till.
3. **Testurval:** 100 nya propositioner, dragna efter justeringen och kodade utan att se
   klassningens svar (`klassning_facit_test.csv`).

## Resultat

| | Precision | Täckning | F1 | Helt rätt |
|---|---|---|---|---|
| Gamla reglerna, testurvalet | 0,76 | 0,67 | 0,71 | 65 % |
| **Nya reglerna, testurvalet** | **0,84** | **0,83** | **0,83** | **77 %** |
| Nya reglerna, utvecklingsurvalet (överskattat) | 0,93 | 1,00 | 0,96 | 94 % |

Precision: andelen av de tilldelade sakfrågorna som är rätt. Täckning: andelen av de rätta
sakfrågorna som hittas. Testurvalets siffror är mätta innan tre uppenbara fel som testet avslöjade
rättades ("lss" träffade "vägtullssystem", "pension" träffade "pensionatsrörelser" och
"konsument" räknades som hushållens ekonomi); efter rättelsen är F1 0,86, men den siffran är
inte längre oberoende.

## Kvarstående svagheter

- Sakfrågor som sällan står i rubriken missas oftare: lag och ordning (täckning 0,77 i testet,
  t.ex. "fordonsmålvakter", "stöldgods"), miljö och sjukvård (0,60).
- Handkodningen är gjord av en person. En andra, oberoende kodare skulle visa hur samstämmig
  kodningen är.
- Urvalen är för små för säkra siffror per sakfråga; totalsiffrorna är stabilare.

Testet `tests/test_tolkning.py::test_klassning_mot_handkodat_facit` stoppar körningen om
klassningen blir sämre än så här.
