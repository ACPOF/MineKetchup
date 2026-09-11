"""
Mine de Ketchup — tableau de bord du producteur.

Trois sections, protégées par le même mot de passe (secret ADMIN_PASSWORD) :
  1. Commandes  : consulter les commandes reçues et changer leur statut.
  2. Produits   : gérer le catalogue (ajouter / modifier / activer / réordonner).
  3. Détaillants: gérer la liste déroulante de la page de commande. C'est ici
                  qu'on ajoute un détaillant UNE SEULE FOIS ; ensuite il
                  commande en 3 clics.

Utilise la clé service_role de Supabase (accès complet), d'où le mot de passe.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib.branding import brand_header, inject_theme, money
from lib.supabase_client import get_admin_client

st.set_page_config(
    page_title="Mine de Ketchup — Tableau de bord",
    page_icon="🍅",
    layout="wide",
)
inject_theme(wide=True)

STATUS_OPTIONS = ["nouvelle", "en préparation", "prête", "complétée", "annulée"]
STATUS_ICON = {
    "nouvelle": "🔴",
    "en préparation": "🟠",
    "prête": "🟢",
    "complétée": "✅",
    "annulée": "⚪",
}
OPEN_STATUSES = ["nouvelle", "en préparation", "prête"]


# ------------------------------------------------------------------
# Accès
# ------------------------------------------------------------------
def check_password() -> bool:
    if st.session_state.get("admin_authenticated"):
        return True

    brand_header("Tableau de bord du producteur")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            st.markdown("### 🔒 Accès réservé")
            pwd = st.text_input("Mot de passe", type="password", label_visibility="collapsed")
            if st.button("Se connecter", type="primary", width="stretch"):
                if pwd and pwd == st.secrets.get("ADMIN_PASSWORD"):
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
    return False


if not check_password():
    st.stop()

client = get_admin_client()


# ------------------------------------------------------------------
# Accès aux données
# ------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def load_orders() -> tuple[list[dict], list[dict]]:
    try:
        orders_res = (
            client.table("orders")
            .select("*, retailers(business_name, contact_name, phone, email)")
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:  # noqa: BLE001 — base pas encore migrée (table retailers absente)
        orders_res = client.table("orders").select("*").order("created_at", desc=True).execute()
    items_res = client.table("order_items").select("*").execute()
    return orders_res.data or [], items_res.data or []


def load_products() -> list[dict]:
    res = client.table("products").select("*").order("sort_order").order("name").execute()
    return res.data or []


def load_retailers() -> list[dict]:
    res = client.table("retailers").select("*").order("business_name").execute()
    return res.data or []


def order_buyer(order: dict) -> dict:
    """Coordonnées de l'auteur d'une commande : détaillant lié, sinon champs texte."""
    linked = order.get("retailers") or {}
    return {
        "business_name": linked.get("business_name") or order.get("retailer_name") or "—",
        "contact_name": linked.get("contact_name") or order.get("contact_name"),
        "phone": linked.get("phone") or order.get("phone"),
        "email": linked.get("email") or order.get("email"),
        "registered": bool(order.get("retailer_id")),
    }


def refresh() -> None:
    load_orders.clear()
    st.rerun()


# ------------------------------------------------------------------
# En-tête
# ------------------------------------------------------------------
head_left, head_right = st.columns([5, 1])
with head_left:
    brand_header("Tableau de bord du producteur")
with head_right:
    if st.button("Se déconnecter", width="stretch"):
        st.session_state.admin_authenticated = False
        st.rerun()

tab_orders, tab_products, tab_retailers = st.tabs(
    ["📋 Commandes", "🧂 Produits", "🏪 Détaillants"]
)


# ==================================================================
# 1. COMMANDES
# ==================================================================
with tab_orders:
    orders, items = load_orders()

    counts = {s: sum(1 for o in orders if o["status"] == s) for s in STATUS_OPTIONS}
    metric_cols = st.columns(4)
    metric_cols[0].metric("Nouvelles", counts["nouvelle"])
    metric_cols[1].metric("En préparation", counts["en préparation"])
    metric_cols[2].metric("Prêtes", counts["prête"])
    metric_cols[3].metric("Total reçues", len(orders))

    if not orders:
        st.info("Aucune commande reçue pour le moment.")
    else:
        items_by_order: dict[str, list[dict]] = {}
        for it in items:
            items_by_order.setdefault(it["order_id"], []).append(it)

        filter_col, refresh_col = st.columns([5, 1])
        with filter_col:
            status_filter = st.multiselect(
                "Filtrer par statut", STATUS_OPTIONS, default=OPEN_STATUSES
            )
        with refresh_col:
            st.write("")
            if st.button("🔄 Rafraîchir", width="stretch"):
                refresh()

        shown = [o for o in orders if o["status"] in status_filter] if status_filter else orders
        st.caption(f"{len(shown)} commande(s) affichée(s) sur {len(orders)} au total.")

        for order in shown:
            buyer = order_buyer(order)
            order_items = items_by_order.get(order["id"], [])
            created = pd.to_datetime(order["created_at"]).strftime("%Y-%m-%d %H:%M")
            nb = sum(float(it["quantity"]) for it in order_items)
            header = (
                f"{STATUS_ICON.get(order['status'], '•')}  {buyer['business_name']}"
                f"  —  {created}  —  {nb:g} article(s)"
            )
            with st.expander(header):
                info_col, items_col = st.columns([1, 2])
                with info_col:
                    if not buyer["registered"]:
                        st.warning(
                            "Commerce **non enregistré** — ajoutez-le dans l'onglet "
                            "« Détaillants » pour ses prochaines commandes.",
                            icon="⚠️",
                        )
                    st.markdown(f"**Contact :** {buyer['contact_name'] or '—'}")
                    st.markdown(f"**Téléphone :** {buyer['phone'] or '—'}")
                    st.markdown(f"**Courriel :** {buyer['email'] or '—'}")
                    st.markdown(f"**Date souhaitée :** {order.get('requested_date') or '—'}")
                    st.markdown(f"**Notes :** {order.get('notes') or '—'}")
                    st.caption(f"N° {str(order['id']).split('-')[0].upper()}")
                with items_col:
                    if order_items:
                        st.dataframe(
                            pd.DataFrame(
                                [
                                    {
                                        "Produit": it["product_name"],
                                        "Quantité": float(it["quantity"]),
                                        "Format": it["unit"],
                                        "Prix": money(it.get("price")) or "—",
                                    }
                                    for it in order_items
                                ]
                            ),
                            hide_index=True,
                            width="stretch",
                        )
                    else:
                        st.write("Aucun article.")

                status_col, save_col = st.columns([3, 1])
                with status_col:
                    new_status = st.selectbox(
                        "Statut",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(order["status"]),
                        key=f"status_{order['id']}",
                    )
                with save_col:
                    st.write("")
                    if st.button(
                        "Enregistrer",
                        key=f"save_{order['id']}",
                        disabled=new_status == order["status"],
                        width="stretch",
                        type="primary",
                    ):
                        client.table("orders").update({"status": new_status}).eq(
                            "id", order["id"]
                        ).execute()
                        refresh()


# ==================================================================
# 2. PRODUITS
# ==================================================================
with tab_products:
    st.markdown("### Catalogue")
    st.caption(
        "Ce que les détaillants voient sur la page de commande. "
        "Désactivez un produit pour le retirer de la liste sans perdre l'historique."
    )

    try:
        products = load_products()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Lecture du catalogue impossible : `{exc}`")
        products = []

    def reorder(product_list: list[dict], index: int, delta: int) -> None:
        """Déplace un produit vers le haut/bas et renumérote proprement sort_order."""
        target = index + delta
        if not 0 <= target < len(product_list):
            return
        reordered = list(product_list)
        reordered[index], reordered[target] = reordered[target], reordered[index]
        for position, prod in enumerate(reordered, start=1):
            if prod["sort_order"] != position * 10:
                client.table("products").update({"sort_order": position * 10}).eq(
                    "id", prod["id"]
                ).execute()

    for index, product in enumerate(products):
        with st.container(border=True):
            title_col, up_col, down_col, active_col = st.columns([6, 1, 1, 2])
            with title_col:
                state = "" if product["is_active"] else "  ·  :gray[désactivé]"
                price_txt = money(product.get("price"))
                st.markdown(
                    f"**{product['name']}**{state}  \n"
                    f":gray[{product.get('category') or 'Sans catégorie'} — "
                    f"{product.get('unit') or 'unité'}"
                    f"{' — ' + price_txt if price_txt else ' — prix à saisir'}]"
                )
            with up_col:
                if st.button("⬆️", key=f"up_{product['id']}", disabled=index == 0,
                             width="stretch", help="Monter"):
                    reorder(products, index, -1)
                    st.rerun()
            with down_col:
                if st.button("⬇️", key=f"down_{product['id']}", disabled=index == len(products) - 1,
                             width="stretch", help="Descendre"):
                    reorder(products, index, 1)
                    st.rerun()
            with active_col:
                label = "Désactiver" if product["is_active"] else "Activer"
                if st.button(label, key=f"toggle_{product['id']}", width="stretch"):
                    client.table("products").update(
                        {"is_active": not product["is_active"]}
                    ).eq("id", product["id"]).execute()
                    st.rerun()

            with st.expander("Modifier"):
                with st.form(f"edit_product_{product['id']}"):
                    name = st.text_input("Nom", value=product["name"])
                    description = st.text_area(
                        "Description", value=product.get("description") or "", height=80
                    )
                    f1, f2, f3 = st.columns(3)
                    category = f1.text_input("Catégorie", value=product.get("category") or "")
                    unit = f2.text_input("Format / unité", value=product.get("unit") or "unité")
                    price = f3.number_input(
                        "Prix ($)",
                        min_value=0.0,
                        step=0.25,
                        format="%.2f",
                        value=float(product["price"]) if product.get("price") is not None else 0.0,
                        help="0 = aucun prix affiché aux détaillants.",
                    )
                    image_url = st.text_input(
                        "URL de l'image", value=product.get("image_url") or "",
                        placeholder="https://…/ketchup-classique.jpg",
                    )
                    if st.form_submit_button("Enregistrer", type="primary"):
                        try:
                            client.table("products").update(
                                {
                                    "name": name.strip(),
                                    "description": description.strip() or None,
                                    "category": category.strip() or None,
                                    "unit": unit.strip() or "unité",
                                    "price": float(price) if price > 0 else None,
                                    "image_url": image_url.strip() or None,
                                }
                            ).eq("id", product["id"]).execute()
                            st.success("Produit mis à jour.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Échec de l'enregistrement : `{exc}`")

                confirm = st.checkbox(
                    "Je veux supprimer définitivement ce produit", key=f"del_ok_{product['id']}"
                )
                if st.button("🗑️ Supprimer", key=f"del_{product['id']}", disabled=not confirm):
                    client.table("products").delete().eq("id", product["id"]).execute()
                    st.rerun()

    with st.expander("➕ Ajouter un produit"):
        with st.form("new_product", clear_on_submit=True):
            n_name = st.text_input("Nom *")
            n_desc = st.text_area("Description", height=80)
            n1, n2, n3 = st.columns(3)
            n_cat = n1.text_input("Catégorie", placeholder="Ketchups")
            n_unit = n2.text_input("Format / unité", value="bouteille 350 ml")
            n_price = n3.number_input("Prix ($)", min_value=0.0, step=0.25, format="%.2f")
            n_image = st.text_input("URL de l'image")
            if st.form_submit_button("Ajouter au catalogue", type="primary"):
                if not n_name.strip():
                    st.error("Le nom est requis.")
                else:
                    try:
                        client.table("products").insert(
                            {
                                "name": n_name.strip(),
                                "description": n_desc.strip() or None,
                                "category": n_cat.strip() or None,
                                "unit": n_unit.strip() or "unité",
                                "price": float(n_price) if n_price > 0 else None,
                                "image_url": n_image.strip() or None,
                                "sort_order": (max((p["sort_order"] for p in products), default=0) + 10),
                            }
                        ).execute()
                        st.success("Produit ajouté.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Échec de l'ajout : `{exc}`")


# ==================================================================
# 3. DÉTAILLANTS
# ==================================================================
with tab_retailers:
    st.markdown("### Détaillants enregistrés")
    st.caption(
        "Ce sont les commerces proposés dans la liste déroulante de la page de "
        "commande. Ajoutez un détaillant une seule fois ici : ensuite il commande "
        "en 3 clics, sans jamais retaper ses coordonnées."
    )

    try:
        retailers = load_retailers()
        retailers_ok = True
    except Exception as exc:  # noqa: BLE001
        retailers_ok = False
        retailers = []
        st.error(
            "La table `retailers` est introuvable. Exécutez `supabase_schema.sql` "
            f"dans Supabase (SQL Editor) pour la créer.\n\n`{exc}`"
        )

    if retailers_ok:
        c_search, c_count = st.columns([4, 1])
        with c_search:
            search = st.text_input(
                "Rechercher", placeholder="Nom du commerce…", label_visibility="collapsed"
            )
        with c_count:
            st.metric("Actifs", sum(1 for r in retailers if r["is_active"]))

        needle = (search or "").strip().lower()
        visible = [
            r
            for r in retailers
            if not needle
            or needle in (r["business_name"] or "").lower()
            or needle in (r.get("contact_name") or "").lower()
        ]

        for retailer in visible:
            with st.container(border=True):
                info_col, toggle_col = st.columns([6, 2])
                with info_col:
                    state = "" if retailer["is_active"] else "  ·  :gray[désactivé]"
                    details = " · ".join(
                        v for v in (
                            retailer.get("contact_name"),
                            retailer.get("phone"),
                            retailer.get("email"),
                        ) if v
                    )
                    st.markdown(
                        f"**{retailer['business_name']}**{state}  \n"
                        f":gray[{details or 'Aucune coordonnée enregistrée'}]"
                    )
                with toggle_col:
                    label = "Désactiver" if retailer["is_active"] else "Activer"
                    if st.button(label, key=f"rtoggle_{retailer['id']}", width="stretch"):
                        client.table("retailers").update(
                            {"is_active": not retailer["is_active"]}
                        ).eq("id", retailer["id"]).execute()
                        st.rerun()

                with st.expander("Modifier"):
                    with st.form(f"edit_retailer_{retailer['id']}"):
                        r_name = st.text_input("Nom du commerce *", value=retailer["business_name"])
                        r1, r2, r3 = st.columns(3)
                        r_contact = r1.text_input("Contact", value=retailer.get("contact_name") or "")
                        r_phone = r2.text_input("Téléphone", value=retailer.get("phone") or "")
                        r_email = r3.text_input("Courriel", value=retailer.get("email") or "")
                        r_notes = st.text_area(
                            "Notes internes", value=retailer.get("notes") or "", height=70,
                            help="Visible uniquement ici, jamais sur la page de commande.",
                        )
                        if st.form_submit_button("Enregistrer", type="primary"):
                            if not r_name.strip():
                                st.error("Le nom du commerce est requis.")
                            else:
                                try:
                                    client.table("retailers").update(
                                        {
                                            "business_name": r_name.strip(),
                                            "contact_name": r_contact.strip() or None,
                                            "phone": r_phone.strip() or None,
                                            "email": r_email.strip() or None,
                                            "notes": r_notes.strip() or None,
                                        }
                                    ).eq("id", retailer["id"]).execute()
                                    st.success("Détaillant mis à jour.")
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    st.error(f"Échec de l'enregistrement : `{exc}`")

        if not visible:
            st.info("Aucun détaillant ne correspond à cette recherche.")

        with st.expander("➕ Ajouter un détaillant", expanded=not retailers):
            with st.form("new_retailer", clear_on_submit=True):
                a_name = st.text_input("Nom du commerce *", placeholder="Épicerie du Coin")
                a1, a2, a3 = st.columns(3)
                a_contact = a1.text_input("Contact", placeholder="Prénom Nom")
                a_phone = a2.text_input("Téléphone")
                a_email = a3.text_input("Courriel")
                a_notes = st.text_area("Notes internes", height=70)
                if st.form_submit_button("Ajouter à la liste", type="primary"):
                    if not a_name.strip():
                        st.error("Le nom du commerce est requis.")
                    else:
                        try:
                            client.table("retailers").insert(
                                {
                                    "business_name": a_name.strip(),
                                    "contact_name": a_contact.strip() or None,
                                    "phone": a_phone.strip() or None,
                                    "email": a_email.strip() or None,
                                    "notes": a_notes.strip() or None,
                                }
                            ).execute()
                            st.success(f"« {a_name.strip()} » peut maintenant commander.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(
                                "Échec de l'ajout (un commerce du même nom existe "
                                f"peut-être déjà).\n\n`{exc}`"
                            )
