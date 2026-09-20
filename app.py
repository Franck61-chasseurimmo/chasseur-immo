import streamlit as st

from database import (
supabase,
get_acquereurs,
get_annonces,
get_matches
)

from matching import matcher_tous_les_acquereurs

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
st.sidebar.caption("Recherche immobilière")

# ============================================================

# TABLEAU DE BORD

# ============================================================

if page == "🏠 Tableau de bord":

```
st.title("🏠 Chasseur Immo")

st.subheader("Tableau de bord")

try:

    acquereurs = get_acquereurs(actif=False)
    annonces = get_annonces()
    matches = get_matches()

    nb_acquereurs = len(acquereurs)
    nb_annonces = len(annonces)
    nb_matches = len(matches)

    nb_correspondances = sum(
        1
        for match in matches
        if match.get("statut_matching") == "correspondance"
    )

    nb_a_verifier = sum(
        1
        for match in matches
        if match.get("statut_matching") == "a_verifier"
    )

    nb_ecartes = sum(
        1
        for match in matches
        if match.get("statut_matching") == "ecarte"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "👤 Acquéreurs",
            nb_acquereurs
        )

    with col2:
        st.metric(
            "🏠 Annonces",
            nb_annonces
        )

    with col3:
        st.metric(
            "🎯 Matches",
            nb_matches
        )

    st.markdown("---")

    st.subheader("État du matching")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "🟢 Correspondances",
            nb_correspondances
        )

    with col2:
        st.metric(
            "🟠 À vérifier",
            nb_a_verifier
        )

    with col3:
        st.metric(
            "🔴 Écartés",
            nb_ecartes
        )

    st.success(
        "✅ Connexion à Supabase opérationnelle."
    )

except Exception as e:

    st.error(
        "❌ Erreur lors du chargement du tableau de bord."
    )

    st.write(str(e))
```

# ============================================================

# ACQUEREURS

# ============================================================

elif page == "👤 Acquéreurs":

```
st.title("👤 Acquéreurs")

st.write(
    "Créez le cahier des charges de votre acquéreur."
)

st.subheader("Identité")

col1, col2 = st.columns(2)

with col1:
    prenom = st.text_input(
        "Prénom *"
    )

with col2:
    nom = st.text_input(
        "Nom *"
    )

col1, col2 = st.columns(2)

with col1:
    telephone = st.text_input(
        "Téléphone"
    )

with col2:
    email = st.text_input(
        "Email"
    )

st.subheader("🏠 Type de bien")

col1, col2, col3 = st.columns(3)

with col1:
    recherche_maison = st.checkbox(
        "Maison"
    )

with col2:
    recherche_pavillon = st.checkbox(
        "Pavillon"
    )

with col3:
    recherche_maison_pierre = st.checkbox(
        "Maison en pierre"
    )

st.subheader("🛏️ Critères")

col1, col2 = st.columns(2)

with col1:
    plain_pied_obligatoire = st.checkbox(
        "Plain-pied obligatoire"
    )

with col2:
    garage_obligatoire = st.checkbox(
        "Garage obligatoire"
    )

col1, col2 = st.columns(2)

with col1:
    chambres_min = st.number_input(
        "Chambres minimum",
        min_value=0,
        value=0,
        step=1
    )

with col2:
    chambres_rdc_min = st.number_input(
        "Chambres au RDC minimum",
        min_value=0,
        value=0,
        step=1
    )

col1, col2 = st.columns(2)

with col1:
    salle_eau_rdc = st.checkbox(
        "Salle d'eau au RDC obligatoire"
    )

with col2:
    salles_eau_min = st.number_input(
        "Salles d'eau minimum",
        min_value=0,
        value=0,
        step=1
    )

sous_sol_recherche = st.checkbox(
    "Sous-sol recherché"
)

st.subheader("📍 Localisation")

secteur = st.text_input(
    "Secteur",
    value="Alençon"
)

rayon_km = st.number_input(
    "Rayon de recherche (km)",
    min_value=0.0,
    value=20.0,
    step=1.0
)

st.subheader("🌳 Terrain")

surface_terrain = st.number_input(
    "Surface de terrain souhaitée (m²)",
    min_value=0.0,
    value=0.0,
    step=10.0
)

st.subheader("💰 Budget")

budget_max = st.number_input(
    "Budget maximum (€)",
    min_value=0.0,
    value=0.0,
    step=1000.0
)

st.caption(
    "Une marge automatique de 2 000 € est appliquée au matching."
)

st.subheader("📝 Notes")

notes = st.text_area(
    "Précisions complémentaires"
)

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
            "⚠️ Le budget maximum est obligatoire."
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
                "chambres_rdc_min": chambres_rdc_min if chambres_rdc_min > 0 else None,
                "salle_eau_rdc": salle_eau_rdc,
                "salles_eau_min": salles_eau_min if salles_eau_min > 0 else None,
                "garage_obligatoire": garage_obligatoire,
                "sous_sol_recherche": sous_sol_recherche,
                "secteur": secteur,
                "rayon_km": rayon_km,
                "surface_terrain_souhaitee": surface_terrain if surface_terrain > 0 else None,
                "budget_max": budget_max,
                "marge_budget": 2000,
                "notes": notes,
                "actif": True
            }

            supabase.table(
                "acquereurs"
            ).insert(
                data
            ).execute()

            st.success(
                "✅ Acquéreur enregistré avec succès."
            )

        except Exception as e:

            st.error(
                "❌ Erreur lors de l'enregistrement."
            )

            st.write(str(e))
```

