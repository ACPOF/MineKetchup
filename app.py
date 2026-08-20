"""
Page principale : formulaire de commande pour les détaillants.

Aucune identification requise. Le détaillant :
1. indique la quantité désirée pour chaque produit du catalogue,
2. remplit ses coordonnées,
3. soumet — la commande est enregistrée dans Supabase et apparaît
   immédiatement dans le tableau de bord du producteur.

Aucun paiement n'est traité par cette app.
"""

import pandas as pd
import streamlit as st

from lib.supabase_client import get_public_client

st.set_page_config(
    page_title="Passer une commande",
    page_icon="🧺",
    layout="centered",
)


def load_products():
    client = get_public_client()
    response = (
        client.table("products")
        .select("id, name, description, category, unit, price")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    )
    return response.data or []


def reset_cart():
    for key in list(st.session_state.keys()):
        if key.startswith("qty_"):
            del st.session_state[key]


st.title("🧺 Passer une commande")
st.caption(
    "Remplissez les quantités désirées ci-dessous, puis vos coordonnées. "
    "Aucun paiement n'est requis ici — vous serez contacté(e) pour la "
    "confirmation et le paiement."
)

products = load_products()

if not products:
    st.warning(
        "Le catalogue de produits n'est pas encore configuré. "
        "Merci de contacter le producteur directement."
    )
    st.stop()

if "order_submitted" not in st.session_state:
    st.session_state.order_submitted = False

if st.session_state.order_submitted:
    st.success(
        "✅ Votre commande a bien été envoyée ! Vous recevrez une "
        "confirmation directement du producteur."
    )
    if st.button("Passer une nouvelle commande"):
        reset_cart()
        st.session_state.order_submitted = False
        st.rerun()
    st.stop()

st.subheader("1. Choisissez vos produits")

# Regrouper par catégorie pour un affichage plus lisible
categories = {}
for p in products:
    cat = p.get("category") or "Autres"
    categories.setdefault(cat, []).append(p)

for cat, items in categories.items():
    st.markdown(f"**{cat}**")
    for p in items:
        cols = st.columns([4, 2, 2])
        with cols[0]:
            label = p["name"]
            if p.get("description"):
                st.markdown(f"{label}  \n:gray[{p['description']}]")
            else:
                st.markdown(label)
        with cols[1]:
            price_txt = f"{p['price']:.2f} $ / {p['unit']}" if p.get("price") else p["unit"]
            st.markdown(f":gray[{price_txt}]")
        with cols[2]:
            st.number_input(
                "Quantité",
                min_value=0,
                step=1,
                key=f"qty_{p['id']}",
                label_visibility="collapsed",
            )
    st.divider()

# Construire le panier à partir des quantités saisies
cart = []
for p in products:
    qty = st.session_state.get(f"qty_{p['id']}", 0)
    if qty and qty > 0:
        cart.append({**p, "quantity": qty})

if cart:
    st.subheader("Résumé de votre commande")
    df = pd.DataFrame(
        [
            {
                "Produit": c["name"],
                "Quantité": c["quantity"],
                "Unité": c["unit"],
            }
            for c in cart
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)
else:
    st.info("Ajoutez au moins un produit ci-dessus pour continuer.")

st.subheader("2. Vos coordonnées")

with st.form("order_form"):
    retailer_name = st.text_input("Nom de votre commerce *", max_chars=200)
    contact_name = st.text_input("Nom du contact")
    col1, col2 = st.columns(2)
    with col1:
        phone = st.text_input("Téléphone")
    with col2:
        email = st.text_input("Courriel")
    requested_date = st.date_input("Date de livraison/collecte souhaitée", value=None)
    notes = st.text_area(
        "Notes ou produits hors-catalogue",
        placeholder="Ex : allergies, instructions de livraison, produit spécial...",
    )

    submitted = st.form_submit_button("Envoyer ma commande", type="primary")

    if submitted:
        errors = []
        if not retailer_name.strip():
            errors.append("Le nom de votre commerce est requis.")
        if not cart:
            errors.append("Veuillez sélectionner au moins un produit.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            client = get_public_client()
            order_payload = {
                "retailer_name": retailer_name.strip(),
                "contact_name": contact_name.strip() or None,
                "phone": phone.strip() or None,
                "email": email.strip() or None,
                "requested_date": requested_date.isoformat() if requested_date else None,
                "notes": notes.strip() or None,
            }
            try:
                order_res = client.table("orders").insert(order_payload).execute()
                order_id = order_res.data[0]["id"]

                items_payload = [
                    {
                        "order_id": order_id,
                        "product_id": c["id"],
                        "product_name": c["name"],
                        "unit": c["unit"],
                        "quantity": c["quantity"],
                        "price": c.get("price"),
                    }
                    for c in cart
                ]
                client.table("order_items").insert(items_payload).execute()

                st.session_state.order_submitted = True
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Une erreur est survenue lors de l'envoi de la commande : {exc}")
