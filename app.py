"""Application personnelle. Accès privé géré par Streamlit Community Cloud."""
import logging
import streamlit as st
from validation import valider, normaliser_url
from interface import (
    PAGES, SOURCES, appliquer_style, marque, aller,
    euros, libelle_annonce, carte_annonce,
    filtrer_annonces, tableau_de_bord,
)

LOGGER = logging.getLogger(__name__)
STATUTS = {
    'correspondance': '🟢 Correspondance',
    'a_verifier': '🟠 À vérifier',
    'ecarte': '🔴 Écarté',
    'preference_non_satisfaite': '🟡 Préférence non satisfaite',
}
CHOIX = PAGES


def erreur(message):
    LOGGER.exception(message)
    st.error(message + ' Vérifiez la configuration et les journaux côté hébergement.')


def cle_champ(nom):
    contexte = st.session_state.get('contexte_formulaire', 'initial')
    return 'champ_' + contexte + '_' + nom


def preparer_formulaire(data, selection):
    """Créer des champs neufs et charger leurs valeurs à chaque changement de fiche."""
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
        'titre', 'url', 'source', 'commune', 'description',
    ):
        st.session_state[cle_champ(champ)] = str(data.get(champ) or '')

    entiers = (
        'chambres', 'chambres_rdc', 'salles_eau',
        'chambres_min', 'chambres_rdc_min', 'salles_eau_min',
    )
    decimaux = (
        'prix', 'budget_max', 'marge_budget', 'rayon_km',
        'surface_habitable', 'surface_habitable_min', 'surface_terrain',
        'surface_terrain_souhaitee', 'latitude', 'longitude',
        'latitude_reference', 'longitude_reference',
    )

    for champ in entiers + decimaux:
        valeur = data.get(champ)
        if valeur is not None:
            valeur = int(valeur) if champ in entiers else float(valeur)
        st.session_state[cle_champ(champ)] = valeur

    for champ in (
        'recherche_maison', 'recherche_pavillon', 'recherche_maison_pierre',
        'recherche_appartement', 'plain_pied_obligatoire',
        'garage_obligatoire', 'salle_eau_rdc', 'salle_bain_rdc',
        'sous_sol_recherche',
    ):
        valeur = data.get(champ)
        if champ in ('salle_eau_rdc', 'salle_bain_rdc') and selection[0] == 'Annonces':
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
        'type_maison': ['', 'maison', 'pavillon', 'maison_pierre', 'appartement'],
        'type_annonceur': ['inconnu', 'particulier', 'professionnel'],
        'statut_annonce': ['disponible', 'retiree', 'vendue', 'archivee'],
        'dpe': ['', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'non_applicable'],
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
        key=cle_champ(key),
    )


def coordonnees(data, reference=False):
    suffixe = '_reference' if reference else ''
    values = {}

    for key, label, limite in (
        ('latitude', 'Latitude', 90.0),
        ('longitude', 'Longitude', 180.0),
    ):
        champ = key + suffixe
        values[champ] = st.number_input(
            label,
            min_value=-limite,
            max_value=limite,
            value=None,
            format='%.6f',
            key=cle_champ(champ),
        )

    return values


def trois_etats(label, key, data):
    return st.selectbox(
        label,
        [None, True, False],
        format_func=lambda x: 'Inconnu' if x is None else 'Oui' if x else 'Non',
        key=cle_champ(key),
    )


def choisir(options, valeur):
    return options.index(valeur) if valeur in options else 0


