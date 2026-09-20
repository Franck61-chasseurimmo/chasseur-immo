# ============================================================
# MOTEUR DE MATCHING - CHASSEUR IMMO
# ============================================================

import math


# ============================================================
# OUTILS
# ============================================================

def valeur_annonce(annonce, champ):
    """
    Retourne la valeur d'un champ d'annonce.
    Si l'information n'existe pas, retourne None.
    """
    return annonce.get(champ)


def ajouter_resultat(resultats, statut, critere, message):
    """
    Ajoute un résultat de contrôle.
    """
    resultats.append({
        "statut": statut,
        "critere": critere,
        "message": message
    })


def calculer_distance_km(lat1, lon1, lat2, lon2):
    """
    Calcule la distance entre deux coordonnées GPS
    avec la formule de Haversine.
    """

    if None in (lat1, lon1, lat2, lon2):
        return None

    rayon_terre = 6371

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return rayon_terre * c


# ============================================================
# VERIFICATION DU TYPE DE BIEN
# ============================================================

def verifier_type_bien(acquereur, annonce, resultats):

    types_recherches = []

    if acquereur.get("recherche_maison"):
        types_recherches.append("maison")

    if acquereur.get("recherche_pavillon"):
        types_recherches.append("pavillon")

    if acquereur.get("recherche_maison_pierre"):
        types_recherches.append("maison_pierre")

    # Aucun type précisé
    if not types_recherches:
        ajouter_resultat(
            resultats,
            "a_verifier",
            "type",
            "Aucun type de bien précis n'a été renseigné."
        )
        return

    type_annonce = annonce.get("type_maison")

    # Information absente
    if not type_annonce:
        ajouter_resultat(
            resultats,
            "a_verifier",
            "type",
            "Le type de maison n'est pas précisé dans l'annonce."
        )
        return

    type_annonce = str(type_annonce).lower().strip()

    # On vérifie si le type de l'annonce correspond
    correspond = False

    if "maison" in types_recherches:
        if "maison" in type_annonce:
            correspond = True

    if "pavillon" in types_recherches:
        if "pavillon" in type_annonce:
            correspond = True

    if "maison_pierre" in types_recherches:
        if annonce.get("maison_pierre") is True:
            correspond = True

    if correspond:
        ajouter_resultat(
            resultats,
            "correspondance",
            "type",
            "Le type de bien correspond à la recherche."
        )
    else:
        ajouter_resultat(
            resultats,
            "a_verifier",
            "type",
            "Le type de bien ne correspond pas clairement aux critères."
        )


# ============================================================
# BUDGET
# ============================================================

def verifier_budget(acquereur, annonce, resultats):

    budget = acquereur.get("budget_max")
    marge = acquereur.get("marge_budget") or 2000
    prix = annonce.get("prix")

    if not budget:
        return

    if prix is None:
        ajouter_resultat(
            resultats,
            "a_verifier",
            "budget",
            "Le prix de l'annonce n'est pas renseigné."
        )
        return

    budget_acceptable = budget + marge

    if prix <= budget_acceptable:

        ajouter_resultat(
            resultats,
            "correspondance",
            "budget",
            f"Prix : {prix:,.0f} € / limite : {budget_acceptable:,.0f} €."
        )

    else:

        ajouter_resultat(
            resultats,
            "ecarte",
            "budget",
            f"Prix : {prix:,.0f} € / limite : {budget_acceptable:,.0f} €."
        )


# ============================================================
# CHAMBRES
# ============================================================

def verifier_chambres(acquereur, annonce, resultats):

    minimum = acquereur.get("chambres_min")
    chambres = annonce.get("chambres")

    if not minimum:
        return

    if chambres is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "chambres",
            "Le nombre de chambres n'est pas précisé."
        )

        return

    if chambres >= minimum:

        ajouter_resultat(
            resultats,
            "correspondance",
            "chambres",
            f"{chambres} chambres / minimum demandé : {minimum}."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "chambres",
            f"{chambres} chambres / minimum demandé : {minimum}."
        )


# ============================================================
# CHAMBRES RDC
# ============================================================

def verifier_chambres_rdc(acquereur, annonce, resultats):

    minimum = acquereur.get("chambres_rdc_min")
    chambres_rdc = annonce.get("chambres_rdc")

    if not minimum:
        return

    if chambres_rdc is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "chambres_rdc",
            "Le nombre de chambres au RDC n'est pas précisé."
        )

        return

    if chambres_rdc >= minimum:

        ajouter_resultat(
            resultats,
            "correspondance",
            "chambres_rdc",
            f"{chambres_rdc} chambre(s) au RDC / minimum demandé : {minimum}."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "chambres_rdc",
            f"{chambres_rdc} chambre(s) au RDC / minimum demandé : {minimum}."
        )


