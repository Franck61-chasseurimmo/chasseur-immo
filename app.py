
import streamlit as st

from database import (
    get_acquereurs,
    get_annonces,
    get_matches,
    insert_annonce,
    insert_match,
)

from matching import matcher_tous_les_acquereurs


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Chasseur Immo",
    page_icon="🏡",
    layout="wide"
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
        .main {
            background-color: #f7f8fa;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .card {
            background: white;
            padding: 1.2rem;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            margin-bottom: 1rem;
        }

        .success-card {
            background: #ecfdf5;
            border-left: 5px solid #10b981;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .warning-card {
            background: #fffbeb;
            border-left: 5px solid #f59e0b;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .danger-card {
            background: #fef2f2;
            border-left: 5px solid #ef4444;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .small-text {
            color: #6b7280;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# TITRE
# ============================================================

st.title("🏡 Chasseur Immo")
st.caption("Recherche et matching immobilier")


# ============================================================
# MENU
# ============================================================

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Tableau de bord",
        "👤 Acquéreurs",
        "🏡 Annonces",
        "🎯 Matching"
    ]
)


# ============================================================
# TEST YAHOO
# ============================================================

st.sidebar.divider()

st.sidebar.subheader("📧 Connexion Yahoo")

tester_yahoo = st.sidebar.button(
    "🧪 Tester la connexion Yahoo",
    use_container_width=True
)

if tester_yahoo:

    try:

        from email_import import get_yahoo_connection

        mail = get_yahoo_connection()

        st.sidebar.success(
            "✅ Connexion Yahoo réussie !"
        )

        mail.logout()

    except Exception as erreur:

        st.sidebar.error(
            "❌ La connexion Yahoo a échoué."
        )

        st.sidebar.code(
            str(erreur)
        )


# ============================================================
# OUTILS
# ============================================================

def afficher_statut(statut):

    if statut == "correspondance":
        return "🟢 Correspondance"

    if statut == "a_verifier":
        return "🟠 À vérifier"

    if statut == "ecarte":
        return "🔴 Écarté"

    return statut


def valeur_ou_vide(valeur):

    if valeur is None:
        return ""

    return valeur


# ============================================================
# TABLEAU DE BORD
# ============================================================