def formulaire_acquereur(data):
    with st.form(cle_champ('form_acquereur')):
        result = {}
        st.markdown('### Coordonnées de l’acquéreur')
        colonnes_identite = st.columns(2)

        for i, (key, label) in enumerate([
            ('prenom', 'Prénom *'),
            ('nom', 'Nom *'),
            ('telephone', 'Téléphone'),
            ('email', 'E-mail'),
            ('secteur', 'Commune(s) recherchée(s), séparées par des virgules'),
        ]):
            zone = st if key == 'secteur' else colonnes_identite[i % 2]
            result[key] = zone.text_input(label, key=cle_champ(key)).strip()

        st.caption(
            'Sans rayon : indiquez les communes acceptées. Avec rayon : indiquez '
            'une seule commune de départ, par exemple Alençon (61). Son centre '
            'sera utilisé automatiquement ; vous pouvez aussi préciser un point GPS ci-dessous.'
        )

        st.markdown('### Budget et secteur')
        colonnes_budget = st.columns(3)

        for i, (key, label) in enumerate([
            ('budget_max', 'Budget maximum hors frais d’acquisition (€)'),
            ('marge_budget', 'Marge budgétaire autorisée (€ ; vide = 0)'),
            ('rayon_km', 'Rayon à vol d’oiseau (km)'),
        ]):
            with colonnes_budget[i]:
                result[key] = nombre(label, key, data)

        st.caption(
            'Le budget est comparé au prix affiché ; '
            'les frais d’acquisition et travaux ne sont pas calculés.'
        )

        with st.expander('Point de départ GPS — facultatif'):
            st.caption(
                'Laissez vide pour utiliser automatiquement '
                'le centre de la commune recherchée.'
            )
            result.update(coordonnees(data, reference=True))

        st.markdown('### Critères de recherche')
        st.caption('Plusieurs types de biens peuvent être acceptés.')
        colonnes_criteres = st.columns(2)

        for i, (key, label) in enumerate([
            ('recherche_maison', 'Maison (y compris pavillon et maison en pierre)'),
            ('recherche_pavillon', 'Pavillon'),
            ('recherche_maison_pierre', 'Maison en pierre recherchée'),
            ('recherche_appartement', 'Appartement'),
            ('plain_pied_obligatoire', 'Plain-pied obligatoire'),
            ('garage_obligatoire', 'Garage obligatoire'),
            ('salle_eau_rdc', 'Salle d’eau au RDC obligatoire'),
            ('salle_bain_rdc', 'Salle de bains au RDC obligatoire'),
            ('sous_sol_recherche', 'Sous-sol souhaité'),
        ]):
            result[key] = colonnes_criteres[i % 2].checkbox(
                label, key=cle_champ(key)
            )

        colonnes_minimums = st.columns(3)

        for i, (key, label) in enumerate([
            ('chambres_min', 'Chambres minimum (impératif)'),
            ('chambres_rdc_min', 'Chambres au RDC minimum (impératif)'),
            ('salles_eau_min', 'Salles d’eau minimum (impératif)'),
        ]):
            with colonnes_minimums[i]:
                result[key] = nombre(label, key, data, entier=True)

        result['surface_habitable_min'] = nombre(
            'Surface habitable minimum (m², impératif)',
            'surface_habitable_min',
            data,
        )
        result['surface_terrain_souhaitee'] = nombre(
            'Terrain souhaité minimum (m², préférence)',
            'surface_terrain_souhaitee',
            data,
        )

        st.caption(
            'Maison en pierre, sous-sol et terrain sont des préférences. '
            'Les autres minima et obligations sont impératifs. '
            'Une information inconnue reste à vérifier.'
        )
        result['notes'] = st.text_area(
            'Notes (non interprétées par le matching)',
            key=cle_champ('notes'),
        )
        result['actif'] = st.checkbox(
            'Recherche active', key=cle_champ('actif')
        )
        submitted = st.form_submit_button(
            'Enregistrer et recalculer', type='primary'
        )

    return submitted, result


def formulaire_annonce(data):
    with st.form(cle_champ('form_annonce')):
        result = {}
        st.markdown('### Le bien')
        colonnes_identite = st.columns(2)

        for key, label in (
            ('titre', 'Titre'),
            ('url', 'URL *'),
            ('source', 'Source'),
            ('commune', 'Commune'),
        ):
            zone = (
                colonnes_identite[0] if key == 'source'
                else colonnes_identite[1] if key == 'commune'
                else st
            )
            result[key] = zone.text_input(
                label, key=cle_champ(key)
            ).strip()

        colonnes_type = st.columns(2)

        for i, (key, label, options) in enumerate([
            (
                'type_maison',
                'Type de bien',
                ['', 'maison', 'pavillon', 'maison_pierre', 'appartement'],
            ),
            (
                'type_annonceur',
                'Annonceur',
                ['inconnu', 'particulier', 'professionnel'],
            ),
            (
                'statut_annonce',
                'Disponibilité',
                ['disponible', 'retiree', 'vendue', 'archivee'],
            ),
            (
                'dpe',
                'DPE déclaré (informatif)',
                ['', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'non_applicable'],
            ),
        ]):
            result[key] = colonnes_type[i % 2].selectbox(
                label, options, key=cle_champ(key)
            ) or None

        colonnes_prix = st.columns(3)

        for i, (key, label) in enumerate([
            ('prix', 'Prix affiché (€)'),
            ('surface_habitable', 'Surface habitable (m²)'),
            ('surface_terrain', 'Terrain (m²)'),
        ]):
            with colonnes_prix[i]:
                result[key] = nombre(label, key, data)

        st.markdown('### Les critères utiles aux acquéreurs')
        colonnes_chambres = st.columns(3)

        for i, (key, label) in enumerate([
            ('chambres', 'Chambres'),
            ('chambres_rdc', 'Chambres au RDC'),
            ('salles_eau', 'Salles d’eau'),
        ]):
            with colonnes_chambres[i]:
                result[key] = nombre(label, key, data, entier=True)

        colonnes_equipements = st.columns(2)

        for i, (key, label) in enumerate([
            ('plain_pied', 'Plain-pied'),
            ('garage', 'Garage'),
            ('salle_eau_rdc', 'Salle d’eau au RDC'),
            ('salle_bain_rdc', 'Salle de bains au RDC'),
            ('sous_sol', 'Sous-sol'),
            ('maison_pierre', 'Construction en pierre'),
        ]):
            with colonnes_equipements[i % 2]:
                result[key] = trois_etats(label, key, data)

        st.caption(
            'Laissez « Inconnu » lorsque l’annonce ne précise pas une caractéristique. '
            'Les champs numériques peuvent rester vides ; 0 signifie une valeur réellement connue. '
            'Sans coordonnées GPS, la commune est localisée au recalcul ; '
            'en cas d’homonyme, précisez le département, par exemple Pacé (61).'
        )

        with st.expander('Coordonnées GPS — facultatif'):
            result.update(coordonnees(data))

        with st.expander(
            'Description de la fiche',
            expanded=bool(data.get('description')),
        ):
            result['description'] = st.text_area(
                'Description (non interprétée automatiquement)',
                key=cle_champ('description'),
                height=160,
            )

        submitted = st.form_submit_button(
            'Enregistrer et recalculer', type='primary'
        )

    return submitted, result


