"""Application personnelle. Accès privé géré par Streamlit Community Cloud."""
import logging
import streamlit as st
from validation import valider, normaliser_url

LOGGER = logging.getLogger(__name__)

STATUTS = {
    'correspondance': '🟢 Correspondance',
    'a_verifier': '🟠 À vérifier',
    'ecarte': '🔴 Écarté',
    'preference_non_satisfaite': '🟡 Préférence non satisfaite'
}

CHOIX = [
    'Tableau de bord',
    'Acquéreurs',
    'Annonces',
    'Import Bien’ici',
    'Matching',
    'Diagnostic Yahoo'
]


def erreur(message):
    LOGGER.exception(message)
    st.error(
        message
        + ' Vérifiez la configuration et les journaux côté hébergement.'
    )


def cle_champ(nom):
    contexte = st.session_state.get('contexte_formulaire', 'initial')
    return 'champ_' + contexte + '_' + nom


def preparer_formulaire(data, selection):
    """Charger de nouveaux champs à chaque changement de fiche."""
    if st.session_state.get('selection_formulaire_v2') == selection:
        return

    for key in list(st.session_state):
        if key.startswith('champ_'):
            del st.session_state[key]

    revision = st.session_state.get('revision_formulaire', 0) + 1
    st.session_state['revision_formulaire'] = revision
    st.session_state['contexte_formulaire'] = str(revision)
    st.session_state['selection_formulaire_v2'] = selection

    for champ in (
        'prenom', 'nom', 'telephone', 'email', 'secteur', 'notes',
        'titre', 'url', 'source', 'commune', 'description'
    ):
        st.session_state[cle_champ(champ)] = str(data.get(champ) or '')

    entiers = (
        'chambres', 'chambres_rdc', 'salles_eau',
        'chambres_min', 'chambres_rdc_min', 'salles_eau_min'
    )

    decimaux = (
        'prix', 'budget_max', 'marge_budget', 'rayon_km',
        'surface_habitable', 'surface_habitable_min', 'surface_terrain',
        'surface_terrain_souhaitee', 'latitude', 'longitude',
        'latitude_reference', 'longitude_reference'
    )

    for champ in entiers + decimaux:
        valeur = data.get(champ)

        if valeur is not None:
            valeur = int(valeur) if champ in entiers else float(valeur)

        st.session_state[cle_champ(champ)] = valeur

    for champ in (
        'recherche_maison', 'recherche_pavillon', 'recherche_maison_pierre',
        'recherche_appartement', 'plain_pied_obligatoire',
        'garage_obligatoire', 'salle_eau_rdc', 'sous_sol_recherche'
    ):
        valeur = data.get(champ)

        if champ == 'salle_eau_rdc' and selection[0] == 'Annonces':
            st.session_state[cle_champ(champ)] = (
                valeur if isinstance(valeur, bool) else None
            )
        else:
            st.session_state[cle_champ(champ)] = bool(valeur)

    st.session_state[cle_champ('actif')] = bool(data.get('actif', True))

    for champ in ('plain_pied', 'garage', 'sous_sol', 'maison_pierre'):
        valeur = data.get(champ)
        st.session_state[cle_champ(champ)] = (
            valeur if isinstance(valeur, bool) else None
        )

    choix = {
        'type_maison': [
            '', 'maison', 'pavillon', 'maison_pierre', 'appartement'
        ],
        'type_annonceur': [
            'inconnu', 'particulier', 'professionnel'
        ],
        'statut_annonce': [
            'disponible', 'retiree', 'vendue', 'archivee'
        ],
        'dpe': [
            '', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'non_applicable'
        ]
    }

    for champ, options in choix.items():
        valeur = data.get(champ)
        st.session_state[cle_champ(champ)] = (
            valeur if valeur in options else options[0]
        )


