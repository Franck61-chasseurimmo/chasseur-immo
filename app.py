import streamlit as st

from database import (
    supabase,
    get_acquereurs,
    get_annonces,
    get_matches
)

from matching import matcher_tous_les_acquereurs


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Chasseur Immo",
    page_icon="🏠",
    layout="wide"
)


# ============================================================
# MENU
# ============================================================

st.sidebar.title("🏠 Chasseur Immo")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Tableau de bord",
        "👤 Acquéreurs",
        "📋 Annonces",
        "🎯 Matching"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Application en construction")


# ============================================================
# TABLEAU DE BORD
# ============================================================

if page == "🏠 Tableau de bord":

    st.title("🏠 Tableau de bord")

    st.write(
        "Bienvenue dans votre espace de recherche immobilière."
    )

    try:

        acquereurs = supabase.table(
            "acquereurs"
        ).select(
            "id",
            count="exact"
        ).execute()

        annonces = supabase.table(
            "annonces"
        ).select(
            "id",
            count="exact"
        ).execute()

        matches = supabase.table(
            "matches"
        ).select(
            "id",
            count="exact"
        ).execute()

        nb_acquereurs = acquereurs.count or 0
        nb_annonces = annonces.count or 0
        nb_matches = matches.count or 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Acquéreurs",
                nb_acquereurs
            )

        with col2:
            st.metric(
                "Annonces",
                nb_annonces
            )

        with col3:
            st.metric(
                "Matches",
                nb_matches
            )

        st.success(
            "✅ Connexion à Supabase réussie."
        )

    except Exception as e:

        st.error(
            "❌ Impossible de se connecter à Supabase."
        )

        st.write(str(e))


# ============================================================
# ACQUEREURS
# ============================================================

