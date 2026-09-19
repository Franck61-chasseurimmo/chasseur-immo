import streamlit as st

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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Acquéreurs",
            "0"
        )

    with col2:
        st.metric(
            "Annonces",
            "0"
        )

    with col3:
        st.metric(
            "Matches",
            "0"
        )

    st.markdown("---")

    st.info(
        "Les statistiques seront automatiquement alimentées "
        "par Supabase."
    )

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
