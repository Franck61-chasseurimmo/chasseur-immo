"""Localisation des communes françaises, sans transmettre les fiches personnelles."""
import json
import math
import re
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

import streamlit as st

VERSION = 1


class LocalisationImpossible(Exception):
    pass


def normaliser_nom(value):
    texte = unicodedata.normalize('NFKD', str(value or '').casefold())
    texte = ''.join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"[\s'’\-]+", ' ', texte).strip()


def lire_commune(value):
    texte = str(value or '').strip()
    if not texte or len(texte) > 120 or any(c in texte for c in ',;/|'):
        raise LocalisationImpossible(
            'Indiquez une seule commune précise, par exemple Alençon (61).'
        )
    code = None
    match = re.fullmatch(
        r'(.+?)\s*\((\d{2,3}|2[AB]|\d{5})\)', texte, re.I
    )
    if match:
        texte, code = match.groups()
    else:
        match = re.fullmatch(r'(\d{5})\s+(.+)', texte)
        if match:
            code, texte = match.groups()
    if not all(c.isalpha() or c in " -'’" for c in texte) or not texte.strip():
        raise LocalisationImpossible('Nom de commune non reconnu.')
    return texte.strip(), code.upper() if code else None


class _SansRedirection(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise LocalisationImpossible('Coordonnées de commune indisponibles.')
    lon, lat = value
    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        for v in value
    ):
        raise LocalisationImpossible('Coordonnées de commune invalides.')
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise LocalisationImpossible('Coordonnées de commune hors limites.')
    return float(lon), float(lat)


def analyser_communes(rows, recherche):
    nom, code = lire_commune(recherche)
    if not isinstance(rows, list):
        raise LocalisationImpossible(
            'Réponse du service des communes non reconnue.'
        )
    candidats = [
        r for r in rows
        if isinstance(r, dict)
        and normaliser_nom(r.get('nom')) == normaliser_nom(nom)
        and (
            not code
            or (
                code in (r.get('codesPostaux') or [])
                if len(code) == 5
                else r.get('codeDepartement') == code
            )
        )
    ]
    if len(candidats) != 1:
        raise LocalisationImpossible(
            'Commune absente ou ambiguë : précisez son département, '
            'par exemple Pacé (61).'
        )
    commune = candidats[0]
    centre = commune.get('centre') or {}
    if not isinstance(centre, dict) or centre.get('type') != 'Point':
        raise LocalisationImpossible('Centre de commune indisponible.')
    lon, lat = _point(centre.get('coordinates'))

    # Le rectangle contient la commune. Un chemin méridien puis parallèle
    # donne une borne supérieure prudente de l'écart à son centre.
    # Aucun centre de commune n'est présenté comme l'adresse du bien.
    bbox = commune.get('bbox') or {}
    incertitude = None
    if isinstance(bbox, dict) and bbox.get('type') == 'Polygon':
        try:
            points = [
                _point(p)
                for anneau in bbox['coordinates']
                for p in anneau
            ]
            if (
                len(points) >= 4
                and min(p[0] for p in points) <= lon <= max(p[0] for p in points)
                and min(p[1] for p in points) <= lat <= max(p[1] for p in points)
            ):
                ecart_lat = max(abs(p[1] - lat) for p in points)
                ecart_lon = max(abs(p[0] - lon) for p in points)
                incertitude = 6371 * math.radians(ecart_lat + ecart_lon) + 0.1
        except (KeyError, TypeError, LocalisationImpossible):
            pass

    return dict(
        version=VERSION,
        recherche=str(recherche),
        nom=commune['nom'],
        code=commune.get('code'),
        latitude=lat,
        longitude=lon,
        incertitude_km=incertitude,
        source='geo.api.gouv.fr',
    )


@st.cache_data(ttl=86400, max_entries=512, show_spinner=False)
def rechercher_commune(recherche):
    nom, code = lire_commune(recherche)
    params = dict(
        nom=nom,
        fields='nom,code,codeDepartement,codesPostaux,centre,bbox',
        format='json',
    )
    if code:
        params['codePostal' if len(code) == 5 else 'codeDepartement'] = code

    requete = Request(
        'https://geo.api.gouv.fr/communes?' + urlencode(params),
        headers={
            'Accept': 'application/json',
            'User-Agent': 'ChasseurImmo/1.0',
        },
    )
    try:
        with build_opener(_SansRedirection()).open(
            requete, timeout=6
        ) as response:
            if response.status != 200:
                raise LocalisationImpossible(
                    'Service des communes indisponible ; réessayez plus tard.'
                )
            contenu = response.read(2000001)
        if len(contenu) > 2000000:
            raise LocalisationImpossible(
                'Réponse du service des communes trop volumineuse.'
            )
        rows = json.loads(contenu)
    except (OSError, ValueError) as exc:
        raise LocalisationImpossible(
            'Service des communes indisponible ; réessayez plus tard.'
        ) from exc
    return analyser_communes(rows, recherche)


def preparer_localisations(acquereurs, annonces, chercher=None):
    """Ajouter des données temporaires au matching ; ne pas modifier les fiches."""
    acheteurs = [dict(a) for a in acquereurs]
    biens = [dict(b) for b in annonces]
    actifs = [
        a for a in acheteurs
        if a.get('actif', True) and (a.get('rayon_km') or 0) > 0
    ]
    if not actifs:
        return acheteurs, biens

    cache = {}
    echeance = time.monotonic() + 30

    def localiser(row, champ):
        recherche = str(row.get(champ) or '').strip()
        if recherche not in cache:
            if time.monotonic() >= echeance:
                row['_geo_erreur'] = (
                    'Lecture des communes reportée ; '
                    'relancez le recalcul pour reprendre.'
                )
                return
            try:
                cache[recherche] = (chercher or rechercher_commune)(recherche)
            except LocalisationImpossible as exc:
                cache[recherche] = str(exc)
        resultat = cache[recherche]
        if isinstance(resultat, dict):
            row['_geo'] = resultat
        else:
            row['_geo_erreur'] = resultat

    for a in actifs:
        if (
            a.get('latitude_reference') is None
            and a.get('longitude_reference') is None
        ):
            localiser(a, 'secteur')

    for b in biens:
        if (
            b.get('statut_annonce', 'disponible') == 'disponible'
            and b.get('latitude') is None
            and b.get('longitude') is None
        ):
            localiser(b, 'commune')

    return acheteurs, biens