if page == "🏠 Tableau de bord":

    st.title("🏠 Tableau de bord")

    try:

        acquereurs = get_acquereurs(actif=True)
        annonces = get_annonces()
        matches = get_matches()

        correspondances = [
            match
            for match in matches
            if match.get("statut_matching") == "correspondance"
        ]

        a_verifier = [
            match
            for match in matches
            if match.get("statut_matching") == "a_verifier"
        ]

        ecartes = [
            match
            for match in matches
            if match.get("statut_matching") == "ecarte"
        ]

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "👤 Acquéreurs actifs",
                len(acquereurs)
            )

        with col2:

            st.metric(
                "🏡 Annonces",
                len(annonces)
            )

        with col3:

            st.metric(
                "🟢 Correspondances",
                len(correspondances)
            )

        with col4:

            st.metric(
                "🟠 À vérifier",
                len(a_verifier)
            )

        st.divider()

        st.subheader("Dernières annonces")

        if not annonces:

            st.info(
                "Aucune annonce enregistrée pour le moment."
            )

        else:

            for annonce in annonces[:10]:

                titre = (
                    annonce.get("titre")
                    or "Annonce sans titre"
                )

                prix = annonce.get("prix")
                commune = annonce.get("commune") or ""
                source = annonce.get("source") or ""

                if prix is not None:

                    prix_affiche = f"{prix:,.0f} €"

                else:

                    prix_affiche = "Prix non renseigné"

                st.markdown(
                    f"""
                    <div class="card">
                        <h4>{titre}</h4>
                        <p>
                            <strong>{prix_affiche}</strong>
                            &nbsp; | &nbsp;
                            {commune}
                            &nbsp; | &nbsp;
                            {source}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        st.subheader("Derniers matches")

        if not matches:

            st.info(
                "Aucun matching réalisé pour le moment."
            )

        else:

            for match in matches[:10]:

                statut = match.get(
                    "statut_matching"
                )

                score = match.get(
                    "score",
                    0
                )

                st.write(
                    f"{afficher_statut(statut)} — "
                    f"Score : {score}%"
                )

    except Exception as erreur:

        st.error(
            "Une erreur est survenue lors du chargement du tableau de bord."
        )

        st.code(
            str(erreur)
        )


# ============================================================
# ACQUEREURS
# ============================================================

elif page == "👤 Acquéreurs":

    st.title("👤 Acquéreurs")

    onglet_creation, onglet_liste = st.tabs(
        [
            "➕ Ajouter un acquéreur",
            "📋 Liste des acquéreurs"
        ]
    )

    # --------------------------------------------------------
    # CREATION
    # --------------------------------------------------------

    with onglet_creation:

        st.subheader("Créer un acquéreur")

        with st.form("form_acquereur"):

            col1, col2 = st.columns(2)

            with col1:

                prenom = st.text_input(
                    "Prénom *"
                )

                nom = st.text_input(
                    "Nom *"
                )

                telephone = st.text_input(
                    "Téléphone"
                )

            with col2:

                email = st.text_input(
                    "Email"
                )

                secteur = st.text_input(
                    "Secteur recherché",
                    value="Alençon"
                )

                rayon_km = st.number_input(
                    "Rayon de recherche (km)",
                    min_value=0.0,
                    value=0.0,
                    step=1.0
                )

            st.divider()

            st.subheader("Type de bien")

            col1, col2, col3 = st.columns(3)

            with col1:

                recherche_maison = st.checkbox(
                    "Maison"
                )

            with col2:

                recherche_pavillon = st.checkbox(
                    "Pavillon"
                )

            with col3:

                recherche_maison_pierre = st.checkbox(
                    "Maison en pierre"
                )

            st.divider()

            st.subheader("Critères obligatoires")

            col1, col2 = st.columns(2)

            with col1:

                plain_pied_obligatoire = st.checkbox(
                    "Plain-pied obligatoire"
                )

                garage_obligatoire = st.checkbox(
                    "Garage obligatoire"
                )

                salle_eau_rdc = st.checkbox(
                    "Salle d'eau au RDC"
                )

            with col2:

                sous_sol_recherche = st.checkbox(
                    "Sous-sol recherché"
                )

            st.divider()

            st.subheader("Critères de surface et pièces")

            col1, col2, col3 = st.columns(3)

            with col1:

                chambres_min = st.number_input(
                    "Chambres minimum",
                    min_value=0,
                    value=0,
                    step=1
                )

            with col2:

                chambres_rdc_min = st.number_input(
                    "Chambres au RDC minimum",
                    min_value=0,
                    value=0,
                    step=1
                )

            with col3:

                salles_eau_min = st.number_input(
                    "Salles d'eau minimum",
                    min_value=0,
                    value=0,
                    step=1
                )

            surface_terrain_souhaitee = st.number_input(
                "Surface de terrain souhaitée (m²)",
                min_value=0.0,
                value=0.0,
                step=10.0
            )

            st.divider()

            st.subheader("Budget")

            col1, col2 = st.columns(2)

            with col1:

                budget_max = st.number_input(
                    "Budget maximum (€)",
                    min_value=0.0,
                    value=0.0,
                    step=5000.0
                )

            with col2:

                marge_budget = st.number_input(
                    "Marge acceptable (€)",
                    min_value=0.0,
                    value=2000.0,
                    step=500.0
                )

            notes = st.text_area(
                "Notes complémentaires"
            )

            actif = st.checkbox(
                "Acquéreur actif",
                value=True
            )

            submitted = st.form_submit_button(
                "💾 Enregistrer l'acquéreur",
                use_container_width=True
            )

        if submitted:

            if not prenom.strip():

                st.error(
                    "Le prénom est obligatoire."
                )

            elif not nom.strip():

                st.error(
                    "Le nom est obligatoire."
                )

            else:

                from database import supabase

                data = {
                    "nom": nom.strip(),
                    "prenom": prenom.strip(),
                    "telephone": telephone.strip(),
                    "email": email.strip(),
                    "recherche_maison": recherche_maison,
                    "recherche_pavillon": recherche_pavillon,
                    "recherche_maison_pierre": recherche_maison_pierre,
                    "plain_pied_obligatoire": plain_pied_obligatoire,
                    "chambres_min": (
                        chambres_min
                        if chambres_min > 0
                        else None
                    ),
                    "chambres_rdc_min": (
                        chambres_rdc_min
                        if chambres_rdc_min > 0
                        else None
                    ),
                    "salle_eau_rdc": salle_eau_rdc,
                    "salles_eau_min": (
                        salles_eau_min
                        if salles_eau_min > 0
                        else None
                    ),
                    "garage_obligatoire": garage_obligatoire,
                    "sous_sol_recherche": sous_sol_recherche,
                    "secteur": secteur.strip() or "Alençon",
                    "rayon_km": (
                        rayon_km
                        if rayon_km > 0
                        else None
                    ),
                    "surface_terrain_souhaitee": (
                        surface_terrain_souhaitee
                        if surface_terrain_souhaitee > 0
                        else None
                    ),
                    "budget_max": (
                        budget_max
                        if budget_max > 0
                        else None
                    ),
                    "marge_budget": marge_budget,
                    "notes": notes.strip(),
                    "actif": actif
                }

                try:

                    response = (
                        supabase
                        .table("acquereurs")
                        .insert(data)
                        .execute()
                    )

                    if response.data:

                        st.success(
                            f"✅ Acquéreur {prenom} {nom} enregistré."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "L'acquéreur n'a pas pu être enregistré."
                        )

                except Exception as erreur:

                    st.error(
                        "Erreur lors de l'enregistrement."
                    )

                    st.code(
                        str(erreur)
                    )

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    with onglet_liste:

        st.subheader("Acquéreurs actifs")

        try:

            acquereurs = get_acquereurs(
                actif=True
            )

            if not acquereurs:

                st.info(
                    "Aucun acquéreur actif."
                )

            else:

                for acquereur in acquereurs:

                    prenom = acquereur.get(
                        "prenom",
                        ""
                    )

                    nom = acquereur.get(
                        "nom",
                        ""
                    )

                    budget = acquereur.get(
                        "budget_max"
                    )

                    if budget:

                        budget_affiche = (
                            f"{budget:,.0f} €"
                        )

                    else:

                        budget_affiche = (
                            "Non renseigné"
                        )

                    with st.expander(
                        f"👤 {prenom} {nom}"
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            st.write(
                                f"**Secteur :** "
                                f"{acquereur.get('secteur', '')}"
                            )

                            st.write(
                                f"**Rayon :** "
                                f"{acquereur.get('rayon_km') or 'Non renseigné'} km"
                            )

                            st.write(
                                f"**Budget :** "
                                f"{budget_affiche}"
                            )

                        with col2:

                            st.write(
                                f"**Téléphone :** "
                                f"{acquereur.get('telephone') or '-'}"
                            )

                            st.write(
                                f"**Email :** "
                                f"{acquereur.get('email') or '-'}"
                            )

                            st.write(
                                f"**Notes :** "
                                f"{acquereur.get('notes') or '-'}"
                            )

        except Exception as erreur:

            st.error(
                "Impossible de charger les acquéreurs."
            )

            st.code(
                str(erreur)
            )


# ============================================================
# ANNONCES
# ============================================================

elif page == "🏡 Annonces":

    st.title("🏡 Annonces")

    st.info(
        "Pour le moment, les annonces sont ajoutées manuellement. "
        "La recherche automatique sur les sites sera ajoutée ensuite."
    )

    st.subheader("➕ Ajouter une annonce")

    with st.form("form_annonce"):

        titre = st.text_input(
            "Titre de l'annonce"
        )

        url = st.text_input(
            "URL de l'annonce *"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            source = st.text_input(
                "Source",
                placeholder="Ex : Leboncoin"
            )

        with col2:

            prix = st.number_input(
                "Prix (€)",
                min_value=0.0,
                value=0.0,
                step=1000.0
            )

        with col3:

            commune = st.text_input(
                "Commune"
            )

        st.divider()

        st.subheader("Caractéristiques du bien")

        col1, col2, col3 = st.columns(3)

        with col1:

            type_maison = st.selectbox(
                "Type",
                [
                    "",
                    "maison",
                    "pavillon",
                    "maison_pierre"
                ]
            )

            chambres = st.number_input(
                "Nombre de chambres",
                min_value=0,
                value=0,
                step=1
            )

            chambres_rdc = st.number_input(
                "Chambres au RDC",
                min_value=0,
                value=0,
                step=1
            )

        with col2:

            plain_pied = st.checkbox(
                "Plain-pied"
            )

            salle_eau_rdc = st.checkbox(
                "Salle d'eau au RDC"
            )

            salles_eau = st.number_input(
                "Nombre de salles d'eau",
                min_value=0,
                value=0,
                step=1
            )

        with col3:

            garage = st.checkbox(
                "Garage"
            )

            sous_sol = st.checkbox(
                "Sous-sol"
            )

            maison_pierre = st.checkbox(
                "Maison en pierre"
            )

        surface_terrain = st.number_input(
            "Surface du terrain (m²)",
            min_value=0.0,
            value=0.0,
            step=10.0
        )

        st.divider()

        st.subheader("Localisation")

        col1, col2 = st.columns(2)

        with col1:

            latitude = st.number_input(
                "Latitude",
                value=0.0,
                format="%.6f"
            )

        with col2:

            longitude = st.number_input(
                "Longitude",
                value=0.0,
                format="%.6f"
            )

        description = st.text_area(
            "Description"
        )

        submitted = st.form_submit_button(
            "💾 Enregistrer l'annonce et lancer le matching",
            use_container_width=True
        )

    if submitted:

        if not url.strip():

            st.error(
                "L'URL de l'annonce est obligatoire."
            )

        else:

            try:

                annonce_existante = None

                from database import get_annonce_by_url

                annonce_existante = get_annonce_by_url(
                    url.strip()
                )

                if annonce_existante:

                    st.warning(
                        "Cette annonce existe déjà dans la base."
                    )

                    annonce = annonce_existante

                else:

                    annonce_data = {
                        "titre": titre.strip(),
                        "url": url.strip(),
                        "source": source.strip(),
                        "prix": (
                            prix
                            if prix > 0
                            else None
                        ),
                        "commune": commune.strip(),
                        "latitude": (
                            latitude
                            if latitude != 0
                            else None
                        ),
                        "longitude": (
                            longitude
                            if longitude != 0
                            else None
                        ),
                        "type_maison": (
                            type_maison
                            or None
                        ),
                        "plain_pied": plain_pied,
                        "maison_pierre": maison_pierre,
                        "pavillon": (
                            type_maison == "pavillon"
                        ),
                        "chambres": (
                            chambres
                            if chambres > 0
                            else None
                        ),
                        "chambres_rdc": (
                            chambres_rdc
                            if chambres_rdc > 0
                            else None
                        ),
                        "salle_eau_rdc": salle_eau_rdc,
                        "salles_eau": (
                            salles_eau
                            if salles_eau > 0
                            else None
                        ),
                        "garage": garage,
                        "sous_sol": sous_sol,
                        "surface_terrain": (
                            surface_terrain
                            if surface_terrain > 0
                            else None
                        ),
                        "description": description.strip()
                    }

                    annonce = insert_annonce(
                        annonce_data
                    )

                if annonce:

                    st.success(
                        "✅ Annonce enregistrée."
                    )

                    st.subheader(
                        "🎯 Matching avec les acquéreurs"
                    )

                    acquereurs = get_acquereurs(
                        actif=True
                    )

                    if not acquereurs:

                        st.info(
                            "Aucun acquéreur actif à comparer."
                        )

                    else:

                        resultats = matcher_tous_les_acquereurs(
                            acquereurs,
                            annonce
                        )

                        nombre_matches = 0

                        for resultat in resultats:

                            acquereur = resultat[
                                "acquereur"
                            ]

                            match_data = {
                                "acquereur_id": acquereur[
                                    "id"
                                ],
                                "annonce_id": annonce[
                                    "id"
                                ],
                                "statut_matching": resultat[
                                    "statut_matching"
                                ],
                                "score": resultat[
                                    "score"
                                ],
                                "details_matching": resultat[
                                    "details_matching"
                                ],
                                "statut": "nouveau"
                            }

                            insert_match(
                                match_data
                            )

                            nombre_matches += 1

                            nom_complet = (
                                f"{acquereur.get('prenom', '')} "
                                f"{acquereur.get('nom', '')}"
                            )

                            statut = resultat[
                                "statut_matching"
                            ]

                            score = resultat[
                                "score"
                            ]

                            if statut == "correspondance":

                                st.success(
                                    f"🟢 {nom_complet} — "
                                    f"Correspondance — "
                                    f"{score}%"
                                )

                            elif statut == "a_verifier":

                                st.warning(
                                    f"🟠 {nom_complet} — "
                                    f"À vérifier — "
                                    f"{score}%"
                                )

                            else:

                                st.error(
                                    f"🔴 {nom_complet} — "
                                    f"Écarté — "
                                    f"{score}%"
                                )

                        st.info(
                            f"{nombre_matches} acquéreur(s) "
                            "ont été analysés."
                        )

                else:

                    st.error(
                        "Impossible d'enregistrer l'annonce."
                    )

            except Exception as erreur:

                st.error(
                    "Une erreur est survenue."
                )

                st.code(
                    str(erreur)
                )


# ============================================================
# MATCHING
# ============================================================

elif page == "🎯 Matching":

    st.title("🎯 Matching")

    st.write(
        "Cette page permet de consulter les correspondances "
        "entre les annonces et les acquéreurs."
    )

    try:

        matches = get_matches()
        annonces = get_annonces()
        acquereurs = get_acquereurs(
            actif=False
        )

        annonces_dict = {
            annonce["id"]: annonce
            for annonce in annonces
        }

        acquereurs_dict = {
            acquereur["id"]: acquereur
            for acquereur in acquereurs
        }

        if not matches:

            st.info(
                "Aucun matching enregistré pour le moment."
            )

        else:

            col1, col2, col3, col4 = st.columns(4)

            correspondances = [
                m
                for m in matches
                if m.get("statut_matching") == "correspondance"
            ]

            a_verifier = [
                m
                for m in matches
                if m.get("statut_matching") == "a_verifier"
            ]

            ecartes = [
                m
                for m in matches
                if m.get("statut_matching") == "ecarte"
            ]

            with col1:

                st.metric(
                    "Total",
                    len(matches)
                )

            with col2:

                st.metric(
                    "🟢 Correspondances",
                    len(correspondances)
                )

            with col3:

                st.metric(
                    "🟠 À vérifier",
                    len(a_verifier)
                )

            with col4:

                st.metric(
                    "🔴 Écartés",
                    len(ecartes)
                )

            st.divider()

            filtre = st.selectbox(
                "Afficher",
                [
                    "Tous",
                    "🟢 Correspondances",
                    "🟠 À vérifier",
                    "🔴 Écartés"
                ]
            )

            matches_affiches = []

            for match in matches:

                statut = match.get(
                    "statut_matching"
                )

                if filtre == "Tous":

                    matches_affiches.append(
                        match
                    )

                elif (
                    filtre == "🟢 Correspondances"
                    and statut == "correspondance"
                ):

                    matches_affiches.append(
                        match
                    )

                elif (
                    filtre == "🟠 À vérifier"
                    and statut == "a_verifier"
                ):

                    matches_affiches.append(
                        match
                    )

                elif (
                    filtre == "🔴 Écartés"
                    and statut == "ecarte"
                ):

                    matches_affiches.append(
                        match
                    )

            for match in matches_affiches:

                acquereur = acquereurs_dict.get(
                    match.get("acquereur_id"),
                    {}
                )

                annonce = annonces_dict.get(
                    match.get("annonce_id"),
                    {}
                )

                nom_complet = (
                    f"{acquereur.get('prenom', '')} "
                    f"{acquereur.get('nom', '')}"
                )

                titre = (
                    annonce.get("titre")
                    or "Annonce sans titre"
                )

                url = annonce.get("url")

                statut = match.get(
                    "statut_matching"
                )

                score = match.get(
                    "score",
                    0
                )

                if statut == "correspondance":

                    st.markdown(
                        '<div class="success-card">',
                        unsafe_allow_html=True
                    )

                elif statut == "a_verifier":

                    st.markdown(
                        '<div class="warning-card">',
                        unsafe_allow_html=True
                    )

                else:

                    st.markdown(
                        '<div class="danger-card">',
                        unsafe_allow_html=True
                    )

                st.markdown(
                    f"### {afficher_statut(statut)}"
                )

                st.write(
                    f"**Acquéreur :** {nom_complet}"
                )

                st.write(
                    f"**Annonce :** {titre}"
                )

                st.write(
                    f"**Score :** {score}%"
                )

                if url:

                    st.link_button(
                        "🔗 Ouvrir l'annonce",
                        url
                    )

                details = match.get(
                    "details_matching"
                )

                if details:

                    with st.expander(
                        "Voir le détail du matching"
                    ):

                        for detail in details:

                            detail_statut = detail.get(
                                "statut"
                            )

                            critere = detail.get(
                                "critere",
                                ""
                            )

                            message = detail.get(
                                "message",
                                ""
                            )

                            if detail_statut == "correspondance":

                                st.write(
                                    f"🟢 **{critere}** — "
                                    f"{message}"
                                )

                            elif detail_statut == "a_verifier":

                                st.write(
                                    f"🟠 **{critere}** — "
                                    f"{message}"
                                )

                            else:

                                st.write(
                                    f"🔴 **{critere}** — "
                                    f"{message}"
                                )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

    except Exception as erreur:

        st.error(
            "Impossible de charger les résultats de matching."
        )

        st.code(
            str(erreur)
        )
```
