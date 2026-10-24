"""Accès Supabase côté serveur. Aucune connexion lors de l'import Python."""
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    try:
        url, key = st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY']
    except (KeyError, FileNotFoundError) as exc:
        raise RuntimeError('Configurez SUPABASE_URL et SUPABASE_KEY dans les secrets.') from exc
    return create_client(url, key)


def _lister(table, filtres=None, ordre='id'):
    rows, debut = [], 0
    while True:
        query = get_supabase().table(table).select('*')
        for key, value in (filtres or {}).items():
            query = query.eq(key, value)
        lot = query.order(ordre).range(debut, debut + 499).execute().data or []
        rows.extend(lot)
        if len(lot) < 500:
            return rows
        debut += 500


def get_acquereurs(actif=True):
    return _lister('acquereurs', {'actif': True} if actif else None)


def get_annonces(actives=False):
    return _lister('annonces', {'statut_annonce': 'disponible'} if actives else None)


def get_matches():
    return _lister('matches')


def get_matches_for_acquereur(acquereur_id):
    return _lister('matches', {'acquereur_id': acquereur_id})


def get_annonce_by_url(url):
    rows = get_supabase().table('annonces').select('*').eq('url', url).limit(1).execute().data
    return rows[0] if rows else None


def enregistrer(table, data, identifiant=None):
    query = get_supabase().table(table)
    result = (query.update(data).eq('id', identifiant) if identifiant is not None else query.insert(data)).execute()
    if not result.data:
        raise RuntimeError('Enregistrement non confirmé par la base.')
    return result.data[0]


def insert_annonce(data):
    # ignore_duplicates préserve les caractéristiques déjà corrigées manuellement.
    result = get_supabase().table('annonces').upsert(data, on_conflict='url', ignore_duplicates=True).execute()
    return result.data[0] if result.data else get_annonce_by_url(data['url'])


def insert_match(data):
    # Le recalcul ne doit jamais écraser le suivi commercial.
    payload = {k: v for k, v in data.items() if k not in ('statut', 'commentaire')}
    result = get_supabase().table('matches').upsert(payload, on_conflict='acquereur_id,annonce_id').execute()
    return result.data[0] if result.data else None


def email_traite(cle):
    return bool(get_supabase().table('email_imports').select('cle').eq('cle', cle).limit(1).execute().data)


def marquer_email(cle, nombre):
    get_supabase().table('email_imports').upsert({'cle': cle, 'nombre_annonces': nombre}, on_conflict='cle').execute()
