# Backup: rutinen "FX & Räntor – daglig digest" (ordagrann kopia)

Kopierad 2026-09-23, innan ombyggnaden. Rutinen är **inte ändrad** — den kör vidare som vanligt tills den nya versionen är klar.

| Fält | Värde |
|---|---|
| Namn | FX & Räntor – daglig digest (ING, SEB, Sløk/Yardeni, Twelve Data) |
| Trigger-id | `trig_01TkoGSFWagxXtcuG6x5EbtH` |
| Cron (UTC) | `0 6 * * 1-5` (vardagar 08:00 svensk sommartid) |
| Aktiverad | ja |
| Skapad | 2026-09-09T11:12:49Z |
| Körs i session | `session_01E81Z4GWXyHCkYuFvhyAPwt` (persistent) |
| Senaste körning | 2026-09-23T06:15Z, lyckades |

Återställning: `update_trigger(trigger_id="trig_01TkoGSFWagxXtcuG6x5EbtH", prompt=<texten nedan>)`, eller skapa en ny rutin med samma cron och prompt.

## Prompt (ordagrann)

````text
Dags för den dagliga FX/räntor-digesten. Kör igenom hela kedjan självständigt, på svenska, utan att fråga mig om något.

1. Trigga GitHub Actions-workflowen `ing_think_digest.yml` i repot claesludvig/projekt på branchen `main`. Vänta tills den är klar (poll via GitHub API, upp till ~5 min). Hämta sedan ing-think-digest/data/latest_articles.json från main via GitHub API (url, title, published, author, fulltext, category).

2. Trigga ÄVEN workflowen `seb_research_digest.yml` i samma repo (branch main) — obligatoriskt. Vänta tills den är klar (upp till ~5 min). Hämta sedan seb-research-digest/data/latest_articles.json från main via GitHub API (url, title, heading, published, assetClass, reportType, fulltext). SEB publicerar ofta samma innehåll både som en engelsk "Nordic Alert" och en svensk "Morning Alert" samma dag — använd i så fall den svenska versionen som primärkälla. Välj ut de 2-4 mest relevanta och innehållsrika rapporterna för räntor/valutor/makro (hoppa över bildbaserade tabeller med <50 ord text).

3. Om någon av workflowarna misslyckas, skicka ändå ett kort mail till ludvig.uggla@gmail.com som förklarar vad som gick fel — men fortsätt med resten av digesten med de källor som faktiskt gick att hämta.

4. Sök i användarens Gmail (Gmail-verktyget search_threads) efter "Slok OR Sløk OR Yardeni" och hämta fulltext (get_thread, messageFormat PLAIN_TEXT) för de 1-2 senaste från vardera avsändaren (agm@apollo.com = Torsten Sløk/Apollo Daily Spark, yardeni-research@ghost.io = Ed Yardeni/Yardeni QuickTakes). Yardenis mail är ofta delvis betalspärrade — använd den fria inledningen. Om ingen ny relevant e-post hittas sedan gårdagen, nämn det kort i källistan istället för att hoppa över sektionen tyst.

5. MARKNADSÖVERSIKT (Twelve Data, live) — obligatoriskt. Twelve Data stödjer inte index direkt (S&P 500, DAX, OMXS30 etc.) utan bara aktier/ETF:er/forex/krypto, och EU-börslistade instrument (t.ex. tyska XETR-noteringar) kräver en betald plan — håll dig därför till dessa fem amerikanskt noterade ETF-proxyer som är bekräftat gratis att hämta:
   - EWD = Sverige/OMXS30-proxy (iShares MSCI Sweden ETF)
   - EWG = Tyskland/DAX-proxy (iShares MSCI Germany ETF)
   - FEZ = Euro Stoxx 50-proxy (SPDR EURO STOXX 50 ETF)
   - SPY = S&P 500-proxy
   - QQQ = Nasdaq 100-proxy

   Anropa Twelve Data-verktyget get_time_series EN gång per symbol (interval=1day, outputsize=55) — INTE get_quote eller get_technical_indicator separat, det slösar onödiga API-anrop. Free-tier-gränsen är 8 credits/minut (utöver 800/dag), så fem anrop i följd är säkert men gör dem inte i större batchar. Ur varje svar (nyaste rad först):
   - Senast = close på rad 1. Dag % = (close rad 1 − close rad 2) / close rad 2 × 100.
   - MA20 = medelvärdet av de 20 senaste close-värdena (rad 1–20).
   - MA50 = medelvärdet av de 50 senaste close-värdena (rad 1–50).
   - Trendstyrka % = (MA20 − MA50) / MA50 × 100.
   Rangordna alla fem fallande efter trendstyrka. ANVÄND ALLTID DE FAKTISKA SIFFRORNA FRÅN VERKTYGET, gissa aldrig. Om ett anrop misslyckas (t.ex. rate limit), vänta en minut och försök igen en gång; lyckas det ändå inte, skriv det i den punkten istället för att hitta på siffror.