def nombre(label, key, data, entier=False):
    return st.number_input(
        label,
        min_value=0 if entier else 0.0,
        value=None,
        step=1 if entier else 1.0,
        key=cle_champ(key)
    )


def coordonnees(data, reference=False):
    suffixe = '_reference' if reference else ''
    values = {}

    for key, label, limite in [
        ('latitude', 'Latitude', 90.0),
        ('longitude', 'Longitude', 180.0)
    ]:
        champ = key + suffixe

        values[champ] = st.number_input(
            label,
            min_value=-limite,
            max_value=limite,
            value=None,
            format='%.6f',
            key=cle_champ(champ)
        )

    return values


def trois_etats(label, key, data):
    return st.selectbox(
        label,
        [None, True, False],
        format_func=lambda x: (
            'Inconnu' if x is None else 'Oui' if x else 'Non'
        ),
        key=cle_champ(key)
    )


def choisir(options, valeur):
    return options.index(valeur) if valeur in options else 0


def formulaire_acquereur(data):
    with st.form(cle_champ('form_acquereur')):
        result = {}

        for key, label in [
            ('prenom', 'Prénom *'),
            ('nom', 'Nom *'),
            ('telephone', 'Téléphone'),
            ('email', 'E-mail'),
            (
                'secteur',
                'Commune(s) recherchée(s), séparées par des virgules'
            )
        ]:
            result[key] = st.text_input(
                label,
                key=cle_champ(key)
            ).strip()

        st.caption(
            'Sans rayon : la commune doit appartenir à cette liste. '
            'Avec rayon : utilisez le centre GPS ci-dessous. '
            'Un secteur vague reste à préciser.'
        )

        for key, label in [
            (
                'budget_max',
                'Budget maximum hors frais d’acquisition (€)'
            ),
            (
                'marge_budget',
                'Marge budgétaire autorisée (€ ; vide = 0)'
            ),
            ('rayon_km', 'Rayon à vol d’oiseau (km)')
        ]:
            result[key] = nombre(label, key, data)

        st.caption(
            'Le budget est comparé au prix affiché ; '
            'les frais d’acquisition et travaux ne sont pas calculés.'
        )

        result.update(coordonnees(data, reference=True))

        st.write('Types acceptés — plusieurs choix possibles')

        for key, label in [
            (
                'recherche_maison',
                'Maison (y compris pavillon et maison en pierre)'
            ),
            ('recherche_pavillon', 'Pavillon'),
            (
                'recherche_maison_pierre',
                'Maison en pierre recherchée'
            ),
            ('recherche_appartement', 'Appartement'),
            ('plain_pied_obligatoire', 'Plain-pied obligatoire'),
            ('garage_obligatoire', 'Garage obligatoire'),
            ('salle_eau_rdc', 'Salle d’eau au RDC obligatoire'),
            ('sous_sol_recherche', 'Sous-sol souhaité')
        ]:
            result[key] = st.checkbox(
                label,
                key=cle_champ(key)
            )

        for key, label in [
            ('chambres_min', 'Chambres minimum (impératif)'),
            ('chambres_rdc_min', 'Chambres au RDC minimum (impératif)'),
            ('salles_eau_min', 'Salles d’eau minimum (impératif)')
        ]:
            result[key] = nombre(label, key, data, entier=True)

        result['surface_habitable_min'] = nombre(
            'Surface habitable minimum (m², impératif)',
            'surface_habitable_min',
            data
        )

        result['surface_terrain_souhaitee'] = nombre(
            'Terrain souhaité minimum (m², préférence)',
            'surface_terrain_souhaitee',
            data
        )

        st.caption(
            'Maison en pierre, sous-sol et terrain sont des préférences. '
            'Les autres minima et obligations sont impératifs. '
            'Une information inconnue reste à vérifier.'
        )

        result['notes'] = st.text_area(
            'Notes (non interprétées par le matching)',
            key=cle_champ('notes')
        )

        result['actif'] = st.checkbox(
            'Recherche active',
            key=cle_champ('actif')
        )

        submitted = st.form_submit_button(
            'Enregistrer et recalculer',
            type='primary'
        )

    return submitted, result


