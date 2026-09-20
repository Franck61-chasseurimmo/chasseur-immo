import streamlit as st
from email_import import get_bienici_emails

st.set_page_config(page_title="Emails Bien'ici", page_icon="📥", layout="wide")
st.title("📥 Emails Bien'ici")
st.write("Test de lecture des emails Bien'ici.")

bouton = st.button("📥 Lire les derniers emails Bien'ici", use_container_width=True)

if not bouton:
    st.stop()

emails = get_bienici_emails(limit=20)

st.success("Nombre d'emails trouvés : " + str(len(emails)))

for email_data in emails:
    st.write("Objet : " + email_data.get("subject", "Sans objet"))
    st.write("Expéditeur : " + email_data.get("sender", ""))
    st.write("Date : " + email_data.get("date", ""))
    st.text(email_data.get("text_body", ""))
    st.divider()
