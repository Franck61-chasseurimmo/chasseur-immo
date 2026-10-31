"""Lecture des alertes Yahoo et extraction locale des annonces Bien'ici."""
import base64
import email
import hashlib
import html
import imaplib
import re
from email.header import decode_header
from email.utils import parseaddr
from urllib.parse import urlsplit, urlunsplit, unquote
from html.parser import HTMLParser
from validation import normaliser_url

IMAP_SERVER = 'imap.mail.yahoo.com'
IMAP_PORT = 993


def get_yahoo_connection():
    import streamlit as st

    mail = imaplib.IMAP4_SSL(
        IMAP_SERVER,
        IMAP_PORT,
        timeout=30
    )

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
        if (
            part.get_content_disposition() == 'attachment'
            or part.get_filename()
        ):
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
                'UIDVALIDITY indisponible : import interrompu '
                'pour éviter des collisions.'
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

            if (
                domaine != 'bienici.com'
                and not domaine.endswith('.bienici.com')
            ):
                continue

            text, markup = get_email_body(message)

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


def _destination_lien(url):
    """Décoder localement les liens Mailjet ; ne jamais les visiter."""
    try:
        url = html.unescape(url or '').strip()

        for _ in range(3):
            parts = urlsplit(url)

            if (
                parts.scheme not in ('http', 'https')
                or not parts.hostname
            ):
                return None

            if parts.username or parts.password:
                return None

            if parts.hostname != 'link.bienici.com':
                return url

            if len(url) > 32000:
                return None

            token = unquote(
                parts.path.rstrip('/').rsplit('/', 1)[-1]
            )

            url = base64.b64decode(
                token + '=' * (-len(token) % 4),
                altchars=b'-_',
                validate=True
            ).decode('utf-8')

        return None

    except (ValueError, UnicodeError):
        return None


def extraire_url_bienici(url):
    destination = _destination_lien(url)

    if not destination:
        return None

    try:
        parts = urlsplit(normaliser_url(destination))

        if parts.hostname not in (
            'bienici.com',
            'www.bienici.com'
        ):
            return None

        if not re.fullmatch(r'/annonce/[^/]+/?', parts.path):
            return None

        # Conserver uniquement l'adresse du bien, sans suivi personnel.
        return urlunsplit(
            (
                'https',
                'www.bienici.com',
                parts.path.rstrip('/'),
                '',
                ''
            )
        )

    except ValueError:
        return None


def _urls(texte):
    return re.findall(
        r"https?://[^\s\"'<>]+",
        html.unescape(texte or '')
    )


def extraire_liens_bienici(texte):
    resultat = []

    for url in _urls(texte):
        valide = extraire_url_bienici(
            url.rstrip('.,);]')
        )

        if valide and valide not in resultat:
            resultat.append(valide)

    return resultat


def liens_non_resolus(texte):
    resultat = []

    for url in _urls(texte):
        url = url.rstrip('.,);]')

        try:
            parts = urlsplit(url)

            if parts.hostname != 'link.bienici.com':
                continue

            if parts.path.startswith(
                ('/oo', '/unsub', '/open', '/static', '/images')
            ):
                continue

            # Une destination connue hors annonce n'est pas une erreur.
            if (
                _destination_lien(url) is None
                and url not in resultat
            ):
                resultat.append(url)

        except ValueError:
            continue

    return resultat


class _LecteurLiens(HTMLParser):
    """Associer chaque texte au bien désigné par son propre lien."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.liens = []
        self.textes = []
        self.courant = None
        self.masque = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.masque += 1

        if tag == 'a':
            if self.courant:
                self.liens.append(self.courant)

            self.courant = [
                dict(attrs).get('href', ''),
                []
            ]

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.masque:
            self.masque -= 1

        if tag == 'a' and self.courant:
            self.liens.append(self.courant)
            self.courant = None

    def handle_data(self, data):
        if not self.masque:
            self.textes.append(data)

            if self.courant is not None:
                self.courant[1].append(data)


def _texte_propre(texte):
    return re.sub(
        r'\s+',
        ' ',
        html.unescape(texte or '')
    ).strip()


def extraire_annonces_bienici(email_data):
    """Extraire uniquement les caractéristiques écrites dans l'e-mail."""
    texte = email_data.get('text_body') or ''
    markup = email_data.get('html_body') or ''
    groupes = {}

    def ajouter(url, label=''):
        canonique = extraire_url_bienici(url)

        if canonique:
            groupes.setdefault(canonique, [])
            label = _texte_propre(label)

            if label and label not in groupes[canonique]:
                groupes[canonique].append(label)

    lecteur = _LecteurLiens()
    lecteur.feed(markup)
    lecteur.close()

    if lecteur.courant:
        lecteur.liens.append(lecteur.courant)

    for url, morceaux in lecteur.liens:
        ajouter(url, ' '.join(morceaux))

    # Dans la version texte, [URL] suit généralement son libellé.
    precedent = 0

    for match in re.finditer(
        r'\[(https?://[^\]\s]+)\]',
        texte
    ):
        ajouter(
            match.group(1),
            texte[precedent:match.start()][-500:]
        )
        precedent = match.end()

    for url in extraire_liens_bienici(texte):
        ajouter(url)

    contexte = _texte_propre(
        ' '.join(lecteur.textes) + ' ' + texte
    )

    contexte = re.sub(
        r'https?://[^\s]+',
        '',
        contexte
    )

    agence_unique = len(groupes) == 1 and bool(
        re.search(
            r"\bl['’]agence\b.{0,160}?\bvous propose\b",
            contexte,
            re.I
        )
    )

    resultat = []

    for url, labels in groupes.items():
        bien = {
            'url': url,
            'source': "Bien'ici"
        }

        titres = [
            label for label in labels
            if re.match(
                r'^(maison|pavillon|appartement|studio)\b',
                label,
                re.I
            )
        ]

        if titres:
            titre = titres[0]
            bien['titre'] = titre

            genre = titre.split()[0].lower()

            bien['type_maison'] = (
                'appartement'
                if genre == 'studio'
                else genre
            )

            surface = re.search(
                r'(\d+(?:[.,]\d+)?)\s*m(?:²|2)\b',
                titre,
                re.I
            )

            if surface:
                bien['surface_habitable'] = float(
                    surface.group(1).replace(',', '.')
                )

        for label in labels:
            prix = re.search(
                r'(\d[\d ]*(?:[.,]\d{1,2})?)\s*€',
                label
            )

            if prix and 'prix' not in bien:
                bien['prix'] = float(
                    prix.group(1)
                    .replace(' ', '')
                    .replace(',', '.')
                )

            commune = re.fullmatch(
                r'\d{5}\s+(.+)',
                label
            )

            if commune and 'commune' not in bien:
                bien['commune'] = commune.group(1).strip()

            chambres = re.search(
                r'\b(\d+)\s+chambres?\b',
                label,
                re.I
            )

            if chambres and 'chambres' not in bien:
                bien['chambres'] = int(chambres.group(1))

        if agence_unique:
            bien['type_annonceur'] = 'professionnel'

        # « 5 pièces » ne signifie pas « 5 chambres ».
        # Les équipements absents de l'e-mail restent inconnus.
        resultat.append(bien)

    return resultat


def get_annonces_from_bienici_emails(limit=100):
    resultat = {}

    for item in get_bienici_emails(limit):
        for bien in extraire_annonces_bienici(item):
            resultat.setdefault(bien['url'], bien)

    return list(resultat.values())
