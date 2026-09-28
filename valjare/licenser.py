"""Villkor för att använda och återpublicera varje källa.

status:
  oppen     öppna data som får återanvändas med källhänvisning enligt utgivarens villkor
  citat     publicerade rapporter; enstaka uppgifter får citeras med källhänvisning, men
            systematisk återpublicering av tabeller bör stämmas av med utgivaren
  avstamning  tabellerna återpubliceras i databasen och på sidan; tillstånd bör begäras
              innan sidan sprids utanför en intern krets (utkast till förfrågan i granskning/)

Villkoren ska bekräftas mot utgivarens aktuella text (länken) innan publicering.
Uppgifterna här är en sammanställning, inte en juridisk bedömning.
"""

LICENSER = [
    # (källa, utgivare, status, villkor i korthet, länk till villkoren)
    ("SCB, Statistikdatabasen och DeSO", "Statistiska centralbyrån", "oppen",
     "Öppna data; ange SCB som källa.", "https://www.scb.se/vara-tjanster/oppna-data/"),
    ("Kolada", "RKA", "oppen", "Öppna data via Koladas API; ange Kolada/RKA som källa.",
     "https://www.kolada.se/"),
    ("Riksdagens öppna data", "Sveriges riksdag", "oppen", "Öppna data; ange riksdagen som källa.",
     "https://data.riksdagen.se/"),
    ("Valmyndighetens rådata", "Valmyndigheten", "oppen", "Öppna data om val; ange Valmyndigheten som källa.",
     "https://www.val.se/valresultat-och-statistik/statistik-och-data.html"),
    ("Eurostat", "Europeiska kommissionen", "oppen",
     "Fri återanvändning med källhänvisning (kommissionens beslut 2011/833/EU).",
     "https://ec.europa.eu/eurostat/about-us/policies/copyright"),
    ("Världsbanken (SIPRI:s militärutgifter m.m.)", "Världsbanken", "oppen", "CC BY 4.0; ange källan.",
     "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets"),
    ("Riksbankens SWEA-API", "Sveriges riksbank", "oppen", "Öppna data; ange Riksbanken som källa.",
     "https://www.riksbank.se/sv/statistik/"),
    ("Polisens statistik över skjutningar och sprängningar", "Polismyndigheten", "oppen",
     "Offentlig statistik i pdf; ange Polismyndigheten som källa.",
     "https://polisen.se/om-polisen/polisens-arbete/sprangningar-och-skjutningar/"),
    ("Nationella trygghetsundersökningen", "Brå", "oppen", "Officiell statistik; ange Brå som källa.",
     "https://bra.se/statistik"),
    ("SVT:s vallokalsundersökning (Valu)", "SVT", "avstamning",
     "Rapporterna är upphovsrättsskyddade. Databasen återpublicerar tabeller per väljargrupp 1991–2026; "
     "begär tillstånd innan sidan sprids.", "https://omoss.svt.se/"),
    ("Valforskningsprogrammet (Svenska väljare, rapport 2026:7 m.fl.)", "Göteborgs universitet", "avstamning",
     "Rapporter med källhänvisning; databasen återpublicerar tabeller över partiernas väljare. "
     "Stäm av med programmet.", "https://www.gu.se/valforskningsprogrammet"),
    ("SOM-institutet, Svenska trender", "Göteborgs universitet", "citat",
     "Enstaka värden citeras med källhänvisning (viktigaste samhällsproblem, förslag, förtroende). "
     "Stäm av om sidan sprids brett.", "https://www.gu.se/som-institutet"),
]

STATUS_TEXT = {"oppen": "Öppna data", "citat": "Citat med källhänvisning", "avstamning": "Stäm av före spridning"}
