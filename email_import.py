import imaplib
import streamlit as st

IMAP_SERVER = "imap.mail.yahoo.com"
IMAP_PORT = 993

def get_yahoo_connection():
    yahoo_email = st.secrets["YAHOO_EMAIL"]
    yahoo_app_password = st.secrets["YAHOO_APP_PASSWORD"]
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(yahoo_email, yahoo_app_password)
    return mail
