import imaplib
import email
from email.header import decode_header
import streamlit as st


IMAP_SERVER = "imap.mail.yahoo.com"
IMAP_PORT = 993


def get_yahoo_connection():
    """
    Ouvre une connexion sécurisée à Yahoo Mail avec
    le mot de passe d'application stocké dans Streamlit Secrets.
    """

    yahoo_email = st.secrets["YAHOO_EMAIL"]
    yahoo_app_password = st.secrets["YAHOO_APP_PASSWORD"]

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)

    mail.login(yahoo_email, yahoo_app_password)

    return mail


def decode_email_subject(subject):
    """
    Décode correctement l'objet d'un email,
    notamment les accents français.
    """

    if not subject:
        return ""

    decoded_parts = decode_header(subject)
    result = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="replace")
        else:
            result += part

    return result


def get_email_body(message):
    """
    Récupère le contenu texte et HTML d'un email.
    """

    text_body = ""
    html_body = ""

    if message.is_multipart():

        for part in message.walk():

            content_type = part.get_content_type()
            content_disposition = str(
                part.get("Content-Disposition", "")
            )

            if "attachment" in content_disposition.lower():
                continue

            try:
                payload = part.get_payload(decode=True)

                if payload is None:
                    continue

                charset = part.get_content_charset() or "utf-8"

                decoded_payload = payload.decode(
                    charset,
                    errors="replace"
                )

            except Exception:
                continue

            if content_type == "text/plain":
                text_body += decoded_payload

            elif content_type == "text/html":
                html_body += decoded_payload

    else:

        try:
            payload = message.get_payload(decode=True)

            if payload:

                charset = message.get_content_charset() or "utf-8"

                decoded_payload = payload.decode(
                    charset,
                    errors="replace"
                )

                if message.get_content_type() == "text/html":
                    html_body = decoded_payload
                else:
                    text_body = decoded_payload

        except Exception:
            pass

    return text_body, html_body


def get_bienici_emails(limit=20):
    """
    Recherche les derniers emails Bien'ici.

    La boîte est ouverte en lecture seule :
    aucun email n'est supprimé, déplacé ou marqué comme lu.
    """

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

            results.append(
                {
                    "email_id": email_id.decode(),
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                    "text_body": text_body,
                    "html_body": html_body,
                }
            )

        return results

    finally:

        try:
            mail.logout()
        except Exception:
            pass
