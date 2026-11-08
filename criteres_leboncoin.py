"""Analyser un descriptif Leboncoin collé par l’utilisateur."""

from criteres_bienici import analyser_criteres, CHAMPS
from leboncoin_import import extraire_url_leboncoin


def completer_depuis_description(db, bien, description):
    """Enregistrer le texte et compléter les critères inconnus."""

    if (
        not bien.get('id')
        or not extraire_url_leboncoin(bien.get('url'))
    ):
        raise ValueError(
            'Sélectionnez une annonce Leboncoin déjà enregistrée.'
        )

    texte = str(description or '').strip()

    if len(texte) < 20:
        raise ValueError(
            'Collez le descriptif complet de cette annonce '
            '(au moins 20 caractères).'
        )

    if len(texte) > 100000:
        raise ValueError(
            'Le texte est trop long. Collez uniquement '
            'le descriptif de cette annonce.'
        )

    valeurs = analyser_criteres(
        {'description': texte}
    )

    trace = valeurs['extraction_criteres']
    trace['source'] = 'Leboncoin — texte collé'
    trace['mode'] = 'copie_manuelle'

    changements = {
        'description': valeurs.get('description') or texte,
        'extraction_criteres': trace,
    }

    completes = []
    conserves = []
    a_verifier = []

    for champ in CHAMPS:
        if champ not in valeurs:
            a_verifier.append(champ)
            continue

        if bien.get(champ) is None or bien.get(champ) == '':
            changements[champ] = valeurs[champ]
            completes.append(champ)

        elif bien[champ] != valeurs[champ]:
            conserves.append(champ)

    total = (
        bien.get('chambres')
        if bien.get('chambres') is not None
        else changements.get('chambres')
    )

    rdc = (
        bien.get('chambres_rdc')
        if bien.get('chambres_rdc') is not None
        else changements.get('chambres_rdc')
    )

    if (
        total is not None
        and rdc is not None
        and rdc > total
    ):
        for champ in ('chambres', 'chambres_rdc'):
            if champ in changements:
                changements.pop(champ)
                completes.remove(champ)

                if champ not in a_verifier:
                    a_verifier.append(champ)

                trace['preuves'][champ] = [
                    {
                        'valeur': None,
                        'extrait': (
                            'Nombre total et nombre au RDC '
                            'incompatibles : à vérifier.'
                        ),
                    }
                ]

    nouvelle = db.enregistrer(
        'annonces',
        changements,
        bien['id'],
    )

    if not nouvelle:
        raise RuntimeError(
            'Enregistrement du descriptif non confirmé.'
        )

    return {
        'bien': nouvelle,
        'completes': completes,
        'conserves': conserves,
        'a_verifier': a_verifier,
    }
