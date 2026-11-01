"""Orchestration partagée entre l'interface et les tests hors connexion."""

from matching import matcher_acquereur

from email_import import (
    extraire_annonces_bienici,
    extraire_url_bienici,
    liens_non_resolus,
)


def recalculer(db, acquereurs=None, annonces=None):
    acheteurs = (
        db.get_acquereurs()
        if acquereurs is None
        else acquereurs
    )

    biens = (
        db.get_annonces(actives=True)
        if annonces is None
        else annonces
    )

    nombre = 0

    for bien in biens:
        if bien.get("statut_annonce", "disponible") != "disponible":
            continue

        for acheteur in acheteurs:
            if not acheteur.get("actif", True):
                continue

            resultat = matcher_acquereur(
                acheteur,
                bien,
            )

            db.insert_match(
                dict(
                    acquereur_id=acheteur["id"],
                    annonce_id=bien["id"],
                    **resultat,
                )
            )

            nombre += 1

    return nombre


def importer_emails(db, emails, source="bienici"):
    if source == "bienici":
        extraire = extraire_annonces_bienici
        normaliser = extraire_url_bienici
        prefixe = "bienici-v2:"

    elif source == "leboncoin":
        from leboncoin_import import (
            extraire_annonces_leboncoin,
            extraire_url_leboncoin,
        )

        extraire = extraire_annonces_leboncoin
        normaliser = extraire_url_leboncoin
        prefixe = "leboncoin-v1:"

    else:
        raise ValueError("Source d’alertes inconnue.")

    bilan = {
        "messages": 0,
        "nouveaux": 0,
        "existants": 0,
        "enrichis": 0,
        "deja_traites": 0,
        "non_resolus": 0,
        "sans_annonce": 0,
    }

    acheteurs = db.get_acquereurs()
    index = {}

    # Retrouver les annonces de cette source,
    # y compris les anciennes URL de suivi.
    for bien in db.get_annonces():
        canonique = normaliser(bien.get("url"))

        if canonique and (
            canonique not in index
            or bien.get("url") == canonique
        ):
            index[canonique] = bien

    for item in emails:
        # Reprendre les anciens messages une fois
        # avec le nouvel extracteur.
        cle = prefixe + item["cle"]

        if db.email_traite(cle):
            bilan["deja_traites"] += 1
            continue

        texte = (
            (item.get("html_body") or "")
            + "\n"
            + (item.get("text_body") or "")
        )

        annonces = extraire(item)

        if source == "leboncoin":
            from leboncoin_import import (
                liens_leboncoin_non_resolus,
            )

            non_resolus = liens_leboncoin_non_resolus(item)

        else:
            non_resolus = liens_non_resolus(texte)

        bilan["non_resolus"] += len(non_resolus)

        if not annonces:
            bilan["sans_annonce"] += 1

        for annonce in annonces:
            url = annonce["url"]

            ancienne = (
                index.get(url)
                or db.get_annonce_by_url(url)
            )

            if ancienne:
                bien = ancienne
                bilan["existants"] += 1

            else:
                donnees = dict(annonce)

                donnees.setdefault(
                    "type_annonceur",
                    "inconnu",
                )

                donnees["statut_annonce"] = "disponible"
                bien = db.insert_annonce(donnees)
                bilan["nouveaux"] += 1

            if not bien:
                raise RuntimeError(
                    "Annonce non enregistrée ; "
                    "message non marqué traité."
                )

            changements = {}

            for champ, valeur in annonce.items():
                actuel = bien.get(champ)
                manque = actuel is None or actuel == ""

                if (
                    champ == "type_annonceur"
                    and actuel == "inconnu"
                ):
                    manque = True

                if valeur is not None and manque:
                    changements[champ] = valeur

            if bien.get("url") != url:
                changements["url"] = url

            if changements:
                bien = db.enregistrer(
                    "annonces",
                    changements,
                    bien["id"],
                )

                if ancienne:
                    bilan["enrichis"] += 1

            # Les valeurs connues, y compris zéro et False,
            # ne sont pas écrasées.
            index[url] = bien

            recalculer(
                db,
                acquereurs=acheteurs,
                annonces=[bien],
            )

        if annonces and not non_resolus:
            db.marquer_email(
                cle,
                len(annonces),
            )

        bilan["messages"] += 1

    return bilan
