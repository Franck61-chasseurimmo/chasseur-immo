import streamlit as st

from email_import import (
    get_bienici_emails,
    extraire_liens_bienici,
)


# Configuration de la page
st.set_page_config(
    page_title="Emails Bien'ici",
    page_icon="🏠",
    layout="wide",
)


# Titre de la page
st.title("🏠 Annonces immobilières Bien'ici")
st.write(
    "Cette page récupère les e-mails Bien'ici et affiche les liens "
    "vers les annonces détectées."
)


# Bouton pour lancer la récupération des e-mails
if st.button("📩 Récupérer les e-mails Bien'ici", type="primary"):

    with st.spinner("Récupération des e-mails en cours..."):

        try:
            emails = get_bienici_emails()

        except Exception as erreur:
            st.error(
                "Une erreur est survenue lors de la récupération des e-mails :"
            )
            st.exception(erreur)
            st.stop()

    # Vérification du résultat
    if not emails:
        st.info("Aucun e-mail Bien'ici trouvé.")
        st.stop()

    st.success(
        f"{len(emails)} e-mail(s) Bien'ici récupéré(s)."
    )

    # Affichage des e-mails
    for index, email_data in enumerate(emails, start=1):

        # Récupération sécurisée des informations
        sujet = email_data.get("subject", "Sans objet")
        expediteur = email_data.get("sender", "Expéditeur inconnu")
        date_email = email_data.get("date", "Date inconnue")

        # Selon le code du backend, le corps peut avoir plusieurs noms.
        html_body = email_data.get("html_body", "")
        text_body = email_data.get("text_body", "")

        # Conversion en texte pour éviter les erreurs si une valeur vaut None
        html_body = html_body or ""
        text_body = text_body or ""

        # Regroupement du contenu de l'e-mail
        contenu_complet = f"{html_body}\n{text_body}"

        # Extraction des liens Bien'ici
        try:
            liens = extraire_liens_bienici(contenu_complet)

        except Exception as erreur:
            st.warning(
                f"Impossible d'extraire les liens de l'e-mail {index}."
            )
            st.exception(erreur)
            liens = []

        # Suppression des doublons tout en conservant l'ordre
        liens_uniques = list(dict.fromkeys(liens))

        # Affichage sous forme de bloc repliable
        with st.expander(
            f"📧 {sujet}",
            expanded=(index == 1),
        ):
            st.write(f"**Expéditeur :** {expediteur}")
            st.write(f"**Date :** {date_email}")

            st.divider()

            if liens_uniques:
                st.subheader(
                    f"🔗 {len(liens_uniques)} annonce(s) trouvée(s)"
                )

                for numero, lien in enumerate(liens_uniques, start=1):
                    st.link_button(
                        f"🔗 Voir l’annonce {numero}",
                        lien,
                        use_container_width=True,
                    )

                    # Affichage facultatif de l'URL
                    st.caption(lien)

            else:
                st.info(
                    "Aucun lien d'annonce Bien'ici n'a été trouvé "
                    "dans cet e-mail."
                )

            # Affichage facultatif du contenu brut pour le débogage
            with st.expander("Voir le contenu brut de l'e-mail"):
                if text_body:
                    st.text_area(
                        "Version texte",
                        text_body,
                        height=250,
                        key=f"text_body_{index}",
                    )

                if html_body:
                    st.code(
                        html_body,
                        language="html",
                    )