# ============================================================
# SALLE D'EAU RDC
# ============================================================

def verifier_salle_eau_rdc(acquereur, annonce, resultats):

    if not acquereur.get("salle_eau_rdc"):
        return

    valeur = annonce.get("salle_eau_rdc")

    if valeur is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "salle_eau_rdc",
            "La présence d'une salle d'eau au RDC n'est pas précisée."
        )

    elif valeur is True:

        ajouter_resultat(
            resultats,
            "correspondance",
            "salle_eau_rdc",
            "Salle d'eau au RDC confirmée."
        )

    else:

        ajouter_resultat(
            resultats,
            "ecarte",
            "salle_eau_rdc",
            "L'annonce indique qu'il n'y a pas de salle d'eau au RDC."
        )


# ============================================================
# NOMBRE DE SALLES D'EAU
# ============================================================

def verifier_salles_eau(acquereur, annonce, resultats):

    minimum = acquereur.get("salles_eau_min")
    nombre = annonce.get("salles_eau")

    if not minimum:
        return

    if nombre is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "salles_eau",
            "Le nombre de salles d'eau n'est pas précisé."
        )

        return

    if nombre >= minimum:

        ajouter_resultat(
            resultats,
            "correspondance",
            "salles_eau",
            f"{nombre} salle(s) d'eau / minimum demandé : {minimum}."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "salles_eau",
            f"{nombre} salle(s) d'eau / minimum demandé : {minimum}."
        )


# ============================================================
# PLAIN-PIED
# ============================================================

def verifier_plain_pied(acquereur, annonce, resultats):

    if not acquereur.get("plain_pied_obligatoire"):
        return

    valeur = annonce.get("plain_pied")

    if valeur is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "plain_pied",
            "Le plain-pied n'est pas précisé dans l'annonce."
        )

    elif valeur is True:

        ajouter_resultat(
            resultats,
            "correspondance",
            "plain_pied",
            "Plain-pied confirmé."
        )

    else:

        ajouter_resultat(
            resultats,
            "ecarte",
            "plain_pied",
            "L'annonce indique que le bien n'est pas de plain-pied."
        )


# ============================================================
# GARAGE
# ============================================================

def verifier_garage(acquereur, annonce, resultats):

    if not acquereur.get("garage_obligatoire"):
        return

    valeur = annonce.get("garage")

    if valeur is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "garage",
            "La présence d'un garage n'est pas précisée."
        )

    elif valeur is True:

        ajouter_resultat(
            resultats,
            "correspondance",
            "garage",
            "Garage confirmé."
        )

    else:

        ajouter_resultat(
            resultats,
            "ecarte",
            "garage",
            "L'annonce indique qu'il n'y a pas de garage."
        )


# ============================================================
# SOUS-SOL
# ============================================================

def verifier_sous_sol(acquereur, annonce, resultats):

    if not acquereur.get("sous_sol_recherche"):
        return

    valeur = annonce.get("sous_sol")

    if valeur is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "sous_sol",
            "La présence d'un sous-sol n'est pas précisée."
        )

    elif valeur is True:

        ajouter_resultat(
            resultats,
            "correspondance",
            "sous_sol",
            "Sous-sol confirmé."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "sous_sol",
            "Le sous-sol n'est pas présent selon les informations disponibles."
        )


# ============================================================
# MAISON EN PIERRE
# ============================================================

def verifier_maison_pierre(acquereur, annonce, resultats):

    if not acquereur.get("recherche_maison_pierre"):
        return

    valeur = annonce.get("maison_pierre")

    if valeur is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "maison_pierre",
            "Le caractère pierre de la maison n'est pas précisé."
        )

    elif valeur is True:

        ajouter_resultat(
            resultats,
            "correspondance",
            "maison_pierre",
            "Maison en pierre confirmée."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "maison_pierre",
            "La maison en pierre n'est pas confirmée."
        )


# ============================================================
# TERRAIN
# ============================================================

