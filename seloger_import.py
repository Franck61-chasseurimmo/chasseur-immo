"""Import SeLoger : cartes d’e-mail et résolution des boutons d’annonce."""

import hashlib
import html
import re

from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from criteres_bienici import (
    LectureImpossible,
    analyser_criteres,
    CHAMPS,
)


VERSION = 1


def _propre(texte):
    # Réparer les caractères parfois doublement encodés.
    def reparer(match):
        try:
            return match.group().encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return match.group()

    texte = re.sub(
        r'[^\x00-\x7f]+',
        reparer,
        html.unescape(str(texte or '')),
    )

    return re.sub(r'\s+', ' ', texte).strip()


def extraire_url_seloger(url):
    """Conserver une adresse de vente SeLoger sans paramètres privés."""
    try:
        p = urlsplit(
            html.unescape(str(url or '')).strip()
        )

        if (
            p.scheme not in ('http', 'https')
            or p.hostname not in ('seloger.com', 'www.seloger.com')
        ):
            return None

        if (
            p.username
            or p.password
            or p.port not in (None, 80, 443)
        ):
            return None

        chemin = p.path.rstrip('/')

        moderne = re.fullmatch(
            r'/annonce/achat/'
            r'(?:[A-Za-z0-9_%~-]+/){1,7}'
            r'[A-Za-z0-9]{8,40}',
            chemin,
        )

        ancien = re.fullmatch(
            r'/annonces/achat/'
            r'(?:[A-Za-z0-9_%~-]+/){0,7}'
            r'\d{5,}\.html?',
            chemin,
        )

        if not moderne and not ancien:
            return None

        return urlunsplit(
            ('https', 'www.seloger.com', chemin, '', '')
        )

    except ValueError:
        return None


def _suivi_autorise(url):
    try:
        p = urlsplit(url)
        q = parse_qs(
            p.query,
            keep_blank_values=True,
        )

        return (
            p.scheme == 'https'
            and p.hostname == 'click.by.seloger.com'
            and not p.username
            and not p.password
            and p.port in (None, 443)
            and p.path in ('', '/')
            and not p.fragment
            and set(q) == {'qs'}
            and len(q['qs']) == 1
            and bool(
                re.fullmatch(
                    r'[A-Za-z0-9_-]{16,4096}',
                    q['qs'][0],
                )
            )
        )

    except (ValueError, TypeError):
        return False


class _SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resoudre_lien_seloger(url):
    """Lire la redirection sans télécharger la page finale."""
    courant = html.unescape(
        str(url or '')
    ).strip()

    for _ in range(3):
        canonique = extraire_url_seloger(courant)

        if canonique:
            return canonique

        if not _suivi_autorise(courant):
            return None

        try:
            requete = Request(
                courant,
                headers={'User-Agent': 'ChasseurImmo/1.0'},
            )

            with build_opener(_SansRedirection()).open(
                requete,
                timeout=10,
            ):
                return None

        except HTTPError as exc:
            try:
                if exc.code not in (301, 302, 303, 307, 308):
                    return None

                destination = exc.headers.get('Location')

                if not destination:
                    return None

                courant = urljoin(
                    courant,
                    destination,
                )

            finally:
                exc.close()

        except (URLError, TimeoutError, OSError, ValueError):
            return None

    return extraire_url_seloger(courant)