def formulaire_annonce(data):
    with st.form(cle_champ('form_annonce')):
        result = {}

        for key, label in [
            ('titre', 'Titre'),
            ('url', 'URL *'),
            ('source', 'Source'),
            ('commune', 'Commune')
        ]:
            result[key] = st.text_input(
                label,
                key=cle_champ(key)
            ).strip()

        for key, label, options in [
            (
                'type_maison',
                'Type de bien',
                ['', 'maison', 'pavillon', 'maison_pierre', 'appartement']
            ),
            (
                'type_annonceur',
                'Annonceur',
                ['inconnu', 'particulier', 'professionnel']
            ),
            (
                'statut_annonce',
                'Disponibilité',
                ['disponible', 'retiree', 'vendue', 'archivee']
            ),
            (
                'dpe',
                'DPE déclaré (informatif)',
                ['', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'non_applicable']
            )
        ]:
            result[key] = st.selectbox(
                label,
                options,
                key=cle_champ(key)
            ) or None

        for key, label in [
            ('prix', 'Prix affiché (€)'),
            ('surface_habitable', 'Surface habitable (m²)'),
            ('surface_terrain', 'Terrain (m²)')
        ]:
            result[key] = nombre(label, key, data)

        for key, label in [
            ('chambres', 'Chambres'),
            ('chambres_rdc', 'Chambres au RDC'),
            ('salles_eau', 'Salles d’eau')
        ]:
            result[key] = nombre(label, key, data, entier=True)

        for key, label in [
            ('plain_pied', 'Plain-pied'),
            ('garage', 'Garage'),
            ('salle_eau_rdc', 'Salle d’eau au RDC'),
            ('sous_sol', 'Sous-sol'),
            ('maison_pierre', 'Construction en pierre')
        ]:
            result[key] = trois_etats(label, key, data)

        st.caption(
            'Laissez « Inconnu » lorsque l’annonce ne précise pas '
            'une caractéristique. Les champs numériques peuvent '
            'rester vides ; 0 signifie une valeur réellement connue.'
        )

        result.update(coordonnees(data))

        result['description'] = st.text_area(
            'Description (non interprétée automatiquement)',
            key=cle_champ('description')
        )

        submitted = st.form_submit_button(
            'Enregistrer et recalculer',
            type='primary'
        )

    return submitted, result