6. SKRIV RAPPORTEN I SAMMA STIL OCH FORMAT SOM PODDRAPPORTERNA (Iran/Ukraine/Bloomberg-poddarna) — inte den gamla 8-sektionersmallen. Reglerna:
   - Saklig analysprosa, inga floskler ("sammanfattningsvis", "det är värt att notera", "i en värld där"), ingen dramatisering.
   - Skriv ut konkreta siffror, nivåer, namn och datum ur källorna. Gissa aldrig — är något oklart, säg det.
   - Fokusera på vad som är NYTT i dagens källor, inte ett referat av allmänt kända fakta.
   - Väv ihop ING, SEB, Sløk/Yardeni och marknadsöversikten till EN sammanhängande bild av dagens huvudnarrativ i analysis_paragraphs (ett till två stycken totalt, inte ett per källa).
   - key_developments: minst fyra punkter, varje med en kort bold_lead-etikett och en text. En av punkterna ska vara marknadsöversiktens trendrankning skriven ut som text (instrument, senast, dag %, trendstyrka % för alla fem, rangordnade), inte en HTML-tabell.
   - Texten ska vara klart kortare än den gamla mallen — sikta på ungefär poddrapporternas längd (två korta stycken + 4-6 punkter), inte åtta sektioner.
   JSON-formen (samma som poddrapporterna):
   {
     "title": "Kort, konkret rubrik på svenska som fångar dagens huvudnarrativ",
     "analysis_paragraphs": ["Stycke ett.", "Stycke två."],
     "key_developments": [{"bold_lead": "Kort etikett", "text": "Vad som hänt, med siffror."}]
   }

7. Rendera med EXAKT denna HTML-mall (samma som poddrapporterna, byt ut platshållarna, behåll all styling oförändrad, riktig HTML med bokstavliga <, >, " — aldrig HTML-entities):

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
</head>
<body style="background-color: #f4f6f8; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0;">
  <div style="background-color: #f4f6f8; padding: 40px 20px;">
    <div style="background-color: #ffffff; max-width: 600px; margin: 0 auto; border-radius: 8px; border-top: 6px solid #1a365d; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); overflow: hidden;">
      <div style="padding: 35px 40px;">
        <h1 style="color: #1a365d; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; margin: 0 0 10px 0; text-transform: uppercase;">
          [RUBRIK]
        </h1>
        <div style="color: #718096; font-size: 14px; font-style: italic; margin: 0 0 25px 0;">
          FX &amp; räntor — marknadspulsen [DAGENS DATUM]
        </div>
        [ETT &lt;p style="color: #2d3748; font-size: 15px; line-height: 1.6; margin: 0 0 20px 0;"&gt;-stycke PER ANALYSSTYCKE]
        <h2 style="color: #1a365d; font-size: 17px; font-weight: 700; margin: 30px 0 15px 0; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px;">
          Viktigaste händelserna idag
        </h2>
        <ul style="margin: 0 0 20px 0; padding-left: 20px;">
          [EN &lt;li style="color: #2d3748; font-size: 15px; line-height: 1.6; margin-bottom: 12px;"&gt;&lt;strong style="color: #1a365d;"&gt;[BOLD_LEAD]:&lt;/strong&gt; [TEXT]&lt;/li&gt; PER PUNKT]
        </ul>
        <div style="margin-top: 40px; border-top: 1px solid #f0f4f8; padding-top: 15px; font-size: 12px; color: #a0aec0; text-align: center;">
          Denna rapport har genererats automatiskt av din personliga nyhetsbevakare.
        </div>
      </div>
    </div>
  </div>
</body>
</html>

8. Skicka mailet via Gmail (send_message, INTE draft) till ludvig.uggla@gmail.com. Ämne: "FX & Räntor – marknadspulsen (dagens datum)". htmlBody = mallen ovan. Ingen separat textversion behövs — samma som poddrapporterna.

9. Klart — avsluta efter att mailet är skickat, ingen vidare interaktion behövs. Svara kort i chatten (1 mening) att mailet skickats.
````
