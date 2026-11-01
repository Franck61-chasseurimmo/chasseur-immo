"""Extraction des annonces présentes dans les alertes Leboncoin."""
import re
from urllib.parse import urlsplit, urlunsplit
from email_import import (
    get_emails_alertes,
    _LecteurLiens,
    _texte_propre,
    _urls
)
from validation import normaliser_url


def get_leboncoin_emails(limit=100):
    return get_emails_alertes(
        limit=limit,
        source='leboncoin'
    )


def extraire_url_leboncoin(url):
    try:
        parts = urlsplit(normaliser_url(url))

        if parts.hostname not in (
            'leboncoin.fr',
            'www.leboncoin.fr'
        ):
            return None

        identifiant = re.fullmatch(
            r'/vi/(\d+)\.htm/?',
            parts.path
        )

        if identifiant is None:
            identifiant = re.fullmatch(
                r'/ad/ventes_immobilieres/(\d+)/?',
                parts.path
            )

        if identifiant is None:
            identifiant = re.fullmatch(
                r'/ventes_immobilieres/(\d+)\.htm/?',
                parts.path
            )

        if identifiant is None:
            return None

        return urlunsplit(
            (
                'https',
                'www.leboncoin.fr',
                '/vi/' + identifiant.group(1) + '.htm',
                '',
                ''
            )
        )

    except (ValueError, TypeError):
        return None


def extraire_liens_leboncoin(texte):
    resultat = []

    for url in _urls(texte):
        canonique = extraire_url_leboncoin(
            url.rstrip('.,);]')
        )

        if canonique and canonique not in resultat:
            resultat.append(canonique)

    return resultat


def _liens_html(email_data):
    lecteur = _LecteurLiens()
    lecteur.feed(email_data.get('html_body') or '')
    lecteur.close()

    if lecteur.courant:
        lecteur.liens.append(lecteur.courant)

    return lecteur.liens


def liens_leboncoin_non_resolus(email_data):
    resultat = []

    for url, morceaux in _liens_html(email_data):
        if extraire_url_leboncoin(url):
            continue

        label = _texte_propre(' '.join(morceaux))

        if (
            re.search(
                r"\bvoir\s+l['’]annonce\b",
                label,
                re.I
            )
            and url not in resultat
        ):
            resultat.append(url)

    return resultat


def nombre_annoncees_leboncoin(email_data):
    sujet = email_data.get('subject') or ''

    match = re.search(
        r'\b(\d+)\s+(?:nouveaux?|nouvelles?)\s+(?:biens?|annonces?)\b',
        sujet,
        re.I
    )

    return int(match.group(1)) if match else None


def _nombre(texte):
    return float(
        texte.replace(' ', '').replace(',', '.')
    )


def extraire_annonces_leboncoin(email_data):
    groupes = {}

    def ajouter(url, morceaux):
        canonique = extraire_url_leboncoin(url)

        if canonique:
            groupes.setdefault(canonique, [])

            for morceau in morceaux:
                morceau = _texte_propre(morceau)

                if morceau and morceau not in groupes[canonique]:
                    groupes[canonique].append(morceau)

    for url, morceaux in _liens_html(email_data):
        ajouter(url, morceaux)

    texte = email_data.get('text_body') or ''
    precedent = 0

    for match in re.finditer(
        r'\[(https?://[^\]\s]+)\]',
        texte
    ):
        ajouter(
            match.group(1),
            texte[precedent:match.start()].splitlines()
        )
        precedent = match.end()

    for url in extraire_liens_leboncoin(texte):
        ajouter(url, [])

    resultat = []

    for url, morceaux in groupes.items():
        bien = {
            'url': url,
            'source': 'Leboncoin',
            'type_annonceur': 'inconnu'
        }

        for morceau in morceaux:
            if (
                re.match(
                    r'^(Maison|Pavillon|Appartement|Studio)\b',
                    morceau,
                    re.I
                )
                and 'titre' not in bien
            ):
                bien['titre'] = morceau
                genre = morceau.split()[0].lower()

                bien['type_maison'] = (
                    'appartement'
                    if genre == 'studio'
                    else genre
                )

                surface = re.search(
                    r'(\d+(?:[.,]\d+)?)\s*m(?:²|2)\b',
                    morceau,
                    re.I
                )

                if surface:
                    bien['surface_habitable'] = _nombre(
                        surface.group(1)
                    )

            # Le prix au m² n'est pas le prix du bien.
            prix = re.search(
                r'(?<![\d.,])(\d[\d ]*(?:[.,]\d{1,2})?)\s*€(?!\s*/)',
                morceau
            )

            if prix and 'prix' not in bien:
                bien['prix'] = _nombre(prix.group(1))

            terrain = re.search(
                r'\bTerrain\s*:\s*(\d[\d ]*(?:[.,]\d+)?)\s*m(?:²|2)\b',
                morceau,
                re.I
            )

            if terrain and 'surface_terrain' not in bien:
                bien['surface_terrain'] = _nombre(
                    terrain.group(1)
                )

            commune = re.fullmatch(
                r'([^\d€·:]+?)\s+(\d{5})',
                morceau
            )

            if commune and 'commune' not in bien:
                bien['commune'] = commune.group(1).strip()

            if 'commune' not in bien:
                commune = re.fullmatch(
                    r'(\d{5})\s+([^\d€·:]+)',
                    morceau
                )

                if commune:
                    bien['commune'] = commune.group(2).strip()

            if morceau.lower() in ('pro', 'professionnel'):
                bien['type_annonceur'] = 'professionnel'

            chambres = re.search(
                r'\b(\d+)\s+chambres?\b',
                morceau,
                re.I
            )

            if chambres and 'chambres' not in bien:
                bien['chambres'] = int(chambres.group(1))

        # Les pièces ne sont pas transformées en chambres.
        # Les équipements non renseignés restent inconnus.
        resultat.append(bien)

    return resultat
