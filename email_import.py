"""Lecture IMAP seule ; validation stricte des liens sans requête vers les annonces."""
import base64
import email
import hashlib
import html
import imaplib
import re
from email.header import decode_header
from email.utils import parseaddr
from urllib.parse import urlsplit
from validation import normaliser_url

IMAP_SERVER = 'imap.mail.yahoo.com'
IMAP_PORT = 993


def get_yahoo_connection():
    import streamlit as st

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)

    try:
        mail.login(
            st.secrets['YAHOO_EMAIL'],
            st.secrets['YAHOO_APP_PASSWORD']
        )
    except Exception:
        try:
            mail.logout()
        except Exception:
            pass
        raise

    return mail


def decode_email_subject(subject):
    result = []

    for value, charset in decode_header(subject or ''):
        if isinstance(value, bytes):
            try:
                value = value.decode(
                    charset or 'utf-8',
                    errors='replace'
                )
            except LookupError:
                value = value.decode(
                    'utf-8',
                    errors='replace'
                )

        result.append(value)

    return ''.join(result)


def get_email_body(message):
    bodies = {
        'text/plain': [],
        'text/html': []
    }

    def contenu(part):
        if part.get_content_disposition() == 'attachment' or part.get_filename():
            return

        if part.is_multipart():
            for enfant in part.get_payload():
                yield from contenu(enfant)
        else:
            yield part

    for part in contenu(message):
        typ = part.get_content_type()

        if (
            part.is_multipart()
            or part.get_content_disposition() == 'attachment'
            or typ not in bodies
        ):
            continue

        payload = part.get_payload(decode=True)

        if payload is None:
            continue

        try:
            value = payload.decode(
                part.get_content_charset() or 'utf-8',
                errors='replace'
            )
        except LookupError:
            value = payload.decode(
                'utf-8',
                errors='replace'
            )

        bodies[typ].append(value)

    return (
        '\n'.join(bodies['text/plain']),
        '\n'.join(bodies['text/html'])
    )


def get_bienici_emails(limit=100):
    if not isinstance(limit, int) or not 1 <= limit <= 5000:
        raise ValueError(
            'La limite doit être comprise entre 1 et 5000 e-mails.'
        )

    mail = get_yahoo_connection()

    try:
        status, _ = mail.select('INBOX', readonly=True)

        if status != 'OK':
            raise RuntimeError('Impossible de lire INBOX.')

        _, validity_data = mail.response('UIDVALIDITY')
        validity = (validity_data or [b''])[0] or b''

        if not validity:
            raise RuntimeError(
                'UIDVALIDITY indisponible : import interrompu pour éviter des collisions.'
            )

        status, data = mail.uid(
            'search',
            None,
            '(FROM "bienici.com")'
        )

        if status != 'OK':
            raise RuntimeError('La recherche IMAP a échoué.')

        results = []

        for uid in reversed((data[0] or b'').split()[-limit:]):
            status, parts = mail.uid(
                'fetch',
                uid,
                '(BODY.PEEK[])'
            )

            if status != 'OK':
                raise RuntimeError(
                    'Lecture IMAP interrompue ; relancez pour reprendre.'
                )

            raw = next(
                (p[1] for p in parts if isinstance(p, tuple)),
                None
            )

            if raw is None:
                raise RuntimeError(
                    'Message IMAP incomplet ; relancez pour reprendre.'
                )

            message = email.message_from_bytes(raw)
            sender = message.get('From', '')
            domaine = parseaddr(sender)[1].rsplit('@', 1)[-1].lower()

            if domaine != 'bienici.com' and not domaine.endswith('.bienici.com'):
                continue

            text, markup = get_email_body(message)

            # Le compte + INBOX + UIDVALIDITY + UID évitent les collisions entre boîtes.
            import streamlit as st

            material = (
                f'{st.secrets["YAHOO_EMAIL"]}'
                f'|INBOX|{validity!r}|{uid!r}'
            )

            cle = hashlib.sha256(material.encode()).hexdigest()

            results.append(
                dict(
                    email_id=uid.decode(),
                    cle=cle,
                    subject=decode_email_subject(
                        message.get('Subject')
                    ),
                    sender=sender,
                    date=message.get('Date', ''),
                    text_body=text,
                    html_body=markup
                )
            )

        return results

    finally:
        try:
            mail.logout()
        except Exception:
            pass


def extraire_url_bienici(url):
    if not url:
        return None

    try:
        url = html.unescape(url).strip()
        parts = urlsplit(url)

        if parts.hostname == 'link.bienici.com':
            token = parts.path.rstrip('/').rsplit('/', 1)[-1]

            url = base64.urlsafe_b64decode(
                token + '=' * (-len(token) % 4)
            ).decode('utf-8')

            parts = urlsplit(url)

        if (
            parts.hostname not in ('bienici.com', 'www.bienici.com')
            or not parts.path.startswith('/annonce/')
        ):
            return None

        if not parts.path.removeprefix('/annonce/').strip('/'):
            return None

        return normaliser_url(url)

    except (ValueError, UnicodeError):
        return None


def extraire_liens_bienici(texte):
    urls = re.findall(
        r'https?://[^\s"\'<>]+',
        html.unescape(texte or '')
    )

    result = []

    for url in urls:
        valid = extraire_url_bienici(
            url.rstrip('.,);]')
        )

        if valid and valid not in result:
            result.append(valid)

    return result


def liens_non_resolus(texte):
    urls = re.findall(
        r'https?://[^\s"\'<>]+',
        html.unescape(texte or '')
    )

    return list(
        dict.fromkeys(
            u for u in urls
            if urlsplit(u).hostname == 'link.bienici.com'
            and extraire_url_bienici(u) is None
        )
    )


def get_annonces_from_bienici_emails(limit=100):
    annonces = []
    seen = set()

    for item in get_bienici_emails(limit):
        texte = item['html_body'] + '\n' + item['text_body']

        for url in extraire_liens_bienici(texte):
            if url not in seen:
                seen.add(url)

                annonces.append(
                    dict(
                        url=url,
                        source="Bien'ici",
                        email_id=item['email_id'],
                        email_subject=item['subject'],
                        email_date=item['date']
                    )
                )

    return annonces