# ============================================================

# ANNONCES

# ============================================================

elif page == "📋 Annonces":

```
st.title("📋 Annonces")

st.write(
    "Ajoutez une annonce immobilière manuellement."
)

st.info(
    "🔎 La recherche automatique des sites immobiliers "
    "sera ajoutée ensuite."
)

st.subheader("🔗 Informations générales")

url = st.text_input(
    "URL de l'annonce *",
    placeholder="https://..."
)

titre = st.text_input(
    "Titre de l'annonce"
)

col1, col2, col3 = st.columns(3)

with col1:
    prix = st.number_input(
        "Prix (€)",
        min_value=0.0,
        value=0.0,
        step=1000.0
    )

with col2:
    commune = st.text_input(
        "Commune"
    )

with col3:
    source = st.text_input(
        "Source",
        placeholder="LeBonCoin, SeLoger..."
    )

st.subheader("🏠 Type de bien")

type_maison = st.selectbox(
    "Type",
    [
        "Maison",
        "Pavillon",
        "Maison en pierre"
    ]
)

col1, col2, col3 = st.columns(3)

with col1:
    maison_pierre = st.selectbox(
        "Maison en pierre ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

with col2:
    pavillon = st.selectbox(
        "Pavillon ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

with col3:
    plain_pied = st.selectbox(
        "Plain-pied ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

st.subheader("🛏️ Chambres et salles d'eau")

col1, col2, col3 = st.columns(3)

with col1:
    chambres = st.number_input(
        "Chambres",
        min_value=0,
        value=0,
        step=1
    )

with col2:
    chambres_rdc = st.number_input(
        "Chambres RDC",
        min_value=0,
        value=0,
        step=1
    )

with col3:
    salles_eau = st.number_input(
        "Salles d'eau",
        min_value=0,
        value=0,
        step=1
    )

col1, col2, col3 = st.columns(3)

with col1:
    salle_eau_rdc = st.selectbox(
        "Salle d'eau RDC ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

with col2:
    garage = st.selectbox(
        "Garage ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

with col3:
    sous_sol = st.selectbox(
        "Sous-sol ?",
        [
            "Non précisé",
            "Oui",
            "Non"
        ]
    )

surface_terrain = st.number_input(
    "Surface du terrain (m²)",
    min_value=0.0,
    value=0.0,
    step=10.0
)

description = st.text_area(
    "Description"
)

st.markdown("---")

if st.button(
    "🔎 Enregistrer et lancer le matching",
    type="primary",
    use_container_width=True
):

    if not url:

        st.error(
            "⚠️ L'URL de l'annonce est obligatoire."
        )

    else:

        try:

            def convertir_booleen(valeur):

                if valeur == "Oui":
                    return True

                if valeur == "Non":
                    return False

                return None

            annonce_data = {
                "url": url,
                "titre": titre,
                "source": source,
                "prix": prix if prix > 0 else None,
                "commune": commune,
                "type_maison": type_maison,
                "plain_pied": convertir_booleen(plain_pied),
                "maison_pierre": convertir_booleen(maison_pierre),
                "pavillon": convertir_booleen(pavillon),
                "chambres": chambres if chambres > 0 else None,
                "chambres_rdc": chambres_rdc if chambres_rdc > 0 else None,
                "salle_eau_rdc": convertir_booleen(salle_eau_rdc),
                "salles_eau": salles_eau if salles_eau > 0 else None,
                "garage": convertir_booleen(garage),
                "sous_sol": convertir_booleen(sous_sol),
                "surface_terrain": surface_terrain if surface_terrain > 0 else None,
                "description": description
            }

            annonce_existante = (
                supabase
                .table("annonces")
                .select("*")
                .eq("url", url)
                .execute()
            )

            if annonce_existante.data:

                annonce = annonce_existante.data[0]

                st.warning(
                    "⚠️ Cette annonce existe déjà."
                )

            else:

                response = (
                    supabase
                    .table("annonces")
                    .insert(annonce_data)
                    .execute()
                )

                annonce = response.data[0]

                st.success(
                    "✅ Annonce enregistrée."
                )

            acquereurs = get_acquereurs(
                actif=True
            )

            if not acquereurs:

                st.warning(
                    "⚠️ Aucun acquéreur actif."
                )

            else:

                resultats = matcher_tous_les_acquereurs(
                    acquereurs,
                    annonce
                )

                for resultat in resultats:

                    match_data = {
                        "acquereur_id": resultat["acquereur"]["id"],
                        "annonce_id": annonce["id"],
                        "statut_matching": resultat["statut_matching"],
                        "score": resultat["score"],
                        "details_matching": resultat["details_matching"],
                        "statut": "nouveau",
                        "alerte_envoyee": False
                    }

                    (
                        supabase
                        .table("matches")
                        .upsert(
                            match_data,
                            on_conflict="acquereur_id,annonce_id"
                        )
                        .execute()
                    )

                st.markdown("---")
                st.subheader("🎯 Résultats")

                for resultat in resultats:

                    acquereur = resultat["acquereur"]
                    statut = resultat["statut_matching"]
                    score = resultat["score"]

                    if statut == "correspondance":

                        emoji = "🟢"
                        texte = "Correspondance"

                    elif statut == "a_verifier":

                        emoji = "🟠"
                        texte = "À vérifier"

                    else:

                        emoji = "🔴"
                        texte = "Écarté"

                    st.markdown(
                        f"### {emoji} "
                        f"{acquereur['prenom']} "
                        f"{acquereur['nom']}"
                    )

                    st.write(
                        f"**Statut :** {texte}"
                    )

                    st.write(
                        f"**Score :** {score}%"
                    )

                    for detail in resultat["details_matching"]:

                        if detail["statut"] == "correspondance":

                            st.success(
                                "✅ " + detail["message"]
                            )

                        elif detail["statut"] == "a_verifier":

                            st.warning(
                                "⚠️ " + detail["message"]
                            )

                        else:

                            st.error(
                                "❌ " + detail["message"]
                            )

        except Exception as e:

            st.error(
                "❌ Erreur lors du traitement de l'annonce."
            )

            st.write(str(e))
```

