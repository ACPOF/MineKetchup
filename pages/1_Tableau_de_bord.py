"""
Tableau de bord admin (producteur) : consultation des commandes reçues.

Protégé par un mot de passe simple (défini dans les secrets Streamlit,
clé ADMIN_PASSWORD). Utilise la clé service_role de Supabase, qui a accès
complet aux données — c'est pourquoi cette page ne doit être utilisée
qu'après authentification.
"""

import pandas as pd
import streamlit as st

from lib.supabase_client import get_admin_client

st.set_page_config(
    page_title="Tableau de bord - Commandes",
    page_icon="📋",
    layout="wide",
)

STATUS_OPTIONS = ["nouvelle", "en préparation", "prête", "complétée", "annulée"]


def check_password() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    st.title("🔒 Tableau de bord")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd and pwd == st.secrets.get("ADMIN_PASSWORD"):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    return False


if not check_password():
    st.stop()

st.title("📋 Commandes reçues")

col_logout, _ = st.columns([1, 5])
with col_logout:
    if st.button("Se déconnecter"):
        st.session_state.admin_authenticated = False
        st.rerun()

client = get_admin_client()


@st.cache_data(ttl=15)
def load_orders():
    orders_res = (
        client.table("orders")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    items_res = client.table("order_items").select("*").execute()
    return orders_res.data or [], items_res.data or []


orders, items = load_orders()

if not orders:
    st.info("Aucune commande reçue pour le moment.")
    st.stop()

items_by_order = {}
for it in items:
    items_by_order.setdefault(it["order_id"], []).append(it)

st.subheader("Filtrer")
status_filter = st.multiselect(
    "Statut",
    STATUS_OPTIONS,
    default=[s for s in STATUS_OPTIONS if s not in ("complétée", "annulée")],
)

filtered_orders = [o for o in orders if o["status"] in status_filter] if status_filter else orders

st.caption(f"{len(filtered_orders)} commande(s) affichée(s) sur {len(orders)} au total.")

if st.button("🔄 Rafraîchir"):
    load_orders.clear()
    st.rerun()

for order in filtered_orders:
    order_items = items_by_order.get(order["id"], [])
    header = (
        f"{order['retailer_name']} — {order['status']} — "
        f"{pd.to_datetime(order['created_at']).strftime('%Y-%m-%d %H:%M')}"
    )
    with st.expander(header):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Contact :** {order.get('contact_name') or '—'}")
            st.markdown(f"**Téléphone :** {order.get('phone') or '—'}")
            st.markdown(f"**Courriel :** {order.get('email') or '—'}")
        with col2:
            st.markdown(f"**Date souhaitée :** {order.get('requested_date') or '—'}")
            st.markdown(f"**Notes :** {order.get('notes') or '—'}")

        if order_items:
            df = pd.DataFrame(
                [
                    {
                        "Produit": it["product_name"],
                        "Quantité": it["quantity"],
                        "Unité": it["unit"],
                    }
                    for it in order_items
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.write("Aucun article.")

        new_status = st.selectbox(
            "Statut de la commande",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(order["status"]),
            key=f"status_{order['id']}",
        )
        if new_status != order["status"]:
            if st.button("Enregistrer le statut", key=f"save_{order['id']}"):
                client.table("orders").update({"status": new_status}).eq(
                    "id", order["id"]
                ).execute()
                load_orders.clear()
                st.success("Statut mis à jour.")
                st.rerun()
