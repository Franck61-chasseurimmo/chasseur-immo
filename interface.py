"""Présentation et filtres de Chasseur Immo, sans modification des données."""
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from matching import normaliser_texte

SOURCES = {
    'bienici': 'Bien’ici',
    'leboncoin': 'Leboncoin',
    'seloger': 'SeLoger',
    'figaro': 'Figaro Immobilier',
}

PAGES = [
    'Tableau de bord',
    'Acquéreurs',
    'Annonces',
    'Importer les annonces',
    'Biens pour mes acquéreurs',
    'Réglages',
]


def appliquer_style():
    st.markdown('''<style>
    .block-container {
      max-width:1180px;
      padding-top:2.4rem;
      padding-bottom:3rem;
    }
    h1 {
      font-size:2.15rem !important;
      letter-spacing:-.045em;
    }
    h2 {
      font-size:1.4rem !important;
      letter-spacing:-.025em;
    }
    h3 {
      font-size:1.05rem !important;
    }
    [data-testid="stMetric"] {
      background:white;
      border:1px solid #E4E4E9;
      border-radius:14px;
      padding:18px 20px;
      border-top:3px solid #E80042;
    }
    [data-testid="stMetricValue"] {
      font-size:1.65rem;
    }
    [data-testid="stForm"] {
      background:white;
      border-radius:14px;
    }
    [data-testid="stExpander"] {
      background:white;
      border-radius:12px;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
      padding:5px 0;
      line-height:1.5;
    }
    .immo-brand {
      display:flex;
      align-items:center;
      gap:12px;
      margin:4px 0 28px;
    }
    .immo-sign {
      background:#E80042;
      color:white;
      font-size:30px;
      font-weight:700;
      width:46px;
      height:50px;
      border-radius:8px;
      text-align:center;
      line-height:48px;
    }
    .immo-brand strong {
      color:white;
      font-size:22px;
      line-height:1.1;
    }
    .immo-brand small {
      display:block;
      color:#E1E1E1;
      font-size:10px;
      letter-spacing:.14em;
      margin-top:8px;
    }
    .immo-eyebrow {
      font-size:11px;
      letter-spacing:.16em;
      font-weight:700;
      color:#C50038;
      margin:8px 0;
    }
    .immo-card {
      background:white;
      border:1px solid #E4E4E9;
      border-radius:14px;
      padding:22px 24px;
      margin:12px 0;
    }
    .immo-card strong {
      font-size:18px;
      color:#292929;
    }
    .immo-card p {
      color:#62626F;
      margin:8px 0 0;
    }
    .immo-card .immo-price {
      color:#C50038;
      font-weight:750;
      font-size:24px;
      margin-top:8px;
    }
    @media(max-width:700px) {
      .block-container {
        padding:1.5rem 1rem 3rem;
      }
      h1 {
        font-size:1.75rem !important;
      }
      .immo-card {
        padding:16px;
      }
    }
    </style>''', unsafe_allow_html=True)


def marque():
    st.sidebar.markdown('''
    <div class="immo-brand">
      <div class="immo-sign">⌂</div>
      <div>
        <strong>CHASSEUR<br>IMMO</strong>
        <small>VOTRE ESPACE IMMOBILIER</small>
      </div>
    </div>
    ''', unsafe_allow_html=True)


def euros(value):
    if value is None:
        return 'Prix à préciser'
    return f'{float(value):,.0f} €'.replace(',', ' ')


def nombre_affiche(value, unite=''):
    if value is None:
        return 'À préciser'
    return f'{float(value):g}{unite}'


def libelle_annonce(bien):
    return ' · '.join([
        bien.get('titre') or 'Annonce sans titre',
        bien.get('commune') or 'Commune à préciser',
        euros(bien.get('prix')),
    ])


def carte_annonce(bien):
    titre = escape(str(bien.get('titre') or 'Annonce à compléter'))
    lieu = escape(str(bien.get('commune') or 'Commune à préciser'))
    source = escape(str(bien.get('source') or 'Source à préciser'))
    surface = escape(nombre_affiche(bien.get('surface_habitable'), ' m²'))
    chambres = escape(nombre_affiche(bien.get('chambres')))
    prix = escape(euros(bien.get('prix')))

    st.markdown(f'''
    <div class="immo-card">
      <div class="immo-eyebrow">{source}</div>
      <strong>{titre}</strong>
      <div class="immo-price">{prix}</div>
      <p>
        {lieu} &nbsp; · &nbsp; {surface}
        &nbsp; · &nbsp; Chambres : {chambres}
      </p>
    </div>
    ''', unsafe_allow_html=True)


def aller(page, annonce=None, rapide=None):
    st.session_state['navigation'] = page

    if page == 'Annonces':
        if annonce is not None:
            st.session_state['selecteur_Annonces'] = str(annonce)
            st.session_state['recherche_annonces'] = ''
            st.session_state['filtre_source_annonces'] = 'Toutes'
            st.session_state['filtre_statut_annonces'] = 'Toutes'
            st.session_state['prix_filtre_annonces'] = None
            st.session_state['sans_descriptif_annonces'] = False

        elif rapide == 'sans_descriptif':
            st.session_state['recherche_annonces'] = ''
            st.session_state['filtre_source_annonces'] = 'Toutes'
            st.session_state['filtre_statut_annonces'] = 'disponible'
            st.session_state['prix_filtre_annonces'] = None
            st.session_state['sans_descriptif_annonces'] = True


