#!/usr/bin/env python3
"""Skickar utskicket som mejl via Gmails SMTP.

Avsändare och mottagare är samma adress: utskicket går från din Gmail till
din Gmail. Inga uppgifter ligger i koden - de läses ur miljön och sätts som
GitHub-secrets på repot:

    GMAIL_USER           din Gmail-adress
    GMAIL_APP_PASSWORD   app-lösenord (16 tecken) från Googles kontoinställningar
    DIGEST_TO            valfri; annan mottagare än avsändaren

Ett app-lösenord krävs eftersom Google inte tillåter vanlig
lösenordsinloggning mot SMTP. Det skapas under Google-kontot ->
Säkerhet -> Tvåstegsverifiering -> App-lösenord, och kan återkallas separat
utan att kontots huvudlösenord ändras.

Saknas uppgifterna hoppar skriptet över sändningen och avslutas utan fel, så
att hämtningen fungerar även innan secrets är på plats.
"""

import os
import smtplib
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_email import DATA, render  # noqa: E402

SMTP_VARD = "smtp.gmail.com"
SMTP_PORT = 465  # implicit TLS


def plain_text(data: dict) -> str:
    """Enkel textversion för klienter som inte visar HTML."""
    rader = [
        "Svensk politik och regeringsförhandlingarna",
        f"{data.get('fetched_at','')[:10]} · {data.get('new_count',0)} nya poster",
        "",
    ]
    for a in data.get("articles", []):
        meta = " · ".join(x for x in [a.get("source"), a.get("published"), a.get("author")] if x)
        if a.get("commentator"):
            meta += " [kommentator]"
        rader += [a.get("title", ""), meta, a.get("summary", ""), a.get("url", ""), ""]
    return "\n".join(rader)


def main() -> int:
    import json

    anvandare = os.environ.get("GMAIL_USER", "").strip()
    losen = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    if not anvandare or not losen:
        print("GMAIL_USER/GMAIL_APP_PASSWORD saknas - hoppar över mejlutskicket.")
        return 0

    if not DATA.exists():
        print("saknar data/latest_articles.json - inget att skicka.", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))

    if not data.get("articles"):
        # Workflowet kallar bara hit när något är nytt, men dubbelkolla ändå:
        # ett tomt utskick är brus i inkorgen.
        print("Inga nya poster - skickar inget mejl.")
        return 0

    amne, html_kropp = render(data)
    mottagare = os.environ.get("DIGEST_TO", "").strip() or anvandare

    msg = EmailMessage()
    msg["Subject"] = amne
    msg["From"] = formataddr(("Politikdigest", anvandare))
    msg["To"] = mottagare
    msg.set_content(plain_text(data))
    msg.add_alternative(html_kropp, subtype="html")

    with smtplib.SMTP_SSL(SMTP_VARD, SMTP_PORT, timeout=30) as smtp:
        smtp.login(anvandare, losen)
        smtp.send_message(msg)

    print(f"Skickade {data.get('new_count', 0)} poster till {mottagare}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
