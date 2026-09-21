import imaplib
import email
import re
import base64

from email.header import decode_header

import streamlit as st

IMAP_SERVER = "imap.mail.yahoo.com"
IMAP_PORT = 993

# ============================================================

# CONNEXION YAHOO

# ============================================================

def get_yahoo_connection():
"""
Ouvre une connexion sécurisée à Yahoo Mail.
"""

```
yahoo_email = st.secrets["YAHOO_EMAIL"]
yahoo_app_password = st.secrets["YAHOO_APP_PASSWORD"]

mail = imaplib.IMAP4_SSL(
    IMAP_SERVER,
    IMAP_PORT
)

mail.login(
    yahoo_email,
    yahoo_app_password
)

return mail
```

# ============================================================

# DECODE OBJET EMAIL

# ============================================================

def decode_email_subject(subject):
"""
Décode correctement l'objet d'un email.
"""

```
if not subject:
    return ""

decoded_parts = decode_header(subject)

result = ""

for part, encoding in decoded_parts:

    if isinstance(part, bytes):

        result += part.decode(
            encoding or "utf-8",
            errors="replace"
        )

    else:

        result += part

return result
```

# ============================================================

# RECUPERATION DU CONTENU EMAIL

# ============================================================

def get_email_body(message):
"""
Récupère le contenu texte et HTML d'un email.
"""

```
text_body = ""
html_body = ""

if message.is_multipart():

    for part in message.walk():

        content_type = part.get_content_type()

        content_disposition = str(
            part.get(
                "Content-Disposition",
                ""
            )
        )

        if "attachment" in content_disposition.lower():
            continue

        try:

            payload = part.get_payload(
                decode=True
            )

            if payload is None:
                continue

            charset = (
                part.get_content_charset()
                or "utf-8"
            )

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

        payload = message.get_payload(
            decode=True
        )

        if payload:

            charset = (
                message.get_content_charset()
                or "utf-8"
            )

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
```

# ============================================================

# EXTRACTION URL BIEN'ICI

# ============================================================

def extraire_url_bienici(url):

```
"""
Transforme un lien de redirection Bien'ici
en URL réelle de l'annonce.

Exemple :

https://link.bienici.com/.../aHR0cHM6Ly93d3cuYmllbmljaS5jb20v...

devient :

https://www.bienici.com/annonce/...
"""

if not url:
    return None

url = url.replace(
    "&amp;",
    "&"
)

# --------------------------------------------------------
# Cas normal :
# la partie Base64 commence après le dernier "/"
# --------------------------------------------------------

parties = url.rstrip("/").split("/")

if not parties:
    return None

derniere_partie = parties[-1]

try:

    # Les liens Bien'ici peuvent avoir
    # une longueur Base64 non multiple de 4.
    padding = "=" * (
        -len(derniere_partie) % 4
    )

    decoded = base64.urlsafe_b64decode(
        derniere_partie + padding
    ).decode(
        "utf-8",
        errors="replace"
    )

    if decoded.startswith(
        "http://"
    ) or decoded.startswith(
        "https://"
    ):

        return decoded

except Exception:

    pass

# --------------------------------------------------------
# Si l'extraction échoue,
# on conserve le lien original.
# --------------------------------------------------------

return url
```

# ============================================================

# EXTRACTION DES LIENS D'UN EMAIL

# ============================================================

def extraire_liens_bienici(
text_body="",
html_body=""
):

```
"""
Recherche tous les liens Bien'ici présents
dans un email.

Retourne une liste sans doublons.
"""

contenu = (
    html_body
    + "\n"
    + text_body
)

# --------------------------------------------------------
# Recherche des liens link.bienici.com
# --------------------------------------------------------

urls = re.findall(
    r'https?://link\.bienici\.com/[^\s"<>]+',
    contenu
)

resultats = []

for url in urls:

    # Nettoyage des caractères HTML
    url = url.rstrip(
        ".,);'>\""
    )

    url_reelle = extraire_url_bienici(
        url
    )

    if not url_reelle:
        continue

    if "bienici.com/annonce/" not in url_reelle:
        continue

    if url_reelle not in resultats:

        resultats.append(
            url_reelle
        )

return resultats
```

# ============================================================

# RECUPERATION DES EMAILS BIEN'ICI

# ============================================================

def get_bienici_emails(limit=20):

```
"""
Recherche les derniers emails Bien'ici.

La boîte est ouverte en lecture seule.

Aucun email n'est supprimé,
déplacé ou marqué comme lu.
"""

mail = get_yahoo_connection()

try:

    mail.select(
        "INBOX",
        readonly=True
    )

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

    for email_id in reversed(
        email_ids
    ):

        status, message_data = mail.fetch(
            email_id,
            "(BODY.PEEK[])"
        )

        if status != "OK":

            continue

        raw_email = None

        for response_part in message_data:

            if isinstance(
                response_part,
                tuple
            ):

                raw_email = (
                    response_part[1]
                )

                break

        if not raw_email:

            continue

        message = email.message_from_bytes(
            raw_email
        )

        subject = decode_email_subject(
            message.get(
                "Subject",
                ""
            )
        )

        sender = message.get(
            "From",
            ""
        )

        date = message.get(
            "Date",
            ""
        )

        text_body, html_body = (
            get_email_body(
                message
            )
        )

        # ------------------------------------------------
        # EXTRACTION DES ANNONCES
        # ------------------------------------------------

        liens_annonces = (
            extraire_liens_bienici(
                text_body,
                html_body
            )
        )

        results.append(
            {
                "email_id":
                    email_id.decode(),

                "subject":
                    subject,

                "sender":
                    sender,

                "date":
                    date,

                "text_body":
                    text_body,

                "html_body":
                    html_body,

                "liens_annonces":
                    liens_annonces,

                "nombre_annonces":
                    len(liens_annonces)
            }
        )

    return results

finally:

    try:

        mail.logout()

    except Exception:

        pass
```

# ============================================================

# RECUPERATION DES ANNONCES DEPUIS LES EMAILS

# ============================================================

def get_annonces_from_bienici_emails(
limit=20
):

```
"""
Récupère toutes les URLs d'annonces
trouvées dans les emails Bien'ici.

Les doublons sont supprimés.
"""

emails = get_bienici_emails(
    limit=limit
)

annonces = []

urls_deja_vues = set()

for email_data in emails:

    for url in email_data.get(
        "liens_annonces",
        []
    ):

        if url in urls_deja_vues:
            continue

        urls_deja_vues.add(
            url
        )

        annonces.append(
            {
                "url": url,

                "email_id":
                    email_data.get(
                        "email_id"
                    ),

                "subject":
                    email_data.get(
                        "subject"
                    ),

                "date":
                    email_data.get(
                        "date"
                    )
            }
        )

return annonces
```
