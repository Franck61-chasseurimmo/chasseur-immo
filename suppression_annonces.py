"""Sélection et suppression définitive de plusieurs annonces depuis l'interface."""
import logging

import streamlit as st

from interface import libelle_annonce

LOGGER = logging.getLogger(__name__)


def afficher_suppression_groupee(db, annonces):
    """Ne supprime que les fiches sélectionnées, après confirmation explicite."""
    bilan = st.session_state.pop('bilan_suppression_groupee', None)
    if bilan:
        st.session_state.pop('selection_suppression_groupee', None)
        st.session_state.pop('derniere_selection_suppression', None)
        if bilan['supprimees']:
            st.success(
                f'{bilan["supprimees"]} annonce(s) et leurs correspondances '
                'supprimées définitivement.'
            )
        if bilan['echecs']:
            st.error(
                f'{len(bilan["echecs"])} suppression(s) non confirmée(s). '
                'Vérifiez les fiches restantes avant de réessayer.'
            )
            for nom in bilan['echecs']:
                st.write('À vérifier : ' + nom)

    par_id = {str(a['id']): a for a in annonces}
    if not par_id:
        return

    cle = 'selection_suppression_groupee'
    selection = st.session_state.get(cle, [])
    valides = [identifiant for identifiant in selection if identifiant in par_id]
    if valides != selection:
        st.session_state[cle] = valides

    with st.expander('Supprimer plusieurs annonces'):
        st.caption(
            'La sélection porte uniquement sur les annonces de la liste filtrée. '
            'Pour tout supprimer, retirez les filtres avant de tout sélectionner.'
        )
        gauche, droite = st.columns(2)
        if gauche.button('Tout sélectionner dans la liste', key='selectionner_annonces'):
            st.session_state[cle] = list(par_id)
        if droite.button('Tout désélectionner', key='deselectionner_annonces'):
            st.session_state[cle] = []

        def libelle(identifiant):
            bien = par_id[identifiant]
            return libelle_annonce(bien) + ' · ' + str(bien.get('source') or 'Source inconnue')

        choisis = st.multiselect(
            'Annonces à supprimer', list(par_id),
            format_func=libelle, key=cle,
        )
        signature = tuple(sorted(choisis))
        if st.session_state.get('derniere_selection_suppression') != signature:
            st.session_state['revision_confirmation_suppression'] = (
                st.session_state.get('revision_confirmation_suppression', 0) + 1
            )
            st.session_state['derniere_selection_suppression'] = signature
        if not choisis:
            st.caption('Sélectionnez quelques annonces ou utilisez « Tout sélectionner ».')
            return

        st.warning(
            f'{len(choisis)} annonce(s) sélectionnée(s). La suppression est définitive '
            'et efface aussi leurs correspondances et leur suivi commercial. '
            'Les acquéreurs sont conservés. Les annonces restent sur les sites d’origine.'
        )
        with st.form('formulaire_suppression_groupee'):
            confirme = st.checkbox(
                f'Je confirme la suppression définitive de ces {len(choisis)} annonce(s)',
                key='confirmation_suppression_' + str(
                    st.session_state['revision_confirmation_suppression']
                ),
            )
            supprimer = st.form_submit_button(
                f'Supprimer définitivement les {len(choisis)} annonces sélectionnées'
            )
        if not supprimer:
            return
        if not confirme:
            st.error('Cochez la confirmation pour supprimer cette sélection.')
            return

        resultat = {'supprimees': 0, 'echecs': []}
        with st.spinner('Suppression des annonces sélectionnées…'):
            for identifiant in choisis:
                try:
                    retour = db.supprimer_annonce(identifiant)
                    if not retour or str(retour.get('id')) != identifiant:
                        raise RuntimeError('Suppression non confirmée.')
                    resultat['supprimees'] += 1
                except Exception:
                    LOGGER.exception('Suppression groupée : une fiche reste à vérifier.')
                    resultat['echecs'].append(libelle(identifiant))
        st.session_state['bilan_suppression_groupee'] = resultat
        st.session_state.pop('selection_formulaire_v2', None)
        st.session_state.pop('selecteur_Annonces', None)
        st.rerun()
