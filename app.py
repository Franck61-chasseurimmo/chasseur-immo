import streamlit as st

# ---------------------------------------------------------
# CONFIGURATION DE LA PAGE
# ---------------------------------------------------------

st.set_page_config(
    page_title="Chasseur Immo",
    page_icon="🏠",
    layout="wide"
)

# ---------------------------------------------------------
# PAGE PRINCIPALE
# ---------------------------------------------------------

st.title("🏠 Chasseur Immo")

st.subheader("Application de recherche et de matching immobilier")

st.write(
    "Bienvenue dans votre outil de gestion des mandats de recherche."
)

# ---------------------------------------------------------
# MENU TEMPORAIRE
# ---------------------------------------------------------

st.sidebar.title("Navigation")

st.sidebar.info(
    "🚧 Application en construction"
)

st.markdown("---")

st.success(
    "✅ La première version de l'application est prête."
)

st.write(
    "Les prochaines étapes seront la connexion à Supabase, "
    "la création des fiches acquéreurs et le moteur de matching."
)
