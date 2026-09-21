import imaplib
import email
import re
import base64
from email.header import decode_header
import streamlit as st

IMAP_SERVER = "imap.mail.yahoo.com"
IMAP_PORT = 993

def get_yahoo_connection():
yahoo_email = st.secrets["YAHOO_EMAIL"]
yahoo_app_password = st.secrets["YAHOO_APP_PASSWORD"]
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(yahoo_email, yahoo_app_password)
return mail

def decode_email_subject(subject):
if not subject:
return ""
result = ""
for part, encoding in decode_header(subject):
if isinstance(part, bytes):
result += part.decode(encoding or "utf-8", errors="replace")
else:
result += part
return result

def get_email_body(message):
text_body = ""
html_body = ""

for part in message.walk():
    if part.get_content_maintype() == "multipart":
        continue

    if "attachment" in str(part.get("Content-Disposition", "")).lower():
        continue

    try:
        payload = part.get_payload(decode=True)
        if not payload:
            continue

        charset = part.get_content_charset() or "utf-8"
        contenu = payload.decode(charset, errors="replace")

        if part.get_content_type() == "text/plain":
            text_body += contenu

        if part.get_content_type() == "text/html":
            html_body += contenu

    except Exception:
        continue

return text_body, html_body

def extraire_url_bienici(url):
parties = url.rstrip("/").split("/")

if not parties:
    return None

code = parties[-1]

try:
    padding = "=" * (-len(code) % 4)
    resultat = base64.urlsafe_b64decode(code + padding).decode("utf-8")

    if resultat.startswith("http"):
        return resultat

except Exception:
    pass

return url

def extraire_liens_bienici(text_body, html_body):
contenu = html_body + "\n" + text_body

urls = re.findall(
    r'https?://link\.bienici\.com/[^\s"<>]+',
    contenu
)

resultats = []

for url in urls:
    url = url.rstrip(".,);'>\"")
    url_reelle = extraire_url_bienici(url)

    if url_reelle and "bienici.com/annonce/" in url_reelle:
        if url_reelle not in resultats:
            resultats.append(url_reelle)

return resultats

def get_bienici_emails(limit=20):
mail = get_yahoo_connection()

try:
    mail.select("INBOX", readonly=True)

    status, data = mail.search(
        None,
        '(FROM "bienici.com")'
    )

    if status != "OK":
        return []

    email_ids = data[0].split()

    if not email_ids:
        return []

    email_ids = email_ids[-limit:]
    results = []

    for email_id in reversed(email_ids):
        status, message_data = mail.fetch(
            email_id,
            "(BODY.PEEK[])"
        )

        if status != "OK":
            continue

        raw_email = None

        for response_part in message_data:
            if isinstance(response_part, tuple):
                raw_email = response_part[1]
                break

        if not raw_email:
            continue

        message = email.message_from_bytes(raw_email)

        subject = decode_email_subject(
            message.get("Subject", "")
        )

        sender = message.get("From", "")
        date = message.get("Date", "")

        text_body, html_body = get_email_body(message)

        liens = extraire_liens_bienici(
            text_body,
            html_body
        )

        results.append({
            "email_id": email_id.decode(),
            "subject": subject,
            "sender": sender,
            "date": date,
            "text_body": text_body,
            "html_body": html_body,
            "liens_annonces": liens,
            "nombre_annonces": len(liens)
        })

    return results

finally:
    mail.logout()

def get_annonces_from_bienici_emails(limit=20):
emails = get_bienici_emails(limit)
annonces = []
urls_deja_vues = set()

for email_data in emails:
    for url in email_data.get("liens_annonces", []):
        if url in urls_deja_vues:
            continue

        urls_deja_vues.add(url)

        annonces.append({
            "url": url,
            "email_id": email_data.get("email_id"),
            "subject": email_data.get("subject"),
            "date": email_data.get("date")
        })

return annonces
