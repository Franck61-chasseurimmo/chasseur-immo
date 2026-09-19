import streamlit as st
from supabase import create_client, Client

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Chasseur Immo",
    page_icon="🏠",
    layout="wide"
)

# ============================================================
# CONNEXION SUPABASE
# ============================================================

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


supabase = init_supabase()

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
        acquereurs = supabase.table("acquereurs").select(
            "id",
            count="exact"
        ).execute()

        annonces = supabase.table("annonces").select(
            "id",
            count="exact"
        ).execute()

        matches = supabase.table("matches").select(
            "id",
            count="exact"
        ).execute()

        nb_acquereurs = acquereurs.count or 0
        nb_annonces = annonces.count or 0
        nb_matches = matches.count or 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Acquéreurs", nb_acquereurs)

        with col2:
            st.metric("Annonces", nb_annonces)

        with col3:
            st.metric("Matches", nb_matches)

        st.success("✅ Connexion à Supabase réussie.")

    except Exception as e:

        st.error("❌ Impossible de se connecter à Supabase.")
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
        prenom = st.text_input("Prénom *")

    with col2:
        nom = st.text_input("Nom *")

    col3, col4 = st.columns(2)

    with col3:
        telephone = st.text_input("Téléphone")

    with col4:
        email = st.text_input("Email")

    # --------------------------------------------------------
    # TYPE DE BIEN
    # --------------------------------------------------------

    st.subheader("🏠 Type de bien recherché")

    col1, col2, col3 = st.columns(3)

    with col1:
        recherche_maison = st.checkbox("Maison")

    with col2:
        recherche_pavillon = st.checkbox("Pavillon")

    with col3:
        recherche_maison_pierre = st.checkbox("Maison en pierre")

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
                    "plain_pied_obligatoire": plain_pied_obligatoire,
                    "chambres_min": chambres_min if chambres_min > 0 else None,
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
                    "secteur": secteur,
                    "rayon_km": rayon_km,
                    "surface_terrain_souhaitee": (
                        surface_terrain
                        if surface_terrain > 0
                        else None
                    ),
                    "budget_max": budget_max,
                    "marge_budget": 2000,
                    "notes": notes,
                    "actif": True
                }

                result = supabase.table(
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

    st.info(
        "Les annonces immobilières seront affichées ici."
    )


# ============================================================
# MATCHING
# ============================================================

elif page == "🎯 Matching":

    st.title("🎯 Matching")

    st.info(
        "Le moteur de matching sera construit ici."
    )