elif page == "👤 Acquéreurs":

    st.title("👤 Nouvel acquéreur")

    st.write(
        "Créez ici le profil de recherche de votre acquéreur."
    )

    # --------------------------------------------------------
    # IDENTITE
    # --------------------------------------------------------

    st.subheader("👤 Identité")

    col1, col2 = st.columns(2)

    with col1:

        prenom = st.text_input(
            "Prénom *"
        )

    with col2:

        nom = st.text_input(
            "Nom *"
        )

    col3, col4 = st.columns(2)

    with col3:

        telephone = st.text_input(
            "Téléphone"
        )

    with col4:

        email = st.text_input(
            "Email"
        )

    # --------------------------------------------------------
    # TYPE DE BIEN
    # --------------------------------------------------------

    st.subheader("🏠 Type de bien recherché")

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

    # --------------------------------------------------------
    # CARACTERISTIQUES
    # --------------------------------------------------------

    st.subheader("🛏️ Caractéristiques")

    col1, col2 = st.columns(2)

    with col1:

        plain_pied_obligatoire = st.checkbox(
            "Plain-pied obligatoire"
        )

    with col2:

        garage_obligatoire = st.checkbox(
            "Garage obligatoire"
        )

    col3, col4 = st.columns(2)

    with col3:

        chambres_min = st.number_input(
            "Chambres minimum",
            min_value=0,
            step=1,
            value=0
        )

    with col4:

        chambres_rdc_min = st.number_input(
            "Chambres au RDC minimum",
            min_value=0,
            step=1,
            value=0
        )

    col5, col6 = st.columns(2)

    with col5:

        salle_eau_rdc = st.checkbox(
            "Salle d'eau au RDC obligatoire"
        )

    with col6:

        salles_eau_min = st.number_input(
            "Nombre minimum de salles d'eau",
            min_value=0,
            step=1,
            value=0
        )

    sous_sol_recherche = st.checkbox(
        "Sous-sol recherché"
    )

    # --------------------------------------------------------
    # LOCALISATION
    # --------------------------------------------------------

    st.subheader("📍 Localisation")

    col1, col2 = st.columns(2)

    with col1:

        secteur = st.text_input(
            "Secteur de référence",
            value="Alençon"
        )

    with col2:

        rayon_km = st.number_input(
            "Rayon de recherche (km)",
            min_value=0.0,
            step=1.0,
            value=20.0
        )

    # --------------------------------------------------------
    # TERRAIN ET BUDGET
    # --------------------------------------------------------

    st.subheader("💰 Terrain & budget")

    col1, col2 = st.columns(2)

    with col1:

        surface_terrain = st.number_input(
            "Surface de terrain souhaitée (m²)",
            min_value=0.0,
            step=10.0,
            value=0.0
        )

    with col2:

        budget_max = st.number_input(
            "Budget maximum (€)",
            min_value=0.0,
            step=1000.0,
            value=0.0
        )

    st.caption(
        "Une marge automatique de 2 000 € sera appliquée au matching."
    )

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    st.subheader("📝 Notes / précisions")

    notes = st.text_area(
        "Informations complémentaires",
        placeholder=(
            "Exemple : proche commerces, éviter route passante, "
            "travaux acceptés..."
        )
    )

    # --------------------------------------------------------
    # ENREGISTREMENT
    # --------------------------------------------------------

    st.markdown("---")

    if st.button(
        "💾 Enregistrer l'acquéreur",
        type="primary",
        use_container_width=True
    ):

        if not prenom or not nom:

            st.error(
                "⚠️ Le prénom et le nom sont obligatoires."
            )

        elif budget_max <= 0:

            st.error(
                "⚠️ Merci de renseigner un budget maximum."
            )

        else:

            try:

                data = {
                    "nom": nom,
                    "prenom": prenom,
                    "telephone": telephone,
                    "email": email,

                    "recherche_maison": recherche_maison,
                    "recherche_pavillon": recherche_pavillon,
                    "recherche_maison_pierre": recherche_maison_pierre,

                    "plain_pied_obligatoire":
                        plain_pied_obligatoire,

                    "chambres_min":
                        chambres_min
                        if chambres_min > 0
                        else None,

                    "chambres_rdc_min":
                        chambres_rdc_min
                        if chambres_rdc_min > 0
                        else None,

                    "salle_eau_rdc":
                        salle_eau_rdc,

                    "salles_eau_min":
                        salles_eau_min
                        if salles_eau_min > 0
                        else None,

                    "garage_obligatoire":
                        garage_obligatoire,

                    "sous_sol_recherche":
                        sous_sol_recherche,

                    "secteur":
                        secteur,

                    "rayon_km":
                        rayon_km,

                    "surface_terrain_souhaitee":
                        surface_terrain
                        if surface_terrain > 0
                        else None,

                    "budget_max":
                        budget_max,

                    "marge_budget":
                        2000,

                    "notes":
                        notes,

                    "actif":
                        True
                }

                supabase.table(
                    "acquereurs"
                ).insert(data).execute()

                st.success(
                    "✅ Acquéreur enregistré avec succès !"
                )

                st.balloons()

            except Exception as e:

                st.error(
                    "❌ Erreur lors de l'enregistrement."
                )

                st.write(str(e))


# ============================================================
# ANNONCES
# ============================================================

