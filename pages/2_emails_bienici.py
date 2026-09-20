import streamlit as st
from email_import import get_bienici_emails

st.set_page_config(page_title="Emails Bien'ici", page_icon="📥", layout="wide")

st.title("📥 Emails Bien'ici")

st.write("Test de lecture des emails Bien'ici reçus sur Yahoo.")

if not st.button("📥 Lire les derniers emails Bien'ici", use_container_width=True):
st.stop()

emails = get_bienici_emails(limit=20)

if len(emails) == 0:
st.warning("⚠️ Aucun email Bien'ici trouvé.")
st.stop()

st.success(f"✅ {len(emails)} email(s) Bien'ici trouvé(s).")

email_data = emails[0]

st.subheader("📧 Premier email trouvé")

st.write("Objet : " + email_data.get("subject", "Sans objet"))
st.write("Expéditeur : " + email_data.get("sender", ""))
st.write("Date : " + email_data.get("date", ""))

text_body = email_data.get("text_body", "")
html_body = email_data.get("html_body", "")

if text_body:
st.subheader("Contenu")
st.text(text_body)
elif html_body:
st.subheader("Contenu HTML")
st.html(html_body)
else:
st.info("Le contenu de cet email n'a pas pu être lu.")