def editeur(db, acheteurs=False):
    rows = (
        db.get_acquereurs(actif=False)
        if acheteurs
        else db.get_annonces()
    )

    titre = 'Acquéreurs' if acheteurs else 'Annonces'
    st.title(titre)
    by_id = {str(x['id']): x for x in rows}

    def libelle(key):
        if key == '__nouveau__':
            return '➕ Nouvelle fiche'

        d = by_id[key]

        return (
            f'{d.get("prenom", "")} {d.get("nom", "")}'
            if acheteurs
            else d.get('titre') or d.get('url') or 'Sans titre'
        ) + f' — {key}'

    identifiant = st.selectbox(
        'Créer ou modifier',
        ['__nouveau__'] + list(by_id),
        format_func=libelle,
        key='selecteur_' + titre
    )

    data = by_id.get(identifiant, {})
    preparer_formulaire(data, (titre, identifiant))

    if not acheteurs and data:
        if data.get('url'):
            try:
                adresse = normaliser_url(data['url'])
                st.link_button(
                    'Ouvrir l’annonce sur le site',
                    adresse
                )
            except ValueError:
                st.warning(
                    'Cette fiche contient une ancienne URL invalide. '
                    'Vous pouvez la corriger ou archiver la fiche.'
                )

        if data.get('statut_annonce') != 'archivee':
            if st.button(
                'Archiver cette annonce',
                key='archiver_' + str(data['id'])
            ):
                try:
                    db.enregistrer(
                        'annonces',
                        {'statut_annonce': 'archivee'},
                        data['id']
                    )
                except Exception:
                    erreur('Archivage impossible.')
                    return

                st.session_state.pop('selection_formulaire_v2', None)
                st.rerun()

    st.caption(
        'Le choix dans la liste charge la fiche. '
        'Enregistrer sert uniquement à sauvegarder vos modifications.'
    )

    if acheteurs:
        submitted, result = formulaire_acquereur(data)
    else:
        submitted, result = formulaire_annonce(data)

    if not submitted:
        return

    try:
        result = valider(result, acquereur=acheteurs)

        if not acheteurs and result.get('prix') == 0:
            raise ValueError(
                'Prix : laissez vide si inconnu ; '
                'un prix connu doit être supérieur à zéro.'
            )

        if acheteurs and result.get('budget_max') == 0:
            raise ValueError(
                'Budget : laissez vide si inconnu ; '
                'un budget connu doit être supérieur à zéro.'
            )

        if not acheteurs:
            existante = db.get_annonce_by_url(result['url'])

            if existante and str(existante['id']) != identifiant:
                raise ValueError(
                    'Cette URL existe déjà. Sélectionnez '
                    'la fiche existante pour la modifier.'
                )

        saved = db.enregistrer(
            'acquereurs' if acheteurs else 'annonces',
            result,
            data.get('id')
        )

    except ValueError as exc:
        st.error(str(exc))
        return

    except Exception:
        erreur('La fiche n’a pas pu être enregistrée.')
        return

    st.success('Fiche enregistrée.')

    from services import recalculer

    try:
        if acheteurs:
            count = recalculer(db, acquereurs=[saved])
        else:
            count = recalculer(db, annonces=[saved])

        st.success(
            f'{count} comparaison(s) actualisée(s). '
            'Le suivi commercial est conservé.'
        )

        st.caption(
            'Pour actualiser la liste des fiches, '
            'changez de rubrique puis revenez.'
        )

    except Exception:
        erreur(
            'La fiche est enregistrée, mais le matching est incomplet. '
            'Utilisez « Recalculer tous les matches ».'
        )


def import_bienici(db):
    from email_import import (
        get_bienici_emails,
        extraire_liens_bienici,
        liens_non_resolus
    )
    from services import importer_emails

    st.title('Import Bien’ici')

    st.info(
        'Import des alertes Bien’ici : lien, titre, prix, commune '
        'et surface sont récupérés lorsqu’ils sont présents '
        'dans l’e-mail. Les autres critères restent à compléter '
        'dans Annonces.'
    )

    limite = st.number_input(
        'Nombre des derniers e-mails à examiner',
        min_value=1,
        max_value=5000,
        value=100,
        step=50
    )

    st.caption(
        'Augmentez la limite pour reprendre des messages anciens. '
        'Seule INBOX est examinée, sans marquer les messages comme lus.'
    )

    if st.button('Lire les alertes Yahoo'):
        try:
            with st.spinner('Lecture des alertes…'):
                st.session_state['emails_preview'] = (
                    get_bienici_emails(int(limite))
                )
        except Exception:
            erreur('Impossible de lire les e-mails Yahoo.')

    items = st.session_state.get('emails_preview', [])

    for item in items:
        texte = item['text_body'] + '\n' + item['html_body']

        with st.expander(item['subject'] or 'Alerte sans objet'):
            st.write(item['date'])

            for url in extraire_liens_bienici(texte):
                st.link_button('Ouvrir l’annonce', url)

            unresolved = liens_non_resolus(texte)

            if unresolved:
                st.warning(
                    f'{len(unresolved)} lien(s) de suivi non décodé(s). '
                    'Ils nécessitent un exemple d’e-mail anonymisé '
                    'pour adapter l’extracteur.'
                )

    if items and st.button(
        'Importer les liens et lancer le matching',
        type='primary'
    ):
        try:
            with st.spinner('Enregistrement…'):
                bilan = importer_emails(db, items)

            st.success(
                f'{bilan["nouveaux"]} nouvelle(s) annonce(s), '
                f'{bilan["existants"]} lien(s) déjà présent(s), '
                f'{bilan["enrichis"]} fiche(s) complétée(s), '
                f'{bilan["deja_traites"]} e-mail(s) déjà traité(s).'
            )

            if bilan['non_resolus'] or bilan['sans_annonce']:
                st.warning(
                    f'{bilan["non_resolus"]} lien(s) non décodé(s) ; '
                    f'{bilan["sans_annonce"]} e-mail(s) sans annonce '
                    'reconnue. Ces messages restent à reprendre.'
                )

            st.caption(
                'Les informations absentes de l’e-mail restent '
                'inconnues. Vérifiez les fiches dans Annonces '
                'avant de proposer un bien.'
            )

        except Exception:
            erreur(
                'Import interrompu. Les annonces déjà enregistrées '
                'sont conservées ; relancez l’import pour reprendre.'
            )