def filtrer_annonces(rows):
    recherche = st.text_input(
        'Rechercher une annonce',
        placeholder='Commune, titre ou mot du descriptif…',
        key='recherche_annonces',
    )

    colonnes = st.columns(3)
    sources = sorted({
        str(b.get('source'))
        for b in rows
        if b.get('source')
    })

    if (
        st.session_state.get('filtre_source_annonces', 'Toutes')
        not in ['Toutes'] + sources
    ):
        st.session_state.pop('filtre_source_annonces', None)

    source = colonnes[0].selectbox(
        'Site',
        ['Toutes'] + sources,
        key='filtre_source_annonces',
    )

    statuts = {
        'Toutes': 'Toutes les annonces',
        'disponible': 'Disponibles',
        'archivee': 'Archivées',
        'retiree': 'Retirées',
        'vendue': 'Vendues',
    }

    statut = colonnes[1].selectbox(
        'Disponibilité des annonces',
        list(statuts),
        format_func=statuts.get,
        key='filtre_statut_annonces',
    )

    tri = colonnes[2].selectbox(
        'Trier par',
        ['Plus récentes', 'Prix croissant', 'Prix décroissant', 'Commune'],
        key='tri_annonces',
    )

    with st.expander('Affiner la recherche'):
        maximum = st.number_input(
            'Prix maximum (€)',
            min_value=0.0,
            value=None,
            step=10000.0,
            key='prix_filtre_annonces',
        )
        sans_texte = st.checkbox(
            'Sans descriptif uniquement',
            key='sans_descriptif_annonces',
        )
        st.caption('Un prix inconnu reste visible, même avec un plafond.')

    mots = normaliser_texte(recherche).split()

    visibles = [
        b for b in rows
        if (source == 'Toutes' or b.get('source') == source)
        and (
            statut == 'Toutes'
            or b.get('statut_annonce', 'disponible') == statut
        )
        and (
            maximum is None
            or b.get('prix') is None
            or b['prix'] <= maximum
        )
        and (
            not sans_texte
            or not str(b.get('description') or '').strip()
        )
        and all(
            mot in normaliser_texte(' '.join(
                str(b.get(k) or '')
                for k in ('titre', 'commune', 'source', 'description')
            ))
            for mot in mots
        )
    ]

    if tri == 'Prix croissant':
        visibles.sort(
            key=lambda b: (b.get('prix') is None, b.get('prix') or 0)
        )
    elif tri == 'Prix décroissant':
        visibles.sort(
            key=lambda b: (b.get('prix') is None, -(b.get('prix') or 0))
        )
    elif tri == 'Commune':
        visibles.sort(key=lambda b: normaliser_texte(b.get('commune')))
    else:
        visibles.sort(
            key=lambda b: b.get('imported_at') or '',
            reverse=True,
        )

    st.caption(
        f'{len(visibles)} annonce(s) affichée(s) sur {len(rows)}. '
        'Choisissez une fiche ci-dessous pour la consulter ou la compléter.'
    )
    return visibles


def tableau_de_bord(db):
    date = datetime.now(ZoneInfo('Europe/Paris')).strftime('%d/%m/%Y')
    st.markdown(
        '<div class="immo-eyebrow">VOTRE ACTIVITÉ · ' + date + '</div>',
        unsafe_allow_html=True,
    )
    st.title('Chaque bien, le bon acquéreur.')
    st.write(
        'Retrouvez vos annonces, complétez les informations utiles '
        'et préparez vos prochaines propositions.'
    )

    acheteurs = db.get_acquereurs()
    biens = db.get_annonces(actives=True)
    aids = {str(a['id']) for a in acheteurs}
    bids = {str(b['id']) for b in biens}

    matches = [
        m for m in db.get_matches()
        if str(m['acquereur_id']) in aids
        and str(m['annonce_id']) in bids
    ]

    confirmes = sum(
        m['statut_matching'] == 'correspondance'
        for m in matches
    )
    verifier = sum(
        m['statut_matching'] == 'a_verifier'
        for m in matches
    )

    colonnes = st.columns(4)
    labels = [
        'Acquéreurs actifs',
        'Annonces disponibles',
        'Correspondances confirmées',
        'Résultats à vérifier',
    ]
    valeurs = [len(acheteurs), len(biens), confirmes, verifier]

    for col, label, valeur in zip(colonnes, labels, valeurs):
        col.metric(label, valeur)

    st.write('')
    st.subheader('Vos prochaines actions')
    gauche, droite = st.columns(2)

    with gauche.container(border=True):
        st.markdown('**Récupérer les nouvelles annonces**')
        st.caption(
            'Une seule rubrique pour vos quatre sites et votre boîte Yahoo.'
        )
        st.button(
            'Importer les annonces',
            type='primary',
            on_click=aller,
            args=('Importer les annonces',),
            use_container_width=True,
        )

    manquants = sum(
        not str(b.get('description') or '').strip()
        for b in biens
    )

    with droite.container(border=True):
        st.markdown(f'**{manquants} annonce(s) sans descriptif**')
        st.caption(
            'Complétez le texte des fiches pour permettre l’analyse des critères.'
        )
        st.button(
            'Compléter les fiches',
            on_click=aller,
            args=('Annonces',),
            kwargs={'rapide': 'sans_descriptif'},
            use_container_width=True,
        )

    st.button(
        'Voir les biens pour mes acquéreurs',
        on_click=aller,
        args=('Biens pour mes acquéreurs',),
        use_container_width=True,
    )

    st.divider()
    st.subheader('Dernières annonces disponibles')

    if not biens:
        st.info(
            'Votre tableau est prêt. Importez vos premières alertes '
            'pour retrouver vos annonces ici.'
        )

    recentes = sorted(
        biens,
        key=lambda b: b.get('imported_at') or '',
        reverse=True,
    )[:5]

    for bien in recentes:
        carte_annonce(bien)
        st.button(
            'Consulter la fiche',
            key='ouvrir_fiche_' + str(bien['id']),
            on_click=aller,
            args=('Annonces',),
            kwargs={'annonce': bien['id']},
        )
