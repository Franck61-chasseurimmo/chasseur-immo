"""Alertes Figaro Immobilier, sans ouvrir les liens de connexion automatique."""
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, build_opener

from criteres_bienici import analyser_criteres, CHAMPS, LectureImpossible
from seloger_import import _PageAnnonce, _SansRedirection, _verifier_nombres, _propre

VERSION = 1
HOTE = 'immobilier.lefigaro.fr'


def _adresse_publique(chemin):
    match = re.fullmatch(r'/(?:annonces/)?annonce-(\d{5,12})\.html', chemin)
    return 'https://' + HOTE + '/annonces/annonce-' + match.group(1) + '.html' if match else None


def extraire_url_figaro(url):
    """Décoder le redirectUrl localement et jeter la clé de connexion."""
    try:
        p = urlsplit(html.unescape(str(url or '')).strip())
        if p.scheme not in ('http', 'https') or p.hostname != HOTE:
            return None
        if p.username or p.password or p.port not in (None, 80, 443):
            return None
        direct = _adresse_publique(p.path)
        if direct:
            return direct
        if p.path != '/annonces/authentification-auto.html':
            return None
        params = parse_qs(p.query, keep_blank_values=True)
        if len(params.get('redirectUrl', [])) != 1:
            return None
        destination = urlsplit(params['redirectUrl'][0])
        if destination.scheme or destination.netloc or destination.username or destination.password:
            return None
        return _adresse_publique(destination.path)
    except ValueError:
        return None


def extraire_metadonnees_figaro(message):
    """Ne retenir du champ technique que les identifiants publics et codes postaux."""
    raw = message.get('X-Mailin-Custom') or ''
    if len(raw) > 100000:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict) or data.get('transaction') != 'VENTE' or data.get('application_code') != 'FI':
        return []
    elements = data.get('classifieds')
    if not isinstance(elements, list):
        return []
    resultat = []
    for element in elements[:500]:
        if not isinstance(element, dict) or not re.fullmatch(r'\d{5,12}', str(element.get('id', ''))):
            continue
        ligne = {'id': str(element['id'])}
        cp = str(element.get('zipCode', ''))
        if re.fullmatch(r'\d{5}', cp):
            ligne['code_postal'] = cp
        resultat.append(ligne)
    return resultat