def page_matching(db):
    from services import recalculer

    st.title('Matching')

    if st.button('Recalculer tous les matches'):
        try:
            with st.spinner('Recalcul…'):
                count = recalculer(db)

            st.success(f'{count} comparaison(s) actualisée(s).')

        except Exception:
            erreur(
                'Recalcul incomplet ; il peut être relancé '
                'sans perdre le suivi commercial.'
            )

    acheteurs = {
        str(a['id']): a
        for a in db.get_acquereurs()
    }

    biens = {
        str(a['id']): a
        for a in db.get_annonces(actives=True)
    }

    selection = st.selectbox(
        'Acquéreur',
        ['Tous'] + list(acheteurs),
        format_func=lambda x: (
            x if x == 'Tous'
            else (
                f'{acheteurs[x].get("prenom", "")} '
                f'{acheteurs[x].get("nom", "")} — {x}'
            )
        )
    )

    statut_filtre = st.selectbox(
        'Résultat',
        ['Tous'] + list(STATUTS),
        format_func=lambda x: STATUTS.get(x, x)
    )

    vendeur = st.selectbox(
        'Annonceur',
        ['Tous', 'particulier', 'professionnel', 'inconnu']
    )

    matches = [
        m for m in db.get_matches()
        if str(m['acquereur_id']) in acheteurs
        and str(m['annonce_id']) in biens
    ]

    matches.sort(
        key=lambda m: (
            m.get('couverture') or 0,
            m.get('score') or 0
        ),
        reverse=True
    )

    visibles = 0

    for m in matches:
        aid = str(m['acquereur_id'])
        bid = str(m['annonce_id'])
        a = acheteurs[aid]
        b = biens[bid]

        if selection != 'Tous' and aid != selection:
            continue

        if (
            statut_filtre != 'Tous'
            and m['statut_matching'] != statut_filtre
        ):
            continue

        if (
            vendeur != 'Tous'
            and (b.get('type_annonceur') or 'inconnu') != vendeur
        ):
            continue

        visibles += 1

        titre_resultat = (
            f'{STATUTS.get(m["statut_matching"], m["statut_matching"])}'
            f' · {a.get("prenom", "")} {a.get("nom", "")}'
            f' · {b.get("titre") or b.get("url")}'
        )

        with st.expander(titre_resultat):
            score_affiche = (
                'non calculable'
                if m.get('score') is None
                else f'{m["score"]} %'
            )

            st.write(
                f'Adéquation sur critères connus : {score_affiche}'
                f' · Critères vérifiés : '
                f'{m.get("couverture") if m.get("couverture") is not None else "à recalculer"} %'
            )

            st.caption(
                'Ces pourcentages ne représentent pas une probabilité '
                'd’achat. Le statut tient compte des incompatibilités '
                'impératives et des données manquantes.'
            )

            if b.get('url'):
                st.link_button('Voir le bien', b['url'])

            for d in m.get('details_matching') or []:
                st.write(
                    f'{STATUTS.get(d["statut"], d["statut"])}'
                    f' — {d["critere"]} : {d["message"]}'
                )

            suivi = [
                'nouveau', 'a_contacter', 'propose',
                'visite', 'refuse', 'clos'
            ]

            if m.get('statut') and m['statut'] not in suivi:
                suivi.insert(0, m['statut'])

            with st.form('suivi_' + str(m['id'])):
                statut = st.selectbox(
                    'Suivi commercial',
                    suivi,
                    index=choisir(suivi, m.get('statut'))
                )

                commentaire = st.text_area(
                    'Commentaire',
                    value=m.get('commentaire') or ''
                )

                if st.form_submit_button('Enregistrer le suivi'):
                    try:
                        db.enregistrer(
                            'matches',
                            {
                                'statut': statut,
                                'commentaire': commentaire
                            },
                            m['id']
                        )
                        st.success('Suivi enregistré.')

                    except Exception:
                        erreur('Suivi non enregistré.')

    if not visibles:
        st.info(
            'Aucun résultat pour ces filtres. '
            'Complétez les fiches ou lancez un recalcul.'
        )