class _Liens(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.liens = []
        self.courant = None
        self.masque = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.masque += 1

        if tag == 'a' and not self.masque:
            if self.courant:
                self.liens.append(self.courant)

            self.courant = [
                dict(attrs),
                [],
            ]

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.masque:
            self.masque -= 1

        if tag == 'a' and self.courant:
            self.liens.append(self.courant)
            self.courant = None

    def handle_data(self, data):
        if self.courant is not None and not self.masque:
            self.courant[1].append(data)


def _ancres(item):
    lecteur = _Liens()
    lecteur.feed(item.get('html_body') or '')
    lecteur.close()

    if lecteur.courant:
        lecteur.liens.append(lecteur.courant)

    if lecteur.liens:
        return [
            (
                attrs.get('href', ''),
                attrs.get('name', ''),
                _propre(' '.join(textes)),
            )
            for attrs, textes in lecteur.liens
        ]

    # La version texte place l’URL avant son libellé.
    texte = item.get('text_body') or ''

    positions = list(
        re.finditer(
            r'https?://[^\s<>]+',
            texte,
        )
    )

    resultat = []

    for i, match in enumerate(positions):
        fin = (
            positions[i + 1].start()
            if i + 1 < len(positions)
            else len(texte)
        )

        resultat.append(
            (
                match.group().rstrip('.,);]'),
                '',
                _propre(texte[match.end():fin]),
            )
        )

    return resultat


def _caracteristiques(label, nom=''):
    resultat = {}

    prix = re.fullmatch(
        r'(\d[\d ]*(?:[.,]\d{1,2})?)\s*€',
        label,
    )

    if prix:
        resultat['prix'] = float(
            prix.group(1)
            .replace(' ', '')
            .replace(',', '.')
        )

    titre = re.fullmatch(
        r'(Maison|Pavillon|Appartement|Studio)\s+à\s+vendre',
        label,
        re.I,
    )

    if titre:
        genre = titre.group(1).lower()

        resultat.update(
            titre=label,
            type_maison=(
                'appartement'
                if genre == 'studio'
                else genre
            ),
        )

    if (
        nom == 'adcriteria'
        or re.match(r'^\d+\s+pièces?\b', label, re.I)
    ):
        surface = re.search(
            r'(\d+(?:[.,]\d+)?)\s*m(?:²|2)\b',
            label,
            re.I,
        )

        if surface and not re.search(
            r'\bterrain\b',
            label,
            re.I,
        ):
            resultat['surface_habitable'] = float(
                surface.group(1).replace(',', '.')
            )

    localisation = re.fullmatch(
        r'(?:.*,\s*)?([^,]+?)\s*\((\d{5})\)',
        label,
    )

    if localisation:
        resultat['commune'] = (
            localisation.group(1).strip()
        )

    chambres = re.search(
        r'\b(\d+)\s+chambres?\b',
        label,
        re.I,
    )

    if chambres:
        resultat['chambres'] = int(
            chambres.group(1)
        )

    return resultat


def _candidats(item):
    candidats = []
    carte = {}
    directs = {}

    for url, nom, label in _ancres(item):
        canonique = extraire_url_seloger(url)

        if canonique:
            directs.setdefault(
                canonique,
                {},
            ).update(
                _caracteristiques(label, nom)
            )

        if nom == 'reccoimage':
            carte = {}

        if nom in (
            'reccoprice',
            'reccotitle',
            'adcriteria',
            'reccolocation',
        ):
            carte.update(
                _caracteristiques(label, nom)
            )

        elif not item.get('html_body'):
            carte.update(
                _caracteristiques(label)
            )

        bouton = bool(
            re.fullmatch(
                r"Voir\s+l['’]annonce",
                label,
                re.I,
            )
        )

        if bouton or nom == 'reccobutton':
            candidats.append(
                (url, dict(carte))
            )
            carte = {}

    for url, donnees in directs.items():
        candidats.append(
            (url, donnees)
        )

    return candidats


def preparer_emails_seloger(
    emails,
    resoudre=None,
    cache=None,
    limite=20,
):
    """Résoudre au plus 20 nouveaux liens d’annonce."""
    cache = {} if cache is None else cache
    resoudre = resoudre or resoudre_lien_seloger

    tentatives = set()
    resultat = []

    for item in emails:
        annonces = {}
        echecs = set()

        for lien, donnees in _candidats(item):
            canonique = (
                extraire_url_seloger(lien)
                or extraire_url_seloger(cache.get(lien))
            )

            if (
                not canonique
                and _suivi_autorise(lien)
                and lien not in tentatives
                and len(tentatives) < limite
            ):
                tentatives.add(lien)

                canonique = extraire_url_seloger(
                    resoudre(lien)
                )

                if canonique:
                    cache[lien] = canonique

            if not canonique:
                echecs.add(
                    hashlib.sha256(
                        lien.encode()
                    ).hexdigest()
                )
                continue

            bien = annonces.setdefault(
                canonique,
                {
                    'url': canonique,
                    'source': 'SeLoger',
                    'type_annonceur': 'inconnu',
                },
            )

            for champ, valeur in donnees.items():
                if champ not in bien:
                    bien[champ] = valeur

        copie = dict(item)
        copie['annonces_seloger'] = list(
            annonces.values()
        )
        copie['seloger_non_resolus'] = sorted(echecs)

        resultat.append(copie)

    return resultat


def extraire_annonces_seloger(item):
    if 'annonces_seloger' not in item:
        item = preparer_emails_seloger(
            [item],
            resoudre=lambda url: None,
            limite=0,
        )[0]

    return [
        dict(
            bien,
            url=extraire_url_seloger(bien.get('url')),
        )
        for bien in item['annonces_seloger']
        if extraire_url_seloger(bien.get('url'))
    ]


def liens_seloger_non_resolus(item):
    if 'seloger_non_resolus' not in item:
        item = preparer_emails_seloger(
            [item],
            resoudre=lambda url: None,
            limite=0,
        )[0]

    return list(
        item['seloger_non_resolus']
    )


class _PageAnnonce(HTMLParser):
    CIBLES = {
        'cdp-main-description-title': 'titre',
        'cdp-main-description-expandable-text': 'description',
        'cdp-hardfacts-keyfacts': 'criteres',
        'cdp-classified-keys': 'identite',
    }

    VIDES = {
        'area', 'base', 'br', 'col', 'embed',
        'hr', 'img', 'input', 'link', 'meta',
        'param', 'source', 'track', 'wbr',
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.profondeur = 0
        self.actifs = {}

        self.textes = {
            champ: []
            for champ in self.CIBLES.values()
        }

    def handle_starttag(self, tag, attrs):
        if tag in self.VIDES:
            if tag == 'br':
                self.handle_data('\n')
            return

        self.profondeur += 1

        champ = self.CIBLES.get(
            dict(attrs).get('data-testid')
        )

        if champ:
            self.actifs[champ] = self.profondeur

    def handle_endtag(self, tag):
        if tag in self.VIDES:
            return

        for champ, profondeur in list(self.actifs.items()):
            if profondeur == self.profondeur:
                del self.actifs[champ]

        self.profondeur = max(
            0,
            self.profondeur - 1,
        )

    def handle_data(self, data):
        for champ in self.actifs:
            self.textes[champ].append(data)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

        if tag not in self.VIDES:
            self.handle_endtag(tag)


def analyser_page_seloger(markup, url):
    canonique = extraire_url_seloger(url)

    if not canonique:
        raise LectureImpossible(
            'URL SeLoger non reconnue.'
        )

    lecteur = _PageAnnonce()
    lecteur.feed(markup)
    lecteur.close()

    identifiant = (
        urlsplit(canonique)
        .path.rsplit('/', 1)[-1]
    )

    identite = _propre(
        ' '.join(lecteur.textes['identite'])
    )

    if not re.search(
        r'(?<![A-Za-z0-9])'
        + re.escape(identifiant)
        + r'(?![A-Za-z0-9])',
        identite,
    ):
        raise LectureImpossible(
            'L’identité de la page SeLoger '
            'ne correspond pas au lien.'
        )

    description = ''.join(
        lecteur.textes['description']
    ).strip()

    if len(description) < 30:
        raise LectureImpossible(
            'Descriptif complet SeLoger absent ou non reconnu.'
        )

    titre = _propre(
        ' '.join(lecteur.textes['titre'])
    )

    donnees = {
        'description': titre + '\n' + description,
    }

    faits = _propre(
        ' '.join(lecteur.textes['criteres'])
    )

    chambres = {
        int(match.group(1))
        for match in re.finditer(
            r'\b(\d{1,2})\s+chambres?\b',
            faits,
            re.I,
        )
    }

    if len(chambres) == 1:
        donnees['bedroomsQuantity'] = chambres.pop()

    return donnees


def charger_annonce_seloger(url):
    canonique = extraire_url_seloger(url)

    if not canonique:
        raise LectureImpossible(
            'URL SeLoger non reconnue.'
        )

    try:
        request = Request(
            canonique,
            headers={
                'User-Agent': 'ChasseurImmo/1.0',
                'Accept': 'text/html',
            },
        )

        with build_opener(_SansRedirection()).open(
            request,
            timeout=10,
        ) as response:
            if (
                response.status != 200
                or 'text/html' not in (
                    response.headers.get('Content-Type') or ''
                ).lower()
            ):
                raise LectureImpossible(
                    'Page SeLoger indisponible.'
                )

            contenu = response.read(2500001)

        if len(contenu) > 2500000:
            raise LectureImpossible(
                'Page SeLoger trop volumineuse.'
            )

        markup = contenu.decode(
            'utf-8',
            errors='replace',
        )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        raise LectureImpossible(
            'Lecture du descriptif SeLoger impossible.'
        ) from exc

    return analyser_page_seloger(
        markup,
        canonique,
    )


def completer_annonce_seloger(db, bien, charger=None):
    if not extraire_url_seloger(bien.get('url')):
        return bien, False

    trace = bien.get('extraction_criteres') or {}

    if (
        trace.get('version') == VERSION
        and str(trace.get('source', '')).startswith('SeLoger')
    ):
        return bien, False

    donnees = (
        charger or charger_annonce_seloger
    )(bien['url'])

    valeurs = analyser_criteres(donnees)
    trace = valeurs['extraction_criteres']

    trace.update(
        source='SeLoger',
        mode='lecture_publique',
        url_source=extraire_url_seloger(bien['url']),
    )

    for preuve in trace.get('preuves', {}).get('chambres', []):
        if preuve['extrait'] == 'Nombre de chambres déclaré par Bien’ici.':
            preuve['extrait'] = (
                'Nombre de chambres déclaré par SeLoger.'
            )

    changements = {
        champ: valeur
        for champ, valeur in valeurs.items()
        if (
            champ == 'extraction_criteres'
            or bien.get(champ) is None
            or bien.get(champ) == ''
        )
    }

    _verifier_nombres(
        bien,
        changements,
    )

    nouvelle = db.enregistrer(
        'annonces',
        changements,
        bien['id'],
    )

    if not nouvelle:
        raise RuntimeError(
            'Enregistrement des critères non confirmé.'
        )

    return nouvelle, True


def _verifier_nombres(bien, changements):
    total = (
        bien.get('chambres')
        if bien.get('chambres') is not None
        else changements.get('chambres')
    )

    rdc = (
        bien.get('chambres_rdc')
        if bien.get('chambres_rdc') is not None
        else changements.get('chambres_rdc')
    )

    retires = []

    if (
        total is not None
        and rdc is not None
        and rdc > total
    ):
        for champ in ('chambres', 'chambres_rdc'):
            if champ in changements:
                changements.pop(champ)
                retires.append(champ)

                changements['extraction_criteres']['preuves'][champ] = [
                    {
                        'valeur': None,
                        'extrait': 'Nombres incompatibles : à vérifier.',
                    }
                ]

    return retires


def completer_description_seloger(db, bien, description):
    """Analyser un descriptif collé dans la fiche SeLoger."""
    if (
        not bien.get('id')
        or not extraire_url_seloger(bien.get('url'))
    ):
        raise ValueError(
            'Sélectionnez une annonce SeLoger déjà enregistrée.'
        )

    texte = str(description or '').strip()

    if not 20 <= len(texte) <= 100000:
        raise ValueError(
            'Collez uniquement le descriptif complet de cette annonce '
            '(20 à 100 000 caractères).'
        )

    valeurs = analyser_criteres(
        {'description': texte}
    )

    trace = valeurs['extraction_criteres']

    trace.update(
        source='SeLoger — texte collé',
        mode='copie_manuelle',
    )

    changements = {
        'description': valeurs.get('description') or texte,
        'extraction_criteres': trace,
    }

    completes = []
    conserves = []
    a_verifier = []

    for champ in CHAMPS:
        if champ not in valeurs:
            a_verifier.append(champ)

        elif bien.get(champ) is None or bien.get(champ) == '':
            changements[champ] = valeurs[champ]
            completes.append(champ)

        elif bien[champ] != valeurs[champ]:
            conserves.append(champ)

    for champ in _verifier_nombres(bien, changements):
        completes.remove(champ)

        if champ not in a_verifier:
            a_verifier.append(champ)

    nouvelle = db.enregistrer(
        'annonces',
        changements,
        bien['id'],
    )

    if not nouvelle:
        raise RuntimeError(
            'Enregistrement du descriptif non confirmé.'
        )

    return {
        'bien': nouvelle,
        'completes': completes,
        'conserves': conserves,
        'a_verifier': a_verifier,
    }
