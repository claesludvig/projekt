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
