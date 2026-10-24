"""Gestion du recalcul des correspondances et de l'import des annonces."""
from matching import matcher_acquereur
from email_import import extraire_liens_bienici, liens_non_resolus


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
        if bien.get('statut_annonce', 'disponible') != 'disponible':
            continue

        for acheteur in acheteurs:
            if not acheteur.get('actif', True):
                continue

            resultat = matcher_acquereur(acheteur, bien)

            db.insert_match(
                dict(
                    acquereur_id=acheteur['id'],
                    annonce_id=bien['id'],
                    **resultat
                )
            )

            nombre += 1

    return nombre


def importer_emails(db, emails):
    bilan = dict(
        messages=0,
        nouveaux=0,
        existants=0,
        deja_traites=0,
        non_resolus=0,
        sans_annonce=0
    )

    acheteurs = db.get_acquereurs()

    for item in emails:
        if db.email_traite(item['cle']):
            bilan['deja_traites'] += 1
            continue

        texte = (
            (item.get('html_body') or '')
            + '\n'
            + (item.get('text_body') or '')
        )

        liens = extraire_liens_bienici(texte)
        non_resolus = liens_non_resolus(texte)

        bilan['non_resolus'] += len(non_resolus)

        if not liens:
            bilan['sans_annonce'] += 1

        for url in liens:
            ancienne = db.get_annonce_by_url(url)

            bien = ancienne or db.insert_annonce(
                dict(
                    url=url,
                    source="Bien'ici",
                    statut_annonce='disponible',
                    type_annonceur='inconnu'
                )
            )

            if not bien:
                raise RuntimeError(
                    'Annonce non enregistrée ; message non marqué traité.'
                )

            if ancienne:
                bilan['existants'] += 1
            else:
                bilan['nouveaux'] += 1

            recalculer(
                db,
                acquereurs=acheteurs,
                annonces=[bien]
            )

        # Marquer le message après la réussite de toutes les écritures.
        # En cas de panne, le traitement pourra être relancé.
        # Les messages avec des liens non décodés restent à reprendre.
        if liens and not non_resolus:
            db.marquer_email(
                item['cle'],
                len(liens)
            )

        bilan['messages'] += 1

    return bilan