class _EmailFigaro(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textes = []
        self.cartes = []
        self.liens = []
        self.ancre = None
        self.masque = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.masque += 1
        if tag in ('p', 'br', 'tr'):
            self.textes.append('\n')
        if tag == 'a' and not self.masque:
            self.ancre = [dict(attrs).get('href', ''), []]

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.masque:
            self.masque -= 1
        if tag in ('p', 'tr'):
            self.textes.append('\n')
        if tag == 'a' and self.ancre:
            lien, mots = self.ancre
            self.liens.append(lien)
            label = _propre(' '.join(mots))
            if re.fullmatch(r"Voir\s+l['’]annonce", label, re.I):
                self.cartes.append((''.join(self.textes), lien))
                self.textes = []
            self.ancre = None

    def handle_data(self, data):
        if not self.masque:
            self.textes.append(data)
            if self.ancre is not None:
                self.ancre[1].append(data)


def _caracteristiques(texte):
    lignes = '\n'.join(_propre(x) for x in texte.splitlines() if x.strip())
    plat = _propre(lignes)
    bien = {}
    prix = re.search(r'(?<![\d.,])(\d[\d ]*(?:[.,]\d{1,2})?)\s*€(?!\s*/)', plat)
    if prix:
        bien['prix'] = float(prix.group(1).replace(' ', '').replace(',', '.'))
    genre = re.search(r'\b(Maison|Pavillon|Appartement|Studio)(?=\s|\d|[•·])', plat, re.I)
    if genre:
        nom = genre.group(1).lower()
        bien['type_maison'] = 'appartement' if nom == 'studio' else nom
        bien['titre'] = genre.group(1).capitalize()
        suite = plat[genre.end():]
        surface = re.search(r'(\d+(?:[.,]\d+)?)\s*m(?:²|2)', suite)
        if surface and not re.search(r'\bterrain\b', suite[:surface.start()], re.I):
            bien['surface_habitable'] = float(surface.group(1).replace(',', '.'))
            bien['titre'] += ' · ' + surface.group(1) + ' m²'
    commune = re.search(r"^([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ '\-’]{1,80})\s*\((\d{2,3}|\d{5})\)\s*$", lignes, re.M)
    if commune:
        bien['commune'] = commune.group(1).strip()
    chambres = re.search(r'\b(\d+)\s+chambres?\b', plat, re.I)
    if chambres:
        bien['chambres'] = int(chambres.group(1))
    return bien


def _extraire(item):
    texte = html.unescape(item.get('text_body') or '')
    lecteur = _EmailFigaro()
    lecteur.feed(item.get('html_body') or '')
    lecteur.close()
    annonces = {}
    positions = []
    for match in re.finditer(r'https?://[^\s<>]+', texte):
        lien = match.group().rstrip('.,);]')
        canonique = extraire_url_figaro(lien)
        if canonique:
            annonces.setdefault(canonique, {})
            positions.append((canonique, match.start(), match.end()))
    for i, (canonique, debut, fin) in enumerate(positions):
        fin_bloc = len(texte)
        for suivante, debut_suivant, _ in positions[i + 1:]:
            if suivante != canonique:
                fin_bloc = debut_suivant
                break
        bloc = re.sub(r'https?://[^\s<>]+', '', texte[fin:fin_bloc])
        for champ, valeur in _caracteristiques(bloc).items():
            annonces[canonique].setdefault(champ, valeur)
    for lien in lecteur.liens:
        canonique = extraire_url_figaro(lien)
        if canonique:
            annonces.setdefault(canonique, {})
    for meta in item.get('figaro_annonces_meta') or []:
        if isinstance(meta, dict) and re.fullmatch(r'\d{5,12}', str(meta.get('id', ''))):
            annonces.setdefault(_adresse_publique('/annonce-' + str(meta['id']) + '.html'), {})
    # Une seule carte et un seul identifiant : association sans ambiguïté.
    # Pour plusieurs biens, ne pas attribuer les données HTML par simple ordre.
    if len(annonces) == 1 and len(lecteur.cartes) == 1:
        donnees = next(iter(annonces.values()))
        donnees.update(_caracteristiques(lecteur.cartes[0][0]))
    else:
        for contenu, lien in lecteur.cartes:
            canonique = extraire_url_figaro(lien)
            if canonique:
                annonces.setdefault(canonique, {}).update(_caracteristiques(contenu))
    resultat = [dict(donnees, url=lien, source='Figaro Immobilier', type_annonceur='inconnu')
                for lien, donnees in annonces.items()]
    manquants = max(0, len(lecteur.cartes) - len(annonces))
    echecs = [hashlib.sha256(('carte-figaro-' + str(i)).encode()).hexdigest() for i in range(manquants)]
    return resultat, echecs


def extraire_annonces_figaro(item):
    return _extraire(item)[0]


def liens_figaro_non_resolus(item):
    return _extraire(item)[1]


class _PageFigaro(_PageAnnonce):
    CIBLES = {'classified-description': 'description', 'classified-main-infos': 'titre',
              'classified-features': 'criteres'}

    def __init__(self):
        super().__init__()
        self.canonique = None
        self.payload = None
        self._script_payload = False
        self._morceaux_payload = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'link' and d.get('rel') == 'canonical':
            self.canonique = extraire_url_figaro(d.get('href'))
        if tag == 'script' and d.get('id') == '__NUXT_DATA__' and d.get('type') == 'application/json':
            self._script_payload = True
            self._morceaux_payload = []
        attrs = list(attrs)
        if d.get('id') in self.CIBLES:
            attrs.append(('data-testid', d['id']))
        super().handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self._script_payload:
            self._morceaux_payload.append(data)
        else:
            super().handle_data(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self._script_payload:
            self._script_payload = False
            try:
                self.payload = json.loads(''.join(self._morceaux_payload))
            except ValueError:
                self.payload = None
        super().handle_endtag(tag)


def analyser_page_figaro(markup, url):
    canonique = extraire_url_figaro(url)
    lecteur = _PageFigaro()
    lecteur.feed(markup)
    lecteur.close()
    if not canonique or lecteur.canonique != canonique:
        raise LectureImpossible('L’identité de la page Figaro ne correspond pas au lien.')
    description = ''.join(lecteur.textes['description']).strip()
    donnees_structurees = {}
    if isinstance(lecteur.payload, list):
        elements = lecteur.payload

        def lire_ref(ref):
            return elements[ref] if isinstance(ref, int) and not isinstance(ref, bool) and 0 <= ref < len(elements) else None

        identifiant = re.search(r'annonce-(\d+)\.html$', canonique).group(1)
        candidats = [x for x in elements if isinstance(x, dict) and 'descriptionFull' in x
                     and str(lire_ref(x.get('id'))) == identifiant]
        if len(candidats) == 1:
            objet = candidats[0]
            complet = lire_ref(objet['descriptionFull'])
            if isinstance(complet, str) and len(complet.strip()) >= 30:
                description = complet.strip()
            chambres = lire_ref(objet.get('bedRoomCount'))
            if isinstance(chambres, int) and not isinstance(chambres, bool) and 0 <= chambres <= 30:
                donnees_structurees['bedroomsQuantity'] = chambres
    if re.search(r'Voir\s+la\s+suite\s+de\s+la\s+description', description, re.I) or description.endswith(('...', '…')):
        raise LectureImpossible('Seul un résumé Figaro est disponible ; le descriptif complet reste à reprendre.')
    if len(description) < 30:
        raise LectureImpossible('Descriptif complet Figaro absent ou non reconnu.')
    donnees = dict(donnees_structurees, description=description)
    faits = _propre(' '.join(lecteur.textes['titre'] + lecteur.textes['criteres']))
    chambres = {int(m.group(1)) for m in re.finditer(r'\b(\d{1,2})\s+chambres?\b', faits, re.I)}
    if len(chambres) == 1 and 'bedroomsQuantity' not in donnees:
        donnees['bedroomsQuantity'] = chambres.pop()
    return donnees


def charger_annonce_figaro(url):
    canonique = extraire_url_figaro(url)
    if not canonique:
        raise LectureImpossible('URL Figaro Immobilier non reconnue.')
    try:
        requete = Request(canonique, headers={'User-Agent': 'ChasseurImmo/1.0', 'Accept': 'text/html'})
        with build_opener(_SansRedirection()).open(requete, timeout=10) as response:
            if response.status != 200 or 'text/html' not in (response.headers.get('Content-Type') or '').lower():
                raise LectureImpossible('Page Figaro indisponible.')
            contenu = response.read(3000001)
        if len(contenu) > 3000000:
            raise LectureImpossible('Page Figaro trop volumineuse.')
    except HTTPError as exc:
        raise LectureImpossible(f'Figaro refuse ou ne peut fournir la page (HTTP {exc.code}).') from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise LectureImpossible('Connexion au descriptif Figaro impossible.') from exc
    return analyser_page_figaro(contenu.decode('utf-8', errors='replace'), canonique)


def _enregistrer_analyse(db, bien, donnees, mode):
    valeurs = analyser_criteres(donnees)
    trace = valeurs['extraction_criteres']
    source = 'Figaro Immobilier' + (' — texte collé' if mode == 'copie_manuelle' else '')
    trace.update(version=VERSION, source=source, mode=mode, url_source=extraire_url_figaro(bien['url']))
    for preuve in trace.get('preuves', {}).get('chambres', []):
        if preuve['extrait'] == 'Nombre de chambres déclaré par Bien’ici.':
            preuve['extrait'] = 'Nombre de chambres déclaré par Figaro Immobilier.'
    changements = {'extraction_criteres': trace}
    completes, conserves, a_verifier = [], [], []
    for champ, valeur in valeurs.items():
        if champ == 'extraction_criteres':
            continue
        if bien.get(champ) is None or bien.get(champ) == '' or (champ == 'description' and mode == 'copie_manuelle'):
            changements[champ] = valeur
            if champ in CHAMPS:
                completes.append(champ)
        elif champ in CHAMPS and bien[champ] != valeur:
            conserves.append(champ)
    a_verifier = [champ for champ in CHAMPS if champ not in valeurs]
    for champ in _verifier_nombres(bien, changements):
        completes.remove(champ)
        if champ not in a_verifier:
            a_verifier.append(champ)
    nouvelle = db.enregistrer('annonces', changements, bien['id'])
    if not nouvelle:
        raise RuntimeError('Enregistrement du descriptif Figaro non confirmé.')
    return {'bien': nouvelle, 'completes': completes, 'conserves': conserves, 'a_verifier': a_verifier}


def completer_annonce_figaro(db, bien, charger=None):
    if not extraire_url_figaro(bien.get('url')):
        return bien, False
    trace = bien.get('extraction_criteres') or {}
    if trace.get('version') == VERSION and str(trace.get('source', '')).startswith('Figaro Immobilier'):
        return bien, False
    donnees = (charger or charger_annonce_figaro)(bien['url'])
    return _enregistrer_analyse(db, bien, donnees, 'lecture_publique')['bien'], True


def completer_description_figaro(db, bien, description):
    if not bien.get('id') or not extraire_url_figaro(bien.get('url')):
        raise ValueError('Sélectionnez une annonce Figaro Immobilier déjà enregistrée.')
    texte = str(description or '').strip()
    if not 20 <= len(texte) <= 100000:
        raise ValueError('Collez uniquement le descriptif complet de cette annonce (20 à 100 000 caractères).')
    return _enregistrer_analyse(db, bien, {'description': texte}, 'copie_manuelle')
