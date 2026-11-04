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
