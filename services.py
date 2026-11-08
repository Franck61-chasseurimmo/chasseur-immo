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
        if bien.get('statut_annonce', 'disponible') != 'disponible':
            continue

        for acheteur in acheteurs:
            if not acheteur.get('actif', True):
                continue

            resultat = matcher_acquereur(
                acheteur,
                bien,
            )

            db.insert_match(
                dict(
                    acquereur_id=acheteur['id'],
                    annonce_id=bien['id'],
                    **resultat,
                )
            )

            nombre += 1

    return nombre


def importer_emails(
    db,
    emails,
    source='bienici',
    enrichir=False,
):
    if source == 'bienici':
        extraire = extraire_annonces_bienici
        normaliser = extraire_url_bienici
        prefixe = 'bienici-v2:'

    elif source == 'leboncoin':
        from leboncoin_import import (
            extraire_annonces_leboncoin,
            extraire_url_leboncoin,
        )

        extraire = extraire_annonces_leboncoin
        normaliser = extraire_url_leboncoin
        prefixe = 'leboncoin-v1:'

    elif source == 'seloger':
        from seloger_import import (
            extraire_annonces_seloger,
            extraire_url_seloger,
        )

        extraire = extraire_annonces_seloger
        normaliser = extraire_url_seloger
        prefixe = 'seloger-v1:'

    else:
        raise ValueError('Source d’alertes inconnue.')

    bilan = {
        'messages': 0,
        'nouveaux': 0,
        'existants': 0,
        'enrichis': 0,
        'deja_traites': 0,
        'non_resolus': 0,
        'sans_annonce': 0,
        'criteres_lus': 0,
        'criteres_erreurs': 0,
        'criteres_reportes': 0,
    }

    tentatives = set()
    acheteurs = db.get_acquereurs()
    index = {}

    # Retrouver les annonces de cette source,
    # y compris les anciennes URL de suivi.
    for bien in db.get_annonces():
        canonique = normaliser(
            bien.get('url')
        )

        if canonique and (
            canonique not in index
            or bien.get('url') == canonique
        ):
            index[canonique] = bien

    for item in emails:
        # Conserver les identifiants de traitement existants.
        cle = prefixe + item['cle']

        if db.email_traite(cle):
            bilan['deja_traites'] += 1
            continue

        texte = (
            (item.get('html_body') or '')
            + '\n'
            + (item.get('text_body') or '')
        )

        annonces = extraire(item)

        if source == 'leboncoin':
            from leboncoin_import import (
                liens_leboncoin_non_resolus,
            )

            non_resolus = liens_leboncoin_non_resolus(item)

        elif source == 'seloger':
            from seloger_import import (
                liens_seloger_non_resolus,
            )

            non_resolus = liens_seloger_non_resolus(item)

        else:
            non_resolus = liens_non_resolus(texte)

        bilan['non_resolus'] += len(non_resolus)

        if not annonces:
            bilan['sans_annonce'] += 1

        for annonce in annonces:
            url = annonce['url']

            ancienne = (
                index.get(url)
                or db.get_annonce_by_url(url)
            )

            if ancienne:
                bien = ancienne
                bilan['existants'] += 1

            else:
                donnees = dict(annonce)

                donnees.setdefault(
                    'type_annonceur',
                    'inconnu',
                )

                donnees['statut_annonce'] = 'disponible'
                bien = db.insert_annonce(donnees)
                bilan['nouveaux'] += 1

            if not bien:
                raise RuntimeError(
                    'Annonce non enregistrée ; '
                    'message non marqué traité.'
                )

            changements = {}

            for champ, valeur in annonce.items():
                actuel = bien.get(champ)
                manque = actuel is None or actuel == ''

                if (
                    champ == 'type_annonceur'
                    and actuel == 'inconnu'
                ):
                    manque = True

                if valeur is not None and manque:
                    changements[champ] = valeur

            if bien.get('url') != url:
                changements['url'] = url

            if changements:
                bien = db.enregistrer(
                    'annonces',
                    changements,
                    bien['id'],
                )

                if ancienne:
                    bilan['enrichis'] += 1

            # Les valeurs connues, y compris zéro et False,
            # ne sont pas écrasées.
            if (
                enrichir
                and source in ('bienici', 'seloger')
                and bien.get(
                    'statut_annonce',
                    'disponible',
                ) == 'disponible'
            ):
                from criteres_bienici import (
                    completer_annonce,
                    LectureImpossible,
                    VERSION,
                )

                if source == 'seloger':
                    from seloger_import import (
                        completer_annonce_seloger,
                        VERSION,
                    )

                    completer_annonce = completer_annonce_seloger

                trace = bien.get('extraction_criteres') or {}

                deja_analysee = (
                    trace.get('version') == VERSION
                    and (
                        source != 'seloger'
                        or str(
                            trace.get('source', '')
                        ).startswith('SeLoger')
                    )
                )

                if (
                    not deja_analysee
                    and url not in tentatives
                ):
                    if len(tentatives) >= 20:
                        bilan['criteres_reportes'] += 1

                    else:
                        tentatives.add(url)

                        try:
                            bien, lu = completer_annonce(
                                db,
                                bien,
                            )

                            bilan['criteres_lus'] += int(lu)

                        except LectureImpossible:
                            bilan['criteres_erreurs'] += 1

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

        bilan['messages'] += 1

    return bilan


def completer_biens_bienici(db, limite=20):
    """Reprendre les fiches Bien’ici déjà importées."""

    from criteres_bienici import (
        completer_annonce,
        LectureImpossible,
        VERSION,
    )

    acheteurs = db.get_acquereurs()

    candidats = [
        bien
        for bien in db.get_annonces(actives=True)
        if extraire_url_bienici(bien.get('url'))
        and bien.get(
            'statut_annonce',
            'disponible',
        ) == 'disponible'
        and (
            bien.get('extraction_criteres') or {}
        ).get('version') != VERSION
    ]

    bilan = {
        'analyses': 0,
        'erreurs': 0,
        'restants': max(
            0,
            len(candidats) - limite,
        ),
    }

    for bien in candidats[:limite]:
        try:
            bien, lu = completer_annonce(
                db,
                bien,
            )

        except LectureImpossible:
            bilan['erreurs'] += 1
            continue

        bilan['analyses'] += int(lu)

        recalculer(
            db,
            acquereurs=acheteurs,
            annonces=[bien],
        )

    return bilan


def completer_biens_seloger(db, limite=20):
    """Reprendre les fiches SeLoger déjà importées."""

    from seloger_import import (
        completer_annonce_seloger,
        extraire_url_seloger,
        VERSION,
        LectureImpossible,
    )

    acheteurs = db.get_acquereurs()

    candidats = [
        bien
        for bien in db.get_annonces(actives=True)
        if extraire_url_seloger(bien.get('url'))
        and bien.get(
            'statut_annonce',
            'disponible',
        ) == 'disponible'
        and (
            bien.get('extraction_criteres') or {}
        ).get('version') != VERSION
    ]

    bilan = {
        'analyses': 0,
        'erreurs': 0,
        'restants': max(
            0,
            len(candidats) - limite,
        ),
    }

    for bien in candidats[:limite]:
        try:
            bien, lu = completer_annonce_seloger(
                db,
                bien,
            )

        except LectureImpossible:
            bilan['erreurs'] += 1
            continue

        bilan['analyses'] += int(lu)

        recalculer(
            db,
            acquereurs=acheteurs,
            annonces=[bien],
        )

    return bilan