elif page == "📋 Annonces":

    st.title("📋 Annonces")

    st.write(
        "Ajoutez une annonce pour lancer le matching."
    )

    st.info(
        "🔎 La recherche automatique des sites immobiliers "
        "sera ajoutée dans une prochaine étape."
    )

    # --------------------------------------------------------
    # INFORMATIONS GENERALES
    # --------------------------------------------------------

    st.subheader("🔗 Informations de l'annonce")

    url = st.text_input(
        "URL de l'annonce *",
        placeholder="https://..."
    )

    titre = st.text_input(
        "Titre de l'annonce"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        prix = st.number_input(
            "Prix (€)",
            min_value=0.0,
            step=1000.0,
            value=0.0
        )

    with col2:

        commune = st.text_input(
            "Commune"
        )

    with col3:

        source = st.text_input(
            "Source",
            placeholder="LeBonCoin, SeLoger..."
        )

    # --------------------------------------------------------
    # TYPE
    # --------------------------------------------------------

    st.subheader("🏠 Type de bien")

    col1, col2, col3 = st.columns(3)

    with col1:

        type_maison = st.selectbox(
            "Type",
            [
                "Maison",
                "Pavillon",
                "Maison en pierre"
            ]
        )

    with col2:

        maison_pierre = st.selectbox(
            "Maison en pierre ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    with col3:

        pavillon = st.selectbox(
            "Pavillon ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    # --------------------------------------------------------
    # CARACTERISTIQUES
    # --------------------------------------------------------

    st.subheader("🛏️ Caractéristiques")

    col1, col2, col3 = st.columns(3)

    with col1:

        chambres = st.number_input(
            "Nombre de chambres",
            min_value=0,
            step=1,
            value=0
        )

    with col2:

        chambres_rdc = st.number_input(
            "Chambres au RDC",
            min_value=0,
            step=1,
            value=0
        )

    with col3:

        salles_eau = st.number_input(
            "Nombre de salles d'eau",
            min_value=0,
            step=1,
            value=0
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        plain_pied_choix = st.selectbox(
            "Plain-pied ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    with col2:

        garage_choix = st.selectbox(
            "Garage ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    with col3:

        sous_sol_choix = st.selectbox(
            "Sous-sol ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    with col4:

        salle_eau_rdc_choix = st.selectbox(
            "Salle d'eau RDC ?",
            [
                "Non précisé",
                "Oui",
                "Non"
            ]
        )

    # --------------------------------------------------------
    # TERRAIN
    # --------------------------------------------------------

    surface_terrain = st.number_input(
        "Surface du terrain (m²)",
        min_value=0.0,
        step=10.0,
        value=0.0
    )

    description = st.text_area(
        "Description de l'annonce"
    )

    # --------------------------------------------------------
    # LANCEMENT
    # --------------------------------------------------------

    st.markdown("---")

    if st.button(
        "🔎 Enregistrer l'annonce et lancer le matching",
        type="primary",
        use_container_width=True
    ):

        if not url:

            st.error(
                "⚠️ L'URL de l'annonce est obligatoire."
            )

        else:

            try:

                # --------------------------------------------
                # Conversion des valeurs Oui / Non / Non précisé
                # --------------------------------------------

                def convertir_booleen(valeur):

                    if valeur == "Oui":
                        return True

                    if valeur == "Non":
                        return False

                    return None

                annonce_data = {

                    "url": url,
                    "titre": titre,
                    "source": source,

                    "prix":
                        prix
                        if prix > 0
                        else None,

                    "commune":
                        commune,

                    "type_maison":
                        type_maison,

                    "plain_pied":
                        convertir_booleen(
                            plain_pied_choix
                        ),

                    "maison_pierre":
                        convertir_booleen(
                            maison_pierre
                        ),

                    "pavillon":
                        convertir_booleen(
                            pavillon
                        ),

                    "chambres":
                        chambres
                        if chambres > 0
                        else None,

                    "chambres_rdc":
                        chambres_rdc
                        if chambres_rdc > 0
                        else None,

                    "salle_eau_rdc":
                        convertir_booleen(
                            salle_eau_rdc_choix
                        ),

                    "salles_eau":
                        salles_eau
                        if salles_eau > 0
                        else None,

                    "garage":
                        convertir_booleen(
                            garage_choix
                        ),

                    "sous_sol":
                        convertir_booleen(
                            sous_sol_choix
                        ),

                    "surface_terrain":
                        surface_terrain
                        if surface_terrain > 0
                        else None,

                    "description":
                        description
                }

                # --------------------------------------------
                # Vérification doublon
                # --------------------------------------------

                annonce_existante = (
                    supabase
                    .table("annonces")
                    .select("*")
                    .eq("url", url)
                    .execute()
                )

                if annonce_existante.data:

                    annonce = annonce_existante.data[0]

                    st.warning(
                        "⚠️ Cette annonce existe déjà. "
                        "Le matching va être relancé."
                    )

                else:

                    insertion = (
                        supabase
                        .table("annonces")
                        .insert(annonce_data)
                        .execute()
                    )

                    annonce = insertion.data[0]

                    st.success(
                        "✅ Annonce enregistrée."
                    )

                # --------------------------------------------
                # Récupération des acquéreurs actifs
                # --------------------------------------------

                acquereurs = get_acquereurs(
                    actif=True
                )

                if not acquereurs:

                    st.warning(
                        "⚠️ Aucun acquéreur actif n'est enregistré."
                    )

                else:

                    # ----------------------------------------
                    # MATCHING
                    # ----------------------------------------

                    resultats = matcher_tous_les_acquereurs(
                        acquereurs,
                        annonce
                    )

                    st.markdown("---")

                    st.subheader(
                        "🎯 Résultats du matching"
                    )

                    # ----------------------------------------
                    # Enregistrement des matches
                    # ----------------------------------------

                    for resultat in resultats:

                        acquereur = resultat[
                            "acquereur"
                        ]

                        match_data = {

                            "acquereur_id":
                                acquereur["id"],

                            "annonce_id":
                                annonce["id"],

                            "statut_matching":
                                resultat[
                                    "statut_matching"
                                ],

                            "score":
                                resultat["score"],

                            "details_matching":
                                resultat[
                                    "details_matching"
                                ],

                            "statut":
                                "nouveau",

                            "alerte_envoyee":
                                False
                        }

                        supabase.table(
                            "matches"
                        ).upsert(
                            match_data,
                            on_conflict=(
                                "acquereur_id,annonce_id"
                            )
                        ).execute()

                    # ----------------------------------------
                    # AFFICHAGE
                    # ----------------------------------------

                    for resultat in resultats:

                        acquereur = resultat[
                            "acquereur"
                        ]

                        statut = resultat[
                            "statut_matching"
                        ]

                        score = resultat[
                            "score"
                        ]

                        if statut == "correspondance":

                            emoji = "🟢"
                            titre_statut = (
                                "Correspondance"
                            )

                        elif statut == "a_verifier":

                            emoji = "🟠"
                            titre_statut = (
                                "À vérifier"
                            )

                        else:

                            emoji = "🔴"
                            titre_statut = (
                                "Écarté"
                            )

                        with st.expander(
                            f"{emoji} "
                            f"{acquereur['prenom']} "
                            f"{acquereur['nom']} "
                            f" — {titre_statut} "
                            f" — Score {score}%"
                        ):

                            for detail in resultat[
                                "details_matching"
                            ]:

                                if detail[
                                    "statut"
                                ] == "correspondance":

                                    st.success(
                                        "✅ "
                                        + detail["message"]
                                    )

                                elif detail[
                                    "statut"
                                ] == "a_verifier":

                                    st.warning(
                                        "⚠️ "
                                        + detail["message"]
                                    )

                                else:

                                    st.error(
                                        "❌ "
                                        + detail["message"]
                                    )

            except Exception as e:

                st.error(
                    "❌ Une erreur est survenue."
                )

                st.write(str(e))


# ============================================================
# MATCHING
# ============================================================

elif page == "🎯 Matching":

    st.title("🎯 Matching")

    st.write(
        "Historique des correspondances entre annonces et acquéreurs."
    )

    try:

        matches = get_matches()

        if not matches:

            st.info(
                "Aucun matching enregistré pour le moment."
            )

        else:

            for match in matches:

                statut = match.get(
                    "statut_matching"
                )

                if statut == "correspondance":
                    emoji = "🟢"

                elif statut == "a_verifier":
                    emoji = "🟠"

                else:
                    emoji = "🔴"

                st.write(
                    f"{emoji} "
                    f"Score : {match.get('score', 0)}%"
                )

    except Exception as e:

        st.error(
            "❌ Impossible de récupérer les matches."
        )

        st.write(str(e))
