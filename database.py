"""Accès Supabase côté serveur. Aucune connexion lors de l'import Python."""

import streamlit as st

from supabase import create_client


@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

    except (KeyError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Configurez SUPABASE_URL et SUPABASE_KEY dans les secrets."
        ) from exc

    return create_client(url, key)


def _lister(table, filtres=None, ordre="id"):
    rows = []
    debut = 0

    while True:
        query = get_supabase().table(table).select("*")

        for key, value in (filtres or {}).items():
            query = query.eq(key, value)

        lot = (
            query.order(ordre)
            .range(debut, debut + 499)
            .execute()
            .data
            or []
        )

        rows.extend(lot)

        if len(lot) < 500:
            return rows

        debut += 500


def get_acquereurs(actif=True):
    return _lister(
        "acquereurs",
        {"actif": True} if actif else None,
    )


def get_annonces(actives=False):
    return _lister(
        "annonces",
        {"statut_annonce": "disponible"} if actives else None,
    )


def get_matches():
    return _lister("matches")


def get_matches_for_acquereur(acquereur_id):
    return _lister(
        "matches",
        {"acquereur_id": acquereur_id},
    )


def get_annonce_by_url(url):
    rows = (
        get_supabase()
        .table("annonces")
        .select("*")
        .eq("url", url)
        .limit(1)
        .execute()
        .data
    )

    return rows[0] if rows else None


def enregistrer(table, data, identifiant=None):
    query = get_supabase().table(table)

    if identifiant is not None:
        query = query.update(data).eq("id", identifiant)
    else:
        query = query.insert(data)

    result = query.execute()

    if not result.data:
        raise RuntimeError(
            "Enregistrement non confirmé par la base."
        )

    return result.data[0]


def insert_annonce(data):
    # Préserver les caractéristiques déjà corrigées manuellement.
    result = (
        get_supabase()
        .table("annonces")
        .upsert(
            data,
            on_conflict="url",
            ignore_duplicates=True,
        )
        .execute()
    )

    if result.data:
        return result.data[0]

    return get_annonce_by_url(data["url"])


def supprimer_annonce(identifiant):
    """Supprimer une annonce et ses correspondances liées."""
    if not identifiant or not str(identifiant).strip():
        raise ValueError(
            "Sélectionnez une annonce à supprimer."
        )

    # La contrainte ON DELETE CASCADE déjà présente dans Supabase
    # supprime automatiquement les correspondances de cette annonce.
    result = (
        get_supabase()
        .table("annonces")
        .delete()
        .eq("id", str(identifiant))
        .execute()
    )

    if not result.data:
        raise RuntimeError(
            "Suppression non confirmée par la base."
        )

    return result.data[0]


def insert_match(data):
    # Le recalcul ne doit jamais écraser le suivi commercial.
    payload = {
        key: value
        for key, value in data.items()
        if key not in ("statut", "commentaire")
    }

    result = (
        get_supabase()
        .table("matches")
        .upsert(
            payload,
            on_conflict="acquereur_id,annonce_id",
        )
        .execute()
    )

    return result.data[0] if result.data else None


def email_traite(cle):
    result = (
        get_supabase()
        .table("email_imports")
        .select("cle")
        .eq("cle", cle)
        .limit(1)
        .execute()
    )

    return bool(result.data)


def marquer_email(cle, nombre):
    (
        get_supabase()
        .table("email_imports")
        .upsert(
            {
                "cle": cle,
                "nombre_annonces": nombre,
            },
            on_conflict="cle",
        )
        .execute()
    )