# ============================================================

# MATCHING

# ============================================================

elif page == "🎯 Matching":

```
st.title("🎯 Matching")

st.write(
    "Toutes les correspondances entre vos annonces et vos acquéreurs."
)

try:

    matches = get_matches()
    acquereurs = get_acquereurs(actif=False)
    annonces = get_annonces()

    acquereurs_par_id = {
        acquereur["id"]: acquereur
        for acquereur in acquereurs
    }

    annonces_par_id = {
        annonce["id"]: annonce
        for annonce in annonces
    }

    if not matches:

        st.info(
            "Aucun matching enregistré pour le moment."
        )

    else:

        nb_correspondances = sum(
            1
            for match in matches
            if match.get("statut_matching") == "correspondance"
        )

        nb_a_verifier = sum(
            1
            for match in matches
            if match.get("statut_matching") == "a_verifier"
        )

        nb_ecartes = sum(
            1
            for match in matches
            if match.get("statut_matching") == "ecarte"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "🟢 Correspondances",
                nb_correspondances
            )

        with col2:
            st.metric(
                "🟠 À vérifier",
                nb_a_verifier
            )

        with col3:
            st.metric(
                "🔴 Écartés",
                nb_ecartes
            )

        st.markdown("---")

        for match in matches:

            statut = match.get(
                "statut_matching"
            )

            score = match.get(
                "score",
                0
            )

            acquereur = acquereurs_par_id.get(
                match.get("acquereur_id")
            )

            annonce = annonces_par_id.get(
                match.get("annonce_id")
            )

            if statut == "correspondance":

                emoji = "🟢"
                texte_statut = "Correspondance"

            elif statut == "a_verifier":

                emoji = "🟠"
                texte_statut = "À vérifier"

            else:

                emoji = "🔴"
                texte_statut = "Écarté"

            if acquereur:

                nom_acquereur = (
                    f"{acquereur.get('prenom', '')} "
                    f"{acquereur.get('nom', '')}"
                ).strip()

            else:

                nom_acquereur = "Acquéreur introuvable"

            if annonce:

                titre_annonce = (
                    annonce.get("titre")
                    or "Annonce sans titre"
                )

                commune = (
                    annonce.get("commune")
                    or "Commune non précisée"
                )

                prix = annonce.get(
                    "prix"
                )

                url_annonce = annonce.get(
                    "url"
                )

            else:

                titre_annonce = "Annonce introuvable"
                commune = "—"
                prix = None
                url_annonce = None

            st.markdown("---")

            st.markdown(
                f"## {emoji} {nom_acquereur}"
            )

            col1, col2 = st.columns(
                [3, 1]
            )

            with col1:

                st.write(
                    f"**Statut :** {texte_statut}"
                )

                st.write(
                    f"**Annonce :** {titre_annonce}"
                )

                st.write(
                    f"📍 **Commune :** {commune}"
                )

                if prix:

                    st.write(
                        f"💰 **Prix :** "
                        f"{prix:,.0f} €".replace(",", " ")
                    )

            with col2:

                st.metric(
                    "Score",
                    f"{score}%"
                )

            if url_annonce:

                st.link_button(
                    "🔗 Ouvrir l'annonce",
                    url_annonce
                )

            st.write(
                "### 🔎 Détail des critères"
            )

            details = match.get(
                "details_matching"
            ) or []

            if not details:

                st.info(
                    "Aucun détail disponible."
                )

            else:

                for detail in details:

                    detail_statut = detail.get(
                        "statut"
                    )

                    message = detail.get(
                        "message",
                        ""
                    )

                    if detail_statut == "correspondance":

                        st.success(
                            "🟢 " + message
                        )

                    elif detail_statut == "a_verifier":

                        st.warning(
                            "🟠 " + message
                        )

                    else:

                        st.error(
                            "🔴 " + message
                        )

except Exception as e:

    st.error(
        "❌ Erreur lors du chargement du matching."
    )

    st.write(str(e))
```
