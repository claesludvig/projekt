# Bolån, räntebindning och realekonomin

`python hamta.py` hämtar SCB (PxWebApi v2) + Riksbankens styrränta till `data/*.csv`.
`python analys.py` skattar sambanden och skriver `data/resultat.json` och `grafer/*.png`.

| Fil | SCB-tabell | Innehåll |
|---|---|---|
| hushall_lan_rantebindning.csv | TAB1538 | Hushållens lån hos MFI, ursprunglig/återstående bindning (mnkr) |
| bolan_rantebindning.csv | TAB2811 | Bolån hos MFI efter ursprunglig bindning (mnkr) |
| bolanerantor.csv | TAB5783 | Bolåneräntor nya/utestående per bindningstid (%) |
| fastpi_smahus.csv | TAB1150 | Fastighetsprisindex småhus, kvartal |
| bygglov.csv | TAB2534 | Bygglov nybyggnad, lägenheter, kvartal |
| paborjade.csv | TAB4572 | Påbörjade/färdigställda lägenheter, kvartal |
| konsumtion_manad_coicop.csv | TAB6932 | Konsumtionsindikator per COICOP, månad, säsongrensad fasta priser |
| konsumtion_vecka_coicop.csv | TAB6930 | Samma, vecka |
| konsumtion_nr_kvartal.csv | TAB6331 | NR hushållskonsumtion per COICOP, kvartal |

OBS: TAB1538 har felaktiga värden i *återstående* bindningstid 2025-05–2026-05 (negativa belopp); de maskas i analysen.

## Strukturmodell (`python modell.py`)

Kvartal 2006–2026. Resultat i `data/modell_resultat.json`, graf `grafer/5_modell_simulering.png`.

1. **Genomslag** – identitet `r = s·r_rörl + (1−s)·r_bunden`; rörliga följer styrräntan, bundna omsätts med takten μ per kvartal mot nya bundna räntor.
2. **Bostadspriser** – felkorrigering mot `ln(P/KPIF) − ln(Y) = α − β·r` (pris/inkomst beror på räntan).
3. **Utbud** – Tobins q: `ln påbörjade = η·ln(P/byggkostnad)_{t−2} + ζ·r_{t−2} + trend`.
4. **Konsumtion** – `Δ4 ln C = b·Δ4 y + γ·Δ4(ränteutgift/inkomst)_{t−1} + δ·Δ4 p_{t−2}` (kassaflöde vs förmögenhet).
5. **Identitet** – bestånd = bestånd + färdigställda; färdigställda ≈ 0,87·påbörjade 7 kv tidigare.

Simulering: +1 pe permanent styrränta med andel rörligt 42 % (2022) resp. 78 % (2026).

## Huspris-ECM enligt Riksbanken/Riksgälden (`python prismodell.py`)

Replikerar felkorrigeringsmodellen i Riksbankens bostadsutredning (2011) och Riksgälden (Bjellerup & Majtorp 2019):
långsikt med dynamisk OLS `hp* = α + β_y·di − β_r·ir − γ·D_LTV`, kortsikt med general-to-specific.
Tre varianter: Riksgäldens definition (realränta efter skatt, bakåtblickande KPIF) t.o.m. 2019 respektive hela urvalet,
samt realränta med förväntad inflation = inflationsmålet (huvudvariant). Resultat i `data/prismodell_resultat.json`.

## SVAR över delperioder à la Riksbanken (`python hamta_svar.py && python svar.py`)

Replikering av Stockhammar, Strid & Tornese (2022, EK nr 9). BVAR(4) med Minnesota-prior (dummyobservationer),
sju svenska variabler i Cholesky-ordning (KPIF, konsumtion, BNP, reala skulder, reala huspriser, styrränta, real växelkurs),
euroområdet som exogent omvärldsblock. 77 delperioder 1997–2019 (expanderande slut / krympande start).
`LAM=0.5 SUF=_lam05 python svar.py` kör med lösare prior. Resultat i `data/svar_resultat*.json`, `grafer/7_svar_delperioder*.png`.