def verifier_terrain(acquereur, annonce, resultats):

    minimum = acquereur.get("surface_terrain_souhaitee")
    surface = annonce.get("surface_terrain")

    if not minimum:
        return

    if surface is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "terrain",
            "La surface du terrain n'est pas précisée."
        )

        return

    if surface >= minimum:

        ajouter_resultat(
            resultats,
            "correspondance",
            "terrain",
            f"Terrain : {surface:,.0f} m² / souhait : {minimum:,.0f} m²."
        )

    else:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "terrain",
            f"Terrain : {surface:,.0f} m² / souhait : {minimum:,.0f} m²."
        )


# ============================================================
# LOCALISATION
# ============================================================

def verifier_distance(
    acquereur,
    annonce,
    latitude_reference=None,
    longitude_reference=None,
    resultats=None
):

    if resultats is None:
        resultats = []

    rayon = acquereur.get("rayon_km")

    if not rayon:
        return

    lat_annonce = annonce.get("latitude")
    lon_annonce = annonce.get("longitude")

    if latitude_reference is None or longitude_reference is None:
        ajouter_resultat(
            resultats,
            "a_verifier",
            "localisation",
            "La position du secteur de référence n'est pas disponible."
        )
        return

    distance = calculer_distance_km(
        latitude_reference,
        longitude_reference,
        lat_annonce,
        lon_annonce
    )

    if distance is None:

        ajouter_resultat(
            resultats,
            "a_verifier",
            "localisation",
            "La localisation précise de l'annonce n'est pas disponible."
        )

    elif distance <= rayon:

        ajouter_resultat(
            resultats,
            "correspondance",
            "localisation",
            f"Distance : {distance:.1f} km / rayon : {rayon:.1f} km."
        )

    else:

        ajouter_resultat(
            resultats,
            "ecarte",
            "localisation",
            f"Distance : {distance:.1f} km / rayon : {rayon:.1f} km."
        )


# ============================================================
# MATCHING PRINCIPAL
# ============================================================

def matcher_acquereur(
    acquereur,
    annonce,
    latitude_reference=None,
    longitude_reference=None
):

    resultats = []

    verifier_type_bien(
        acquereur,
        annonce,
        resultats
    )

    verifier_budget(
        acquereur,
        annonce,
        resultats
    )

    verifier_chambres(
        acquereur,
        annonce,
        resultats
    )

    verifier_chambres_rdc(
        acquereur,
        annonce,
        resultats
    )

    verifier_salle_eau_rdc(
        acquereur,
        annonce,
        resultats
    )

    verifier_salles_eau(
        acquereur,
        annonce,
        resultats
    )

    verifier_plain_pied(
        acquereur,
        annonce,
        resultats
    )

    verifier_garage(
        acquereur,
        annonce,
        resultats
    )

    verifier_sous_sol(
        acquereur,
        annonce,
        resultats
    )

    verifier_maison_pierre(
        acquereur,
        annonce,
        resultats
    )

    verifier_terrain(
        acquereur,
        annonce,
        resultats
    )

    verifier_distance(
        acquereur,
        annonce,
        latitude_reference,
        longitude_reference,
        resultats
    )

    # ========================================================
    # CALCUL DU STATUT GLOBAL
    # ========================================================

    statuts = [
        resultat["statut"]
        for resultat in resultats
    ]

    nombre_ecartes = statuts.count("ecarte")
    nombre_a_verifier = statuts.count("a_verifier")

    # Un critère clairement incompatible suffit
    # à classer le bien comme écarté.
    if nombre_ecartes > 0:

        statut_global = "ecarte"

    # Sinon, s'il reste des informations à contrôler
    elif nombre_a_verifier > 0:

        statut_global = "a_verifier"

    # Tous les critères connus correspondent
    else:

        statut_global = "correspondance"

    # ========================================================
    # SCORE
    # ========================================================

    nombre_correspondances = statuts.count("correspondance")
    nombre_total = len(statuts)

    if nombre_total > 0:

        score = round(
            (nombre_correspondances / nombre_total) * 100
        )

    else:

        score = 0

    return {
        "statut_matching": statut_global,
        "score": score,
        "details_matching": resultats
    }


# ============================================================
# MATCHING DE TOUS LES ACQUEREURS
# ============================================================

def matcher_tous_les_acquereurs(
    acquereurs,
    annonce,
    latitude_reference=None,
    longitude_reference=None
):

    resultats = []

    for acquereur in acquereurs:

        resultat = matcher_acquereur(
            acquereur,
            annonce,
            latitude_reference,
            longitude_reference
        )

        resultats.append({
            "acquereur": acquereur,
            "statut_matching": resultat["statut_matching"],
            "score": resultat["score"],
            "details_matching": resultat["details_matching"]
        })

    return resultats
