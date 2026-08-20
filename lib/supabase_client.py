"""
Petites fonctions utilitaires pour créer les clients Supabase.

Deux clients distincts, à dessein :
- le client "public" (clé anon) : utilisé par la page de commande, accès
  limité par les policies RLS (lecture des produits actifs, insertion de
  commandes seulement).
- le client "admin" (clé service_role) : utilisé UNIQUEMENT par le tableau
  de bord, après vérification du mot de passe admin. Cette clé contourne
  RLS et a accès complet — elle ne doit jamais être envoyée au navigateur
  du détaillant, ce qui est le cas ici puisque Streamlit exécute tout le
  code Python côté serveur.
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_public_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


@st.cache_resource
def get_admin_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)
