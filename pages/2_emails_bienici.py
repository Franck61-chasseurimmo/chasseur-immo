import streamlit as st
from email_import import get_bienici_emails

st.set_page_config(page_title="Emails Bien'ici", page_icon="📥", layout="wide")

st.title("📥 Emails Bien'ici")

st.write("Test de connexion et lecture des emails Bien'ici.")

bouton = st.button("📥 Lire les derniers emails Bien'ici", use_container_width=True)

if bouton:
    emails = get_bienici_emails(limit=20)

nombre = len(emails)

st.success("Nombre d'emails trouvés : " + str(nombre))

if nombre > 0:
    premier = emails[0]

    st.write("Objet : " + premier.get("subject", "Sans objet"))
    st.write("Expéditeur : " + premier.get("sender", ""))
    st.write("Date : " + premier.get("date", ""))

    st.write("Contenu :")

    st.text(premier.get("text_body", ""))

else:
    st.warning("Aucun email Bien'ici trouvé.")

