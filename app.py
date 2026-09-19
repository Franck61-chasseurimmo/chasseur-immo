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

    st.title("👤 Acquéreurs")

    st.info(
        "La gestion des fiches acquéreurs sera construite ici."
    )


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
