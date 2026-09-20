import streamlit as st
from email_import import get_yahoo_connection


st.title("Test connexion Yahoo")

try:
    mail = get_yahoo_connection()

    st.success("✅ Connexion à Yahoo réussie !")

    mail.logout()

except Exception as e:
    st.error("❌ La connexion à Yahoo a échoué.")

    st.write("Détail de l'erreur :")
    st.code(str(e))
