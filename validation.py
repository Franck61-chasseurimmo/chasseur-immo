"""Validation des saisies, indépendante de Streamlit et des connexions."""
import math
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def normaliser_url(value):
    parts = urlsplit((value or '').strip())

    if (
        parts.scheme.lower() not in ('http', 'https')
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError('Une URL HTTP(S) valide est nécessaire.')

    host = parts.hostname.lower().rstrip('.')
    port = parts.port
    netloc = f'[{host}]' if ':' in host else host

    if port and not (
        port == 80 and parts.scheme == 'http'
        or port == 443 and parts.scheme == 'https'
    ):
        netloc += f':{port}'

    params = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith('utm_')
        and k.lower() not in ('fbclid', 'gclid', 'mc_cid', 'mc_eid')
    ]

    return urlunsplit(
        (
            parts.scheme.lower(),
            netloc,
            parts.path or '/',
            urlencode(sorted(params)),
            ''
        )
    )


def valider(data, acquereur=False):
    data = dict(data)

    if not acquereur and data.get('type_maison') == 'maison_pierre':
        if data.get('maison_pierre') is False:
            raise ValueError(
                'Type maison en pierre incompatible avec construction en pierre = Non.'
            )

        data['maison_pierre'] = True

    if acquereur:
        if (
            not str(data.get('nom', '')).strip()
            or not str(data.get('prenom', '')).strip()
        ):
            raise ValueError('Nom et prénom obligatoires.')

        if data.get('email') and not re.fullmatch(
            r'[^\s@]+@[^\s@]+\.[^\s@]+',
            data['email']
        ):
            raise ValueError('Adresse e-mail invalide.')

    else:
        data['url'] = normaliser_url(data.get('url'))

    for key in (
        'prix',
        'budget_max',
        'marge_budget',
        'chambres',
        'chambres_rdc',
        'salles_eau',
        'chambres_min',
        'chambres_rdc_min',
        'salles_eau_min',
        'surface_terrain',
        'surface_terrain_souhaitee',
        'surface_habitable',
        'surface_habitable_min',
        'rayon_km'
    ):
        value = data.get(key)

        if value is not None and (
            not math.isfinite(float(value))
            or float(value) < 0
        ):
            raise ValueError(
                f'{key} doit être un nombre positif ou nul.'
            )

    for latkey, lonkey in (
        ('latitude', 'longitude'),
        ('latitude_reference', 'longitude_reference')
    ):
        lat = data.get(latkey)
        lon = data.get(lonkey)

        if (lat is None) != (lon is None):
            raise ValueError(
                'Renseignez ensemble latitude et longitude.'
            )

        if lat is not None and (
            not math.isfinite(lat)
            or not math.isfinite(lon)
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
        ):
            raise ValueError('Coordonnées GPS invalides.')

    for child, total in (
        ('chambres_rdc', 'chambres'),
        ('chambres_rdc_min', 'chambres_min')
    ):
        if (
            data.get(child) is not None
            and data.get(total) is not None
            and data[child] > data[total]
        ):
            raise ValueError(
                'Les chambres au RDC ne peuvent dépasser le nombre total de chambres.'
            )

    if (
        acquereur
        and data.get('rayon_km')
        and data.get('latitude_reference') is None
    ):
        raise ValueError(
            'Un rayon nécessite les coordonnées du centre de recherche.'
        )

    return data