def editeur(db, acheteurs=False):
    rows = (
        db.get_acquereurs(actif=False)
        if acheteurs else db.get_annonces()
    )
    titre = 'Acquéreurs' if acheteurs else 'Annonces'
    st.title(titre)

    if acheteurs and st.session_state.pop('acquereur_supprime', None):
        st.session_state.pop('selecteur_Acquéreurs', None)
        st.session_state.pop('selection_formulaire_v2', None)
        st.success(
            'Acquéreur et correspondances liées supprimés définitivement.'
        )

    if not acheteurs:
        retour = st.session_state.pop('retour_analyse_leboncoin', None)
        if retour:
            st.success(
                f'Descriptif enregistré : {retour["nombre"]} critère(s) complété(s).'
            )
            if retour['conserves']:
                st.info(
                    'Certaines valeurs déjà renseignées diffèrent du texte : '
                    'elles ont été conservées. Vérifiez les extraits '
                    'et corrigez la fiche si nécessaire.'
                )
            if retour['nombre'] == 0:
                st.info(
                    'Aucun nouveau critère rempli : les valeurs sont déjà renseignées '
                    'ou le texte ne permet pas de les déterminer avec certitude.'
                )
            if retour['matching']:
                st.success('Matching actualisé.')
            else:
                st.warning(
                    'Le descriptif et les critères sont enregistrés, mais le matching '
                    'est incomplet. Utilisez « Recalculer tous les matches » dans Matching.'
                )

    if not acheteurs and st.session_state.pop('annonce_supprimee', None):
        st.session_state.pop('selecteur_Annonces', None)
        st.session_state.pop('selection_formulaire_v2', None)
        st.success(
            'Annonce et correspondances liées supprimées définitivement.'
        )

    if acheteurs:
        recherche = st.text_input(
            'Rechercher un acquéreur',
            placeholder='Nom, prénom ou commune…',
            key='recherche_acquereurs',
        )
        from matching import normaliser_texte

        mots = normaliser_texte(recherche).split()
        rows = [
            a for a in rows
            if all(
                m in normaliser_texte(' '.join(
                    str(a.get(k) or '')
                    for k in ('prenom', 'nom', 'secteur')
                ))
                for m in mots
            )
        ]
        st.caption(
            f'{len(rows)} fiche(s). Sélectionnez une personne '
            'ou créez une nouvelle fiche.'
        )
    else:
        rows = filtrer_annonces(rows)

    by_id = {str(x['id']): x for x in rows}

    def libelle(key):
        if key == '__nouveau__':
            return '➕ Nouvelle fiche'
        d = by_id[key]
        texte = (
            f'{d.get("prenom", "")} {d.get("nom", "")}'
            + (' · inactive' if not d.get('actif', True) else '')
            if acheteurs else libelle_annonce(d)
        )
        doublons = [
            k for k, valeur in by_id.items()
            if (
                f'{valeur.get("prenom", "")} {valeur.get("nom", "")}'
                + (' · inactive' if not valeur.get('actif', True) else '')
                if acheteurs else libelle_annonce(valeur)
            ) == texte
        ]
        return texte + (
            f' · fiche {doublons.index(key) + 1}'
            if len(doublons) > 1 else ''
        )

    cle_selection = 'selecteur_' + titre
    if (
        st.session_state.get(cle_selection, '__nouveau__')
        not in ['__nouveau__'] + list(by_id)
    ):
        st.session_state.pop(cle_selection, None)

    identifiant = st.selectbox(
        'Créer ou modifier',
        ['__nouveau__'] + list(by_id),
        format_func=libelle,
        key='selecteur_' + titre,
    )
    data = by_id.get(identifiant, {})
    preparer_formulaire(data, (titre, identifiant))

    if data and not acheteurs:
        carte_annonce(data)

    if acheteurs and data:
        with st.expander('Supprimer définitivement cet acquéreur'):
            st.warning(
                'Cette action efface cet acquéreur et toutes ses correspondances, '
                'y compris leur suivi commercial. Elle est irréversible. '
                'Les annonces sont conservées.'
            )
            with st.form('suppression_acquereur_' + str(data['id'])):
                confirme = st.checkbox(
                    'Je confirme la suppression définitive de cet acquéreur',
                    key='confirmer_suppression_acquereur_' + str(data['id']),
                )
                supprimer = st.form_submit_button(
                    'Supprimer définitivement cet acquéreur'
                )
            if supprimer:
                if not confirme:
                    st.error(
                        'Cochez la confirmation pour supprimer cet acquéreur.'
                    )
                else:
                    try:
                        db.supprimer_acquereur(data['id'])
                    except Exception:
                        erreur('Suppression de l’acquéreur impossible.')
                        return
                    st.session_state['acquereur_supprime'] = str(data['id'])
                    st.rerun()

    if not acheteurs and data:
        from leboncoin_import import extraire_url_leboncoin
        from seloger_import import extraire_url_seloger
        from figaro_import import extraire_url_figaro

        source_texte = (
            'figaro' if extraire_url_figaro(data.get('url'))
            else 'seloger' if extraire_url_seloger(data.get('url'))
            else 'leboncoin' if extraire_url_leboncoin(data.get('url'))
            else None
        )

        if source_texte:
            nom_texte = {
                'seloger': 'SeLoger',
                'leboncoin': 'Leboncoin',
                'figaro': 'Figaro Immobilier',
            }[source_texte]

            with st.expander(
                'Compléter les critères depuis le descriptif ' + nom_texte,
                expanded=not bool(data.get('description')),
            ):
                st.caption(
                    'Ouvrez cette annonce sur ' + nom_texte
                    + ', copiez uniquement son descriptif, puis collez-le ici. '
                    'Le bouton enregistre le texte, complète les critères inconnus '
                    'et recalcule le matching. Les valeurs déjà renseignées sont conservées ; '
                    'les informations ambiguës restent à vérifier.'
                )
                with st.form(
                    'analyse_' + source_texte + '_' + str(data['id'])
                ):
                    texte_colle = st.text_area(
                        'Descriptif complet à analyser',
                        value=data.get('description') or '',
                        height=220,
                        max_chars=100000,
                        key='texte_' + source_texte + '_' + str(data['id']),
                    )
                    analyser = st.form_submit_button(
                        'Analyser et compléter', type='primary'
                    )

                if analyser:
                    from criteres_leboncoin import completer_depuis_description

                    if source_texte == 'seloger':
                        from seloger_import import completer_description_seloger
                        completer_depuis_description = completer_description_seloger
                    elif source_texte == 'figaro':
                        from figaro_import import completer_description_figaro
                        completer_depuis_description = completer_description_figaro

                    from services import recalculer

                    try:
                        resultat = completer_depuis_description(
                            db, data, texte_colle
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        erreur(
                            'Analyse ou enregistrement du descriptif impossible.'
                        )
                    else:
                        matching_ok = True
                        try:
                            recalculer(db, annonces=[resultat['bien']])
                        except Exception:
                            LOGGER.exception(
                                'Descriptif enregistré, matching incomplet.'
                            )
                            matching_ok = False

                        st.session_state['retour_analyse_leboncoin'] = {
                            'nombre': len(resultat['completes']),
                            'conserves': bool(resultat['conserves']),
                            'matching': matching_ok,
                        }
                        st.session_state.pop(
                            'selection_formulaire_v2', None
                        )
                        st.rerun()

        trace = data.get('extraction_criteres') or {}
        if trace:
            with st.expander(
                'Informations extraites du descriptif '
                + str(trace.get('source') or 'Bien’ici')
            ):
                st.caption(
                    'Les extraits justifient l’analyse automatique. '
                    'Vos valeurs déjà renseignées sont conservées. '
                    'Les critères sans mention explicite restent inconnus.'
                )
                noms = {
                    'chambres': 'Chambres',
                    'chambres_rdc': 'Chambres au RDC',
                    'garage': 'Garage',
                    'plain_pied': 'Plain-pied',
                    'salle_eau_rdc': 'Salle d’eau au RDC',
                    'salle_bain_rdc': 'Salle de bains au RDC',
                }
                for champ, preuves in trace.get('preuves', {}).items():
                    for preuve in preuves:
                        valeur = preuve.get('valeur')
                        affiche = (
                            'À vérifier' if valeur is None
                            else 'Oui' if valeur is True
                            else 'Non' if valeur is False
                            else str(valeur)
                        )
                        st.write(noms.get(champ, champ) + ' : ' + affiche)
                        st.caption(preuve.get('extrait') or '')

        if data.get('url'):
            try:
                adresse = normaliser_url(data['url'])
                st.link_button('Ouvrir l’annonce sur le site', adresse)
            except ValueError:
                st.warning(
                    'Cette fiche contient une ancienne URL invalide. '
                    'Vous pouvez la corriger ou archiver la fiche.'
                )

        if data.get('statut_annonce') != 'archivee':
            if st.button(
                'Archiver cette annonce',
                key='archiver_' + str(data['id']),
            ):
                try:
                    db.enregistrer(
                        'annonces',
                        {'statut_annonce': 'archivee'},
                        data['id'],
                    )
                except Exception:
                    erreur('Archivage impossible.')
                    return
                st.session_state.pop('selection_formulaire_v2', None)
                st.rerun()

        with st.expander('Supprimer définitivement cette annonce'):
            st.warning(
                'Cette action efface cette annonce et toutes ses correspondances, '
                'y compris leur suivi commercial. Elle est irréversible. '
                'L’annonce reste publiée sur son site d’origine.'
            )
            with st.form('suppression_' + str(data['id'])):
                confirme = st.checkbox(
                    'Je confirme la suppression définitive de cette annonce',
                    key='confirmer_suppression_' + str(data['id']),
                )
                supprimer = st.form_submit_button(
                    'Supprimer définitivement'
                )
            if supprimer:
                if not confirme:
                    st.error(
                        'Cochez la confirmation pour supprimer cette annonce.'
                    )
                else:
                    try:
                        db.supprimer_annonce(data['id'])
                    except Exception:
                        erreur('Suppression impossible.')
                        return
                    st.session_state['annonce_supprimee'] = str(data['id'])
                    st.rerun()

    st.caption(
        'Le choix dans la liste charge la fiche. '
        'Enregistrer sert uniquement à sauvegarder vos modifications.'
    )
    submitted, result = (
        formulaire_acquereur(data) if acheteurs
        else formulaire_annonce(data)
    )

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
                    'Cette URL existe déjà. '
                    'Sélectionnez la fiche existante pour la modifier.'
                )

        saved = db.enregistrer(
            'acquereurs' if acheteurs else 'annonces',
            result,
            data.get('id'),
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
        count = (
            recalculer(db, acquereurs=[saved])
            if acheteurs else recalculer(db, annonces=[saved])
        )
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
    import_alertes(db, source='bienici')


def import_alertes(db, source='bienici'):
    from email_import import (
        get_emails_alertes,
        extraire_liens_bienici,
        liens_non_resolus,
    )
    from services import (
        importer_emails,
        completer_biens_bienici,
        completer_biens_seloger,
        completer_biens_figaro,
    )

    if source == 'leboncoin':
        from leboncoin_import import (
            extraire_liens_leboncoin,
            liens_leboncoin_non_resolus,
            nombre_annoncees_leboncoin,
        )
        nom = 'Leboncoin'
        extraire_liens = extraire_liens_leboncoin
    elif source == 'seloger':
        from seloger_import import (
            preparer_emails_seloger,
            extraire_annonces_seloger,
            liens_seloger_non_resolus,
        )
        nom = 'SeLoger'
        extraire_liens = None
    elif source == 'figaro':
        from figaro_import import (
            extraire_annonces_figaro,
            liens_figaro_non_resolus,
        )
        nom = 'Figaro Immobilier'
        extraire_liens = None
    else:
        nom = 'Bien’ici'
        extraire_liens = extraire_liens_bienici

    st.subheader(nom)
    st.caption(
        '1. Lisez vos alertes Yahoo.  2. Vérifiez les liens.  '
        '3. Importez pour actualiser les correspondances.'
    )

    with st.expander('Quelles informations sont récupérées ?'):
        st.write(
            'Les informations écrites dans les alertes sont récupérées : '
            'lien, titre, prix, commune et surfaces lorsqu’ils sont présents. '
            'Les caractéristiques non précisées restent inconnues.'
        )

    if source in ('bienici', 'seloger', 'figaro'):
        st.caption(
            'Le descriptif est analysé lorsqu’il est accessible, '
            'jusqu’à 20 annonces par import. Sinon, vous pouvez le coller '
            'dans la fiche. Les valeurs déjà connues sont conservées.'
        )

        if st.button(
            'Compléter les annonces ' + nom + ' déjà enregistrées'
        ):
            try:
                with st.spinner('Lecture des descriptifs ' + nom + '…'):
                    fonction = {
                        'bienici': completer_biens_bienici,
                        'seloger': completer_biens_seloger,
                        'figaro': completer_biens_figaro,
                    }[source]
                    resultat = fonction(db)

                st.success(
                    f'{resultat["analyses"]} descriptif(s) analysé(s), '
                    'matching actualisé.'
                )
                if resultat['erreurs']:
                    st.warning(
                        f'{resultat["erreurs"]} descriptif(s) inaccessible(s). '
                        'Les fiches sont conservées et pourront être reprises.'
                    )
                    for motif in resultat.get('motifs', []):
                        st.caption(motif)

                if resultat['restants']:
                    st.info(
                        f'{resultat["restants"]} fiche(s) supplémentaire(s) '
                        'à traiter : cliquez à nouveau sur ce bouton.'
                    )

                st.session_state.pop('selection_formulaire_v2', None)
            except Exception:
                erreur(
                    'Complément des critères interrompu. '
                    'Les fiches déjà enregistrées sont conservées.'
                )

    with st.expander('Options de lecture'):
        limite = st.number_input(
            'Nombre des derniers e-mails à examiner',
            min_value=1,
            max_value=5000,
            value=100,
            step=50,
            key='limite_' + source,
        )
        st.caption(
            'Seule INBOX est examinée, sans marquer les messages comme lus. '
            'Augmentez la limite pour reprendre des messages plus anciens.'
        )

    cle_apercu = 'emails_preview_' + source

    if source == 'seloger':
        st.caption(
            'La lecture résout uniquement les boutons d’annonces SeLoger, '
            'jusqu’à 20 nouveaux liens par clic. SeLoger peut comptabiliser '
            'ces ouvertures. Les liens de gestion et de désabonnement sont ignorés. '
            'En cas de liens non résolus, relancez la lecture ; les destinations '
            'déjà trouvées sont réutilisées pendant cette session.'
        )
    elif source == 'figaro':
        st.caption(
            'Les adresses publiques des annonces sont extraites localement, '
            'sans utiliser la clé de connexion automatique du message. '
            'Les liens de gestion, de désabonnement et des partenaires sont ignorés.'
        )

    if st.button('Lire les alertes Yahoo', key='lire_' + source):
        try:
            with st.spinner('Lecture des alertes ' + nom + '…'):
                st.session_state[cle_apercu] = get_emails_alertes(
                    int(limite), source=source
                )
                if source == 'seloger':
                    cache = st.session_state.setdefault(
                        'seloger_resolutions', {}
                    )
                    if len(cache) > 1000:
                        cache.clear()
                    st.session_state[cle_apercu] = preparer_emails_seloger(
                        st.session_state[cle_apercu],
                        cache=cache,
                    )
                if not st.session_state[cle_apercu]:
                    st.info(
                        'Aucune alerte ' + nom
                        + ' trouvée dans les messages examinés '
                        'de votre boîte de réception.'
                    )
        except Exception:
            erreur('Impossible de lire les e-mails ' + nom + '.')

    items = st.session_state.get(cle_apercu, [])

    for item in items:
        texte = (
            (item.get('text_body') or '')
            + '\n'
            + (item.get('html_body') or '')
        )

        with st.expander(item.get('subject') or 'Alerte sans objet'):
            st.write(item.get('date') or '')

            if source == 'seloger':
                liens = [
                    b['url'] for b in extraire_annonces_seloger(item)
                ]
            elif source == 'figaro':
                liens = [
                    b['url'] for b in extraire_annonces_figaro(item)
                ]
            else:
                liens = extraire_liens(texte)

            for url in liens:
                st.link_button('Ouvrir l’annonce', url)

            if source == 'leboncoin':
                non_resolus = liens_leboncoin_non_resolus(item)
                annoncees = nombre_annoncees_leboncoin(item)
                if annoncees is not None and annoncees > len(liens):
                    st.caption(
                        f'Le sujet annonce {annoncees} biens ; '
                        f'cet e-mail contient {len(liens)} lien(s) d’annonces reconnus. '
                        'Seuls les biens présents dans le message seront importés.'
                    )
            elif source == 'seloger':
                non_resolus = liens_seloger_non_resolus(item)
            elif source == 'figaro':
                non_resolus = liens_figaro_non_resolus(item)
            else:
                non_resolus = liens_non_resolus(texte)

            if non_resolus:
                st.warning(
                    f'{len(non_resolus)} lien(s) d’annonce non reconnu(s). '
                    'Un exemple d’e-mail peut être nécessaire '
                    'pour adapter l’extracteur.'
                )

    if items and st.button(
        'Importer les liens et lancer le matching',
        type='primary',
        key='importer_' + source,
    ):
        try:
            with st.spinner('Enregistrement…'):
                bilan = importer_emails(
                    db,
                    items,
                    source=source,
                    enrichir=(source in ('bienici', 'seloger', 'figaro')),
                )

            st.success(
                f'{bilan["nouveaux"]} nouvelle(s) annonce(s), '
                f'{bilan["existants"]} lien(s) déjà présent(s), '
                f'{bilan["enrichis"]} fiche(s) complétée(s), '
                f'{bilan["deja_traites"]} e-mail(s) déjà traité(s).'
            )

            if source in ('bienici', 'seloger', 'figaro'):
                st.info(
                    f'{bilan.get("criteres_lus", 0)} '
                    'descriptif(s) complet(s) analysé(s).'
                )
                if (
                    bilan.get('criteres_erreurs')
                    or bilan.get('criteres_reportes')
                ):
                    st.warning(
                        f'{bilan.get("criteres_erreurs", 0)} lecture(s) impossible(s), '
                        f'{bilan.get("criteres_reportes", 0)} analyse(s) reportée(s). '
                        'Utilisez « Compléter les annonces ' + nom
                        + ' déjà enregistrées » pour reprendre. '
                        'L’import des liens est conservé.'
                    )
                    for motif in bilan.get('criteres_messages', []):
                        st.caption(motif)

            if bilan['non_resolus'] or bilan['sans_annonce']:
                st.warning(
                    f'{bilan["non_resolus"]} lien(s) non reconnu(s) ; '
                    f'{bilan["sans_annonce"]} e-mail(s) sans annonce reconnue. '
                    'Ces messages restent à reprendre.'
                )

            st.caption(
                'Les données absentes restent inconnues. '
                'Un nombre de pièces ne renseigne pas les chambres. '
                'Une absence de mention Pro ne confirme pas un particulier. '
                'Vérifiez les fiches avant de proposer un bien.'
            )
        except Exception:
            erreur(
                'Import interrompu. Les annonces déjà enregistrées '
                'sont conservées ; relancez l’import pour reprendre.'
            )


def page_matching(db):
    from services import recalculer

    st.title('Biens pour mes acquéreurs')
    st.caption(
        'Avec un rayon, les communes sont localisées automatiquement '
        'si les coordonnées GPS manquent. Le départ est le centre de la commune '
        'recherchée. La distance au centre de la commune du bien est indicative : '
        'si son étendue peut franchir la limite, le résultat reste à vérifier. '
        'Seuls les noms des communes sont transmis au service public geo.api.gouv.fr. '
        'Après un changement de commune, relancez le recalcul.'
    )

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

    acheteurs = {str(a['id']): a for a in db.get_acquereurs()}
    biens = {
        str(a['id']): a
        for a in db.get_annonces(actives=True)
    }

    selection = st.selectbox(
        'Acquéreur',
        ['Tous'] + list(acheteurs),
        format_func=lambda x: (
            x if x == 'Tous' else
            f'{acheteurs[x].get("prenom", "")} '
            f'{acheteurs[x].get("nom", "")} — {x}'
        ),
    )
    statut_filtre = st.selectbox(
        'Résultat',
        ['Tous'] + list(STATUTS),
        format_func=lambda x: STATUTS.get(x, x),
    )
    vendeur = st.selectbox(
        'Annonceur',
        ['Tous', 'particulier', 'professionnel', 'inconnu'],
    )

    matches = [
        m for m in db.get_matches()
        if str(m['acquereur_id']) in acheteurs
        and str(m['annonce_id']) in biens
    ]

    priorite = {
        'correspondance': 0,
        'a_verifier': 1,
        'preference_non_satisfaite': 2,
        'ecarte': 3,
    }
    matches.sort(key=lambda m: (
        priorite.get(m['statut_matching'], 4),
        -(m.get('couverture') or 0),
        -(m.get('score') or 0),
    ))

    visibles = 0

    for m in matches:
        aid = str(m['acquereur_id'])
        bid = str(m['annonce_id'])
        a, b = acheteurs[aid], biens[bid]

        if (
            selection != 'Tous' and aid != selection
            or statut_filtre != 'Tous'
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
            f'{STATUTS.get(m["statut_matching"], m["statut_matching"])} · '
            f'{a.get("prenom", "")} {a.get("nom", "")} · '
            f'{b.get("titre") or "Annonce à compléter"} · '
            f'{euros(b.get("prix"))}'
        )

        with st.expander(titre_resultat):
            score_affiche = (
                'non calculable'
                if m.get('score') is None
                else f'{m["score"]} %'
            )
            couverture = (
                m.get('couverture')
                if m.get('couverture') is not None
                else 'à recalculer'
            )
            st.write(
                f'Adéquation sur critères connus : {score_affiche} · '
                f'Critères vérifiés : {couverture} %'
            )
            st.caption(
                'Ces pourcentages ne représentent pas une probabilité d’achat. '
                'Le statut tient compte des incompatibilités impératives '
                'et des données manquantes.'
            )

            if b.get('url'):
                st.link_button('Voir le bien', b['url'])

            details = m.get('details_matching') or []

            for titre_groupe, statuts_groupe in (
                ('Ce qui bloque', ('ecarte',)),
                ('À vérifier', ('a_verifier',)),
                (
                    'Préférences non satisfaites',
                    ('preference_non_satisfaite',),
                ),
            ):
                groupe = [
                    d for d in details
                    if d['statut'] in statuts_groupe
                ]
                if groupe:
                    st.markdown('**' + titre_groupe + '**')
                    for d in groupe:
                        st.write(
                            f'{STATUTS.get(d["statut"], d["statut"])} — '
                            f'{d["critere"]} : {d["message"]}'
                        )

            conformes = [
                d for d in details
                if d['statut'] == 'correspondance'
            ]
            if conformes:
                with st.expander(
                    f'Ce qui convient ({len(conformes)})'
                ):
                    for d in conformes:
                        st.write(
                            f'🟢 {d["critere"]} : {d["message"]}'
                        )

            suivi = [
                'nouveau', 'a_contacter', 'propose',
                'visite', 'refuse', 'clos',
            ]
            if m.get('statut') and m['statut'] not in suivi:
                suivi.insert(0, m['statut'])

            with st.form('suivi_' + str(m['id'])):
                statut = st.selectbox(
                    'Suivi commercial',
                    suivi,
                    index=choisir(suivi, m.get('statut')),
                )
                commentaire = st.text_area(
                    'Commentaire',
                    value=m.get('commentaire') or '',
                )
                if st.form_submit_button('Enregistrer le suivi'):
                    try:
                        db.enregistrer(
                            'matches',
                            {
                                'statut': statut,
                                'commentaire': commentaire,
                            },
                            m['id'],
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
    st.subheader('Connexion Yahoo')

    if st.button('Tester la connexion Yahoo'):
        from email_import import get_yahoo_connection

        try:
            mail = get_yahoo_connection()
            mail.logout()
            st.success('Connexion Yahoo réussie.')
        except Exception:
            erreur(
                'Connexion Yahoo impossible. '
                'Vérifiez l’adresse et le mot de passe d’application.'
            )


def main(default='Tableau de bord'):
    st.set_page_config(
        page_title='Chasseur Immo',
        page_icon='🏡',
        layout='wide',
    )
    appliquer_style()
    marque()

    alias = {
        'Matching': 'Biens pour mes acquéreurs',
        'Diagnostic Yahoo': 'Réglages',
    }
    ancienne_source = {
        'Import Bien’ici': 'bienici',
        'Import Leboncoin': 'leboncoin',
        'Import SeLoger': 'seloger',
        'Import Figaro Immobilier': 'figaro',
    }

    if 'navigation' not in st.session_state:
        st.session_state['navigation'] = (
            'Importer les annonces'
            if default in ancienne_source
            else alias.get(default, default)
            if default in CHOIX or default in alias
            else 'Tableau de bord'
        )
        if default in ancienne_source:
            st.session_state['source_import'] = ancienne_source[default]

    page = st.sidebar.radio(
        'Navigation', CHOIX, key='navigation'
    )
    st.sidebar.divider()
    st.sidebar.caption(
        'Les informations inconnues restent à vérifier '
        'avant de proposer un bien.'
    )

    import database as db

    try:
        if page == 'Acquéreurs':
            editeur(db, acheteurs=True)
        elif page == 'Annonces':
            editeur(db)
        elif page == 'Importer les annonces':
            st.title('Importer les annonces')
            source = st.selectbox(
                'Site à importer',
                list(SOURCES),
                format_func=SOURCES.get,
                key='source_import',
            )
            import_alertes(db, source=source)
        elif page == 'Biens pour mes acquéreurs':
            page_matching(db)
        elif page == 'Réglages':
            st.title('Réglages')
            st.caption(
                'Vérifiez ici la connexion de votre boîte Yahoo à l’application.'
            )
            diagnostic_yahoo()
        else:
            tableau_de_bord(db)
    except Exception:
        erreur(
            'Chargement impossible. Vérifiez les journaux '
            'de l’application et la connexion Supabase.'
        )


if __name__ == '__main__':
    main()
