import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    """
    Crée et retourne la connexion à Supabase.
    """

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


# Connexion globale utilisée par l'application
supabase = get_supabase()


# ============================================================
# ACQUEREURS
# ============================================================

def get_acquereurs(actif=True):
    """
    Récupère les acquéreurs.
    """

    query = supabase.table("acquereurs").select("*")

    if actif:
        query = query.eq("actif", True)

    response = query.order("created_at", desc=True).execute()

    return response.data


# ============================================================
# ANNONCES
# ============================================================

def get_annonces():
    """
    Récupère toutes les annonces.
    """

    response = (
        supabase
        .table("annonces")
        .select("*")
        .order("imported_at", desc=True)
        .execute()
    )

    return response.data


def get_annonce_by_url(url):
    """
    Recherche une annonce à partir de son URL.
    """

    response = (
        supabase
        .table("annonces")
        .select("*")
        .eq("url", url)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def insert_annonce(data):
    """
    Enregistre une nouvelle annonce.
    """

    response = (
        supabase
        .table("annonces")
        .insert(data)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


# ============================================================
# MATCHES
# ============================================================

def get_matches():
    """
    Récupère tous les matches.
    """

    response = (
        supabase
        .table("matches")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data


def get_matches_for_acquereur(acquereur_id):
    """
    Récupère les matches d'un acquéreur.
    """

    response = (
        supabase
        .table("matches")
        .select("*")
        .eq("acquereur_id", acquereur_id)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data


def insert_match(data):
    """
    Enregistre un match.
    """

    response = (
        supabase
        .table("matches")
        .upsert(
            data,
            on_conflict="acquereur_id,annonce_id"
        )
        .execute()
    )

    if response.data:
        return response.data[0]

    return None