def diagnostic_yahoo():
    st.title('Diagnostic Yahoo')

    if st.button('Tester la connexion Yahoo'):
        from email_import import get_yahoo_connection

        try:
            mail = get_yahoo_connection()
            mail.logout()
            st.success('Connexion Yahoo réussie.')

        except Exception:
            erreur(
                'Connexion Yahoo impossible. Vérifiez l’adresse '
                'et le mot de passe d’application.'
            )


def main(default='Tableau de bord'):
    st.set_page_config(
        page_title='Chasseur Immo',
        page_icon='🏡',
        layout='wide'
    )

    st.sidebar.title('🏡 Chasseur Immo')

    page = st.sidebar.radio(
        'Navigation',
        CHOIX,
        index=choisir(CHOIX, default)
    )

    import database as db

    try:
        if page == 'Acquéreurs':
            editeur(db, acheteurs=True)

        elif page == 'Annonces':
            editeur(db)

        elif page == 'Import Bien’ici':
            import_bienici(db)

        elif page == 'Matching':
            page_matching(db)

        elif page == 'Diagnostic Yahoo':
            diagnostic_yahoo()

        else:
            st.title('Tableau de bord')

            acheteurs = db.get_acquereurs()
            biens = db.get_annonces(actives=True)

            aids = {str(a['id']) for a in acheteurs}
            bids = {str(b['id']) for b in biens}

            matches = [
                m for m in db.get_matches()
                if str(m['acquereur_id']) in aids
                and str(m['annonce_id']) in bids
            ]

            cols = st.columns(3)

            cols[0].metric('Acquéreurs actifs', len(acheteurs))
            cols[1].metric('Annonces disponibles', len(biens))
            cols[2].metric(
                'Correspondances confirmées',
                sum(
                    m['statut_matching'] == 'correspondance'
                    for m in matches
                )
            )

            st.write('Dernières annonces disponibles')

            for bien in sorted(
                biens,
                key=lambda b: b.get('imported_at') or '',
                reverse=True
            )[:10]:
                st.write(
                    bien.get('titre') or 'Annonce à compléter'
                )

                st.write(
                    f'{bien.get("commune") or "Commune inconnue"}'
                    f' · {bien.get("prix") if bien.get("prix") is not None else "Prix inconnu"}'
                )

                if bien.get('url'):
                    st.link_button('Ouvrir', bien['url'])

    except Exception:
        erreur(
            'Chargement impossible. Exécutez la migration SQL '
            'et vérifiez les secrets Supabase.'
        )


if __name__ == '__main__':
    main()
