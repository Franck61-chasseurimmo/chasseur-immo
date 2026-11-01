"""Compléter les critères depuis les données publiques de la seule annonce Bien’ici."""

import json
import re
import unicodedata

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from email_import import extraire_url_bienici


VERSION = 1

CHAMPS = (
    'chambres',
    'chambres_rdc',
    'garage',
    'plain_pied',
    'salle_eau_rdc',
    'salle_bain_rdc',
)


class LectureImpossible(RuntimeError):
    pass


class _SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _Texte(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux = []
        self.masque = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.masque += 1

        if tag in ('br', 'p', 'div', 'li'):
            self.morceaux.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.masque:
            self.masque -= 1

        if tag in ('p', 'div', 'li'):
            self.morceaux.append('\n')

    def handle_data(self, data):
        if not self.masque:
            self.morceaux.append(data)


def texte_description(value):
    lecteur = _Texte()
    lecteur.feed(str(value or '')[:100000])

    return '\n'.join(
        re.sub(r'\s+', ' ', ligne).strip()
        for ligne in ''.join(lecteur.morceaux).splitlines()
        if ligne.strip()
    )


def _normaliser(texte):
    texte = ''.join(
        c
        for c in unicodedata.normalize('NFKD', texte.lower())
        if not unicodedata.combining(c)
    )

    return re.sub(
        r'\s+',
        ' ',
        texte.replace('’', "'").replace('‑', '-').replace('–', '-'),
    ).strip()


def charger_annonce_bienici(url):
    canonique = extraire_url_bienici(url)

    if not canonique:
        raise LectureImpossible(
            'Cette URL ne désigne pas une annonce Bien’ici reconnue.'
        )

    identifiant = urlsplit(canonique).path.rsplit('/', 1)[-1]

    if not re.fullmatch(r'[A-Za-z0-9_-]{1,240}', identifiant):
        raise LectureImpossible(
            'Identifiant Bien’ici non reconnu.'
        )

    # Même ressource JSON que celle appelée par la page publique Bien’ici.
    endpoint = (
        'https://www.bienici.com/realEstateAd.json?id='
        + quote(identifiant, safe='')
    )

    request = Request(
        endpoint,
        headers={
            'Accept': 'application/json',
            'User-Agent': 'ChasseurImmo/1.0',
        },
    )

    try:
        with build_opener(_SansRedirection()).open(
            request,
            timeout=10,
        ) as response:
            if response.status != 200:
                raise LectureImpossible(
                    'Descriptif Bien’ici indisponible.'
                )

            if 'json' not in (
                response.headers.get('Content-Type') or ''
            ).lower():
                raise LectureImpossible(
                    'Bien’ici n’a pas fourni les données attendues.'
                )

            contenu = response.read(1500001)

        if len(contenu) > 1500000:
            raise LectureImpossible(
                'Réponse Bien’ici trop volumineuse.'
            )

        donnees = json.loads(contenu)

    except HTTPError as exc:
        raise LectureImpossible(
            f'Bien’ici indisponible (HTTP {exc.code}).'
        ) from exc

    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise LectureImpossible(
            'Lecture du descriptif Bien’ici impossible.'
        ) from exc

    if (
        not isinstance(donnees, dict)
        or donnees.get('id') != identifiant
    ):
        raise LectureImpossible(
            'L’identité de l’annonce reçue ne correspond pas au lien.'
        )

    if donnees.get('adType') != 'buy':
        raise LectureImpossible(
            'Cette annonce n’est pas une vente reconnue.'
        )

    if (
        not isinstance(donnees.get('description'), str)
        or not donnees['description'].strip()
    ):
        raise LectureImpossible(
            'Le descriptif de cette annonce est absent.'
        )

    return donnees


NOMBRES = {
    'un': 1,
    'une': 1,
    'deux': 2,
    'trois': 3,
    'quatre': 4,
    'cinq': 5,
    'six': 6,
    'sept': 7,
    'huit': 8,
    'neuf': 9,
    'dix': 10,
}

COMPTE = (
    r'(\d{1,2}|un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)'
)

CHAMBRE = re.compile(
    r'\b'
    + COMPTE
    + r'\s+(?:(?:belles?|grandes?|petites?|vastes?)\s+)*chambres?\b'
)

RDC = r'(?:rdc|rez[ -]de[ -]chaussee)'

ETAGE = (
    r'(?:(?:\d+(?:er|eme|e)?|premier|deuxieme|second|troisieme)'
    r'\s*etage|etage|sous[ -]sol|combles)'
)

NIVEAU = re.compile(
    r"\b(?:au\s+|a\s+l[' ]|a\s+|le\s+|en\s+)("
    + RDC
    + '|'
    + ETAGE
    + r')\b|\b('
    + RDC
    + '|'
    + ETAGE
    + r')\s*:'
)

HYPOTHESE = re.compile(
    r"\b(?:possibilites?|possibles?|potentiel\w*|pourr\w*|"
    r"pouvant|pouvez|peut|creation|creer|construire|amenageables?|"
    r"transform\w*|projet\w*|envisag\w*|futur\w*)\b"
    r"|\ba amenager\b"
)


def _compter(texte):
    if HYPOTHESE.search(texte) or re.search(
        r'\b(?:chambre\s*(?:/|ou)\s*bureau|'
        r'bureau\s*(?:/|ou)\s*chambre)\b',
        texte,
    ):
        return None

    if re.search(
        r"\b(?:sans|aucune|pas de)\s+chambres?\b",
        texte,
    ):
        return 0

    valeurs = [
        int(m.group(1))
        if m.group(1).isdigit()
        else NOMBRES[m.group(1)]
        for m in CHAMBRE.finditer(texte)
    ]

    # Plusieurs groupes peuvent se recouper :
    # « 3 chambres dont une... ».
    # Ne pas les additionner ou choisir arbitrairement un nombre.
    if (
        len(valeurs) == 1
        and len(re.findall(r'\bchambres?\b', texte)) == 1
    ):
        return valeurs[0]

    if (
        not valeurs
        and len(re.findall(r'\bchambre\b', texte)) == 1
    ):
        return 1

    return None


def analyser_criteres(donnees):
    description = texte_description(
        donnees.get('description')
    )

    texte = _normaliser(description)

    texte = re.split(
        r'les informations sur les risques|honoraires|contactez votre',
        texte,
    )[0]

    preuves = {
        champ: []
        for champ in CHAMPS
    }

    def ajouter(champ, valeur, extrait):
        if valeur is not None:
            preuves[champ].append(
                {
                    'valeur': valeur,
                    'extrait': extrait[:600],
                }
            )

    chambres = donnees.get('bedroomsQuantity')

    if (
        isinstance(chambres, int)
        and not isinstance(chambres, bool)
        and 0 <= chambres <= 30
    ):
        ajouter(
            'chambres',
            chambres,
            'Nombre de chambres déclaré par Bien’ici.',
        )

    if isinstance(donnees.get('hasGarage'), bool):
        ajouter(
            'garage',
            donnees['hasGarage'],
            'Présence du garage déclarée par Bien’ici.',
        )

    premier_niveau = NIVEAU.search(texte)

    introduction = (
        texte[:premier_niveau.start()]
        if premier_niveau
        else texte
    )

    if not preuves['chambres']:
        for phrase in re.split(
            r'[.!?;]\s+|\n+',
            introduction,
        ):
            if CHAMBRE.search(phrase):
                ajouter(
                    'chambres',
                    _compter(phrase),
                    phrase,
                )

    # Une place de parking ou un carport n’est pas un garage.
    for phrase in re.split(r'[.!?;]\s+', texte):
        if re.search(r'\bgarage\b', phrase):
            negatif = re.search(
                r"\b(?:sans|aucun|pas de|absence de)"
                r"\s+(?:(?:un|grand|petit)\s+)*garage\b",
                phrase,
            )

            if negatif:
                ajouter('garage', False, phrase)

            elif (
                not HYPOTHESE.search(phrase)
                and not re.search(
                    r'\bancien\s+garage\b|\bgarage\s+automobile\b',
                    phrase,
                )
            ):
                ajouter('garage', True, phrase)

        if re.search(r'\bplain[ -]pied\b', phrase):
            if re.search(
                r"(?:pas\s+(?:de\s+)?|non[ -])plain[ -]pied",
                phrase,
            ):
                ajouter('plain_pied', False, phrase)

            elif (
                not HYPOTHESE.search(phrase)
                and not re.search(
                    r'\b(?:vie|vivre|espace|partie)\b'
                    r'.{0,30}plain[ -]pied',
                    phrase,
                )
                and re.search(
                    r'\b(?:maison|pavillon|habitation)\s+'
                    r'(?:(?:entierement|totalement|de|est)\s+)*'
                    r'plain[ -]pied\b',
                    phrase,
                )
            ):
                ajouter('plain_pied', True, phrase)

    # Un niveau reste actif jusqu’au niveau suivant.
    # Une omission ne confirme pas une absence.
    niveaux = list(NIVEAU.finditer(texte))
    segments_rdc = []

    for i, match in enumerate(niveaux):
        niveau = match.group(1) or match.group(2)

        if not re.fullmatch(RDC, niveau):
            continue

        fin = (
            niveaux[i + 1].start()
            if i + 1 < len(niveaux)
            else len(texte)
        )

        segment = texte[match.end():fin]

        prochain_est_titre = (
            i + 1 < len(niveaux)
            and texte[niveaux[i + 1].end():]
            .lstrip()
            .startswith(':')
        )

        if (
            i + 1 < len(niveaux)
            and not prochain_est_titre
            and segment.strip()
            and not re.search(r'[.;!?:]\s*$', segment)
        ):
            # « Une chambre à l’étage » ne doit pas
            # être attribuée au RDC.
            coupures = list(
                re.finditer(r'[.;!?]\s+', segment)
            )

            segment = (
                segment[:coupures[-1].end()]
                if coupures
                else ''
            )

        segments_rdc.append(segment)

        for phrase in re.split(r'[.!?;]\s+', segment):
            if HYPOTHESE.search(phrase):
                continue

            for champ, motif in (
                (
                    'salle_eau_rdc',
                    r"salle\s+d[' ]eau|salle\s+de\s+douches?|sde|sdd",
                ),
                (
                    'salle_bain_rdc',
                    r'salle\s+de\s+bains?|sdb',
                ),
            ):
                cible = re.search(
                    r'\b(?:' + motif + r')\b',
                    phrase,
                )

                if cible:
                    avant = phrase[
                        max(0, cible.start() - 25):cible.start()
                    ]

                    absent = bool(
                        re.search(
                            r"(?:sans|aucune|pas de|absence de)"
                            r"\s+(?:une\s+)?$",
                            avant,
                        )
                    )

                    ajouter(
                        champ,
                        not absent,
                        phrase,
                    )

        compte = _compter(segment)

        ajouter(
            'chambres_rdc',
            compte,
            niveau + ' : ' + segment,
        )

    # Formulations avec le niveau après la caractéristique.
    for phrase in re.split(r'[.!?;]\s+', texte):
        if HYPOTHESE.search(phrase):
            continue

        for match in re.finditer(
            r'\b'
            + COMPTE
            + r'\s+chambres?\s+(?:situees?\s+)?au\s+'
            + RDC
            + r'\b',
            phrase,
        ):
            valeur = match.group(1)

            prefixe = phrase[
                max(0, match.start() - 30):match.start()
            ]

            if not re.search(
                r"(?:sans|pas de|aucune)\s*$",
                prefixe,
            ):
                ajouter(
                    'chambres_rdc',
                    (
                        int(valeur)
                        if valeur.isdigit()
                        else NOMBRES[valeur]
                    ),
                    phrase,
                )

        if re.search(
            r'\b(?:aucune|pas de|sans)\s+chambre\s+au\s+' + RDC,
            phrase,
        ):
            ajouter('chambres_rdc', 0, phrase)

        for champ, motif in (
            (
                'salle_eau_rdc',
                r"salle\s+d[' ]eau|salle\s+de\s+douches?|sde|sdd",
            ),
            (
                'salle_bain_rdc',
                r'salle\s+de\s+bains?|sdb',
            ),
        ):
            m = re.search(
                r'\b(?:'
                + motif
                + r')\s+(?:situee\s+)?au\s+'
                + RDC
                + r'\b',
                phrase,
            )

            if m:
                avant = phrase[
                    max(0, m.start() - 25):m.start()
                ]

                absent = bool(
                    re.search(
                        r'(?:sans|aucune|pas de)\s+$',
                        avant,
                    )
                )

                ajouter(
                    champ,
                    not absent,
                    phrase,
                )

    resultat = {}
    traces = {}

    for champ, observations in preuves.items():
        valeurs = {
            p['valeur']
            for p in observations
        }

        if len(valeurs) == 1:
            resultat[champ] = observations[0]['valeur']
            traces[champ] = observations

        elif observations:
            traces[champ] = [
                {
                    'valeur': None,
                    'extrait': 'Mentions contradictoires : à vérifier.',
                }
            ]

    if (
        resultat.get('chambres') is not None
        and resultat.get('chambres_rdc') is not None
        and resultat['chambres_rdc'] > resultat['chambres']
    ):
        resultat.pop('chambres_rdc')

        traces['chambres_rdc'] = [
            {
                'valeur': None,
                'extrait': (
                    'Nombre au RDC supérieur au total : à vérifier.'
                ),
            }
        ]

    resultat['extraction_criteres'] = {
        'version': VERSION,
        'date': datetime.now(timezone.utc).isoformat(),
        'source': 'Bien’ici',
        'preuves': traces,
    }

    if description:
        resultat['description'] = description

    return resultat


def completer_annonce(db, bien, charger=None, force=False):
    """Compléter les champs inconnus sans écraser les saisies existantes."""
    if not extraire_url_bienici(bien.get('url')):
        return bien, False

    trace = bien.get('extraction_criteres') or {}

    if not force and trace.get('version') == VERSION:
        return bien, False

    donnees = (
        charger or charger_annonce_bienici
    )(bien['url'])

    valeurs = analyser_criteres(donnees)
    changements = {}

    for champ, valeur in valeurs.items():
        if (
            champ == 'extraction_criteres'
            or bien.get(champ) is None
            or bien.get(champ) == ''
        ):
            changements[champ] = valeur

    total = (
        bien.get('chambres')
        if bien.get('chambres') is not None
        else changements.get('chambres')
    )

    rdc = changements.get('chambres_rdc')

    if total is not None and rdc is not None and rdc > total:
        changements.pop('chambres_rdc')

        changements['extraction_criteres']['preuves']['chambres_rdc'] = [
            {
                'valeur': None,
                'extrait': (
                    'Incompatible avec le total déjà enregistré : à vérifier.'
                ),
            }
        ]

    nouvelle = db.enregistrer(
        'annonces',
        changements,
        bien['id'],
    )

    return nouvelle, True
