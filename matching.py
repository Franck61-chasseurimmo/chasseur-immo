"""Matching explicable : inconnu, préférence et incompatibilité sont distincts."""
import math
import unicodedata


def normaliser_texte(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '').lower())
                   if not unicodedata.combining(c)).strip()


def calculer_distance_km(lat1, lon1, lat2, lon2):
    if any(x is None for x in (lat1, lon1, lat2, lon2)):
        return None

    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))

    if not all(math.isfinite(x) for x in (lat1, lon1, lat2, lon2)):
        raise ValueError('Coordonnées non finies.')

    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError('Coordonnées hors limites.')

    a1, a2 = map(math.radians, (lat1, lat2))
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(dlon / 2) ** 2

    return 6371 * 2 * math.asin(math.sqrt(min(1, max(0, a))))


def matcher_acquereur(acquereur, annonce, latitude_reference=None, longitude_reference=None):
    details = []

    def ajouter(critere, valeur, conforme, imperatif, message):
        statut = (
            'a_verifier' if valeur is None else
            'correspondance' if conforme else
            'ecarte' if imperatif else
            'preference_non_satisfaite'
        )

        details.append(
            dict(
                critere=critere,
                statut=statut,
                message=message,
                imperatif=imperatif
            )
        )

    types = [
        k for k in ('maison', 'pavillon', 'maison_pierre', 'appartement')
        if acquereur.get('recherche_' + k)
    ]

    categorie = normaliser_texte(annonce.get('type_maison'))

    if not types:
        ajouter('type', None, False, True, 'Type recherché non renseigné.')

    elif not categorie:
        ajouter('type', None, False, True, 'Type du bien à vérifier.')

    else:
        # Le matériau est comparé séparément ; un pavillon appartient aux maisons.
        maison = categorie in ('maison', 'pavillon', 'maison_pierre')

        ok = (
            ('maison' in types and maison)
            or ('maison_pierre' in types and maison)
            or categorie in types
        )

        ajouter('type', categorie, ok, True, f'Type déclaré : {categorie}.')

    budget = acquereur.get('budget_max')

    if budget is None or budget <= 0:
        ajouter('budget', None, False, True, 'Budget acquéreur non renseigné.')

    else:
        marge = acquereur.get('marge_budget')
        limite = budget + (0 if marge is None else marge)
        prix = annonce.get('prix')

        ajouter(
            'budget',
            prix,
            prix is not None and prix <= limite,
            True,
            f'Prix : {prix if prix is not None else "inconnu"} € ; plafond avec marge : {limite:g} €.'
        )

    for achat, bien, critere, obligatoire in (
        ('chambres_min', 'chambres', 'chambres', True),
        ('chambres_rdc_min', 'chambres_rdc', 'chambres_rdc', True),
        ('salles_eau_min', 'salles_eau', 'salles_eau', True),
        ('surface_habitable_min', 'surface_habitable', 'surface_habitable', True),
        ('surface_terrain_souhaitee', 'surface_terrain', 'terrain', False),
    ):
        minimum = acquereur.get(achat)

        if minimum is not None and minimum > 0:
            valeur = annonce.get(bien)

            ajouter(
                critere,
                valeur,
                valeur is not None and valeur >= minimum,
                obligatoire,
                f'Valeur : {valeur if valeur is not None else "inconnue"} ; minimum : {minimum:g}.'
            )

    for achat, bien, obligatoire in (
        ('plain_pied_obligatoire', 'plain_pied', True),
        ('garage_obligatoire', 'garage', True),
        ('salle_eau_rdc', 'salle_eau_rdc', True),
        ('sous_sol_recherche', 'sous_sol', False),
        ('recherche_maison_pierre', 'maison_pierre', False),
    ):
        if acquereur.get(achat):
            valeur = annonce.get(bien)

            ajouter(
                bien,
                valeur,
                valeur is True,
                obligatoire,
                'Information inconnue.' if valeur is None else
                'Présence confirmée.' if valeur else
                'Absence confirmée.'
            )

    rayon = acquereur.get('rayon_km')
    secteur = acquereur.get('secteur')

    if rayon is not None and rayon > 0:
        lat = acquereur.get('latitude_reference', latitude_reference)
        lon = acquereur.get('longitude_reference', longitude_reference)

        distance = calculer_distance_km(
            lat,
            lon,
            annonce.get('latitude'),
            annonce.get('longitude')
        )

        ajouter(
            'localisation',
            distance,
            distance is not None and distance <= rayon,
            True,
            'Coordonnées de référence ou du bien manquantes.' if distance is None else
            f'Distance à vol d’oiseau : {distance:.1f} km ; rayon : {rayon:g} km.'
        )

    elif secteur:
        # Sans rayon, le secteur représente une liste explicite de communes.
        communes = {
            normaliser_texte(x)
            for x in secteur.replace(';', ',').split(',')
            if x.strip()
        }

        commune = annonce.get('commune')

        ajouter(
            'localisation',
            commune or None,
            normaliser_texte(commune) in communes,
            True,
            f'Commune : {commune or "inconnue"} ; communes demandées : {secteur}.'
        )

    else:
        ajouter(
            'localisation',
            None,
            False,
            True,
            'Secteur acquéreur non renseigné.'
        )

    statuts = [d['statut'] for d in details]

    statut = (
        'ecarte' if 'ecarte' in statuts else
        'a_verifier' if 'a_verifier' in statuts else
        'preference_non_satisfaite' if 'preference_non_satisfaite' in statuts else
        'correspondance'
    )

    connus = sum(s != 'a_verifier' for s in statuts)
    conformes = statuts.count('correspondance')

    return dict(
        statut_matching=statut,
        score=round(100 * conformes / connus) if connus else None,
        couverture=round(100 * connus / len(details)) if details else 0,
        details_matching=details
    )


def matcher_tous_les_acquereurs(
    acquereurs,
    annonce,
    latitude_reference=None,
    longitude_reference=None
):
    return [
        dict(
            acquereur=a,
            **matcher_acquereur(
                a,
                annonce,
                latitude_reference,
                longitude_reference
            )
        )
        for a in acquereurs
        if a.get('actif', True)
    ]
